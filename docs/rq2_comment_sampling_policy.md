# RQ2 Comment Sampling & Acquisition Policy (HT-03)
## Group 6: Analysis of Factors Influencing YouTube Trending Content
### Author: Ha (JP Market Analyst) | Date: 2026-10-25

---

## 1. Mục Đích & Bối Cảnh Nghiên Cứu
Câu hỏi nghiên cứu số 2 (**RQ2**) đặt ra:
> *"Tỷ lệ bình luận tiêu cực (`negative_comment_ratio`) trên video YouTube có mối quan hệ như thế nào với mức độ lan truyền (lượt xem / tăng trưởng lượt xem) của video đó tại thị trường Nhật Bản?"*

Để trả lời câu hỏi này một cách khách quan và có thể tái hiện, chính sách này quy định quy trình chọn mẫu, thu thập và tiền xử lý bình luận tiếng Nhật.

---

## 2. Quy Trình Chọn Mẫu Video (Stratified Sampling)
Thay vì sử dụng danh sách video cố định viết cứng (`MANUAL_TRENDING_VIDEOS`), quy trình mới tự động trích xuất mẫu đại diện từ:
`data/processed/youtube_cohort_registry_JP.csv`

### Tiêu chí phân tầng (Stratification):
1. **Lọc tính hợp lệ:** Chỉ chọn các video có `video_id` 11 ký tự hợp lệ và có tính năng bình luận khả dụng (`t0_comment_count > 0`).
2. **Cân bằng Category:** Lấy mẫu phân tầng theo tỷ lệ phân bố của các nhóm danh mục chính:
   * Gaming (20)
   * Entertainment (24)
   * People & Blogs (22)
   * Music (10)
   * News, Film, Howto, Sports (~20%)
3. **Cân bằng quy mô tương tác:** Bao gồm cả video có lượng tương tác cao, trung bình và mới nổi.

---

## 3. Quy Định Tham Số Thu Thập (Acquisition Parameters)
* **Số lượng comment tối đa / video (`max_comments_per_video`):** Cố định **100 bình luận cấp 1 (top-level comments)** cho mỗi video. Không gọi đệ quy các sub-replies để tránh thiên lệch hội thoại giữa 2 cá nhân.
* **Thứ tự sắp xếp (`order`):** Mặc định sử dụng **`order=relevance`** (do YouTube xếp hạng theo mức độ nổi bật/tương tác).
  * *Lưu ý về Bias:* Bình luận lấy theo `relevance` có xu hướng thu hút nhiều tranh luận hoặc lượt like cao hơn, có thể làm tỷ lệ cảm xúc hơi nghiêng về cực đoan (rất thích hoặc rất ghét). Nhóm ghi nhận đây là một **Hạn chế phương pháp luận (Methodological Limitation)** và sẽ kiểm chứng độ nhạy với `order=time` trên tập kiểm định.
* **Thời điểm lấy bình luận (`collected_at`):** Được ghi lại chính xác theo định dạng UTC ISO 8601 để đảm bảo tính thời gian (Time-aligned) trước khi đo lường mức tăng trưởng của video.

---

## 4. Bảo Vệ Quyền Riêng Tư (PII Protection)
* Hệ thống **KHÔNG thu thập và KHÔNG lưu trữ** các thông tin nhận dạng cá nhân nhạy cảm:
  * Không lưu `authorChannelUrl`, `authorProfileImageUrl`, `channelId` của người bình luận.
  * Chỉ lưu mã định danh `comment_id` của YouTube và nội dung văn bản thuần túy (`comment_text`).
  * Tất cả các báo cáo và slide công khai chỉ trích dẫn ví dụ ẩn danh.

---

## 5. Quy Chuẩn Làm Sạch Văn Bản Tiếng Nhật (NLP Preprocessing)
1. **Bảo toàn ngôn ngữ bản địa:** Giữ nguyên 100% chữ viết tiếng Nhật (Kanji, Hiragana, Katakana) và các biểu tượng cảm xúc (Emoji). Emoji trong tiếng Nhật mang trọng số cảm xúc cực kỳ quan trọng (ví dụ: 😭, 😡, 👍).
2. **Chuẩn hóa liên kết:** Thay thế mọi đường dẫn URL (website, link rác, spam) bằng token chuẩn `<URL>`.
3. **Khử khoảng trắng thừa:** Thu gọn các chuỗi ký tự xuống dòng hoặc cách trống liên tiếp (`\s+`) thành một dấu cách duy nhất.
4. **Loại bỏ trùng lặp:** Khử trùng tuyệt đối theo khóa chính `comment_id`.

---

*Chính sách này có hiệu lực áp dụng cho toàn bộ dữ liệu bình luận tiếng Nhật thuộc đề tài.*