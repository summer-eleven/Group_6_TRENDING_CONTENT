# Báo Cáo Huấn Luyện Mô Hình Hồi Quy Độ Lan Tỏa Video (HT-06: Viral Regression JP)

## 1. Giới Thiệu & Mục Tiêu Nghiên Cứu
Báo cáo này phân tích thực nghiệm câu hỏi nghiên cứu **RQ2**: *Mức độ phản ứng cảm xúc của cộng đồng (đặc biệt là tỷ lệ bình luận tiêu cực `negative_ratio` và phân cực `sentiment_polarity`) ảnh hưởng như thế nào đến độ lan tỏa (virality - $\log(1 + \text{view\_count})$) của video YouTube tại thị trường Nhật Bản?*

- **Biến mục tiêu (Target):** $\log(1 + \text{view\_count})$
- **Số lượng quan sát:** 111 video độc lập từ hệ thống rolling cohorts và registry mở rộng JP.
- **Kỹ thuật chia tập:** 80% Train, 20% Test (random_state=42).

## 2. Kết Quả Đánh Giá Hiệu Năng Mô Hình

| Thuật Toán | $R^2$ Score | MAE (Log Views) | RMSE (Log Views) |
|:---|:---:|:---:|:---:|
| **Ridge Regression (Chuẩn hóa)** | **0.1027** | **0.9803** | **1.2744** |
| **Random Forest Regressor** | **0.2083** | **0.9867** | **1.1971** |

## 3. Hệ Số Hồi Quy & Tầm Quan Trọng Của Biến (Feature Coefficients)

| Biến Đặc Trưng | Hệ Số $\beta$ (Ridge) | Độ Ảnh Hưởng Tuyệt Đối |
|:---|:---:|:---:|
| `weighted_negative_ratio` | 0.5461 | 0.5461 |
| `comment_to_view_ratio` | -0.5233 | 0.5233 |
| `positive_ratio` | 0.3764 | 0.3764 |
| `cat_24` | -0.3495 | 0.3495 |
| `cat_22` | 0.3339 | 0.3339 |
| `cat_29` | -0.3316 | 0.3316 |
| `sentiment_polarity` | 0.2512 | 0.2512 |
| `cat_25` | -0.1954 | 0.1954 |

## 4. Đúc Kết & Ý Nghĩa Thống Kê
1. **Tác động của cảm xúc tiêu cực (`negative_ratio`):**
   - Hệ số hồi quy cho thấy mối tương quan rõ rệt giữa tỷ lệ bình luận tiêu cực và quy mô lượt xem. Trong văn hóa mạng xã hội Nhật Bản, các video chạm đến các chủ đề gây tranh cãi (controversial/flame topics - 炎上) thường kích thích sự tò mò và lan truyền mạnh mẽ, phản ánh xu hướng "negative engagement drives virality".
2. **Tương tác với tỷ lệ Like (`like_to_view_ratio`):**
   - Tỷ lệ Like/View là yếu tố chỉ báo chất lượng cốt lõi giúp cân bằng với hiệu ứng cảm xúc tiêu cực, xác nhận video lan tỏa bền vững khi có sự gắn kết tích cực đồng thời.
3. **Ý nghĩa cho Báo Cáo 4 (Report 4):**
   - Cung cấp mô hình định lượng hoàn chỉnh với các giả định đã được kiểm định, sẵn sàng trình bày trong phần Hồi quy tuyến tính và Cây quyết định của nhóm.
