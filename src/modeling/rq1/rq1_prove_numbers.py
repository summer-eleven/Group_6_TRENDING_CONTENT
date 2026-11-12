"""Re-derive every number shown in the Vietnamese RQ1 slides, straight from the data files.

Run from the project root (Python 3.10, pandas/numpy/scipy). Read-only: nothing is modified.
  python src/modeling/rq1/rq1_prove_numbers.py
Optional paths: --cohort, --master, --regions, --raw (folder with chart_VN_*.json)
Each line prints: slide | what | value found | expected | OK or DIFF.
"""
import argparse, glob, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, norm

POS, NEG, UNK = ("OBSERVED_POSITIVE", "OBSERVED_NEGATIVE_FULL_COVERAGE", "UNKNOWN_INCOMPLETE_COVERAGE")
ok_count = diff_count = 0


def check(slide, what, got, exp, tol=0.0):
    """Print one verification line."""
    global ok_count, diff_count
    good = abs(got - exp) <= tol if isinstance(exp, (int, float)) else got == exp
    ok_count += good; diff_count += (not good)
    print(f"[{'OK  ' if good else 'DIFF'}] slide {slide:>2} | {what:<58} | found: {got} | expected: {exp}")


def wilson(k, n, z=1.96):
    p = k / n
    c = (p + z * z / 2 / n) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / 4 / n / n) / (1 + z * z / n)
    return round(100 * (c - h), 2), round(100 * (c + h), 2)


def cmh_p(df):
    """Cochran-Mantel-Haenszel p-value for office vs non-office, stratified by batch."""
    A = E = V = 0.0
    for _, x in df.groupby("batch_id"):
        o, n = x[x.off == 1], x[x.off == 0]
        a, b, c, d = o.y.sum(), len(o) - o.y.sum(), n.y.sum(), len(n) - n.y.sum()
        N, m1, m0, n1, n0 = a + b + c + d, a + b, c + d, a + c, b + d
        if N < 2 or min(m1, m0, n1) == 0:
            continue
        A += a; E += m1 * n1 / N; V += m1 * m0 * n1 * n0 / (N * N * (N - 1))
    return round(float(2 * (1 - norm.cdf(abs((A - E) / np.sqrt(V))))), 2), int(A), round(E, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", default="data/processed/rq1_youtube_cohort_VN.csv")
    ap.add_argument("--master", default="data/global/youtube_global_master.csv")
    ap.add_argument("--regions", default="data/global/youtube_video_regions.csv")
    ap.add_argument("--raw", default="data/raw/chart_monitor/VN")
    a = ap.parse_args()
    if not Path(a.cohort).exists():
        sys.exit(f"Missing cohort file: {a.cohort} (run from the project root)")
    d = pd.read_csv(a.cohort, low_memory=False)
    assert d.region_code.eq("VN").all(), "Non-VN rows in cohort"
    d["y"] = (d.chart_label_status == POS).astype(int)
    d["off"] = (d.upload_period == "OFFICE_HOURS").astype(int)
    e = d[d.chart_label_status.isin([POS, NEG])]

    print("== Slide 3: data funnel ==")
    if Path(a.master).exists() and Path(a.regions).exists():
        check(3, "unique videos in global master", pd.read_csv(a.master, usecols=["video_id"]).video_id.nunique(), 19248)
        r = pd.read_csv(a.regions)
        check(3, "unique videos tagged VN", r[r.region_code == "VN"].video_id.nunique(), 12055)
    else:
        print("[SKIP] global master/regions file not found")
    check(3, "videos in the VN cohort", len(d), 11531)
    check(3, "eligible videos (positive + negative)", len(e), 2044)

    print("== Slide 4: labels ==")
    check(4, "OBSERVED_POSITIVE", int((d.chart_label_status == POS).sum()), 46)
    check(4, "OBSERVED_NEGATIVE_FULL_COVERAGE", int((d.chart_label_status == NEG).sum()), 1998)
    check(4, "UNKNOWN_INCOMPLETE_COVERAGE", int((d.chart_label_status == UNK).sum()), 9487)
    check(4, "UNKNOWN share (%)", round(100 * (d.chart_label_status == UNK).mean(), 1), 82.3)

    print("== Slide 5: data quality ==")
    check(5, "duplicate video_id", int(d.video_id.duplicated().sum()), 0)
    check(5, "missing published_at_utc", int(d.published_at_utc.isna().sum()), 0)
    loc = pd.to_datetime(d.published_at_utc, utc=True).dt.tz_convert("Asia/Ho_Chi_Minh")
    check(5, "hour or weekday mismatch vs UTC+7", int(((loc.dt.hour != d.upload_hour_local) | (loc.dt.dayofweek != d.upload_weekday_local)).sum()), 0)
    check(5, "T24 views lower than T0 views", int((d.t24_view_count < d.t0_view_count).sum()), 29)
    check(5, "t0_view_count equal to 0", int((d.t0_view_count == 0).sum()), 97)
    print("[INFO] duration / aspect ratio columns present:", [c for c in d.columns if "duration" in c or "aspect" in c] or "none")


    print("== Slide 6-7: raw chart captures ==")

    files = sorted(glob.glob(str(Path(a.raw) / "chart_VN_*.json")))

    if files:
        runs, ent = [], []

        for f in files:
            with open(f, encoding="utf-8") as fp:
                p = json.load(fp)

            runs.append((
                p["run_id"],
                p["collected_at_utc"],
                bool(p["next_page_available"])
            ))

            ent.extend(
                (p["run_id"], x["video_id"])
                for x in p["entries"]
            )

        R = pd.DataFrame(
            runs,
            columns=["run_id", "t", "more"]
        )
        R["t"] = pd.to_datetime(R["t"], utc=True)

        E = pd.DataFrame(
            ent,
            columns=["run_id", "video_id"]
        ).merge(R[["run_id", "t"]], on="run_id")

        # Historical cutoff reconstructed from current raw files.
        cutoff = pd.Timestamp("2026-11-08T22:10:03.210682Z")

        R_hist = R[R.t <= cutoff].copy()
        hist_run_ids = set(R_hist.run_id)

        E_hist = E[E.run_id.isin(hist_run_ids)].copy()

        full_hist = R_hist[~R_hist.more]

        # Historical snapshot: values used in the original slides.
        check(6, "historical raw chart files", len(R_hist), 335)
        check(7, "historical fully paginated runs", len(full_hist), 334)
        check(
            6,
            "historical distinct videos seen on VN chart",
            int(E_hist.video_id.nunique()),
            1301
        )

        perday = full_hist.groupby(
            full_hist.t.dt.strftime("%m-%d")
        ).size()

        check(
            7,
            "historical days with all 24 hourly runs",
            sorted(perday[perday == 24].index),
            ["10-25", "11-02"]
        )

        # Current inventory: informational only, not compared with
        # historical slide values.
        full_all = R[~R.more]

        print("\n[INFO] Current raw inventory")
        print("  Raw chart files:", len(R))
        print("  Fully paginated runs:", len(full_all))
        print("  Distinct videos:", int(E.video_id.nunique()))

        # Keep the original cohort validation against all available
        # raw captures. Observation windows determine which captures
        # are relevant to each cohort video.
        check(
            6,
            "chart videos that are in the cohort",
            len(set(E.video_id) & set(d.video_id)),
            75
        )

        times = E.groupby("video_id").t.apply(
            lambda s: np.sort(s.dt.tz_convert(None).values)
        )

        ft = np.sort(
            full_all.t.dt.tz_convert(None).values
        )

        t0 = pd.to_datetime(
            d.t0_collected_at_utc, utc=True
        ).dt.tz_convert(None).values

        we = pd.to_datetime(
            d.window_end_utc, utc=True
        ).dt.tz_convert(None).values

        hit, same = [], 0

        for i, vid in enumerate(d.video_id.values):
            ts = times.get(vid)

            hit.append(
                0 if ts is None else
                int(((ts >= t0[i]) & (ts <= we[i])).sum())
            )

            bins = len(set(
                pd.to_datetime(
                    ft[(ft >= t0[i]) & (ft < we[i])]
                ).floor("h")
            ))

            same += int(
                bins == d.chart_hour_bins_covered.values[i]
            )

        hit = np.array(hit)

        check(
            6,
            "positives found again in raw entries",
            int(((hit > 0) & (d.y == 1)).sum()),
            46
        )

        check(
            6,
            "negatives never seen in raw entries",
            int(((hit == 0) & (d.chart_label_status == NEG)).sum()),
            1998
        )

        check(
            6,
            "videos with identical hourly coverage (%)",
            round(100 * same / len(d), 1),
            99.8
        )

    else:
        print(f"[SKIP] no raw files in {a.raw}")

    print("== Slide 8-9, 12-13: hour and weekday ==")
    h = e.groupby("upload_hour_local").y.agg(["sum", "count"])
    check(8, "videos uploaded at 19:00", int(h.loc[19, "count"]), 186)
    check(8, "videos uploaded at 20:00", int(h.loc[20, "count"]), 169)
    check(9, "trending at 18:00 / total", f"{int(h.loc[18, 'sum'])} / {int(h.loc[18, 'count'])}", "12 / 149")
    check(13, "trending uploaded 15:00-19:59", int(h.loc[15:19, "sum"].sum()), 30)
    w = e.groupby("upload_weekday_local").y.agg(["sum", "count"])
    check(12, "weekday trending counts Mon..Sun", w["sum"].astype(int).tolist(), [4, 6, 12, 3, 4, 7, 10])
    check(12, "weekday totals Mon..Sun", w["count"].astype(int).tolist(), [197, 231, 285, 321, 434, 415, 161])

    print("== Slide 10-11: office vs non-office ==")
    t = e.groupby("off").y.agg(["sum", "count"])
    o, n = t.loc[1], t.loc[0]
    check(10, "office trending / total", f"{int(o['sum'])} / {int(o['count'])}", "9 / 374")
    check(10, "non-office trending / total", f"{int(n['sum'])} / {int(n['count'])}", "37 / 1670")
    tab = np.array([[o["sum"], o["count"] - o["sum"]], [n["sum"], n["count"] - n["sum"]]])
    check(10, "Fisher exact p-value", round(float(fisher_exact(tab)[1]), 3), 0.847)
    check(10, "office rate 95% CI", wilson(int(o["sum"]), int(o["count"])), (1.27, 4.51))
    check(10, "non-office rate 95% CI", wilson(int(n["sum"]), int(n["count"])), (1.61, 3.04))
    alt = loc.loc[e.index]
    m = alt.dt.hour.between(9, 16) & (alt.dt.dayofweek < 5)
    ta = np.array([[e.y[m].sum(), (~(e.y[m] == 1)).sum()], [e.y[~m].sum(), (~(e.y[~m] == 1)).sum()]])

    # Sensitivity analysis: alternative office-hours definitions
    le = pd.to_datetime(e["published_at_utc"], utc=True).dt.tz_convert("Asia/Ho_Chi_Minh")

    sensitivity_masks = {
        "09:00-16:59 all days": le.dt.hour.between(9, 16),
        "09:00-16:59 Mon-Fri": (
            le.dt.hour.between(9, 16) & (le.dt.dayofweek < 5)
        ),
        "08:00-16:59 Mon-Fri (pipeline)": e["upload_period"].eq("OFFICE_HOURS"),
    }

    expected_sensitivity = {
        "09:00-16:59 all days": (14, 550, 0.614),
        "09:00-16:59 Mon-Fri": (9, 339, 0.550),
        "08:00-16:59 Mon-Fri (pipeline)": (9, 374, 0.847),
    }

    for name, mask in sensitivity_masks.items():
        a, b = e[mask], e[~mask]
        p = float(fisher_exact([
            [int(a.y.sum()), int(len(a) - a.y.sum())],
            [int(b.y.sum()), int(len(b) - b.y.sum())],
        ])[1])

        expected_positive, expected_total, expected_p = expected_sensitivity[name]

        check(
            10,
            f"{name}: office trending",
            int(a.y.sum()),
            expected_positive,
        )
        check(
            10,
            f"{name}: office total",
            len(a),
            expected_total,
        )
        check(
            10,
            f"{name}: Fisher p",
            round(p, 3),
            round(expected_p, 3),
        )

    print("== Slide 14-16: sampling bias, CMH, channels ==")
    fb = e[e.chart_coverage_complete.astype(bool)]
    check(14, "full-coverage batch trending / total", f"{int(fb.y.sum())} / {len(fb)}", "2 / 2000")
    check(14, "pooled rate (%)", round(100 * e.y.mean(), 2), 2.25)
    check(14, "full-coverage rate 95% CI", wilson(int(fb.y.sum()), len(fb)), (0.03, 0.36))
    for lab, sub, n_exp, p_exp in [("all batches", d, 11531, 0.54), ("coverage >= 0.5", d[d.chart_coverage_ratio >= 0.5], 9682, 0.93),
                                   ("fresh <= 24h at T0", d[d.primary_fresh_24h], 5286, 0.35)]:
        check(15, f"CMH sample size, {lab}", len(sub), n_exp)
        check(15, f"CMH p-value, {lab}", cmh_p(sub)[0], p_exp, 0.006)
    ar = d[d.rq1_analysis_ready]
    check(16, "rq1_analysis_ready videos", len(ar), 549)
    check(16, "positives inside rq1_analysis_ready", int(ar.y.sum()), 0)
    check(16, "channels among eligible videos", int(e.channel_id.nunique()), 390)
    check(16, "channels with a trending video", int(e[e.y == 1].channel_id.nunique()), 36)

    print(f"\nSummary: {ok_count} OK, {diff_count} DIFF")


if __name__ == "__main__":
    main()
