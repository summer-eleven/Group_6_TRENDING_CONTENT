"""
youtube_jp_expansion_crawler.py

Thu thap toi da video JP (trending + control) de mo rong dataset.
Duoc thiet ke de chay moi 2 ngay, toi da hoa quota YouTube Data API v3.

Chi phi quota uoc tinh:
  - videos.list (trending, 4 pages x 50): 4 units
  - search.list (30 control queries): 30 x 100 = 3000 units
  - videos.list (fetch details batch 50): ~30 units

Chay:
  python -m src.ingestion.youtube_jp_expansion_crawler

Output:
  data/raw/youtube_jp_trending_expansion_raw.json
  data/raw/youtube_jp_control_expansion_raw.json
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")

if not API_KEY:
    raise ValueError("YOUTUBE_API_KEY was not found. Check your .env file.")

REGION = "JP"
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

TRENDING_OUTPUT = "data/raw/youtube_jp_trending_expansion_raw.json"
CONTROL_OUTPUT = "data/raw/youtube_jp_control_expansion_raw.json"

BASE_DATASET = "data/processed/youtube_dataset_2000_clean.csv"

# ------------------------------------------------------------------
# Search queries tieng Nhat + tieng Anh pho bien tai JP
# Moi query ton 100 quota units, toi da hoa so luong video moi
# ------------------------------------------------------------------
SEARCH_QUERIES = [
    # Tieng Nhat - chu de pho bien
    "音楽",
    "ゲーム",
    "料理",
    "ニュース",
    "アニメ",
    "映画",
    "スポーツ",
    "教育",
    "旅行",
    "バラエティ",
    "歌ってみた",
    "踊ってみた",
    "VLOG",
    "コメディ",
    "テクノロジー",
    "フィットネス",
    "ドキュメンタリー",
    "ビジネス",
    "科学",
    "歴史",
    # Tieng Anh - pho bien tai JP
    "music Japan",
    "gaming Japan",
    "Japanese food",
    "Japan travel",
    "anime review",
    "Japan culture",
    "Japanese comedy",
    "Japan news",
    "Japanese music 2026",
    "Japan technology",
]

# ------------------------------------------------------------------
# Doc existing video IDs de tranh trung lap
# ------------------------------------------------------------------
print("=" * 60)
print("LOADING EXISTING DATASET")
print("=" * 60)

existing_ids = set()

if Path(BASE_DATASET).exists():
    base_df = pd.read_csv(
        BASE_DATASET,
        dtype={"video_id": "string"},
        usecols=["video_id"],
    )
    existing_ids.update(
        base_df["video_id"].dropna().astype(str).tolist()
    )
    print("Existing videos in dataset:", len(existing_ids))
else:
    print("WARNING:", BASE_DATASET, "not found — starting fresh.")

for extra_path in [
    "data/raw/youtube_trending_expansion_raw.json",
    "data/raw/youtube_control_expansion_raw.json",
    TRENDING_OUTPUT,
    CONTROL_OUTPUT,
]:
    if Path(extra_path).exists():
        with open(extra_path, "r", encoding="utf-8") as f:
            extra_records = json.load(f)
        extra_ids = {
            r["video_id"]
            for r in extra_records
            if r.get("video_id")
        }
        existing_ids.update(extra_ids)
        print("  +", len(extra_ids), "IDs from", extra_path)

print("Total existing IDs (to skip):", len(existing_ids))
print()

# ==================================================================
# PHASE 1: Trending JP (mostPopular chart, pagination)
# ==================================================================
print("=" * 60)
print("PHASE 1: TRENDING JP VIDEOS")
print("=" * 60)

trending_records = []
trending_ids = set()
page_token = None
page_num = 0
MAX_TRENDING_PAGES = 4

while page_num < MAX_TRENDING_PAGES:
    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": REGION,
        "maxResults": 50,
        "key": API_KEY,
    }
    if page_token:
        params["pageToken"] = page_token

    response = requests.get(VIDEOS_URL, params=params, timeout=30)
    print("  Page", page_num + 1, "— Status:", response.status_code)

    if response.status_code != 200:
        print("  ERROR:", response.text[:300])
        break

    data = response.json()
    collected_at = datetime.now(timezone.utc).isoformat()

    for rank, video in enumerate(
        data.get("items", []),
        start=page_num * 50 + 1,
    ):
        video_id = video.get("id")
        if not video_id or video_id in existing_ids:
            continue

        snippet = video.get("snippet", {})
        statistics = video.get("statistics", {})

        trending_records.append({
            "video_id": video_id,
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
            "is_trending": 1,
            "trending_rank": rank,
        })
        trending_ids.add(video_id)

    page_token = data.get("nextPageToken")
    page_num += 1

    if not page_token:
        print("  No more pages.")
        break

    time.sleep(0.5)

print("  New trending JP videos collected:", len(trending_records))

Path(TRENDING_OUTPUT).parent.mkdir(parents=True, exist_ok=True)
with open(TRENDING_OUTPUT, "w", encoding="utf-8") as f:
    json.dump(trending_records, f, ensure_ascii=False, indent=2)
print("  Saved to:", TRENDING_OUTPUT)
print()

# ==================================================================
# PHASE 2: Control JP (search queries)
# ==================================================================
print("=" * 60)
print("PHASE 2: CONTROL JP VIDEOS (via search)")
print("=" * 60)

skip_ids = existing_ids | trending_ids
candidate_ids = []

for query in SEARCH_QUERIES:
    print("  Searching:", repr(query))

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "regionCode": REGION,
        "relevanceLanguage": "ja",
        "maxResults": 50,
        "key": API_KEY,
    }

    response = requests.get(SEARCH_URL, params=params, timeout=30)
    status = response.status_code
    print("    Status:", status, end="")

    if status != 200:
        print(" — ERROR:", response.text[:200])
        time.sleep(1)
        continue

    data = response.json()
    new_from_query = 0

    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId")

        if not video_id:
            continue
        if video_id in skip_ids:
            continue
        if video_id in candidate_ids:
            continue

        candidate_ids.append(video_id)
        skip_ids.add(video_id)
        new_from_query += 1

    print(" — new:", new_from_query, "(total:", len(candidate_ids), ")")
    time.sleep(0.3)

print("\n  Total control candidates:", len(candidate_ids))
print("  Fetching video details...")

control_records = []
collected_at = datetime.now(timezone.utc).isoformat()

for start in range(0, len(candidate_ids), 50):
    batch = candidate_ids[start:start + 50]
    batch_num = start // 50 + 1
    total_batches = (len(candidate_ids) - 1) // 50 + 1

    params = {
        "part": "snippet,statistics",
        "id": ",".join(batch),
        "key": API_KEY,
    }

    response = requests.get(VIDEOS_URL, params=params, timeout=30)

    if response.status_code != 200:
        print("  Batch", batch_num, "FAILED:", response.text[:200])
        continue

    data = response.json()

    for video in data.get("items", []):
        snippet = video.get("snippet", {})
        statistics = video.get("statistics", {})

        control_records.append({
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
        })

    print(
        "  Batch", batch_num, "/", total_batches,
        "— fetched", len(data.get("items", [])), "videos",
    )
    time.sleep(0.3)

with open(CONTROL_OUTPUT, "w", encoding="utf-8") as f:
    json.dump(control_records, f, ensure_ascii=False, indent=2)
print("  Saved to:", CONTROL_OUTPUT)

# ==================================================================
# SUMMARY
# ==================================================================
print()
print("=" * 60)
print("JP EXPANSION COMPLETED")
print("Existing videos (skipped): ", len(existing_ids))
print("New trending JP:           ", len(trending_records))
print("New control JP:            ", len(control_records))
print("Total new JP videos:       ", len(trending_records) + len(control_records))
print()
print("Next step: run build_youtube_dataset_jp.py to rebuild dataset")
print("=" * 60)
