CREATE DATABASE youtube_trending;
GO
USE youtube_trending;
GO

CREATE TABLE videos (
    video_id        VARCHAR(50)     NOT NULL PRIMARY KEY,
    title           NVARCHAR(500)   NOT NULL,
    channel_id      VARCHAR(50)     NULL,
    channel_title   NVARCHAR(200)   NULL,
    category_id     INT             NULL,
    published_at    DATETIME2       NULL,
    view_count      BIGINT          NULL,
    like_count      BIGINT          NULL,
    comment_count   BIGINT          NULL,
    region_code     VARCHAR(10)     NULL,
    collected_at    DATETIME2       DEFAULT GETDATE()
);
GO