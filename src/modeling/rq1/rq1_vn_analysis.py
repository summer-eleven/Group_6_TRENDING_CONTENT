"""RQ1 (Vietnam only): upload time vs YouTube Trending observation.

Reads  : data/processed/rq1_youtube_cohort_VN.csv  (never modified)
Writes : reports/rq1/vietnam/tables/*.csv and reports/rq1/vietnam/figures/*.png

Run from the project root (Python 3.10):
  pip install pandas numpy scipy matplotlib
  python src/modeling/rq1/rq1_vn_analysis.py

Label rules (never convert UNKNOWN into Not Trending):
  OBSERVED_POSITIVE, OBSERVED_NEGATIVE_FULL_COVERAGE -> eligible
  UNKNOWN_INCOMPLETE_COVERAGE -> excluded from the main analysis
"""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, chi2_contingency, norm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC = Path("data/processed/rq1_youtube_cohort_VN.csv")
OUT = Path("reports/rq1/vietnam")
TAB, FIG = OUT / "tables", OUT / "figures"
TZ = "Asia/Ho_Chi_Minh"
POS, NEG, UNK = ("OBSERVED_POSITIVE", "OBSERVED_NEGATIVE_FULL_COVERAGE",
                 "UNKNOWN_INCOMPLETE_COVERAGE")


def wilson(k, n, z=1.96):
    """Wilson 95% confidence interval in percent."""
    p = k / n
    c = (p + z * z / 2 / n) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / 4 / n / n) / (1 + z * z / n)
    return 100 * (c - h), 100 * (c + h)


def rate_table(df, col):
    """Trending count, total and rate with Wilson CI for each level of col."""
    g = df.groupby(col)["y"].agg(trending="sum", total="count").reset_index()
    g["not_trending"] = g["total"] - g["trending"]
    g["rate_pct"] = 100 * g["trending"] / g["total"]
    ci = [wilson(k, n) for k, n in zip(g["trending"], g["total"])]
    g["ci_low"], g["ci_high"] = [c[0] for c in ci], [c[1] for c in ci]
    return g


def test_2x2(a, b):
    """a, b = (trending, total). Returns Fisher p, chi-square p, Cramer V."""
    t = np.array([[a[0], a[1] - a[0]], [b[0], b[1] - b[0]]])
    chi = chi2_contingency(t, correction=False)
    return dict(fisher_p=fisher_exact(t)[1], chi2_p=chi[1],
                min_expected=chi[3].min(), cramers_v=np.sqrt(chi[0] / t.sum()))


def cmh(df, label):
    """Cochran-Mantel-Haenszel test of office vs non-office, stratified by batch."""
    A = E = V = R = S = 0.0
    k = 0
    for _, x in df.groupby("batch_id"):
        o, n = x[x.off == 1], x[x.off == 0]
        a, b = o.y.sum(), len(o) - o.y.sum()
        c, d = n.y.sum(), len(n) - n.y.sum()
        N, m1, m0, n1, n0 = a + b + c + d, a + b, c + d, a + c, b + d
        if N < 2 or min(m1, m0, n1) == 0:
            continue
        k += 1
        A += a; E += m1 * n1 / N
        V += m1 * m0 * n1 * n0 / (N * N * (N - 1))
        R += a * d / N; S += b * c / N
    z = (A - E) / np.sqrt(V)
    return dict(sample=label, n_videos=len(df), strata=k, office_pos_observed=A,
                office_pos_expected=round(E, 2), mh_odds_ratio=round(R / S, 3),
                cmh_p=2 * (1 - norm.cdf(abs(z))))


def bar(ax, x, y, color, ylabel, xlabel, labels=None, ci=None, fmt="{:.1f}"):
    ax.bar(x, y, color=color, width=0.7)
    if ci is not None:
        lo, hi = np.array(ci).T
        ax.errorbar(x, y, yerr=[np.array(y) - lo, hi - np.array(y)], fmt="none",
                    ecolor="black", capsize=6)
    for xi, yi in zip(x, y):
        ax.text(xi, yi, fmt.format(yi), ha="center", va="bottom", fontsize=8)
    ax.set_ylabel(ylabel); ax.set_xlabel(xlabel)
    if labels is not None:
        ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.spines[["top", "right"]].set_visible(False)


def save(fig, name):
    fig.tight_layout(); fig.savefig(FIG / name, dpi=200); plt.close(fig)


def main():
    if not SRC.exists():
        sys.exit(f"Missing input file: {SRC} (run from the project root)")
    TAB.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(SRC, low_memory=False)
    assert d["region_code"].eq("VN").all(), "Non-VN rows found"
    assert not d["video_id"].duplicated().any(), "Duplicate video_id"

    # Consistency check of local time fields against the UTC timestamp
    loc = pd.to_datetime(d["published_at_utc"], utc=True).dt.tz_convert(TZ)
    assert (loc.dt.hour == d["upload_hour_local"]).all(), "Hour mismatch"
    assert (loc.dt.dayofweek == d["upload_weekday_local"]).all(), "Weekday mismatch"

    d["y"] = (d["chart_label_status"] == POS).astype(int)
    d["off"] = (d["upload_period"] == "OFFICE_HOURS").astype(int)

    # 1) Label funnel
    funnel = d["chart_label_status"].value_counts().rename_axis("label").reset_index(name="videos")
    funnel.to_csv(TAB / "label_counts.csv", index=False)
    print(funnel.to_string(index=False))

    # 2) Eligible sample (positive + negative only)
    e = d[d["chart_label_status"].isin([POS, NEG])].copy()
    print(f"Eligible: {len(e)} | trending: {e.y.sum()} | excluded UNKNOWN: {(d.chart_label_status == UNK).sum()}")

    # 3) Main test: office vs non-office (pipeline definition)
    per = rate_table(e, "upload_period"); per.to_csv(TAB / "office_vs_non_office.csv", index=False)
    o = per[per.upload_period == "OFFICE_HOURS"].iloc[0]
    n = per[per.upload_period == "NON_OFFICE_HOURS"].iloc[0]
    main = test_2x2((o.trending, o.total), (n.trending, n.total))
    pd.DataFrame([main]).to_csv(TAB / "office_vs_non_office_tests.csv", index=False)
    print(per.round(2).to_string(index=False)); print({k: round(v, 4) for k, v in main.items()})

    # 4) Sensitivity: alternative office-hours definitions
    le = pd.to_datetime(e["published_at_utc"], utc=True).dt.tz_convert(TZ)
    rows = []
    for name, m in {"09:00-16:59 all days": le.dt.hour.between(9, 16),
                    "09:00-16:59 Mon-Fri": le.dt.hour.between(9, 16) & (le.dt.dayofweek < 5),
                    "08:00-16:59 Mon-Fri (pipeline)": e["off"].eq(1)}.items():
        a, b = e[m], e[~m]
        t = test_2x2((a.y.sum(), len(a)), (b.y.sum(), len(b)))
        rows.append(dict(definition=name, office_trending=a.y.sum(), office_total=len(a),
                         rest_trending=b.y.sum(), rest_total=len(b), **t))
    pd.DataFrame(rows).to_csv(TAB / "sensitivity_office_definition.csv", index=False)

    # 5) Hour and weekday tables
    hr = rate_table(e, "upload_hour_local"); hr.to_csv(TAB / "by_hour.csv", index=False)
    wd = rate_table(e, "upload_weekday_local")
    wd["weekday"] = wd["upload_weekday_local"].map(dict(enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])))
    wd.to_csv(TAB / "by_weekday.csv", index=False)

    # 6) Batch effect and stratified (CMH) analysis on ALL videos
    bt = d.groupby("batch_id").agg(videos=("y", "size"), observed_positive=("y", "sum"),
                                   coverage_ratio=("chart_coverage_ratio", "mean")).reset_index()
    bt.to_csv(TAB / "by_batch.csv", index=False)
    cm = pd.DataFrame([cmh(d, "all batches"),
                       cmh(d[d.chart_coverage_ratio >= 0.5], "coverage >= 0.5"),
                       cmh(d[d.primary_fresh_24h], "fresh <= 24h at T0")])
    cm.to_csv(TAB / "cmh_by_batch.csv", index=False); print(cm.to_string(index=False))
    full = e[e.chart_coverage_complete.astype(bool)]
    print(f"Pooled rate {100*e.y.mean():.2f}% vs full-coverage rate {100*full.y.mean():.2f}% (n={len(full)})")

    # 7) Figures
    blue, orange = "#2b59c3", "#c2410c"
    h = hr.set_index("upload_hour_local").reindex(range(24), fill_value=0)
    f, ax = plt.subplots(figsize=(9, 4)); bar(ax, np.arange(24), h["total"], blue, "Number of videos", "Upload hour (local, UTC+7)", fmt="{:.0f}"); ax.set_title("Chart 1 - Video Distribution by Upload Hour"); save(f, "chart1_hour_distribution.png")
    f, ax = plt.subplots(figsize=(9, 4)); bar(ax, np.arange(24), h["rate_pct"], orange, "Trending rate (%)", "Upload hour (local, UTC+7)"); ax.set_title("Chart 2 - Trending Rate by Upload Hour"); save(f, "chart2_hour_rate.png")
    f, ax = plt.subplots(figsize=(5, 4)); bar(ax, np.arange(2), per["rate_pct"].values, blue, "Trending rate (%) with 95% CI", "", labels=["Non-Office" if p.startswith("NON") else "Office" for p in per.upload_period], ci=list(zip(per.ci_low, per.ci_high)), fmt="{:.2f}"); ax.set_title("Chart 3 - Office vs Non-Office"); save(f, "chart3_office_vs_non_office.png")
    f, ax = plt.subplots(figsize=(7, 4)); bar(ax, np.arange(7), wd["rate_pct"].values, orange, "Trending rate (%)", "Upload weekday", labels=wd["weekday"]); ax.set_title("Chart 4 - Trending Rate by Weekday"); save(f, "chart4_weekday_rate.png")
    pooled = (100 * e.y.mean(), wilson(e.y.sum(), len(e))); fr = (100 * full.y.mean(), wilson(full.y.sum(), len(full)))
    f, ax = plt.subplots(figsize=(5, 4)); bar(ax, np.arange(2), [pooled[0], fr[0]], blue, "Trending rate (%) with 95% CI", "", labels=["Pooled", "Full-coverage batch"], ci=[pooled[1], fr[1]], fmt="{:.2f}"); ax.set_title("Chart 5 - Pooled vs Full-Coverage"); save(f, "chart5_pooled_vs_full_coverage.png")
    print("Done. Outputs in", OUT)


if __name__ == "__main__":
    main()
