# Data Contract: Raw vs Processed Data (Week 3)

Tài liệu này định nghĩa các quy tắc, kiểu dữ liệu, và cách biến đổi dữ liệu từ dạng thô (Raw - MinIO) sang dạng chuẩn (Processed - Database) để phục vụ cho việc viết Data-Quality Checks (Task A3) và Database Loader (Task N3).

## 1. Expected Data Types & Required Fields

| Field Name | Raw Type (Crawler/JSON) | Processed Type (Database) | Required (Bắt buộc) | Ghi chú |
| :--- | :--- | :--- | :--- | :--- |
| `video_id` | String | String | **Yes** (Primary Key) | Không được phép NULL[cite: 3]. |
| `title` | String | String | **Yes** | Không được phép NULL hoặc rỗng[cite: 3]. |
| `channel` | String | String | **Yes** | Không được phép NULL[cite: 3]. |
| `url` | String | String | **Yes** | Phải đúng định dạng URL YouTube[cite: 3]. |
| `views` / `view_count`| String (e.g., "1.2M views") | Integer | **Yes** | Phải >= 0. Tránh lỗi views âm[cite: 3]. |
| `published` | String (e.g., "2 days ago") | String | No | Lưu tạm chuỗi thô vào DB theo scope Tuần 3. |
| `search_query` | String | String | No | Lưu vết từ khóa tìm kiếm. |

## 2. Missing-Value Rules (Quy tắc xử lý giá trị thiếu)

* **Đối với các trường Required (Bắt buộc):** Nếu bản ghi bị thiếu (NULL/Empty) một trong các trường `video_id`, `title`, `channel`, `url`, bản ghi đó sẽ bị **loại bỏ (drop)** và ghi log lỗi trong quá trình xử lý[cite: 3].
* **Đối với các trường Non-Required (Không bắt buộc):** Nếu thiếu, hệ thống sẽ chèn giá trị `NULL` hoặc giá trị mặc định trống vào Database[cite: 3].

## 3. Transformations: Raw to Processed (Quy tắc biến đổi)

Các quy tắc biến đổi này áp dụng khi chuyển dữ liệu thô sang dữ liệu chuẩn bị load vào DB[cite: 3]:

* **`view_count`:** 
  * Chuyển đổi trường hợp giá trị là `"No views"` thành `0`.
  * Loại bỏ chuỗi `" views"` từ raw text.
  * Phân tích các hậu tố viết tắt: `K` (nhân 1,000), `M` (nhân 1,000,000) và ép kiểu (cast) về số nguyên (Integer) hợp lệ[cite: 3].
* **`url`:**
  * Nếu dữ liệu thô không có full URL, tự động nội suy bằng chuỗi template: `https://www.youtube.com/watch?v={video_id}`[cite: 3].
* **`published`:**
  * Giữ nguyên chuỗi thô (Raw string) từ crawler. Không thực hiện parse sang DateTime trong Tuần 3, bảo toàn chuỗi văn bản (VD: `"2 days ago"`) để nạp trực tiếp vào cơ sở dữ liệu.

## 4. Duplicate Rules (Quy tắc xử lý trùng lặp)

Để xử lý an toàn các video ID bị trùng lặp trong Database (theo yêu cầu của Database Loader)[cite: 3]:
* **Định danh duy nhất (Unique Key):** Sử dụng trường `video_id` làm Primary Key.
* **Quy tắc khi Insert (Upsert):** Áp dụng cơ chế **Ghi đè (Overwrite/Upsert)**. Nếu một `video_id` đã tồn tại trong cơ sở dữ liệu, cập nhật bản ghi cũ bằng dữ liệu của bản ghi mới nhất từ đợt crawl hiện tại (đảm bảo cập nhật số lượt xem và các thay đổi mới).
