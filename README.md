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

### Current Data Volume

- Unique videos: 2,011
- Trending videos: 1,011
- Control videos: 1,000
- Historical records: 8,066
- Target: 10,000+ records

### Environment Setup

Copy the environment template:

```powershell
Copy-Item .env.example .env