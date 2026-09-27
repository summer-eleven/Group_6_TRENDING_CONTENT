import os
import json
import requests
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("YOUTUBE_API_KEY")

url = "https://www.googleapis.com/youtube/v3/videos"

params = {
    "part": "snippet,statistics",
    "chart": "mostPopular",
    "regionCode": "VN",
    "maxResults": 50,
    "key": api_key,
}

response = requests.get(url, params=params, timeout=30)

print("Status Code:", response.status_code)

if response.status_code != 200:
    print(response.text)
    raise SystemExit

data = response.json()

collected_at = datetime.now(timezone.utc).isoformat()

records = []

for rank, video in enumerate(data.get("items", []), start=1):
    snippet = video.get("snippet", {})
    statistics = video.get("statistics", {})

    record = {
        "video_id": video.get("id"),
        "title": snippet.get("title"),
        "channel_id": snippet.get("channelId"),
        "channel_title": snippet.get("channelTitle"),
        "category_id": snippet.get("categoryId"),
        "published_at": snippet.get("publishedAt"),
        "region_code": "VN",
        "collected_at": collected_at,
        "view_count": statistics.get("viewCount"),
        "like_count": statistics.get("likeCount"),
        "comment_count": statistics.get("commentCount"),
        "is_trending": 1,
        "trending_rank": rank,
    }

    records.append(record)

print("Records collected:", len(records))

for record in records[:3]:
    print("-" * 60)
    print(record)

output_path = "data/raw/youtube_trending_raw.json"

with open(output_path, "w", encoding="utf-8") as file:
    json.dump(records, file, ensure_ascii=False, indent=2)

print("-" * 60)
print("Raw JSON saved to:", output_path)







