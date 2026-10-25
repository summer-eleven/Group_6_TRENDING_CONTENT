"""Build Video-Level Dataset for RQ2 Sentiment Analysis & Modeling (HT-05).

Aggregates comment-level sentiment to video-level metrics:
  - total_comments, positive_ratio, negative_ratio, neutral_ratio
  - weighted_negative_ratio (weighted by comment likes)
  - joins with video performance metrics (views, likes, comments, category, upload time)
  - outputs to data/processed/rq2_video_sentiment_JP.csv
"""

from pathlib import Path
import numpy as np
import pandas as pd

SENTIMENT_PATH = Path("data/processed/comments_sentiment_JP.csv")
REGISTRY_PATH = Path("data/processed/youtube_cohort_registry_JP.csv")
MASTER_PATH = Path("data/processed/youtube_dataset_2000_clean.csv")
OUTPUT_PATH = Path("data/processed/rq2_video_sentiment_JP.csv")


def build_rq2_dataset():
    if not SENTIMENT_PATH.is_file():
        raise FileNotFoundError(f"Missing sentiment comments file: {SENTIMENT_PATH}")

    df_sent = pd.read_csv(SENTIMENT_PATH)
    print(f"Loaded {len(df_sent):,} comment sentiment rows across {df_sent['video_id'].nunique()} videos.")

    # 1. Aggregate comments per video
    records = []
    for vid, group in df_sent.groupby("video_id"):
        tot = len(group)
        pos = (group["sentiment"] == "positive").sum()
        neg = (group["sentiment"] == "negative").sum()
        neu = (group["sentiment"] == "neutral").sum()

        likes = group["comment_like_count"].fillna(0).clip(lower=0)
        weights = likes + 1
        weighted_neg = (weights * (group["sentiment"] == "negative")).sum() / weights.sum()

        avg_score = group["sentiment_score"].mean()

        records.append({
            "video_id": vid,
            "region_code": "JP",
            "sample_comment_count": tot,
            "positive_count": pos,
            "negative_count": neg,
            "neutral_count": neu,
            "positive_ratio": round(pos / tot, 4),
            "negative_ratio": round(neg / tot, 4),
            "neutral_ratio": round(neu / tot, 4),
            "sentiment_polarity": round((pos - neg) / tot, 4),
            "weighted_negative_ratio": round(weighted_neg, 4),
            "avg_sentiment_confidence": round(avg_score, 4),
        })

    vid_sent_df = pd.DataFrame(records)

    # 2. Load Registry & Master to join metadata
    meta_dict = {}

    if REGISTRY_PATH.is_file():
        df_reg = pd.read_csv(REGISTRY_PATH, dtype={"video_id": str, "category_id": str})
        for _, row in df_reg.iterrows():
            vid = str(row["video_id"]).strip()
            if vid not in meta_dict:
                v_count = row.get("t0_view_count")
                if pd.isna(v_count) or v_count == 0:
                    v_count = row.get("t24_view_count", 0)
                l_count = row.get("t0_like_count", 0)
                c_count = row.get("t0_comment_count", 0)
                is_trend = 1 if row.get("chart_label_status") == "CHARTED" else 0

                meta_dict[vid] = {
                    "title": row.get("title", ""),
                    "channel_id": row.get("channel_id", ""),
                    "channel_title": row.get("channel_title", ""),
                    "category_id": str(row.get("category_id", "24")),
                    "published_at": row.get("published_at", ""),
                    "view_count": float(v_count) if pd.notna(v_count) else 0.0,
                    "like_count": float(l_count) if pd.notna(l_count) else 0.0,
                    "comment_count": float(c_count) if pd.notna(c_count) else 0.0,
                    "is_trending": is_trend,
                }

    if MASTER_PATH.is_file():
        df_mast = pd.read_csv(MASTER_PATH, dtype={"video_id": str, "category_id": str})
        for _, row in df_mast.iterrows():
            vid = str(row["video_id"]).strip()
            if vid not in meta_dict or meta_dict[vid]["view_count"] == 0:
                meta_dict[vid] = {
                    "title": row.get("title", ""),
                    "channel_id": row.get("channel_id", ""),
                    "channel_title": row.get("channel_title", ""),
                    "category_id": str(row.get("category_id", "24")),
                    "published_at": row.get("published_at", ""),
                    "view_count": float(row.get("view_count", 0)),
                    "like_count": float(row.get("like_count", 0)),
                    "comment_count": float(row.get("comment_count", 0)),
                    "is_trending": int(row.get("is_trending", 0)),
                }

    # 3. Merge metadata into aggregated sentiment frame
    merged_rows = []
    for _, r in vid_sent_df.iterrows():
        vid = r["video_id"]
        meta = meta_dict.get(vid, {
            "title": "",
            "channel_id": "",
            "channel_title": "",
            "category_id": "24",
            "published_at": "",
            "view_count": 0.0,
            "like_count": 0.0,
            "comment_count": 0.0,
            "is_trending": 0,
        })
        row_dict = r.to_dict()
        row_dict.update(meta)
        merged_rows.append(row_dict)

    final_df = pd.DataFrame(merged_rows)

    # 4. Feature engineering for Modeling & EDA
    final_df["log_view_count"] = np.log1p(final_df["view_count"].clip(lower=0))
    final_df["log_like_count"] = np.log1p(final_df["like_count"].clip(lower=0))
    final_df["like_to_view_ratio"] = final_df["like_count"] / (final_df["view_count"] + 1)
    final_df["comment_to_view_ratio"] = final_df["comment_count"] / (final_df["view_count"] + 1)

    # Parse published hour in Japan Standard Time (UTC+9)
    pub_dt = pd.to_datetime(final_df["published_at"], utc=True, errors="coerce")
    pub_jst = pub_dt.dt.tz_convert("Asia/Tokyo")
    final_df["upload_hour_jst"] = pub_jst.dt.hour.fillna(12).astype(int)
    final_df["upload_dayofweek"] = pub_jst.dt.dayofweek.fillna(0).astype(int)
    final_df["is_weekend"] = final_df["upload_dayofweek"].isin([5, 6]).astype(int)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print("\n=======================================================")
    print("RQ2 VIDEO-LEVEL DATASET BUILT (HT-05)")
    print(f"Total videos: {len(final_df)}")
    print(f"Saved to:     {OUTPUT_PATH}")
    print("\nSummary Statistics of Sentiment Ratios:")
    print(final_df[["positive_ratio", "negative_ratio", "neutral_ratio", "log_view_count"]].describe().round(4))
    print("=======================================================")


if __name__ == "__main__":
    build_rq2_dataset()
