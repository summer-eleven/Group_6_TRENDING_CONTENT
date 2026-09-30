import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

#Bổ sung nhận tham số dòng lệnh --region
parser = argparse.ArgumentParser(description="YouTube Snapshot Crawler")
parser.add_argument("--region", type=str, default=None, help="Mã quốc gia cần crawl (vd: JP)")
args = parser.parse_args()


API_KEY = os.getenv("YOUTUBE_API_KEY")

BASE_DATASET = "data/processed/youtube_dataset_2000_clean.csv"
OUTPUT_DIR = Path("data/raw/snapshots")

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

#Nếu có truyền --region JP, chỉ lọc đúng region đó
if args.region:
    df = df[df["region_code"] == args.region.upper()]
    regions = [args.region.upper()]
    print(f"--> Đang lọc snapshot riêng cho Region: {args.region.upper()} ({len(df)} videos)")
else:
    regions = sorted(df["region_code"].dropna().unique())
    
collected_at = datetime.now(timezone.utc)
timestamp = collected_at.strftime("%Y%m%d_%H%M%S")

#regions = sorted(
#    df["region_code"]
#    .dropna()
#    .unique()
#)

popular_by_region = {}

for region in regions:
    print("Checking trending videos for region:", region)

    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region,
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
        print(response.text)
        popular_by_region[region] = {}
        continue

    data = response.json()

    popular_by_region[region] = {
        video["id"]: rank
        for rank, video in enumerate(
            data.get("items", []),
            start=1,
        )
    }

video_ids = df["video_id"].dropna().tolist()

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

    trending_rank = popular_by_region.get(
        region,
        {},
    ).get(video_id)

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

output_path = OUTPUT_DIR / f"youtube_snapshot_{timestamp}.json"

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

available_count = sum(
    1 for record in records
    if record["video_available"]
)

trending_count = sum(
    1 for record in records
    if record["is_trending"] == 1
)

# Tự động gắn tên region vào tên file (VD: youtube_snapshot_JP_20260930_140000.json)
region_suffix = f"_{args.region.upper()}" if args.region else "_ALL"
output_path = OUTPUT_DIR / f"youtube_snapshot{region_suffix}_{timestamp}.json"

print()
print("=" * 60)
print("SNAPSHOT COMPLETED")
print("Records:", len(records))
print("Available videos:", available_count)
print("Trending now:", trending_count)
print("Control now:", len(records) - trending_count)
print("Collected at:", collected_at.isoformat())
print("Saved to:", output_path)
print("=" * 60)