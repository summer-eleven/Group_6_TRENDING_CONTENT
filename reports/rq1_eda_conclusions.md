# RQ1 EDA Conclusions & Data Dictionary
## Group 6 — Analysis of Factors Influencing YouTube Trending Content
### Author: Ha (JP Market) | Date: 2026-10-21

---

## I. Data Dictionary (RQ1 Fields)

| # | Field | Type | Description | Example |
|---|-------|------|-------------|---------|
| 1 | `video_id` | string | YouTube video identifier (11 chars) | `FaZ6RnqoGAc` |
| 2 | `region_code` | string | ISO 3166-1 alpha-2 country code from chart/discovery source | `JP`, `VN`, `US` |
| 3 | `published_at` | datetime (UTC) | Video publication timestamp from YouTube API | `2026-10-04T07:01:45Z` |
| 4 | `local_upload_hour` | int (0-23) | Hour of upload in local timezone (JP=UTC+9, VN=UTC+7, US=UTC-4 EDT) | `16` |
| 5 | `upload_period` | string | `Office` if local_upload_hour in [9,17), else `Rest` | `Office` |
| 6 | `category_id` | int | YouTube category ID | `22` (People & Blogs) |
| 7 | `chart_status` | string | `OBSERVED_CHARTED` = seen on chart; `NOT_OBSERVED_WITH_COVERAGE` = not seen but chart was monitored | `OBSERVED_CHARTED` |
| 8 | `chart_coverage_ratio` | float | Fraction of expected hourly chart observations actually captured (0.0-1.0) | `0.85` |
| 9 | `best_rank` | int/NA | Highest (lowest number) position observed on chart; NA if never charted | `3` |
| 10 | `view_count` | int | View count at time of snapshot | `1234567` |
| 11 | `like_count` | int | Like count at time of snapshot | `45678` |
| 12 | `video_available` | bool | Whether video was accessible when checked | `True` |
| 13 | `collected_at` | datetime | Timestamp of data collection | `2026-10-18T14:01:57Z` |
| 14 | `is_trending_num` | int | Binary: 1 if charted, 0 if not | `1` |

### De-duplication Rules
- **Global count**: unique by `video_id` alone (one row per video globally)
- **Country analysis**: unique by `(video_id, region_code)` (a video can appear in multiple countries)
- **Current dataset**: 0 cross-region duplicates found

### Label Definitions
- `OBSERVED_CHARTED`: Video was seen at least once on the YouTube mostPopular chart during the 7-day observation window
- `NOT_OBSERVED_WITH_COVERAGE`: Video was NOT seen on chart, AND the chart monitor ran at least once during the observation window (confirming the chart was checked)
- `UNKNOWN` / `INCOMPLETE`: Video has insufficient chart monitoring data; excluded from RQ1 primary analysis
- **NEVER label a video as `NON_TRENDING`** without full 7-day chart coverage

---

## II. EDA Conclusions

### A. Upload Time Distribution

Across all three markets (VN, JP, US), most videos are uploaded during **Rest hours** (outside 09:00-17:00 local time), accounting for approximately 77% of the sample. This is consistent with the nature of YouTube content creation, where many creators upload in the evening or early morning.

**JP-specific**: The upload hour distribution in Japan shows peaks around 18:00-21:00 JST (after-work hours) and a secondary peak around 06:00-08:00 JST (early morning uploads, likely scheduled releases).

### B. Chart Status Distribution

The overall observed chart rate is **33.29%** (1,210 out of 3,635 eligible videos). However, this varies dramatically by region:

| Region | Chart Rate | Interpretation |
|--------|-----------|----------------|
| JP | 14.82% | Lowest rate; most JP videos come from rolling cohort discovery (not chart-first) |
| VN | 22.90% | Moderate; mix of chart and cohort sources |
| US | 100.00% | All US videos were charted; sampling bias from mostPopular endpoint |
| Others | 100.00% | Same as US: chart-sourced samples only |

The 100% rate for US and other regions indicates these samples consist entirely of videos discovered FROM the chart — making them unsuitable for testing whether upload time affects chart probability (no variation in outcome).

### C. RQ1 Hypothesis Test Results

**Research Question**: Does upload time (Office hours vs Rest hours) affect the probability of a YouTube video appearing on the trending chart?

**Methodology**: Chi-Square test of independence (or Fisher's exact test if expected cell counts < 5) on a 2x2 contingency table: (Office/Rest) x (Charted/Not Charted).

| Market | Direction | Effect Size | p-value | Verdict |
|--------|-----------|------------|---------|---------|
| **VN** | Office > Rest (+5.79pp) | Small | 0.026* | Significant at 5% |
| **JP** | Rest > Office (+6.38pp) | Small | 0.003** | Significant at 1% |
| **US** | Cannot test | N/A | N/A | No outcome variation |

**Key insight**: The direction of the effect is **opposite** between VN and JP:
- In **Vietnam**, uploading during office hours is associated with a slightly higher trending probability
- In **Japan**, uploading during rest hours (evening/night) is associated with a higher trending probability

This suggests that the optimal upload time for trending potential may be **market-specific** and influenced by local audience behavior, time zone effects, or content ecosystem differences.

### D. Limitations

1. **Sampling bias**: Videos discovered via `mostPopular` are pre-selected by YouTube's algorithm. Our sample cannot represent all YouTube videos — only those in the algorithm's consideration set.

2. **Chart coverage gaps**: The chart monitor runs only when the laptop is powered on. Estimated uptime coverage for JP is ~4.2% of theoretical maximum (3 captures out of ~72 expected in 3 days). Many charted videos may have been missed.

3. **Correlation ≠ causation**: Even with a significant p-value, we cannot conclude that upload time *causes* trending. Confounding variables (content type, channel size, promotion strategy) may explain the association.

4. **Small charted counts**: JP has only 34 office-hour charted videos. While the Chi-Square test is valid (expected counts > 5), the precision of the effect size estimate is limited.

5. **Temporal confounds**: Office-hour uploaders may systematically differ from rest-hour uploaders in ways that affect trending probability independently of timing.

6. **US data insufficiency**: With 100% chart rate, the US market cannot contribute to the RQ1 analysis. A larger collection with more non-charted videos is needed.

---

## III. Recommendations for Report 3

1. Present VN and JP results separately with clear indication of opposite effect directions
2. Do NOT generalize a single conclusion across all markets
3. Acknowledge the US data gap explicitly
4. Frame findings as "observed association" not "causal effect"
5. Include chart coverage metrics to contextualize confidence in the NOT_OBSERVED labels
6. Suggest future work: increase sample size, ensure 24/7 chart monitoring, add content-type controls

---

*This document is part of HA5 deliverables for Group 6 Report 3.*