import json

import pandas as pd


INPUT_PATH = "data/raw/youtube_dataset_1000_raw.json"
OUTPUT_PATH = "data/processed/youtube_dataset_1000_clean.csv"


with open(INPUT_PATH, "r", encoding="utf-8") as file:
    records = json.load(file)

df = pd.DataFrame(records)

print("Original shape:", df.shape)


df = df.dropna(subset=["video_id"])
df = df.drop_duplicates(subset=["video_id"])


text_columns = [
    "video_id",
    "title",
    "channel_id",
    "channel_title",
    "category_id",
    "region_code",
]

for column in text_columns:
    df[column] = df[column].astype("string").str.strip()


numeric_columns = [
    "view_count",
    "like_count",
    "comment_count",
    "trending_rank",
]

for column in numeric_columns:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce",
    ).astype("Int64")


df["is_trending"] = pd.to_numeric(
    df["is_trending"],
    errors="coerce",
).astype("Int64")


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


df["upload_hour_utc"] = df["published_at"].dt.hour.astype("Int64")


df["video_url"] = (
    "https://www.youtube.com/watch?v="
    + df["video_id"].astype(str)
)


column_order = [
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

df = df[column_order]


df.to_csv(
    OUTPUT_PATH,
    index=False,
    encoding="utf-8-sig",
)


print("=" * 60)
print("CLEANING COMPLETED")
print("Clean shape:", df.shape)
print("Duplicate video IDs:", df["video_id"].duplicated().sum())
print("Trending:", (df["is_trending"] == 1).sum())
print("Control:", (df["is_trending"] == 0).sum())
print()
print("Missing values:")
print(df.isna().sum())
print()
print("Data types:")
print(df.dtypes)
print()
print("Saved to:", OUTPUT_PATH)
print("=" * 60)