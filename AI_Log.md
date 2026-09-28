# AI Usage Log

## Project Information

**Project:** Analysis of Factors Influencing YouTube Trending Content  
**Group:** Group 6

## Purpose

This file documents the use of AI tools during the development of the project.

AI tools may be used to support research, documentation, programming, debugging, and project planning. All AI-generated outputs must be reviewed and verified by the project members before being used.

## AI Usage Records

| Date | Member | AI Tool | Purpose | Result / Usage |
|---|---|---|---|---|
| 2026-09-20 | Hạ | ChatGPT | Support project planning and research methodology | Used as guidance and reviewed before inclusion |
| 2026-09-20 | Hạ | ChatGPT | Support project architecture design | Used as guidance for the initial architecture |
| 2026-09-20 | Hạ | ChatGPT | Support GitHub repository setup | Used as guidance for repository organization |

## Verification

All AI-assisted content is reviewed and verified by the project members before being included in the final project.
# AI Log - Lịch sử hỗ trợ kỹ thuật (Nhiệm vụ Hà - Tuần 3)

Tài liệu tham chiếu chính: "YouTube Data Pipeline: Week 3 Engineering Task Assignment"[cite: 2].

| Thời gian | Nhiệm vụ | Lệnh người dùng (Prompt) | Phản hồi & Quyết định hệ thống (AI Support & Decisions) |
| :--- | :--- | :--- | :--- |
| **2026-09-24 15:06:39** | **A1** | "task a1 của Hà"[cite: 1] | AI liệt kê chi tiết yêu cầu nhiệm vụ A1 (đối chiếu Data Dictionary) dựa trên tài liệu "YouTube Data Pipeline: Week 3 Engineering Task Assignment"[cite: 1, 2]. |
| **2026-09-24 15:17:15** | **A1** | "so sánh và đánh giá các trường dữ liệu sau đánh dấu rõ tình trạng"[cite: 1] | AI lập bảng so sánh và phân loại trạng thái các trường dữ liệu thành: Available Now, Derivable, và Not Yet Collected[cite: 1]. |
| **2026-09-24 15:21:04** | **A1** | "xuất mã md cho tôi"[cite: 1] | AI cung cấp nội dung định dạng Markdown hoàn chỉnh cho tệp `docs/data_dictionary.md`[cite: 1]. |
| **2026-09-24 15:32:02** | **A2** | "giải thích rõ ràng các yêu cầu mục tiêu của A2"[cite: 1] | AI giải thích chi tiết về yêu cầu thiết lập hợp đồng dữ liệu (data contract) được quy định trong tài liệu "YouTube Data Pipeline: Week 3 Engineering Task Assignment"[cite: 1, 2]. |
| **2026-09-24 15:47:42** | **A2** | "tạo một bản data contract đầy đủ và nếu gặp những chỗ lưu ý phân vân hãy dừng lại và hỏi"[cite: 1] | AI soạn thảo bản nháp hợp đồng dữ liệu và chủ động tạm dừng để hỏi người dùng chốt 3 quy tắc xử lý: trùng lặp, "No views", và thời gian đăng bài[cite: 1]. |
| **2026-09-24 15:51:51** | **A2** | "1 chọn ghi đè bản cũ 2 chuyển thành 0 cứ lưu tạm chuỗi thô vào db"[cite: 1] | Dựa trên quyết định của người dùng, AI cập nhật và xuất mã Markdown chính thức cho tệp `docs/data_contract.md`[cite: 1]. |
| **2026-09-24 16:06:36** | **A3** | "kiểm tra chất lượng dữ liệu thì nên import với phần code nào của dự án"[cite: 1] | AI tư vấn rằng các hàm kiểm tra cần được viết dạng module tái sử dụng và tích hợp vào quy trình của Hạ (Task H3) cũng như trước bước nạp Database của Nguyên (Task N3)[cite: 1]. |
| **2026-09-27 01:35:15** | **A3** | "task a3 cuar tuaanf 3"[cite: 1] | AI liệt kê các hạng mục cần kiểm tra chất lượng (Data-quality checks) cho nhiệm vụ A3 dựa trên tài liệu "YouTube Data Pipeline: Week 3 Engineering Task Assignment"[cite: 1, 2]. |






## 2026-09-27 to 2026-09-28 - Week 3 Data Engineering (Leader Hạ)

### Task 

Build, scale, integrate, and verify the YouTube data engineering pipeline for Report 2.

### AI-assisted activities

- Assisted with YouTube Data API integration.
- Assisted with expanding the dataset from 1,011 to 2,011 unique videos.
- Assisted with snapshot collection and historical dataset design.
- Assisted with MinIO upload automation and Docker troubleshooting.
- Assisted with SQL Server schema integration.
- Assisted with Python ODBC connection and database loaders.
- Assisted with SQL verification for row count, duplicates, null values, and sample records.
- Assisted with Docker Compose configuration and environment-variable security.
- Assisted with Git staging, stash, rebase, conflict resolution, and commit organization.
- Assisted with technical documentation and Report 2 evidence organization.

### Human Verification

All generated code and commands were manually reviewed and executed by the team.

Verified using:

- Docker Compose
- MinIO Web UI
- Python terminal output
- SQL Server Management Studio
- GitHub commit history

Current verified volume: 2011 unique videos; 10077 historical snapshot records; 0 failed loads.

No API keys or passwords were committed to GitHub.


### Current Verified Status
- Unique videos: 2,011
- Historical snapshot records: 10,077
- Failed database loads: 0
- 10,000+ milestone achieved.
- Long-term target: 100,000 records.
- Current progress toward long-term target: 10.08%.