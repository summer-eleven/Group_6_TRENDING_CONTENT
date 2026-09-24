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

