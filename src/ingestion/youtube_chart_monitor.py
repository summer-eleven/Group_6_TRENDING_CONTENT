'''Monitor videos.list(chart=mostPopular) independently of legacy hourly snapshots.

Examples (from the repository root):
  uv run python -m src.ingestion.youtube_chart_monitor capture --region VN --max-pages 10
  uv run python -m src.ingestion.youtube_chart_monitor capture --region VN --max-pages 10 --apply
  uv run python -m src.ingestion.youtube_chart_monitor sync --file data/raw/chart_monitor/VN/<file>.json --apply

PLAN does not call YouTube or modify local files. Capture --apply calls YouTube,
saves JSON locally, uploads it to MinIO, and inserts SQL chart runs and entries.
If MinIO/SQL fails, the local JSON remains available for 'sync --apply'.
No non-trending labels are produced. Coverage is limited to the API chart scope.
'''

import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from src.ingestion.upload_raw_to_minio import upload_file_to_minio
from src.utils.db_connection import get_connection

load_dotenv()
API_URL = 'https://www.googleapis.com/youtube/v3/videos'
ROOT = Path('data/raw/chart_monitor')
REGIONS = ('VN', 'US', 'JP')


def utc_now():
    return datetime.now(timezone.utc)


def naive_utc(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamp must include its UTC offset')
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    try:
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def capture(region, category_id, max_pages):
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        raise RuntimeError('YOUTUBE_API_KEY is missing in .env')

    started = utc_now()
    run_id = started.strftime('%Y%m%d_%H%M%S_%f') + '_' + uuid.uuid4().hex[:8]
    token = None
    rows = []
    seen = set()
    pages = []
    used_tokens = set()
    has_more = False

    with requests.Session() as session:
        for page_index in range(max_pages):
            params = {
                'part': 'snippet',
                'chart': 'mostPopular',
                'regionCode': region,
                'maxResults': 50,
                'key': api_key,
            }
            if category_id != '0':
                params['videoCategoryId'] = category_id
            if token:
                if token in used_tokens:
                    raise RuntimeError('Repeated nextPageToken: refusing infinite pagination')
                used_tokens.add(token)
                params['pageToken'] = token

            try:
                response = session.get(API_URL, params=params, timeout=40)
            except requests.RequestException:
                # Avoid leaking API key in exception text (request URL).
                raise RuntimeError('YouTube request failed (network/timeout); check connectivity') from None
            if not response.ok:
                try:
                    reason = response.json().get('error', {}).get('message', '')
                except (ValueError, AttributeError):
                    reason = ''
                # Intentionally do not print response URL: it contains the API key.
                raise RuntimeError(f'YouTube videos.list HTTP {response.status_code}: {reason[:300]}')
            data = response.json()
            raw_items = data.get('items', [])
            if not isinstance(raw_items, list):
                raise RuntimeError('YouTube API response items is not a list')
            page_time = utc_now().isoformat()
            pages.append({
                'page_number': page_index + 1,
                'fetched_at_utc': page_time,
                'items_returned': len(raw_items),
                'page_info': data.get('pageInfo', {}),
                'raw_api_response': data,
            })
            for offset, video in enumerate(raw_items):
                vid = video.get('id')
                if not isinstance(vid, str) or not vid or vid in seen:
                    continue
                seen.add(vid)
                snip = video.get('snippet') or {}
                rows.append({
                    'video_id': vid,
                    'chart_rank': page_index * 50 + offset + 1,
                    'title': snip.get('title'),
                    'channel_id': snip.get('channelId'),
                    'video_category_id': snip.get('categoryId'),
                })
            token = data.get('nextPageToken')
            has_more = bool(token)
            if not token:
                break

    finished = utc_now()
    payload = {
        'schema_version': 1,
        'run_id': run_id,
        'region_code': region,
        'chart_name': 'mostPopular',
        'requested_category_id': category_id,
        'collected_at_utc': started.isoformat(),
        'completed_at_utc': finished.isoformat(),
        'pages_fetched': len(pages),
        'requested_max_pages': max_pages,
        'items_count': len(rows),
        'next_page_available': has_more,
        'fully_paginated': not has_more,
        'pages': pages,
        'entries': rows,
        'interpretation': 'Observed chart membership only; absence is not proof of non-viral or non-trending.',
    }
    dest = ROOT / region / f'chart_{region}_{run_id}.json'
    atomic_write(dest, payload)
    print(f'CAPTURE SAVED: {dest} | videos={len(rows)} | pages={len(pages)} | more_pages={has_more}')
    return dest


def sync(path):
    path = Path(path)
    payload = json.loads(path.read_text(encoding='utf-8'))
    expected = {
        'run_id', 'region_code', 'chart_name', 'requested_category_id',
        'collected_at_utc', 'completed_at_utc', 'pages_fetched',
        'items_count', 'next_page_available', 'entries',
    }
    if expected - payload.keys():
        raise ValueError(f'Missing chart JSON keys: {sorted(expected - payload.keys())}')
    if payload['region_code'] not in REGIONS or payload['chart_name'] != 'mostPopular':
        raise ValueError('Unexpected chart scope')
    entries = payload['entries']
    if payload['items_count'] != len(entries):
        raise ValueError('Chart JSON items_count mismatch')
    if len({v['video_id'] for v in entries}) != len(entries):
        raise ValueError('Chart JSON contains duplicate video IDs')

    object_key = f"chart_monitor/{payload['region_code']}/{path.name}"
    upload_file_to_minio(str(path), object_key)

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT 1 FROM dbo.youtube_chart_runs WHERE run_id = ?', payload['run_id'])
        if cursor.fetchone():
            print(f'ALREADY SYNCED: run_id={payload["run_id"]} (no duplicate SQL rows)')
            return
        cursor.execute('''
            INSERT INTO dbo.youtube_chart_runs
            (run_id, region_code, chart_name, requested_category_id,
             collected_at_utc, completed_at_utc, pages_fetched, items_count,
             next_page_available, minio_object_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            payload['run_id'], payload['region_code'], payload['chart_name'],
            str(payload['requested_category_id']), naive_utc(payload['collected_at_utc']),
            naive_utc(payload['completed_at_utc']), int(payload['pages_fetched']),
            len(entries), int(bool(payload['next_page_available'])), object_key,
        ))
        if entries:
            data_rows = [
                (payload['run_id'], entry['video_id'], int(entry['chart_rank']),
                 str(entry['title'])[:500] if entry.get('title') is not None else None,
                 entry.get('channel_id'), entry.get('video_category_id'))
                for entry in entries
            ]
            cursor.fast_executemany = True
            cursor.executemany('''
                INSERT INTO dbo.youtube_chart_entries
                (run_id, video_id, chart_rank, title, channel_id, video_category_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', data_rows)
        connection.commit()
        print(f'SYNC SUCCESS: run_id={payload["run_id"]} | entries={len(entries)} | object={object_key}')
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description='Independent YouTube mostPopular Chart Monitor')
    commands = parser.add_subparsers(dest='command', required=True)
    cap = commands.add_parser('capture', help='PLAN by default; --apply calls API and syncs')
    cap.add_argument('--region', choices=REGIONS, required=True)
    cap.add_argument('--max-pages', type=int, default=10)
    cap.add_argument('--category-id', default='0', help='0 = default chart; otherwise category-specific chart')
    cap.add_argument('--apply', action='store_true')
    resume = commands.add_parser('sync', help='Upload a saved capture and sync SQL')
    resume.add_argument('--file', required=True, type=Path)
    resume.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    if args.command == 'capture':
        if not 1 <= args.max_pages <= 20:
            parser.error('--max-pages must be between 1 and 20')
        if not args.apply:
            print(f'PLAN: region={args.region} chart=mostPopular category={args.category_id} max_pages={args.max_pages}')
            print('No API requests, files, SQL, or MinIO changes. Add --apply to capture.')
            return
        dest = capture(args.region, args.category_id, args.max_pages)
        try:
            sync(dest)
        except Exception as error:
            print(f'SYNC FAILED, local JSON preserved: {dest}')
            print(f'After fixing the service, run: uv run python -m src.ingestion.youtube_chart_monitor sync --file "{dest}" --apply')
            raise SystemExit(str(error)) from error
    else:
        if not args.apply:
            print(f'PLAN: sync local JSON {args.file}. No writes until --apply.')
            return
        sync(args.file)


if __name__ == '__main__':
    main()
