"""Build an observational RQ1 dataset from the VN/US/JP rolling cohorts.

Research question: Is upload during office hours associated with the chance that
an enrolled video is observed on the *requested YouTube mostPopular chart* in
the first 24 hours after its T0 observation?

Only an observed match is positive. A negative outcome is assigned ONLY when
all 24 elapsed hourly bins contain at least one fully-paginated chart capture.
Otherwise the outcome stays unknown (NA); this avoids invented negatives.

Inputs:  data/processed/youtube_cohort_registry_<REGION>.csv (metadata),
         SQL dbo.youtube_cohort_observations (T0 and T24 measurements),
         SQL dbo.youtube_chart_runs and dbo.youtube_chart_entries.

Default mode is read-only PLAN (reads CSV and SQL, NO API or data writes).
Use --apply to write data/processed/rq1_youtube_cohort_<REGION>.csv.

From project root:
  uv run python -m src.processing.build_rq1_dataset --region VN
  uv run python -m src.processing.build_rq1_dataset --region VN --apply
"""

import argparse
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.db_connection import get_connection

REGIONS = ('VN', 'US', 'JP')
LOCAL_TZ = {'VN': 'Asia/Ho_Chi_Minh', 'US': 'America/New_York', 'JP': 'Asia/Tokyo'}
REQUIRED_REGISTRY = {
    'video_id', 'region_code', 'batch_id', 'channel_id', 'published_at',
    't0_collected_at',
}


def query_frame(cursor, sql, params=()):
    cursor.execute(sql, *params)
    column_names = [col[0] for col in cursor.description]
    return pd.DataFrame.from_records(cursor.fetchall(), columns=column_names)


def read_observations_and_chart(region):
    """Read authoritative observations and chart history; never modify SQL."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        observations = query_frame(cursor, '''
            SELECT batch_id, video_id, region_code, phase, observed_at_utc,
                   view_count, like_count, comment_count, video_available
            FROM dbo.youtube_cohort_observations
            WHERE region_code = ? AND phase IN ('T0', 'T24')
        ''', (region,))
        chart_runs = query_frame(cursor, '''
            SELECT run_id, collected_at_utc, completed_at_utc,
                   pages_fetched, items_count, next_page_available
            FROM dbo.youtube_chart_runs
            WHERE region_code = ? AND chart_name = 'mostPopular'
              AND requested_category_id = '0'
        ''', (region,))
        chart_entries = query_frame(cursor, '''
            SELECT e.run_id, e.video_id, e.chart_rank, r.collected_at_utc
            FROM dbo.youtube_chart_entries e
            JOIN dbo.youtube_chart_runs r ON r.run_id = e.run_id
            WHERE r.region_code = ? AND r.chart_name = 'mostPopular'
              AND r.requested_category_id = '0'
        ''', (region,))
        return observations, chart_runs, chart_entries
    finally:
        conn.close()


def build_dataset(registry, observations, chart_runs, chart_entries, region, now=None):
    """Pure transformation for testing; SQL access is outside this function."""
    now = pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
    if now.tzinfo is None:
        raise ValueError('now must be timezone-aware')
    now = now.tz_convert('UTC')

    missing = REQUIRED_REGISTRY - set(registry.columns)
    if missing:
        raise ValueError(f'Registry lacks required columns: {sorted(missing)}')
    df = registry.loc[registry['region_code'].astype(str) == region].copy()
    if df.empty:
        raise ValueError(f'No registry records for {region}')
    df['video_id'] = df['video_id'].astype(str)
    df['batch_id'] = df['batch_id'].astype(str)
    if df['video_id'].duplicated().any():
        raise ValueError('Registry has duplicate video_id rows; resolve before analysis')

    df['published_at_utc'] = pd.to_datetime(df['published_at'], utc=True, errors='coerce')
    df['t0_collected_at_utc'] = pd.to_datetime(df['t0_collected_at'], utc=True, errors='coerce')
    if df['published_at_utc'].isna().any() or df['t0_collected_at_utc'].isna().any():
        raise ValueError('Missing or invalid published_at/t0_collected_at in registry')

    local = df['published_at_utc'].dt.tz_convert(LOCAL_TZ[region])
    df['published_at_local'] = local.dt.strftime('%Y-%m-%d %H:%M:%S%z')
    df['upload_hour_local'] = local.dt.hour
    df['upload_weekday_local'] = local.dt.dayofweek  # Monday=0
    is_office = (local.dt.dayofweek < 5) & local.dt.hour.between(8, 16)
    df['upload_period'] = np.where(is_office, 'OFFICE_HOURS', 'NON_OFFICE_HOURS')
    df['video_age_at_t0_hours'] = (
        df['t0_collected_at_utc'] - df['published_at_utc']
    ).dt.total_seconds() / 3600
    df['primary_fresh_24h'] = df['video_age_at_t0_hours'].between(0, 24)
    df['window_end_utc'] = df['t0_collected_at_utc'] + pd.Timedelta(hours=24)
    df['window_ended'] = now >= df['window_end_utc']

    if observations.empty:
        raise ValueError('No matching rows in dbo.youtube_cohort_observations')

    # The registry already contains some t0_* / t24_* measurement columns.
    # SQL observations are authoritative here. Drop only those overlapping
    # measurements before merging, to avoid Pandas _x/_y suffixes and the
    # subsequent KeyError for t0_view_count / t24_view_count.
    measurement_fields = (
        'observed_at_utc', 'view_count', 'like_count',
        'comment_count', 'video_available'
    )
    sql_measurement_names = {
        f'{phase}_{field}'
        for phase in ('t0', 't24')
        for field in measurement_fields
    }
    overlapping = sorted(sql_measurement_names.intersection(df.columns))
    if overlapping:
        df = df.drop(columns=overlapping)

    ob = observations.copy()
    for c in ('batch_id', 'video_id'):
        ob[c] = ob[c].astype(str)
    ob['observed_at_utc'] = pd.to_datetime(ob['observed_at_utc'], utc=True, errors='coerce')
    if ob.duplicated(['batch_id', 'video_id', 'phase']).any():
        raise ValueError('Duplicate SQL observations per batch/video/phase')

    for phase in ('T0', 'T24'):
        subset = ob.loc[ob['phase'] == phase, [
            'batch_id', 'video_id', 'observed_at_utc',
            'view_count', 'like_count', 'comment_count', 'video_available'
        ]].copy()
        subset = subset.rename(columns={
            key: f'{phase.lower()}_{key}'
            for key in ('observed_at_utc', 'view_count', 'like_count',
                        'comment_count', 'video_available')
        })
        df = df.merge(subset, how='left', on=['batch_id', 'video_id'], validate='one_to_one')

    # SQL T0 should match the registry's UTC timestamp; differences could
    # indicate a wrong registry entry or batch and must not be silently ignored.
    mismatched = (df['t0_observed_at_utc'].isna() |
                  ((df['t0_observed_at_utc'] - df['t0_collected_at_utc'])
                   .dt.total_seconds().abs() > 2))
    if mismatched.any():
        raise ValueError(f'{int(mismatched.sum())} registry rows have missing/mismatched SQL T0 observations')

    df['t24_ready'] = df['t24_observed_at_utc'].notna()
    df['actual_t24_hours'] = (
        df['t24_observed_at_utc'] - df['t0_collected_at_utc']
    ).dt.total_seconds() / 3600
    v0 = pd.to_numeric(df['t0_view_count'], errors='coerce')
    v24 = pd.to_numeric(df['t24_view_count'], errors='coerce')
    df['view_delta_t24'] = v24 - v0
    valid_interval = df['actual_t24_hours'] > 0
    df['views_per_hour_t24'] = np.where(
        valid_interval, df['view_delta_t24'] / df['actual_t24_hours'], np.nan
    )

    # Only *fully paginated* default-category chart runs qualify as coverage.
    # Partial runs may nevertheless establish a positive observation.
    runs = chart_runs.copy()
    if not runs.empty:
        runs['collected_at_utc'] = pd.to_datetime(runs['collected_at_utc'], utc=True, errors='coerce')
        runs = runs.dropna(subset=['collected_at_utc'])
        runs['next_page_available'] = pd.to_numeric(runs['next_page_available'], errors='coerce')
        full_runs = runs.loc[runs['next_page_available'] == 0].copy()
    else:
        full_runs = runs.copy()

    def as_sorted_naive_utc_numpy(times):
        if len(times) == 0:
            return np.array([], dtype='datetime64[ns]')
        return np.sort(times.dt.tz_convert('UTC').dt.tz_localize(None).to_numpy(dtype='datetime64[ns]'))

    all_chart_times = as_sorted_naive_utc_numpy(runs['collected_at_utc']) if not runs.empty else np.array([], dtype='datetime64[ns]')
    full_chart_times = as_sorted_naive_utc_numpy(full_runs['collected_at_utc']) if not full_runs.empty else np.array([], dtype='datetime64[ns]')

    def coverage_counts(t0):
        t0_naive = t0.tz_convert('UTC').tz_localize(None).to_datetime64()
        t1_naive = t0_naive + np.timedelta64(24, 'h')
        i0, i1 = np.searchsorted(all_chart_times, (t0_naive, t1_naive))
        j0, j1 = np.searchsorted(full_chart_times, (t0_naive, t1_naive))
        complete = full_chart_times[j0:j1]
        if len(complete):
            elapsed_hours = ((complete - t0_naive) / np.timedelta64(1, 'h')).astype(int)
            bins = len(np.unique(elapsed_hours))
        else:
            bins = 0
        return int(i1 - i0), int(j1 - j0), int(bins)

    counts = [coverage_counts(t0) for t0 in df['t0_collected_at_utc']]
    df['chart_runs_in_window'] = [x[0] for x in counts]
    df['full_chart_runs_in_window'] = [x[1] for x in counts]
    df['chart_hour_bins_covered'] = [x[2] for x in counts]
    df['chart_coverage_ratio'] = df['chart_hour_bins_covered'] / 24.0
    df['chart_coverage_complete'] = df['window_ended'] & df['chart_hour_bins_covered'].eq(24)
    df['chart_coverage_status'] = np.select(
        [~df['window_ended'], df['chart_coverage_complete'], df['full_chart_runs_in_window'].eq(0)],
        ['PENDING_WINDOW', 'COMPLETE_24H', 'NO_FULL_CHART_RUNS'],
        default='INCOMPLETE_24H'
    )

    # Chart hits: a positive observation is valid even if overall coverage is
    # incomplete. Scope is category=0/mostPopular only, not every viral video.
    if not chart_entries.empty:
        entries = chart_entries.copy()
        entries['video_id'] = entries['video_id'].astype(str)
        entries['chart_collected_at_utc'] = pd.to_datetime(entries['collected_at_utc'], utc=True, errors='coerce')
        entries['chart_rank'] = pd.to_numeric(entries['chart_rank'], errors='coerce')
        entries = entries.merge(
            df[['video_id', 't0_collected_at_utc', 'window_end_utc']],
            how='inner', on='video_id'
        )
        entries = entries.loc[
            entries['chart_collected_at_utc'].ge(entries['t0_collected_at_utc']) &
            entries['chart_collected_at_utc'].lt(entries['window_end_utc'])
        ]
        positives = entries.groupby('video_id', as_index=False).agg(
            first_chart_seen_utc=('chart_collected_at_utc', 'min'),
            best_chart_rank=('chart_rank', 'min'),
            chart_hit_runs=('run_id', 'nunique')
        )
        df = df.merge(positives, how='left', on='video_id', validate='one_to_one')
    else:
        for c in ('first_chart_seen_utc', 'best_chart_rank', 'chart_hit_runs'):
            df[c] = pd.NA

    has_hit = df['first_chart_seen_utc'].notna()
    labels = pd.Series(pd.NA, index=df.index, dtype='Int64')
    labels.loc[has_hit] = 1
    labels.loc[~has_hit & df['chart_coverage_complete']] = 0
    df['chart_observed_24h'] = labels
    df['chart_label_status'] = np.select(
        [has_hit, df['chart_coverage_complete']],
        ['OBSERVED_POSITIVE', 'OBSERVED_NEGATIVE_FULL_COVERAGE'],
        default='UNKNOWN_INCOMPLETE_COVERAGE'
    )
    df['rq1_analysis_ready'] = (
        df['primary_fresh_24h'] & df['t24_ready'] &
        df['chart_coverage_complete'] & df['chart_observed_24h'].notna()
    )

    columns = [
        'video_id', 'batch_id', 'region_code', 'channel_id', 'channel_title', 'title',
        'published_at_utc', 'published_at_local', 'upload_hour_local', 'upload_weekday_local',
        'upload_period', 't0_collected_at_utc', 'window_end_utc',
        'video_age_at_t0_hours', 'primary_fresh_24h', 'window_ended',
        't0_view_count', 't24_view_count', 'view_delta_t24',
        'actual_t24_hours', 'views_per_hour_t24', 't24_ready',
        'chart_runs_in_window', 'full_chart_runs_in_window',
        'chart_hour_bins_covered', 'chart_coverage_ratio',
        'chart_coverage_complete', 'chart_coverage_status',
        'first_chart_seen_utc', 'best_chart_rank', 'chart_hit_runs',
        'chart_observed_24h', 'chart_label_status', 'rq1_analysis_ready'
    ]
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df[columns].sort_values(['batch_id', 'video_id']).reset_index(drop=True)


def atomic_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', prefix='.rq1_', suffix='.csv',
                                     dir=path.parent, delete=False,
                                     encoding='utf-8-sig', newline='') as f:
        tmp = Path(f.name)
    try:
        df.to_csv(tmp, encoding='utf-8-sig', index=False)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description='Build read-only/optional CSV RQ1 cohort dataset')
    parser.add_argument('--region', choices=REGIONS, required=True)
    parser.add_argument('--registry-path', type=Path)
    parser.add_argument('--output-path', type=Path)
    parser.add_argument('--apply', action='store_true', help='Write output CSV; default is PLAN only')
    args = parser.parse_args()
    registry_path = args.registry_path or Path(f'data/processed/youtube_cohort_registry_{args.region}.csv')
    output_path = args.output_path or Path(f'data/processed/rq1_youtube_cohort_{args.region}.csv')
    registry = pd.read_csv(registry_path, dtype={'video_id': 'string', 'region_code': 'string', 'batch_id': 'string', 'channel_id': 'string'})
    observations, runs, entries = read_observations_and_chart(args.region)
    df = build_dataset(registry, observations, runs, entries, args.region)
    print('MODE:', 'APPLY (writes one analysis CSV only)' if args.apply else 'PLAN (SQL+CSV reads only)')
    print('Region:', args.region)
    print('Cohort video IDs:', len(df))
    print('Unique video IDs:', df['video_id'].nunique())
    print('Fresh within 24h:', int(df['primary_fresh_24h'].sum()))
    print('SQL T24 captured:', int(df['t24_ready'].sum()))
    print('Positive chart observations:', int(df['chart_observed_24h'].eq(1).sum()))
    print('Confirmed chart negatives (complete coverage):', int(df['chart_observed_24h'].eq(0).sum()))
    print('Unknown chart outcomes:', int(df['chart_observed_24h'].isna().sum()))
    print('Complete 24h chart coverage:', int(df['chart_coverage_complete'].sum()))
    print('RQ1 analysis-ready:', int(df['rq1_analysis_ready'].sum()))
    print('Office/Non-office distribution:')
    print(df.groupby('upload_period').agg(videos=('video_id', 'nunique'), fresh_24h=('primary_fresh_24h', 'sum')).to_string())
    print('Output:', output_path)
    if args.apply:
        atomic_csv(df, output_path)
        print('CSV SAVED:', output_path)
    else:
        print('PLAN COMPLETE: output not written. Add --apply to save analysis CSV.')


if __name__ == '__main__':
    main()
