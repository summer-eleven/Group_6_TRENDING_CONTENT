IF DB_ID('youtube_trending') IS NULL
BEGIN
    CREATE DATABASE youtube_trending;
END
GO
 
USE youtube_trending;
GO
 
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'youtube_videos')
BEGIN
    CREATE TABLE youtube_videos (
        -- video_id la duy nhat tren YouTube -> vua la khoa chinh vua dung
        -- de chan trung lap khi insert/upsert.
        video_id            VARCHAR(20)     NOT NULL PRIMARY KEY,
 
        title               NVARCHAR(500)   NOT NULL,   -- NVARCHAR vi tieu de co the co dau/unicode
        channel_id          VARCHAR(30)     NULL,
        channel_title       NVARCHAR(200)   NULL,
        category_id         VARCHAR(10)     NULL,        -- API tra ve dang string, khong ep INT
        published_at        DATETIME2       NULL,
        region_code         VARCHAR(5)      NULL,         -- "VN", "US", "GB", ...
 
        view_count          BIGINT          NULL,
        like_count          BIGINT          NULL,
        comment_count       BIGINT          NULL,
 
        is_trending         BIT             NOT NULL DEFAULT 0,  -- 1 = trending, 0 = control video
        trending_rank       INT             NULL,                -- NULL voi control video
 
        -- Metadata phuc vu truy vet & Report 2 (chung minh du lieu di qua pipeline).
        raw_object_path     NVARCHAR(500)   NULL,        -- duong dan object goc tren MinIO
        collected_at        DATETIME2       NOT NULL,     -- luc crawler thu thap
        inserted_at         DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
 
        CONSTRAINT chk_view_count_non_negative CHECK (view_count IS NULL OR view_count >= 0),
        CONSTRAINT chk_like_count_non_negative CHECK (like_count IS NULL OR like_count >= 0)
    );
 
    CREATE INDEX idx_youtube_videos_published_at ON youtube_videos (published_at);
    CREATE INDEX idx_youtube_videos_channel_id   ON youtube_videos (channel_id);
    CREATE INDEX idx_youtube_videos_collected_at ON youtube_videos (collected_at);
    CREATE INDEX idx_youtube_videos_is_trending   ON youtube_videos (is_trending);
END
GO