
# RQ1 - Exploratory Data Analysis
# Vietnam Rolling Cohort - Pilot Dataset

# 1. Load data
rq1 <- read.csv(
  "data/processed/rq1_youtube_cohort_VN.csv",
  stringsAsFactors = FALSE
)

# 2. Prepare upload hours
hours <- as.integer(rq1$upload_hour_local)

fresh <- tolower(
  as.character(rq1$primary_fresh_24h)
) == "true"

stopifnot(
  !anyNA(hours),
  all(hours %in% 0:23),
  !anyNA(fresh)
)

# 3. Count videos for each hour
all_counts <- tabulate(hours + 1L, nbins = 24)

fresh_counts <- tabulate(
  hours[fresh] + 1L,
  nbins = 24
)

hour_table <- rbind(
  "All Videos" = all_counts,
  "Discovered Within 24h" = fresh_counts
)

print(hour_table)

# 4. Define visualization
draw_upload_plot <- function() {
  barplot(
    hour_table,
    beside = TRUE,
    col = c("steelblue", "darkorange"),
    names.arg = sprintf("%02d", 0:23),
    main = "RQ1 - Upload Hour Distribution (VN Pilot)",
    xlab = "Upload Hour (Vietnam)",
    ylab = "Number of Videos",
    las = 2,
    cex.names = 0.8,
    legend.text = rownames(hour_table),
    args.legend = list(x = "topright", bty = "n")
  )
}

# 5. Display in RStudio
draw_upload_plot()

# 6. Save image for Report 3
dir.create(
  "reports/assets/rq1",
  recursive = TRUE,
  showWarnings = FALSE
)

png(
  "reports/assets/rq1/rq1_upload_hours_vn_R.png",
  width = 1800,
  height = 900,
  res = 150
)

draw_upload_plot()
dev.off()

cat("EDA chart saved successfully!\n")


# ==========================================
# RQ1 - EDA 2: Video Age at T0
# ==========================================

# 1. Prepare age data
office_age <- rq1$video_age_at_t0_hours[
  rq1$upload_period == "OFFICE_HOURS"
]

non_office_age <- rq1$video_age_at_t0_hours[
  rq1$upload_period == "NON_OFFICE_HOURS"
]

age_data <- list(
  office_age,
  non_office_age
)

names(age_data) <- c(
  paste0("Office Hours (n=", length(office_age), ")"),
  paste0("Non-Office Hours (n=", length(non_office_age), ")")
)

# 2. Summary statistics
print(sapply(age_data, median, na.rm = TRUE))
print(sapply(age_data, mean, na.rm = TRUE))

# 3. Create boxplot function
draw_age_plot <- function() {
  boxplot(
    age_data,
    main = "RQ1 - Video Age at T0 by Upload Period (VN Pilot)",
    ylab = "Video Age at T0 (hours)",
    col = c("lightblue", "moccasin"),
    border = "gray30",
    outline = TRUE
  )

  points(
    1:2,
    sapply(age_data, mean, na.rm = TRUE),
    pch = 17,
    col = "darkgreen",
    cex = 1.4
  )
}

# 4. Display in RStudio
draw_age_plot()

# 5. Save image
png(
  "reports/assets/rq1/rq1_video_age_by_period_vn_R.png",
  width = 1800,
  height = 1000,
  res = 150
)

draw_age_plot()
dev.off()

cat("Video age boxplot saved successfully!\n")


# ==========================================
# RQ1 - EDA 3: Channel Diversity
# ==========================================

# 1. Load channel summary
channels <- read.csv(
  "data/processed/rq1_channel_diversity_VN.csv",
  stringsAsFactors = FALSE
)

# 2. Select top 10 channels
channels <- channels[
  order(channels$total_videos, decreasing = TRUE),
]

top10 <- head(channels, 10)

# Reverse for horizontal bar chart
top10 <- top10[nrow(top10):1, ]

# 3. Prepare stacked counts
channel_counts <- rbind(
  "Office Hours" = top10$office_videos,
  "Non-Office Hours" = top10$non_office_videos
)

print(top10[, c(
  "channel_title",
  "total_videos",
  "office_videos",
  "non_office_videos"
)])

# 4. Define plot function
draw_channel_plot <- function() {

  par(mar = c(5, 18, 4, 2))

  barplot(
    channel_counts,
    horiz = TRUE,
    names.arg = top10$channel_title,
    col = c("steelblue", "darkorange"),
    las = 1,
    cex.names = 0.8,
    xlim = c(0, max(top10$total_videos) + 2),
    main = "RQ1 - Channel Diversity (VN Pilot)",
    xlab = "Number of Videos",
    legend.text = rownames(channel_counts),
    args.legend = list(
      x = "bottomright",
      bty = "n"
    )
  )
}

# 5. Display in RStudio
draw_channel_plot()

# 6. Export PNG
png(
  "reports/assets/rq1/rq1_channel_diversity_vn_R.png",
  width = 2000,
  height = 1200,
  res = 160
)

draw_channel_plot()
dev.off()

cat("Channel diversity chart saved successfully!\n")

# ==========================================
# RQ1 - EDA 4: Summary Statistics
# ==========================================

periods <- c("OFFICE_HOURS", "NON_OFFICE_HOURS")

eda_summary <- do.call(
  rbind,
  lapply(periods, function(p) {

    x <- rq1[rq1$upload_period == p, ]

    data.frame(
      upload_period = p,
      total_videos = length(unique(x$video_id)),
      unique_channels = length(unique(x$channel_id)),
      median_age_hours = round(
        median(x$video_age_at_t0_hours, na.rm = TRUE), 2
      ),

      fresh_24h = sum(
        tolower(as.character(x$primary_fresh_24h)) == "true",
        na.rm = TRUE
      ),
      analysis_ready = sum(
        tolower(as.character(x$rq1_analysis_ready)) == "true",
        na.rm = TRUE
      )

    )
  })
)

print(eda_summary)

write.csv(
  eda_summary,
  "reports/assets/rq1/rq1_eda_summary_vn_R.csv",
  row.names = FALSE
)

cat("RQ1 EDA summary saved successfully!\n")

# ==========================================
# RQ1 - EDA 5: T0-T24 View Growth
# ==========================================

# 1. Reload updated RQ1 dataset
rq1 <- read.csv(
  "data/processed/rq1_youtube_cohort_VN.csv",
  stringsAsFactors = FALSE
)

# 2. Select videos with completed T24
ready <- tolower(as.character(rq1$t24_ready)) == "true"
growth <- rq1[!is.na(ready) & ready, ]

# 3. Calculate average view growth per hour
growth$view_delta_t24 <- as.numeric(growth$view_delta_t24)
growth$actual_t24_hours <- as.numeric(growth$actual_t24_hours)

growth <- growth[
  !is.na(growth$view_delta_t24) &
    is.finite(growth$actual_t24_hours) &
    growth$actual_t24_hours > 0 &
    growth$view_delta_t24 >= 0,
]

growth$views_per_hour <- (
  growth$view_delta_t24 / growth$actual_t24_hours
)

# 4. Prepare upload periods
growth$upload_period <- factor(
  growth$upload_period,
  levels = c("OFFICE_HOURS", "NON_OFFICE_HOURS"),
  labels = c("Office Hours", "Non-Office Hours")
)

# 5. Check data
print(
  aggregate(
    views_per_hour ~ upload_period,
    data = growth,
    FUN = median
  )
)

cat("Valid T24 videos:", nrow(growth), "\n")

# 6. Create plot function
draw_growth_plot <- function() {

  if (nrow(growth) == 0) {
    stop("No valid T24 observations available.")
  }

  log_growth <- log1p(growth$views_per_hour)

  boxplot(
    log_growth ~ growth$upload_period,
    col = c("lightblue", "moccasin"),
    main = "RQ1 - T0 to T24 View Growth (VN Pilot)",
    xlab = "Upload Period",
    ylab = "Average Views per Hour (log scale)",
    outline = FALSE,
    yaxt = "n"
  )

  stripchart(
    log_growth ~ growth$upload_period,
    vertical = TRUE,
    method = "jitter",
    jitter = 0.12,
    pch = 19,
    col = "darkblue",
    add = TRUE
  )

  ticks <- c(0, 1, 10, 100, 500, 1000, 2000)

  axis(
    2,
    at = log1p(ticks),
    labels = ticks,
    las = 1
  )
}

# 7. Display in RStudio
draw_growth_plot()

# 8. Export image
png(
  "reports/assets/rq1/rq1_t24_growth_vn_R.png",
  width = 1800,
  height = 1100,
  res = 150
)

draw_growth_plot()
dev.off()

cat("T24 growth chart saved successfully!\n")

# ==========================================
# RQ1 - EDA 6: T24 Growth Summary
# ==========================================

growth_summary <- do.call(
  rbind,
  lapply(levels(growth$upload_period), function(p) {

    values <- growth$views_per_hour[
      !is.na(growth$upload_period) &
        growth$upload_period == p
    ]

    values <- values[is.finite(values)]

    data.frame(
      upload_period = p,
      videos = length(values),
      mean_views_per_hour = round(mean(values), 2),
      median_views_per_hour = round(median(values), 2),
      min_views_per_hour = round(min(values), 2),
      max_views_per_hour = round(max(values), 2)
    )
  })
)

print(growth_summary)

write.csv(
  growth_summary,
  "reports/assets/rq1/rq1_t24_growth_summary_vn_R.csv",
  row.names = FALSE
)

cat("T24 growth summary saved successfully!\n")
