"""Doi chieu raw JSON <-> registry CSV <-> SQL (<-> MinIO) cho mot thi truong (NG-03).

Chi DOC. Khong goi YouTube API, khong ghi SQL/MinIO.
  uv run python -m src.processing.verify_us_consistency --region US --sample 10
Ket qua: reports/assets/sql_us/consistency_report.json va exit code 1 neu co lech.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import pandas as pd


def compare_id_sets(raw: set, registry: set, sql: set) -> dict:
    return {"raw": len(raw), "registry": len(registry), "sql": len(sql),
            "raw_not_in_sql": sorted(raw - sql)[:20], "sql_not_in_raw": sorted(sql - raw)[:20],
            "registry_not_in_sql": sorted(registry - sql)[:20], "sql_not_in_registry": sorted(sql - registry)[:20],
            "consistent": raw == sql == registry}


def read_raw(cohort_root: Path, region: str, phase: str) -> dict:
    """{video_id: view_count} tu moi t0.json/t24.json cua region."""
    out, fname = {}, ("t0.json" if phase == "T0" else "t24.json")
    key = "view_count" if phase == "T0" else "t24_view_count"
    for p in sorted((cohort_root / region).glob(f"*/{fname}")):
        for r in json.loads(p.read_text(encoding="utf-8-sig")).get("records", []):
            out[str(r["video_id"])] = r.get(key)
    return out


def read_sql(region: str) -> tuple[pd.DataFrame, dict]:
    from src.utils.db_connection import get_connection
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""SELECT video_id, phase, view_count, minio_object_path
                       FROM dbo.youtube_cohort_observations WHERE region_code = ?""", region)
        df = pd.DataFrame.from_records(cur.fetchall(), columns=["video_id", "phase", "view_count", "minio_object_path"])
        cur.execute("""SELECT COUNT(*) FROM (SELECT batch_id, video_id, phase FROM dbo.youtube_cohort_observations
                       WHERE region_code = ? GROUP BY batch_id, video_id, phase HAVING COUNT(*) > 1) d""", region)
        dups = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM dbo.youtube_chart_runs WHERE region_code = ?", region)
        runs = cur.fetchone()[0]
        return df, {"duplicate_batch_video_phase": dups, "chart_runs": runs}
    finally:
        conn.close()


def check_minio(paths: list) -> dict:
    from src.ingestion.upload_raw_to_minio import get_minio_client
    import os
    client, bucket = get_minio_client(), os.getenv("MINIO_BUCKET")
    missing = []
    for p in paths:
        try:
            client.stat_object(bucket, p)
        except Exception:
            missing.append(p)
    return {"checked": len(paths), "missing": missing[:20], "missing_count": len(missing)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="US", choices=("VN", "US", "JP"))
    ap.add_argument("--cohort-root", type=Path, default=Path("data/raw/rolling_cohorts"))
    ap.add_argument("--registry-root", type=Path, default=Path("data/processed"))
    ap.add_argument("--sample", type=int, default=10)
    ap.add_argument("--skip-minio", action="store_true")
    ap.add_argument("--output", type=Path, default=Path("reports/assets/sql_us/consistency_report.json"))
    a = ap.parse_args()

    reg = pd.read_csv(a.registry_root / f"youtube_cohort_registry_{a.region}.csv",
                      dtype={"video_id": "string", "region_code": "string"})
    reg = reg[reg["region_code"] == a.region]
    sql_df, sql_stats = read_sql(a.region)
    report = {"region": a.region, "sql_stats": sql_stats, "phases": {}}
    ok = sql_stats["duplicate_batch_video_phase"] == 0
    for phase in ("T0", "T24"):
        raw = read_raw(a.cohort_root, a.region, phase)
        sql_phase = sql_df[sql_df["phase"] == phase]
        reg_ids = set(reg["video_id"].dropna().astype(str)) if phase == "T0" else \
            set(reg.loc[reg["t24_collected_at"].notna(), "video_id"].astype(str))
        cmp_ = compare_id_sets(set(raw), reg_ids, set(sql_phase["video_id"].astype(str)))
        # doi chieu gia tri view_count tren mau ngau nhien
        ids = sorted(set(raw) & set(sql_phase["video_id"].astype(str)))
        random.seed(42)
        mism = []
        sql_map = dict(zip(sql_phase["video_id"].astype(str), sql_phase["view_count"]))
        for vid in random.sample(ids, min(a.sample, len(ids))):
            if raw[vid] is not None and sql_map.get(vid) is not None and int(raw[vid]) != int(sql_map[vid]):
                mism.append({"video_id": vid, "raw": raw[vid], "sql": int(sql_map[vid])})
        cmp_["sampled"] = min(a.sample, len(ids)); cmp_["view_count_mismatches"] = mism
        if not a.skip_minio:
            cmp_["minio"] = check_minio(sorted(set(sql_phase["minio_object_path"].dropna()))[:200])
            ok &= cmp_["minio"]["missing_count"] == 0
        report["phases"][phase] = cmp_
        ok &= cmp_["consistent"] and not mism
    report["all_consistent"] = bool(ok)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
