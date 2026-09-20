# Analysis Plan - YouTube Trending Content Project

## 1. Overview & Objectives
Kế hoạch phân tích dữ liệu này nhằm xác định lộ trình kỹ thuật chi tiết để kiểm định các Giả thuyết Nghiên cứu (Hypotheses) liên quan đến hai câu hỏi chính:
- **RQ1:** Tác động của Thời điểm đăng video (`Upload Time`) tới khả năng lọt Top Trending.
- **RQ2:** Tác động của Tương tác tiêu cực (`Negative User Engagement` - Dislike, Comment tiêu cực) tới hiệu suất viral của video.

---

## 2. Exploratory Data Analysis (EDA) & Data Cleaning
- **Môi trường thực hiện:** Jupyter Notebook (`notebooks/1_Exploration.ipynb`) và **RStudio**.
- **Các bước thực hiện:**
  - **Kiểm tra & Làm sạch:** Xử lý giá trị khuyết thiếu (Missing values), dữ liệu trùng lặp (Duplicates) và các giá trị ngoại lệ (Outliers).
  - **Phân tích đơn biến (Univariate Analysis):** Tính toán các chỉ số thống kê mô tả (Mean, Median, Standard Deviation, Min, Max) cho các biến số định lượng (`view_count`, `dislike_count`, `time_to_trend`).
  - **Biến đổi dữ liệu (Feature Engineering):**
    - Trích xuất `upload_hour` và `upload_day` từ `publish_time`.
    - Gán nhãn khung giờ: **Khung giờ hành chính** (8h-17h) vs **Khung giờ nghỉ ngơi/vàng** (17h-23h, cuối tuần).
    - Tính toán tỷ lệ tương tác tiêu cực: $\text{Dislike Ratio} = \frac{\text{dislike\_count}}{\text{view\_count}}$.
  - **Xây dựng Data Dictionary:** Lập từ điển dữ liệu mô tả chi tiết từng thuộc tính trong dataset.

---

## 3. Data Visualization Plan
Tạo các biểu đồ trực quan hóa để phát hiện xu hướng và mô hình phân bố (sử dụng RStudio / Python Matplotlib & Seaborn):
- **Phân bố khung giờ (RQ1):** Biểu đồ cột (Bar chart) hoặc Histograms so sánh số lượng video lọt Top Trending được đăng trong khung giờ hành chính vs khung giờ nghỉ ngơi.
- **Tương quan tương tác tiêu cực (RQ2):** Biểu đồ phân tán (Scatter plot) kết hợp đường xu hướng thể hiện mối tương quan giữa `dislike_count` / Dislike Ratio và `view_count` / `trending_duration`.
- **So sánh theo danh mục (Category Comparison):** Biểu đồ hộp (Boxplot) thể hiện phân bố Dislike Ratio và số lượt xem giữa các nhóm `category_id`.
- **Ma trận tương quan (Correlation Heatmap):** Kiểm tra đa cộng tuyến giữa các biến độc lập và biến bổ trợ (`like_count`, `comment_count`, `view_count`).

---

## 4. Statistical Analysis & Hypothesis Testing
Thực hiện các kiểm định thống kê để bác bỏ hoặc chấp nhận giả thuyết $H_0 / H_1$:
- **Kiểm định cho RQ1 (Thời điểm đăng):** 
  - Sử dụng **Chi-Square Test of Independence** (đánh giá mối liên hệ giữa khung giờ đăng và trạng thái `is_trending`) hoặc **Two-sample t-test / Mann-Whitney U test** (so sánh thời gian lọt top `time_to_trend` giữa 2 khung giờ).
- **Kiểm định cho RQ2 (Tương tác tiêu cực):**
  - Sử dụng **Pearson / Spearman Correlation Test** để xác định mức độ tương quan giữa tỷ lệ Dislike và tổng lượng View.

---

## 5. Machine Learning Modeling & Evaluation
Xây dựng **2 mô hình Machine Learning** khác nhau trong `notebooks/2_Modeling.ipynb` và `src/modeling/model.py` để kiểm định và dự báo:

### Mô hình 1: Logistic Regression (Phân loại / Classification)
- **Mục tiêu:** Dự đoán xác suất một video có lọt Top Trending hay không dựa trên `upload_hour`, `category_id` và các chỉ số tương tác ban đầu.
- **Vai trò:** Đánh giá tầm quan trọng của yếu tố thời gian đăng video (RQ1).

### Mô hình 2: Random Forest Regressor / Gradient Boosting (Hồi quy / Regression)
- **Mục tiêu:** Dự đoán hiệu suất lan truyền (`view_count` hoặc `trending_duration`) dựa trên mức độ tương tác tiêu cực (`dislike_count`, comment ratio) và các biến bổ trợ.
- **Vai trò:** Kiểm định phi tuyến tính về tác động của tương tác tiêu cực (RQ2).

### Đánh giá & So sánh mô hình (Model Evaluation):
- **Phân loại (Classification):** Accuracy, Precision, Recall, F1-Score, ROC-AUC curve.
- **Hồi quy (Regression):** Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), $R^2$ Score.
- **Biện luận:** So sánh hiệu quả giữa 2 mô hình và đưa ra kết luận bác bỏ/chấp nhận $H_0$ dựa trên kết quả đầu ra.
