# Data Dictionary - YouTube Trending Content Analysis

Document này định nghĩa từ điển dữ liệu chính thức cho hệ thống thu thập và xử lý dữ liệu YouTube, được đối chiếu trực tiếp từ thiết kế ban đầu và kết quả thực tế từ module `youtube_crawler`.

---

## 1. Schema Overview & Field Reconciliation

| Variable | Description | Data Type | Role | Status | Source & Processing Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`video_id`** | Unique identifier of a YouTube video | String | Identifier | **Available Now** | Trích xuất trực tiếp từ `videoId` của crawler. |
| **`title`** | Title of the video | String | Feature | **Available Now** | Trích xuất trực tiếp từ `title.runs[0].text`. |
| **`channel`** | Name of the YouTube channel publishing the video | String | Feature | **Available Now** | Field bổ sung thực tế từ crawler (`ownerText.runs[0].text`). |
| **`views`** | Raw video view count as displayed on YouTube | String | Raw Feature | **Available Now** | Lấy dạng văn bản trực tiếp từ crawler (`viewCountText.simpleText`, ví dụ: `"1.2M views"`). |
| **`view_count`** | Cleaned numerical view count | Integer | Popularity Indicator | **Derivable** | Chuyển đổi và trích xuất số nguyên từ trường `views`. |
| **`published`** | Publication time description from YouTube | String | Raw Feature | **Available Now** | Lấy từ crawler (`publishedTimeText.simpleText`, ví dụ: `"2 days ago"`). Cần chuẩn hóa sang `DateTime` ở bước processing. |
| **`url`** | Direct link to the YouTube video | String | Feature | **Derivable** | Tạo tự động từ dạng `https://www.youtube.com/watch?v={video_id}`. |
| **`search_query`** | Search keyword used during data crawling | String | Feature / Metadata | **Available Now** | Field bổ sung thực tế lưu vết từ khóa tìm kiếm. |
| **`like_count`** | Total number of likes | Integer | Engagement Feature | **Not Yet Collected** | Chức năng thu thập `like_count` chưa được tích hợp trong crawler hiện tại. |
| **`comment_count`** | Total number of comments | Integer | Engagement Feature | **Not Yet Collected** | Chức năng thu thập `comment_count` chưa được tích hợp trong crawler hiện tại. |
| **`trending_status`** | Indicates whether the video is trending | Boolean | Target | **Not Yet Collected** | Hiện tại crawler chưa gắn nhãn hoặc thu thập cờ dữ liệu xu hướng. |
| **`category_id`** | YouTube video category identifier | String | Feature | **Not Yet Collected** | Trích xuất danh mục video chưa được hỗ trợ bởi crawler hiện tại. |

---

## 2. Summary of Field Statuses

* **Available Now:** `video_id`, `title`, `channel`, `views`, `published`, `search_query`
* **Derivable (Tính toán/Biến đổi từ Raw):** `view_count` (từ `views`), `url` (từ `video_id`), `published` (chuẩn hóa sang timestamp/DateTime)
* **Not Yet Collected (Chưa thu thập):** `like_count`, `comment_count`, `trending_status`, `category_id`

---
*Ghi chú cho Pipeline Week 3:* Chỉ đẩy các trường có trạng thái **Available Now** và **Derivable** vào cơ sở dữ liệu (Database Layer). Không tạo các trường giả lập cho các dữ liệu thuộc nhóm **Not Yet Collected**.


---

## 3. RQ1 Rolling Cohort Standardized Schema (Nhiệm vụ HA2)

Dành riêng cho nghiên cứu RQ1 (Ảnh hưởng của thời điểm đăng tải video đến khả năng lọt trending) kết hợp Rolling Cohort 24h và cửa sổ quan sát chart 7 ngày:

| STT | Tên trường | Kiểu dữ liệu | Vai trò trong RQ1 | Mô tả & Quy tắc xử lý | Giá trị mẫu / Định dạng |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | **`video_id`** | String | Định danh chính | Unique video ID trên YouTube (11 ký tự). Khử trùng cấp độ global khi đếm >= 100.000. | `"kJQP7kiw5Fk"` |
| 2 | **`region_code`** | String | Phân nhóm thị trường | Thị trường phát hiện / kiểm tra chart (`JP`, `VN`, `US`). | `"JP"` |
| 3 | **`discovered_at`** / **`first_seen_at`** | Timestamp | Audit / Tracking | Thời điểm hệ thống phát hiện video lần đầu tiên qua cohort discovery. Chuẩn UTC ISO 8601. | `"2026-10-13T10:00:00Z"` |
| 4 | **`published_at`** | Timestamp | Biến thời gian gốc | Thời điểm đăng tải gốc của video theo chuẩn UTC ISO 8601. | `"2026-10-13T01:30:00Z"` |
| 5 | **`local_upload_hour`** | Integer (0-23) | Biến giải thích chính (X) | Giờ đăng tải theo giờ địa phương của thị trường:<br>• JP: UTC + 9 (`Asia/Tokyo`)<br>• VN: UTC + 7 (`Asia/Ho_Chi_Minh`)<br>• US: Giờ địa phương chuẩn hóa. | `10` (10:30 sáng JST) |
| 6 | **`upload_period`** | Categorical | Phân nhóm phân tích | Phân loại giờ làm việc / giờ nghỉ theo quy ước Report 1:<br>• `Office`: Giờ hành chính (ví dụ 09:00 - 17:00)<br>• `Rest`: Giờ nghỉ ngơi / ngoài giờ. | `"Office"` |
| 7 | **`category_id`** | String / Integer | Biến kiểm soát | ID phân loại danh mục nội dung trên YouTube (Music, Gaming, Entertainment,...). | `"10"` |
| 8 | **`T0_at`** | Timestamp | Mốc thời gian Cohort | Thời điểm đo lường metrics ban đầu ($T_0$) ngay khi phát hiện. Chuẩn UTC. | `"2026-10-13T10:05:00Z"` |
| 9 | **`T24_at`** | Timestamp | Mốc thời gian Cohort | Thời điểm đo lường metrics sau 24 giờ ($T_{24}$). Chuẩn UTC. | `"2026-10-14T10:10:00Z"` |
| 10 | **`elapsed_hours`** | Float | Kiểm tra độ trễ đo lường | Số giờ trôi qua thực tế giữa $T_{24}$ và $T_0$: `(T24_at - T0_at) / 3600`. Gán cờ `DELAYED` nếu chênh lệch đáng kể so với 24.0h. | `24.08` |
| 11 | **`chart_status`** | Categorical | Biến mục tiêu chính (Y) | Trạng thái xuất hiện trên YouTube mostPopular trong 7 ngày:<br>• `OBSERVED_CHARTED`: Video xuất hiện trên chart ít nhất 1 lần.<br>• `UNKNOWN` / `INCOMPLETE`: Chưa vào chart nhưng thiếu dữ liệu quan sát do máy tắt.<br>• Tuyệt đối KHÔNG tự ý gán `NON_TRENDING` khi chưa đủ 7 ngày quan sát đầy đủ. | `"OBSERVED_CHARTED"` |
| 12 | **`chart_coverage_ratio`** | Float (0.0 - 1.0) | Đánh giá chất lượng đo lường | Tỷ lệ số lần chart monitor quan sát thành công trong cửa sổ 7 ngày: `actual_chart_calls / expected_chart_calls`. | `0.95` |
| 13 | **`best_rank`** | Integer (1-50) / NA | Mức độ phổ biến | Thứ hạng cao nhất đạt được trên top 50 Trending trong cửa sổ 7 ngày. `NA` nếu chưa vào chart. | `12` |
| 14 | **`valid_for_rq1`** | Boolean | Lọc mẫu nghiên cứu | Điều kiện đưa vào mô hình RQ1 (`TRUE`/`FALSE`):<br>• Video có `published_at` hợp lệ.<br>• Đủ cặp $T_0$ và $T_{24}$ hợp lệ (không lỗi missing metrics).<br>• Đạt độ phủ quan sát chart tối thiểu theo thỏa thuận nhóm (hoặc đã `OBSERVED_CHARTED`). | `TRUE` |

---

## 4. Quy tắc phân loại và Khử trùng lặp (De-duplication Rules)

1. **Khử trùng Cấp độ Toàn cầu (Global Unique Count):**
   - Đếm trên trường `video_id` duy nhất độc lập với quốc gia: `n_distinct(video_id) >= 100,000`.
   - Một video có thể xuất hiện ở cả VN, US và JP nhưng toàn nhóm chỉ tính là 1 đơn vị dữ liệu độc nhất.

2. **Khử trùng Cấp độ Thị trường (Market / Country Level):**
   - Mỗi đơn vị quan sát cho RQ1 theo quốc gia được xác định bởi cặp khóa `(video_id, region_code)`.

3. **Cửa sổ quan sát 7 ngày (7-day Observation Window):**
   - `OBSERVED_CHARTED`: Video có ít nhất 1 lần xuất hiện trong danh sách mostPopular trong 7 ngày kể từ lúc phát hiện.
   - `UNKNOWN / INCOMPLETE`: Video chưa từng xuất hiện trên chart nhưng số giờ máy tính chạy theo dõi không đạt ngưỡng độ phủ tối thiểu (ví dụ `chart_coverage_ratio < 0.70`).

---

## 5. RQ2 Comment Sentiment & Virality Modeling Schema (Nhiệm vụ HT-05 / HT-06)

Dành cho nghiên cứu RQ2 (Ảnh hưởng của phản ứng cảm xúc cộng đồng đến độ lan tỏa của video trên YouTube Nhật Bản) và mô hình hồi quy giải thích độ lan tỏa (Virality Regression):

### A. Bình luận cấp vi mô (Comment-Level Schema: `data/processed/comments_sentiment_JP.csv`)

| Tên trường | Kiểu dữ liệu | Vai trò | Mô tả chi tiết | Ví dụ |
| :--- | :--- | :--- | :--- | :--- |
| **`comment_id`** | String | Định danh | ID độc nhất của bình luận YouTube. Khử trùng lặp trên toàn bộ các mẻ cào. | `"UgwxXYZ123"` |
| **`video_id`** | String | Khóa ngoại | Video chứa bình luận (11 ký tự). | `"QDaqG4FUYAM"` |
| **`region_code`** | String | Phân vùng | Phân vùng thị trường nghiên cứu (`JP`). | `"JP"` |
| **`comment_clean`** | String | Văn bản sạch | Văn bản bình luận sau khi xử lý token hóa URL (`<URL>`), bảo toàn Kanji, Katakana, Hiragana, Emoji. | `"最高に面白い！ <URL>"` |
| **`comment_like_count`** | Integer | Trọng số ảnh hưởng | Số lượt thích của riêng bình luận đó từ người xem khác. | `24` |
| **`sentiment`** | Categorical | Nhãn cảm xúc | Kết quả phân loại từ mô hình XLM-RoBERTa (`positive`, `negative`, `neutral`). | `"positive"` |
| **`sentiment_score`** | Float (0.0 - 1.0) | Độ tin cậy mô hình | Xác suất (Softmax score) mà mô hình gán cho nhãn cảm xúc dự đoán. | `0.8924` |

### B. Video cấp vĩ mô (Video-Level Dataset Schema: `data/processed/rq2_video_sentiment_JP.csv`)

| Tên trường | Kiểu dữ liệu | Vai trò trong RQ2/Report 4 | Công thức / Mô tả quy chuẩn |
| :--- | :--- | :--- | :--- |
| **`video_id`** | String | Định danh chính | Khóa chính của video trong tập dữ liệu hồi quy. |
| **`sample_comment_count`** | Integer | Cỡ mẫu bình luận | Số lượng bình luận được cào và phân loại của video (tối đa 80/video). |
| **`positive_ratio`** | Float [0, 1] | Tỷ lệ tích cực | `positive_count / sample_comment_count` |
| **`negative_ratio`** | Float [0, 1] | Biến giải thích chính ($X_1$) | `negative_count / sample_comment_count` (Đo lường mức độ gây tranh cãi/phẫn nộ). |
| **`neutral_ratio`** | Float [0, 1] | Tỷ lệ trung tính | `neutral_count / sample_comment_count` |
| **`sentiment_polarity`** | Float [-1, 1] | Cực tính cảm xúc ($X_2$) | `(positive_count - negative_count) / sample_comment_count` |
| **`weighted_negative_ratio`**| Float [0, 1] | Tiêu cực có trọng số ($X_3$)| Tỷ lệ bình luận tiêu cực có điều chỉnh theo trọng số số lượt thích `log1p(comment_like_count)`. |
| **`view_count`** | Float | Quy mô lượt xem | Lượt xem đo lường tại thời điểm khảo sát hoặc $T_0$. |
| **`log_view_count`** | Float | Biến mục tiêu ($Y$) | $\log(1 + \text{view\_count})$ dùng trong mô hình hồi quy tuyến tính OLS/Ridge/Random Forest. |
| **`like_to_view_ratio`** | Float | Biến tương tác ($X_4$) | $\text{like\_count} / (\text{view\_count} + 1)$ (Đo lường mức độ đồng thuận tích cực). |
| **`comment_to_view_ratio`**| Float | Biến tương tác ($X_5$) | $\text{comment\_count} / (\text{view\_count} + 1)$ (Mức độ kích thích thảo luận). |
| **`upload_hour_jst`** | Integer (0-23) | Biến thời gian | Giờ đăng tải theo múi giờ Nhật Bản (JST = UTC + 9). |
| **`is_weekend`** | Binary (0, 1) | Biến mùa vụ | 1 nếu video đăng vào Thứ 7 hoặc Chủ Nhật theo giờ JST, ngược lại 0. |
| **`is_trending`** | Binary (0, 1) | Cờ xu hướng | 1 nếu video từng xuất hiện trên bảng mostPopular Trending, 0 nếu không. |

