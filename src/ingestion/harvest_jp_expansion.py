"""High-speed JP Video Expansion Harvester.

Collects unique JP videos from the 1,199 seed channels to scale up towards 35,000 unique IDs.
Uses efficient batching:
  - channels.list in batches of 50 to resolve upload playlist IDs (1 unit per 50 channels)
  - playlistItems.list with maxResults=50 (1 unit per 50 videos)
  - videos.list in batches of 50 to fetch metadata (1 unit per 50 videos)
  - Filters out all existing video_ids across master, registry, and chart monitor
"""

import argparse
import glob
import json
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
API_BASE = "https://www.googleapis.com/youtube/v3"
MASTER_PATH = Path("data/processed/youtube_dataset_2000_clean.csv")
REGISTRY_PATH = Path("data/processed/youtube_cohort_registry_JP.csv")
RAW_OUT_DIR = Path("data/raw/expansion_jp")


def collect_existing_ids():
    existing = set()
    if MASTER_PATH.is_file():
        df = pd.read_csv(MASTER_PATH, usecols=["video_id"], dtype=str)
        existing.update(df["video_id"].dropna())

    if REGISTRY_PATH.is_file():
        df = pd.read_csv(REGISTRY_PATH, usecols=["video_id"], dtype=str)
        existing.update(df["video_id"].dropna())

    for f in glob.glob("data/raw/chart_monitor/JP/*.json"):
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8-sig"))
            for en in d.get("entries", []):
                if en.get("video_id"):
                    existing.add(str(en["video_id"]))
        except Exception:
            pass

    for f in glob.glob("data/raw/expansion_jp/*.json"):
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8-sig"))
            for it in d.get("items", []):
                if it.get("video_id"):
                    existing.add(str(it["video_id"]))
        except Exception:
            pass

    return existing


def get_upload_playlists(session, channel_ids):
    playlists = {}
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i+50]
        params = {
            "part": "contentDetails",
            "id": ",".join(batch),
            "maxResults": 50,
            "key": API_KEY,
        }
        res = session.get(f"{API_BASE}/channels", params=params, timeout=30)
        if res.status_code != 200:
            continue
        data = res.json()
        for item in data.get("items", []):
            cid = item.get("id")
            uploads = item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
            if cid and uploads:
                playlists[cid] = uploads
    return playlists


def harvest(target_new=3000, max_per_channel=30, lookback_days=180):
    if not API_KEY:
        raise ValueError("YOUTUBE_API_KEY missing from .env")

    session = requests.Session()
    existing_ids = collect_existing_ids()
    print(f"Known video IDs across all sources: {len(existing_ids):,}")

    master = pd.read_csv(MASTER_PATH)
    jp_channels = master[master["region_code"] == "JP"]["channel_id"].dropna().unique().tolist()
    print(f"Available JP seed channels: {len(jp_channels):,}")

    print("Resolving uploads playlist IDs for channels...")
    playlists = get_upload_playlists(session, jp_channels)
    print(f"Resolved {len(playlists):,} upload playlists.")

    collected_candidates = []
    seen_in_run = set()
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    print(f"Targeting: {target_new:,} new videos (max {max_per_channel}/channel, lookback {lookback_days} days)...")

    for idx, (cid, pid) in enumerate(playlists.items(), 1):
        if len(collected_candidates) >= target_new:
            break

        page_token = None
        per_ch_count = 0

        for page in range(2):
            if per_ch_count >= max_per_channel or len(collected_candidates) >= target_new:
                break

            params = {
                "part": "contentDetails",
                "playlistId": pid,
                "maxResults": 50,
                "key": API_KEY,
            }
            if page_token:
                params["pageToken"] = page_token

            try:
                r = session.get(f"{API_BASE}/playlistItems", params=params, timeout=30)
                if r.status_code == 404:
                    break
                if r.status_code != 200:
                    continue
                data = r.json()
            except Exception:
                break

            items = data.get("items", [])
            if not items:
                break

            for it in items:
                cd = it.get("contentDetails", {})
                vid = cd.get("videoId")
                pub = cd.get("videoPublishedAt")
                if not vid or vid in existing_ids or vid in seen_in_run:
                    continue

                if pub:
                    try:
                        p_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                        if p_dt < cutoff:
                            continue
                    except Exception:
                        pass

                seen_in_run.add(vid)
                collected_candidates.append({
                    "video_id": vid,
                    "channel_id": cid,
                    "published_at": pub,
                })
                per_ch_count += 1
                if per_ch_count >= max_per_channel or len(collected_candidates) >= target_new:
                    break

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        if idx % 100 == 0 or len(collected_candidates) >= target_new:
            print(f"  Processed {idx}/{len(playlists)} channels | Found {len(collected_candidates):,}/{target_new:,} unique videos...")

    print(f"\nDiscovered {len(collected_candidates):,} candidates. Fetching metadata via videos.list in batches of 50...")

    final_records = []
    for i in range(0, len(collected_candidates), 50):
        batch = collected_candidates[i:i+50]
        vids = [b["video_id"] for b in batch]
        params = {
            "part": "snippet,statistics",
            "id": ",".join(vids),
            "maxResults": 50,
            "key": API_KEY,
        }
        res = session.get(f"{API_BASE}/videos", params=params, timeout=30)
        if res.status_code != 200:
            continue
        data = res.json()
        now_str = datetime.now(timezone.utc).isoformat()

        for it in data.get("items", []):
            vid = it.get("id")
            snip = it.get("snippet", {})
            stat = it.get("statistics", {})

            rec = {
                "video_id": vid,
                "region_code": "JP",
                "batch_id": "EXPANSION_JP",
                "title": snip.get("title"),
                "channel_id": snip.get("channelId"),
                "channel_title": snip.get("channelTitle"),
                "category_id": snip.get("categoryId"),
                "published_at": snip.get("publishedAt"),
                "first_seen_at": now_str,
                "discovery_source": "channel_uploads_expansion",
                "seed_region": "JP",
                "region_availability": "JP",
                "t0_collected_at": now_str,
                "t0_view_count": int(stat.get("viewCount", 0)) if stat.get("viewCount") else 0,
                "t0_like_count": int(stat.get("likeCount", 0)) if stat.get("likeCount") else 0,
                "t0_comment_count": int(stat.get("commentCount", 0)) if stat.get("commentCount") else 0,
                "t24_collected_at": None,
                "t24_view_count": None,
                "t24_like_count": None,
                "t24_comment_count": None,
                "hours_elapsed": None,
                "view_delta_24h": None,
                "views_per_hour_avg_24h": None,
                "chart_label_status": None,
            }
            final_records.append(rec)

    # Save to Raw JSON
    RAW_OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_OUT_DIR / f"jp_expansion_{stamp}_{len(final_records)}.json"
    raw_path.write_text(json.dumps({"count": len(final_records), "items": final_records}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved raw JSON: {raw_path}")

    # Append to Registry JP
    if REGISTRY_PATH.is_file():
        old_reg = pd.read_csv(REGISTRY_PATH)
    else:
        old_reg = pd.DataFrame()

    new_df = pd.DataFrame(final_records)
    combined = pd.concat([old_reg, new_df], ignore_index=True).drop_duplicates(subset=["video_id"])
    combined.to_csv(REGISTRY_PATH, index=False, encoding="utf-8")

    print("\n================ HARVEST COMPLETED ================")
    print(f"New videos added in this run: {len(final_records):,}")
    print(f"New total videos in youtube_cohort_registry_JP.csv: {len(combined):,}")
    print(f"Total Unique JP Videos across all sources: {len(existing_ids) + len(final_records):,}")
    print("====================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-new", type=int, default=3000)
    parser.add_argument("--max-per-channel", type=int, default=30)
    parser.add_argument("--lookback-days", type=int, default=180)
    args = parser.parse_args()

    harvest(target_new=args.target_new, max_per_channel=args.max_per_channel, lookback_days=args.lookback_days)