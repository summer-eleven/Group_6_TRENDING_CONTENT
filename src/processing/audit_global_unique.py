#!/usr/bin/env python3
"""Audit unique YouTube videos across a master CSV and regional registries.

Safe by default: reads CSVs only. --save writes small summary reports, but never
modifies input files or connects to YouTube, SQL Server, or MinIO.

Usage from repository root after placing this file at src/processing/:
    python -m src.processing.audit_global_unique
    python -m src.processing.audit_global_unique --save
    python -m src.processing.audit_global_unique --save --export-ids
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
TARGET_REGIONS = ("VN", "US", "JP")
METADATA_FIELDS = ("title", "channel_id", "published_at")


def parse_args():
    parser = argparse.ArgumentParser(description="Read-only unique video audit for the Trending Content project")
    parser.add_argument("--master", type=Path, default=Path("data/processed/youtube_dataset_2000_clean.csv"))
    parser.add_argument("--registry-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/assets/data_audit"))
    parser.add_argument("--save", action="store_true", help="Save JSON and small CSV summary reports")
    parser.add_argument("--export-ids", action="store_true", help="Export all unique IDs to CSV (requires --save); do not commit this large file")
    return parser.parse_args()


def clean(value):
    return (value or "").strip()


def read_csv(path: Path, source_name: str, videos: dict, source_stats: list):
    stats = {"source": source_name, "path": str(path), "rows": 0, "valid_rows": 0,
             "distinct_ids": 0, "blank_ids": 0, "invalid_ids": 0,
             "duplicate_rows_within_source": 0}
    seen_here = set()
    file_region_match = re.search(r"_([A-Za-z]{2})\.csv$", path.name)
    file_region = file_region_match.group(1).upper() if file_region_match and source_name.startswith("registry:") else ""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "video_id" not in reader.fieldnames:
            raise ValueError(f"File lacks a video_id column: {path}")
        for row in reader:
            stats["rows"] += 1
            video_id = clean(row.get("video_id"))
            if not video_id:
                stats["blank_ids"] += 1
                continue
            if not VIDEO_ID_RE.fullmatch(video_id):
                stats["invalid_ids"] += 1
                continue
            stats["valid_rows"] += 1
            if video_id in seen_here:
                stats["duplicate_rows_within_source"] += 1
            seen_here.add(video_id)
            region = clean(row.get("region_code")).upper() or file_region or "UNKNOWN"
            meta_present = {field for field in METADATA_FIELDS if clean(row.get(field))}
            entry = videos.setdefault(video_id, {"regions": set(), "sources": set(), "metadata": set()})
            entry["regions"].add(region)
            entry["sources"].add(source_name)
            entry["metadata"].update(meta_present)
    stats["distinct_ids"] = len(seen_here)
    source_stats.append(stats)


def make_report(videos: dict, source_stats: list):
    per_region = Counter()
    pairwise = Counter()
    for video in videos.values():
        regions = video["regions"]
        per_region.update(regions)
        for left, right in combinations(sorted(regions), 2):
            pairwise[f"{left}|{right}"] += 1
    target_union = sum(bool(v["regions"] & set(TARGET_REGIONS)) for v in videos.values())
    missing_meta = {f: sum(f not in v["metadata"] for v in videos.values()) for f in METADATA_FIELDS}
    complete_meta = sum(all(f in v["metadata"] for f in METADATA_FIELDS) for v in videos.values())
    return {
        "audit_time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "Master CSV plus youtube_cohort_registry_*.csv in registry directory",
        "target_unique_global": 100000,
        "unique_global_all_regions": len(videos),
        "unique_union_VN_US_JP": target_union,
        "remaining_to_100000_all_regions": max(0, 100000 - len(videos)),
        "remaining_to_100000_VN_US_JP": max(0, 100000 - target_union),
        "unique_by_region": dict(sorted(per_region.items())),
        "pairwise_region_overlap": dict(sorted(pairwise.items())),
        "complete_core_metadata": complete_meta,
        "missing_core_metadata_by_field": missing_meta,
        "input_sources": source_stats,
        "limitations": [
            "Counts cover only the local input CSV files; any US/JP data stored elsewhere are not included.",
            "A valid 11-character video ID format is not proof that the video still exists on YouTube.",
            "Regional counts reflect dataset membership; a video can appear in multiple regions.",
            "Historical snapshots and RQ1 analysis subsets are intentionally not counted as new sources.",
        ],
    }


def write_summary(folder: Path, report: dict, videos: dict, export_ids: bool):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "global_unique_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with (folder / "global_unique_by_region.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["region", "unique_video_ids"])
        for region, count in report["unique_by_region"].items():
            writer.writerow([region, count])
    with (folder / "global_unique_sources.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source", "path", "rows", "valid_rows", "distinct_ids",
                                                         "blank_ids", "invalid_ids", "duplicate_rows_within_source"])
        writer.writeheader()
        writer.writerows(report["input_sources"])
    if export_ids:
        with (folder / "global_unique_video_ids.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["video_id", "regions", "sources", "complete_core_metadata"])
            for video_id in sorted(videos):
                entry = videos[video_id]
                writer.writerow([video_id, ";".join(sorted(entry["regions"])),
                                 ";".join(sorted(entry["sources"])),
                                 int(all(f in entry["metadata"] for f in METADATA_FIELDS))])
    return folder


def main():
    args = parse_args()
    if args.export_ids and not args.save:
        raise SystemExit("--export-ids requires --save")
    if not args.master.is_file():
        raise SystemExit(f"Master CSV not found: {args.master} (run from repository root)")
    registries = sorted(args.registry_dir.glob("youtube_cohort_registry_*.csv"))
    if not registries:
        print("WARNING: No regional registry CSV found. US/JP registries may exist on other PCs.")
    videos = {}
    source_stats = []
    read_csv(args.master, "master", videos, source_stats)
    for registry in registries:
        region = registry.stem.removeprefix("youtube_cohort_registry_").upper()
        read_csv(registry, f"registry:{region}", videos, source_stats)
    report = make_report(videos, source_stats)
    print("\n=== TRENDING CONTENT / UNIQUE-VIDEO AUDIT ===")
    print("Input files:", 1 + len(registries))
    print("Valid unique IDs (ALL regions):", f"{report['unique_global_all_regions']:,}")
    print("Valid unique IDs (VN/US/JP union):", f"{report['unique_union_VN_US_JP']:,}")
    print("Still needed to reach 100,000 (VN/US/JP):", f"{report['remaining_to_100000_VN_US_JP']:,}")
    print("Region memberships:")
    for region, count in report["unique_by_region"].items():
        print(f"  {region:<8} {count:>10,}")
    print("Complete core metadata:", f"{report['complete_core_metadata']:,}")
    print("Missing metadata:", report["missing_core_metadata_by_field"])
    print("Region overlaps:", report["pairwise_region_overlap"] or "none")
    for s in source_stats:
        print(f"  {s['source']}: {s['distinct_ids']:,} distinct; {s['invalid_ids']:,} invalid; {s['blank_ids']:,} blank")
    if args.save:
        out_dir = write_summary(args.output_dir, report, videos, args.export_ids)
        print("Saved summaries to:", out_dir.resolve())
        if args.export_ids:
            print("ID export includes a potentially large dataset; keep it out of Git.")
    else:
        print("Read-only mode: no files written. Use --save to save summary reports.")


if __name__ == "__main__":
    main()
