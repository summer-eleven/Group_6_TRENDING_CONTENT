# Data Pipeline

## Pipeline Overview

```
YouTube API → Python → MinIO (Raw) → Database
```

Pipeline được thiết kế theo hướng tách biệt giữa **lưu trữ dữ liệu thô (raw)** và **dữ liệu đã chuẩn hóa (processed)**, đảm bảo có thể truy vết và tái xử lý dữ liệu khi cần.

## Components

### 1. YouTube API
- Nguồn dữ liệu đầu vào (xem chi tiết tại `docs/data_source.md`)
- Trả về dữ liệu dạng JSON

### 2. Python (Thu thập & xử lý)
- Script gọi API định kỳ (scheduled job, VD: cron job chạy hằng ngày)
- Xử lý lỗi, retry khi request thất bại hoặc vượt quota
- Convert dữ liệu JSON thô, gắn thêm metadata (VD: `collected_at`)
- Đẩy dữ liệu thô lên MinIO
- Sau đó parse, làm sạch dữ liệu và ghi vào Database

### 3. MinIO (Raw Storage)
- Lưu trữ dữ liệu thô (raw JSON) ngay sau khi thu thập từ API
- Mục đích: backup, cho phép tái xử lý dữ liệu (re-parse) nếu logic xử lý thay đổi sau này
- Tổ chức thư mục theo ngày thu thập, ví dụ:
  ```
  raw/
    youtube/
      2026-09-12/
        trending_VN.json
        comments_<video_id>.json
  ```

### 4. Database (Processed Data)
- Lưu dữ liệu đã được làm sạch, chuẩn hóa theo schema cố định
- Phục vụ trực tiếp cho bước Data Analysis & Machine Learning (Hà)

## Dataset Schema (sơ bộ)

### Bảng `videos`

| Column | Type | Mô tả |
|---|---|---|
| video_id | VARCHAR (PK) | ID video |
| title | TEXT | Tiêu đề video |
| channel_id | VARCHAR | ID kênh |
| channel_title | VARCHAR | Tên kênh |
| category_id | INT | Danh mục video |
| published_at | TIMESTAMP | Thời gian upload video |
| view_count | BIGINT | Lượt xem |
| like_count | BIGINT | Lượt like |
| comment_count | BIGINT | Tổng số comment |
| region_code | VARCHAR | Khu vực trending |
| collected_at | TIMESTAMP | Thời điểm thu thập dữ liệu |

### Bảng `comments`

| Column | Type | Mô tả |
|---|---|---|
| comment_id | VARCHAR (PK) | ID comment |
| video_id | VARCHAR (FK → videos.video_id) | Video tương ứng |
| text | TEXT | Nội dung comment |
| published_at | TIMESTAMP | Thời gian đăng comment |
| sentiment_score | FLOAT (nullable) | Điểm cảm xúc (tính sau ở bước phân tích) |
| collected_at | TIMESTAMP | Thời điểm thu thập dữ liệu |

> Schema trên là sơ bộ, có thể điều chỉnh sau khi Hà hoàn thành `docs/variables.md` (xác định rõ Independent/Dependent/Supporting Variables).

## Lưu trữ trên MinIO vs Database

| Loại dữ liệu | Lưu ở đâu | Lý do |
|---|---|---|
| JSON response gốc từ API | MinIO | Giữ nguyên bản, phục vụ backup/tái xử lý |
| Dữ liệu đã làm sạch, chuẩn hóa | Database | Phục vụ truy vấn nhanh, phân tích, ML |

## Việc cần làm tiếp theo
- [ ] Cài đặt MinIO (local/docker) để test lưu trữ raw data
- [ ] Chọn hệ quản trị Database (VD: PostgreSQL) và tạo schema thực tế
- [ ] Viết script Python demo pipeline end-to-end với 1 lần thu thập thử
- [ ] Trao đổi với Hà để thống nhất schema cuối cùng dựa trên `variables.md`
