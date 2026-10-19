import json

import pandas as pd


BASE_PATH = "data/processed/youtube_dataset_1000_clean.csv"
TRENDING_PATH = "data/raw/youtube_trending_expansion_raw.json"
CONTROL_PATH = "data/raw/youtube_control_expansion_raw.json"

OUTPUT_PATH = "data/processed/youtube_dataset_2000_clean.csv"


COLUMN_ORDER = [
    "video_id",
    "title",
    "channel_id",
    "channel_title",
    "category_id",
    "published_at",
    "upload_hour_utc",
    "region_code",
    "collected_at",
    "view_count",
    "like_count",
    "comment_count",
    "is_trending",
    "trending_rank",
    "video_url",
]


def prepare_expansion(path):
    with open(path, "r", encoding="utf-8") as file:
        records = json.load(file)

    df = pd.DataFrame(records)

    df["published_at"] = pd.to_datetime(
        df["published_at"],
        errors="coerce",
        utc=True,
    )

    df["collected_at"] = pd.to_datetime(
        df["collected_at"],
        errors="coerce",
        utc=True,
    )

    df["upload_hour_utc"] = (
        df["published_at"]
        .dt.hour
        .astype("Int64")
    )

    numeric_columns = [
        "view_count",
        "like_count",
        "comment_count",
        "is_trending",
        "trending_rank",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        ).astype("Int64")

    df["video_url"] = (
        "https://www.youtube.com/watch?v="
        + df["video_id"].astype(str)
    )

    return df[COLUMN_ORDER]


base_df = pd.read_csv(BASE_PATH)

base_df["published_at"] = pd.to_datetime(
    base_df["published_at"],
    errors="coerce",
    utc=True,
)

base_df["collected_at"] = pd.to_datetime(
    base_df["collected_at"],
    errors="coerce",
    utc=True,
)

trending_df = prepare_expansion(TRENDING_PATH)
control_df = prepare_expansion(CONTROL_PATH)


combined_df = pd.concat(
    [
        base_df[COLUMN_ORDER],
        trending_df,
        control_df,
    ],
    ignore_index=True,
)


before_deduplication = len(combined_df)

duplicate_count = combined_df[
    "video_id"
].duplicated().sum()


combined_df = combined_df.sort_values(
    by="is_trending",
    ascending=False,
)

combined_df = combined_df.drop_duplicates(
    subset=["video_id"],
    keep="first",
)

after_deduplication = len(combined_df)


trending_count = (
    combined_df["is_trending"] == 1
).sum()

control_count = (
    combined_df["is_trending"] == 0
).sum()


combined_df.to_csv(
    OUTPUT_PATH,
    index=False,
    encoding="utf-8-sig",
)


print("=" * 60)
print("DATASET 2000 BUILD COMPLETED")
print("Base videos:", len(base_df))
print("New trending videos:", len(trending_df))
print("New control videos:", len(control_df))
print("Before deduplication:", before_deduplication)
print("Duplicate video IDs:", duplicate_count)
print("Total unique videos:", after_deduplication)
print("Trending:", trending_count)
print("Control:", control_count)
print("Saved to:", OUTPUT_PATH)
print("=" * 60)