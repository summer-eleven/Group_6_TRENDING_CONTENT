from pathlib import Path

import pandas as pd


BASE_PATH = Path(
    "data/processed/youtube_dataset_2000_clean.csv"
)

SNAPSHOT_DIR = Path(
    "data/raw/snapshots"
)

OUTPUT_PATH = Path(
    "data/processed/youtube_history.csv"
)


def normalize_dataframe(df, snapshot_id, source_file):
    df = df.copy()

    if "video_available" not in df.columns:
        df["video_available"] = True

    if "upload_hour_utc" not in df.columns:
        published = pd.to_datetime(
            df["published_at"],
            errors="coerce",
            utc=True,
        )

        df["upload_hour_utc"] = (
            published.dt.hour.astype("Int64")
        )

    if "video_url" not in df.columns:
        df["video_url"] = (
            "https://www.youtube.com/watch?v="
            + df["video_id"].astype(str)
        )

    df["snapshot_id"] = snapshot_id
    df["source_file"] = source_file

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

    numeric_columns = [
        "view_count",
        "like_count",
        "comment_count",
        "is_trending",
        "trending_rank",
        "upload_hour_utc",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        ).astype("Int64")

    return df


base_df = pd.read_csv(BASE_PATH)

base_df = normalize_dataframe(
    base_df,
    snapshot_id="baseline_1000",
    source_file=BASE_PATH.name,
)

frames = [base_df]

snapshot_files = sorted(
    SNAPSHOT_DIR.glob("youtube_snapshot_*.json")
)

print("Snapshot files found:", len(snapshot_files))

for snapshot_path in snapshot_files:
    print("Loading:", snapshot_path.name)

    snapshot_df = pd.read_json(snapshot_path)

    snapshot_df = normalize_dataframe(
        snapshot_df,
        snapshot_id=snapshot_path.stem,
        source_file=snapshot_path.name,
    )

    frames.append(snapshot_df)


history_df = pd.concat(
    frames,
    ignore_index=True,
)


before_deduplication = len(history_df)

history_df = history_df.drop_duplicates(
    subset=[
        "video_id",
        "region_code",
        "collected_at",
    ],
    keep="last",
)

after_deduplication = len(history_df)


column_order = [
    "snapshot_id",
    "source_file",
    "video_id",
    "title",
    "channel_id",
    "channel_title",
    "category_id",
    "published_at",
    "upload_hour_utc",
    "region_code",
    "collected_at",
    "view_count",
    "like_count",
    "comment_count",
    "is_trending",
    "trending_rank",
    "video_available",
    "video_url",
]

history_df = history_df[column_order]

history_df = history_df.sort_values(
    by=[
        "collected_at",
        "video_id",
    ]
)

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

history_df.to_csv(
    OUTPUT_PATH,
    index=False,
    encoding="utf-8-sig",
)


print()
print("=" * 60)
print("HISTORY MERGE COMPLETED")
print("Base records:", len(base_df))
print("Snapshot files:", len(snapshot_files))
print("Records before deduplication:", before_deduplication)
print("Records after deduplication:", after_deduplication)
print(
    "Unique videos:",
    history_df["video_id"].nunique(),
)
print(
    "Snapshot IDs:",
    history_df["snapshot_id"].nunique(),
)
print("Saved to:", OUTPUT_PATH)
print("=" * 60)