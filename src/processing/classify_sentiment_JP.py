import sys
# Ensure UTF-8 output on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
from pathlib import Path
import pandas as pd
import torch
from transformers import pipeline

INPUT_PATH = Path("data/processed/comments_clean_JP.csv")
OUTPUT_PATH = Path("data/processed/comments_sentiment_JP.csv")

if not INPUT_PATH.exists():
    raise FileNotFoundError(f"Không tìm thấy file {INPUT_PATH}!")

print("--> Đang tải dữ liệu sạch...")
comments = pd.read_csv(INPUT_PATH)
total_count = len(comments)
print(f"Tổng số comment trong tập sạch: {total_count:,}")

# Incremental cache check
cached_dict = {}
if OUTPUT_PATH.exists():
    try:
        prev_df = pd.read_csv(OUTPUT_PATH)
        if "comment_id" in prev_df.columns and "sentiment" in prev_df.columns:
            for _, r in prev_df.iterrows():
                cid = str(r["comment_id"]).strip()
                cached_dict[cid] = (r["sentiment"], r.get("sentiment_score", 0.8))
        print(f"--> Tìm thấy {len(cached_dict):,} kết quả sentiment đã phân loại trước đó.")
    except Exception as e:
        print(f"Không thể đọc cache cũ: {e}")

# Identify comments that need classification
needs_pred = []
for idx, r in comments.iterrows():
    cid = str(r["comment_id"]).strip()
    if cid not in cached_dict:
        needs_pred.append(idx)

print(f"--> Số lượng comment mới cần phân loại AI: {len(needs_pred):,} / {total_count:,}")

if len(needs_pred) > 0:
    device = 0 if torch.cuda.is_available() else -1
    print(f"--> Đang tải model (Thiết bị sử dụng: {'GPU' if device == 0 else 'CPU'})...")

    sentiment_pipe = pipeline(
        "sentiment-analysis",
        model="cardiffnlp/twitter-xlm-roberta-base-sentiment",
        tokenizer="cardiffnlp/twitter-xlm-roberta-base-sentiment",
        truncation=True,
        max_length=512,
        device=device,
    )

    texts_to_pred = comments.loc[needs_pred, "comment_clean"].astype(str).str[:1000].tolist()
    print(f"--> Đang phân loại {len(texts_to_pred):,} comments mới (batch_size=64)...")
    results = sentiment_pipe(texts_to_pred, batch_size=64)

    for idx, res in zip(needs_pred, results):
        cid = str(comments.loc[idx, "comment_id"]).strip()
        cached_dict[cid] = (res["label"].lower(), float(res["score"]))

# Assign all sentiments
sentiments = []
scores = []
for _, r in comments.iterrows():
    cid = str(r["comment_id"]).strip()
    val = cached_dict.get(cid, ("neutral", 0.5))
    sentiments.append(val[0])
    scores.append(val[1])

comments["sentiment"] = sentiments
comments["sentiment_score"] = scores

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
comments.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

print("\n" + "=" * 60)
print("PHÂN LOẠI HOÀN TẤT!")
print(f"- Đã lưu kết quả tại: {OUTPUT_PATH}")
print(f"- Tổng số bình luận đã gán nhãn: {len(comments):,}")
print("\nPhân phối nhãn sentiment toàn bộ:")
print(comments["sentiment"].value_counts())
print(comments["sentiment"].value_counts(normalize=True).mul(100).round(2).astype(str) + " %")
print("=" * 60)
