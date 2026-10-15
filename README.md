# Group_6_Trending_Content
## Project Title
Analysis of Factors Influencing YouTube Trending Content
## Project Overview
This project investigates factors that may influence the popularity of YouTube videos.
The Project focuses on two main factors:
- Upload Time
- Negative User Engagement
## Problem Statement
YouTube contains a large amount of video content with different levels of popularity and engagement. However, it is unclear whether the timing of video uploads and negative user engagement are significantly associated with a video's ability to become trending or achieve high visibility.
Therefore, this project aims to analyze YouTube video data to investigate the relationship between these factors and video popularity.
## Research Questions
### RQ1: Upload Time
Does the upload time of a YouTube video affect its probability f becoming trending?
### RQ2: Negative User Engagement
Does negative user engagement affect the virality of a YouTube videos?
## Research Hypotheses
### RQ1: Upload Time
**H₀₁(Null Hypothesis):**
Upload time has no significant affect on the probability of a YouTube video becoming trending.

**H₀₂(Alternative Hypothesis):**
Upload time has a significant affect on the probability of a YouTube video becoming trending.
### RQ2: Negative User Engagement
**H₀₂(Null Hypothesis):**
Negative user engagement has no significant effect on the virality of the YouTube video.

**H₁₂(Alternative Hypothesis):**
Negative user engagement has a significant effect on the virality a YouTube video.

## Week 3 - Data Engineering Pipeline

### Current Pipeline

YouTube Data API
→ Raw JSON
→ MinIO Data Lake
→ Processing
→ SQL Server
→ SQL Verification

## Current Data Volume

- Unique videos: 2,011
- Trending videos: 1,011
- Control videos: 1,000
- Historical records: 10,077
- Long-term target: 100,000 records
- Progress: 10.08%

### Environment Setup

Copy the environment template:

```powershell
Copy-Item .env.example .env
```


## Hourly Snapshot and Viral Detection Pipeline

The project now supports automated hourly YouTube data collection for regional analysis.

### Hourly Snapshot Collection

- Region currently automated: VN
- Collection frequency: every 1 hour
- Automation: Windows Task Scheduler
- Raw snapshot storage: `data/raw/snapshots/VN/`
- Object storage: MinIO
- Structured storage: SQL Server
- Snapshot metrics:
  - View count
  - Like count
  - Comment count
  - Trending status
  - Trending rank
  - Video availability

### Growth Analysis

Hourly snapshots are merged into a historical dataset and used to calculate:

- View growth
- Like growth
- Comment growth
- Views per hour
- Likes per hour
- Comments per hour
- View growth percentage per hour
- Like growth percentage per hour
- Comment growth percentage per hour

Only intervals between 45 and 75 minutes are treated as valid hourly intervals.

### Viral Detection v1

Viral candidates are evaluated using percentile-based signals:

- Views per hour
- View growth percentage per hour
- Likes per hour
- Comments per hour

The percentile signals are combined into a `viral_score`.

Videos must have at least 3 valid signals to be included as viral candidates.

Trending status is kept separate from the viral score so that the system can distinguish between:

- Fast-growing videos that are not currently trending
- Fast-growing videos that are already in YouTube Most Popular

### Current Processing Results

As of the latest completed analysis:

- Unique videos: 2,011
- Historical records: 29,517
- Snapshot files processed: 21
- Snapshot IDs including baseline: 22
- VN viral candidates: 1,276
- Current VN trending videos: 15
- Viral ranking snapshot: 2026-10-01 03:00 UTC
- Viral ranking snapshot in Vietnam time: 2026-10-01 10:00 ICT

### Generated Analytical Datasets

The processing pipeline generates:

- `data/processed/youtube_history.csv`
- `data/processed/youtube_growth.csv`
- `data/processed/youtube_viral_candidates_vn.csv`
- `data/processed/youtube_current_trending_vn.csv`

Processed CSV files are excluded from Git and can be regenerated from the pipeline.


---

## Project Status Update - 2026-10-15

### Current Data Volume

- Master dataset unique videos: 2,411
- VN Rolling Cohort unique videos: 2,030
- Known unique videos across master and cohort: 4,441
- Verified VN cohort T0 observations: 2,030
- Verified VN cohort T24 observations: 1,030
- Next collection milestone: more than 35,000 unique videos

Unique video counts are distinct from historical observations.
T0 and T24 records do not count as additional unique videos.

### Automated VN Data Pipeline

The current pipeline includes:

1. Daily Cohort Discovery
   - Runs daily at 08:00 Vietnam time.
   - Target: up to 1,000 new unique videos per run.
   - Uses YouTube Data API v3 and uploads playlists.
   - Stores T0 observations in SQL Server and MinIO.

2. Rolling Cohort T24
   - Checks pending batches every hour.
   - Collects follow-up statistics after at least 24 hours.
   - Synchronizes observations to SQL Server and MinIO.

3. YouTube Chart Monitor
   - Runs hourly at minute 10.
   - Collects YouTube mostPopular chart observations.
   - Stores raw JSON in MinIO and structured records in SQL Server.

The legacy VN Hourly Snapshot scheduled task is disabled.

### RQ1 - Upload Time and Chart Observation

Research focus:
Association between upload period and observed appearance
on the YouTube mostPopular chart.

Current dataset:
data/processed/rq1_youtube_cohort_VN.csv

Current results:
- Cohort videos: 2,030
- Videos discovered within 24 hours of upload: 901
- Completed T24 observations: 1,030
- Observed chart positives: 24
- Confirmed chart negatives: 0
- Complete 24-hour chart coverage: 0
- RQ1 analysis-ready videos: 0

Preliminary EDA was conducted using Python and RStudio.

Important limitations:
- Chart observation is not equivalent to universal viral status.
- Missing chart observations cannot be treated as confirmed negatives.
- Hourly sampling cannot rule out appearances between captures.
- Existing cohorts have incomplete chart coverage.
- Upload-period groups may differ in channel composition and video age.

RQ1 hypothesis testing has not yet been completed.

### RQ2 - Negative Comments and Viral Activity

The YouTube comment collection module is located at:
src/ingestion/youtube_comments.py

Initial VN pilot:
- Videos tested: 3
- Top-level comments collected: 24
- Duplicate comment IDs: 0
- Missing video IDs: 0
- Empty comment texts: 0
- Invalid comment publication dates: 0

The initial collection uses relevance-ranked comments.
This is a pipeline validation sample, not a representative
dataset for sentiment-based hypothesis testing.

Next steps:
- Expand the comment sample.
- Clean and normalize comment text.
- Build and validate sentiment labels.
- Aggregate negative comment ratios by video.
- Align comments with the appropriate observation window.

### Reproducibility

Python dependencies are managed using uv.

Read-only planning commands:

uv run python -m src.ingestion.run_daily_cohort --region VN

uv run python -m src.ingestion.youtube_chart_monitor capture --region VN

RQ1 analysis dataset generation:

uv run python -m src.processing.build_rq1_dataset --region VN --apply

Raw data is stored locally and in MinIO.
Structured cohort and chart observations are stored in SQL Server.

Secrets must remain in .env and must not be committed to Git.
