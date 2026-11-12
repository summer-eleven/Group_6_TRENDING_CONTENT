# Research Variables Table (Updated per Final Analysis Plan)

| Variable | Type | Role | Purpose |
| --- | --- | --- | --- |
| `upload_hour` / `upload_period` | Datetime / Categorical (Office vs Rest) | **Independent Variable** (IV1) | Phân loại khung giờ đăng video (Giờ hành chính: 08:00–17:00 vs. Giờ nghỉ ngơi: 17:01–07:59 địa phương) để đánh giá tác động tới xác suất lọt Top Trending (RQ1). |
| `negative_ratio` / `weighted_negative_ratio` | Numerical (Continuous, [0, 1]) | **Independent Variable** (IV2) | Đo lường tỷ lệ bình luận tiêu cực và phân cực cảm xúc từ khán giả thông qua mô hình NLP Transformer (CardiffNLP XLM-RoBERTa), thay thế cho `dislike_count` (do YouTube API đã ẩn chỉ số dislike công khai từ cuối năm 2021) để kiểm định ảnh hưởng tới độ lan tỏa của video (RQ2). |
| `chart_status` / `is_trending` | Binary (Categorical) | **Dependent Variable** (DV1) | Trạng thái video có xuất hiện trên bảng xếp hạng Trending Chart trong chu kỳ theo dõi có độ phủ hay không (`OBSERVED_CHARTED` vs `NOT_OBSERVED_WITH_COVERAGE`) (RQ1). |
| `log_view_count` ($\log(1 + \text{view\_count})$) | Numerical (Continuous) | **Dependent Variable** (DV2) | Đo lường độ lan tỏa (virality) quy chuẩn hóa phân phối lệch của lượt xem video khi chịu tác động từ cảm xúc bình luận (RQ2). |
| `positive_ratio` | Numerical (Continuous, [0, 1]) | **Supporting Variable** (SV) | Tỷ lệ bình luận tích cực, giúp kiểm soát mức độ gắn kết thiện cảm của khán giả. |
| `sentiment_polarity` | Numerical (Continuous, [-1, 1]) | **Supporting Variable** (SV) | Độ phân cực cảm xúc ròng (`positive_ratio - negative_ratio`). |
| `category_id` | Categorical | **Supporting Variable** (SV) | Phân loại danh mục video (Gaming, Comedy, Music, Entertainment,...) kiểm soát biến nhiễu đặc thù thể loại. |
| `like_to_view_ratio` | Numerical (Continuous) | **Supporting Variable** (SV) | Tỷ lệ Like trên View, phản ánh mức độ hài lòng cốt lõi của người xem. |
| `comment_to_view_ratio` | Numerical (Continuous) | **Supporting Variable** (SV) | Tỷ lệ bình luận trên View, đo lường mật độ tương tác đàm thoại. |
| `upload_hour_jst` / `is_weekend` | Numerical / Binary | **Supporting Variable** (SV) | Giờ xuất bản và cờ đánh dấu cuối tuần theo múi giờ Tokyo (Asia/Tokyo). |
