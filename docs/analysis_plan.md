# Detailed Analysis Plan (Kế hoạch Phân tích Dữ liệu Chi tiết)
*Dự án: Phân tích các yếu tố ảnh hưởng tới Nội dung Thịnh hành trên YouTube (Group 6)*

## 1. Mục tiêu và Định hướng Nghiên cứu
Kế hoạch phân tích này được thiết kế để giải quyết hai câu hỏi nghiên cứu cốt lõi (đã chốt theo `finalize_analysis_plan.md`):
- **RQ1 (Thời điểm đăng tải):** Tác động của khung giờ xuất bản video (`upload_period`: Giờ hành chính vs. Giờ nghỉ ngơi) tới xác suất xuất hiện trên bảng xếp hạng Thịnh hành (`OBSERVED_CHARTED`).
- **RQ2 (Hiệu ứng cảm xúc bình luận):** Tác động của tỷ lệ bình luận tiêu cực (`negative_ratio` / `weighted_negative_ratio`) đo lường qua mô hình Transformer NLP tới độ lan tỏa (`log_view_count`) của video tại thị trường Nhật Bản (thay thế cho `dislike_count` do YouTube API đã ẩn công khai).

---

## 2. Phân tích Khám phá Dữ liệu (EDA)

### 2.1. Thống kê Mô tả
- **Phân tích đơn biến (Univariate Analysis):**
  - Tính toán các chỉ số thống kê mô tả (Mean, Median, Standard Deviation, Min, Max, Skewness) cho các biến định lượng: `view_count`, `log_view_count`, `negative_ratio`, `positive_ratio`, `like_to_view_ratio`, `comment_to_view_ratio`.
  - Phân tích tần số và tỷ lệ cho các biến phân loại: `upload_period`, `chart_status`, `category_id`, `region_code`.
- **Phân tích hai biến (Bivariate Analysis):**
  - Lập bảng chéo (Contingency Table $2 \times 2$) giữa `upload_period` và `chart_status` theo từng quốc gia (VN, JP, US).
  - Khảo sát phân phối của `negative_ratio` và `log_view_count` qua các nhóm danh mục `category_id`.

### 2.2. Kế hoạch Trực quan hóa Dữ liệu (Visualization Plan)
- **Biểu đồ tỷ lệ quan sát Trending (RQ1):** Biểu đồ cột ghép (Grouped Bar chart) so sánh tỷ lệ vào Chart giữa Giờ hành chính và Giờ nghỉ ngơi giữa Việt Nam và Nhật Bản.
- **Biểu đồ phân bố 24 giờ đăng tải:** Biểu đồ đường (Line plot) thể hiện mật độ đăng video trong ngày theo múi giờ địa phương (ICT vs JST).
- **Biểu đồ phân bố cảm xúc bình luận (RQ2):** Biểu đồ tròn/cột phân bố 3 nhãn cảm xúc Positive, Negative, Neutral trên 21,624 bình luận JP.
- **Biểu đồ phân tán (Scatter Plot RQ2):** Thể hiện mối tương quan giữa `weighted_negative_ratio` và $\log(1 + \text{view\_count})$.
- **Biểu đồ hộp (Boxplot RQ2):** Phân bố `negative_ratio` theo từng thể loại video tại Nhật Bản.

---

## 3. Kiểm định Giả thuyết Thống kê (Statistical Hypothesis Testing)

### 3.1. Kiểm định RQ1: Thời điểm đăng và Xu hướng Thịnh hành
- **Giả thuyết:**
  - $H_0$: Không có mối liên hệ giữa thời điểm đăng video (Giờ hành chính vs Giờ nghỉ) và xác suất lọt vào bảng xếp hạng Trending.
  - $H_1$: Có mối liên hệ có ý nghĩa thống kê giữa thời điểm đăng video và xác suất lọt vào bảng xếp hạng Trending.
- **Phương pháp:** Kiểm định Chi-Square ($\chi^2$) về tính độc lập trên bảng chéo $2 \times 2$. Ngưỡng ý nghĩa $\alpha = 0.05$.

### 3.2. Kiểm định RQ2: Tương tác bình luận tiêu cực và Độ lan tỏa
- **Giả thuyết:**
  - $H_0$: Tỷ lệ bình luận tiêu cực không có mối quan hệ với độ lan tỏa của video ($\beta_{\text{negative}} = 0$).
  - $H_1$: Tỷ lệ bình luận tiêu cực có mối liên hệ với độ lan tỏa của video ($\beta_{\text{negative}} \neq 0$).
- **Phương pháp:** Kiểm định $t$-test cho hệ số hồi quy trong mô hình OLS và so sánh hiệu năng giải thích với Random Forest Regressor.

---

## 4. Xây dựng Mô hình Dự đoán & Phân tích Đa biến (Modeling)
- **Biến mục tiêu:** $\log(1 + \text{view\_count})$
- **Biến độc lập chính:** `negative_ratio`, `weighted_negative_ratio`, `positive_ratio`
- **Biến kiểm soát:** `like_to_view_ratio`, `comment_to_view_ratio`, `category_id`, `upload_hour_jst`, `is_weekend`
- **Mô hình triển khai (theo chuẩn Report 4):**
  1. **Ridge Regression:** Mô hình tuyến tính chuẩn hóa L2 giúp xử lý đa cộng tuyến và đánh giá trọng số $\beta$.
  2. **Random Forest Regressor:** Mô hình phi tuyến dựa trên quần thể cây quyết định nắm bắt các tương tác phi tuyến phức tạp.
- **Tiêu chuẩn đánh giá:** $R^2$, MAE, RMSE, 5-Fold Cross Validation.
