# Data Source

## Data Source
YouTube Trending Videos — dữ liệu công khai được thu thập thông qua YouTube Data API v3.

Phạm vi thu thập tập trung vào hai yếu tố chính phục vụ nghiên cứu:
- **Upload Time** (thời gian đăng tải video)
- **Negative User Engagement** (mức độ tương tác tiêu cực của người dùng)

## API
- **Tên API:** YouTube Data API v3
- **Nhà cung cấp:** Google Cloud Platform
- **Endpoint chính sử dụng:**
  - `videos.list` với tham số `chart=mostPopular` — lấy danh sách video trending theo khu vực (`regionCode`)
  - `commentThreads.list` — lấy comment của video (phục vụ phân tích negative engagement)
- **Xác thực:** API Key (tạo qua Google Cloud Console)
- **Giới hạn (Quota):** Mặc định 10,000 units/ngày; mỗi request `videos.list` tốn khoảng 1 unit, `commentThreads.list` tốn khoảng 1 unit/request

> **Lưu ý quan trọng:** YouTube đã ngừng công khai số liệu `dislikeCount` từ tháng 12/2021. Vì vậy "Negative User Engagement" cần được định nghĩa lại thông qua các chỉ số thay thế như:
> - Tỉ lệ comment mang tính tiêu cực (qua sentiment analysis)
> - Tỉ lệ comment/view bất thường
> - Các chỉ số gián tiếp khác cần thảo luận thêm với nhóm Data Analysis (Hà)

## Available Fields

| Field | Nguồn (Endpoint) | Mô tả |
|---|---|---|
| `id` | videos.list | ID video |
| `snippet.publishedAt` | videos.list | Thời gian upload video |
| `snippet.title` | videos.list | Tiêu đề video |
| `snippet.channelId` / `channelTitle` | videos.list | Kênh đăng tải |
| `snippet.categoryId` | videos.list | Danh mục video |
| `snippet.tags` | videos.list | Tag của video |
| `statistics.viewCount` | videos.list | Lượt xem |
| `statistics.likeCount` | videos.list | Lượt like |
| `statistics.commentCount` | videos.list | Tổng số comment |
| `snippet.textDisplay` | commentThreads.list | Nội dung comment (phục vụ phân tích cảm xúc) |
| `snippet.publishedAt` (comment) | commentThreads.list | Thời gian đăng comment |

## Data Collection Method

1. Sử dụng Python với thư viện `google-api-python-client` để gọi API.
2. Thu thập dữ liệu định kỳ (đề xuất: 1 lần/ngày) để theo dõi biến động theo thời gian upload.
3. Lưu response gốc (raw JSON) trước khi qua bước xử lý, nhằm đảm bảo có thể tái xử lý nếu cần.
4. Xử lý lỗi và giới hạn quota: thêm cơ chế retry, log lỗi khi vượt quota hoặc lỗi kết nối.
5. Dữ liệu thô sau khi thu thập sẽ được chuyển sang bước lưu trữ (xem `data_pipeline.md`).

## Việc cần làm tiếp theo
- [ ] Tạo Google Cloud Project và bật YouTube Data API v3
- [ ] Tạo API Key và test thử gọi `videos.list`
- [ ] Xác định danh sách `regionCode` cần thu thập (VD: VN, US...)
- [ ] Thảo luận với Hà về cách định nghĩa "Negative Engagement" thay thế cho dislikeCount
