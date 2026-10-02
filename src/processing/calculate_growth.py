import argparse
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(
    description="Calculate hourly growth and viral candidates for one region."
)
parser.add_argument(
    "--region",
    default="US",
    help="YouTube region code to analyse (default: US)",
)
args = parser.parse_args()

REGION = args.region.upper()
REGION_LOWER = REGION.lower()

INPUT_PATH = Path("data/processed/youtube_history.csv")
OUTPUT_PATH = Path("data/processed/youtube_growth.csv")
VIRAL_OUTPUT_PATH = Path(
    f"data/processed/youtube_viral_candidates_{REGION_LOWER}.csv"
)
TRENDING_OUTPUT_PATH = Path(
    f"data/processed/youtube_current_trending_{REGION_LOWER}.csv"
)

# Only intervals between 45 and 75 minutes count as "hourly"
HOURLY_MIN = 0.75
HOURLY_MAX = 1.25

# ---------------------------------------------------------------------------
# Load & type conversion
# ---------------------------------------------------------------------------
df = pd.read_csv(INPUT_PATH)

df["collected_at"] = pd.to_datetime(
    df["collected_at"],
    errors="coerce",
    utc=True,
)

for column in ["view_count", "like_count", "comment_count"]:
    df[column] = pd.to_numeric(df[column], errors="coerce")

df = df.sort_values(
    by=["video_id", "region_code", "collected_at"]
).reset_index(drop=True)

# ---------------------------------------------------------------------------
# Deltas between consecutive snapshots (per video + region)
# ---------------------------------------------------------------------------
grouped = df.groupby(["video_id", "region_code"], sort=False)

df["previous_collected_at"] = grouped["collected_at"].shift(1)

df["hours_elapsed"] = (
    (df["collected_at"] - df["previous_collected_at"])
    .dt.total_seconds()
    / 3600
)

df["view_delta"] = grouped["view_count"].diff()
df["like_delta"] = grouped["like_count"].diff()
df["comment_delta"] = grouped["comment_count"].diff()

df["previous_view_count"] = grouped["view_count"].shift(1)
df["previous_like_count"] = grouped["like_count"].shift(1)
df["previous_comment_count"] = grouped["comment_count"].shift(1)

valid_interval = df["hours_elapsed"] > 0

# Absolute growth per hour
df["views_per_hour"] = (df["view_delta"] / df["hours_elapsed"]).where(valid_interval)
df["likes_per_hour"] = (df["like_delta"] / df["hours_elapsed"]).where(valid_interval)
df["comments_per_hour"] = (df["comment_delta"] / df["hours_elapsed"]).where(valid_interval)

# Relative growth (% per hour) requires previous count > 0
for metric in ["view", "like", "comment"]:
    valid = valid_interval & (df[f"previous_{metric}_count"] > 0)
    df[f"{metric}_growth_pct_per_hour"] = (
        (df[f"{metric}_delta"] / df[f"previous_{metric}_count"])
        / df["hours_elapsed"]
        * 100
    ).where(valid)

df["is_hourly_interval"] = df["hours_elapsed"].between(HOURLY_MIN, HOURLY_MAX)

# ---------------------------------------------------------------------------
# Latest hourly snapshot for the chosen region
# ---------------------------------------------------------------------------
region_df = df[df["region_code"] == REGION]

if region_df.empty:
    raise ValueError(
        f"No rows found for region {REGION}. "
        f"Available regions: {sorted(df['region_code'].dropna().unique())}"
    )

latest_hourly = region_df[
    region_df["is_hourly_interval"] & region_df["views_per_hour"].notna()
].copy()

if latest_hourly.empty:
    raise ValueError(
        f"No valid hourly intervals for region {REGION}. "
        "Collect at least two snapshots about 1 hour apart."
    )

latest_hourly = (
    latest_hourly
    .sort_values("collected_at")
    .groupby(["video_id", "region_code"], as_index=False)
    .tail(1)
)

latest_hourly_time = latest_hourly["collected_at"].max()

latest_hourly = latest_hourly[
    latest_hourly["collected_at"] == latest_hourly_time
].copy()

# ---------------------------------------------------------------------------
# Percentile signals -> viral score
# ---------------------------------------------------------------------------
score_columns = [
    "views_per_hour",
    "view_growth_pct_per_hour",
    "likes_per_hour",
    "comments_per_hour",
]

for column in score_columns:
    latest_hourly[f"{column}_pct_rank"] = latest_hourly[column].rank(
        pct=True,
        method="average",
    )

rank_columns = [f"{c}_pct_rank" for c in score_columns]

latest_hourly["signal_count"] = latest_hourly[rank_columns].notna().sum(axis=1)
latest_hourly["viral_score"] = latest_hourly[rank_columns].mean(
    axis=1,
    skipna=True,
)

viral_candidates = (
    latest_hourly[latest_hourly["signal_count"] >= 3]
    .copy()
    .sort_values("viral_score", ascending=False)
)

top_viral_candidates = viral_candidates.head(20)

top_growth = latest_hourly.sort_values(
    "views_per_hour",
    ascending=False,
).head(20)

# ---------------------------------------------------------------------------
# Current trending list for the region
# ---------------------------------------------------------------------------
latest_region_time = region_df["collected_at"].max()

latest_region_snapshot = region_df[
    region_df["collected_at"] == latest_region_time
].copy()

current_trending = (
    latest_region_snapshot[latest_region_snapshot["is_trending"] == 1]
    .copy()
    .sort_values("trending_rank", ascending=True)
)

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
viral_candidates.to_csv(VIRAL_OUTPUT_PATH, index=False, encoding="utf-8-sig")
current_trending.to_csv(TRENDING_OUTPUT_PATH, index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
print("Region:", REGION)
print("History records:", len(df))
print("Unique videos:", df["video_id"].nunique())
print("Regions:", sorted(df["region_code"].dropna().unique()))
print("Viral ranking snapshot:", latest_hourly_time)
print("Saved to:", OUTPUT_PATH)

print()
print(f"Top 20 {REGION} videos by latest hourly view growth:")
print(
    top_growth[
        [
            "video_id",
            "title",
            "collected_at",
            "view_count",
            "views_per_hour",
            "view_growth_pct_per_hour",
            "likes_per_hour",
            "comments_per_hour",
            "is_trending",
            "trending_rank",
        ]
    ].to_string(index=False)
)

print()
print(f"Top 20 {REGION} viral candidates:")
print(
    top_viral_candidates[
        [
            "video_id",
            "title",
            "viral_score",
            "signal_count",
            "views_per_hour",
            "view_growth_pct_per_hour",
            "likes_per_hour",
            "comments_per_hour",
            "is_trending",
            "trending_rank",
        ]
    ].to_string(index=False)
)

print()
print("Viral candidates:", len(viral_candidates))
print(f"Current trending {REGION}:", len(current_trending))
print("Viral candidates saved to:", VIRAL_OUTPUT_PATH)
print(f"Current trending {REGION} saved to:", TRENDING_OUTPUT_PATH)