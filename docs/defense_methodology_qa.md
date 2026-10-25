# Kịch bản Phản biện Phương pháp luận & Quy mô Mẫu (Defense Methodology Q&A)
## Nhóm 6: Analysis of Factors Influencing YouTube Trending Content
### Thành viên phụ trách thị trường JP: Hà | Cập nhật: 2026-10-25

---

## Câu hỏi Phản biện Trọng tâm từ Hội đồng / Giảng viên:
> *"Tại sao tổng dữ liệu thu thập của thị trường JP (hoặc toàn nhóm) đạt hàng chục ngàn video (mục tiêu 35.000 / 100.000 video), nhưng trong bảng kiểm định RQ1 chỉ đưa vào phân tích khoảng 1.600 – 2.500 video?"*

---

## Kịch bản Trả lời Chuẩn mực (3 Bước):

### Bước 1: Ranh giới giữa "Tập thu thập mở rộng" và "Mẫu nghiên cứu hợp lệ"
* Trong Khoa học Dữ liệu, cần phân biệt rạch ròi giữa:
  1. **Scraped Population (Tổng tập dữ liệu cào được $\ge$ 35.000 video):** Phục vụ cào bình luận, phân tích ngôn ngữ tự nhiên NLP Sentiment và huấn luyện mô hình Hồi quy đa biến (Regression) ở RQ2 và Report 4.
  2. **Eligible Analytic Sample (Mẫu hợp lệ cho RQ1 $\approx$ 1.673 video JP):** Tập mẫu tuân thủ nghiêm ngặt điều kiện của thiết kế nghiên cứu đoàn hệ (Cohort Study).

### Bước 2: Hai lý do khoa học bắt buộc phải lọc mẫu cho RQ1 (Tránh Bias & Data Leakage)
1. **Tính mới của video (Freshness / Cohort Anchor):**
   * RQ1 là nghiên cứu **đoàn hệ tiến cứu (Prospective Rolling Cohort)**. Video phải được bắt đầu theo dõi ngay khi mới đăng tải ($T_0 \le 7$ ngày).
   * Nếu đưa những video đã đăng 2–3 tháng trước vào, các video này đã kết thúc vòng đời từ lâu. Việc không thấy chúng trên Chart hôm nay rồi gán nhãn `NOT_OBSERVED_WITH_COVERAGE` (cho là không bao giờ trending) sẽ phạm phải lỗi **Sai lệch sống sót (Survivorship Bias)** và **Data Leakage**.
2. **Độ phủ giám sát biểu đồ (Chart Monitoring Coverage Ratio):**
   * Một video chỉ được gán nhãn chính thức khi hệ thống Chart Monitor có dữ liệu đo lường liên tục trong cửa sổ 7 ngày sau khi video đăng.
   * Những video thiếu độ phủ quan sát bắt buộc phải gán cờ `UNKNOWN` hoặc loại khỏi phân tích sơ cấp của RQ1 để bảo toàn tính trung thực của dữ liệu.

### Bước 3: Đảm bảo Sức mạnh Thống kê (Statistical Power)
* Với $N = 1.673$ video JP trong bảng chéo $2 \times 2$:
  * Tần số kỳ vọng ($E$) ở tất cả các ô đều $> 30$, vượt xa ngưỡng tối thiểu $E \ge 5$ của kiểm định Chi-Square Pearson.
  * Sức mạnh thống kê đạt $> 95\%$ tại mức ý nghĩa $\alpha = 0.05$.
  * Thống kê kiểm định đạt $X^2 = 8.89$ với $p = 0.003 < 0.01$ (rất có ý nghĩa thống kê).
* Kết luận: Mẫu 1.673 video hoàn toàn đủ sức mạnh thống kê để đưa ra kết luận khoa học đáng tin cậy.

---

*Tài liệu nội bộ phục vụ bảo vệ đồ án và giải trình báo cáo Report 3 & 4.*