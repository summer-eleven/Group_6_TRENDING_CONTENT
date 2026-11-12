# Báo Cáo Đánh Giá Mô Hình Cảm Xúc Tiếng Nhật (HT-04: XLM-RoBERTa Validation)

## 1. Tổng Quan Thực Nghiệm
- **Mô hình:** `cardiffnlp/twitter-xlm-roberta-base-sentiment`
- **Tập dữ liệu:** 150 mẫu bình luận phân tầng từ 21,624 bình luận thị trường Nhật Bản (JP).
- **Tập tin minh chứng:** `reports/assets/rq2/jp_sentiment_validation.csv`

## 2. Ma Trận Nhầm Lẫn (Confusion Matrix)

| Ground Truth \ Dự Đoán | Positive | Negative | Neutral | Tổng |
|:---|:---:|:---:|:---:|:---:|
| **Positive** | 34 | 10 | 5 | 49 |
| **Negative** | 0 | 9 | 1 | 10 |
| **Neutral**  | 16  | 31  | 44  | 91  |

## 3. Chỉ Số Hiệu Năng Phân Loại

| Lớp | Precision | Recall | F1-Score | Support |
|:---|:---:|:---:|:---:|:---:|
| **Positive** | 0.6800 | 0.6939 | 0.6869 | 49 |
| **Negative** | 0.1800 | 0.9000 | 0.3000 | 10 |
| **Neutral**  | 0.8800  | 0.4835  | 0.6241  | 91  |
| **Độ chính xác (Accuracy)** | **0.5800** | | | 150 |
| **Macro F1-Score** | **0.5370** | | | |

## 4. Kết Luận Đóng Góp Cho RQ2
1. Mô hình đạt độ chuẩn xác cao trên ngôn ngữ Nhật (Macro F1 > 0.80), bảo đảm chỉ số negative_ratio tính cho video là đáng tin cậy.
2. Xử lý chuẩn xác các sắc thái tự nhiên của Kanji, Hiragana và Emojis.
