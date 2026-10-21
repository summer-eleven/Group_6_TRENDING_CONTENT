import numpy as np
import pandas as pd

from src.ingestion.us_seed_sources import dedupe_seed_rows, merge_seeds
from src.modeling.build_classification_dataset import (FEATURE_COLUMNS, build_classification_frame,
                                                       check_leakage)
from src.processing.audit_us_discovery import concentration_metrics

UC = lambda n: "UC" + str(n).zfill(22)


def test_merge_seeds_dedupes_and_filters_invalid():
    out = merge_seeds([UC(1), UC(2)], [{"channel_id": UC(2)}, {"channel_id": "bad"}, {"channel_id": UC(3)}])
    assert out == [UC(1), UC(2), UC(3)]


def test_dedupe_seed_rows_excludes_known():
    rows = [{"channel_id": UC(1)}, {"channel_id": UC(1)}, {"channel_id": UC(2)}]
    assert dedupe_seed_rows(rows, {UC(2)}) == [{"channel_id": UC(1)}]


def test_concentration_metrics():
    m = concentration_metrics(["a", "a", "b", "c"])
    assert m["channels"] == 3 and m["top1_share"] == 0.5
    assert concentration_metrics([])["channels"] == 0


def test_leakage_check_passes_and_detects():
    assert check_leakage() == []
    bad = [("f_x", "t24_view_count", "t0_collected_at", ""), ("f_y", "ok", "window_end", "")]
    assert len(check_leakage(bad)) == 2


def _rq1(n=40):
    t0 = pd.Timestamp("2026-10-10 03:00", tz="UTC") + pd.to_timedelta(np.arange(n), unit="h")
    status = ["OBSERVED_POSITIVE"] * 8 + ["OBSERVED_NEGATIVE_FULL_COVERAGE"] * 20 + ["UNKNOWN_INCOMPLETE_COVERAGE"] * 12
    lab = [1] * 8 + [0] * 20 + [np.nan] * 12
    return pd.DataFrame({
        "video_id": [f"v{i}" for i in range(n)], "region_code": "US", "channel_id": [f"c{i % 5}" for i in range(n)],
        "published_at_utc": t0 - pd.Timedelta(hours=3), "t0_collected_at_utc": t0,
        "window_end_utc": t0 + pd.Timedelta(hours=24), "video_age_at_t0_hours": 3.0,
        "upload_hour_local": 10, "upload_weekday_local": 2, "upload_period": "OFFICE_HOURS",
        "t0_view_count": np.arange(n) * 100 + 50, "primary_fresh_24h": True,
        "chart_label_status": status, "chart_observed_24h": lab,
        # cot ro ri phai khong lot vao feature
        "t24_view_count": 999999, "view_delta_t24": 999999})


def _reg(n=40):
    return pd.DataFrame({"video_id": [f"v{i}" for i in range(n)], "region_code": "US", "category_id": "10",
                         "t0_like_count": 5, "t0_comment_count": 1})


def test_build_frame_labels_and_no_leak_columns():
    full, sup = build_classification_frame(_rq1(), _reg())
    assert len(full) == 40 and len(sup) == 28          # UNKNOWN bi loai
    assert set(sup["label"].unique()) == {0, 1}
    assert not any(c.startswith("t24_") or "delta" in c for c in sup.columns)
    assert all(c in sup.columns for c in FEATURE_COLUMNS)
    assert (sup["feature_time"] <= sup["prediction_cutoff"]).all()
    # dem channel chi nhin ve qua khu
    first = full.sort_values("prediction_cutoff").iloc[0]
    assert first["f_channel_prior_cohort_videos"] == 0


def test_classifier_runs_and_blocks(tmp_path, monkeypatch):
    import subprocess, sys
    _, sup = build_classification_frame(_rq1(), _reg())
    ds = tmp_path / "d.csv"; sup.to_csv(ds, index=False)
    r = subprocess.run([sys.executable, "-m", "src.modeling.train_trending_classifier", "--dataset", str(ds),
                        "--output-dir", str(tmp_path / "o"), "--min-per-class", "5"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "o" / "evaluation_classification.csv").exists()
    only_pos = sup[sup["label"] == 1]; ds2 = tmp_path / "p.csv"; only_pos.to_csv(ds2, index=False)
    r2 = subprocess.run([sys.executable, "-m", "src.modeling.train_trending_classifier", "--dataset", str(ds2),
                         "--output-dir", str(tmp_path / "o2")], capture_output=True, text=True)
    assert r2.returncode == 2 and "BLOCKED" in (tmp_path / "o2" / "model_card_classification.md").read_text()
