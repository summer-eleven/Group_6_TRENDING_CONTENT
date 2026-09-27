import os

import pandas as pd
import pyodbc
from dotenv import load_dotenv

load_dotenv()

DATASET_PATH = "data/processed/youtube_dataset_2000_clean.csv"

server = os.getenv("DB_SERVER")
database = os.getenv("DB_NAME")
username = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
driver = os.getenv("DB_DRIVER")

connection_string = (
    f"DRIVER={{{driver}}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=yes;"
)

df = pd.read_csv(DATASET_PATH)

df["published_at"] = pd.to_datetime(
    df["published_at"],
    errors="coerce",
    utc=True,
)

df["collected_at"] = pd.to_datetime(
    df["collected_at"],
    errors="coerce",
    utc=True,
)


def clean_value(value):
    if pd.isna(value):
        return None
    return value


connection = pyodbc.connect(
    connection_string,
    timeout=10,
)

cursor = connection.cursor()

merge_sql = """
MERGE youtube_videos AS target
USING (
    SELECT
        ? AS video_id,
        ? AS title,
        ? AS channel_id,
        ? AS channel_title,
        ? AS category_id,
        ? AS published_at,
        ? AS region_code,
        ? AS view_count,
        ? AS like_count,
        ? AS comment_count,
        ? AS is_trending,
        ? AS trending_rank,
        ? AS collected_at
) AS source
ON target.video_id = source.video_id

WHEN MATCHED THEN
    UPDATE SET
        title = source.title,
        channel_id = source.channel_id,
        channel_title = source.channel_title,
        category_id = source.category_id,
        published_at = source.published_at,
        region_code = source.region_code,
        view_count = source.view_count,
        like_count = source.like_count,
        comment_count = source.comment_count,
        is_trending = source.is_trending,
        trending_rank = source.trending_rank,
        collected_at = source.collected_at

WHEN NOT MATCHED THEN
    INSERT (
        video_id,
        title,
        channel_id,
        channel_title,
        category_id,
        published_at,
        region_code,
        view_count,
        like_count,
        comment_count,
        is_trending,
        trending_rank,
        collected_at
    )
    VALUES (
        source.video_id,
        source.title,
        source.channel_id,
        source.channel_title,
        source.category_id,
        source.published_at,
        source.region_code,
        source.view_count,
        source.like_count,
        source.comment_count,
        source.is_trending,
        source.trending_rank,
        source.collected_at
    );
"""

loaded = 0
failed = 0

for _, row in df.iterrows():
    try:
        cursor.execute(
            merge_sql,
            clean_value(row["video_id"]),
            str(clean_value(row["title"]))[:500],
            clean_value(row["channel_id"]),
            str(clean_value(row["channel_title"]))[:200]
            if clean_value(row["channel_title"]) is not None
            else None,
            clean_value(row["category_id"]),
            clean_value(row["published_at"]),
            clean_value(row["region_code"]),
            clean_value(row["view_count"]),
            clean_value(row["like_count"]),
            clean_value(row["comment_count"]),
            clean_value(row["is_trending"]),
            clean_value(row["trending_rank"]),
            clean_value(row["collected_at"]),
        )

        loaded += 1

    except Exception as error:
        failed += 1
        print(
            "Failed video:",
            row["video_id"],
            error,
        )

connection.commit()

cursor.execute(
    "SELECT COUNT(*) FROM youtube_videos"
)

database_count = cursor.fetchone()[0]

print("=" * 60)
print("DATABASE LOAD COMPLETED")
print("Input records:", len(df))
print("Loaded:", loaded)
print("Failed:", failed)
print("Database rows:", database_count)
print("=" * 60)

cursor.close()
connection.close()