# RQ1 Cross-Country Comparison Summary
## "Does upload time (Office vs Rest) affect YouTube trending probability?"

Generated: 2026-10-21 | Author: Ha (JP market) | Group 6 ADY201m

---

## 1. Summary Table by Region

| Region | Period | Eligible N | Charted | Not Charted | Chart Rate (%) | Test | Statistic | p-value | Conclusion |
|--------|--------|-----------|---------|-------------|----------------|------|-----------|---------|------------|
| **VN** | Office | 362 | 98 | 264 | 27.07% | Chi-Square | X²=4.95 | 0.026* | Reject H0 |
| **VN** | Rest | 935 | 199 | 736 | 21.28% | | | | |
| **VN** | _Delta_ | | | | **+5.79pp** | | | | |
| **JP** | Office | 348 | 34 | 314 | 9.77% | Chi-Square | X²=8.89 | 0.003** | Reject H0 |
| **JP** | Rest | 1325 | 214 | 1111 | 16.15% | | | | |
| **JP** | _Delta_ | | | | **-6.38pp** | | | | |
| **US** | Office | 70 | 70 | 0 | 100.00% | N/A | N/A | N/A | Insufficient variation |
| **US** | Rest | 229 | 229 | 0 | 100.00% | | | | |
| **US** | _Delta_ | | | | **0.00pp** | | | | |

> **pp** = percentage points

### Key Findings

1. **VN (Vietnam):** Office-hours uploads show a **higher** chart rate (+5.79pp) compared to Rest hours. Statistically significant at 5% level (p=0.026).

2. **JP (Japan):** Office-hours uploads show a **lower** chart rate (-6.38pp) compared to Rest hours. Statistically significant at 1% level (p=0.003). This is the **opposite direction** from VN.

3. **US (United States):** All 299 eligible US videos were `OBSERVED_CHARTED` (100% chart rate for both periods). This means there is **no variation in the outcome variable** — a 2x2 contingency table cannot be formed. The test is inapplicable; we cannot conclude anything about the US market from this sample.

### Interpretation Notes

- A statistically significant p-value provides evidence of **association** between upload timing and chart observation in the sample. It does NOT prove that upload time *causes* trending.
- The **opposite direction** between VN and JP suggests that the relationship between upload timing and trending may be market-specific, potentially influenced by local viewing habits, content creator strategies, or YouTube algorithm behavior in different markets.
- The US result is a data limitation, not a finding: our sampling method via `mostPopular` playlist inherently over-selects videos that are already trending.

---

## 2. Sample Composition

| Metric | VN | JP | US | Other* | Global |
|--------|-----|------|------|--------|--------|
| Eligible RQ1 sample | 1,297 | 1,673 | 299 | 366 | 3,635 |
| OBSERVED_CHARTED | 297 | 248 | 299 | 366 | 1,210 |
| NOT_OBSERVED_WITH_COVERAGE | 1,000 | 1,425 | 0 | 0 | 2,425 |
| Chart rate (%) | 22.90% | 14.82% | 100.00% | 100.00% | 33.29% |
| Office period (%) | 27.91% | 20.80% | 23.41% | — | 23.41% |
| Rest period (%) | 72.09% | 79.20% | 76.59% | — | 76.59% |

*Other regions: AU (17), GB (130), ID (45), KR (46), PH (40), SG (41), TH (47) — all 100% charted, insufficient non-charted observations for testing.

---

## 3. Chart Coverage & Data Quality

| Metric | Value |
|--------|-------|
| Total unique video_ids | 3,635 |
| Missing published_at | 0 |
| Duplicate (video_id only) | 0 |
| Chart monitor runs (JP) | 3 files (Oct 18, 19, 21) |
| Rolling cohort batches (JP) | 2 batches (10 + 200 videos) |
| T+24h delayed batches | 1 (batch JP_20261019, elapsed 45.55h, labeled DELAYED) |

### Chart Coverage Assessment

- JP chart monitor has been running **hourly** since Oct 18 but only captured **3 JSON files** (machine was likely off during some hours)
- The `chart_coverage_ratio` column in the dataset reflects the proportion of expected chart observations actually captured
- Videos with insufficient chart coverage are labeled `NOT_OBSERVED_WITH_COVERAGE` (never falsely labeled as `NON_TRENDING`)

---

## 4. Limitations & Bias

### 4.1 Sampling Bias
- **mostPopular playlist sampling**: Videos discovered through YouTube's `mostPopular` endpoint are already pre-filtered by YouTube's algorithm. This creates selection bias — our sample over-represents videos that YouTube already considers popular.
- **Channel-based discovery**: Seed channels come from the master dataset, which was built from chart-listed videos. New channels not in the master are never sampled.
- **Cross-region duplicates**: A video can appear in multiple regions' charts. De-duplication is handled per (video_id, region_code) for country-level analysis, and per video_id alone for global counts.

### 4.2 Chart Coverage Gaps
- **Laptop uptime dependency**: Chart monitor and rolling cohort tasks only run when the Windows machine is powered on. Weekend/overnight gaps reduce chart coverage.
- **3 chart captures for JP in 3 days**: This is below the theoretical 72 hourly captures, meaning many chart appearances may have been missed.
- **Consequence**: The `NOT_OBSERVED_WITH_COVERAGE` count may include videos that actually appeared on the chart when the machine was off. This would **understate** the true chart rate.

### 4.3 Statistical Power
- **US market**: Zero non-charted videos means the test is inapplicable. To test US, we need more non-charted video observations.
- **JP Office charted count**: Only 34 charted during office hours. While sufficient for Chi-Square (expected counts > 5), the effect size may not be precisely estimated.
- **Small region samples** (AU, SG, PH, etc.): Too few observations for meaningful country-level testing.

### 4.4 Temporal Confounds
- Upload time may correlate with **content type** (e.g., news channels upload during office hours, entertainment channels at night). The observed association may reflect content type differences rather than a pure timing effect.
- The 7-day observation window for chart status may not capture videos that trend after a delay.

---

## 5. Reconciliation with Team Data

### Comparison Points for Nguyen (US) and Ha (VN Leader):
- **Global unique video_ids**: 3,635 (Ha's processed dataset)
- **VN charted rate**: 22.90% — to be compared with Nguyen's SQL query results
- **If discrepancies found**, check:
  1. Cross-region duplicates (same video_id in VN and US charts)
  2. Timezone conversion differences (UTC vs local)
  3. Missing chart runs when laptop was off
  4. Different eligibility criteria (7-day coverage threshold)

### Example Video IDs for Cross-Verification (JP):
| video_id | published_at (UTC) | local_hour (JP) | period | chart_status |
|----------|-------------------|-----------------|--------|-------------|
| FaZ6RnqoGAc | 2026-10-04 07:01:45 | 16 | Office | OBSERVED_CHARTED |
| BoMpd2Pq6DU | 2026-10-04 12:00:17 | 21 | Rest | OBSERVED_CHARTED |
| Z9NWm-Ycy2Q | 2026-09-29 15:00:06 | 0 | Rest | OBSERVED_CHARTED |
| 69X7ZSEUx2Y | 2026-09-30 17:00:35 | 2 | Rest | NOT_OBSERVED_WITH_COVERAGE |
| rs1yyYSHz-4 | 2026-09-10 12:38:43 | 21 | Rest | NOT_OBSERVED_WITH_COVERAGE |

> Cross-region duplicate video_ids in dataset: **0** (no overlap between VN/JP/US samples)

---

*Report prepared for Group 6 Report 3. All raw data stored locally; cleaned CSV is generated output (not committed to Git).*