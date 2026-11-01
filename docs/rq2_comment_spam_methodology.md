# Quy Trình & Phương Pháp Luận Kiểm Soát Bình Luận Bot / Spam (RQ2)

## 1. Giới Thiệu
Tài liệu này quy chuẩn hóa quy trình phát hiện và kiểm soát chất lượng bình luận cho Câu hỏi nghiên cứu 2 (RQ2), đảm bảo dữ liệu phục vụ mô hình học máy và thống kê không bị ô nhiễm bởi các chiến dịch seeding, bot tự động hoặc quảng cáo rác.

## 2. Các Tầng Kiểm Soát (Multi-Layer Defense)

### Tầng 1: Thu thập thông minh (Intelligent Ingestion)
- Thiết lập tham số `order="relevance"` khi gọi endpoint `commentThreads` của YouTube Data API v3.
- Tận dụng trực tiếp bộ lọc chống gian lận và đánh giá tín nhiệm người dùng nội bộ của Google/YouTube.

### Tầng 2: Tiền xử lý & Khử trùng lặp (Heuristic & Lexical Cleaning)
- Khử trùng lặp khóa chính `comment_id` tuyệt đối giữa các mẻ cào.
- Thay thế URL ngoài bằng token `<URL>` để tránh bot tạo link rác và phân tách ký tự an toàn.
- Quét biểu thức chính quy (Regex) các mẫu lừa đảo tài chính và tuyển dụng qua LINE đặc thù tại Nhật Bản.

### Tầng 3: Trọng số tương tác thực tế (Engagement Weighting)
- Thay vì chỉ sử dụng tỷ lệ tiêu cực thô `negative_ratio`, nhóm bổ sung biến `weighted_negative_ratio` điều chỉnh theo số lượt thích của bình luận:
$$\text{weighted\_negative\_ratio} = \frac{\sum (\log(1 + \text{likes}_i) + 1) \cdot \mathbb{I}_{\text{neg}}}{\sum (\log(1 + \text{likes}_i) + 1)}$$
- Do các bình luận spam hiếm khi nhận được lượt thích hữu cơ từ cộng đồng người xem thật, trọng số của chúng tự động bị triệt tiêu trong mô hình hồi quy giải thích độ lan tỏa video.
