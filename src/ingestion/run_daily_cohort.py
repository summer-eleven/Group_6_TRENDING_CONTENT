"""Daily Rolling Cohort orchestrator for Group_6_TRENDING_CONTENT.

Use from the project root, with the existing modules:
  src.ingestion.discover_playlist_videos  (including --max-per-channel support)
  src.ingestion.rolling_cohort
  src.processing.sync_rolling_cohort

PLAN is the default and does not call the YouTube API, SQL, or MinIO.
A real run must explicitly include --apply. Do NOT schedule a real run before a
successful small-batch test, and keep Docker Desktop / SQL / MinIO available.

Example plan:
  uv run python -m src.ingestion.run_daily_cohort --region VN --target-new 1000

Example first REAL small-batch run:
  uv run python -m src.ingestion.run_daily_cohort --region VN --target-new 20 --max-channels 80 --max-per-channel 3 --discovery-max-requests 40 --apply

Each day, this script can create at most one new cohort batch per region.
One date is calculated using the host machine's local date (on Hạ's VN PC).
It will also attempt to re-sync any previously created but unsynced T0 files.
"""

import argparse
import inspect
import json
import math
import os
import socket
import subprocess
import sys
from contextlib import contextmanager
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
REGIONS = ("VN", "US", "JP")


def args_parser():
    p = argparse.ArgumentParser(description="Discover and sync one new Rolling Cohort T0 batch per local day")
    p.add_argument("--region", required=True, choices=REGIONS)
    p.add_argument("--target-new", type=int, default=1000)
    p.add_argument("--max-channels", type=int, default=400)
    p.add_argument("--max-per-channel", type=int, default=10)
    p.add_argument("--lookback-days", type=int, default=7)
    p.add_argument("--pages-per-channel", type=int, default=1)
    p.add_argument("--discovery-max-requests", type=int, default=160)
    p.add_argument("--details-max-requests", type=int, default=30)
    p.add_argument("--master-path", type=Path, default=MASTER)
    p.add_argument("--cohort-root", type=Path, default=COHORTS)
    p.add_argument("--registry-root", type=Path, default=REGISTRY_DIR)
    p.add_argument("--candidate-root", type=Path, default=CANDIDATES)
    p.add_argument("--apply", action="store_true", help="Actually call API and sync SQL/MinIO; default is PLAN only")
    ns = p.parse_args()
    for key in ("target_new", "max_channels", "max_per_channel", "lookback_days",
                "pages_per_channel", "discovery_max_requests", "details_max_requests"):
        if getattr(ns, key) < 1:
            p.error(f"--{key.replace('_','-')} must be positive")
    return ns


def json_data(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def registry_ids(registry_root):
    result = set()
    files = list(registry_root.glob("youtube_cohort_registry_*.csv"))
    for path in files:
        df = pd.read_csv(path, usecols=["video_id"], dtype={"video_id": "string"})
        result.update(df["video_id"].dropna().astype(str))
    return result, len(files)


def collect_known(master_path, cohort_root, registry_root):
    # known_video_ids() includes *all* region subdirectories under cohort_root.
    baseline, previous_count = known_video_ids(master_path, cohort_root)
    registry, registry_files = registry_ids(registry_root)
    baseline.update(registry)
    return baseline, previous_count, registry_files


def manifest_dates_for_region(cohort_root, region):
    root = cohort_root / region
    for path in root.glob("*/manifest.json"):
        try:
            payload = json_data(path)
            created = datetime.fromisoformat(str(payload["created_at_utc"]).replace("Z", "+00:00"))
            if created.tzinfo is None:
                raise ValueError("created_at_utc has no timezone")
            yield path, created.astimezone().date().isoformat()
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Could not validate manifest {path}: {exc}") from exc


def ensure_ports():
    # Avoid wasting YouTube quota when downstream storage is unavailable.
    for port, name in ((9000, "MinIO"), (1433, "SQL Server")):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=3):
                pass
        except OSError as exc:
            raise RuntimeError(f"{name} is not reachable at localhost:{port}; start Docker Desktop first") from exc


@contextmanager
def single_run_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"Another run or a stale lock exists: {path}. Check active tasks before removing it.") from exc
    try:
        with os.fdopen(fd, "w") as f:
            f.write(f"pid={os.getpid()} created={datetime.now(timezone.utc).isoformat()}\n")
        yield
    finally:
        path.unlink(missing_ok=True)


def call_module(*argv):
    cmd = [sys.executable, "-m", *map(str, argv)]
    print("RUN:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def sync_unfinished_t0(cohort_root, region):
    for manifest_path in sorted((cohort_root / region).glob("*/manifest.json")):
        t0_path = manifest_path.parent / "t0.json"
        synced_marker = manifest_path.parent / ".t0_synced"
        if synced_marker.exists():
            continue
        if not t0_path.is_file():
            raise RuntimeError(f"Missing T0 for {manifest_path}")
        # Idempotent: SQL has UNIQUE(batch_id, video_id, phase).
        call_module("src.processing.sync_rolling_cohort", "--manifest", manifest_path, "--phase", "T0", "--apply")
        synced_marker.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
        print("SYNCED T0:", manifest_path.parent.name, flush=True)


def gather_candidates(a, known_ids):
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("YOUTUBE_API_KEY missing from .env")

    master = pd.read_csv(a.master_path, dtype={"video_id": "string", "channel_id": "string", "region_code": "string"})
    # Pull the entire ranked source list and rotate the FIRST channel each day,
    # preventing the same small subset of channels from dominating daily batches.
    all_channels = discovery.select_seed_channels(master, a.region, 1_000_000)
    if not all_channels:
        print("No seed channels available; no new cohort created.")
        return None, 0, 0, 0
    offset = (datetime.now().date().toordinal() * 113) % len(all_channels)
    rotated = all_channels[offset:] + all_channels[:offset]
    channels = rotated[:a.max_channels]
    print("Seed channels today:", len(channels), "/", len(all_channels), "| rotation offset:", offset)

    # Require the user's modified version supporting --max-per-channel.
    if "max_per_channel" not in inspect.signature(discovery.discover).parameters:
        raise RuntimeError("discover_playlist_videos.py must support discover(..., max_per_channel). Check Step 22 changes.")

    client = discovery.YouTubeClient(key, a.discovery_max_requests)
    try:
        uploads = discovery.uploads_playlists(client, channels)
        cutoff = datetime.now(timezone.utc) - timedelta(days=a.lookback_days)
        rows, counters, stopped = discovery.discover(
            client, uploads, known_ids, a.target_new, a.pages_per_channel, cutoff, a.max_per_channel
        )
    finally:
        client.session.close()
    for row in rows:
        row["seed_region"] = a.region
    if len({x["video_id"] for x in rows}) != len(rows):
        raise RuntimeError("Discovery returned duplicate video IDs")
    from collections import Counter
    distribution = Counter(x["channel_id"] for x in rows)
    if distribution and max(distribution.values()) > a.max_per_channel:
        raise RuntimeError("Per-channel cap not enforced by Discovery; refusing to start")
    print("Candidate IDs:", len(rows), "| channels:", len(distribution),
          "| API calls:", client.request_count, "| uploads playlists:", len(uploads))
    print("Excluded:", counters, "| Budget hit:", stopped)
    if not rows:
        return None, 0, client.request_count, len(distribution)

    out_dir = a.candidate_root / a.region
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    out = out_dir / f"playlist_candidates_{a.region}_{stamp}.json"
    payload = {"region_seed": a.region, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
               "api_requests": client.request_count, "candidate_count": len(rows), "candidates": rows,
               "selection_policy": {"max_per_channel": a.max_per_channel, "max_channels": a.max_channels,
                                    "lookback_days": a.lookback_days, "channel_rotation": offset}}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Saved candidate JSON:", out)
    return out, len(rows), client.request_count, len(distribution)


def main():
    a = args_parser()
    today = datetime.now().date().isoformat()  # host Windows local date
    if not a.master_path.exists():
        raise SystemExit(f"Missing master: {a.master_path}")
    known, prev_cohorts, registry_files = collect_known(a.master_path, a.cohort_root, a.registry_root)
    existing_today = [p for p, date in manifest_dates_for_region(a.cohort_root, a.region) if date == today]
    print("MODE:", "APPLY" if a.apply else "PLAN (no API or data writes)")
    print("Region:", a.region, "| Windows local day:", today)
    print("Known video IDs across master + registries + T0:", len(known))
    print("Previous cohort T0 records:", prev_cohorts, "| Registry files:", registry_files)
    print("Existing batches created today:", len(existing_today))
    print("Requested new IDs:", a.target_new, "| max channels:", a.max_channels,
          "| max per channel:", a.max_per_channel)
    print("Discovery request cap:", a.discovery_max_requests,
          "| details request cap:", a.details_max_requests)
    if not a.apply:
        print("PLAN COMPLETE. To begin a real run, supply --apply after testing a SMALL batch.")
        return

    load_dotenv()
    with single_run_lock(a.cohort_root / a.region / ".daily_run.lock"):
        ensure_ports()
        # Finish partial T0 syncs before generating any new video IDs.
        sync_unfinished_t0(a.cohort_root, a.region)
        existing_today = [p for p, date in manifest_dates_for_region(a.cohort_root, a.region) if date == today]
        if existing_today:
            print("SKIP: a cohort batch has already been created today:", existing_today[0])
            print("The daily run will not create another batch.")
            return
        known, _, _ = collect_known(a.master_path, a.cohort_root, a.registry_root)
        candidate_path, candidate_count, discovery_calls, _ = gather_candidates(a, known)
        if not candidate_path:
            print("NO NEW CANDIDATES. No cohort created; review channel selection and API budget.")
            return
        necessary = math.ceil(candidate_count / 50)
        if necessary > a.details_max_requests:
            raise RuntimeError(f"Need {necessary} videos.list calls; details cap is {a.details_max_requests}. "
                               "Candidate JSON saved; no T0 created.")
        previous_manifests = set((a.cohort_root / a.region).glob("*/manifest.json"))
        call_module("src.ingestion.rolling_cohort", "start", "--region", a.region,
                    "--candidates", candidate_path, "--limit", candidate_count,
                    "--master-path", a.master_path, "--output-root", a.cohort_root,
                    "--max-requests", a.details_max_requests)
        created = set((a.cohort_root / a.region).glob("*/manifest.json")) - previous_manifests
        if len(created) != 1:
            raise RuntimeError(f"Expected one new cohort manifest; found {len(created)}. Inspect run before retrying.")
        sync_unfinished_t0(a.cohort_root, a.region)
        manifest = json_data(next(iter(created)))
        print("DAILY COHORT SUCCESS | batch:", manifest["batch_id"],
              "| confirmed video IDs:", manifest["video_ids_confirmed"],
              "| discovery API requests:", discovery_calls, flush=True)
        print("NOTE: master remains unchanged; count unique IDs across master + registries for progress.")
        print("NOTE: no chart label is inferred; chart monitoring is a separate process.")


if __name__ == "__main__":
    main()
