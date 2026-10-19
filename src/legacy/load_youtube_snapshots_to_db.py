import os

import pandas as pd
import pyodbc
from dotenv import load_dotenv

load_dotenv()

HISTORY_PATH = "data/processed/youtube_history.csv"

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

df = pd.read_csv(HISTORY_PATH)

df["collected_at"] = pd.to_datetime(
    df["collected_at"],
    errors="coerce",
    utc=True,
)


def clean_number(value):
    if pd.isna(value):
        return None
    return int(value)


def clean_datetime(value):
    if pd.isna(value):
        return None

    return (
        value
        .to_pydatetime()
        .replace(tzinfo=None)
    )


def clean_text(value):
    if pd.isna(value):
        return None
    return str(value)


def clean_bool(value, default=0):
    if pd.isna(value):
        return default
    return int(bool(value))


connection = pyodbc.connect(
    connection_string,
    timeout=10,
)

cursor = connection.cursor()

merge_sql = """
MERGE youtube_video_snapshots AS target
USING (
    SELECT
        ? AS video_id,
        ? AS region_code,
        ? AS collected_at,
        ? AS view_count,
        ? AS like_count,
        ? AS comment_count,
        ? AS is_trending,
        ? AS trending_rank,
        ? AS video_available
) AS source
ON
    target.video_id = source.video_id
    AND target.region_code = source.region_code
    AND target.collected_at = source.collected_at

WHEN MATCHED THEN
    UPDATE SET
        view_count = source.view_count,
        like_count = source.like_count,
        comment_count = source.comment_count,
        is_trending = source.is_trending,
        trending_rank = source.trending_rank,
        video_available = source.video_available

WHEN NOT MATCHED THEN
    INSERT (
        video_id,
        region_code,
        collected_at,
        view_count,
        like_count,
        comment_count,
        is_trending,
        trending_rank,
        video_available
    )
    VALUES (
        source.video_id,
        source.region_code,
        source.collected_at,
        source.view_count,
        source.like_count,
        source.comment_count,
        source.is_trending,
        source.trending_rank,
        source.video_available
    );
"""

loaded = 0
failed = 0

for _, row in df.iterrows():
    try:
        cursor.execute(
            merge_sql,
            clean_text(row["video_id"]),
            clean_text(row["region_code"]),
            clean_datetime(row["collected_at"]),
            clean_number(row["view_count"]),
            clean_number(row["like_count"]),
            clean_number(row["comment_count"]),
            clean_number(row["is_trending"]),
            clean_number(row["trending_rank"]),
            clean_bool(row["video_available"], default=1),
        )

        loaded += 1

    except Exception as error:
        failed += 1

        print(
            "Failed snapshot:",
            row["video_id"],
            row["collected_at"],
            error,
        )

connection.commit()

cursor.execute(
    "SELECT COUNT(*) FROM youtube_video_snapshots"
)

database_count = cursor.fetchone()[0]

print("=" * 60)
print("SNAPSHOT DATABASE LOAD COMPLETED")
print("Input records:", len(df))
print("Loaded:", loaded)
print("Failed:", failed)
print("Database snapshot rows:", database_count)
print("=" * 60)

cursor.close()
connection.close()