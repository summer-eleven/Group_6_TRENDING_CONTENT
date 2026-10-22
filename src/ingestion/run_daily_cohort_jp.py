"""JP-only daily cohort wrapper that skips SQL/MinIO sync.

On Ha's machine, Docker/SQL/MinIO are NOT available.
This script reuses the core logic from run_daily_cohort but skips:
  - ensure_ports() check
  - sync_unfinished_t0() calls
  - sync after creating new batch

Usage:
  uv run python -m src.ingestion.run_daily_cohort_jp --target-new 1000 --apply
  uv run python -m src.ingestion.run_daily_cohort_jp --target-new 2000 --apply
"""

import argparse
import inspect
import json
import math
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from src.ingestion import discover_playlist_videos as discovery
from src.ingestion.rolling_cohort import known_video_ids

MASTER = Path("data/processed/youtube_dataset_2000_clean.csv")
COHORTS = Path("data/raw/rolling_cohorts")
REGISTRY_DIR = Path("data/processed")
CANDIDATES = Path("data/raw/playlist_discovery")
REGION = "JP"


def args_parser():
    p = argparse.ArgumentParser(description="JP daily cohort (no SQL/MinIO)")
    p.add_argument("--target-new", type=int, default=1000)
    p.add_argument("--max-channels", type=int, default=400)
    p.add_argument("--max-per-channel", type=int, default=10)
    p.add_argument("--lookback-days", type=int, default=7)
    p.add_argument("--pages-per-channel", type=int, default=1)
    p.add_argument("--discovery-max-requests", type=int, default=450)
    p.add_argument("--details-max-requests", type=int, default=60)
    p.add_argument("--apply", action="store_true")
    return p.parse_args()


def registry_ids():
    result = set()
    for path in REGISTRY_DIR.glob("youtube_cohort_registry_*.csv"):
        df = pd.read_csv(path, usecols=["video_id"], dtype={"video_id": "string"})
        result.update(df["video_id"].dropna().astype(str))
    return result


def collect_known():
    baseline, prev_count = known_video_ids(MASTER, COHORTS)
    baseline.update(registry_ids())
    return baseline, prev_count


def manifest_dates():
    root = COHORTS / REGION
    dates = []
    for path in root.glob("*/manifest.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            created = datetime.fromisoformat(
                str(payload["created_at_utc"]).replace("Z", "+00:00")
            )
            dates.append((path, created.astimezone().date().isoformat()))
        except Exception:
            pass
    return dates


def main():
    a = args_parser()
    load_dotenv()
    today = datetime.now().date().isoformat()
    known, prev = collect_known()
    existing_today = [p for p, d in manifest_dates() if d == today]

    print(f"MODE: {'APPLY' if a.apply else 'PLAN'} | Region: {REGION} | Day: {today}")
    print(f"Known video IDs: {len(known)} | Previous T0 batches: {prev}")
    print(f"Batches today: {len(existing_today)} | Target new: {a.target_new}")
    print(f"NOTE: SQL/MinIO sync SKIPPED (not available on this machine)")

    if not a.apply:
        print("PLAN COMPLETE. Add --apply for a real run.")
        return

    if existing_today:
        print(f"SKIP: batch already created today: {existing_today[0]}")
        return

    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("YOUTUBE_API_KEY missing from .env")

    master = pd.read_csv(MASTER, dtype={"video_id": "string", "channel_id": "string", "region_code": "string"})
    all_channels = discovery.select_seed_channels(master, REGION, 1_000_000)
    if not all_channels:
        print("No seed channels available.")
        return

    offset = (datetime.now().date().toordinal() * 113) % len(all_channels)
    channels = (all_channels[offset:] + all_channels[:offset])[:a.max_channels]
    print(f"Seed channels: {len(channels)}/{len(all_channels)} | rotation: {offset}")

    if "max_per_channel" not in inspect.signature(discovery.discover).parameters:
        raise RuntimeError("discover_playlist_videos.py must support max_per_channel")

    client = discovery.YouTubeClient(key, a.discovery_max_requests)
    try:
        uploads = discovery.uploads_playlists(client, channels)
        cutoff = datetime.now(timezone.utc) - timedelta(days=a.lookback_days)
        rows, counters, stopped = discovery.discover(
            client, uploads, known, a.target_new, a.pages_per_channel, cutoff, a.max_per_channel
        )
    finally:
        client.session.close()

    for row in rows:
        row["seed_region"] = REGION

    print(f"Candidates: {len(rows)} | API calls: {client.request_count}")
    if not rows:
        print("No new candidates found.")
        return

    out_dir = CANDIDATES / REGION
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    out = out_dir / f"playlist_candidates_{REGION}_{stamp}.json"
    payload = {
        "region_seed": REGION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "api_requests": client.request_count,
        "candidate_count": len(rows),
        "candidates": rows,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved candidates: {out}")

    necessary = math.ceil(len(rows) / 50)
    if necessary > a.details_max_requests:
        raise RuntimeError(f"Need {necessary} calls; cap is {a.details_max_requests}")

    prev_manifests = set((COHORTS / REGION).glob("*/manifest.json"))
    cmd = [
        sys.executable, "-m", "src.ingestion.rolling_cohort", "start",
        "--region", REGION,
        "--candidates", str(out),
        "--limit", str(len(rows)),
        "--master-path", str(MASTER),
        "--output-root", str(COHORTS),
        "--max-requests", str(a.details_max_requests),
    ]
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    created = set((COHORTS / REGION).glob("*/manifest.json")) - prev_manifests
    if created:
        m = json.loads(next(iter(created)).read_text(encoding="utf-8-sig"))
        print(f"SUCCESS | batch: {m['batch_id']} | videos: {m['video_ids_confirmed']}")
        marker = next(iter(created)).parent / ".t0_synced"
        marker.write_text(f"{datetime.now(timezone.utc).isoformat()} auto-no-sql", encoding="utf-8")
        print(f"Created .t0_synced marker (SQL sync skipped)")
    else:
        print("WARNING: no new manifest found after rolling_cohort start")


if __name__ == "__main__":
    main()