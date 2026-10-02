import json
import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")

REGIONS = ["US"]

API_URL = "https://www.googleapis.com/youtube/v3/videos"

all_records = []

for region in REGIONS:
    print("Collecting region:", region)
    page_token = None
    rank = 0

    while True:
        params = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": region,
            "maxResults": 50,
            "key": API_KEY,
        }
        if page_token:
            params["pageToken"] = page_token

        response = requests.get(API_URL, params=params, timeout=30)
        print("Status Code:", response.status_code)
        if response.status_code != 200:
            print(response.text)
            break

        data = response.json()
        collected_at = datetime.now(timezone.utc).isoformat()

        for video in data.get("items", []):
            rank += 1
            snippet = video.get("snippet", {})
            statistics = video.get("statistics", {})
            all_records.append({
                "video_id": video.get("id"),
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
                "trending_rank": rank,
            })

        page_token = data.get("nextPageToken")
        if not page_token:
            break

unique_records = {}

for record in all_records:
    video_id = record["video_id"]
    
    if video_id not in unique_records:
        unique_records[video_id] = record

records = list(unique_records.values())

output_path = "data/raw/youtube_popular_raw.json"

with open(output_path, "w", encoding="utf-8") as file:
    json.dump(
        records,
        file,
        ensure_ascii=False,
        indent=2
    )

print()
print("=" * 60)
print("COLLECTION COMPLETED")
print("Raw records:", len(all_records))
print("Unique videos:", len(records))
print("Saved to:", output_path)
print("=" * 60)