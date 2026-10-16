USE [youtube_trending]
GO
/****** Object:  Table [dbo].[youtube_chart_entries]    Script Date: 10/15/2026 10:46:29 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[youtube_chart_entries](
	[run_id] [varchar](64) NOT NULL,
	[video_id] [varchar](20) NOT NULL,
	[chart_rank] [int] NOT NULL,
	[title] [nvarchar](500) NULL,
	[channel_id] [varchar](50) NULL,
	[video_category_id] [varchar](20) NULL,
 CONSTRAINT [PK_chart_entries] PRIMARY KEY CLUSTERED
(
	[run_id] ASC,
	[video_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[youtube_chart_runs]    Script Date: 10/15/2026 10:46:29 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[youtube_chart_runs](
	[run_id] [varchar](64) NOT NULL,
	[region_code] [varchar](5) NOT NULL,
	[chart_name] [varchar](30) NOT NULL,
	[requested_category_id] [varchar](12) NOT NULL,
	[collected_at_utc] [datetime2](3) NOT NULL,
	[completed_at_utc] [datetime2](3) NOT NULL,
	[pages_fetched] [int] NOT NULL,
	[items_count] [int] NOT NULL,
	[next_page_available] [bit] NOT NULL,
	[minio_object_path] [nvarchar](500) NOT NULL,
	[inserted_at_utc] [datetime2](3) NOT NULL,
PRIMARY KEY CLUSTERED
(
	[run_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[youtube_cohort_observations]    Script Date: 10/15/2026 10:46:29 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[youtube_cohort_observations](
	[observation_id] [bigint] IDENTITY(1,1) NOT NULL,
	[batch_id] [varchar](80) NOT NULL,
	[video_id] [varchar](20) NOT NULL,
	[region_code] [varchar](5) NOT NULL,
	[phase] [varchar](3) NOT NULL,
	[observed_at_utc] [datetime2](3) NOT NULL,
	[view_count] [bigint] NULL,
	[like_count] [bigint] NULL,
	[comment_count] [bigint] NULL,
	[video_available] [bit] NOT NULL,
	[minio_object_path] [nvarchar](500) NULL,
	[inserted_at_utc] [datetime2](3) NOT NULL,
PRIMARY KEY CLUSTERED
(
	[observation_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_cohort_batch_video_phase] UNIQUE NONCLUSTERED
(
	[batch_id] ASC,
	[video_id] ASC,
	[phase] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
SET ANSI_PADDING ON
GO
/****** Object:  Index [IX_chart_entries_video]    Script Date: 10/15/2026 10:46:29 PM ******/
CREATE NONCLUSTERED INDEX [IX_chart_entries_video] ON [dbo].[youtube_chart_entries]
(
	[video_id] ASC,
	[run_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO
SET ANSI_PADDING ON
GO
/****** Object:  Index [IX_chart_runs_region_time]    Script Date: 10/15/2026 10:46:29 PM ******/
CREATE NONCLUSTERED INDEX [IX_chart_runs_region_time] ON [dbo].[youtube_chart_runs]
(
	[region_code] ASC,
	[collected_at_utc] DESC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO
SET ANSI_PADDING ON
GO
/****** Object:  Index [IX_cohort_video_time]    Script Date: 10/15/2026 10:46:29 PM ******/
CREATE NONCLUSTERED INDEX [IX_cohort_video_time] ON [dbo].[youtube_cohort_observations]
(
	[video_id] ASC,
	[region_code] ASC,
	[observed_at_utc] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO
ALTER TABLE [dbo].[youtube_chart_runs] ADD  DEFAULT (sysutcdatetime()) FOR [inserted_at_utc]
GO
ALTER TABLE [dbo].[youtube_cohort_observations] ADD  DEFAULT (sysutcdatetime()) FOR [inserted_at_utc]
GO
ALTER TABLE [dbo].[youtube_chart_entries]  WITH CHECK ADD  CONSTRAINT [FK_chart_entries_run] FOREIGN KEY([run_id])
REFERENCES [dbo].[youtube_chart_runs] ([run_id])
GO
ALTER TABLE [dbo].[youtube_chart_entries] CHECK CONSTRAINT [FK_chart_entries_run]
GO
ALTER TABLE [dbo].[youtube_chart_entries]  WITH CHECK ADD  CONSTRAINT [CK_chart_entries_rank] CHECK  (([chart_rank]>=(1)))
GO
ALTER TABLE [dbo].[youtube_chart_entries] CHECK CONSTRAINT [CK_chart_entries_rank]
GO
ALTER TABLE [dbo].[youtube_chart_runs]  WITH CHECK ADD  CONSTRAINT [CK_chart_runs_items] CHECK  (([items_count]>=(0)))
GO
ALTER TABLE [dbo].[youtube_chart_runs] CHECK CONSTRAINT [CK_chart_runs_items]
GO
ALTER TABLE [dbo].[youtube_chart_runs]  WITH CHECK ADD  CONSTRAINT [CK_chart_runs_pages] CHECK  (([pages_fetched]>=(1)))
GO
ALTER TABLE [dbo].[youtube_chart_runs] CHECK CONSTRAINT [CK_chart_runs_pages]
GO
ALTER TABLE [dbo].[youtube_cohort_observations]  WITH CHECK ADD  CONSTRAINT [CK_cohort_phase] CHECK  (([phase]='T24' OR [phase]='T0'))
GO
ALTER TABLE [dbo].[youtube_cohort_observations] CHECK CONSTRAINT [CK_cohort_phase]
GO
