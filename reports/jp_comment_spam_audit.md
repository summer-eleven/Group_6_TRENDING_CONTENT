# Báo Cáo Kiểm Toán Bình Luận Rác & Bot (JP Comment Spam Audit)

## 1. Mục Đích & Bối Cảnh Nghiên Cứu
Trong nghiên cứu RQ2 (*Ảnh hưởng của cảm xúc bình luận đến mức độ lan tỏa của video*), các bình luận dạng bot spam, seeding quảng cáo, lừa đảo tài chính hoặc copypasta có thể làm sai lệch phân phối cảm xúc thật của khán giả tự nhiên (organic audience). Báo cáo này kiểm toán toàn diện mức độ xuất hiện và kiểm soát chất lượng trên tập dữ liệu thị trường Nhật Bản (JP).

## 2. Kết Quả Kiểm Toán Định Lượng

| Chỉ Số | Giá Trị Thực Tế | Tỷ Lệ (%) |
| :--- | :---: | :---: |
| **Tổng số bình luận phân tích** | **21,624** | 100.00% |
| **Bình luận tự nhiên (Organic)** | **21,459** | **99.24%** |
| **Bình luận có dấu hiệu Spam / Bot** | **165** | **0.76%** |

### Phân loại chi tiết các dạng Spam phát hiện:

| Phân Loại Spam | Số Lượng | Tỷ Lệ | Dấu Hiệu Nhận Diện |
| :--- | :---: | :---: | :--- |
| `ORGANIC` (Bình luận thật) | 21,459 | 99.24% | Ngôn ngữ tự nhiên của người xem, đa dạng cú pháp |
| `EMOJI_FLOOD` (Chuỗi biểu tượng cảm xúc) | 64 | 0.30% | Toàn bộ bình luận chỉ chứa icon hoặc ký tự lặp vô nghĩa |
| `URL_INVITATION` (Chứa liên kết / Dẫn dụ) | 33 | 0.15% | Chứa URL ngoài, lời mời vào group chat, link rút gọn |
| `FINANCIAL_SCAM` (Lừa đảo / Việc làm / Đầu tư) | 25 | 0.12% | Từ khóa mồi chài: 副業, LINE追加, 投資, 稼げる |
| `COPYPASTA_DUPLICATE` (Kịch bản bot trùng lặp) | 34 | 0.16% | Trùng lặp hoàn toàn văn bản giữa nhiều video/tài khoản |
| `SELF_PROMOTION` (Quảng cáo chéo kênh cá nhân) | 9 | 0.04% | Kêu gọi đăng ký kênh chéo: チャンネル登録, プロフ見て |

## 3. Tác Động Của Việc Lọc Spam Đối Với Phân Phối Cảm Xúc (RQ2 Sensitivity)

| Nhãn Cảm Xúc | Toàn Bộ Mẫu Thô (Raw) | Sau Khi Lọc Spam (Organic Only) | Biến Thiên (Delta) |
| :--- | :---: | :---: | :---: |
| **Positive (Tích cực)** | 62.84% | 62.80% | -0.04% |
| **Negative (Tiêu cực)** | 21.31% | 21.43% | +0.12% |
| **Neutral (Trung tính)** | 15.85% | 15.77% | -0.08% |

## 4. Đánh Giá Độ Vững & Kết Luận Phương Pháp
1. **Tỷ lệ kiểm soát cực cao:** Bình luận rác/bot chỉ chiếm **dưới 3%** trong tập dữ liệu. Điều này đạt được nhờ chiến lược thu thập theo thuật toán độ liên quan (`order="relevance"`) của YouTube API, nơi các nội dung rác đã bị thuật toán nền tảng thanh lọc.
2. **Độ vững thống kê (Robustness):** Sự khác biệt về tỷ lệ cảm xúc trước và sau lọc là không đáng kể (< 1%), chứng minh các biến hồi quy `negative_ratio` và `sentiment_polarity` trong [rq2_video_sentiment_JP.csv](file:///data/processed/rq2_video_sentiment_JP.csv) phản ánh trung thực hành vi của khán giả Nhật Bản, không bị sai lệch bởi bot seeding.
