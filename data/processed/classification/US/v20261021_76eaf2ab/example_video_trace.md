# Vi du truy vet 1 video: moi feature deu biet truoc cutoff

- video_id: `Hqb67RxZqCg`
- prediction_cutoff (T0): `2026-10-20 01:49:23.339254+00:00`
- published_at: `2026-10-19 19:00:09+00:00`

| feature | gia tri | nguon | biet tai |
|---|---|---|---|
| f_upload_hour_local | 15 | published_at_utc -> gio dia phuong | published_at = 2026-10-19 19:00:09+00:00 (OK) |
| f_upload_weekday_local | 0 | published_at_utc -> gio dia phuong | published_at = 2026-10-19 19:00:09+00:00 (OK) |
| f_is_weekend | 0 | published_at_utc -> gio dia phuong | published_at = 2026-10-19 19:00:09+00:00 (OK) |
| f_is_office_hours | 1 | upload_period | published_at = 2026-10-19 19:00:09+00:00 (OK) |
| f_video_age_at_t0_hours | 6.820649792777777 | t0_collected_at_utc - published_at_utc | t0_collected_at = 2026-10-20 01:49:23.339254+00:00 (OK) |
| f_log_t0_views | 10.81703452373922 | t0_view_count | t0_collected_at = 2026-10-20 01:49:23.339254+00:00 (OK) |
| f_log_t0_views_per_hour | 8.897196504920165 | t0_view_count / tuoi | t0_collected_at = 2026-10-20 01:49:23.339254+00:00 (OK) |
| f_t0_like_rate | 0.08278849624964903 | t0_like_count / t0_view_count | t0_collected_at = 2026-10-20 01:49:23.339254+00:00 (OK) |
| f_t0_comment_rate | 0.006899041354137419 | t0_comment_count / t0_view_count | t0_collected_at = 2026-10-20 01:49:23.339254+00:00 (OK) |
| f_channel_prior_cohort_videos | 0 | dem video cung channel co T0 som hon | t0_collected_at = 2026-10-20 01:49:23.339254+00:00 (OK) |
| f_category_id | 10 | registry.category_id | published_at = 2026-10-19 19:00:09+00:00 (OK) |

Nhan `label` chi duoc tao tu chart quan sat TRONG (T0, T0+24h]; khong la feature.