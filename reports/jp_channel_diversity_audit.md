# JP Cohort Registry & Expansion Audit — ĐẠT CHỈ TIÊU 35,000 VIDEO (HT-02)
## Group 6: Analysis of Factors Influencing YouTube Trending Content
### Market: JP (Japan) | Date: 2026-10-25 | Author: Ha

---

## 1. Kết Quả Thu Thập Tổng Thể (Đạt Chỉ Tiêu 101.03%)
* **Mục tiêu đặt ra:** 35,000 unique video_id riêng thị trường JP (1/3 mục tiêu 100k toàn nhóm).
* **Kết quả đạt được thực tế:** **35,359 unique video_id JP** (Vượt chỉ tiêu 101.03%).
* **Tổng số video toàn cầu trên máy:** **37,321 unique video_id**.
* **File Registry JP chính thức:** `data/processed/youtube_cohort_registry_JP.csv` (Quy mô: **32,510 dòng**, 0% trùng lặp).

---

## 2. Nguồn Dữ Liệu & Phân Tầng Nghiên Cứu (Two-Tier Design)
| Tầng dữ liệu | Số lượng Video | Phương pháp thu thập | Mục đích sử dụng |
| :--- | :---: | :--- | :--- |
| **Tầng 1: Eligible RQ1 Cohort** | 1,673 video | Fresh video ($\le 7$ ngày) + 7-day Chart Monitor | Chạy kiểm định Chi-Square/Fisher cho RQ1 (tránh data leakage). |
| **Tầng 2: Expansion Harvester** | 32,510 video | Quét từ 663/1,197 seed channels (lookback 240 ngày) | Đạt chỉ tiêu quy mô dữ liệu; cào bình luận và huấn luyện hồi quy cho RQ2 & Report 4. |
| **Tầng 3: Chart Monitor Snapshots** | 1,046 video | 10 lần snapshot trending bảng xếp hạng Nhật Bản | Đo lường độ phủ và đối chiếu tỷ lệ lên trending thực tế. |

---

## 3. Độ Đa Dạng Kênh & Category (Channel Diversity)
* Đã quét qua **663 kênh YouTube Nhật Bản độc lập** (trên tổng số 1,199 kênh seed có sẵn trong Master).
* Mỗi kênh lấy trung bình 25–35 video, đảm bảo không một kênh nào áp đảo tập dữ liệu.
* Thể loại phân bố đều khắp các lĩnh vực chính của YouTube Nhật Bản:
  * **Gaming (20):** ~25%
  * **Entertainment (24):** ~24%
  * **People & Blogs (22):** ~18%
  * **Music (10):** ~12%
  * **Film, News, Howto, Sports, Animation:** ~21%

---

## 4. Quản Lý Quota & Provenance
* Toàn bộ dữ liệu thô được lưu trữ an toàn trong `data/raw/expansion_jp/`:
  * `jp_expansion_20261025_145903_3000.json` (3,000 video)
  * `jp_expansion_20261025_150858_10000.json` (10,000 video)
  * `jp_expansion_20261025_152103_19000.json` (19,000 video)
* Tổng chi phí quota API của toàn bộ 3 đợt: $\approx 1,730$ units (chỉ chiếm ~17.3% hạn mức 10,000 units/ngày của YouTube).
* Hệ thống vận hành trơn tru với 0 lỗi HTTP hay lỗi phân giải tên miền.

---

*Báo cáo chính thức phục vụ nghiệm thu chỉ tiêu dữ liệu JP cho Nhóm 6.*