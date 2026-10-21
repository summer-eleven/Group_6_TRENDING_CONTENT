-- US validation queries (CHI DOC, an toan chay nhieu lan). Chay bang sqlcmd / SSMS tren DB youtube_trending.
USE youtube_trending;
GO
-- 1. So video unique US trong cohort va so quan sat theo phase
SELECT phase, COUNT(*) AS observations, COUNT(DISTINCT video_id) AS unique_videos
FROM dbo.youtube_cohort_observations WHERE region_code = 'US' GROUP BY phase;

-- 2. Tong unique US (T0/T24 khong cong don)
SELECT COUNT(DISTINCT video_id) AS us_unique_videos
FROM dbo.youtube_cohort_observations WHERE region_code = 'US';

-- 3. Trung lap (batch_id, video_id, phase) - ky vong 0 dong
SELECT batch_id, video_id, phase, COUNT(*) AS n
FROM dbo.youtube_cohort_observations WHERE region_code = 'US'
GROUP BY batch_id, video_id, phase HAVING COUNT(*) > 1;

-- 4. Video US xuat hien o batch khac nhau (cung video_id nhieu batch) - ky vong 0 dong
SELECT video_id, COUNT(DISTINCT batch_id) AS batches
FROM dbo.youtube_cohort_observations WHERE region_code = 'US' AND phase = 'T0'
GROUP BY video_id HAVING COUNT(DISTINCT batch_id) > 1;

-- 5. Metric thieu / am
SELECT SUM(CASE WHEN view_count IS NULL THEN 1 ELSE 0 END) AS null_views,
       SUM(CASE WHEN like_count IS NULL THEN 1 ELSE 0 END) AS null_likes,
       SUM(CASE WHEN comment_count IS NULL THEN 1 ELSE 0 END) AS null_comments,
       SUM(CASE WHEN view_count < 0 THEN 1 ELSE 0 END) AS negative_views,
       SUM(CASE WHEN video_available = 0 THEN 1 ELSE 0 END) AS unavailable
FROM dbo.youtube_cohort_observations WHERE region_code = 'US';

-- 6. T24 ma khong co T0 - ky vong 0 dong
SELECT t24.batch_id, t24.video_id
FROM dbo.youtube_cohort_observations t24
LEFT JOIN dbo.youtube_cohort_observations t0
  ON t0.batch_id = t24.batch_id AND t0.video_id = t24.video_id AND t0.phase = 'T0'
WHERE t24.region_code = 'US' AND t24.phase = 'T24' AND t0.observation_id IS NULL;

-- 7. Chart runs US va entries
SELECT COUNT(*) AS runs, SUM(CAST(next_page_available AS int)) AS partial_runs,
       MIN(collected_at_utc) AS first_run, MAX(collected_at_utc) AS last_run
FROM dbo.youtube_chart_runs WHERE region_code = 'US' AND chart_name = 'mostPopular';

SELECT COUNT(*) AS entries, COUNT(DISTINCT e.video_id) AS unique_chart_videos
FROM dbo.youtube_chart_entries e JOIN dbo.youtube_chart_runs r ON r.run_id = e.run_id
WHERE r.region_code = 'US';

-- 8. Doi chieu MinIO path: moi quan sat phai co object path
SELECT phase, SUM(CASE WHEN minio_object_path IS NULL THEN 1 ELSE 0 END) AS missing_minio_path
FROM dbo.youtube_cohort_observations WHERE region_code = 'US' GROUP BY phase;

-- 9. Mau ngau nhien 10 video de doi chieu thu cong voi raw JSON / registry
SELECT TOP 10 video_id, batch_id, phase, observed_at_utc, view_count, minio_object_path
FROM dbo.youtube_cohort_observations WHERE region_code = 'US' ORDER BY NEWID();
