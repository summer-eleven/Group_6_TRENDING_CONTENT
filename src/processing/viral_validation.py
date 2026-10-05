"""
viral_validation.py - N2/N3/N5: quan ly cycle kiem chung viral candidates.

  # 1) Sau khi chay merge_snapshots + calculate_growth:
  uv run python -m src.processing.viral_validation init-run --region VN --top 20
  #    -> ghi run + candidates vao SQL Server
  #    -> tao evidence/validation/<run_dir>/evidence_input.csv (moi candidate x nguon)

  # 2) Thu bang chung THU CONG (vidIQ / Google Trends / Social Blade), dien CSV,
  #    luu screenshot theo quy uoc ten, roi:
  uv run python -m src.processing.viral_validation load-evidence --file evidence/validation/<run_dir>/evidence_input.csv

Quy uoc: moi thoi gian trong CSV phai co offset (vd 2026-10-04T14:05:00+07:00). Luu DB dang UTC.
Khong scrape vidIQ/Social Blade (ToS) - thu thap thu cong.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

VIRAL_CSV = Path("data/processed/youtube_viral_candidates_vn.csv")
EVIDENCE_ROOT = Path("evidence/validation")

# (source, granularity, scope) - gia tri mac dinh, nguoi thu co the sua trong CSV
SOURCES = [
    ("vidIQ", "hourly", "video"),
    ("Google Trends", "hourly", "topic"),
    ("Social Blade", "daily", "channel"),
]
RESULTS = {"supports", "contradicts", "inconclusive", "not_available"}
GRANULARITY = {"hourly", "daily", "weekly"}
SCOPES = {"video", "channel", "topic"}
VALID_SOURCES = {"vidIQ", "Google Trends", "Social Blade", "Other"}
TZ_RE = re.compile(r"(Z|[+-]\d{2}:?\d{2})$")
TEMPLATE_COLUMNS = [
    "run_id", "video_id", "video_url", "title", "external_source", "source_granularity",
    "source_scope", "external_metric", "external_value", "evidence_result",
    "evidence_collected_at", "evidence_region", "evidence_url", "evidence_path",
    "notes", "collected_by",
]


# ----------------------------- pure functions ------------------------------
def build_candidates(df: pd.DataFrame, top: int) -> pd.DataFrame:
    """Lay top-N theo viral_score, them rank_in_run va youtube_charted."""
    out = df.sort_values("viral_score", ascending=False).head(top).copy()
    out["rank_in_run"] = range(1, len(out) + 1)
    out["youtube_charted"] = (pd.to_numeric(out["is_trending"], errors="coerce").fillna(0) == 1).astype(int)
    rank = pd.to_numeric(out["trending_rank"], errors="coerce")
    out["youtube_chart_rank"] = rank.where(out["youtube_charted"] == 1)
    return out


def build_template(cands: pd.DataFrame, run_id: int, region: str) -> pd.DataFrame:
    rows = []
    for _, c in cands.iterrows():
        for source, gran, scope in SOURCES:
            rows.append({
                "run_id": run_id, "video_id": c["video_id"],
                "video_url": f"https://www.youtube.com/watch?v={c['video_id']}",
                "title": c.get("title", ""), "external_source": source,
                "source_granularity": gran, "source_scope": scope,
                "external_metric": "", "external_value": "", "evidence_result": "",
                "evidence_collected_at": "", "evidence_region": region,
                "evidence_url": "", "evidence_path": "", "notes": "", "collected_by": "",
            })
    return pd.DataFrame(rows, columns=TEMPLATE_COLUMNS)


def validate_evidence_row(row: dict) -> tuple[dict | None, str | None]:
    """Tra ve (record_sach, None) hoac (None, ly_do_loi). Dong chua dien -> ('SKIP')."""
    g = lambda k: str(row.get(k) or "").strip()
    result = g("evidence_result")
    if not result:
        return None, "SKIP"
    if result not in RESULTS:
        return None, f"evidence_result khong hop le: {result}"
    if g("external_source") not in VALID_SOURCES:
        return None, f"external_source khong hop le: {g('external_source')}"
    if g("source_granularity") not in GRANULARITY:
        return None, "source_granularity khong hop le"
    if g("source_scope") not in SCOPES:
        return None, "source_scope khong hop le"
    ts = g("evidence_collected_at")
    if not ts or not TZ_RE.search(ts):
        return None, "evidence_collected_at thieu hoac khong co offset timezone"
    parsed = pd.to_datetime(ts, utc=True, errors="coerce")
    if pd.isna(parsed):
        return None, "evidence_collected_at khong parse duoc"
    if result != "not_available" and not g("evidence_url"):
        return None, "thieu evidence_url"
    if result != "not_available" and not (g("evidence_path") or g("notes")):
        return None, "can evidence_path (screenshot) hoac notes"
    if result in {"contradicts", "inconclusive", "not_available"} and not g("notes"):
        return None, f"{result} bat buoc co notes giai thich"
    rec = {
        "run_id": int(g("run_id")), "video_id": g("video_id"),
        "external_source": g("external_source"), "source_granularity": g("source_granularity"),
        "source_scope": g("source_scope"), "external_metric": g("external_metric") or "n/a",
        "external_value": g("external_value") or None, "evidence_result": result,
        "evidence_collected_at": parsed.to_pydatetime().replace(tzinfo=None),
        "evidence_region": g("evidence_region") or None, "evidence_url": g("evidence_url") or None,
        "evidence_path": g("evidence_path") or None, "notes": g("notes") or None,
        "collected_by": g("collected_by") or None,
    }
    return rec, None


# ------------------------------- DB commands -------------------------------
def init_run(args) -> None:
    from src.utils.db_connection import get_connection

    df = pd.read_csv(VIRAL_CSV)
    df["collected_at"] = pd.to_datetime(df["collected_at"], utc=True)
    df = df[df["region_code"].str.upper() == args.region.upper()]
    observed = df["collected_at"].max()
    cands = build_candidates(df[df["collected_at"] == observed], args.top)
    observed_naive = observed.to_pydatetime().replace(tzinfo=None)
    rule = f"top {args.top} by viral_score, signal_count>=3"

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT run_id FROM dbo.viral_validation_runs WHERE region_code=? AND ranking_observed_at=?",
                    args.region.upper(), observed_naive)
        row = cur.fetchone()
        if row:
            run_id = row[0]
            print(f"Run da ton tai: run_id={run_id} (khong tao lai)")
        else:
            cur.execute("INSERT INTO dbo.viral_validation_runs (region_code, ranking_observed_at, candidate_rule, created_by) "
                        "OUTPUT INSERTED.run_id VALUES (?,?,?,?)",
                        args.region.upper(), observed_naive, rule, args.by)
            run_id = cur.fetchone()[0]
        for _, c in cands.iterrows():
            chart_rank = None if pd.isna(c["youtube_chart_rank"]) else int(c["youtube_chart_rank"])
            cur.execute(
                "IF NOT EXISTS (SELECT 1 FROM dbo.viral_validation_candidates WHERE run_id=? AND video_id=?) "
                "INSERT INTO dbo.viral_validation_candidates "
                "(run_id, video_id, rank_in_run, viral_score, signal_count, youtube_charted, youtube_chart_rank) "
                "VALUES (?,?,?,?,?,?,?)",
                run_id, c["video_id"], run_id, c["video_id"], int(c["rank_in_run"]),
                float(c["viral_score"]), int(c["signal_count"]), int(c["youtube_charted"]), chart_rank)
        conn.commit()
    finally:
        cur.close()
        conn.close()

    run_dir = EVIDENCE_ROOT / f"{observed.strftime('%Y%m%dT%H%MZ')}_{args.region.upper()}_run{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    out = run_dir / "evidence_input.csv"
    build_template(cands, run_id, args.region.upper()).to_csv(out, index=False, encoding="utf-8-sig")
    print(f"run_id={run_id} | ranking_observed_at(UTC)={observed_naive} | candidates={len(cands)}")
    print(f"Template: {out}")
    print("Screenshot dat tai: <run_dir>/<video_id>/<nguon>_<YYYYMMDDTHHMMSSZ>.png")


def load_evidence(args) -> None:
    import pyodbc
    from src.utils.db_connection import get_connection

    df = pd.read_csv(args.file, dtype=str, keep_default_na=False)
    conn = get_connection()
    cur = conn.cursor()
    ok = dup = skipped = bad = 0
    sql = ("INSERT INTO dbo.viral_validation_evidence (run_id, video_id, external_source, source_granularity, "
           "source_scope, external_metric, external_value, evidence_result, evidence_collected_at, evidence_region, "
           "evidence_url, evidence_path, notes, collected_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)")
    try:
        for i, row in df.iterrows():
            rec, err = validate_evidence_row(row.to_dict())
            if err == "SKIP":
                skipped += 1
                continue
            if err:
                bad += 1
                print(f"[dong {i + 2}] BO QUA - {err}")
                continue
            if rec["evidence_path"] and not Path(rec["evidence_path"]).exists():
                print(f"[dong {i + 2}] CANH BAO - khong thay file: {rec['evidence_path']}")
            try:
                cur.execute(sql, *rec.values())
                conn.commit()
                ok += 1
            except pyodbc.IntegrityError as exc:
                conn.rollback()
                msg = str(exc)
                if "uq_vv_evidence" in msg:
                    dup += 1
                else:
                    bad += 1
                    print(f"[dong {i + 2}] DB tu choi: {msg[:160]}")
    finally:
        cur.close()
        conn.close()
    print(f"Inserted={ok} | duplicate={dup} | invalid={bad} | chua dien (skip)={skipped}")


def main() -> None:
    p = argparse.ArgumentParser(description="Viral validation cycle helper")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("init-run")
    a.add_argument("--region", default="VN")
    a.add_argument("--top", type=int, default=20)
    a.add_argument("--by", default=None, help="nguoi tao run")
    a.set_defaults(func=init_run)
    b = sub.add_parser("load-evidence")
    b.add_argument("--file", required=True)
    b.set_defaults(func=load_evidence)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()