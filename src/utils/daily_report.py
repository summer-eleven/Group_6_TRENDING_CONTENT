"""Báo cáo cuối ngày cho Rolling Cohort + Chart Monitor (Phương án A - Task Scheduler).

CHỈ ĐỌC file local: không gọi YouTube API, không truy cập SQL/MinIO, không sửa raw.
Đặt file tại src/utils/daily_report.py rồi chạy từ THƯ MỤC GỐC dự án:

  uv run python -m src.utils.daily_report --region JP
  uv run python -m src.utils.daily_report --region JP --date 2026-10-19

Đầu ra:
  - In báo cáo Markdown ra màn hình (dán thẳng vào nhóm chat).
  - reports/daily/<REGION>_<YYYYMMDD>_report.md      (báo cáo của ngày)
  - reports/daily/daily_kpi_<REGION>.csv             (1 dòng/ngày; chạy lại cùng ngày thì ghi đè dòng đó)

Các chỉ số khớp kế hoạch: unique_new_today, unique_region_total, global_unique,
duplicates, t24_done/delayed, chart_coverage, failed_calls.

Giới hạn cần nhớ:
  * global_unique / unique_region_total chỉ đếm dữ liệu CÓ TRÊN MÁY NÀY (master, registry, cohort local).
    Số toàn nhóm phải gộp bằng COUNT DISTINCT(video_id) trên SQL của Hạ.
  * Log .bat hiện không có timestamp -> lỗi không gán được theo ngày, chỉ báo số tích lũy.
    Để đếm lỗi theo ngày, mỗi .bat nên ghi một dòng đầu lượt chạy dạng "[2026-10-19T14:00:00] START":
      for /f %%i in ('powershell -nop -c "Get-Date -Format s"') do set TS=%%i
      echo [%TS%] START >> logs\\JP_chart.log
    Timestamp trong log được hiểu theo múi giờ của thị trường (JP = Asia/Tokyo).
  * Ngưỡng DELAYED (--delay-tolerance-hours) và ngưỡng độ phủ (--min-coverage) là giá trị MẶC ĐỊNH
    tạm thời; cần thống nhất bằng văn bản với Hạ trước khi dùng làm tiêu chí loại mẫu.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

REGIONS = ("VN", "US", "JP")
LOCAL_TZ = {"VN": "Asia/Ho_Chi_Minh", "US": "America/New_York", "JP": "Asia/Tokyo"}
MASTER = Path("data/processed/youtube_dataset_2000_clean.csv")
PROCESSED = Path("data/processed")
COHORT_ROOT = Path("data/raw/rolling_cohorts")
CHART_ROOT = Path("data/raw/chart_monitor")
LOG_DIR = Path("logs")
OUT_DIR = Path("reports/daily")

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
CHART_FILE_RE = re.compile(r"^chart_[A-Z]{2}_(\d{8})_")
LOG_TS_RE = re.compile(r"^\[?(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})")

FAIL_PATTERNS = [
    ("module_not_found", re.compile(r"No module named")),
    ("bad_cli_args", re.compile(r"unrecognized arguments|invalid choice|the following arguments are required")),
    ("traceback", re.compile(r"Traceback \(most recent call last\)")),
    ("sync_failed", re.compile(r"SYNC FAILED")),
    ("sql_error", re.compile(r"Invalid object name|\[42S02\]|Login failed|ODBC Driver .* (?:error|failed)", re.I)),
    ("api_error", re.compile(r"HttpError|quotaExceeded|rateLimitExceeded|Quota exceeded", re.I)),
    ("nonzero_exit", re.compile(r"exit code[:= ]+[1-9]\d*", re.I)),
]

SECRET_RE = re.compile(
    r"(AIza[0-9A-Za-z_\-]{20,})"
    r"|((?:api_?key|key|password|pwd|passwd|token|secret|access_key|secret_key)\s*[=:]\s*)([^\s;&'\"]+)",
    re.I,
)
USER_PATH_RE = re.compile(r"(?i)([A-Z]:\\Users\\)[^\\]+")


# ----------------------------------------------------------------------------- helpers
def mask(text: str) -> str:
    """Che API key/mật khẩu/tên user Windows trước khi đưa dòng log vào báo cáo."""
    text = SECRET_RE.sub(lambda m: "***" if m.group(1) else f"{m.group(2)}***", text)
    return USER_PATH_RE.sub(r"\1<user>", text)


def ts(value):
    if value is None or value == "":
        return pd.NaT
    try:
        return pd.to_datetime(value, utc=True, errors="coerce")
    except Exception:
        return pd.NaT


def load_json(path: Path, problems: list):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as exc:
        problems.append(f"Không đọc được {path.name}: {type(exc).__name__}")
        return None


def local_day_bounds(day: dt.date, tz: str):
    start = pd.Timestamp(day).tz_localize(tz)
    end = (pd.Timestamp(day) + pd.Timedelta(days=1)).tz_localize(tz)
    return start.tz_convert("UTC"), end.tz_convert("UTC")


def fmt_local(t, tz: str, fmt: str = "%Y-%m-%d %H:%M") -> str:
    return "—" if pd.isna(t) else t.tz_convert(tz).strftime(fmt)


def md_table(headers: list, rows: list) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def pct(n, d) -> str:
    return "n/a" if not d else f"{n / d:.1%}"


# ----------------------------------------------------------------------------- đọc dữ liệu
def read_cohorts(root: Path, region: str, problems: list) -> list:
    base = root / COHORT_ROOT / region
    out = []
    if not base.is_dir():
        return out
    for d in sorted(p for p in base.iterdir() if p.is_dir()):
        manifest = load_json(d / "manifest.json", problems) if (d / "manifest.json").exists() else None
        if not isinstance(manifest, dict):
            continue
        t0 = load_json(d / "t0.json", problems) if (d / "t0.json").exists() else None
        t24 = load_json(d / "t24.json", problems) if (d / "t24.json").exists() else None
        out.append({
            "batch_id": manifest.get("batch_id", d.name),
            "status": manifest.get("status"),
            "created": ts(manifest.get("created_at_utc")),
            "due": ts(manifest.get("due_at_utc")),
            "t0": (t0 or {}).get("records", []) if isinstance(t0, dict) else [],
            "t24": (t24 or {}).get("records", []) if isinstance(t24, dict) else [],
        })
    return out


def read_ids(path: Path, problems: list):
    if not path.exists():
        return None
    try:
        return pd.read_csv(path, usecols=lambda c: c in {"video_id", "region_code", "batch_id"},
                           dtype=str, encoding="utf-8-sig")
    except Exception as exc:  # noqa: BLE001 - báo lỗi đọc, không làm sập báo cáo
        problems.append(f"Không đọc được {path.name}: {type(exc).__name__}")
        return None


def read_chart_runs(root: Path, region: str, day: dt.date, problems: list) -> pd.DataFrame:
    """Chỉ đọc file chart có ngày UTC trong [day-1, day+1] để chạy nhanh khi dữ liệu nhiều ngày."""
    base = root / CHART_ROOT / region
    rows = []
    if base.is_dir():
        keep = {(day + dt.timedelta(days=k)).strftime("%Y%m%d") for k in (-1, 0, 1)}
        for p in sorted(base.glob("chart_*.json")):
            m = CHART_FILE_RE.match(p.name)
            if m and m.group(1) not in keep:
                continue
            c = load_json(p, problems)
            if not isinstance(c, dict):
                continue
            rows.append({
                "run_id": c.get("run_id"),
                "collected": ts(c.get("collected_at_utc")),
                "pages": c.get("pages_fetched"),
                "items": c.get("items_count"),
                "full": bool(c.get("fully_paginated")) and not c.get("next_page_available"),
                "default_chart": c.get("chart_name") == "mostPopular" and str(c.get("requested_category_id")) == "0",
            })
    return pd.DataFrame(rows, columns=["run_id", "collected", "pages", "items", "full", "default_chart"])


# ----------------------------------------------------------------------------- các mục báo cáo
def t0_integrity(records: list) -> dict:
    def title(r):
        return str(r.get("title") or "")
    return {
        "records": len(records),
        "bad_video_id": sum(1 for r in records if not VIDEO_ID_RE.match(str(r.get("video_id") or ""))),
        "empty_title": sum(1 for r in records if not title(r).strip()),
        "unicode_replacement": sum(1 for r in records if "\ufffd" in title(r)),
        "missing_published_at": sum(1 for r in records if pd.isna(ts(r.get("published_at")))),
    }


def cohort_section(cohorts: list, start_utc, end_utc, now, tol: float) -> dict:
    today = [c for c in cohorts if not pd.isna(c["created"]) and start_utc <= c["created"] < end_utc]
    t24_rows = []
    for c in cohorts:
        if not c["t24"]:
            continue
        done_times = [t for t in (ts(r.get("t24_collected_at")) for r in c["t24"]) if not pd.isna(t)]
        elapsed = pd.to_numeric(pd.Series([r.get("hours_elapsed") for r in c["t24"]]), errors="coerce").dropna()
        t24_rows.append({
            "batch_id": c["batch_id"],
            "n": len(c["t24"]),
            "done_at": max(done_times) if done_times else pd.NaT,
            "elapsed_min": float(elapsed.min()) if len(elapsed) else float("nan"),
            "elapsed_max": float(elapsed.max()) if len(elapsed) else float("nan"),
            "delayed": bool(len(elapsed) and elapsed.max() > 24 + tol),
            "unavailable": sum(1 for r in c["t24"] if r.get("t24_video_available") is False),
        })
    done_today = [x for x in t24_rows if not pd.isna(x["done_at"]) and start_utc <= x["done_at"] < end_utc]
    pending = [c for c in cohorts if not c["t24"] and c["status"] != "COMPLETED"]
    overdue = [c for c in pending if not pd.isna(c["due"]) and c["due"] <= now]
    return {
        "today_batches": today,
        "t0_records": [r for c in today for r in c["t0"]],
        "done_today": done_today,
        "delayed_today": [x for x in done_today if x["delayed"]],
        "overdue": overdue,
        "pending_not_due": len(pending) - len(overdue),
    }


def unique_section(root: Path, region: str, cohorts_by_region: dict, start_utc, today_ids: list, problems: list) -> dict:
    notes = []
    master = read_ids(root / MASTER, problems)
    registries = {r: read_ids(root / PROCESSED / f"youtube_cohort_registry_{r}.csv", problems) for r in REGIONS}
    master_has_region = master is not None and "region_code" in master
    if master is not None and not master_has_region:
        notes.append("master không có cột region_code: chỉ dùng cho global_unique, không tính vào từng vùng.")
    for r, reg in registries.items():
        if reg is None and r == region:
            notes.append(f"Chưa có data/processed/youtube_cohort_registry_{r}.csv (chưa đóng góp vào unique_region_total).")

    excluded = {c["batch_id"] for r in REGIONS for c in cohorts_by_region[r]
                if not pd.isna(c["created"]) and c["created"] >= start_utc}

    def ids(df, reg=None, drop=None):
        if df is None or "video_id" not in df:
            return set()
        d = df
        if reg is not None:
            if "region_code" not in d:
                return set()
            d = d[d["region_code"] == reg]
        if drop and "batch_id" in d:
            d = d[~d["batch_id"].isin(drop)]
        return set(d["video_id"].dropna().astype(str))

    def cohort_ids(r, only_before=False):
        return {str(x.get("video_id")) for c in cohorts_by_region[r]
                if not only_before or c["batch_id"] not in excluded
                for x in c["t0"] if x.get("video_id")}

    region_known = {}
    for r in REGIONS:
        region_known[r] = (ids(master, r) if master_has_region else set()) | ids(registries[r]) | cohort_ids(r)
    global_all = ids(master) | set().union(*(ids(registries[r]) for r in REGIONS)) | set().union(*(cohort_ids(r) for r in REGIONS))

    known_before = ids(master)
    for r in REGIONS:
        reg = registries[r]
        if reg is not None and "batch_id" not in reg:
            notes.append(f"registry {r} không có cột batch_id: bỏ qua khi tính trùng trong ngày (tránh báo trùng giả).")
        elif reg is not None:
            known_before |= ids(reg, drop=excluded)
        known_before |= cohort_ids(r, only_before=True)

    today_set = set(today_ids)
    others = set().union(*(region_known[r] for r in REGIONS if r != region))
    overlaps = []
    live = [r for r in REGIONS if region_known[r]]
    for i, a in enumerate(live):
        for b in live[i + 1:]:
            overlaps.append((f"{a} ∩ {b}", len(region_known[a] & region_known[b])))

    reg = registries[region]
    reg_dup = {}
    if reg is not None and "video_id" in reg:
        reg_dup["video_id trùng"] = int(reg.duplicated("video_id").sum())
        if "region_code" in reg:
            reg_dup["(video_id, region_code) trùng"] = int(reg.duplicated(["video_id", "region_code"]).sum())

    return {
        "notes": notes,
        "new_today": len(today_set - known_before),
        "dup_within_day": len(today_ids) - len(today_set),
        "dup_vs_known": len(today_set & known_before),
        "dup_cross_region": len(today_set & others),
        "region_total": len(region_known[region]),
        "region_parts": {
            "master": len(ids(master, region)) if master_has_region else 0,
            "registry": len(ids(registries[region])),
            "cohort_local": len(cohort_ids(region)),
        },
        "global_unique": len(global_all),
        "overlaps": overlaps,
        "reg_dup": reg_dup,
    }


def chart_section(runs: pd.DataFrame, start_utc, end_utc, now, tz: str) -> dict:
    window_end = min(end_utc, now)
    expected = max(0, min(25, int((window_end - start_utc) // pd.Timedelta(hours=1))))
    d = runs[runs["default_chart"]] if len(runs) else runs
    d = d[(d["collected"] >= start_utc) & (d["collected"] < window_end)] if len(d) else d
    actual, full = len(d), int(d["full"].sum()) if len(d) else 0
    bins = set()
    if len(d):
        f = d[d["full"]]
        bins = {int((t - start_utc) // pd.Timedelta(hours=1)) for t in f["collected"]}
        bins = {b for b in bins if 0 <= b < expected}
    missing = [b for b in range(expected) if b not in bins]
    gaps, run_start = [], None
    for i, b in enumerate(missing):
        run_start = b if run_start is None else run_start
        if i + 1 == len(missing) or missing[i + 1] != b + 1:
            s = fmt_local(start_utc + pd.Timedelta(hours=run_start), tz, "%H:%M")
            e = fmt_local(start_utc + pd.Timedelta(hours=b + 1), tz, "%H:%M")
            gaps.append(f"{s}–{e} ({b - run_start + 1} giờ)")
            run_start = None
    return {
        "expected": expected, "actual": actual, "full": full, "partial": actual - full,
        "bins_covered": len(bins),
        "coverage": (len(bins) / expected) if expected else float("nan"),
        "gaps": gaps,
        "table": d.sort_values("collected") if len(d) else d,
    }


def log_section(root: Path, region: str, start_utc, end_utc, tz: str) -> dict:
    per_log, undated_total, today_total, has_dated = [], 0, 0, False
    messages = Counter()
    by_type = Counter()
    for name in (f"{region}_cohort.log", f"{region}_chart.log", f"{region}_t24.log"):
        path = root / LOG_DIR / name
        if not path.exists():
            continue
        current = None
        dated = undated = 0
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.replace("\r", "")
            m = LOG_TS_RE.match(line)
            if m:
                has_dated = True
                try:
                    current = pd.Timestamp(f"{m.group(1)} {m.group(2)}").tz_localize(tz).tz_convert("UTC")
                except Exception:  # noqa: BLE001
                    current = None
            kind = next((k for k, rx in FAIL_PATTERNS if rx.search(line)), None)
            if kind is None:
                continue
            by_type[kind] += 1
            messages[mask(line.strip())[:160]] += 1
            if current is None:
                undated += 1
            elif start_utc <= current < end_utc:
                dated += 1
        per_log.append((name, dated, undated))
        today_total += dated
        undated_total += undated
    return {"per_log": per_log, "today": today_total, "undated": undated_total, "has_dated": has_dated,
            "by_type": by_type, "top": messages.most_common(5)}


def rq1_qa(root: Path, region: str, min_cov: float) -> tuple[list, list]:
    lines, flags = [], []
    new_path = root / PROCESSED / f"rq1_youtube_cohort_{region}.csv"
    legacy_path = root / PROCESSED / "youtube_rq1_dataset.csv"
    if new_path.exists():
        d = pd.read_csv(new_path, encoding="utf-8-sig", low_memory=False)
        lines.append(f"Nguồn: `{new_path.name}` (build_rq1_dataset.py), {len(d):,} dòng, {d['video_id'].nunique():,} video_id.")
        for col in ("chart_label_status", "chart_coverage_status", "rq1_analysis_ready", "t24_ready"):
            if col in d:
                lines.append(f"- {col}: " + ", ".join(f"{k}={v}" for k, v in d[col].value_counts(dropna=False).items()))
        if "rq1_analysis_ready" in d and not d["rq1_analysis_ready"].astype(str).str.lower().eq("true").any():
            flags.append("RQ1: chưa có dòng nào rq1_analysis_ready = True (mẫu chính còn rỗng).")
    elif legacy_path.exists():
        d = pd.read_csv(legacy_path, encoding="utf-8-sig", low_memory=False)
        r = d[d["region_code"] == region] if "region_code" in d else d
        lines.append(f"Chưa có `{new_path.name}`. Đang kiểm `{legacy_path.name}` (file cũ từ youtube_dataset_2000_clean): "
                     f"{len(r):,} dòng {region}.")
        if "chart_coverage_ratio" in r and r["chart_coverage_ratio"].nunique(dropna=True) <= 1 and len(r):
            v = r["chart_coverage_ratio"].dropna().unique().tolist()
            n_neg = int((r.get("chart_status") == "NOT_OBSERVED_WITH_COVERAGE").sum()) if "chart_status" in r else 0
            flags.append(f"RQ1: chart_coverage_ratio chỉ có một giá trị {v} → nhiều khả năng là giá trị mặc định, "
                         f"không phải độ phủ đo thực; {n_neg:,} dòng NOT_OBSERVED_WITH_COVERAGE chưa đáng tin (cần UNKNOWN).")
        need = ["first_seen_at", "T0_at", "T24_at", "elapsed_hours", "valid_for_rq1"]
        miss = [c for c in need if c not in d.columns]
        if miss:
            flags.append("RQ1: file thiếu cột theo Data Dictionary: " + ", ".join(miss) + ".")
        if {"published_at", "collected_at"} <= set(r.columns) and len(r):
            age = (pd.to_datetime(r["collected_at"], utc=True, errors="coerce")
                   - pd.to_datetime(r["published_at"], utc=True, errors="coerce")).dt.total_seconds() / 86400
            old = int((age > 7).sum())
            lines.append(f"- Video đã đăng > 7 ngày tại thời điểm thu: {old:,}/{len(r):,} ({pct(old, len(r))}) → không thuộc cohort 'mới'.")
            if old:
                flags.append(f"RQ1: {old:,} video JP đã đăng > 7 ngày trước lúc thu, không hợp cohort mới.")
        if {"upload_period", "chart_status"} <= set(r.columns) and len(r):
            ct = pd.crosstab(r["upload_period"], r["chart_status"])
            rows = [[idx] + [int(ct.loc[idx, c]) for c in ct.columns] for idx in ct.index]
            lines.append("")
            lines.append(md_table(["upload_period"] + list(ct.columns), rows))
            lines.append("(Chỉ để kiểm tra mô tả; chưa dùng làm kết quả chính khi còn cảnh báo ở trên.)")
    else:
        lines.append("Chưa có file RQ1 dataset nào để kiểm.")
    return lines, flags


# ----------------------------------------------------------------------------- render
def build_report(a, now) -> tuple[str, dict, list]:
    root = Path(a.root).resolve()
    tz = LOCAL_TZ[a.region]
    day = dt.date.fromisoformat(a.date) if a.date else now.tz_convert(tz).date()
    start_utc, end_utc = local_day_bounds(day, tz)
    problems: list = []

    cohorts_by_region = {r: read_cohorts(root, r, problems) for r in REGIONS}
    co = cohort_section(cohorts_by_region[a.region], start_utc, end_utc, now, a.delay_tolerance_hours)
    today_ids = [str(r.get("video_id")) for r in co["t0_records"] if r.get("video_id")]
    un = unique_section(root, a.region, cohorts_by_region, start_utc, today_ids, problems)
    ch = chart_section(read_chart_runs(root, a.region, day, problems), start_utc, end_utc, now, tz)
    lg = log_section(root, a.region, start_utc, end_utc, tz)
    integ = t0_integrity(co["t0_records"])
    qa_lines, qa_flags = rq1_qa(root, a.region, a.min_coverage)

    flags = list(qa_flags)
    if not co["today_batches"]:
        flags.append("Không có batch cohort nào được tạo trong ngày (chạy PLAN không tạo batch).")
    if co["overdue"]:
        flags.append(f"{len(co['overdue'])} batch quá hạn T+24h chưa có t24.json: " +
                     ", ".join(c["batch_id"] for c in co["overdue"]) + ".")
    if co["delayed_today"]:
        flags.append(f"{len(co['delayed_today'])} batch T+24h chạy trễ (> 24h + {a.delay_tolerance_hours}h); giữ thời gian thật, gắn DELAYED.")
    if ch["expected"] and not (ch["coverage"] >= a.min_coverage):
        flags.append(f"Độ phủ chart {ch['coverage']:.0%} < {a.min_coverage:.0%}: video chưa lên chart trong các giờ hở phải là UNKNOWN, không phải NON_TRENDING.")
    if ch["partial"]:
        flags.append(f"{ch['partial']} lượt chart không phân trang đầy đủ (không tính vào độ phủ).")
    failed = lg["today"] if lg["has_dated"] else None
    if lg["today"]:
        flags.append(f"{lg['today']} lỗi gọi/chạy trong ngày theo log có timestamp.")
    elif lg["undated"]:
        flags.append(f"{lg['undated']} lỗi tích lũy trong log chưa có timestamp (không gán được theo ngày).")
    for k, v in integ.items():
        if k != "records" and v:
            flags.append(f"T0 hôm nay: {v} bản ghi lỗi '{k}'.")
    flags += [f"Đọc dữ liệu: {p}" for p in problems]

    L = []
    L.append(f"# Báo cáo cuối ngày — {a.region} — {day.isoformat()} ({tz})")
    L.append(f"Tạo lúc {now.strftime('%Y-%m-%d %H:%M')} UTC · chỉ đọc file local, không gọi API/SQL/MinIO.\n")
    L.append("## 1. KPI")
    cov_txt = "n/a" if not ch["expected"] else f"{ch['coverage']:.0%} ({ch['bins_covered']}/{ch['expected']} giờ)"
    L.append(md_table(["Chỉ số", "Giá trị"], [
        ["unique_new_today", un["new_today"]],
        ["unique_region_total (máy này)", un["region_total"]],
        ["global_unique (máy này)", un["global_unique"]],
        ["duplicates: trong ngày / đã biết / chéo vùng", f"{un['dup_within_day']} / {un['dup_vs_known']} / {un['dup_cross_region']}"],
        ["t24_done hôm nay / delayed", f"{len(co['done_today'])} / {len(co['delayed_today'])}"],
        ["t24 quá hạn chưa chạy (tính tới giờ tạo báo cáo)", len(co["overdue"])],
        ["chart_calls thực nhận / kỳ vọng", f"{ch['actual']} / {ch['expected']}"],
        ["chart_coverage", cov_txt],
        ["failed_calls hôm nay (log có timestamp)", failed if failed is not None else f"n/a (tích lũy chưa gán ngày: {lg['undated']})"],
    ]))
    L.append("\n## 2. Cảnh báo")
    L += [f"- {f}" for f in flags] or ["- Không có cảnh báo."]

    L.append("\n## 3. Unique và trùng lặp")
    L.append(f"- unique_region_total = {un['region_total']} (master {un['region_parts']['master']}, "
             f"registry {un['region_parts']['registry']}, cohort local {un['region_parts']['cohort_local']}; các nguồn có thể chồng nhau, số trên đã khử trùng).")
    if un["overlaps"]:
        L.append("- Trùng giữa các vùng (theo dữ liệu local): " + "; ".join(f"{k} = {v}" for k, v in un["overlaps"]) + ".")
    if un["reg_dup"]:
        L.append("- Registry: " + "; ".join(f"{k} = {v}" for k, v in un["reg_dup"].items()) + ".")
    L += [f"- Lưu ý: {n}" for n in un["notes"]]

    L.append("\n## 4. T0 và T+24h")
    L.append(f"- Batch tạo trong ngày: {len(co['today_batches'])}; bản ghi T0: {integ['records']}; "
             f"lỗi video_id {integ['bad_video_id']}, title rỗng {integ['empty_title']}, "
             f"ký tự lỗi Unicode {integ['unicode_replacement']}, thiếu published_at {integ['missing_published_at']}.")
    if co["done_today"]:
        L.append(md_table(["batch_id", "videos", "T24 xong lúc", "elapsed_h (min–max)", "nhãn", "không còn khả dụng"],
                          [[x["batch_id"], x["n"], fmt_local(x["done_at"], tz),
                            f"{x['elapsed_min']:.2f}–{x['elapsed_max']:.2f}", "DELAYED" if x["delayed"] else "OK", x["unavailable"]]
                           for x in co["done_today"]]))
    else:
        L.append("- Chưa có batch nào hoàn tất T+24h trong ngày.")
    L.append(f"- Batch đang chờ T+24h, chưa tới hạn: {co['pending_not_due']}.")

    L.append("\n## 5. Chart monitor (mostPopular, category 0)")
    L.append(f"- Lượt chạy: {ch['actual']} (đủ trang {ch['full']}, thiếu trang {ch['partial']}); giờ có ≥ 1 lượt đủ trang: {ch['bins_covered']}/{ch['expected']}.")
    L.append("- Các khoảng hở (máy tắt/lỗi): " + ("; ".join(ch["gaps"]) if ch["gaps"] else "không có") + ".")
    if len(ch["table"]) and len(ch["table"]) <= 30:
        L.append(md_table(["giờ địa phương", "pages", "items", "trạng thái"],
                          [[fmt_local(r.collected, tz, "%H:%M:%S"), r.pages, r.items, "OK" if r.full else "THIẾU TRANG"]
                           for r in ch["table"].itertuples()]))
    L.append("- Log timestamp, region, status của từng lượt nằm trong JSON raw; báo cáo này không sửa timestamp.")

    L.append("\n## 6. Lỗi trong log")
    if lg["per_log"]:
        L.append(md_table(["log", "lỗi hôm nay (có timestamp)", "lỗi chưa có timestamp"], [[n, d, u] for n, d, u in lg["per_log"]]))
        if lg["by_type"]:
            L.append("- Theo loại: " + ", ".join(f"{k}={v}" for k, v in lg["by_type"].most_common()) + ".")
        L += [f"  - `{m}` ×{c}" for m, c in lg["top"]]
    else:
        L.append(f"- Không tìm thấy logs/{a.region}_*.log.")

    L.append("\n## 7. Kiểm tra dataset RQ1")
    L += qa_lines

    kpi = {
        "report_date": day.isoformat(), "region": a.region,
        "generated_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "unique_new_today": un["new_today"], "unique_region_total": un["region_total"], "global_unique": un["global_unique"],
        "dup_within_day": un["dup_within_day"], "dup_vs_known": un["dup_vs_known"], "dup_cross_region": un["dup_cross_region"],
        "t24_done_today": len(co["done_today"]), "t24_delayed_today": len(co["delayed_today"]),
        "t24_overdue_pending": len(co["overdue"]),
        "chart_calls_expected": ch["expected"], "chart_calls_actual": ch["actual"], "chart_full_runs": ch["full"],
        "chart_coverage": "" if not ch["expected"] else round(ch["coverage"], 4),
        "failed_calls_today": "" if failed is None else failed, "failed_calls_undated": lg["undated"],
    }
    return "\n".join(L) + "\n", kpi, flags


def write_outputs(root: Path, region: str, day: str, report: str, kpi: dict) -> list:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    md = out / f"{region}_{day.replace('-', '')}_report.md"
    md.write_text(report, encoding="utf-8")
    csv = out / f"daily_kpi_{region}.csv"
    new = pd.DataFrame([kpi])
    if csv.exists():
        old = pd.read_csv(csv, encoding="utf-8-sig", dtype=str)
        old = old[old["report_date"] != day]
        new = pd.concat([old, new.astype(str)], ignore_index=True)
    new.to_csv(csv, index=False, encoding="utf-8-sig")
    return [md, csv]


def main() -> int:
    p = argparse.ArgumentParser(description="Báo cáo cuối ngày (read-only) cho cohort + chart monitor")
    p.add_argument("--region", required=True, choices=REGIONS)
    p.add_argument("--date", help="Ngày địa phương YYYY-MM-DD (mặc định: hôm nay theo múi giờ vùng)")
    p.add_argument("--root", default=".", help="Thư mục gốc dự án (mặc định: thư mục hiện tại)")
    p.add_argument("--now", help="Ghi đè thời điểm 'bây giờ' (ISO, UTC) để chạy lại/kiểm thử")
    p.add_argument("--delay-tolerance-hours", type=float, default=1.0, help="Ngưỡng DELAYED tạm thời: elapsed > 24 + giá trị này")
    p.add_argument("--min-coverage", type=float, default=0.70, help="Ngưỡng độ phủ chart tạm thời để cảnh báo")
    p.add_argument("--no-write", action="store_true", help="Chỉ in ra màn hình, không ghi file")
    p.add_argument("--strict", action="store_true", help="Thoát mã 1 nếu có cảnh báo (dùng khi gắn vào Task Scheduler)")
    a = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # tránh lỗi hiển thị tiếng Việt/Nhật trên PowerShell
    now = pd.to_datetime(a.now, utc=True) if a.now else pd.Timestamp.now(tz="UTC")
    report, kpi, flags = build_report(a, now)
    print(report)
    if not a.no_write:
        for path in write_outputs(Path(a.root).resolve(), a.region, kpi["report_date"], report, kpi):
            print("Đã ghi:", path)
    return 1 if (a.strict and flags) else 0


if __name__ == "__main__":
    sys.exit(main())
