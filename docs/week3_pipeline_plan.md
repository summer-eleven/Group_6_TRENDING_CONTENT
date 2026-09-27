# Week 3 Pipeline Integration Plan

## 1. Pipeline Overview

YouTube API
    ↓
YouTube Crawler
    ↓
Raw Snapshot
    ↓
MinIO
    ↓
Processing
    ↓
Database
    ↓
SQL Verification

## 2. Raw Data Storage

Raw YouTube data will be stored in MinIO.

Bucket:
youtube-raw

Object structure:
snapshots/<timestamp>/youtube_raw.csv

Example:
snapshots/20260927_120000/youtube_raw.csv

## 3. Current Crawler Fields

The current pipeline collects fields including:

- video_id
- region_code
- category_id
- title
- channel_title
- published_at
- view_count
- like_count
- comment_count
- rank
- collected_at

The final database schema must be aligned with the
actual crawler output and the team's Data Dictionary.

## 4. Processing Flow

Raw data
→ validation
→ cleaning / transformation
→ processed records
→ database loader

Existing crawler and cleaning components will be reused
rather than rebuilt.

## 5. Database Integration

Processed records will be loaded into the database
service configured by the team.

The database schema must only contain fields supported
by the actual pipeline.

## 6. Verification

The pipeline will be verified using:

- Row count
- Duplicate video_id checks
- Null-value checks
- Sample record queries
- Basic data-quality validation

## 7. Security

API keys and MinIO/Database credentials must be loaded
from environment variables or configuration files.

Secrets must not be committed to GitHub.