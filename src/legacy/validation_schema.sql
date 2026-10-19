/* ======================================================================
   N1 - Viral/Trending Validation Evidence Schema
   Chay SAU init_schema.sql (can bang youtube_videos).
   Thiet ke: 3 bang + 2 view. validation_status KHONG nhap tay, duoc TINH
   tu evidence trong view vw_viral_validation_status -> truy nguoc duoc.
   Moi timestamp luu UTC (DATETIME2, khong offset).
   ====================================================================== */
USE youtube_trending;
GO

/* 1) Moi lan phan tich = 1 run (region + thoi diem snapshot dung de tinh viral ranking) */
IF OBJECT_ID('dbo.viral_validation_runs', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.viral_validation_runs (
        run_id              INT IDENTITY(1,1) NOT NULL CONSTRAINT pk_vv_runs PRIMARY KEY,
        region_code         VARCHAR(5)     NOT NULL,
        ranking_observed_at DATETIME2      NOT NULL,   -- collected_at cua snapshot dung tinh viral_score (UTC)
        candidate_rule      NVARCHAR(200)  NOT NULL,   -- vd: 'top 20 by viral_score, signal_count>=3'
        created_by          NVARCHAR(100)  NULL,
        created_at          DATETIME2      NOT NULL CONSTRAINT df_vv_runs_created DEFAULT SYSUTCDATETIME(),
        CONSTRAINT uq_vv_runs UNIQUE (region_code, ranking_observed_at)
    );
END
GO

/* 2) Level 1 + tin hieu chart cua YouTube (dong bang tai thoi diem run) */
IF OBJECT_ID('dbo.viral_validation_candidates', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.viral_validation_candidates (
        run_id             INT         NOT NULL,
        video_id           VARCHAR(20) NOT NULL,
        rank_in_run        INT         NOT NULL,
        viral_score        FLOAT       NOT NULL,
        signal_count       TINYINT     NOT NULL,
        youtube_charted    BIT         NOT NULL,       -- is_trending cua snapshot cung collected_at (API mostPopular)
        youtube_chart_rank INT         NULL,
        CONSTRAINT pk_vv_candidates PRIMARY KEY (run_id, video_id),
        CONSTRAINT fk_vv_cand_run   FOREIGN KEY (run_id)   REFERENCES dbo.viral_validation_runs(run_id),
        CONSTRAINT fk_vv_cand_video FOREIGN KEY (video_id) REFERENCES dbo.youtube_videos(video_id),
        CONSTRAINT chk_vv_chart_rank CHECK (
            (youtube_charted = 1 AND youtube_chart_rank IS NOT NULL) OR
            (youtube_charted = 0 AND youtube_chart_rank IS NULL))
    );
END
GO

/* 3) Mot dong = mot quan sat tu mot nguon ngoai (khong gop nhieu nguon vao 1 dong) */
IF OBJECT_ID('dbo.viral_validation_evidence', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.viral_validation_evidence (
        evidence_id           BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT pk_vv_evidence PRIMARY KEY,
        run_id                INT           NOT NULL,
        video_id              VARCHAR(20)   NOT NULL,
        external_source       VARCHAR(30)   NOT NULL,
        source_granularity    VARCHAR(10)   NOT NULL,   -- do min cua nguon: hourly/daily/weekly
        source_scope          VARCHAR(10)   NOT NULL,   -- nguon do o cap video/channel/topic
        external_metric       NVARCHAR(100) NOT NULL,   -- 'n/a' neu not_available
        external_value        NVARCHAR(200) NULL,
        evidence_result       VARCHAR(15)   NOT NULL,   -- supports/contradicts/inconclusive/not_available
        evidence_collected_at DATETIME2     NOT NULL,   -- luc THU bang chung (UTC) != ranking_observed_at
        evidence_region       VARCHAR(5)    NULL,
        evidence_url          NVARCHAR(1000) NULL,
        evidence_path         NVARCHAR(500) NULL,       -- screenshot trong repo
        notes                 NVARCHAR(1000) NULL,
        collected_by          NVARCHAR(100) NULL,
        inserted_at           DATETIME2     NOT NULL CONSTRAINT df_vv_ev_inserted DEFAULT SYSUTCDATETIME(),
        CONSTRAINT fk_vv_ev_cand FOREIGN KEY (run_id, video_id)
            REFERENCES dbo.viral_validation_candidates(run_id, video_id),
        CONSTRAINT chk_vv_source CHECK (external_source IN ('vidIQ','Google Trends','Social Blade','Other')),
        CONSTRAINT chk_vv_gran   CHECK (source_granularity IN ('hourly','daily','weekly')),
        CONSTRAINT chk_vv_scope  CHECK (source_scope IN ('video','channel','topic')),
        CONSTRAINT chk_vv_result CHECK (evidence_result IN ('supports','contradicts','inconclusive','not_available')),
        -- Co ket qua thi bat buoc co URL + (screenshot hoac ghi chu)
        CONSTRAINT chk_vv_proof CHECK (
            evidence_result = 'not_available'
            OR (evidence_url IS NOT NULL AND (evidence_path IS NOT NULL OR notes IS NOT NULL))),
        -- Nguon khong ung ho ket luan -> bat buoc giai thich
        CONSTRAINT chk_vv_explain CHECK (
            evidence_result NOT IN ('contradicts','inconclusive','not_available') OR notes IS NOT NULL),
        -- Chong duplicate evidence cung video/nguon/metric/timestamp
        CONSTRAINT uq_vv_evidence UNIQUE (run_id, video_id, external_source, external_metric, evidence_collected_at)
    );
    CREATE INDEX idx_vv_ev_video ON dbo.viral_validation_evidence (video_id);
END
GO

/* View A: do lech thoi gian. Nguong theo do min cua nguon (chinh tai day neu nhom doi y). */
CREATE OR ALTER VIEW dbo.vw_viral_evidence_timing AS
SELECT
    e.*,
    r.region_code,
    r.ranking_observed_at,
    ABS(DATEDIFF(MINUTE, r.ranking_observed_at, e.evidence_collected_at)) AS gap_minutes,
    CASE WHEN ABS(DATEDIFF(MINUTE, r.ranking_observed_at, e.evidence_collected_at)) >
              CASE e.source_granularity WHEN 'hourly' THEN 180 WHEN 'daily' THEN 1440 ELSE 10080 END
         THEN 1 ELSE 0 END AS time_mismatch
FROM dbo.viral_validation_evidence e
JOIN dbo.viral_validation_runs r ON r.run_id = e.run_id;
GO

/* View B: validation_status duoc TINH, khong nhap tay.
   Level 2 chi tinh khi: supports + khong time_mismatch + scope video/topic
   (Social Blade cap channel chi la ngu canh, khong du de xac nhan 1 video).
   Level 2 va Level 3 doc lap nhau -> co the dong thoi (L2+L3). */
CREATE OR ALTER VIEW dbo.vw_viral_validation_status AS
SELECT
    c.run_id, r.region_code, r.ranking_observed_at,
    c.video_id, c.rank_in_run, c.viral_score,
    c.youtube_charted, c.youtube_chart_rank,
    ISNULL(a.evidence_count, 0)      AS evidence_count,
    ISNULL(a.supports_count, 0)      AS supports_count,
    ISNULL(a.contradicts_count, 0)   AS contradicts_count,
    ISNULL(a.not_available_count, 0) AS not_available_count,
    ISNULL(a.time_mismatch_count, 0) AS time_mismatch_count,
    CASE
        WHEN c.youtube_charted = 1 AND ISNULL(a.supports_count, 0) > 0 THEN 'L2+L3_corroborated_and_charted'
        WHEN c.youtube_charted = 1                                      THEN 'L3_charted_growth_confirmed'
        WHEN ISNULL(a.supports_count, 0) > 0                            THEN 'L2_externally_corroborated'
        ELSE 'L1_viral_candidate'
    END AS validation_status,
    CASE WHEN ISNULL(a.contradicts_count, 0) > 0 THEN 1 ELSE 0 END AS disagreement_flag,
    CASE WHEN ISNULL(a.evidence_count, 0) = 0 THEN 'no_evidence_collected' ELSE 'evidence_collected' END AS coverage
FROM dbo.viral_validation_candidates c
JOIN dbo.viral_validation_runs r ON r.run_id = c.run_id
OUTER APPLY (
    SELECT
        COUNT(*) AS evidence_count,
        SUM(CASE WHEN t.evidence_result = 'supports' AND t.time_mismatch = 0
                  AND t.source_scope IN ('video','topic') THEN 1 ELSE 0 END) AS supports_count,
        SUM(CASE WHEN t.evidence_result = 'contradicts'   THEN 1 ELSE 0 END) AS contradicts_count,
        SUM(CASE WHEN t.evidence_result = 'not_available' THEN 1 ELSE 0 END) AS not_available_count,
        SUM(t.time_mismatch) AS time_mismatch_count
    FROM dbo.vw_viral_evidence_timing t
    WHERE t.run_id = c.run_id AND t.video_id = c.video_id
) a;
GO