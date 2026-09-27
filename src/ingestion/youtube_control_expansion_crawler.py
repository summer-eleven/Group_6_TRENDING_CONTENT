import json
import os
from datetime import datetime, timezone

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")

BASE_DATASET = "data/processed/youtube_dataset_1000_clean.csv"
TRENDING_EXPANSION = "data/raw/youtube_trending_expansion_raw.json"
OUTPUT_PATH = "data/raw/youtube_control_expansion_raw.json"

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

TARGET_NEW_VIDEOS = 400
REGION = "VN"

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
    "photography",
    "design",
    "culture",
    "language learning",
    "productivity",
]

base_df = pd.read_csv(
    BASE_DATASET,
    dtype={"video_id": "string"},
)

existing_ids = set(
    base_df["video_id"]
    .dropna()
    .astype(str)
)

with open(
    TRENDING_EXPANSION,
    "r",
    encoding="utf-8",
) as file:
    trending_expansion = json.load(file)

existing_ids.update(
    record["video_id"]
    for record in trending_expansion
    if record.get("video_id")
)

popular_params = {
    "part": "snippet",
    "chart": "mostPopular",
    "regionCode": REGION,
    "maxResults": 50,
    "key": API_KEY,
}

popular_response = requests.get(
    VIDEOS_URL,
    params=popular_params,
    timeout=30,
)

current_popular_ids = set()

if popular_response.status_code == 200:
    popular_data = popular_response.json()

    current_popular_ids = {
        video["id"]
        for video in popular_data.get("items", [])
    }

candidate_ids = []

for query in SEARCH_QUERIES:
    if len(candidate_ids) >= TARGET_NEW_VIDEOS:
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

        if video_id in existing_ids:
            continue

        if video_id in current_popular_ids:
            continue

        if video_id in candidate_ids:
            continue

        candidate_ids.append(video_id)

        if len(candidate_ids) >= TARGET_NEW_VIDEOS:
            break

records = []

for start in range(0, len(candidate_ids), 50):
    batch = candidate_ids[start:start + 50]

    params = {
        "part": "snippet,statistics",
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

    collected_at = datetime.now(timezone.utc).isoformat()

    for video in data.get("items", []):
        snippet = video.get("snippet", {})
        statistics = video.get("statistics", {})

        records.append(
            {
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
        )

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
print("CONTROL EXPANSION COMPLETED")
print("Existing unique videos:", len(existing_ids))
print("New control videos:", len(records))
print(
    "Expected unique total:",
    len(existing_ids) + len(records),
)
print("Saved to:", OUTPUT_PATH)
print("=" * 60)