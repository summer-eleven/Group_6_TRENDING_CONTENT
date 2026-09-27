# Report 2 - Technical Evidence

## Infrastructure

- `docker_services.png`
  - MinIO and SQL Server are running through Docker Compose.

## MinIO Data Lake

- `minio_raw.png`
  - Raw YouTube data stored under `trending-content/raw/`.

- `minio_processed.png`
  - Processed YouTube data stored under `trending-content/processed/`.

## SQL Server Verification

- `sql_row_count.png`
  - Verifies master and snapshot row counts.

- `sql_duplicate_check.png`
  - Confirms no duplicate snapshot composite keys.

- `sql_null_check.png`
  - Confirms required snapshot fields are not null.

- `sql_sample_records.png`
  - Shows sample snapshot records stored in SQL Server.

- `sql_snapshot_count_8066.png`
  - Confirms 8,066 historical snapshot records are stored in SQL Server.

## Snapshot Pipeline

- `history_8066.png`
  - Confirms the historical dataset contains 8,066 records after deduplication.

## Current Data Volume

- Unique videos: 2,011
- Trending videos: 1,011
- Control videos: 1,000
- Historical records: 8,066
- Target: 10,000+ records