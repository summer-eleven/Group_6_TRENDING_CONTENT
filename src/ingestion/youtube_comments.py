"""Standardized YouTube Comments Ingestion for RQ2 (HT-03).

Selects representative video samples from youtube_cohort_registry_JP.csv:
  - Stratified across major categories and popularity levels
  - Fetches top comments (relevance or time ordered)
  - Records error states (commentsDisabled, inaccessible, empty)
  - Saves raw JSON under data/raw/comments/<REGION>/ with sampling metadata
"""

import argparse
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
API_BASE = "https://www.googleapis.com/youtube/v3"

REGISTRY_DEFAULT = Path("data/processed/youtube_cohort_registry_JP.csv")
RAW_OUT_DEFAULT = Path("data/raw/comments/JP")


def select_stratified_sample(registry_path: Path, sample_size: int = 50, random_state: int = 42) -> pd.DataFrame:
    """Select balanced sample of videos stratified across categories."""
    if not registry_path.is_file():
        raise FileNotFoundError(f"Registry not found: {registry_path}")

    df = pd.read_csv(registry_path, dtype={"video_id": str, "category_id": str})
    
    # Filter valid videos with comments enabled / positive comment count if available
    valid = df[df["video_id"].notna() & (df["video_id"].str.len() == 11)].copy()
    if "t0_comment_count" in valid.columns:
        # Prefer videos known to have comments, or at least positive views
        has_comments = valid[valid["t0_comment_count"] > 0]
        if len(has_comments) >= sample_size:
            valid = has_comments

    # Stratified sampling by category_id
    cat_counts = valid["category_id"].value_counts()
    major_cats = cat_counts[cat_counts >= 2].index.tolist()
    filtered = valid[valid["category_id"].isin(major_cats)]

    if len(filtered) < sample_size:
        return valid.sample(n=min(len(valid), sample_size), random_state=random_state)

    # Proportional sampling per category
    sample_df = (
        filtered.groupby("category_id", group_keys=False)
        .apply(lambda x: x.sample(n=max(1, int(round(len(x) / len(filtered) * sample_size))), random_state=random_state))
    )

    if len(sample_df) > sample_size:
        sample_df = sample_df.sample(n=sample_size, random_state=random_state)
    elif len(sample_df) < sample_size:
        remaining = valid[~valid["video_id"].isin(sample_df["video_id"])]
        if not remaining.empty:
            add_n = min(sample_size - len(sample_df), len(remaining))
            sample_df = pd.concat([sample_df, remaining.sample(n=add_n, random_state=random_state)])

    return sample_df


def fetch_comments_for_video(session, video_id: str, region_code: str = "JP",
                             max_comments: int = 100, order: str = "relevance") -> tuple[list, str]:
    """Fetch top comments for a single video. Returns (comments_list, status)."""
    comments = []
    page_token = None
    status = "OK"

    while len(comments) < max_comments:
        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(100, max_comments - len(comments)),
            "order": order,
            "textFormat": "plainText",
            "key": API_KEY,
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            res = session.get(f"{API_BASE}/commentThreads", params=params, timeout=30)
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
            return comments, f"ERROR_{str(e)[:50]}"

        items = data.get("items", [])
        if not items:
            if not comments:
                status = "EMPTY"
            break

        now_str = datetime.now(timezone.utc).isoformat()
        for it in items:
            top = it.get("snippet", {}).get("topLevelComment", {})
            snip = top.get("snippet", {})
            comments.append({
                "comment_id": top.get("id"),
                "video_id": video_id,
                "region_code": region_code,
                "comment_text": snip.get("textDisplay", ""),
                "comment_like_count": snip.get("likeCount", 0),
                "comment_published_at": snip.get("publishedAt"),
                "collected_at": now_str,
                "order_policy": order,
            })

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return comments, status


def crawl_comments(registry_path: Path = REGISTRY_DEFAULT, out_dir: Path = RAW_OUT_DEFAULT,
                   sample_size: int = 50, max_comments_per_video: int = 100,
                   order: str = "relevance", region: str = "JP"):
    if not API_KEY:
        raise ValueError("YOUTUBE_API_KEY missing from .env")

    out_dir.mkdir(parents=True, exist_ok=True)
    sample_vids = select_stratified_sample(registry_path, sample_size=sample_size)
    print(f"Selected {len(sample_vids)} stratified videos from {registry_path.name}")
    print(f"Category distribution:\n{sample_vids['category_id'].value_counts().to_string()}\n")

    session = requests.Session()
    all_comments = []
    video_summary = []

    print("=" * 65)
    print(f"Starting comment acquisition (order={order}, max {max_comments_per_video}/video)...")
    print("=" * 65)

    for idx, row in enumerate(sample_vids.itertuples(), start=1):
        vid = row.video_id
        cat = getattr(row, "category_id", "NA")
        print(f"[{idx}/{len(sample_vids)}] Video {vid} (cat={cat})... ", end="", flush=True)

        comments, status = fetch_comments_for_video(
            session=session,
            video_id=vid,
            region_code=region,
            max_comments=max_comments_per_video,
            order=order,
        )

        video_summary.append({
            "video_id": vid,
            "category_id": cat,
            "status": status,
            "comments_count": len(comments),
        })

        if status == "OK":
            all_comments.extend(comments)
            print(f"OK ({len(comments)} comments)")
        else:
            print(f"Status: {status}")

        time.sleep(0.2)

    # Save raw batch
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"comments_{region}_{timestamp}.json"

    payload = {
        "region": region,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "sampling_policy": {
            "order": order,
            "max_comments_per_video": max_comments_per_video,
            "target_videos": sample_size,
            "actual_videos_sampled": len(sample_vids),
            "source_registry": str(registry_path),
        },
        "video_status_summary": video_summary,
        "total_comments": len(all_comments),
        "comments": all_comments,
    }

    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Statistics
    df_stat = pd.DataFrame(video_summary)
    disabled_count = (df_stat["status"] == "COMMENTS_DISABLED").sum()
    empty_count = (df_stat["status"] == "EMPTY").sum()
    ok_count = (df_stat["status"] == "OK").sum()

    print("\n" + "=" * 65)
    print(f"RAW COMMENTS ACQUISITION COMPLETE")
    print(f"Saved file: {out_file}")
    print(f"Total comments harvested: {len(all_comments):,}")
    print(f"Videos with active comments: {ok_count}/{len(sample_vids)} ({ok_count/len(sample_vids)*100:.1f}%)")
    print(f"Comments Disabled: {disabled_count} | Empty: {empty_count}")
    print("=" * 65)
    return out_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standardized YouTube comments crawler for JP RQ2")
    parser.add_argument("--registry-path", type=Path, default=REGISTRY_DEFAULT)
    parser.add_argument("--out-dir", type=Path, default=RAW_OUT_DEFAULT)
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--max-comments-per-video", type=int, default=100)
    parser.add_argument("--order", choices=["relevance", "time"], default="relevance")
    parser.add_argument("--region", default="JP")
    args = parser.parse_args()

    crawl_comments(
        registry_path=args.registry_path,
        out_dir=args.out_dir,
        sample_size=args.sample_size,
        max_comments_per_video=args.max_comments_per_video,
        order=args.order,
        region=args.region,
    )