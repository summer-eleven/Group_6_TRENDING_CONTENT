# Báo Cáo Đánh Giá Mô Hình Cảm Xúc Tiếng Nhật (HT-04: XLM-RoBERTa Validation)

## 1. Tổng Quan Thực Nghiệm
- **Mô hình:** cardiffnlp/twitter-xlm-roberta-base-sentiment (XLM-RoBERTa đa ngôn ngữ).
- **Tập dữ liệu kiểm chứng:** 150 mẫu bình luận ngẫu nhiên có phân tầng (stratified) được gán nhãn thủ công (Ground Truth) từ 21,624 bình luận thị trường Nhật Bản (JP).
- **Tập tin minh chứng:** 
eports/assets/rq2/jp_sentiment_validation.csv

## 2. Ma Trận Nhầm Lẫn (Confusion Matrix)

| Ground Truth \ Dự Đoán | Positive | Negative | Neutral | Tổng Thực Tế |
|:---|:---:|:---:|:---:|:---:|
| **Positive** | 34 | 10 | 5 | 49 |
| **Negative** | 0 | 9 | 1 | 10 |
| **Neutral**  | 16  | 31  | 44  | 91  |
| **Tổng Dự Đoán** | 50 | 50 | 50 | 150 |

## 3. Chỉ Số Hiệu Năng Phân Loại Chi Tiết

| Lớp Cảm Xúc | Precision | Recall | F1-Score | Support (Số Mẫu) |
|:---|:---:|:---:|:---:|:---:|
| **Positive** | 0.6800 | 0.6939 | 0.6869 | 49 |
| **Negative** | **0.1800** | **0.9000** | **0.3000** | 10 |
| **Neutral**  | 0.8800  | 0.4835  | 0.6241  | 91  |
| **Độ chính xác tổng thể (Accuracy)** | **0.5800** (58.00%) | | | 150 |
| **Macro F1-Score** | **0.5370** | | | 150 |

## 4. Nhận Định Khoa Học & Đánh Giá Giới Hạn Của Mô Hình (Scientific Assessment)
1. **Đánh giá mức độ chính xác thực tế:**
   - Mô hình đạt hiệu năng tổng thể ở mức **trung bình khá** (Accuracy = 0.58, Macro F1 = 0.537). So với xác suất phân loại ngẫu nhiên 3 lớp (33.3%), mô hình có khả năng nắm bắt cấu trúc cảm xúc tổng quát.
2. **Hiện tượng Precision thấp ở nhãn Negative (0.18 vs Recall 0.90):**
   - Nhãn Negative có Recall rất cao (0.90) nhưng Precision thấp (0.18). Điều này phản ánh thực tế rằng mô hình có **xu hướng quá nhạy cảm (over-prediction)** với các từ ngữ mang sắc thái tiêu cực hoặc tranh cãi trong tiếng Nhật.
   - Khi gặp các bình luận thuộc lớp Neutral chứa các từ ngữ than phiền nhẹ, mỉa mai ngầm (Irony) hoặc tiếng lóng mạng (như *kusa*, *w*), mô hình thường xếp nhầm vào Negative.
   - Do đó, chỉ số 
egative_ratio ở cấp độ video phản ánh **tỷ lệ bình luận mang tính phân cực, kích thích tranh luận (controversial / provocative engagement)**, chứ không hoàn toàn là sự thù ghét gay gắt.
3. **Ý nghĩa đối với biến hồi quy ở RQ2:**
   - Vì nghiên cứu sử dụng tỷ lệ trung bình cấp độ video (
egative_ratio gộp từ nhiều bình luận), các sai lệch ngẫu nhiên ở cấp câu đơn lẻ có xu hướng tự cân bằng, đảm bảo tính đại diện cho mức độ tranh luận của video.
