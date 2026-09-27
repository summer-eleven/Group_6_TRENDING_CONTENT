import json
import os
from datetime import datetime, timezone

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")

BASE_DATASET = "data/processed/youtube_dataset_1000_clean.csv"
OUTPUT_PATH = "data/raw/youtube_trending_expansion_raw.json"

API_URL = "https://www.googleapis.com/youtube/v3/videos"

REGIONS = [
    "VN",
    "US",
    "GB",
    "JP",
    "KR",
    "TH",
    "SG",
    "ID",
    "PH",
    "AU",
]

CATEGORY_IDS = [
    "10",
    "17",
    "20",
    "24",
    "25",
    "27",
    "28",
]

TARGET_NEW_VIDEOS = 600


base_df = pd.read_csv(
    BASE_DATASET,
    dtype={"video_id": "string"},
)

existing_ids = set(
    base_df["video_id"]
    .dropna()
    .astype(str)
)

new_records = {}
collected_at = datetime.now(timezone.utc).isoformat()


for region in REGIONS:
    for category_id in CATEGORY_IDS:
        if len(new_records) >= TARGET_NEW_VIDEOS:
            break

        print(
            "Collecting:",
            region,
            "category:",
            category_id,
        )

        params = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": region,
            "videoCategoryId": category_id,
            "maxResults": 50,
            "key": API_KEY,
        }

        response = requests.get(
            API_URL,
            params=params,
            timeout=30,
        )

        print("Status Code:", response.status_code)

        if response.status_code != 200:
            print("Skipped:", region, category_id)
            continue

        data = response.json()

        for video in data.get("items", []):
            video_id = video.get("id")

            if not video_id:
                continue

            if video_id in existing_ids:
                continue

            if video_id in new_records:
                continue

            snippet = video.get("snippet", {})
            statistics = video.get("statistics", {})

            new_records[video_id] = {
                "video_id": video_id,
                "title": snippet.get("title"),
                "channel_id": snippet.get("channelId"),
                "channel_title": snippet.get("channelTitle"),
                "category_id": snippet.get("categoryId"),
                "published_at": snippet.get("publishedAt"),
                "region_code": region,
                "collected_at": collected_at,
                "view_count": statistics.get("viewCount"),
                "like_count": statistics.get("likeCount"),
                "comment_count": statistics.get("commentCount"),
                "is_trending": 1,
                "trending_rank": None,
                "source_category_id": category_id,
            }

            if len(new_records) >= TARGET_NEW_VIDEOS:
                break

    if len(new_records) >= TARGET_NEW_VIDEOS:
        break


records = list(new_records.values())

with open(
    OUTPUT_PATH,
    "w",
    encoding="utf-8",
) as file:
    json.dump(
        records,
        file,
        ensure_ascii=False,
        indent=2,
    )


print()
print("=" * 60)
print("TRENDING EXPANSION COMPLETED")
print("Existing unique videos:", len(existing_ids))
print("New trending videos:", len(records))
print(
    "Expected unique total:",
    len(existing_ids) + len(records),
)
print("Saved to:", OUTPUT_PATH)
print("=" * 60)