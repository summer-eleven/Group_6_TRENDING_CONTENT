import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


load_dotenv()

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

DEFAULT_MASTER_PATH = Path(
    "data/processed/youtube_dataset_2000_clean.csv"
)
DEFAULT_LOG_PATH = Path(
    "data/processed/unique_video_refresh_log.csv"
)
DEFAULT_RAW_DIR = Path(
    "data/raw/unique_refresh"
)

# Broad discovery terms. The goal is to discover recent videos, not to label
# them as trending. Trending/viral validation happens later in the pipeline.
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
    "news",
    "entertainment",
    "podcast",
    "artificial intelligence",
]

CORE_COLUMNS = [
    "video_id",
    "title",
    "channel_id",
    "channel_title",
    "category_id",
    "published_at",
    "upload_hour_utc",
    "region_code",
    "collected_at",
    "view_count",
    "like_count",
    "comment_count",
    "is_trending",
    "trending_rank",
    "video_url",
]

DISCOVERY_COLUMNS = [
    "first_seen_at",
    "discovery_batch_id",
    "discovery_source",
    "discovery_query",
    "youtube_charted_at_discovery",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Discover recent YouTube videos, remove duplicate video_id values, "
            "and append only genuinely new videos to the project master dataset."
        )
    )

    parser.add_argument(
        "--region",
        required=True,
        help="YouTube region code, for example: VN, US, JP",
    )
    parser.add_argument(
        "--target-new",
        type=int,
        default=200,
        help="Maximum number of new unique videos to add (default: 200)",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=7,
        help=(
            "Search videos published within this recent window. "
            "A 7-day window is safe for a refresh every 2-3 days."
        ),
    )
    parser.add_argument(
        "--pages-per-query",
        type=int,
        default=1,
        help=(
            "Number of YouTube search pages per query. Each page can contain "
            "up to 50 videos and search.list consumes significant API quota."
        ),
    )
    parser.add_argument(
        "--master-path",
        type=Path,
        default=DEFAULT_MASTER_PATH,
        help="Current master dataset used by the hourly snapshot crawler.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Collect and report candidates without modifying project files.",
    )

    args = parser.parse_args()

    if args.target_new <= 0:
        parser.error("--target-new must be greater than 0")
    if args.lookback_days <= 0:
        parser.error("--lookback-days must be greater than 0")
    if not 1 <= args.pages_per_query <= 3:
        parser.error("--pages-per-query must be between 1 and 3")

    args.region = args.region.upper()
    return args


def request_json(url, params, label):
    response = requests.get(
        url,
        params=params,
        timeout=30,
    )

    print(f"{label} status:", response.status_code)

    if response.status_code != 200:
        raise RuntimeError(
            f"YouTube API error during {label}: {response.text}"
        )

    return response.json()


def load_master_dataset(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Master dataset was not found: {path}"
        )

    df = pd.read_csv(
        path,
        dtype={
            "video_id": "string",
            "region_code": "string",
            "category_id": "string",
        },
    )

    missing = [
        column
        for column in CORE_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Master dataset is missing required columns: "
            + ", ".join(missing)
        )

    return df


def collect_current_chart(api_key, region):
    """Return the current API mostPopular IDs and their rank.

    This is stored only as an external YouTube chart signal. It is not treated
    as universal/official Trending ground truth.
    """
    data = request_json(
        VIDEOS_URL,
        {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": region,
            "maxResults": 50,
            "key": api_key,
        },
        label=f"mostPopular {region}",
    )

    return {
        video["id"]: rank
        for rank, video in enumerate(
            data.get("items", []),
            start=1,
        )
        if video.get("id")
    }


def discover_new_ids(
    api_key,
    region,
    existing_ids,
    target_new,
    lookback_days,
    pages_per_query,
):
    published_after = (
        datetime.now(timezone.utc)
        - timedelta(days=lookback_days)
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    candidate_ids = []
    candidate_set = set()
    discovery_query_by_id = {}
    search_requests = 0
    queries_run = 0

    for query in SEARCH_QUERIES:
        if len(candidate_ids) >= target_new:
            break

        queries_run += 1
        page_token = None

        for page_number in range(1, pages_per_query + 1):
            params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "regionCode": region,
                "publishedAfter": published_after,
                "order": "viewCount",
                "safeSearch": "moderate",
                "maxResults": 50,
                "key": api_key,
            }

            if page_token:
                params["pageToken"] = page_token

            print(
                f"Searching {region}: '{query}' "
                f"page {page_number}/{pages_per_query}"
            )

            data = request_json(
                SEARCH_URL,
                params,
                label="search.list",
            )
            search_requests += 1

            for item in data.get("items", []):
                video_id = item.get("id", {}).get("videoId")

                if not video_id:
                    continue
                if video_id in existing_ids:
                    continue
                if video_id in candidate_set:
                    continue

                candidate_set.add(video_id)
                candidate_ids.append(video_id)
                discovery_query_by_id[video_id] = query

                if len(candidate_ids) >= target_new:
                    break

            if len(candidate_ids) >= target_new:
                break

            page_token = data.get("nextPageToken")
            if not page_token:
                break

    return {
        "candidate_ids": candidate_ids,
        "discovery_query_by_id": discovery_query_by_id,
        "queries_run": queries_run,
        "search_requests": search_requests,
        "published_after": published_after,
    }


def fetch_video_details(api_key, video_ids):
    records = []
    detail_requests = 0

    for start in range(0, len(video_ids), 50):
        batch = video_ids[start:start + 50]

        data = request_json(
            VIDEOS_URL,
            {
                "part": "snippet,statistics",
                "id": ",".join(batch),
                "key": api_key,
            },
            label="videos.list details",
        )
        detail_requests += 1

        for video in data.get("items", []):
            records.append(video)

    return records, detail_requests


def build_new_rows(
    videos,
    region,
    collected_at,
    batch_id,
    chart_rank_by_id,
    discovery_query_by_id,
):
    rows = []

    for video in videos:
        video_id = video.get("id")
        if not video_id:
            continue

        snippet = video.get("snippet", {})
        statistics = video.get("statistics", {})
        published_at = snippet.get("publishedAt")

        published_timestamp = pd.to_datetime(
            published_at,
            errors="coerce",
            utc=True,
        )

        upload_hour_utc = (
            int(published_timestamp.hour)
            if not pd.isna(published_timestamp)
            else pd.NA
        )

        chart_rank = chart_rank_by_id.get(video_id)

        rows.append(
            {
                "video_id": video_id,
                "title": snippet.get("title"),
                "channel_id": snippet.get("channelId"),
                "channel_title": snippet.get("channelTitle"),
                "category_id": snippet.get("categoryId"),
                "published_at": published_at,
                "upload_hour_utc": upload_hour_utc,
                "region_code": region,
                "collected_at": collected_at,
                "view_count": statistics.get("viewCount"),
                "like_count": statistics.get("likeCount"),
                "comment_count": statistics.get("commentCount"),
                # Kept for backward compatibility with the current project.
                # In reports this means API mostPopular presence, not universal
                # YouTube Trending ground truth.
                "is_trending": 1 if chart_rank is not None else 0,
                "trending_rank": chart_rank,
                "video_url": (
                    "https://www.youtube.com/watch?v="
                    + video_id
                ),
                "first_seen_at": collected_at,
                "discovery_batch_id": batch_id,
                "discovery_source": "youtube_search_api",
                "discovery_query": discovery_query_by_id.get(video_id),
                "youtube_charted_at_discovery": (
                    1 if chart_rank is not None else 0
                ),
            }
        )

    return pd.DataFrame(rows)


def append_only_new(master_df, new_df):
    before_unique = master_df["video_id"].nunique()

    for column in DISCOVERY_COLUMNS:
        if column not in master_df.columns:
            master_df[column] = pd.NA

    if new_df.empty:
        return master_df, before_unique, before_unique, 0

    existing_ids = set(
        master_df["video_id"]
        .dropna()
        .astype(str)
    )

    new_df = new_df[
        ~new_df["video_id"].astype(str).isin(existing_ids)
    ].copy()

    new_df = new_df.drop_duplicates(
        subset=["video_id"],
        keep="first",
    )

    combined = pd.concat(
        [master_df, new_df],
        ignore_index=True,
        sort=False,
    )

    # Existing rows always win. This ensures a refresh never overwrites the
    # original cohort metadata for a video that is already tracked.
    combined = combined.drop_duplicates(
        subset=["video_id"],
        keep="first",
    )

    after_unique = combined["video_id"].nunique()
    added = after_unique - before_unique

    preferred_columns = CORE_COLUMNS + DISCOVERY_COLUMNS
    remaining_columns = [
        column
        for column in combined.columns
        if column not in preferred_columns
    ]
    combined = combined[
        preferred_columns + remaining_columns
    ]

    return combined, before_unique, after_unique, added


def write_master_atomically(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    df.to_csv(
        temp_path,
        index=False,
        encoding="utf-8-sig",
    )

    temp_path.replace(path)


def append_refresh_log(log_path, row):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_df = pd.DataFrame([row])

    if log_path.exists():
        existing = pd.read_csv(log_path)
        log_df = pd.concat(
            [existing, log_df],
            ignore_index=True,
        )

    log_df.to_csv(
        log_path,
        index=False,
        encoding="utf-8-sig",
    )


def save_raw_discovery(raw_dir, region, batch_id, rows):
    output_dir = raw_dir / region
    output_dir.mkdir(parents=True, exist_ok=True)

    path = output_dir / f"youtube_unique_refresh_{region}_{batch_id}.json"

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            rows.to_dict(orient="records"),
            file,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    return path


def main():
    args = parse_args()

    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise ValueError(
            "YOUTUBE_API_KEY was not found. Check your .env file."
        )

    master_df = load_master_dataset(args.master_path)
    existing_ids = set(
        master_df["video_id"]
        .dropna()
        .astype(str)
    )

    collected_at_dt = datetime.now(timezone.utc)
    collected_at = collected_at_dt.isoformat()
    batch_id = collected_at_dt.strftime("%Y%m%d_%H%M%S")

    print()
    print("=" * 70)
    print("UNIQUE VIDEO REFRESH STARTED")
    print("Region:", args.region)
    print("Current rows:", len(master_df))
    print("Current unique videos:", len(existing_ids))
    print("Target new videos:", args.target_new)
    print("Lookback days:", args.lookback_days)
    print("Dry run:", args.dry_run)
    print("=" * 70)

    chart_rank_by_id = collect_current_chart(
        api_key,
        args.region,
    )

    discovery = discover_new_ids(
        api_key=api_key,
        region=args.region,
        existing_ids=existing_ids,
        target_new=args.target_new,
        lookback_days=args.lookback_days,
        pages_per_query=args.pages_per_query,
    )

    candidate_ids = discovery["candidate_ids"]

    videos, detail_requests = fetch_video_details(
        api_key,
        candidate_ids,
    )

    new_rows = build_new_rows(
        videos=videos,
        region=args.region,
        collected_at=collected_at,
        batch_id=batch_id,
        chart_rank_by_id=chart_rank_by_id,
        discovery_query_by_id=discovery[
            "discovery_query_by_id"
        ],
    )

    combined, before_unique, after_unique, added = append_only_new(
        master_df,
        new_rows,
    )

    duplicates_skipped = max(
        0,
        len(candidate_ids) - added,
    )

    raw_path = None

    if not args.dry_run:
        write_master_atomically(
            combined,
            args.master_path,
        )

        raw_path = save_raw_discovery(
            DEFAULT_RAW_DIR,
            args.region,
            batch_id,
            new_rows,
        )

        append_refresh_log(
            DEFAULT_LOG_PATH,
            {
                "refreshed_at": collected_at,
                "batch_id": batch_id,
                "region_code": args.region,
                "lookback_days": args.lookback_days,
                "pages_per_query": args.pages_per_query,
                "queries_run": discovery["queries_run"],
                "search_requests": discovery["search_requests"],
                "detail_requests": detail_requests,
                "candidate_ids": len(candidate_ids),
                "resolved_video_details": len(new_rows),
                "duplicates_or_unresolved_skipped": duplicates_skipped,
                "new_unique_videos": added,
                "unique_before": before_unique,
                "unique_after": after_unique,
                "master_path": str(args.master_path),
            },
        )

    print()
    print("=" * 70)
    print("UNIQUE VIDEO REFRESH COMPLETED")
    print("Existing unique videos:", before_unique)
    print("Candidate IDs collected:", len(candidate_ids))
    print("Resolved video details:", len(new_rows))
    print("Duplicates/unresolved skipped:", duplicates_skipped)
    print("New unique videos:", added)
    print("Total unique videos:", after_unique)
    print("Search API requests:", discovery["search_requests"])
    print("Video detail requests:", detail_requests)
    print("Published after:", discovery["published_after"])

    if args.dry_run:
        print("DRY RUN: no project files were modified.")
    else:
        print("Master dataset:", args.master_path)
        print("Refresh log:", DEFAULT_LOG_PATH)
        print("Raw discovery:", raw_path)

    print("=" * 70)


if __name__ == "__main__":
    main()
