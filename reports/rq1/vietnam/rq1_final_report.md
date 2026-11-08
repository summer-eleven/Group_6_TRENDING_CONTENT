# RQ1 Final Report: Upload Time and YouTube Trending Probability in Vietnam

Group 6, ADY201m, Topic 4 (Trending Content, YouTube). Region: Vietnam (`region_code = VN`). Time zone: `Asia/Ho_Chi_Minh` (UTC+7).

All figures and tables are produced by `src/modeling/rq1/rq1_vn_analysis.py` and stored in `reports/rq1/vietnam/figures/` and `reports/rq1/vietnam/tables/`. No data from other countries is used.

---

## 1. Research Question and Hypotheses

**RQ1.** Does upload time affect the probability of a YouTube video appearing on the trending chart in Vietnam?

- **H0:** Upload time is not associated with the probability of a YouTube video appearing on the trending chart.
- **H1:** Upload time is associated with the probability of a YouTube video appearing on the trending chart (non-directional).

Note: an earlier planning document (`docs/finalize_analysis_plan.md`) states a directional H1 (rest hours higher than office hours). This report uses the non-directional H1 above and tests it with two-sided tests.

---

## 2. Dataset and Data Quality

**Source.** `data/processed/rq1_youtube_cohort_VN.csv`, built by `src/processing/build_rq1_dataset.py` from the VN rolling cohorts and the hourly `videos.list(chart=mostPopular)` monitor.

| Item | Value |
|---|---|
| Videos in the VN cohort | 11,531 (unique `video_id`) |
| Collection batches | 9 (12 Oct to 22 Oct 2026, T0 time) |
| Channels in the cohort | 1,121 |
| Chart monitor | 335 raw captures, 12 Oct to 8 Nov 2026 (334 full runs) |
| Distinct videos seen on the VN chart | 1,301 (75 of them are in the cohort) |

**Outcome definition.** A video is *Trending* if it appears at least once in a fully paginated hourly chart run within 24 hours after its T0 observation. The default (category 0) `mostPopular` chart for VN is used.

| Label | Videos | Rule |
|---|---:|---|
| `OBSERVED_POSITIVE` | 46 | Seen on the chart within the 24-hour window |
| `OBSERVED_NEGATIVE_FULL_COVERAGE` | 1,998 | All 24 hourly bins have a full chart run and the video was never seen |
| `UNKNOWN_INCOMPLETE_COVERAGE` | 9,487 | Not enough chart coverage to decide |

The main analysis uses the 2,044 eligible videos (positive plus negative). The 9,487 UNKNOWN videos (82.3 percent) are excluded from the main denominator and are never relabelled as Not Trending.

**Verification against raw data.** The labels were recomputed from the 335 raw chart files: all 46 positives and all 1,998 negatives match, and hourly coverage matches for 99.8 percent of videos.

**Data quality checks.**

| Check | Result |
|---|---|
| Duplicate `video_id` | 0 |
| Missing `published_at` | 0 |
| Local hour and weekday vs UTC timestamp | 0 mismatches |
| T24 views lower than T0 views | 29 videos |
| `t0_view_count = 0` | 97 videos |
| T24 not available | 2,061 videos (2,000 not yet due, 61 missing despite being due) |
| Duration, aspect ratio, Shorts metadata | Not stored in the dataset |

**Coverage gaps.** The monitor ran a full 24 hourly runs on only two days (25 Oct and 2 Nov). No run exists on 31 Oct and 4 to 7 Nov. Mean coverage per batch ranges from 0.08 to 1.00, and only batch `VN_20261017_092001` (2,000 videos) has complete 24-hour coverage.

---

## 3. Methodology

- **Upload time.** `published_at_utc` is converted to `Asia/Ho_Chi_Minh`; `upload_hour_local` (0 to 23) and `upload_weekday_local` (0 = Monday) are verified against the timestamp.
- **Office hours.** The pipeline label `upload_period` defines OFFICE_HOURS as Monday to Friday, 08:00 to 16:59 local time. Because project documents use other definitions, two alternatives are reported as sensitivity checks: 09:00 to 16:59 on all days, and 09:00 to 16:59 on Monday to Friday.
- **Trending rate.** Trending videos divided by eligible videos, with a 95 percent Wilson confidence interval.
- **Tests.** Chi-square test of independence for 2x2 tables when all expected counts are at least 5, and Fisher's exact test otherwise (reported for all 2x2 tables); Cramér's V as effect size.
- **Batch-stratified analysis.** To use all 11,531 videos without treating UNKNOWN as negative, a Cochran-Mantel-Haenszel (CMH) test is applied with collection batch as the stratum. Coverage is identical for all videos in a batch, so comparing office and non-office videos inside a batch is not biased by coverage. The outcome here is "observed on the chart at least once", not "Not Trending".
- **Not performed.** Duration groups, Shorts versus Long-form and the logistic regression were not run, because the dataset has no duration or format metadata and only 46 positive observations are available.

---

## 4. Exploratory Data Analysis

Figures: `chart1_hour_distribution.png`, `chart2_hour_rate.png`, `chart4_weekday_rate.png`, `chart5_pooled_vs_full_coverage.png`.

- **Upload hour (Chart 1).** Uploads peak in the evening, at 19:00 (186 videos) and 20:00 (169), and are lowest between 04:00 and 06:00 (44 to 45 per hour).
- **Trending rate by hour (Chart 2).** The highest rates occur at 18:00 (12 of 149, 8.1 percent), 16:00 (5 of 75, 6.7 percent) and 17:00 (6 of 104, 5.8 percent). Thirty of the 46 Trending videos were uploaded between 15:00 and 19:59. Many hours have zero or one Trending video, so hourly rates are unstable and no multiple-testing correction was applied; this chart is descriptive only.
- **Weekday (Chart 4).** Rates range from 0.9 percent (Thursday, Friday) to 6.2 percent (Sunday, 10 of 161). A crude chi-square test gives p = 0.0007, but this result is not reliable (see Section 6).

---

## 5. Statistical Results

### 5.1 Office hours versus non-office hours (main test)

| Upload period | Trending | Not Trending | Total | Trending rate (95% CI) |
|---|---:|---:|---:|---|
| Office Hours | 9 | 365 | 374 | 2.41% (1.27 to 4.51) |
| Non-Office Hours | 37 | 1,633 | 1,670 | 2.22% (1.61 to 3.04) |

- Minimum expected count: 8.42, so the chi-square test is valid (p = 0.822).
- Fisher's exact test: p = 0.847.
- Cramér's V = 0.005 (negligible).
- **Decision:** do not reject H0.

### 5.2 Sensitivity to the office-hours definition

| Definition | Office Trending / Total | Fisher p |
|---|---|---:|
| 08:00 to 16:59, Mon to Fri (pipeline) | 9 / 374 | 0.847 |
| 09:00 to 16:59, Mon to Fri | 9 / 339 | 0.550 |
| 09:00 to 16:59, all days | 14 / 550 | 0.614 |

The conclusion does not depend on the definition.

### 5.3 Batch-stratified analysis (CMH)

| Sample | Videos | Office positives (observed / expected) | MH odds ratio | CMH p |
|---|---:|---|---:|---:|
| All batches | 11,531 | 9 / 10.7 | 0.80 | 0.54 |
| Coverage at least 0.5 | 9,682 | 9 / 9.2 | 0.97 | 0.93 |
| Uploaded at most 24 h before T0 | 5,286 | 4 / 2.7 | 1.74 | 0.35 |

No stratum shows evidence of an association. The last row rests on only 12 positive videos.

### 5.4 Sampling bias check

| Sample | Trending / Total | Rate (95% CI) |
|---|---|---|
| Pooled eligible videos (9 batches) | 46 / 2,044 | 2.25% (1.69 to 2.99) |
| Only the full-coverage batch | 2 / 2,000 | 0.10% (0.03 to 0.36) |

All 1,998 negatives come from one batch, while 44 of the 46 positives come from other batches whose remaining videos are UNKNOWN. The pooled rate is therefore inflated by the sampling design and should not be interpreted as the population Trending probability.

---

## 6. Discussion

1. **Answer to the hypothesis.** There is no statistical evidence that office-hours uploads differ from non-office uploads in the probability of appearing on the VN chart (p = 0.85 in the main test, p = 0.54 in the batch-stratified test, negligible effect size). This holds for three office-hours definitions.
2. **Practical meaning.** The estimated difference is 0.19 percentage points, which is practically negligible, but the confidence intervals are wide (office: 1.27 to 4.51 percent), so a moderate effect cannot be excluded.
3. **Why absence of evidence is not evidence of absence.** Only 46 Trending videos from 36 channels were observed, so statistical power is low.
4. **Weekday and hour patterns.** The Sunday and late-afternoon peaks are not reliable. Negatives come from a single collection week, so weekday counts reflect that week, and 24 hourly comparisons were made without adjustment.
5. **Factors that may affect the results.** Videos are clustered by channel (up to 10 videos per channel); the cohort is built from channel upload playlists and includes channels that are not clearly Vietnamese (for example, a rough check of Vietnamese diacritics in titles finds them in about 22 percent of the cohort but in 93.5 percent of positives); video age at T0 ranges from 0.1 to 168 hours; content type and channel popularity are not controlled.
6. **View growth.** The cohort has only two view measurements per video (T0 and T24), so growth curves cannot be drawn from it. T24 views per hour is higher for Trending videos (median about 1,235 versus 157), which is descriptive only and does not show that upload time influences Trending.

---

## 7. Conclusion

Using 2,044 Vietnamese videos with a reliable label, the data **do not reject H0**: upload during office hours is not statistically associated with the probability of appearing on the VN trending chart (Fisher p = 0.847, Cramér's V = 0.005). A batch-stratified analysis of all 11,531 videos gives the same conclusion (CMH p = 0.54). This is a statement of insufficient evidence, not proof of no effect, and no causal claim is made.

---

## 8. Limitations and Future Work

**Limitations.**
- 82.3 percent of videos lack 24-hour chart coverage, mainly because the monitor was not running during many hours.
- Selection bias: negatives are concentrated in one batch; the cohort is not a random sample of Vietnamese uploads.
- Only 46 positive observations in 36 channels; tests ignore channel clustering and are likely optimistic.
- Duration, aspect ratio and Shorts metadata are missing, so the duration and Shorts analyses and the logistic regression were not performed.
- Snapshot limits: two view measurements per video; the older history file (1,696 videos, 25 Sep to 4 Oct) has 1,547 view decreases and 1,312 missing view counts and does not overlap with the cohort.
- Office hours are defined differently across project documents.

**Future work.**
- Run the chart monitor continuously on an always-on machine and fix the stale `.daily_run.lock` that stopped new cohorts after 22 Oct.
- Collect more cohorts so that more videos reach complete coverage and more positives are observed.
- Fetch `contentDetails.duration` with `videos.list`, and add a reliable format signal for Shorts.
- Use channel-clustered methods (for example GEE or channel-level analysis) and restrict the cohort to Vietnamese channels.
- Add logistic regression once there are enough positive observations (about 10 per predictor).
