"""Mo rong nguon seed channel cho US (NG-02) co kiem soat quota va provenance.

Nguon seed bo sung (deu co nguon goc ro rang):
  1. chart_sql      : channel_id trong dbo.youtube_chart_entries (chart US da luu).
  2. chart_category : videos.list chart=mostPopular + videoCategoryId (1 unit/request),
                      MOI category mot lan. KHONG dung search.list (100 unit/request).

Che do mac dinh la PLAN (khong goi API/SQL, khong ghi file). Chi --apply moi chay that.

  uv run python -m src.ingestion.us_seed_sources --region US
  uv run python -m src.ingestion.us_seed_sources --region US --apply --max-requests 30

File ket qua: data/raw/seed_channels/<REGION>/seed_channels_<REGION>_<stamp>.json
Dung voi run_daily_cohort qua --extra-seed-file (xem docs/us_pipeline_validation.md, muc Patch).
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_CATEGORIES = ["1", "2", "10", "15", "17", "19", "20", "22", "23", "24",
                      "25", "26", "27", "28"]
SEED_ROOT = Path("data/raw/seed_channels")


def is_valid_channel_id(value) -> bool:
    v = str(value or "").strip()
    return v.startswith("UC") and len(v) == 24


def merge_seeds(base_channels: list[str], extra_seeds: list[dict]) -> list[str]:
    """Gop seed moi vao danh sach co san: giu thu tu, khu trung, bo ID sai dinh dang.

    Seed moi dat SAU base de khong doi hanh vi xoay vong hien tai cua run_daily_cohort.
    """
    seen, out = set(), []
    for cid in list(base_channels) + [s.get("channel_id") for s in extra_seeds]:
        cid = str(cid or "").strip()
        if is_valid_channel_id(cid) and cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def load_seed_file(path) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    seeds = payload.get("seeds")
    if not isinstance(seeds, list):
        raise ValueError("Seed file must contain a 'seeds' list")
    return seeds


def dedupe_seed_rows(rows: list[dict], known_channels: set[str]) -> list[dict]:
    """Moi channel 1 lan; giu nguon dau tien; bo channel da co trong master."""
    out, seen = [], set(known_channels)
    for row in rows:
        cid = str(row.get("channel_id") or "").strip()
        if is_valid_channel_id(cid) and cid not in seen:
            seen.add(cid)
            out.append(row)
    return out


def seeds_from_chart_sql(region: str) -> list[dict]:
    from src.utils.db_connection import get_connection
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT e.channel_id
            FROM dbo.youtube_chart_entries e
            JOIN dbo.youtube_chart_runs r ON r.run_id = e.run_id
            WHERE r.region_code = ? AND r.chart_name = 'mostPopular' AND e.channel_id IS NOT NULL
        """, region)
        stamp = datetime.now(timezone.utc).isoformat()
        return [{"channel_id": r[0], "discovery_source": "chart_sql",
                 "discovery_query": f"youtube_chart_entries:{region}",
                 "first_seen_at": stamp, "seed_region": region} for r in cur.fetchall()]
    finally:
        conn.close()


def seeds_from_category_charts(region: str, categories: list[str], client) -> tuple[list[dict], dict]:
    """1 request / category (videos.list). `client` la YouTubeClient cua discover_playlist_videos."""
    rows, stats = [], {"requests": 0, "category_errors": {}}
    for cat in categories:
        if client.request_count >= client.max_requests:
            stats["stopped_by_budget"] = True
            break
        try:
            data = client.get("videos", part="snippet", chart="mostPopular",
                              regionCode=region, videoCategoryId=cat, maxResults=50)
        except RuntimeError as exc:
            stats["category_errors"][cat] = str(exc)[:120]
            if "budget" in str(exc).lower():
                stats["stopped_by_budget"] = True
                break
            continue
        stamp = datetime.now(timezone.utc).isoformat()
        for item in data.get("items", []):
            rows.append({"channel_id": item.get("snippet", {}).get("channelId"),
                         "discovery_source": "chart_category",
                         "discovery_query": f"mostPopular:{region}:cat={cat}",
                         "category_id": cat, "first_seen_at": stamp, "seed_region": region})
    stats["requests"] = client.request_count
    return rows, stats


def main():
    ap = argparse.ArgumentParser(description="Build extra US seed channel file (PLAN by default)")
    ap.add_argument("--region", default="US", choices=("VN", "US", "JP"))
    ap.add_argument("--categories", nargs="*", default=DEFAULT_CATEGORIES)
    ap.add_argument("--max-requests", type=int, default=20)
    ap.add_argument("--master-path", type=Path, default=Path("data/processed/youtube_dataset_2000_clean.csv"))
    ap.add_argument("--skip-sql", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if a.max_requests < 1:
        ap.error("--max-requests must be positive")

    planned = min(a.max_requests, len(a.categories))
    print("MODE:", "APPLY" if a.apply else "PLAN (no API/SQL/file writes)")
    print(f"Region={a.region} | categories={len(a.categories)} | expected API requests<={planned} (~{planned} quota units)")
    if not a.apply:
        print("PLAN COMPLETE. Add --apply to collect seeds.")
        return

    from dotenv import load_dotenv
    import pandas as pd
    from src.ingestion import discover_playlist_videos as discovery
    load_dotenv()
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        raise SystemExit("YOUTUBE_API_KEY missing in .env")

    master = pd.read_csv(a.master_path, dtype={"channel_id": "string", "region_code": "string"})
    known = set(master.loc[master["region_code"].eq(a.region), "channel_id"].dropna().astype(str))
    rows = [] if a.skip_sql else seeds_from_chart_sql(a.region)
    client = discovery.YouTubeClient(key, a.max_requests)
    try:
        cat_rows, stats = seeds_from_category_charts(a.region, a.categories, client)
    finally:
        client.session.close()
    rows += cat_rows
    seeds = dedupe_seed_rows(rows, known)

    out_dir = SEED_ROOT / a.region
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"seed_channels_{a.region}_{stamp}.json"
    out.write_text(json.dumps({"region_seed": a.region,
                               "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                               "api_stats": stats, "known_master_channels": len(known),
                               "raw_rows": len(rows), "new_unique_channels": len(seeds),
                               "seeds": seeds}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Raw seed rows: {len(rows)} | new unique channels vs master: {len(seeds)} | API stats: {stats}")
    print("Saved:", out)


if __name__ == "__main__":
    main()
