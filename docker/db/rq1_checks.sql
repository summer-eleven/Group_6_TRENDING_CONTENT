/*
=====================================================================
 rq1_checks.sql   (N5 - SQL kiem dem va xac minh nhan RQ1)
=====================================================================
 Chi CHON (SELECT), khong ghi/xoa du lieu. Chay trong SSMS / Azure Data Studio,
 boi den tung batch (giua 2 dong GO) roi F5. Doi @region / @since o dau moi batch.

 Bo loc nuoc: dat @region = N'KR' (vd) hoac de NULL = tat ca cac nuoc co trong du lieu.
 PHAN A: chay duoc NGAY tren bang hien co (dbo.youtube_video_snapshots).
 PHAN B: chi chay SAU KHI add_rolling_cohort_schema.sql da duoc Ha duyet + apply.

 DIEU CAN NHO KHI DOC KET QUA
   - "observed_ever_charted" = TUNG DUOC QUAN SAT tren chart trong lich su snapshot da luu,
     KHONG phai "moi lan xuat hien trong doi video".
   - Gio chart bi mat / FAILED / PARTIAL => nhan UNKNOWN/INCOMPLETE, KHONG phai NON_TRENDING.
   - trending_rank 0 hoac NULL khi is_trending = 1 la BAT THUONG, khong phai hang hop le.
   - collected_at trong snapshots la gio UTC (khong co offset).
=====================================================================
*/

/* ================================================================
   PHAN A - TREN BANG HIEN CO
   ================================================================ */

-- A1. So luong hien co theo vung (tu tai lieu nhiem vu; bo loc cung 3 nuoc -> @region)
DECLARE @region NVARCHAR(2) = NULL;   -- NULL = tat ca cac nuoc; hoac N'US', N'KR'...
SELECT region_code, COUNT(*) AS snapshot_rows,
       COUNT(DISTINCT video_id) AS unique_region_videos
FROM dbo.youtube_video_snapshots
WHERE (@region IS NULL OR region_code = @region)
GROUP BY region_code;
GO

-- A2. Anomaly: is_trending = 1 nhung rank NULL/0 (tu tai lieu; them loc @region)
DECLARE @region NVARCHAR(2) = NULL;   -- NULL = tat ca cac nuoc; hoac N'US', N'KR'...
SELECT TOP 20 region_code, video_id, collected_at,
       is_trending, trending_rank
FROM dbo.youtube_video_snapshots
WHERE is_trending = 1
  AND (trending_rank IS NULL OR trending_rank = 0)
  AND (@region IS NULL OR region_code = @region)
ORDER BY collected_at DESC;
GO

-- A2b. Dem anomaly theo vung + thoi gian (doi @since neu can)
DECLARE @region NVARCHAR(2) = NULL;   -- NULL = tat ca cac nuoc; hoac N'US', N'KR'...
DECLARE @since DATETIME2 = DATEADD(DAY, -7, SYSUTCDATETIME());
SELECT region_code,
       SUM(CASE WHEN is_trending = 1 THEN 1 ELSE 0 END)                                         AS charted_rows,
       SUM(CASE WHEN is_trending = 1 AND (trending_rank IS NULL OR trending_rank = 0) THEN 1 ELSE 0 END) AS charted_rows_invalid_rank
FROM dbo.youtube_video_snapshots
WHERE (@region IS NULL OR region_code = @region) AND collected_at >= @since
GROUP BY region_code;
GO

-- A3. Bang chung lich su: tung video da TUNG duoc quan sat tren chart (tu tai lieu; loc @region)
DECLARE @region NVARCHAR(2) = NULL;   -- NULL = tat ca cac nuoc; hoac N'US', N'KR'...
SELECT region_code, video_id,
       MAX(CASE WHEN is_trending = 1 THEN 1 ELSE 0 END) AS observed_ever_charted,
       MIN(CASE WHEN is_trending = 1 THEN collected_at END) AS first_observed_chart_time,
       MIN(CASE WHEN is_trending = 1 AND trending_rank > 0 THEN trending_rank END) AS best_observed_rank
FROM dbo.youtube_video_snapshots
WHERE (@region IS NULL OR region_code = @region)
GROUP BY region_code, video_id;
GO

-- A3b. Tom tat A3 theo vung (bao nhieu video tung charted / khong)
DECLARE @region NVARCHAR(2) = NULL;   -- NULL = tat ca cac nuoc; hoac N'US', N'KR'...
WITH ev AS (
    SELECT region_code, video_id,
           MAX(CASE WHEN is_trending = 1 THEN 1 ELSE 0 END) AS observed_ever_charted
    FROM dbo.youtube_video_snapshots
    WHERE (@region IS NULL OR region_code = @region)
    GROUP BY region_code, video_id
)
SELECT region_code,
       COUNT(*)                   AS videos,
       SUM(observed_ever_charted) AS observed_ever_charted,
       COUNT(*) - SUM(observed_ever_charted) AS never_observed_charted_in_stored_snapshots
FROM ev GROUP BY region_code;
GO

-- A4. Chat luong metadata (N1): view/like/comment NULL hoac 0, va video unavailable.
--     unavailable KHONG duoc tinh la xu huong am.
DECLARE @region NVARCHAR(2) = NULL;   -- NULL = tat ca cac nuoc; hoac N'US', N'KR'...
SELECT region_code,
       COUNT(*)                                                    AS snapshot_rows,
       SUM(CASE WHEN video_available = 0 THEN 1 ELSE 0 END)        AS unavailable_rows,
       SUM(CASE WHEN view_count    IS NULL THEN 1 ELSE 0 END)      AS view_null,
       SUM(CASE WHEN view_count    = 0     THEN 1 ELSE 0 END)      AS view_zero,
       SUM(CASE WHEN like_count    IS NULL THEN 1 ELSE 0 END)      AS like_null,
       SUM(CASE WHEN comment_count IS NULL THEN 1 ELSE 0 END)      AS comment_null
FROM dbo.youtube_video_snapshots
WHERE (@region IS NULL OR region_code = @region)
GROUP BY region_code;
GO


