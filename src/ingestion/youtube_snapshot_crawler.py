import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from src.ingestion.upload_raw_to_minio import upload_file_to_minio
from src.utils.db_connection import get_connection

load_dotenv()

# Receive region code from command line
parser = argparse.ArgumentParser(
    description="Collect hourly YouTube video statistics by region."
)

parser.add_argument(
    "--region",
    required=True,
    help="YouTube region code, for example: VN, US, JP",
)

args = parser.parse_args()

REGION_CODE = args.region.upper()

API_KEY = os.getenv("YOUTUBE_API_KEY")

if not API_KEY:
    raise ValueError(
        "YOUTUBE_API_KEY was not found. Check your .env file."
    )

BASE_DATASET = "data/processed/youtube_dataset_2000_clean.csv"

OUTPUT_DIR = (
    Path("data/raw/snapshots")
    / REGION_CODE
)

VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    BASE_DATASET,
    dtype={
        "video_id": "string",
        "region_code": "string",
        "category_id": "string",
    },
)

df = df[
    df["region_code"].str.upper() == REGION_CODE
].copy()

if df.empty:
    raise ValueError(
        f"No videos found for region {REGION_CODE}"
    )

collected_at = datetime.now(timezone.utc)
timestamp = collected_at.strftime("%Y%m%d_%H%M%S")

print("Checking trending videos for region:", REGION_CODE)

params = {
    "part": "snippet,statistics",
    "chart": "mostPopular",
    "regionCode": REGION_CODE,
    "maxResults": 50,
    "key": API_KEY,
}

response = requests.get(
    VIDEOS_URL,
    params=params,
    timeout=30,
)

print("Status Code:", response.status_code)

if response.status_code != 200:
    raise RuntimeError(
        f"YouTube API error: {response.text}"
    )

data = response.json()

popular_videos = {
    video["id"]: rank
    for rank, video in enumerate(
        data.get("items", []),
        start=1,
    )
}

video_ids = (
    df["video_id"]
    .dropna()
    .drop_duplicates()
    .tolist()
)

statistics_by_id = {}

for start in range(0, len(video_ids), 50):
    batch = video_ids[start:start + 50]

    params = {
        "part": "statistics",
        "id": ",".join(batch),
        "key": API_KEY,
    }

    response = requests.get(
        VIDEOS_URL,
        params=params,
        timeout=30,
    )

    if response.status_code != 200:
        print(response.text)
        continue

    data = response.json()

    for video in data.get("items", []):
        statistics_by_id[video["id"]] = video.get(
            "statistics",
            {},
        )

records = []

for _, row in df.iterrows():
    video_id = str(row["video_id"])
    region = str(row["region_code"])

    statistics = statistics_by_id.get(
        video_id,
        {},
    )

    trending_rank = popular_videos.get(video_id)

    record = {
        "video_id": video_id,
        "title": row["title"],
        "channel_id": row["channel_id"],
        "channel_title": row["channel_title"],
        "category_id": row["category_id"],
        "published_at": row["published_at"],
        "region_code": region,
        "collected_at": collected_at.isoformat(),
        "view_count": statistics.get("viewCount"),
        "like_count": statistics.get("likeCount"),
        "comment_count": statistics.get("commentCount"),
        "is_trending": 1 if trending_rank is not None else 0,
        "trending_rank": trending_rank,
        "video_available": video_id in statistics_by_id,
    }

    records.append(record)

output_path = OUTPUT_DIR / (
    f"youtube_{REGION_CODE}_{timestamp}.json"
)

with open(
    output_path,
    "w",
    encoding="utf-8",
) as file:
    json.dump(
        records,
        file,
        ensure_ascii=False,
        indent=2,
    )

minio_object_name = (
    f"snapshots/{REGION_CODE}/{output_path.name}"
)

upload_file_to_minio(
    output_path,
    minio_object_name,
)

def to_int_or_none(value):
    if value is None or value == "":
        return None
    return int(value)

sql_rows = []

for record in records:
    sql_rows.append(
        (
            record["video_id"],
            record["region_code"],
            collected_at,
            to_int_or_none(record["view_count"]),
            to_int_or_none(record["like_count"]),
            to_int_or_none(record["comment_count"]),
            record["is_trending"],
            record["trending_rank"],
            record["video_available"],
        )
    )


insert_sql = """
INSERT INTO dbo.youtube_video_snapshots (
    video_id,
    region_code,
    collected_at,
    view_count,
    like_count,
    comment_count,
    is_trending,
    trending_rank,
    video_available
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


connection = get_connection()
cursor = None

try:
    cursor = connection.cursor()

    cursor.fast_executemany = True

    cursor.executemany(
        insert_sql,
        sql_rows,
    )

    connection.commit()

    sql_inserted = len(sql_rows)

finally:
    if cursor is not None:
        cursor.close()

    connection.close()

available_count = sum(
    1 for record in records
    if record["video_available"]
)

trending_count = sum(
    1 for record in records
    if record["is_trending"] == 1
)

print()
print("=" * 60)
print("SNAPSHOT COMPLETED")
print("Records:", len(records))
print("Available videos:", available_count)
print("Trending now:", trending_count)
print("Control now:", len(records) - trending_count)
print("SQL rows inserted:", sql_inserted)
print("Collected at:", collected_at.isoformat())
print("Saved to:", output_path)
print("MinIO object:", minio_object_name)
print("=" * 60)