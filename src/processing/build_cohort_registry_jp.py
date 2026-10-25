"""Build and update youtube_cohort_registry_JP.csv from local raw cohort batches.

Matches the exact schema (REGISTRY_COLUMNS) of sync_rolling_cohort.py.
Safe for local-only machines without direct SQL/MinIO access.
"""

import json
from pathlib import Path
import pandas as pd

REGISTRY_COLUMNS = [
    'video_id', 'region_code', 'batch_id', 'title', 'channel_id',
    'channel_title', 'category_id', 'published_at', 'first_seen_at',
    'discovery_source', 'seed_region', 'region_availability',
    't0_collected_at', 't0_view_count', 't0_like_count', 't0_comment_count',
    't24_collected_at', 't24_view_count', 't24_like_count', 't24_comment_count',
    'hours_elapsed', 'view_delta_24h', 'views_per_hour_avg_24h',
    'chart_label_status',
]

COHORT_DIR = Path("data/raw/rolling_cohorts/JP")
OUT_FILE = Path("data/processed/youtube_cohort_registry_JP.csv")


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def build_registry():
    records_by_key = {}

    # Scan all JP batch manifests in chronological order
    manifests = sorted(COHORT_DIR.glob("*/manifest.json"))
    print(f"Found {len(manifests)} JP cohort batch manifests.")

    for m_path in manifests:
        manifest = load_json(m_path)
        batch_id = manifest["batch_id"]
        region = manifest["region_code"]
        b_dir = m_path.parent

        t0_path = b_dir / "t0.json"
        if not t0_path.is_file():
            print(f"Skipping {batch_id}: missing t0.json")
            continue

        t0_data = load_json(t0_path)
        t0_records = t0_data.get("records", [])

        # Index T24 records if present
        t24_by_id = {}
        t24_path = b_dir / "t24.json"
        if t24_path.is_file():
            t24_data = load_json(t24_path)
            for r in t24_data.get("records", []):
                t24_by_id[r["video_id"]] = r

        for r in t0_records:
            vid = str(r["video_id"]).strip()
            key = (vid, region)

            t24_rec = t24_by_id.get(vid, {})

            row = {
                'video_id': vid,
                'region_code': region,
                'batch_id': batch_id,
                'title': r.get('title'),
                'channel_id': r.get('channel_id'),
                'channel_title': r.get('channel_title'),
                'category_id': r.get('category_id'),
                'published_at': r.get('published_at'),
                'first_seen_at': r.get('first_seen_at'),
                'discovery_source': r.get('discovery_source'),
                'seed_region': r.get('seed_region'),
                'region_availability': r.get('region_availability'),
                't0_collected_at': r.get('collected_at'),
                't0_view_count': r.get('view_count'),
                't0_like_count': r.get('like_count'),
                't0_comment_count': r.get('comment_count'),
                't24_collected_at': t24_rec.get('t24_collected_at'),
                't24_view_count': t24_rec.get('t24_view_count'),
                't24_like_count': t24_rec.get('t24_like_count'),
                't24_comment_count': t24_rec.get('t24_comment_count'),
                'hours_elapsed': t24_rec.get('hours_elapsed'),
                'view_delta_24h': t24_rec.get('view_delta_24h'),
                'views_per_hour_avg_24h': t24_rec.get('views_per_hour_avg_24h'),
                'chart_label_status': None,
            }
            records_by_key[key] = row

    df = pd.DataFrame(list(records_by_key.values()), columns=REGISTRY_COLUMNS)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE, index=False, encoding="utf-8")
    print(f"Successfully generated: {OUT_FILE}")
    print(f"Total rows: {len(df)}")
    print(f"Unique video_id: {df['video_id'].nunique()}")
    print(f"Unique channels: {df['channel_id'].nunique()}")
    print(f"Completed T24 videos: {df['t24_collected_at'].notna().sum()}")
    return df


if __name__ == "__main__":
    build_registry()