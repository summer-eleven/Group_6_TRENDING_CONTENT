"""Consolidate all JP videos (Tier 1 cohorts + Tier 2 expansion) into a single 35k master CSV.

Outputs:
  data/processed/youtube_dataset_expansion_JP_35k.csv
"""

import json
from pathlib import Path
import pandas as pd

MASTER_CLEAN = Path("data/processed/youtube_dataset_2000_clean.csv")
REGISTRY_JP = Path("data/processed/youtube_cohort_registry_JP.csv")
EXPANSION_DIR = Path("data/raw/expansion_jp")
OUTPUT_CSV = Path("data/processed/youtube_dataset_expansion_JP_35k.csv")

unique_videos = {}

# 1. Master Clean (Tier 1 RQ1)
if MASTER_CLEAN.is_file():
    df_m = pd.read_csv(MASTER_CLEAN, dtype={"video_id": str, "category_id": str})
    df_m_jp = df_m[df_m["region_code"] == "JP"]
    for _, r in df_m_jp.iterrows():
        vid = str(r["video_id"]).strip()
        if vid and vid not in unique_videos:
            unique_videos[vid] = {
                "video_id": vid,
                "region_code": "JP",
                "title": r.get("title", ""),
                "channel_id": r.get("channel_id", ""),
                "channel_title": r.get("channel_title", ""),
                "category_id": r.get("category_id", "24"),
                "published_at": r.get("published_at", ""),
                "view_count": r.get("view_count", 0),
                "like_count": r.get("like_count", 0),
                "comment_count": r.get("comment_count", 0),
                "tier": "Tier_1_Cohort_Master",
                "source": "youtube_dataset_2000_clean",
            }
print(f"Loaded {len(unique_videos):,} from Master Clean JP.")

# 2. Cohort Registry JP
if REGISTRY_JP.is_file():
    df_r = pd.read_csv(REGISTRY_JP, dtype={"video_id": str, "category_id": str})
    for _, r in df_r.iterrows():
        vid = str(r["video_id"]).strip()
        if vid and vid not in unique_videos:
            v_cnt = r.get("t0_view_count")
            if pd.isna(v_cnt) or v_cnt == 0:
                v_cnt = r.get("t24_view_count", 0)
            unique_videos[vid] = {
                "video_id": vid,
                "region_code": "JP",
                "title": r.get("title", ""),
                "channel_id": r.get("channel_id", ""),
                "channel_title": r.get("channel_title", ""),
                "category_id": r.get("category_id", "24"),
                "published_at": r.get("published_at", ""),
                "view_count": v_cnt,
                "like_count": r.get("t0_like_count", 0),
                "comment_count": r.get("t0_comment_count", 0),
                "tier": "Tier_1_Cohort_Batches",
                "source": "youtube_cohort_registry_JP",
            }
print(f"Total unique after Cohort Registry: {len(unique_videos):,}")

# 3. Expansion Harvest JSONs (Tier 2)
if EXPANSION_DIR.is_dir():
    for f in sorted(EXPANSION_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            items = data.get("items", [])
            for r in items:
                vid = str(r.get("video_id", "")).strip()
                if vid and vid not in unique_videos:
                    unique_videos[vid] = {
                        "video_id": vid,
                        "region_code": "JP",
                        "title": r.get("title", ""),
                        "channel_id": r.get("channel_id", ""),
                        "channel_title": r.get("channel_title", ""),
                        "category_id": r.get("category_id", "24"),
                        "published_at": r.get("published_at", ""),
                        "view_count": r.get("t0_view_count", 0),
                        "like_count": r.get("t0_like_count", 0),
                        "comment_count": r.get("t0_comment_count", 0),
                        "tier": "Tier_2_Expansion_Harvest",
                        "source": f.name,
                    }
        except Exception as e:
            print(f"Error reading {f}: {e}")

final_df = pd.DataFrame(list(unique_videos.values()))
OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
final_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

print("\n" + "=" * 65)
print("CONSOLIDATED 35K JP DATASET EXPORT COMPLETE!")
print(f"Output File:           {OUTPUT_CSV}")
print(f"Total Unique Videos:   {len(final_df):,}")
print(f"Tier Breakdown:\n{final_df['tier'].value_counts().to_string()}")
print("=" * 65)
