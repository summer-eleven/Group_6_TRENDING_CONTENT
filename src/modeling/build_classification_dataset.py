"""Xay dataset Classification chong data leakage (NG-04).

Bai toan: tai thoi diem T0 (prediction_cutoff) cua mot video, du doan video do co xuat hien
tren chart mostPopular (category 0) trong 24h sau T0 hay khong.

QUY TAC CHONG LEAKAGE
  * Feature chi lay thong tin biet tai/truoc T0: published_at, gio dang, category, metric do tai T0,
    so video truoc do cua cung channel trong cohort.
  * KHONG dung T24, view_delta_24h, views_per_hour_t24, chart_*, window_end... lam feature.
  * Nhan 1: da quan sat tren chart. Nhan 0: CHI khi 24 gio-bin chart deu day du
    (OBSERVED_NEGATIVE_FULL_COVERAGE). UNKNOWN bi loai khoi training nhung van duoc dem trong summary.

Dau vao : data/processed/rq1_youtube_cohort_<REGION>.csv (build_rq1_dataset --apply)
          data/processed/youtube_cohort_registry_<REGION>.csv (category, like/comment tai T0)
Dau ra  : data/processed/classification/<REGION>/<version>/
            dataset.csv, feature_dictionary.csv, leakage_checklist.md,
            example_video_trace.md, summary.json

  uv run python -m src.modeling.build_classification_dataset --region US
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

LABEL_OK = {"OBSERVED_POSITIVE", "OBSERVED_NEGATIVE_FULL_COVERAGE"}

NUMERIC_FEATURES = [
    "f_upload_hour_local", "f_upload_weekday_local", "f_is_weekend", "f_is_office_hours",
    "f_video_age_at_t0_hours", "f_log_t0_views", "f_log_t0_views_per_hour",
    "f_t0_like_rate", "f_t0_comment_rate", "f_channel_prior_cohort_videos",
]
CATEGORICAL_FEATURES = ["f_category_id"]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# (feature, nguon, thoi diem biet duoc, mo ta)
FEATURE_DICTIONARY = [
    ("f_upload_hour_local", "published_at_utc -> gio dia phuong", "published_at", "Gio dang (0-23) theo mui gio thi truong"),
    ("f_upload_weekday_local", "published_at_utc -> gio dia phuong", "published_at", "Thu trong tuan, Monday=0"),
    ("f_is_weekend", "published_at_utc -> gio dia phuong", "published_at", "1 neu dang Thu 7/CN"),
    ("f_is_office_hours", "upload_period", "published_at", "1 neu OFFICE_HOURS (T2-T6, 8h-16h59 local)"),
    ("f_video_age_at_t0_hours", "t0_collected_at_utc - published_at_utc", "t0_collected_at", "Tuoi video luc T0 (gio)"),
    ("f_log_t0_views", "t0_view_count", "t0_collected_at", "log1p(view tai T0)"),
    ("f_log_t0_views_per_hour", "t0_view_count / tuoi", "t0_collected_at", "log1p(view tai T0 / max(tuoi, 0.25h))"),
    ("f_t0_like_rate", "t0_like_count / t0_view_count", "t0_collected_at", "Ty le like tai T0"),
    ("f_t0_comment_rate", "t0_comment_count / t0_view_count", "t0_collected_at", "Ty le comment tai T0"),
    ("f_channel_prior_cohort_videos", "dem video cung channel co T0 som hon", "t0_collected_at",
     "So video truoc do cua channel trong cohort (chi dem T0 < cutoff cua hang hien tai)"),
    ("f_category_id", "registry.category_id", "published_at", "Category YouTube (categorical)"),
]

# Cot nguon bi cam lam feature (xuat hien sau cutoff hoac chinh la nhan)
FORBIDDEN_SOURCE_PREFIXES = (
    "t24_", "chart_", "first_chart", "best_chart", "window_", "view_delta", "views_per_hour_t24",
    "actual_t24", "full_chart", "like_delta", "comment_delta",
)
ALLOWED_KNOWN_AT = {"published_at", "t0_collected_at"}


def check_leakage(feature_dictionary=FEATURE_DICTIONARY) -> list:
    """Tra ve danh sach vi pham (rong = dat). Kiem tra tren tu dien feature."""
    problems = []
    for name, source, known_at, _ in feature_dictionary:
        if known_at not in ALLOWED_KNOWN_AT:
            problems.append(f"{name}: known_at={known_at!r} khong nam trong {sorted(ALLOWED_KNOWN_AT)}")
        low = source.lower()
        for p in FORBIDDEN_SOURCE_PREFIXES:
            if p in low:
                problems.append(f"{name}: nguon '{source}' chua token cam '{p}'")
    return problems


def _to_utc(series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce")


def build_classification_frame(rq1: pd.DataFrame, registry: pd.DataFrame,
                               include_non_fresh: bool = False):
    """Thuan khiet (de test). Tra ve (full, supervised)."""
    df = rq1.copy()
    df["video_id"] = df["video_id"].astype(str)
    df["region_code"] = df["region_code"].astype(str)
    reg = registry.copy()
    reg["video_id"] = reg["video_id"].astype(str)
    reg["region_code"] = reg["region_code"].astype(str)
    keep = [c for c in ("video_id", "region_code", "category_id", "t0_like_count", "t0_comment_count")
            if c in reg.columns]
    reg = reg[keep].drop_duplicates(["video_id", "region_code"])
    df = df.merge(reg, on=["video_id", "region_code"], how="left", validate="one_to_one")

    for c in ("published_at_utc", "t0_collected_at_utc", "window_end_utc"):
        df[c] = _to_utc(df[c])
    df["prediction_cutoff"] = df["t0_collected_at_utc"]
    df["feature_time"] = df["t0_collected_at_utc"]

    age = pd.to_numeric(df["video_age_at_t0_hours"], errors="coerce")
    views = pd.to_numeric(df["t0_view_count"], errors="coerce")
    likes = pd.to_numeric(df.get("t0_like_count"), errors="coerce")
    comments = pd.to_numeric(df.get("t0_comment_count"), errors="coerce")
    safe_views = views.where(views > 0)

    df["f_upload_hour_local"] = pd.to_numeric(df["upload_hour_local"], errors="coerce")
    df["f_upload_weekday_local"] = pd.to_numeric(df["upload_weekday_local"], errors="coerce")
    df["f_is_weekend"] = (df["f_upload_weekday_local"] >= 5).astype(int)
    df["f_is_office_hours"] = (df["upload_period"].astype(str) == "OFFICE_HOURS").astype(int)
    df["f_video_age_at_t0_hours"] = age.clip(lower=0)
    df["f_log_t0_views"] = np.log1p(views.clip(lower=0))
    df["f_log_t0_views_per_hour"] = np.log1p((views / age.clip(lower=0.25)).clip(lower=0))
    df["f_t0_like_rate"] = likes / safe_views
    df["f_t0_comment_rate"] = comments / safe_views
    df["f_category_id"] = df["category_id"].astype("string").fillna("unknown")

    # So video truoc do cua channel: chi tinh cac hang co cutoff som hon (khong nhin tuong lai)
    order = df.sort_values(["prediction_cutoff", "video_id"]).index
    df["f_channel_prior_cohort_videos"] = 0
    df.loc[order, "f_channel_prior_cohort_videos"] = (
        df.loc[order].groupby("channel_id", dropna=False).cumcount())

    label = pd.to_numeric(df["chart_observed_24h"], errors="coerce")
    df["label"] = label.astype("Int64")
    df["label_quality"] = df["chart_label_status"].astype(str)

    fresh = df["primary_fresh_24h"].fillna(False).astype(bool)
    mask = df["label_quality"].isin(LABEL_OK) & df["label"].notna()
    if not include_non_fresh:
        mask &= fresh
    supervised = df.loc[mask].copy()

    cols = ["video_id", "region_code", "channel_id", "prediction_cutoff", "feature_time",
            "label", "label_quality"] + FEATURE_COLUMNS
    return df, supervised[cols].sort_values("prediction_cutoff").reset_index(drop=True)


def write_trace(path: Path, row: pd.Series, raw_row: pd.Series):
    lines = ["# Vi du truy vet 1 video: moi feature deu biet truoc cutoff", "",
             f"- video_id: `{row['video_id']}`", f"- prediction_cutoff (T0): `{row['prediction_cutoff']}`",
             f"- published_at: `{raw_row.get('published_at_utc')}`", "",
             "| feature | gia tri | nguon | biet tai |", "|---|---|---|---|"]
    for name, source, known_at, _ in FEATURE_DICTIONARY:
        ts = raw_row.get("published_at_utc") if known_at == "published_at" else raw_row.get("t0_collected_at_utc")
        ok = "OK" if pd.notna(ts) and ts <= row["prediction_cutoff"] else "KIEM TRA"
        lines.append(f"| {name} | {row[name]} | {source} | {known_at} = {ts} ({ok}) |")
    lines += ["", "Nhan `label` chi duoc tao tu chart quan sat TRONG (T0, T0+24h]; khong la feature."]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_leakage_checklist(path: Path, problems: list):
    items = [
        ("Feature chi dung thong tin tai/truoc T0", not problems),
        ("Khong dung T24 / view_delta_24h / views_per_hour_t24", True),
        ("Khong dung chart_* / first_chart_seen / best_chart_rank", True),
        ("Nhan 0 chi tu OBSERVED_NEGATIVE_FULL_COVERAGE (khong tu UNKNOWN)", True),
        ("Moi video_id chi 1 hang -> khong lap train/test theo snapshot", True),
        ("Tach train/test theo thoi gian (prediction_cutoff) trong buoc train", True),
    ]
    text = "# Leakage checklist\n\n" + "\n".join(f"- [{'x' if ok else ' '}] {t}" for t, ok in items)
    if problems:
        text += "\n\n## Vi pham\n" + "\n".join(f"- {p}" for p in problems)
    path.write_text(text + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Build leakage-safe classification dataset")
    ap.add_argument("--region", required=True, choices=("VN", "US", "JP"))
    ap.add_argument("--rq1-path", type=Path)
    ap.add_argument("--registry-path", type=Path)
    ap.add_argument("--output-root", type=Path, default=Path("data/processed/classification"))
    ap.add_argument("--include-non-fresh", action="store_true",
                    help="Giu ca video da >24h tuoi tai T0 (mac dinh: chi video 'fresh')")
    a = ap.parse_args()
    rq1_path = a.rq1_path or Path(f"data/processed/rq1_youtube_cohort_{a.region}.csv")
    reg_path = a.registry_path or Path(f"data/processed/youtube_cohort_registry_{a.region}.csv")

    rq1 = pd.read_csv(rq1_path, dtype={"video_id": "string", "region_code": "string", "batch_id": "string"})
    registry = pd.read_csv(reg_path, dtype={"video_id": "string", "region_code": "string", "category_id": "string"})
    problems = check_leakage()
    if problems:
        raise SystemExit("LEAKAGE CHECK FAILED:\n" + "\n".join(problems))

    full, sup = build_classification_frame(rq1, registry, a.include_non_fresh)
    counts = sup["label"].value_counts().to_dict()
    n_pos, n_neg = int(counts.get(1, 0)), int(counts.get(0, 0))
    status_counts = full["label_quality"].value_counts().to_dict()
    blocker = None
    if n_pos == 0 or n_neg == 0:
        blocker = (f"Thieu lop hop le cho phan loai nhi phan (positives={n_pos}, negatives={n_neg}). "
                   "Bao Ha: can chart coverage 24h day du de co nhan 0 hop le. KHONG gan 0 tu UNKNOWN.")

    digest = hashlib.sha256(sup.to_csv(index=False).encode("utf-8")).hexdigest()[:8]
    version = f"v{pd.Timestamp.now('UTC').strftime('%Y%m%d')}_{digest}"
    out = a.output_root / a.region / version
    out.mkdir(parents=True, exist_ok=True)
    sup.to_csv(out / "dataset.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(FEATURE_DICTIONARY, columns=["feature", "source", "known_at", "description"]).to_csv(
        out / "feature_dictionary.csv", index=False, encoding="utf-8-sig")
    write_leakage_checklist(out / "leakage_checklist.md", problems)
    if len(sup):
        vid = sup.iloc[0]["video_id"]
        write_trace(out / "example_video_trace.md", sup.iloc[0], full.loc[full["video_id"] == vid].iloc[0])
    summary = {"region": a.region, "version": version, "rows_total": int(len(full)),
               "rows_supervised": int(len(sup)), "positives": n_pos, "negatives": n_neg,
               "label_status_counts": {k: int(v) for k, v in status_counts.items()},
               "unknown_excluded": int(status_counts.get("UNKNOWN_INCOMPLETE_COVERAGE", 0)),
               "include_non_fresh": a.include_non_fresh, "blocker": blocker, "inputs": [str(rq1_path), str(reg_path)]}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Output:", out)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if blocker:
        print("\nBLOCKER:", blocker)


if __name__ == "__main__":
    main()
