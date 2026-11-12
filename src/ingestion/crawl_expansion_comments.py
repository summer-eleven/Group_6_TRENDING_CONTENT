"""High-Speed Expansion Comments Crawler for JP RQ2 (HT-03 Scale-Up).

Samples 1,000 diverse videos directly from the 32,000 Tier 2 expansion pool,
fetches top relevance comments (up to 25 per video, 1 API call per video),
and writes raw JSON under data/raw/comments/JP/.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")
API_BASE = "https://www.googleapis.com/youtube/v3"

EXPANSION_DIR = Path("data/raw/expansion_jp")
RAW_COMMENTS_DIR = Path("data/raw/comments")
OUTPUT_DIR = Path("data/raw/comments/JP")


def get_already_crawled_vids():
    known = set()
    for f in RAW_COMMENTS_DIR.glob("**/*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            cmts = data if isinstance(data, list) else data.get("comments", data.get("items", []))
            for c in cmts:
                if "video_id" in c:
                    known.add(c["video_id"])
        except Exception:
            pass
    return known


def load_expansion_sample(sample_size=1000, random_state=42):
    already_crawled = get_already_crawled_vids()
    print(f"Excluding {len(already_crawled)} already crawled video IDs...")

    records = []
    for f in sorted(EXPANSION_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            records.extend(data.get("items", []))
        except Exception as e:
            print(f"Warning loading {f}: {e}")

    df = pd.DataFrame(records)
    print(f"Total expansion records available: {len(df):,}")

    # Filter valid
    valid = df[
        df["video_id"].notna()
        & (df["video_id"].str.len() == 11)
        & (~df["video_id"].isin(already_crawled))
        & (df["t0_view_count"] > 0)
    ].copy()

    print(f"Candidate pool after filtering: {len(valid):,} videos across {valid['category_id'].nunique()} categories.")

    # Stratified proportional sampling
    cat_counts = valid["category_id"].value_counts()
    major_cats = cat_counts[cat_counts >= 10].index.tolist()
    filtered = valid[valid["category_id"].isin(major_cats)]

    sample_df = (
        filtered.groupby("category_id", group_keys=False)
        .apply(lambda x: x.sample(n=max(2, int(round(len(x) / len(filtered) * sample_size))), random_state=random_state))
    )

    if len(sample_df) > sample_size:
        sample_df = sample_df.sample(n=sample_size, random_state=random_state)
    elif len(sample_df) < sample_size:
        remaining = valid[~valid["video_id"].isin(sample_df["video_id"])]
        if not remaining.empty:
            sample_df = pd.concat([sample_df, remaining.sample(n=sample_size - len(sample_df), random_state=random_state)])

    return sample_df.reset_index(drop=True)


def fetch_comments_single_call(session, video_id, max_comments=25, order="relevance", region="JP"):
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": min(100, max_comments),
        "order": order,
        "textFormat": "plainText",
        "key": API_KEY,
    }

    try:
        res = session.get(f"{API_BASE}/commentThreads", params=params, timeout=20)
        if res.status_code == 403:
            err_data = res.json()
            reason = err_data.get("error", {}).get("errors", [{}])[0].get("reason", "")
            if reason == "commentsDisabled":
                return [], "COMMENTS_DISABLED"
            return [], f"HTTP_403_{reason}"
        if res.status_code == 404:
            return [], "VIDEO_NOT_FOUND"
        if res.status_code != 200:
            return [], f"HTTP_{res.status_code}"

        data = res.json()
    except Exception as e:
        return [], f"ERROR_{str(e)[:40]}"

    items = data.get("items", [])
    if not items:
        return [], "EMPTY"

    now_str = datetime.now(timezone.utc).isoformat()
    comments = []
    for it in items:
        top = it.get("snippet", {}).get("topLevelComment", {})
        snip = top.get("snippet", {})
        comments.append({
            "comment_id": top.get("id"),
            "video_id": video_id,
            "region_code": region,
            "comment_text": snip.get("textDisplay", ""),
            "comment_like_count": snip.get("likeCount", 0),
            "comment_published_at": snip.get("publishedAt"),
            "collected_at": now_str,
            "order_policy": order,
        })

    return comments, "OK"


def crawl_expansion(sample_size=1000, max_comments=25):
    if not API_KEY:
        raise ValueError("YOUTUBE_API_KEY missing from .env")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sample_df = load_expansion_sample(sample_size=sample_size)
    print(f"\nSampled {len(sample_df)} videos:")
    print(sample_df["category_id"].value_counts().to_string())

    session = requests.Session()
    all_comments = []
    video_summary = []
    start_time = time.time()

    print("\n" + "=" * 65)
    print(f"STARTING HIGH-SPEED EXPANSION COMMENTS CRAWL (N={len(sample_df)} videos)...")
    print("=" * 65)

    for idx, row in enumerate(sample_df.itertuples(), start=1):
        vid = row.video_id
        cat = getattr(row, "category_id", "NA")

        comments, status = fetch_comments_single_call(session, vid, max_comments=max_comments)
        video_summary.append({
            "video_id": vid,
            "category_id": cat,
            "status": status,
            "comments_count": len(comments),
        })

        if status == "OK":
            all_comments.extend(comments)

        if idx % 50 == 0 or idx == len(sample_df):
            elapsed = time.time() - start_time
            print(f"[{idx:>4}/{len(sample_df)}] Crawled {len(all_comments):>5} comments | Elapsed: {elapsed:.1f}s | Current: {vid} ({status})")

        time.sleep(0.04)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = OUTPUT_DIR / f"comments_JP_expansion_1000_{timestamp}.json"

    payload = {
        "region": "JP",
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "sampling_policy": {
            "order": "relevance",
            "max_comments_per_video": max_comments,
            "target_videos": sample_size,
            "actual_videos_sampled": len(sample_df),
            "source": "expansion_pool_32k",
        },
        "video_status_summary": video_summary,
        "total_comments": len(all_comments),
        "comments": all_comments,
    }

    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    df_stat = pd.DataFrame(video_summary)
    ok_count = (df_stat["status"] == "OK").sum()
    disabled_count = (df_stat["status"] == "COMMENTS_DISABLED").sum()
    empty_count = (df_stat["status"] == "EMPTY").sum()

    print("\n" + "=" * 65)
    print("EXPANSION CRAWL COMPLETE!")
    print(f"Output File:     {out_file}")
    print(f"Total Comments:  {len(all_comments):,}")
    print(f"Active Videos:   {ok_count}/{len(sample_df)} ({ok_count/len(sample_df)*100:.1f}%)")
    print(f"Comments Disabled: {disabled_count} | Empty: {empty_count}")
    print(f"Total Time:      {time.time() - start_time:.1f} seconds")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Expansion comments crawler")
    parser.add_argument("--sample-size", type=int, default=1000)
    parser.add_argument("--max-comments", type=int, default=25)
    args = parser.parse_args()

    crawl_expansion(sample_size=args.sample_size, max_comments=args.max_comments)
