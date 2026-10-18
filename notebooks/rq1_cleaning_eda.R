# ==============================================================================
# RQ1 Data Cleaning & Exploratory Data Analysis Script (HA2 & HA3)
# Rolling Cohort 24h & 7-Day Chart Observation Window (VN, US, JP)
# Member: Hà - Group 6 (ADY201m)
# ==============================================================================

suppressPackageStartupMessages({
  library(tidyverse)
  library(lubridate)
  library(jsonlite)
  library(scales)
})

# 1. Thiet lap duong dan
DATA_PROCESSED <- "data/processed"
ASSETS_DIR <- "reports/assets/rq1"

if (!dir.exists(ASSETS_DIR)) {
  dir.create(ASSETS_DIR, recursive = TRUE)
}

# 2. Doc file processed dataset (Muc 18)
input_file <- file.path(DATA_PROCESSED, "youtube_dataset_2000_clean.csv")
if (!file.exists(input_file)) {
  stop("Khong tim thay file processed dataset: ", input_file)
}

raw_df <- read.csv(input_file, fileEncoding = "UTF-8", stringsAsFactors = FALSE)
message("Doc thanh cong: ", nrow(raw_df), " ban ghi.")

# 3. Chuan hoa Schema & Feature Engineering (Muc 14)
clean_rq1_data <- function(df) {
  df %>%
    mutate(
      pub_utc = ymd_hms(published_at, quiet = TRUE),
      local_published_at = case_when(
        region_code == "JP" ~ with_tz(pub_utc, tzone = "Asia/Tokyo"),
        region_code == "VN" ~ with_tz(pub_utc, tzone = "Asia/Ho_Chi_Minh"),
        region_code == "US" ~ with_tz(pub_utc, tzone = "America/New_York"),
        TRUE ~ pub_utc
      ),
      local_upload_hour = hour(local_published_at),
      upload_period = if_else(local_upload_hour >= 9 & local_upload_hour < 17, "Office", "Rest"),
      chart_coverage_ratio = if_else(rep("chart_coverage_ratio" %in% names(df), n()), as.numeric(df$chart_coverage_ratio), 1.0),
      is_trending_num = if_else(rep("is_trending" %in% names(df), n()), as.integer(df$is_trending), 0L),
      chart_status = case_when(
        is_trending_num == 1 ~ "OBSERVED_CHARTED",
        chart_coverage_ratio >= 0.70 ~ "NOT_OBSERVED_WITH_COVERAGE",
        TRUE ~ "INCOMPLETE_COVERAGE"
      ),
      best_rank = if_else(rep("trending_rank" %in% names(df), n()), as.integer(df$trending_rank), NA_integer_)
    )
}

d <- clean_rq1_data(raw_df)

# Xuat youtube_rq1_dataset.csv (Muc 15 & Muc 18)
output_rq1_dataset <- file.path(DATA_PROCESSED, "youtube_rq1_dataset.csv")
write.csv(d, output_rq1_dataset, row.names = FALSE, fileEncoding = "UTF-8")
message("Da luu file: ", output_rq1_dataset)

# 4. QA & Kiem tra Schema bat buoc (Muc 18 & Muc 21)
stopifnot(all(c("video_id", "region_code", "upload_period", "chart_status") %in% names(d)))

message("--- PHAN PHOI THEO REGION ---")
print(table(d$region_code, useNA = "ifany"))

message("--- PHAN PHOI THEO CHART STATUS ---")
print(table(d$chart_status, useNA = "ifany"))

# Primary sample requires explicit completed-coverage labeling
x <- subset(d, chart_status %in% c("OBSERVED_CHARTED", "NOT_OBSERVED_WITH_COVERAGE"))
x$charted <- as.integer(x$chart_status == "OBSERVED_CHARTED")

message("--- BANG CHEO REGION x UPLOAD_PERIOD x CHARTED ---")
print(with(x, table(region_code, upload_period, charted)))

global_unique <- n_distinct(d$video_id)
eligible_count <- nrow(x)
message("=== MUC 21: DOI SOAT QUY MO ===")
message("Global unique video_id (Muc tieu >= 100k): ", global_unique)
message("Eligible RQ1 sample (Du do phu quan sat): ", eligible_count)

# 5. Ve va luu bieu do (Muc 19 & Muc 20)
# Bieu do 1: Upload hour by region
p1 <- ggplot(d, aes(x = local_upload_hour, fill = region_code)) +
  geom_bar(position = "dodge", alpha = 0.85, color = "black", linewidth = 0.2) +
  scale_x_continuous(breaks = 0:23) +
  labs(title = "Phan phoi So luong Video theo Gio Upload Dia phuong", x = "Gio Upload (0 - 23)", y = "So luong Video", fill = "Thi truong") +
  theme_minimal()
ggsave(file.path(ASSETS_DIR, "rq1_upload_hour_by_region.png"), p1, width = 10, height = 5, dpi = 300)

# Bieu do 2: Office vs Rest distribution with numerator/denominator
period_df <- d %>%
  group_by(region_code, upload_period) %>%
  summarise(n = n(), .groups = "drop_last") %>%
  mutate(total = sum(n), pct = round((n / total) * 100, 1), label_text = paste0(n, "/", total, "\n(", pct, "%)"))

p2 <- ggplot(period_df, aes(x = region_code, y = n, fill = upload_period)) +
  geom_bar(stat = "identity", position = position_dodge(width = 0.8), alpha = 0.85, color = "black", linewidth = 0.2) +
  geom_text(aes(label = label_text), position = position_dodge(width = 0.8), vjust = -0.3, size = 3.5, fontface = "bold") +
  scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
  labs(title = "Phan bo Video: Office vs. Rest", x = "Thi truong", y = "So luong Video", fill = "Khung gio") +
  theme_minimal()
ggsave(file.path(ASSETS_DIR, "rq1_office_rest_distribution.png"), p2, width = 9, height = 5, dpi = 300)

# Bieu do 3: Chart status distribution
status_df <- d %>%
  group_by(region_code, chart_status) %>%
  summarise(n = n(), .groups = "drop_last") %>%
  mutate(total = sum(n), pct = round((n / total) * 100, 1), label_text = paste0(n, "/", total, "\n(", pct, "%)"))

p3 <- ggplot(status_df, aes(x = region_code, y = n, fill = chart_status)) +
  geom_bar(stat = "identity", position = position_dodge(width = 0.8), alpha = 0.85, color = "black", linewidth = 0.2) +
  geom_text(aes(label = label_text), position = position_dodge(width = 0.8), vjust = -0.3, size = 3.2) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
  labs(title = "Phan phoi Trang thai Chart Status", x = "Thi truong", y = "So luong Video", fill = "Trang thai") +
  theme_minimal()
ggsave(file.path(ASSETS_DIR, "rq1_chart_status_distribution.png"), p3, width = 10, height = 5, dpi = 300)

# Bieu do 4: Observed chart rate (Office vs Rest tren tap eligible)
chart_rate_df <- x %>%
  group_by(region_code, upload_period) %>%
  summarise(charted_count = sum(charted), total_eligible = n(), .groups = "drop") %>%
  mutate(rate = round((charted_count / total_eligible) * 100, 2), label_text = paste0(charted_count, "/", total_eligible, "\n(", rate, "%)"))

p4 <- ggplot(chart_rate_df, aes(x = upload_period, y = rate, fill = upload_period)) +
  geom_bar(stat = "identity", width = 0.6, alpha = 0.85, color = "black", linewidth = 0.2) +
  geom_text(aes(label = label_text), vjust = -0.4, size = 3.5, fontface = "bold") +
  facet_wrap(~ region_code) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.2))) +
  labs(title = "Observed Chart Rate: Office vs. Rest", x = "Khung gio", y = "Ty le lot Chart (%)", fill = "Khung gio") +
  theme_minimal()
ggsave(file.path(ASSETS_DIR, "rq1_observed_chart_rate_office_vs_rest.png"), p4, width = 10, height = 5, dpi = 300)

message("Hoan tat! Tat ca bieu do da duoc luu vao: ", ASSETS_DIR)

# ==============================================================================
# 7. Kiem dinh Gia thuyet RQ1 theo tung Thi truong (Nhiem vu HA4)
# ==============================================================================
message("\n=== KIEM DINH GIA THUYET RQ1 (CHI-SQUARE / FISHER) ===")

for (reg in c("VN", "US", "JP")) {
  message("\n--- Kiem dinh thi truong: ", reg, " ---")
  a <- subset(x, region_code == reg & upload_period %in% c("Office", "Rest"))
  t <- table(a$upload_period, a$charted)
  print(t)
  if (all(dim(t) == c(2, 2))) {
    expected <- suppressWarnings(chisq.test(t)$expected)
    if (any(expected < 5)) {
      message("-> Co tan so ky vong < 5: Su dung Fisher's Exact Test:")
      print(fisher.test(t))
    } else {
      message("-> Su dung Pearson Chi-square Test:")
      print(chisq.test(t, correct = FALSE))
    }
  } else {
    message("Chua du bien thien 2x2 cho thi truong: ", reg)
  }
}
