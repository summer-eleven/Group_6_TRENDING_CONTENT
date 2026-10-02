from pathlib import Path
import pandas as pd
import torch
from transformers import pipeline

# Đường dẫn file
INPUT_PATH = Path("data/processed/comments_clean_JP.csv")
OUTPUT_PATH = Path("data/processed/comments_sentiment_JP.csv")

if not INPUT_PATH.exists():
    raise FileNotFoundError(f"Không tìm thấy file {INPUT_PATH}! Hãy hoàn thành bước trước.")

print("--> Đang tải dữ liệu sạch...")
comments = pd.read_csv(INPUT_PATH)
print(f"Tổng số comment cần phân loại: {len(comments)}")

# 1. Khởi tạo pipeline mô hình đa ngôn ngữ XLM-RoBERTa
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

# 2. Sanity Check kỹ thuật: Thử nghiệm 5 mẫu đầu tiên
print("\n" + "=" * 60)
print("TEST THỬ 5 KẾT QUẢ ĐẦU TIÊN:")
sample_texts = comments["comment_clean"].head(5).astype(str).tolist()
sample_preds = sentiment_pipe(sample_texts)

for text, pred in zip(sample_texts, sample_preds):
    print(f"Text: {text[:50]}...")
    print(f" -> Label: {pred['label'].lower()} | Score: {pred['score']:.4f}\n")
print("=" * 60)

# 3. Phân loại toàn bộ dữ liệu theo batch (tối ưu tốc độ)
print("--> Đang phân loại sentiment toàn bộ comments...")
texts = comments["comment_clean"].astype(str).str[:1000].tolist()

# Sử dụng batch_size=32 để chạy nhanh hơn nhiều so với gọi từng dòng
results = sentiment_pipe(texts, batch_size=32)

comments["sentiment"] = [res["label"].lower() for res in results]
comments["sentiment_score"] = [float(res["score"]) for res in results]

# 4. Xuất file kết quả theo yêu cầu bắt buộc
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
comments.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

print("\n" + "=" * 60)
print("PHÂN LOẠI HOÀN TẤT!")
print(f"- Đã lưu kết quả tại: {OUTPUT_PATH}")
print("\nPhân phối nhãn sentiment:")
print(comments["sentiment"].value_counts())
print(comments["sentiment"].value_counts(normalize=True).mul(100).round(2).astype(str) + " %")
print("=" * 60)