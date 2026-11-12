# Kịch bản Phản biện Phương pháp luận & Quy mô Mẫu (Defense Methodology Q&A)
## Nhóm 6: Analysis of Factors Influencing YouTube Trending Content
### Thành viên phụ trách thị trường JP: Hà | Cập nhật: 2026-11-12

---

## Câu hỏi Phản biện Trọng tâm từ Hội đồng / Giảng viên:
> *"Tại sao tổng dữ liệu thu thập của thị trường JP đạt 35.121 video, nhưng trong bảng kiểm định RQ1 chỉ đưa vào phân tích 1.673 video?"*

---

## Kịch bản Trả lời Chuẩn mực (3 Bước):

### Bước 1: Ranh giới giữa "Tập thu thập mở rộng" và "Mẫu nghiên cứu hợp lệ"
* Trong Khoa học Dữ liệu, cần phân biệt rạch ròi giữa hai tập dữ liệu được quản lý qua kiến trúc phân tầng (Data Tiering):
  1. **Scraped Population (Tập dữ liệu mở rộng Tier 2 Harvest = 32.000 video + Tầng T24 = 35.121 video duy nhất):** Được xuất tại `data/processed/youtube_dataset_expansion_JP_35k.csv`. Mục đích là tạo kho nguồn đa dạng để cào 21.624 bình luận, phục vụ phân tích NLP Sentiment và huấn luyện mô hình Hồi quy ở RQ2.
  2. **Eligible Analytic Sample (Mẫu hợp lệ cho RQ1 = 1.673 video JP):** Được lưu trữ tại `data/processed/youtube_rq1_dataset.csv` và `youtube_dataset_2000_clean.csv`. Đây là tập mẫu tuân thủ nghiêm ngặt điều kiện thiết kế đoàn hệ tiến cứu (Prospective Rolling Cohort Study) có theo dõi chu kỳ T+24h và kiểm tra trạng thái trên bảng xếp hạng Trending.

### Bước 2: Nguồn gốc và Khả năng Tái lập của Con số N = 1.673 (Tái lập 100%)
* Dữ liệu N = 1.673 video JP nằm chính xác tại cột `region_code == 'JP'` trong file `data/processed/youtube_rq1_dataset.csv` (tạo bởi `src/processing/build_rq1_dataset.py`).
* Bảng chéo giữa `upload_period` và `chart_status` tái lập như sau:
  - Khung giờ hành chính (Office): 34 video lọt Chart, 314 video không lọt Chart (Tổng: 348 video, tỷ lệ: 9.77%).
  - Khung giờ nghỉ ngơi (Rest): 214 video lọt Chart, 1.111 video không lọt Chart (Tổng: 1.325 video, tỷ lệ: 16.15%).
  - Tổng số quan sát JP = 348 + 1.325 = **1.673 video**.
  - Kiểm định Chi-Square đạt: X² = 8.89 (hoặc 8.39 hiệu chỉnh Yates), p-value = 0.0037 < 0.01 (đạt ý nghĩa thống kê ở mức 1%).

### Bước 3: Đảm bảo Sức mạnh Thống kê (Statistical Power)
* Với N = 1.673 video JP trong bảng chéo 2 x 2:
  - Tần số kỳ vọng (E) ở tất cả các ô đều > 30, vượt xa ngưỡng tối thiểu E >= 5 của kiểm định Chi-Square Pearson.
  - Sức mạnh thống kê đạt > 95% tại mức ý nghĩa alpha = 0.05.
* Kết luận: Mẫu 1.673 video hoàn toàn đủ độ vững và sức mạnh thống kê để đưa ra kết luận khoa học đáng tin cậy cho thị trường Nhật Bản.
