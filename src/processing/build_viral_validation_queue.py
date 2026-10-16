from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

VIRAL_PATH = Path('data/processed/youtube_viral_candidates_vn.csv')
CURRENT_CHART_PATH = Path('data/processed/youtube_current_trending_vn.csv')
OUTPUT_PATH = Path('data/processed/youtube_viral_validation_queue_vn.csv')


def num(series):
    return pd.to_numeric(series, errors='coerce')


def build_queue(top_n: int) -> pd.DataFrame:
    if not VIRAL_PATH.exists():
        raise FileNotFoundError(f'Missing input: {VIRAL_PATH}')

    viral = pd.read_csv(VIRAL_PATH)
    if 'viral_score' not in viral.columns:
        raise ValueError('viral_score column is missing from viral candidates dataset.')

    viral['viral_score'] = num(viral['viral_score'])
    viral = viral.sort_values('viral_score', ascending=False).copy()

    top_viral = viral.head(top_n).copy()
    top_viral['queue_reason'] = 'top_viral_candidate'

    current_chart = pd.DataFrame()
    current_ids = set()
    chart_rank_map = {}

    if CURRENT_CHART_PATH.exists():
        current_chart = pd.read_csv(CURRENT_CHART_PATH)
        if 'video_id' in current_chart.columns:
            current_ids = set(current_chart['video_id'].dropna().astype(str))
        if {'video_id', 'trending_rank'}.issubset(current_chart.columns):
            chart_rank_map = (
                current_chart.dropna(subset=['video_id'])
                .assign(video_id=lambda x: x['video_id'].astype(str))
                .set_index('video_id')['trending_rank']
                .to_dict()
            )

    top_viral['youtube_charted'] = top_viral['video_id'].astype(str).isin(current_ids).astype(int)
    top_viral['youtube_chart_rank'] = top_viral['video_id'].astype(str).map(chart_rank_map)

    selected_ids = set(top_viral['video_id'].astype(str))
    extra_chart = pd.DataFrame()

    if not current_chart.empty and 'video_id' in current_chart.columns:
        extra_chart = current_chart[~current_chart['video_id'].astype(str).isin(selected_ids)].copy()
        if not extra_chart.empty:
            metrics = [
                'video_id', 'viral_score', 'signal_count', 'views_per_hour',
                'view_growth_pct_per_hour', 'likes_per_hour', 'comments_per_hour',
                'first_seen_at', 'discovery_batch_id', 'discovery_source',
                'discovery_query', 'youtube_charted_at_discovery'
            ]
            metrics = [c for c in metrics if c in viral.columns]
            if metrics:
                lookup = viral[metrics].drop_duplicates('video_id')
                extra_chart = extra_chart.merge(lookup, on='video_id', how='left', suffixes=('', '_viral'))
                for col in metrics:
                    if col == 'video_id':
                        continue
                    vcol = f'{col}_viral'
                    if vcol in extra_chart.columns:
                        if col not in extra_chart.columns:
                            extra_chart[col] = extra_chart[vcol]
                        else:
                            extra_chart[col] = extra_chart[col].where(extra_chart[col].notna(), extra_chart[vcol])
                        extra_chart = extra_chart.drop(columns=[vcol])

            extra_chart['queue_reason'] = 'youtube_charted_comparison'
            extra_chart['youtube_charted'] = 1
            if 'trending_rank' in extra_chart.columns:
                extra_chart['youtube_chart_rank'] = extra_chart['trending_rank']
            else:
                extra_chart['youtube_chart_rank'] = pd.NA

    queue = pd.concat([top_viral, extra_chart], ignore_index=True, sort=False)

    defaults = {
        'region_code': 'VN', 'collected_at': pd.NA, 'viral_score': pd.NA,
        'signal_count': pd.NA, 'views_per_hour': pd.NA,
        'view_growth_pct_per_hour': pd.NA, 'likes_per_hour': pd.NA,
        'comments_per_hour': pd.NA, 'first_seen_at': pd.NA,
        'discovery_batch_id': pd.NA, 'discovery_source': pd.NA,
        'discovery_query': pd.NA, 'youtube_charted_at_discovery': pd.NA,
        'video_url': pd.NA, 'title': pd.NA,
    }
    for col, default in defaults.items():
        if col not in queue.columns:
            queue[col] = default

    # Third-party evidence placeholders. NOT_CHECKED is not the same as False.
    for prefix in ['vidiq', 'google_trends', 'socialblade']:
        queue[f'{prefix}_status'] = 'NOT_CHECKED'
        queue[f'{prefix}_metric'] = pd.NA
        queue[f'{prefix}_checked_at'] = pd.NA
        queue[f'{prefix}_evidence'] = pd.NA

    queue['external_signal_count'] = 0
    queue['time_match_status'] = 'NOT_CHECKED'
    queue['evidence_notes'] = pd.NA

    viral_present = num(queue['viral_score']).notna()
    charted = num(queue['youtube_charted']).fillna(0).eq(1)

    queue['validation_status'] = 'REVIEW'
    queue.loc[viral_present & ~charted, 'validation_status'] = 'LEVEL_1_VIRAL_CANDIDATE'
    queue.loc[viral_present & charted, 'validation_status'] = 'LEVEL_3_YOUTUBE_CHARTED_GROWTH_CONFIRMED'
    queue.loc[~viral_present & charted, 'validation_status'] = 'CHART_ONLY_COMPARISON'

    preferred = [
        'video_id', 'title', 'video_url', 'region_code', 'collected_at',
        'queue_reason', 'viral_score', 'signal_count', 'views_per_hour',
        'view_growth_pct_per_hour', 'likes_per_hour', 'comments_per_hour',
        'youtube_charted', 'youtube_chart_rank', 'youtube_charted_at_discovery',
        'first_seen_at', 'discovery_batch_id', 'discovery_source',
        'discovery_query', 'vidiq_status', 'vidiq_metric', 'vidiq_checked_at',
        'vidiq_evidence', 'google_trends_status', 'google_trends_metric',
        'google_trends_checked_at', 'google_trends_evidence',
        'socialblade_status', 'socialblade_metric', 'socialblade_checked_at',
        'socialblade_evidence', 'external_signal_count', 'time_match_status',
        'validation_status', 'evidence_notes'
    ]
    preferred = [c for c in preferred if c in queue.columns]
    remaining = [c for c in queue.columns if c not in preferred]
    queue = queue[preferred + remaining]
    queue = queue.drop_duplicates(subset=['video_id'], keep='first').copy()

    order = {
        'LEVEL_3_YOUTUBE_CHARTED_GROWTH_CONFIRMED': 0,
        'LEVEL_1_VIRAL_CANDIDATE': 1,
        'CHART_ONLY_COMPARISON': 2,
        'REVIEW': 3,
    }
    queue['_order'] = queue['validation_status'].map(order).fillna(9)
    queue = queue.sort_values(['_order', 'viral_score'], ascending=[True, False], na_position='last')
    queue = queue.drop(columns=['_order'])
    return queue


def main():
    parser = argparse.ArgumentParser(description='Build VN viral validation queue.')
    parser.add_argument('--top-n', type=int, default=20)
    args = parser.parse_args()
    if args.top_n < 1:
        raise ValueError('--top-n must be at least 1')

    queue = build_queue(args.top_n)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    queue.to_csv(OUTPUT_PATH, index=False, encoding='utf-8-sig')

    print('=' * 68)
    print('VIRAL VALIDATION QUEUE COMPLETED')
    print(f'Rows in validation queue: {len(queue)}')
    print(f'Top viral candidates requested: {args.top_n}')
    print(f"YouTube-charted rows in queue: {int(num(queue['youtube_charted']).fillna(0).sum())}")
    print('\nValidation status counts:')
    print(queue['validation_status'].value_counts(dropna=False).to_string())
    print(f'\nSaved to: {OUTPUT_PATH}')
    print('=' * 68)

    cols = ['video_id', 'title', 'viral_score', 'views_per_hour',
            'youtube_charted', 'youtube_chart_rank', 'validation_status']
    cols = [c for c in cols if c in queue.columns]
    print('\nValidation queue preview:')
    print(queue[cols].head(25).to_string(index=False))


if __name__ == '__main__':
    main()
