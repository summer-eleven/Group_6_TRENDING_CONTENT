"""Update due Rolling Cohort batches for JP without requiring SQL Server or MinIO.

Designed for local developer environments where Docker/SQL/MinIO are unavailable.
Workflow:
  1. Scans data/raw/rolling_cohorts/JP/ for manifests with status PENDING_T24.
  2. If UTC now >= due_at_utc, runs `rolling_cohort update`.
  3. Rebuilds the JP cohort registry automatically.

Usage:
  uv run python -m src.ingestion.run_due_cohorts_jp --dry-run
  uv run python -m src.ingestion.run_due_cohorts_jp
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ROOT = Path("data/raw/rolling_cohorts/JP")


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

    if status == "COMPLETED" and t24_path.exists():
        print(f"SKIP {batch_id}: already completed with t24.json present")
        return "completed"

    if status == "PENDING_T24" and now < due:
        print(f"WAIT {batch_id}: due at {due.isoformat()}")
        return "waiting"

    if status != "PENDING_T24":
        print(f"SKIP {batch_id}: status={status!r}")
        return "skipped"

    if dry_run:
        print(f"PLAN {batch_id}: UPDATE T24 (dry-run, no API or writes)")
        return "planned"

    print(f"UPDATING {batch_id} (due since {due.isoformat()})...")
    run_step([
        sys.executable, "-m", "src.ingestion.rolling_cohort", "update",
        "--manifest", str(path), "--max-requests", str(max_requests),
    ])

    updated_manifest = json.loads(path.read_text(encoding="utf-8"))
    if updated_manifest.get("status") != "COMPLETED" or not t24_path.exists():
        raise RuntimeError(f"{batch_id}: update did not finish correctly")

    print(f"DONE {batch_id}: T24 completed successfully")
    return "done"


def main():
    parser = argparse.ArgumentParser(description="JP Due Cohort Runner (No SQL/MinIO required)")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--max-requests", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.root.is_dir():
        print(f"Directory not found: {args.root}")
        return

    now = datetime.now(timezone.utc)
    manifests = sorted(args.root.glob("*/manifest.json"))
    print(f"Region: JP | Batches found: {len(manifests)} | UTC now: {now.isoformat()}")

    updated_count = 0
    for m in manifests:
        res = process_manifest(m, now, args.max_requests, args.dry_run)
        if res == "done":
            updated_count += 1

    if updated_count > 0 and not args.dry_run:
        print("\nRebuilding JP cohort registry...")
        run_step([sys.executable, "-m", "src.processing.build_cohort_registry_jp"])

    print("Finished JP due cohorts check.")


if __name__ == "__main__":
    main()
