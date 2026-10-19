/* ======================================================================
   N4 - SQL verification cho validation data (chay lai duoc, chup lam evidence)
   Doi @run_id neu muon kiem tra run khac; mac dinh = run moi nhat.
   ====================================================================== */
USE youtube_trending;
GO
DECLARE @run_id INT = (SELECT MAX(run_id) FROM dbo.viral_validation_runs);

PRINT '--- 1. Row counts ---';
SELECT (SELECT COUNT(*) FROM dbo.viral_validation_runs)       AS runs,
       (SELECT COUNT(*) FROM dbo.viral_validation_candidates) AS candidates,
       (SELECT COUNT(*) FROM dbo.viral_validation_evidence)   AS evidence_rows,
       (SELECT COUNT(*) FROM dbo.viral_validation_evidence WHERE run_id = @run_id) AS evidence_rows_latest_run;

PRINT '--- 2. Duplicate evidence (cung run/video/nguon/metric/timestamp) - ky vong 0 dong ---';
SELECT run_id, video_id, external_source, external_metric, evidence_collected_at, COUNT(*) AS n
FROM dbo.viral_validation_evidence
GROUP BY run_id, video_id, external_source, external_metric, evidence_collected_at
HAVING COUNT(*) > 1;

PRINT '--- 3. Near-duplicate: cung video/nguon/metric, 2 lan thu cach nhau < 10 phut - xem xet gop ---';
SELECT a.video_id, a.external_source, a.external_metric, a.evidence_id AS id_a, b.evidence_id AS id_b,
       a.evidence_collected_at AS t_a, b.evidence_collected_at AS t_b
FROM dbo.viral_validation_evidence a
JOIN dbo.viral_validation_evidence b
  ON a.run_id = b.run_id AND a.video_id = b.video_id AND a.external_source = b.external_source
 AND a.external_metric = b.external_metric AND a.evidence_id < b.evidence_id
 AND ABS(DATEDIFF(MINUTE, a.evidence_collected_at, b.evidence_collected_at)) < 10;

PRINT '--- 4. Missing source / timestamp / proof - ky vong 0 dong ---';
SELECT evidence_id, video_id, external_source, evidence_collected_at, evidence_result, evidence_url, evidence_path, notes
FROM dbo.viral_validation_evidence
WHERE external_source IS NULL OR evidence_collected_at IS NULL OR video_id IS NULL
   OR (evidence_result <> 'not_available' AND (evidence_url IS NULL OR (evidence_path IS NULL AND notes IS NULL)))
   OR (evidence_result IN ('contradicts','inconclusive','not_available') AND notes IS NULL);

PRINT '--- 5. Evidence tro toi candidate khong ton tai (orphan) - ky vong 0 dong ---';
SELECT e.evidence_id, e.run_id, e.video_id
FROM dbo.viral_validation_evidence e
LEFT JOIN dbo.viral_validation_candidates c ON c.run_id = e.run_id AND c.video_id = e.video_id
WHERE c.video_id IS NULL;

PRINT '--- 6. Time mismatch (chenh lech thoi gian vuot nguong theo granularity) ---';
SELECT video_id, external_source, source_granularity, ranking_observed_at, evidence_collected_at, gap_minutes
FROM dbo.vw_viral_evidence_timing
WHERE time_mismatch = 1
ORDER BY gap_minutes DESC;

PRINT '--- 7. Thong ke video theo validation_status (run moi nhat) ---';
SELECT validation_status, COUNT(*) AS videos
FROM dbo.vw_viral_validation_status
WHERE run_id = @run_id
GROUP BY validation_status
ORDER BY validation_status;

PRINT '--- 8. Thong ke theo external_source x evidence_result (run moi nhat) ---';
SELECT external_source, evidence_result, COUNT(DISTINCT video_id) AS videos, COUNT(*) AS evidence_rows
FROM dbo.viral_validation_evidence
WHERE run_id = @run_id
GROUP BY external_source, evidence_result
ORDER BY external_source, evidence_result;

PRINT '--- 9. Coverage: candidate chua co bat ky evidence nao ---';
SELECT video_id, rank_in_run, viral_score
FROM dbo.vw_viral_validation_status
WHERE run_id = @run_id AND coverage = 'no_evidence_collected'
ORDER BY rank_in_run;

PRINT '--- 10. Cac nguon mau thuan (disagreement) - bat buoc giai thich trong bao cao ---';
SELECT s.video_id, s.validation_status, e.external_source, e.evidence_result, e.external_value, e.notes
FROM dbo.vw_viral_validation_status s
JOIN dbo.viral_validation_evidence e ON e.run_id = s.run_id AND e.video_id = s.video_id
WHERE s.run_id = @run_id AND s.disagreement_flag = 1
ORDER BY s.video_id, e.external_source;

PRINT '--- 11. Sample validated videos (L2 / L3 / L2+L3) ---';
SELECT TOP 10 s.video_id, v.title, s.viral_score, s.youtube_chart_rank, s.validation_status,
       s.supports_count, s.contradicts_count
FROM dbo.vw_viral_validation_status s
JOIN dbo.youtube_videos v ON v.video_id = s.video_id
WHERE s.run_id = @run_id AND s.validation_status <> 'L1_viral_candidate'
ORDER BY s.viral_score DESC;

PRINT '--- 12. SUMMARY: candidate nao co / khong co external corroboration ---';
SELECT s.rank_in_run, s.video_id, LEFT(v.title, 60) AS title, s.viral_score,
       s.youtube_charted, s.validation_status,
       CASE WHEN s.supports_count > 0 THEN 'YES'
            WHEN s.contradicts_count > 0 THEN 'CONTRADICTED'
            WHEN s.not_available_count > 0 THEN 'NOT AVAILABLE'
            ELSE 'NOT CHECKED' END AS external_corroboration
FROM dbo.vw_viral_validation_status s
JOIN dbo.youtube_videos v ON v.video_id = s.video_id
WHERE s.run_id = @run_id
ORDER BY s.rank_in_run;
GO