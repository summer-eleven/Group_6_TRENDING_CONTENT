# Research Variables Table

| Variable | Type | Role | Purpose |
| --- | --- | --- | --- |
| `upload_hour` / `publish_time` | Datetime / Categorical | **Independent Variable** (IV1) | Phân loại khung giờ đăng video (khung giờ hành chính vs. khung giờ nghỉ ngơi/vàng) để đánh giá tác động tới khả năng lọt Top Trending (RQ1). |
| `dislike_count` | Numerical (Discrete) | **Independent Variable** (IV2) | Đo lường mức độ tương tác tiêu cực của người dùng để kiểm định ảnh hưởng tới mức độ viral và duy trì xu hướng của video (RQ2). |
| `is_trending` / `time_to_trend` | Binary (0/1) / Numerical | **Dependent Variable** (DV1) | Đánh giá trạng thái và tốc độ (số giờ/ngày) video đạt Top Trending dưới ảnh hưởng của thời điểm đăng (RQ1). |
| `view_count` / `trending_duration` | Numerical (Continuous) | **Dependent Variable** (DV2) | Đo lường hiệu suất lan truyền (tổng lượt xem hoặc số ngày trụ lại trên Top Trending) khi chịu tác động từ tương tác tiêu cực (RQ2). |
| `category_id` | Categorical | **Supporting Variable** (SV) | Phân loại danh mục video (Music, Gaming, News,...) giúp kiểm soát biến nhiễu do đặc thù riêng của từng thể loại. |
| `like_count` | Numerical (Discrete) | **Supporting Variable** (SV) | Dùng làm cơ sở so sánh đối chiếu và tính toán tỷ lệ tương tác (Dislike/Like ratio). |
| `comment_count` | Numerical (Discrete) | **Supporting Variable** (SV) | Mức độ thảo luận chung của người xem, hỗ trợ phân tích độ sôi nổi của video. |
| `video_id` / `title` | Text / String | **Supporting Variable** (SV) | Định danh dữ liệu và phục vụ phân tích khám phá (EDA) các từ khóa giật gân trong tiêu đề. |
