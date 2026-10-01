from pathlib import Path

import pandas as pd


INPUT_PATH = Path(
    "data/processed/youtube_history.csv"
)

OUTPUT_PATH = Path(
    "data/processed/youtube_growth.csv"
)

VIRAL_OUTPUT_PATH = Path(
    "data/processed/youtube_viral_candidates_vn.csv"
)

TRENDING_OUTPUT_PATH = Path(
    "data/processed/youtube_current_trending_vn.csv"
)

df = pd.read_csv(INPUT_PATH)

df["collected_at"] = pd.to_datetime(
    df["collected_at"],
    errors="coerce",
    utc=True,
)

numeric_columns = [
    "view_count",
    "like_count",
    "comment_count",
]

for column in numeric_columns:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce",
    )

df = df.sort_values(
    by=[
        "video_id",
        "region_code",
        "collected_at",
    ]
).reset_index(drop=True)

group_columns = [
    "video_id",
    "region_code",
]

grouped = df.groupby(
    group_columns,
    sort=False,
)

df["previous_collected_at"] = grouped[
    "collected_at"
].shift(1)

df["hours_elapsed"] = (
    (
        df["collected_at"]
        - df["previous_collected_at"]
    )
    .dt.total_seconds()
    / 3600
)

df["view_delta"] = grouped[
    "view_count"
].diff()

df["like_delta"] = grouped[
    "like_count"
].diff()

df["comment_delta"] = grouped[
    "comment_count"
].diff()

df["previous_view_count"] = grouped[
    "view_count"
].shift(1)

df["previous_like_count"] = grouped[
    "like_count"
].shift(1)

df["previous_comment_count"] = grouped[
    "comment_count"
].shift(1)

valid_interval = df["hours_elapsed"] > 0

# Absolute growth per hour
df["views_per_hour"] = (
    df["view_delta"] / df["hours_elapsed"]
).where(valid_interval)

df["likes_per_hour"] = (
    df["like_delta"] / df["hours_elapsed"]
).where(valid_interval)

df["comments_per_hour"] = (
    df["comment_delta"] / df["hours_elapsed"]
).where(valid_interval)

# Valid conditions for percentage growth
valid_view_growth = (
    valid_interval
    & (df["previous_view_count"] > 0)
)

valid_like_growth = (
    valid_interval
    & (df["previous_like_count"] > 0)
)

valid_comment_growth = (
    valid_interval
    & (df["previous_comment_count"] > 0)
)


# Relative percentage growth per hour
df["view_growth_pct_per_hour"] = (
    (
        df["view_delta"]
        / df["previous_view_count"]
    )
    / df["hours_elapsed"]
    * 100
).where(valid_view_growth)

df["like_growth_pct_per_hour"] = (
    (
        df["like_delta"]
        / df["previous_like_count"]
    )
    / df["hours_elapsed"]
    * 100
).where(valid_like_growth)

df["comment_growth_pct_per_hour"] = (
    (
        df["comment_delta"]
        / df["previous_comment_count"]
    )
    / df["hours_elapsed"]
    * 100
).where(valid_comment_growth)

df["is_hourly_interval"] = (
    df["hours_elapsed"]
    .between(0.75, 1.25)
)

latest_hourly = df[
    (df["region_code"] == "VN")
    & (df["is_hourly_interval"])
    & (df["views_per_hour"].notna())
].copy()

latest_hourly = (
    latest_hourly
    .sort_values("collected_at")
    .groupby(
        ["video_id", "region_code"],
        as_index=False,
    )
    .tail(1)
)

latest_hourly_time = latest_hourly[
    "collected_at"
].max()

latest_hourly = latest_hourly[
    latest_hourly["collected_at"]
    == latest_hourly_time
].copy()

score_columns = [
    "views_per_hour",
    "view_growth_pct_per_hour",
    "likes_per_hour",
    "comments_per_hour",
]

for column in score_columns:
    latest_hourly[f"{column}_pct_rank"] = (
        latest_hourly[column]
        .rank(
            pct=True,
            method="average",
        )
    )

rank_columns = [
    "views_per_hour_pct_rank",
    "view_growth_pct_per_hour_pct_rank",
    "likes_per_hour_pct_rank",
    "comments_per_hour_pct_rank",
]

latest_hourly["signal_count"] = (
    latest_hourly[rank_columns]
    .notna()
    .sum(axis=1)
)

latest_hourly["viral_score"] = (
    latest_hourly[rank_columns]
    .mean(
        axis=1,
        skipna=True,
    )
)

viral_candidates = latest_hourly[
    latest_hourly["signal_count"] >= 3
].copy()

viral_candidates = viral_candidates.sort_values(
    "viral_score",
    ascending=False,
)

top_viral_candidates = viral_candidates.head(20)

latest_vn_time = df.loc[
    df["region_code"] == "VN",
    "collected_at",
].max()

latest_vn_snapshot = df[
    (df["region_code"] == "VN")
    & (df["collected_at"] == latest_vn_time)
].copy()

current_trending_vn = latest_vn_snapshot[
    latest_vn_snapshot["is_trending"] == 1
].copy()

current_trending_vn = current_trending_vn.sort_values(
    "trending_rank",
    ascending=True,
)

top_growth = (
    latest_hourly
    .sort_values(
        "views_per_hour",
        ascending=False,
    )
    .head(20)
)

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

df.to_csv(
    OUTPUT_PATH,
    index=False,
    encoding="utf-8-sig",
)

viral_candidates.to_csv(
    VIRAL_OUTPUT_PATH,
    index=False,
    encoding="utf-8-sig",
)

current_trending_vn.to_csv(
    TRENDING_OUTPUT_PATH,
    index=False,
    encoding="utf-8-sig",
)

print("History records:", len(df))
print("Unique videos:", df["video_id"].nunique())
print(
    "Regions:",
    sorted(df["region_code"].dropna().unique())
)

print(
    "Viral ranking snapshot:",
    latest_hourly_time,
)

print("Saved to:", OUTPUT_PATH)
print()
print("Growth preview:")

preview_columns = [
    "video_id",
    "region_code",
    "collected_at",
    "hours_elapsed",
    "view_count",
    "view_delta",
    "views_per_hour",
    "view_growth_pct_per_hour",
    "like_count",
    "like_delta",
    "likes_per_hour",
    "like_growth_pct_per_hour",
    "comment_count",
    "comment_delta",
    "comments_per_hour",
    "comment_growth_pct_per_hour",
    "is_hourly_interval",
]

print(
    df[
        df["is_hourly_interval"]
    ][preview_columns]
    .tail(20)
    .to_string(index=False)
)

print()
print("Top 20 VN videos by latest hourly view growth:")

ranking_columns = [
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

print(
    top_growth[
        ranking_columns
    ].to_string(index=False)
)

normalized_preview_columns = [
    "video_id",
    "title",
    "views_per_hour",
    "views_per_hour_pct_rank",
    "view_growth_pct_per_hour",
    "view_growth_pct_per_hour_pct_rank",
    "likes_per_hour",
    "likes_per_hour_pct_rank",
    "comments_per_hour",
    "comments_per_hour_pct_rank",
]

print()
print("Normalized growth preview:")

print(
    latest_hourly[
        normalized_preview_columns
    ]
    .sort_values(
        "views_per_hour_pct_rank",
        ascending=False,
    )
    .head(20)
    .to_string(index=False)
)

print()
print("Top 20 VN viral candidates:")

viral_columns = [
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

print(
    top_viral_candidates[
        viral_columns
    ].to_string(index=False)
)

print()
print("Viral candidates:", len(viral_candidates))
print("Current trending VN:", len(current_trending_vn))
print("Top viral candidates shown:", len(top_viral_candidates))

print("Viral candidates saved to:", VIRAL_OUTPUT_PATH)
print("Current trending VN saved to:", TRENDING_OUTPUT_PATH)