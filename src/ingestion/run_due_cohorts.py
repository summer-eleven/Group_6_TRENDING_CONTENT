"""Update due Rolling Cohort batches and sync T24 to MinIO/SQL.

Run from the project root with:
    uv run python -m src.ingestion.run_due_cohorts --region VN --dry-run
    uv run python -m src.ingestion.run_due_cohorts --region VN

The existing rolling_cohort.py and sync_rolling_cohort.py do the actual work.
This runner never touches master data, and never updates a batch before due_at_utc.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_ROOT = Path("data/raw/rolling_cohorts")


def parse_utc(value):
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("due_at_utc must include a UTC offset")
    return dt.astimezone(timezone.utc)


def run_step(arguments):
    print("RUN:", " ".join(map(str, arguments)), flush=True)
    subprocess.run(arguments, check=True)


def process_manifest(path, now, max_requests, dry_run):
    manifest = json.loads(path.read_text(encoding="utf-8"))
    batch_id = manifest.get("batch_id", path.parent.name)
    status = manifest.get("status")
    due = parse_utc(manifest["due_at_utc"])
    t24_path = path.parent / "t24.json"
    sync_marker = path.parent / ".t24_synced"

    if sync_marker.exists():
        print(f"SKIP {batch_id}: T24 already synced")
        return "skipped"

    if status == "PENDING_T24" and now < due:
        print(f"WAIT {batch_id}: due {due.isoformat()}")
        return "waiting"

    if status not in ("PENDING_T24", "COMPLETED"):
        print(f"SKIP {batch_id}: unexpected status {status!r}")
        return "skipped"

    if status == "PENDING_T24" and t24_path.exists():
        raise RuntimeError(
            f"{batch_id}: t24.json exists but manifest is PENDING_T24. "
            "Inspect this partial write manually; do not overwrite it."
        )

    if status == "COMPLETED" and not t24_path.exists():
        raise RuntimeError(f"{batch_id}: manifest completed but t24.json is missing")

    if dry_run:
        action = "UPDATE + SYNC" if status == "PENDING_T24" else "SYNC ONLY"
        print(f"PLAN {batch_id}: {action} (dry-run, no API or writes)")
        return "planned"

    if status == "PENDING_T24":
        run_step([
            sys.executable, "-m", "src.ingestion.rolling_cohort", "update",
            "--manifest", str(path), "--max-requests", str(max_requests),
        ])
        updated_manifest = json.loads(path.read_text(encoding="utf-8"))
        if updated_manifest.get("status") != "COMPLETED" or not t24_path.exists():
            raise RuntimeError(f"{batch_id}: update did not finish correctly")

    run_step([
        sys.executable, "-m", "src.processing.sync_rolling_cohort",
        "--manifest", str(path), "--phase", "T24", "--apply",
    ])
    # The marker is written only after sync command returns success.
    sync_marker.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    print(f"DONE {batch_id}: T24 synced")
    return "done"


def main():
    parser = argparse.ArgumentParser(
        description="Find all due batches and update/sync T24 without duplication."
    )
    parser.add_argument("--region", required=True, choices=("VN", "US", "JP"))
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--max-requests", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.max_requests < 1:
        parser.error("--max-requests must be greater than zero")

    region_dir = args.root / args.region
    if not region_dir.is_dir():
        print(f"No batch directory yet: {region_dir}")
        return

    manifests = sorted(region_dir.rglob("manifest.json"))
    now = datetime.now(timezone.utc)
    print(f"Region: {args.region} | Batches found: {len(manifests)} | UTC now: {now.isoformat()}")
    print("Mode:", "DRY RUN" if args.dry_run else "APPLY")
    failures = 0
    for path in manifests:
        try:
            process_manifest(path, now, args.max_requests, args.dry_run)
        except (ValueError, KeyError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
            failures += 1
            print(f"ERROR {path}: {exc}", file=sys.stderr, flush=True)

    if failures:
        print(f"Finished with {failures} batch error(s)", file=sys.stderr)
        raise SystemExit(1)
    print("Finished without batch errors")


if __name__ == "__main__":
    main()
