"""Safely transfer local Rolling Cohort T0/T24 observations to MinIO + SQL.

Default mode is READ-ONLY PLAN: no network requests and no file modifications.
Use --apply to upload raw JSON to MinIO, insert new cohort observations in SQL,
and update a separate per-region CSV registry (NOT the legacy labelled master).

Examples, run from repository root:
  uv run python -m src.processing.sync_rolling_cohort --manifest data/raw/rolling_cohorts/VN/<batch_id>/manifest.json --phase T0
  uv run python -m src.processing.sync_rolling_cohort --manifest data/raw/rolling_cohorts/VN/<batch_id>/manifest.json --phase T0 --apply
  uv run python -m src.processing.sync_rolling_cohort --manifest data/raw/rolling_cohorts/VN/<batch_id>/manifest.json --phase T24 --apply

Important: SQL dbo.youtube_cohort_observations must exist with a UNIQUE constraint
(batch_id, video_id, phase). Existing dbo.youtube_video_snapshots is unchanged.
"""

import argparse
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.ingestion.rolling_cohort import load_json

REGISTRY_COLUMNS = [
    'video_id', 'region_code', 'batch_id', 'title', 'channel_id',
    'channel_title', 'category_id', 'published_at', 'first_seen_at',
    'discovery_source', 'seed_region', 'region_availability',
    't0_collected_at', 't0_view_count', 't0_like_count', 't0_comment_count',
    't24_collected_at', 't24_view_count', 't24_like_count', 't24_comment_count',
    'hours_elapsed', 'view_delta_24h', 'views_per_hour_avg_24h',
    'chart_label_status',
]


def parse_utc(value, field):
    if value is None or str(value).strip() == '':
        raise ValueError(f'Missing {field}')
    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError(f'{field} must have an explicit timezone (UTC)')
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def read_phase(manifest_path, phase):
    manifest = load_json(manifest_path)
    batch_id = manifest.get('batch_id')
    region = manifest.get('region_code')
    if not batch_id or region not in ('VN', 'US', 'JP'):
        raise ValueError('Manifest missing valid batch_id or region_code')
    if len(batch_id) > 80:
        raise ValueError('batch_id too long for database')
    json_path = manifest_path.parent / ('t0.json' if phase == 'T0' else 't24.json')
    if not json_path.exists():
        raise FileNotFoundError(f'Observation file not found: {json_path}')
    payload = load_json(json_path)
    if payload.get('batch_id') != batch_id or payload.get('region_code') != region:
        raise ValueError('Manifest and observation file refer to different batches')
    records = payload.get('records')
    if not isinstance(records, list) or not records:
        raise ValueError('Observation file must have nonempty records list')
    seen = set()
    for row in records:
        vid = str(row.get('video_id', '')).strip()
        if not vid or len(vid) > 20 or vid in seen:
            raise ValueError(f'Missing, invalid or duplicate video_id: {vid}')
        seen.add(vid)
        if row.get('region_code') != region or row.get('discovery_batch_id') != batch_id:
            raise ValueError(f'Batch/region mismatch for video {vid}')
        parse_utc(row['collected_at'], 'collected_at')
        if phase == 'T24':
            parse_utc(row['t24_collected_at'], 't24_collected_at')
    return manifest, json_path, records


def to_int(value):
    return None if value is None or value == '' else int(value)


def sql_rows(manifest, records, phase, object_path):
    items = []
    for r in records:
        available = True if phase == 'T0' else (r.get('t24_video_available') is True)
        timestamp = r['collected_at'] if phase == 'T0' else r['t24_collected_at']
        def metric(name):
            key = name if phase == 'T0' else 't24_' + name
            return to_int(r.get(key))
        items.append((
            manifest['batch_id'], r['video_id'], manifest['region_code'],
            phase, parse_utc(timestamp, 'observation timestamp'),
            metric('view_count'), metric('like_count'), metric('comment_count'),
            int(available), object_path,
        ))
    return items


def registry_rows(manifest, records, phase):
    out = []
    for r in records:
        base = {
            'video_id': str(r['video_id']),
            'region_code': manifest['region_code'],
            'batch_id': manifest['batch_id'],
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
            'chart_label_status': None,  # Never overwrite an existing verified chart label
        }
        if phase == 'T24':
            base.update({
                't24_collected_at': r.get('t24_collected_at'),
                't24_view_count': r.get('t24_view_count'),
                't24_like_count': r.get('t24_like_count'),
                't24_comment_count': r.get('t24_comment_count'),
                'hours_elapsed': r.get('hours_elapsed'),
                'view_delta_24h': r.get('view_delta_24h'),
                'views_per_hour_avg_24h': r.get('views_per_hour_avg_24h'),
            })
        out.append(base)
    return out


def upsert_registry(path, manifest, records, phase):
    """CSV written atomically after SQL commit; rerunning fills missing CSV rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    old = (pd.read_csv(path, dtype={'video_id': 'string', 'region_code': 'string'})
           if path.exists() else pd.DataFrame(columns=REGISTRY_COLUMNS))
    new = pd.DataFrame(registry_rows(manifest, records, phase))
    # Preserve values already recorded from the other phase of this same video.
    both = pd.concat([old, new], ignore_index=True)
    for col in REGISTRY_COLUMNS:
        if col not in both.columns:
            both[col] = pd.NA
    # The newest non-empty data wins, but T24 never deletes T0 values.
    both = (both.groupby(['video_id', 'region_code'], as_index=False, sort=False)
            .agg({c: (lambda series: next((v for v in reversed(series.tolist()) if pd.notna(v)), pd.NA))
                  for c in REGISTRY_COLUMNS if c not in ('video_id', 'region_code')}))
    both['chart_label_status'] = both['chart_label_status'].fillna('NOT_EVALUATED')
    with tempfile.NamedTemporaryFile('w', suffix='.csv', prefix='.cohort_',
                                     dir=path.parent, encoding='utf-8-sig',
                                     newline='', delete=False) as f:
        tmp = Path(f.name)
    try:
        both.to_csv(tmp, index=False, encoding='utf-8-sig')
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return len(both)


def insert_sql(manifest, records, phase, object_path):
    from src.utils.db_connection import get_connection
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''SELECT video_id FROM dbo.youtube_cohort_observations
                          WHERE batch_id = ? AND phase = ?''', manifest['batch_id'], phase)
        existing = {str(row[0]) for row in cursor.fetchall()}
        proposed = [r for r in sql_rows(manifest, records, phase, object_path)
                    if str(r[1]) not in existing]
        if proposed:
            cursor.fast_executemany = True
            cursor.executemany('''
                INSERT INTO dbo.youtube_cohort_observations
                (batch_id, video_id, region_code, phase, observed_at_utc,
                 view_count, like_count, comment_count, video_available, minio_object_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', proposed)
        conn.commit()
        return len(proposed), len(existing)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Safe sync Rolling Cohort to MinIO, SQL and separate CSV registry')
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--phase', choices=['T0', 'T24'], required=True)
    parser.add_argument('--registry-root', type=Path, default=Path('data/processed'))
    parser.add_argument('--apply', action='store_true', help='Perform writes (default is read-only PLAN)')
    args = parser.parse_args()
    manifest, json_path, records = read_phase(args.manifest, args.phase)
    region = manifest['region_code']
    batch_id = manifest['batch_id']
    object_path = f'rolling_cohorts/{region}/{batch_id}/{args.phase.lower()}.json'
    registry = args.registry_root / f'youtube_cohort_registry_{region}.csv'
    print('MODE:', 'APPLY' if args.apply else 'PLAN (no changes)')
    print('Batch:', batch_id, '| Region:', region, '| Phase:', args.phase)
    print('Records:', len(records), '| Unique IDs:', len({r['video_id'] for r in records}))
    print('Local source:', json_path)
    print('MinIO object:', object_path)
    print('SQL table: dbo.youtube_cohort_observations')
    print('CSV registry:', registry)
    print('Legacy master and legacy snapshot tables will NOT be modified.')
    if not args.apply:
        return
    # Upload first. In case SQL fails, rerun re-uploads the same object safely.
    from src.ingestion.upload_raw_to_minio import upload_file_to_minio
    upload_file_to_minio(json_path, object_path)
    inserted, existing = insert_sql(manifest, records, args.phase, object_path)
    total = upsert_registry(registry, manifest, records, args.phase)
    print('SQL newly inserted observations:', inserted)
    print('SQL already present for batch and phase:', existing)
    print('CSV registry (unique video + region pairs):', total)
    print('SYNC SUCCESS. Running the same command again will not duplicate SQL rows.')


if __name__ == '__main__':
    main()
