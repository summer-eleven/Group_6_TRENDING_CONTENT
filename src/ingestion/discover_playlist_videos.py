"""Discover YouTube video IDs using uploads playlists seeded from the project master.

This script discovers CANDIDATES only. It does not write to the master dataset,
MinIO, or SQL Server. Video details and regional eligibility require later verification.

Example (from project root):
    uv run python -m src.ingestion.discover_playlist_videos --region VN --max-channels 20 --target-new 30 --lookback-days 7 --pages-per-channel 1 --max-requests 30 --dry-run
"""

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://www.googleapis.com/youtube/v3"
DEFAULT_MASTER = Path("data/processed/youtube_dataset_2000_clean.csv")
DEFAULT_OUTPUT = Path("data/raw/playlist_discovery")


class PlaylistNotFound(RuntimeError):
    """Raised when playlistItems returns HTTP 404 (deleted/private channel or playlist).

    Subclasses RuntimeError so any existing `except RuntimeError` still works.
    """


def parse_args():
    parser = argparse.ArgumentParser(
        description="Find new candidate video IDs from channels' uploads playlists without modifying the master."
    )
    parser.add_argument("--region", required=True, choices=("VN", "US", "JP"))
    parser.add_argument("--master-path", type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--max-channels", type=int, default=20)
    parser.add_argument("--target-new", type=int, default=50)
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--pages-per-channel", type=int, default=1)
    parser.add_argument(
    "--max-per-channel",
    type=int,
    default=10,
    help="Maximum number of new candidate videos from each channel.",
    )
    parser.add_argument("--max-requests", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.max_per_channel <= 0:
        parser.error("--max-per-channel must be greater than 0")
    for label in ("max_channels", "target_new", "lookback_days", "pages_per_channel", "max_requests"):
        if getattr(args, label) <= 0:
            parser.error(f"--{label.replace('_', '-')} must be greater than 0")
    return args


class YouTubeClient:
    def __init__(self, api_key, max_requests):
        self.api_key = api_key
        self.max_requests = max_requests
        self.request_count = 0
        self.session = requests.Session()

    def get(self, endpoint, **params):
        if self.request_count >= self.max_requests:
            raise RuntimeError(f"API request budget reached ({self.max_requests} calls).")
        params["key"] = self.api_key
        self.request_count += 1
        response = self.session.get(f"{API_BASE}/{endpoint}", params=params, timeout=30)
        if not response.ok:
            try:
                msg = response.json().get("error", {}).get("message", response.text[:250])
            except ValueError:
                msg = response.text[:250]
            # A 404 on playlistItems means this one playlist is gone/inaccessible.
            # Raise a dedicated exception so the caller can skip it and continue.
            if response.status_code == 404 and endpoint == "playlistItems":
                raise PlaylistNotFound(f"YouTube {endpoint} HTTP 404: {msg}")
            raise RuntimeError(f"YouTube {endpoint} HTTP {response.status_code}: {msg}")
        return response.json()


def select_seed_channels(master, region, max_channels):
    subset = master.loc[master["region_code"].eq(region)].copy()
    subset = subset.dropna(subset=["channel_id"])
    subset["channel_id"] = subset["channel_id"].astype(str).str.strip()
    subset = subset[subset["channel_id"].str.startswith("UC") & subset["channel_id"].str.len().eq(24)]
    subset["published_at"] = pd.to_datetime(subset["published_at"], utc=True, errors="coerce")
    subset = subset.sort_values("published_at", ascending=False)
    return subset.drop_duplicates("channel_id").head(max_channels)["channel_id"].tolist()


def uploads_playlists(client, channel_ids):
    output = {}
    for start in range(0, len(channel_ids), 50):
        batch = channel_ids[start:start + 50]
        data = client.get("channels", part="contentDetails", id=",".join(batch), maxResults=50)
        for item in data.get("items", []):
            playlist_id = item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
            if playlist_id:
                output[item["id"]] = playlist_id
    return output


def parse_utc(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def discover(
    client,
    playlists,
    known_ids,
    target_new,
    pages_per_channel,
    cutoff,
    max_per_channel,
):
    found_ids = set()
    rows = []
    counters = {
        "skipped_existing": 0,
        "skipped_old": 0,
        "skipped_missing_date": 0,
        "skipped_repeat": 0,
        "skipped_bad_playlist": 0,
    }
    bad_channels = []
    stopped_by_budget = False
    for channel_id, playlist_id in playlists.items():
        token = None
        added_from_channel = 0
        for page in range(pages_per_channel):
            if added_from_channel >= max_per_channel:
                break
            if client.request_count >= client.max_requests:
                stopped_by_budget = True
                break
            params = {"part": "contentDetails", "playlistId": playlist_id, "maxResults": 50}
            if token:
                params["pageToken"] = token
            try:
                data = client.get("playlistItems", **params)
            except PlaylistNotFound:
                # Deleted / terminated / private channel: skip it, keep going.
                counters["skipped_bad_playlist"] += 1
                bad_channels.append(channel_id)
                print(f"WARN: playlist {playlist_id} (channel {channel_id}) not found (404); skipping channel.")
                break
            for item in data.get("items", []):
                details = item.get("contentDetails", {})
                video_id = details.get("videoId")
                published = parse_utc(details.get("videoPublishedAt"))
                if not video_id:
                    continue
                if not published:
                    counters["skipped_missing_date"] += 1
                    continue
                if published < cutoff:
                    counters["skipped_old"] += 1
                    continue
                if video_id in known_ids:
                    counters["skipped_existing"] += 1
                    continue
                if video_id in found_ids:
                    counters["skipped_repeat"] += 1
                    continue

                if added_from_channel >= max_per_channel:
                    break

                found_ids.add(video_id)
                rows.append({
                    "video_id": video_id,
                    "channel_id": channel_id,
                    "published_at": published.isoformat(),
                    "discovery_source": "uploads_playlist",
                    "seed_region": None,  # populated after discovery; NOT creator's country
                    "upload_playlist_id": playlist_id,
                })
                added_from_channel += 1
                if len(rows) >= target_new:
                    return rows, counters, stopped_by_budget
            token = data.get("nextPageToken")
            if not token:
                break
        if stopped_by_budget:
            break
    if bad_channels:
        print(f"Skipped {len(bad_channels)} channel(s) with unavailable playlists: {', '.join(bad_channels[:10])}"
              + (" ..." if len(bad_channels) > 10 else ""))
    return rows, counters, stopped_by_budget


def main():
    args = parse_args()
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        raise SystemExit("Missing YOUTUBE_API_KEY in .env")
    if not args.master_path.is_file():
        raise SystemExit(f"Master not found: {args.master_path}")
    master = pd.read_csv(args.master_path, dtype={"video_id": "string", "channel_id": "string", "region_code": "string"})
    required = {"video_id", "channel_id", "region_code", "published_at"}
    if not required.issubset(master.columns):
        raise SystemExit(f"Missing master columns: {sorted(required - set(master.columns))}")
    known_ids = set(master["video_id"].dropna().astype(str))
    channels = select_seed_channels(master, args.region, args.max_channels)
    client = YouTubeClient(key, args.max_requests)
    print(f"Region seed: {args.region}; known unique IDs globally: {len(known_ids)}")
    print(f"Seed channels: {len(channels)}; target new candidates: {args.target_new}")
    if not channels:
        print("No valid channels in master for this region.")
        return
    try:
        playlists = uploads_playlists(client, channels)
        cutoff = datetime.now(timezone.utc) - timedelta(days=args.lookback_days)
        rows, counters, stopped_by_budget = discover(
            client,
            playlists,
            known_ids,
            args.target_new,
            args.pages_per_channel,
            cutoff,
            args.max_per_channel,
        )
    finally:
        client.session.close()
    for row in rows:
        row["seed_region"] = args.region
    print(f"Uploads playlists found: {len(playlists)}")
    print(f"Candidate video IDs new to master: {len(rows)}")
    print(f"API calls made: {client.request_count}/{args.max_requests}")
    print(f"Excluded: {counters}")
    print(f"Stopped by request budget: {stopped_by_budget}")
    if rows:
        print("First candidate IDs:", ", ".join(x["video_id"] for x in rows[:10]))
    print("NOTE: Candidate IDs are unverified; seed_region is not creator nationality or confirmed chart eligibility.")
    if args.dry_run:
        print("DRY RUN: no project files written (API calls still consume quota).")
        return
    out_dir = DEFAULT_OUTPUT / args.region
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"playlist_candidates_{args.region}_{stamp}.json"
    payload = {
        "region_seed": args.region,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "api_requests": client.request_count,
        "candidate_count": len(rows),
        "candidates": rows,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved candidate list: {path}")
    print("The master dataset, SQL and MinIO have NOT been changed.")


if __name__ == "__main__":
    main()