"""
build_youtube_dataset_jp.py

Merge JP expansion (trending + control) vao dataset hien co va rebuild.
Chay sau khi youtube_jp_expansion_crawler.py hoan thanh.

Chay:
  python -m src.processing.build_youtube_dataset_jp
"""

import pandas as pd
import json
from pathlib import Path


BASE_DATASET = "data/processed/youtube_dataset_2000_clean.csv"
TRENDING_JP_PATH = "data/raw/youtube_jp_trending_expansion_raw.json"
CONTROL_JP_PATH = "data/raw/youtube_jp_control_expansion_raw.json"

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
    with open(path, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not records:
        return pd.DataFrame(columns=COLUMN_ORDER)

    df = pd.DataFrame(records)

    df["published_at"] = pd.to_datetime(
        df["published_at"], errors="coerce", utc=True,
    )

    df["collected_at"] = pd.to_datetime(
        df["collected_at"], errors="coerce", utc=True,
    )

    df["upload_hour_utc"] = df["published_at"].dt.hour.astype("Int64")

    for col in ["view_count", "like_count", "comment_count", "is_trending", "trending_rank"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    df["video_url"] = "https://www.youtube.com/watch?v=" + df["video_id"].astype(str)

    for col in COLUMN_ORDER:
        if col not in df.columns:
            df[col] = None

    return df[COLUMN_ORDER]


print("=" * 60)
print("REBUILD DATASET WITH JP EXPANSION")
print("=" * 60)

base_df = pd.read_csv(BASE_DATASET)

base_df["published_at"] = pd.to_datetime(
    base_df["published_at"], errors="coerce", utc=True,
)
base_df["collected_at"] = pd.to_datetime(
    base_df["collected_at"], errors="coerce", utc=True,
)

print("Base dataset rows:", len(base_df))

dfs_to_concat = [base_df[COLUMN_ORDER]]

for path, label in [
    (TRENDING_JP_PATH, "JP trending expansion"),
    (CONTROL_JP_PATH, "JP control expansion"),
]:
    if Path(path).exists():
        df = prepare_expansion(path)
        print(label + ":", len(df), "rows")
        dfs_to_concat.append(df)
    else:
        print("WARNING:", path, "not found — skipping.")

combined_df = pd.concat(dfs_to_concat, ignore_index=True)

before = len(combined_df)
print("\nBefore deduplication:", before)

combined_df = combined_df.sort_values(by="is_trending", ascending=False)
combined_df = combined_df.drop_duplicates(subset=["video_id"], keep="first")

after = len(combined_df)
print("After deduplication: ", after)
print("Duplicates removed:  ", before - after)
print()

jp_count = (combined_df["region_code"].str.upper() == "JP").sum()
trending_count = (combined_df["is_trending"] == 1).sum()
control_count = (combined_df["is_trending"] == 0).sum()

print("JP videos in dataset:", jp_count)
print("Total trending:       ", trending_count)
print("Total control:        ", control_count)

combined_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

print()
print("Saved to:", OUTPUT_PATH)
print("=" * 60)
