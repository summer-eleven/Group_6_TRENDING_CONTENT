# Group 6 â€“ Trending Content (YouTube)

## Project Title

**Analysis of Factors Influencing YouTube Trending Content**

## 1. Project Overview

This project studies factors associated with the popularity and visibility of YouTube videos. The implementation focuses on two research questions:

- **RQ1 â€“ Upload Time:** Is a video's upload period associated with its probability of appearing on the YouTube Most Popular chart?
- **RQ2 â€“ Negative User Engagement:** Is negative audience response, measured through comment sentiment, associated with video virality?

The project combines YouTube data collection, data engineering, statistical analysis, and machine-learning workflows. The repository contains Python source code, R analysis assets, notebooks, documentation, and report evidence.

> **Interpretation note:** Appearing on the YouTube Most Popular chart is an observable chart outcome. It is not a universal measure of every possible meaning of â€œviralâ€ or â€œpopular.â€

## 2. Problem Statement

YouTube hosts a large volume of videos with different levels of visibility and engagement. It is not clear whether upload timing and negative audience response are associated with a video's ability to appear on the YouTube Most Popular chart or achieve high visibility.

This project builds data collection and processing workflows to examine these relationships using observed YouTube data. The analysis is observational, so results are interpreted as associations rather than proof of causation.

## 3. Research Questions and Hypotheses

### RQ1 â€“ Upload Time

**Research question:** Is the upload period of a YouTube video associated with its probability of appearing on the YouTube Most Popular chart?

- **Hâ‚€â‚ (Null hypothesis):** Upload period is not significantly associated with the probability of a YouTube video appearing on the YouTube Most Popular chart.
- **Hâ‚â‚ (Alternative hypothesis):** Upload period is significantly associated with the probability of a YouTube video appearing on the YouTube Most Popular chart.

For the Vietnam RQ1 analysis, the pipeline's primary office-hours definition is Mondayâ€“Friday, 08:00â€“16:59 Vietnam local time. Alternative time-window definitions are examined as sensitivity checks.

### RQ2 â€“ Negative User Engagement

**Research question:** Is negative user engagement associated with the virality of a YouTube video?

- **Hâ‚€â‚‚ (Null hypothesis):** Negative user engagement is not significantly associated with video virality.
- **Hâ‚â‚‚ (Alternative hypothesis):** Negative user engagement is significantly associated with video virality.

The comment-analysis workflow collects and processes comments to support sentiment analysis. The project does not treat dislike count as a substitute for negative comment sentiment. RQ2 results should only be reported after comment labels, observation windows, and the video-level measure have been validated.

## 4. System Architecture

The data workflow uses the following high-level architecture:

```text
YouTube Data API
       |
       v
Data Ingestion (Python)
       |
       +------> Raw JSON / local data
       |
       +------> MinIO object storage
                    |
                    v
             Data Processing
                    |
          +---------+---------+
          |                   |
          v                   v
   Processed datasets     SQL Server
          |                   |
          +---------+---------+
                    |
                    v
          Statistical Analysis
          / Machine Learning
                    |
                    v
             Reports and Charts
```

### Docker services

The current `docker-compose.yml` defines two infrastructure services:

| Service | Purpose | Default host port |
|---|---|---:|
| MinIO | Object storage for raw and processed objects | `9000` (API), `9001` (console) |
| SQL Server | Relational storage for structured records | `1433` |

The Python pipeline and RStudio are **not** services in the current Compose file. They run on the host machine unless separately configured.

## 5. Data Collection Pipeline

The repository contains ingestion scripts for YouTube video metadata, regional cohorts, comments, and chart observations.

### 5.1 YouTube data ingestion

The ingestion modules use the YouTube Data API and save collected data for subsequent processing. The source code includes workflows for:

- Video and category collection.
- Trending and control-video collection.
- Regional expansion and cohort discovery.
- Comment collection.
- YouTube Most Popular chart monitoring.
- Follow-up collection for rolling cohorts.

The YouTube API key is read from the `YOUTUBE_API_KEY` environment variable.

### 5.2 Daily cohort and follow-up collection

The Vietnam daily cohort workflow discovers videos and records an initial observation. Follow-up workflows collect later observations for eligible cohort batches.

Example command:

```powershell
uv run python -m src.ingestion.run_daily_cohort --region VN
```

The command may make API requests and write data. Confirm the API key, quota, and intended output before running it.

### 5.3 Hourly chart monitoring

The chart monitor collects observations from the YouTube Most Popular chart. The project has used Windows Task Scheduler for recurring collection.

Example one-time capture command:

```powershell
uv run python -m src.ingestion.youtube_chart_monitor capture --region VN
```

The chart monitor's raw captures are used to validate whether cohort videos were observed on the chart during the relevant observation window. Missing observations must not automatically be interpreted as confirmed negatives when coverage is incomplete.

## 6. Data Processing and Storage

The processing modules support tasks such as:

- Cleaning and standardizing YouTube metadata.
- Merging raw records and building a global master dataset.
- Building RQ1 and RQ2 analysis datasets.
- Creating and synchronizing cohort records.
- Processing comments and sentiment labels.
- Auditing dataset uniqueness and consistency.
- Loading structured video and snapshot records into SQL Server.
- Uploading raw or processed objects to MinIO.

### Storage roles

- **Local files:** working copies of raw data, processed datasets, notebooks, and evidence.
- **MinIO:** object storage for configured raw and processed data workflows.
- **SQL Server:** structured storage for configured video and snapshot records.

Generated datasets and raw collection files may be excluded from Git. A fresh clone therefore does not necessarily contain the datasets used in the reported analysis. Follow the collection and processing workflows, or obtain the required project data from the team, before running analyses that depend on those files.

## 7. Current Dataset Statistics

The following figures reflect the latest project validation information available for this README update. Counts refer to different dataset levels and should not be added together unless explicitly stated.

### 7.1 Global master and Vietnam RQ1 cohort

| Measure | Count |
|---|---:|
| Unique videos in global master | 19,248 |
| Vietnam-tagged videos in global master | 12,055 |
| Videos in Vietnam RQ1 cohort | 11,531 |
| RQ1 eligible observations (positive + confirmed negative) | 2,044 |
| Observed chart positives | 46 |
| Confirmed chart negatives | 1,998 |
| Unknown / incomplete chart coverage | 9,487 |

The `UNKNOWN_INCOMPLETE_COVERAGE` group is not included as a negative class. It represents videos for which the chart observation evidence is insufficient to assign a confirmed negative label.

### 7.2 Chart-monitor validation inventory

At the latest recorded inventory check:

- Raw chart capture files: **377**
- Fully paginated runs: **376**
- Distinct chart videos across the captures: **1,431**

A separate historical comparison used a reconstructed cutoff to reproduce an earlier inventory of 335 raw files, 334 fully paginated runs, and 1,301 distinct videos. That cutoff is a reconstruction for historical comparison; it is not independently authenticated as the original snapshot boundary. The current inventory above should be used when describing the latest collection state.

## 8. RQ1 â€“ Vietnam Analysis and Findings

### 8.1 Analysis sample

The Vietnam RQ1 cohort contains 11,531 videos. Of these:

- 46 were observed as chart positives.
- 1,998 were classified as confirmed chart negatives.
- 9,487 remained unknown because chart coverage was incomplete.

The eligible statistical sample therefore contains 2,044 videos (46 positives and 1,998 confirmed negatives). Unknown cases are excluded from the primary binary hypothesis test rather than being treated as negatives.

### 8.2 Primary office-hours comparison

The pipeline defines office hours as Mondayâ€“Friday, 08:00â€“16:59 Vietnam local time.

| Upload period | Chart positives | Eligible videos | Observed rate |
|---|---:|---:|---:|
| Office hours | 9 | 374 | 2.41% |
| Non-office hours | 37 | 1,670 | 2.22% |

Primary test results:

- Fisher's exact test: **p = 0.847**
- CramÃ©r's V: **0.005**

At the conventional 0.05 significance level, the analysis **fails to reject Hâ‚€â‚**. In this eligible Vietnam sample, the test does not provide evidence of a statistically significant association between the pipeline's office-hours grouping and chart appearance.

This result does not prove that upload time never matters. It is limited to the observed sample, operational definitions, and chart-monitor coverage.

### 8.3 Sensitivity analysis

Alternative office-hour definitions were checked:

| Definition | Office-hour positives / eligible | Fisher's exact p-value |
|---|---:|---:|
| Mondayâ€“Friday, 08:00â€“16:59 (pipeline definition) | 9 / 374 | 0.847 |
| Mondayâ€“Friday, 09:00â€“16:59 | 9 / 339 | 0.550 |
| All days, 09:00â€“16:59 | 14 / 550 | 0.614 |

The sensitivity checks also have p-values above 0.05. The conclusion is unchanged under these tested alternative definitions. These are reclassifications of the existing eligible sample, not independent cohorts.

### 8.4 Limitations

Important limitations include:

- 82.3% of the Vietnam cohort has unknown / incomplete chart coverage and is excluded from the primary binary test.
- The eligible sample contains only 46 chart positives.
- Chart monitoring is based on periodic captures; a video may appear between captures and not be observed.
- Chart appearance is not equivalent to every possible definition of virality.
- Upload-period groups may differ in channel composition, video age, and other factors.
- The analysis is observational and does not establish causation.

## 9. RQ2 â€“ Negative Comment Sentiment

The repository includes comment ingestion and processing components, including:

- `src/ingestion/youtube_comments.py`
- `src/ingestion/crawl_expansion_comments.py`
- `src/processing/clean_comments_JP.py`
- `src/processing/classify_sentiment_JP.py`
- `src/processing/validate_sentiment_JP.py`
- `src/processing/build_rq2_dataset.py`

The intended analysis uses comment sentiment as a measure of negative user engagement. Before reporting an RQ2 hypothesis test, the project needs a validated comment sample, reliable sentiment labels, a defined video-level negative-engagement measure, and observation windows aligned with the virality outcome.

**No final RQ2 effect estimate or hypothesis-test result is stated in this README**, because a verified final result is not available in the project information used for this update.

## 10. Repository Structure

The following is a curated overview of the main project directories. It omits generated datasets, virtual environments, caches, and temporary files.

```text
Group_6_TRENDING_CONTENT/
â”œâ”€â”€ data/
â”‚   â”œâ”€â”€ raw/
â”‚   â”œâ”€â”€ processed/
â”‚   â””â”€â”€ global/
â”œâ”€â”€ docs/
â”œâ”€â”€ docker/
â”‚   â””â”€â”€ db/
â”œâ”€â”€ notebooks/
â”œâ”€â”€ reports/
â”‚   â””â”€â”€ assets/
â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ ingestion/
â”‚   â”œâ”€â”€ processing/
â”‚   â”œâ”€â”€ modeling/
â”‚   â”‚   â””â”€â”€ rq1/
â”‚   â”œâ”€â”€ visualization/
â”‚   â””â”€â”€ utils/
â”œâ”€â”€ .env.example
â”œâ”€â”€ .gitignore
â”œâ”€â”€ docker-compose.yml
â”œâ”€â”€ pyproject.toml
â”œâ”€â”€ uv.lock
â””â”€â”€ README.md
```

Directory responsibilities:

| Directory | Responsibility |
|---|---|
| `src/ingestion/` | YouTube API collection, cohorts, comments, chart monitoring |
| `src/processing/` | Cleaning, dataset construction, storage, synchronization, audits |
| `src/modeling/` | Statistical analysis and machine-learning workflows |
| `src/visualization/` | Analytical charts |
| `src/utils/` | Shared database, reporting, and data-quality utilities |
| `data/` | Local raw, processed, and global datasets |
| `docs/` | Project and analysis documentation |
| `notebooks/` | Exploratory and modeling notebooks |
| `reports/` | Reports and supporting evidence |
| `docker/` | Docker-related database configuration |

## 11. Environment Setup

### 11.1 Prerequisites

Install the following on the host machine:

- Git.
- Python **3.10 or later**.
- `uv`.
- Docker Desktop with Docker Compose.
- Microsoft ODBC Driver 18 for SQL Server, when using the Python SQL Server connection modules.
- R and RStudio, if you intend to run the R analysis assets.

The Python project dependencies are defined in `pyproject.toml` and locked in `uv.lock`. The current `requirements.txt` is only a placeholder and is not the dependency source of record.

### 11.2 Clone the repository

```powershell
git clone https://github.com/summer-eleven/Group_6_TRENDING_CONTENT.git
cd Group_6_TRENDING_CONTENT
```

### 11.3 Install Python dependencies

If `uv` is not installed:

```powershell
pip install uv
```

Then synchronize the project environment from the lock file:

```powershell
uv sync
```

Run project Python commands from the repository root so that relative paths and `.env` discovery behave as expected.

### 11.4 Configure environment variables

Create a local `.env` file:

```powershell
Copy-Item .env.example .env
```

Open `.env` and replace the placeholders with valid local credentials:

```dotenv
YOUTUBE_API_KEY=your_youtube_api_key

MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=your_minio_username
MINIO_SECRET_KEY=your_minio_password
MINIO_BUCKET=trending-content

DB_SERVER=localhost,1433
DB_NAME=youtube_trending
DB_USER=sa
DB_PASSWORD=your_sql_server_password
DB_DRIVER=ODBC Driver 18 for SQL Server
```

The values above are examples, not working credentials. The SQL Server password must satisfy SQL Server's password policy. Keep `.env` private and never commit it to Git.

The source code uses `python-dotenv` in its ingestion and database modules to load environment variables from `.env`.

### 11.5 Start MinIO and SQL Server

From the repository root:

```powershell
docker compose up -d
docker compose ps
```

To stop the services:

```powershell
docker compose down
```

To stop the services and remove their named volumes (this deletes the persisted database and object-storage data):

```powershell
docker compose down -v
```

**Warning:** Do not use `docker compose down -v` if you need to preserve data stored in the SQL Server or MinIO volumes.

The current Compose file starts the MinIO and SQL Server containers. It does not start the Python pipeline or RStudio. Configure the database, MinIO bucket, credentials, and host ODBC driver as required by the scripts before running storage workflows.

## 12. Running the Project

Run commands from the repository root, after completing the environment setup and confirming that the required input data and services are available.

### 12.1 Run the Vietnam daily cohort workflow

```powershell
uv run python -m src.ingestion.run_daily_cohort --region VN
```

This workflow uses the YouTube API and may consume API quota and write new data.

### 12.2 Capture the Vietnam Most Popular chart

```powershell
uv run python -m src.ingestion.youtube_chart_monitor capture --region VN
```

This performs a chart capture. For continuous hourly collection, configure the appropriate Windows Task Scheduler task separately; running this command once does not create a recurring schedule.

### 12.3 Build the Vietnam RQ1 dataset

```powershell
uv run python -m src.processing.build_rq1_dataset --region VN --apply
```

The `--apply` option runs the dataset-building operation. Review the script's options and ensure the required input data is available before executing it.

### 12.4 Run RQ1 analysis and number verification

The repository includes the following analysis scripts:

```powershell
uv run python .\src\modeling\rq1\rq1_vn_analysis.py
uv run python .\src\modeling\rq1\rq1_prove_numbers.py
```

These scripts depend on the expected processed datasets and project directory structure. They are not substitutes for running the upstream data collection and processing steps.

## 13. Reproducibility and Data Validation

For reproducible work:

1. Use the project dependency lock file with `uv sync`.
2. Keep API keys and passwords in the local `.env` file.
3. Run commands from the repository root.
4. Preserve the raw collection data used for an analysis.
5. Record the dataset version, collection window, region, and script used to generate each result.
6. Distinguish unique videos from repeated historical observations or snapshots.
7. Do not label videos as confirmed negatives when chart coverage is incomplete.
8. Re-run the relevant validation scripts after changing source data or processing logic.

Raw data and generated CSV files may be ignored by Git. A successful clone alone does not guarantee that all data required to reproduce the reported results is present.

## 14. Limitations and Interpretation

- The project uses observational YouTube data; statistical association does not establish causation.
- YouTube chart observations depend on collection timing and coverage.
- Unknown chart status must remain distinct from confirmed negative status.
- Regional datasets may differ in size, collection period, and coverage. Do not combine regional counts without a clearly defined aggregation method.
- Comment samples and sentiment labels may be affected by sampling, language, spam, and classification errors.
- Model results should be interpreted within the scope of their training data and validation procedure.

## 15. Security and Git Practices

- Never commit `.env`, API keys, database passwords, or MinIO secrets.
- Use `.env.example` to document required variable names without exposing real values.
- Do not commit `.venv/`, `__pycache__/`, temporary outputs, or generated datasets unless the team explicitly requires them.
- Check staged changes before committing:

```powershell
git status
git diff --cached --check
```

---

**Project:** Group 6 â€“ Trending Content (YouTube)
**Repository:** [summer-eleven/Group_6_TRENDING_CONTENT](https://github.com/summer-eleven/Group_6_TRENDING_CONTENT)

