import json
import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

SEARCH_QUERIES = [
    "music",
    "gaming",
    "technology",
    "movies",
    "sports",
    "education",
    "science",
    "travel",
    "food",
    "podcast",
    "news",
    "entertainment",
    "programming",
    "artificial intelligence",
    "smartphone",
    "football",
    "basketball",
    "cooking",
    "documentary",
    "history",
    "fitness",
    "comedy",
    "animation",
    "business",
    "finance",
]

REGION = "VN"
TARGET_CONTROL_VIDEOS = 600

with open(
    "data/raw/youtube_popular_raw.json",
    "r",
    encoding="utf-8",
) as file:
    popular_records = json.load(file)

popular_ids = {
    record["video_id"]
    for record in popular_records
}

candidate_ids = []

for query in SEARCH_QUERIES:
    if len(candidate_ids) >= TARGET_CONTROL_VIDEOS:
        break

    print("Searching:", query)

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "regionCode": REGION,
        "maxResults": 50,
        "key": API_KEY,
    }

    response = requests.get(
        SEARCH_URL,
        params=params,
        timeout=30,
    )

    print("Status Code:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        continue

    data = response.json()

    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId")

        if not video_id:
            continue

        if video_id in popular_ids:
            continue

        if video_id in candidate_ids:
            continue

        candidate_ids.append(video_id)

        if len(candidate_ids) >= TARGET_CONTROL_VIDEOS:
            break

candidate_ids = candidate_ids[:TARGET_CONTROL_VIDEOS]

records = []

for start in range(0, len(candidate_ids), 50):
    batch_ids = candidate_ids[start:start + 50]

    params = {
        "part": "snippet,statistics",
        "id": ",".join(batch_ids),
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

    collected_at = datetime.now(timezone.utc).isoformat()

    for video in data.get("items", []):
        snippet = video.get("snippet", {})
        statistics = video.get("statistics", {})

        record = {
            "video_id": video.get("id"),
            "title": snippet.get("title"),
            "channel_id": snippet.get("channelId"),
            "channel_title": snippet.get("channelTitle"),
            "category_id": snippet.get("categoryId"),
            "published_at": snippet.get("publishedAt"),
            "region_code": REGION,
            "collected_at": collected_at,
            "view_count": statistics.get("viewCount"),
            "like_count": statistics.get("likeCount"),
            "comment_count": statistics.get("commentCount"),
            "is_trending": 0,
            "trending_rank": None,
        }

        records.append(record)

output_path = "data/raw/youtube_control_raw.json"

with open(output_path, "w", encoding="utf-8") as file:
    json.dump(
        records,
        file,
        ensure_ascii=False,
        indent=2,
    )

print()
print("=" * 60)
print("CONTROL COLLECTION COMPLETED")
print("Control videos:", len(records))
print("Saved to:", output_path)
print("=" * 60)