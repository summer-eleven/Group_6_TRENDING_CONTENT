# Analysis Plan - YouTube Trending Content Project

## 1. Overview & Objectives (Tổng quan & Mục tiêu)
Kế hoạch phân tích dữ liệu này xác định lộ trình kỹ thuật chi tiết để kiểm định các Giả thuyết Nghiên cứu (Hypotheses) và xây dựng các mô hình phân tích cho hai câu hỏi nghiên cứu chính:
* **RQ1 (Thời điểm đăng video):** Đánh giá tác động của Thời điểm đăng video (`upload_hour`) tới khả năng lọt Top Trending (`is_trending`) và tốc độ lọt top (`time_to_trend`).
* **RQ2 (Tương tác tiêu cực):** Đánh giá tác động của Tương tác tiêu cực (Negative User Engagement) tới hiệu suất viral (`view_count`) và độ duy trì xu hướng (`trending_duration`) của video.
  * *Lưu ý cập nhật dữ liệu:* Do YouTube Data API v3 không còn công khai `dislike_count`, Tương tác tiêu cực được đo lường thông qua **Phân tích cảm xúc bình luận (Comment Sentiment Analysis)** thu thập từ API `commentThreads.list` (`negative_comment_ratio` / `negative_comment_count`).

---

## 2. Research Hypotheses & Variables Matrix (Giả thuyết & Ma trận Biến số)

### 2.1. Giả thuyết Nghiên cứu
* **RQ1 - Thời điểm đăng video:**
  * **$H_{01}$:** Thời điểm đăng video (`upload_hour` / khung giờ hành chính vs. giờ nghỉ ngơi) không có sự khác biệt có ý nghĩa thống kê đối với khả năng lọt Top Trending (`is_trending`) hoặc tốc độ lọt top (`time_to_trend`).
  * **$H_{11}$:** Video được đăng vào khung giờ nghỉ ngơi/vàng có tỷ lệ lọt Top Trending cao hơn (hoặc thời gian lọt top ngắn hơn) có ý nghĩa thống kê so với khung giờ hành chính.
* **RQ2 - Tương tác tiêu cực:**
  * **$H_{02}$:** Lượng tương tác tiêu cực (tỷ lệ bình luận tiêu cực `negative_comment_ratio`) không có mối tương quan có ý nghĩa thống kê đến hiệu suất lan truyền (`view_count`) hoặc thời gian trụ top (`trending_duration`).
  * **$H_{12}$:** Lượng tương tác tiêu cực (tỷ lệ bình luận tiêu cực `negative_comment_ratio`) có mối tương quan thuận chiều và có ý nghĩa thống kê với tổng lượt xem (`view_count`) và độ duy trì xu hướng (`trending_duration`).

### 2.2. Ma trận Biến số & Feature Engineering
| Biến số | Loại biến | Vai trò | Mô tả / Công thức tính |
| :--- | :--- | :--- | :--- |
| `upload_hour` / `publish_time` | Datetime / Categorical | Independent (IV1) | Giờ đăng video trích xuất từ `published_at` (Phân loại: Hành chính vs Nghỉ ngơi/Vàng). |
| `negative_comment_ratio` | Numerical (Continuous) | Independent (IV2) | Tỷ lệ bình luận tiêu cực = $\frac{\text{Số comment tiêu cực}}{\text{Tổng comment thu thập}}$. Trích xuất qua NLP Sentiment Analysis. |
| `is_trending` | Binary (0/1) | Dependent (DV1) | Trạng thái video lọt Top Trending (1: Có, 0: Không). |
| `time_to_trend` | Numerical (Continuous) | Dependent (DV1) | Thời gian lọt top (giờ) = `collected_at` - `published_at`. |
| `view_count` | Numerical (Continuous) | Dependent (DV2) | Tổng lượt xem của video. |
| `trending_duration` | Numerical (Discrete) | Dependent (DV2) | Số ngày video duy trì trên bảng xếp hạng Trending. |
| `category_id` | Categorical | Supporting (SV) | Danh mục nội dung (Music, Gaming, News,...) để kiểm soát biến nhiễu. |
| `like_count`, `comment_count` | Numerical (Discrete) | Supporting (SV) | Mức độ tương tác tổng thể. |

---

## 3. Exploratory Data Analysis (EDA) & Visualization Plan

### 3.1. Tiền xử lý & Làm sạch dữ liệu
* **Xử lý giá trị thiếu (Missing Values):** Kiểm tra và xử lý các dòng thiếu comment hoặc thông tin meta.
* **Xử lý nhiễu & Trùng lặp (Deduplication):** Loại bỏ bản ghi trùng lặp theo `video_id` qua từng đợt cào dữ liệu.
* **Biến đổi dữ liệu (Log Transformation):** Áp dụng $log(x + 1)$ cho các biến phân bố lệch phải lớn như `view_count`, `like_count`, `comment_count`.
* **Trích xuất thuộc tính (Feature Extraction):** Phân tích Sentiment trên tập JSON bình luận (`comments_<video_id>.json`) sử dụng thư viện NLP (VADER / TextBlob / PhoBERT) để tính `negative_comment_ratio`.

### 3.2. Kế hoạch Trực quan hóa (Data Visualization)
* **Khung giờ đăng (RQ1):** Bar chart / Histogram so sánh số lượng và tỷ lệ video trending đăng trong khung giờ hành chính vs khung giờ nghỉ ngơi/vàng.
* **Tương tác tiêu cực (RQ2):** Scatter plot kèm đường xu hướng (Regression line) thể hiện mối tương quan giữa `negative_comment_ratio` với `view_count` và `trending_duration`.
* **Phân tích theo Danh mục (Category Analysis):** Boxplot thể hiện phân bố `negative_comment_ratio` và `view_count` giữa các `category_id`.
* **Ma trận Tương quan (Correlation Heatmap):** Kiểm tra đa cộng tuyến (Multicollinearity) giữa các biến độc lập và biến bổ trợ.

---

## 4. Statistical Analysis & Hypothesis Testing (Kiểm định Thống kê)

* **Kiểm định cho RQ1 (Thời điểm đăng):**
  * **Chi-Square Test of Independence:** Đánh giá mối liên hệ phụ thuộc giữa khung giờ đăng (`upload_hour`) và trạng thái `is_trending`.
  * **Two-sample t-test / Mann-Whitney U test:** So sánh trung bình/trung vị thời gian lọt top (`time_to_trend`) giữa 2 nhóm khung giờ.
* **Kiểm định cho RQ2 (Tương tác tiêu cực):**
  * **Pearson / Spearman Correlation Test:** Tính hệ số tương quan ($r$ / $\rho$) và p-value để xác định mức độ và chiều tương quan giữa `negative_comment_ratio` và `view_count` / `trending_duration`.

---

## 5. Machine Learning Plan (Kế hoạch Học máy)

### 5.1. Mô hình Phân loại (Classification Task)
* **Mục tiêu:** Dự đoán khả năng một video lọt Top Trending (`is_trending`: 0/1) dựa trên thông tin thời điểm đăng, danh mục và tương tác ban đầu.
* **Thuật toán áp dụng:**
  * **Logistic Regression:** Mô hình cơ sở (Baseline) để đánh giá hệ số tác động.
  * **Random Forest Classifier & XGBoost Classifier:** Mô hình phi tuyến tính nâng cao khả năng dự đoán và xử lý tương tác phức tạp giữa các thuộc tính.

### 5.2. Mô hình Hồi quy (Regression Task)
* **Mục tiêu:** Dự đoán mức độ lan truyền (`view_count`) hoặc độ duy trì xu hướng (`trending_duration`).
* **Thuật toán áp dụng:**
  * **Multiple Linear Regression / Ridge / Lasso:** Kiểm tra tác động tuyến tính của `negative_comment_ratio` khi kiểm soát các biến nhiễu.
  * **Random Forest Regressor / Gradient Boosting:** Dự đoán phi tuyến tính hiệu suất viral.

### 5.3. Phân tích Tầm quan trọng thuộc tính (Feature Importance)
* Trích xuất chỉ số **Feature Importance** từ Random Forest / XGBoost và áp dụng **SHAP (SHapley Additive exPlanations)** để định lượng mức độ đóng góp tương đối của `upload_hour` vs `negative_comment_ratio` vào hiệu suất của video.

---

## 6. Evaluation & Validation Plan (Đánh giá & Kiểm chứng)

### 6.1. Phương pháp Chia tập Dữ liệu (Data Splitting)
* Sử dụng **Stratified Train/Test Split (80/20)** hoặc **Time-series Split** dựa trên `published_at` để tránh rò rỉ dữ liệu tương lai (Data Leakage).

### 6.2. Tiêu chí Đánh giá Mô hình (Evaluation Metrics)
* **Mô hình Phân loại (`is_trending`):**
  * **Accuracy, Precision, Recall, F1-Score:** Đánh giá tổng thể và khả năng phát hiện đúng video trending.
  * **ROC-AUC Score:** Đánh giá phân tách giữa 2 lớp lọt top và không lọt top.
* **Mô hình Hồi quy (`view_count` / `trending_duration`):**
  * **Mean Absolute Error (MAE) & Root Mean Squared Error (RMSE):** Đo lường độ lệch dự báo lượt xem/ngày duy trì.
  * **$R^2$ Score (Coefficient of Determination):** Đo tỷ lệ biến thiên của biến phụ thuộc được giải thích bởi mô hình.

### 6.3. Kiểm chứng Ý nghĩa Thống kê (Validation)
* **Mức ý nghĩa $\alpha = 0.05$:** Mọi kiểm định thống kê và hệ số mô hình chỉ chấp nhận khi $p\text{-value} < 0.05$.
* **K-Fold Cross-Validation ($k=5$):** Đảm bảo tính ổn định của các mô hình Machine Learning, tránh hiện tượng Overfitting.
