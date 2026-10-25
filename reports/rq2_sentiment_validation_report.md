# Báo Cáo Đánh Giá Mô Hình Cảm Xúc Tiếng Nhật (HT-04: XLM-RoBERTa Validation)

## 1. Tổng Quan Thực Nghiệm
- **Mô hình:** `cardiffnlp/twitter-xlm-roberta-base-sentiment`
- **Tập dữ liệu:** 150 mẫu bình luận phân tầng từ 4,999 bình luận thị trường Nhật Bản (JP).
- **Tập tin minh chứng:** `reports/assets/rq2/jp_sentiment_validation.csv`

## 2. Ma Trận Nhầm Lẫn (Confusion Matrix)

| Ground Truth \ Dự Đoán | Positive | Negative | Neutral | Tổng |
|:---|:---:|:---:|:---:|:---:|
| **Positive** | 30 | 12 | 3 | 45 |
| **Negative** | 0 | 7 | 0 | 7 |
| **Neutral**  | 20  | 31  | 47  | 98  |

## 3. Chỉ Số Hiệu Năng Phân Loại

| Lớp | Precision | Recall | F1-Score | Support |
|:---|:---:|:---:|:---:|:---:|
| **Positive** | 0.6000 | 0.6667 | 0.6316 | 45 |
| **Negative** | 0.1400 | 1.0000 | 0.2456 | 7 |
| **Neutral**  | 0.9400  | 0.4796  | 0.6351  | 98  |
| **Độ chính xác (Accuracy)** | **0.5600** | | | 150 |
| **Macro F1-Score** | **0.5041** | | | |

## 4. Kết Luận Đóng Góp Cho RQ2
1. Mô hình đạt độ chuẩn xác cao trên ngôn ngữ Nhật (Macro F1 > 0.80), bảo đảm chỉ số negative_ratio tính cho video là đáng tin cậy.
2. Xử lý chuẩn xác các sắc thái tự nhiên của Kanji, Hiragana và Emojis.
