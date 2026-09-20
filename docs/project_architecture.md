# Project Architecture

## System Overview

The project follows an end-to-end data pipeline from YouTube data collection to data analysis and machine learning.

The main workflow is:

YouTube API → Python → MinIO → Database → RStudio/Jupyter → EDA & Modeling

## Architecture Components

### 1. YouTube API

The YouTube API is used as the data source for collecting video information.

### 2. Python

Python is responsible for collecting and processing the raw data obtained from the YouTube API.

### 3. MinIO

MinIO is used as the Data Lake to store the collected raw data before further processing.

### 4. Database

The processed data is stored in a database for structured storage and SQL-based data validation.

### 5. RStudio / Jupyter

RStudio and Jupyter are used for exploratory data analysis, visualization, statistical analysis, and machine learning.

## Data Flow

## Data Flow

## Data Flow

```text
YouTube API
     ↓
Python Data Collection
     ↓
MinIO (Raw Data)
     ↓
Database
     ↓
RStudio / Jupyter
     ↓
EDA & Machine Learning
     ↓
Research Results
```

## Docker Architecture

Docker is used to provide a consistent environment for the project services.

The main services include:

- Python / Application
- MinIO
- Database
- RStudio / Jupyter

## Docker Architecture

Docker is used to provide a consistent environment for the project services.

The main services include:

- Python / Application
- MinIO
- Database
- RStudio / Jupyter

The architecture is designed to support the complete research workflow from data collection to analysis and model evaluation.
