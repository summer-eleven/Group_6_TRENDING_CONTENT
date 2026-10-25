"""Multi-batch Comment Cleaning Pipeline for JP RQ2 (HT-03).

Features:
  - Ingests ALL raw comment JSON files under data/raw/comments/JP/ (and legacy data/raw/comments/)
  - Deduplicates by comment_id across all batches
  - Preserves Japanese Kanji, Hiragana, Katakana, and Emoji
  - Normalizes URLs to <URL> token and collapses excessive whitespace
  - Reports data quality statistics: duplicates, empty text, unique video coverage
  - Outputs to data/processed/comments_clean_JP.csv
"""

import glob
import json
import re
from pathlib import Path
import pandas as pd

RAW_JP_DIR = Path("data/raw/comments/JP")
LEGACY_RAW_DIR = Path("data/raw/comments")
OUTPUT_PATH = Path("data/processed/comments_clean_JP.csv")


def load_raw_comments() -> tuple[pd.DataFrame, int]:
    """Find and parse all comment JSON files."""
    json_files = sorted(list(RAW_JP_DIR.glob("*.json"))) + sorted(list(LEGACY_RAW_DIR.glob("*.json")))
    # Exclude files already found in JP subfolder
    json_files = list(dict.fromkeys(json_files))

    if not json_files:
        raise FileNotFoundError("No comment JSON files found in data/raw/comments/ or data/raw/comments/JP/")

    print(f"Discovered {len(json_files)} raw comments JSON batch files:")
    for f in json_files:
        print(f"  - {f.as_posix()} ({f.stat().st_size:,} bytes)")

    records = []
    for f in json_files:
        try:
            content = json.loads(f.read_text(encoding="utf-8-sig"))
            if isinstance(content, list):
                records.extend(content)
            elif isinstance(content, dict):
                if "comments" in content:
                    records.extend(content["comments"])
                elif "items" in content:
                    records.extend(content["items"])
        except Exception as e:
            print(f"Warning: could not parse {f}: {e}")

    df = pd.DataFrame(records)
    return df, len(json_files)


def clean_comments():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    raw_df, num_files = load_raw_comments()
    initial_count = len(raw_df)
    print(f"\nTotal raw comments extracted across {num_files} files: {initial_count:,}")

    if raw_df.empty:
        print("No comments to process.")
        return

    # 1. Deduplicate by comment_id
    dedup_df = raw_df.drop_duplicates(subset=["comment_id"]).copy()
    duplicates_removed = initial_count - len(dedup_df)

    # 2. Filter missing or non-string text
    dedup_df = dedup_df.dropna(subset=["comment_text"])
    dedup_df["comment_text"] = dedup_df["comment_text"].astype(str).str.strip()
    empty_removed = (dedup_df["comment_text"] == "").sum()
    dedup_df = dedup_df[dedup_df["comment_text"] != ""].copy()

    # 3. Clean and normalize:
    # - Replace URLs with <URL> token
    # - Collapse multiple whitespace
    # - KEEP Japanese characters & Emojis intact
    dedup_df["comment_clean"] = dedup_df["comment_text"].str.replace(
        r"https?://\S+|www\.\S+", " <URL> ", regex=True
    )
    dedup_df["comment_clean"] = dedup_df["comment_clean"].str.replace(
        r"\s+", " ", regex=True
    ).str.strip()

    # Filter out empty comments after URL replacement
    dedup_df = dedup_df[dedup_df["comment_clean"] != ""].copy()
    final_count = len(dedup_df)

    # Select standard clean columns
    cols_to_keep = [
        "comment_id", "video_id", "region_code", "comment_text",
        "comment_clean", "comment_like_count", "comment_published_at", "collected_at"
    ]
    available_cols = [c for c in cols_to_keep if c in dedup_df.columns]
    final_df = dedup_df[available_cols]

    # Save to CSV
    final_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    # Print Quality Audit Summary
    unique_vids = final_df["video_id"].nunique()
    print("=" * 65)
    print("COMMENTS CLEANING COMPLETED (HT-03)")
    print(f"- Initial comments ingested:   {initial_count:,}")
    print(f"- Duplicate comments removed:  {duplicates_removed:,} ({duplicates_removed/max(1,initial_count)*100:.1f}%)")
    print(f"- Empty/invalid text removed:  {empty_removed:,}")
    print(f"- Clean valid comments output: {final_count:,}")
    print(f"- Unique videos represented:   {unique_vids:,} videos")
    print(f"- Output saved to:             {OUTPUT_PATH}")
    print("=" * 65)
    return final_df


if __name__ == "__main__":
    clean_comments()