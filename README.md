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
