#!/usr/bin/env python3
"""Merge regional YouTube CSVs into a distinct-video global master.

Run from project root after stage 110.6.2:
    python -m src.processing.build_global_master
    python -m src.processing.build_global_master --save

Defaults to preview only. --save creates NEW derived files; original data is never
modified, and the program does not access APIs, MinIO, Docker or the database.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
REGION = re.compile(r"^[A-Z]{2}$")
TARGET = {"VN", "US", "JP"}
REQUIRED_METADATA = ("title", "channel_id", "published_at")

# Name, repository-relative path, priority for metadata selection.
# Import history may contain videos missing from the main CSV files.
INPUTS = (
    ("vn_master", "data/processed/youtube_dataset_2000_clean.csv", 2),
    ("vn_registry", "data/processed/youtube_cohort_registry_VN.csv", 3),
    ("us_master", "data/imports/US/youtube_dataset_2000_clean.csv", 2),
    ("us_registry", "data/imports/US/youtube_cohort_registry_US.csv", 3),
    ("jp_master", "data/imports/JP/youtube_dataset_2000_clean.csv", 2),
    ("us_history", "data/imports/US/youtube_history.csv", 1),
    ("us_history_region", "data/imports/US/youtube_history_US.csv", 1),
    ("jp_history", "data/imports/JP/youtube_history.csv", 1),
)
# A JP registry may be added later by the Japanese-region owner.
OPTIONAL_INPUTS = (
    ("jp_registry", "data/imports/JP/youtube_cohort_registry_JP.csv", 3),
)

FIELDS = (
    "title", "channel_id", "channel_title", "category_id", "published_at",
    "upload_hour_utc", "video_url", "first_seen_at", "discovery_batch_id",
    "discovery_source", "discovery_query", "youtube_charted_at_discovery",
)

MASTER_FIELDS = (
    "video_id", *FIELDS, "region_codes", "region_count", "source_files",
    "source_count", "metadata_source", "metadata_complete",
)
BRIDGE_FIELDS = ("video_id", "region_code", "source_files")


def clean(value):
    text = str(value if value is not None else "").strip()
    return "" if text.lower() in {"nan", "none", "null", "na"} else text


def normalized_region(row, name):
    # The row's region_code always takes precedence over the file's name.
    raw = clean(row.get("region_code")).upper()
    if REGION.fullmatch(raw):
        return raw
    if raw:
        return "UNKNOWN"
    if name.endswith("_registry"):
        return name[:2].upper()
    return "UNKNOWN"


def create_entry():
    return {
        "regions": set(),
        "region_sources": defaultdict(set),
        "sources": set(),
        "values": {},
        "field_rank": {},
        "channel_ids": set(),
    }


def consume(path, name, priority, videos, stats):
    seen = set()
    report = {
        "source": name, "path": str(path), "rows": 0, "valid_rows": 0,
        "unique_ids": 0, "invalid_ids": 0, "blank_ids": 0,
        "duplicates_in_source": 0,
    }
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or "video_id" not in reader.fieldnames:
            raise ValueError(f"Missing video_id header: {path}")
        if "region_code" not in reader.fieldnames:
            raise ValueError(f"Missing region_code header: {path}")
        for row in reader:
            report["rows"] += 1
            vid = clean(row.get("video_id"))
            if not vid:
                report["blank_ids"] += 1
                continue
            if not VIDEO_ID.fullmatch(vid):
                report["invalid_ids"] += 1
                continue
            report["valid_rows"] += 1
            if vid in seen:
                report["duplicates_in_source"] += 1
            seen.add(vid)
            item = videos.setdefault(vid, create_entry())
            region = normalized_region(row, name)
            item["regions"].add(region)
            item["region_sources"][region].add(name)
            item["sources"].add(name)
            channel = clean(row.get("channel_id"))
            if channel:
                item["channel_ids"].add(channel)
            for field in FIELDS:
                value = clean(row.get(field))
                if not value:
                    continue
                # Highest-quality source wins for each populated metadata field.
                # Equal-priority ties keep first-seen input; no silent overwrites.
                if field not in item["values"] or priority > item["field_rank"][field][0]:
                    item["values"][field] = value
                    item["field_rank"][field] = (priority, name)
    report["unique_ids"] = len(seen)
    stats.append(report)


def summarize(videos, stats):
    by_region = Counter()
    metadata_missing = Counter()
    complete = 0
    target_complete = 0
    incomplete_target = 0
    overlap_target = 0
    target_unique = 0
    channel_conflicts = 0
    metadata_from_history = 0
    for item in videos.values():
        for region in item["regions"]:
            by_region[region] += 1
        good = all(clean(item["values"].get(f)) for f in REQUIRED_METADATA)
        complete += good
        for f in REQUIRED_METADATA:
            if not clean(item["values"].get(f)):
                metadata_missing[f] += 1
        has_target = bool(item["regions"] & TARGET)
        target_unique += has_target
        if has_target:
            target_complete += good
            incomplete_target += not good
            overlap_target += len(item["regions"] & TARGET) > 1
        channel_conflicts += len(item["channel_ids"]) > 1
        # Some videos exist only in history rather than normalized master/registry.
        metadata_from_history += not any(s.endswith("_master") or s.endswith("_registry") for s in item["sources"])
    return {
        "audit_time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "unique_global_all_regions": len(videos),
        "unique_union_VN_US_JP": target_unique,
        "remaining_to_100000_VN_US_JP": max(0, 100000 - target_unique),
        "unique_by_region": dict(sorted(by_region.items())),
        "target_multi_region_video_count": overlap_target,
        "complete_core_metadata_global": complete,
        "complete_core_metadata_target": target_complete,
        "incomplete_core_metadata_target": incomplete_target,
        "missing_core_metadata_by_field_global": dict(sorted(metadata_missing.items())),
        "channel_id_conflicts_across_sources": channel_conflicts,
        "videos_seen_only_in_history_global": metadata_from_history,
        "inputs": stats,
        "limitations": [
            "Each video_id appears once in global master. Regional memberships may overlap.",
            "Regional membership means observed with region_code, NOT the video's country of origin.",
            "The history rows are deduplicated by video_id; snapshot counts are not unique videos.",
            "A valid 11-character ID and nonblank metadata do not prove the video is currently public.",
            "Raw per-source values are preserved in their original input CSVs; selected metadata prefer registry, then master, then history.",
            "Files in data/imports are ignored by Git, and generated large CSVs should also be ignored.",
        ],
    }


def write_outputs(videos, report, output_dir, report_path):
    # Fail instead of overwriting existing output files. To refresh, move/backup
    # the prior outputs after reviewing them, then rerun --save.
    master_path = output_dir / "youtube_global_master.csv"
    region_path = output_dir / "youtube_video_regions.csv"
    paths = (master_path, region_path, report_path)
    existing = [p for p in paths if p.exists()]
    if existing:
        raise FileExistsError("Output already exists (no overwrite): " + ", ".join(map(str, existing)))
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with master_path.open("w", encoding="utf-8-sig", newline="") as master_stream, \
         region_path.open("w", encoding="utf-8-sig", newline="") as region_stream:
        master_writer = csv.DictWriter(master_stream, fieldnames=MASTER_FIELDS)
        region_writer = csv.DictWriter(region_stream, fieldnames=BRIDGE_FIELDS)
        master_writer.writeheader()
        region_writer.writeheader()
        for vid in sorted(videos):
            item = videos[vid]
            row = {"video_id": vid, **{f: item["values"].get(f, "") for f in FIELDS}}
            row["region_codes"] = ";".join(sorted(item["regions"]))
            row["region_count"] = len(item["regions"])
            row["source_files"] = ";".join(sorted(item["sources"]))
            row["source_count"] = len(item["sources"])
            row["metadata_complete"] = int(all(row[f] for f in REQUIRED_METADATA))
            row["metadata_source"] = item["field_rank"].get("title", (0, ""))[1]
            master_writer.writerow(row)
            for region in sorted(item["regions"]):
                region_writer.writerow({
                    "video_id": vid,
                    "region_code": region,
                    "source_files": ";".join(sorted(item["region_sources"][region])),
                })
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return paths


def main():
    parser = argparse.ArgumentParser(description="Build a deduplicated global YouTube master from VN/US/JP CSVs")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    parser.add_argument("--save", action="store_true", help="Write derived CSVs and JSON summary")
    parser.add_argument("--output-dir", type=Path, default=Path("data/global"))
    parser.add_argument("--report-path", type=Path, default=Path("reports/assets/data_audit/global_merge_summary.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    inputs = [(name, root / relative, priority) for name, relative, priority in INPUTS]
    for name, relative, priority in OPTIONAL_INPUTS:
        path = root / relative
        if path.exists():
            inputs.append((name, path, priority))
    missing = [p for _, p, _ in inputs if not p.is_file()]
    if missing:
        raise SystemExit("Missing required files:\n  " + "\n  ".join(map(str, missing)))
    videos = {}
    stats = []
    for name, path, priority in inputs:
        consume(path, name, priority, videos, stats)
    report = summarize(videos, stats)
    print("\n=== TRENDING CONTENT / GLOBAL MASTER PREVIEW ===")
    print("CSV inputs:", len(stats))
    print("Unique across ALL regions:", f"{report['unique_global_all_regions']:,}")
    print("Unique VN/US/JP union:", f"{report['unique_union_VN_US_JP']:,}")
    print("Needed for 100,000 VN/US/JP:", f"{report['remaining_to_100000_VN_US_JP']:,}")
    print("Target unique with complete core metadata:", f"{report['complete_core_metadata_target']:,}")
    print("Target missing core metadata:", f"{report['incomplete_core_metadata_target']:,}")
    print("Seen only in History (all regions):", f"{report['videos_seen_only_in_history_global']:,}")
    print("Channel ID conflicts across sources:", f"{report['channel_id_conflicts_across_sources']:,}")
    print("Regional membership:")
    for region, count in report["unique_by_region"].items():
        print(f"  {region:>8}: {count:>7,}")
    if args.save:
        paths = write_outputs(videos, report, root / args.output_dir, root / args.report_path)
        print("\nSaved NEW files:")
        for path in paths:
            print(" -", path)
    else:
        print("\nREAD-ONLY: Nothing written. Review numbers, then run again with --save.")


if __name__ == "__main__":
    main()
