"""Dong goi ban giao US cho Ha (NG-06): registry + data-quality summary + checksum. KHONG push raw lon.

  uv run python -m src.processing.export_us_handover --region US
Ket qua: reports/assets/handover_<REGION>/ {registry.csv, quality_summary.json, manifest_list.csv, SHA256SUMS.txt}
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def quality_summary(reg: pd.DataFrame) -> dict:
    n = len(reg)
    miss = {c: int(reg[c].isna().sum()) for c in ("title", "channel_id", "category_id", "published_at",
                                                  "t0_view_count") if c in reg.columns}
    return {"rows": n, "unique_video_id": int(reg["video_id"].nunique()),
            "duplicate_video_id": int(reg["video_id"].duplicated().sum()), "missing_by_column": miss,
            "negative_t0_views": int((pd.to_numeric(reg.get("t0_view_count"), errors="coerce") < 0).sum()),
            "with_t24": int(reg["t24_collected_at"].notna().sum()) if "t24_collected_at" in reg.columns else 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="US", choices=("VN", "US", "JP"))
    ap.add_argument("--registry-root", type=Path, default=Path("data/processed"))
    ap.add_argument("--cohort-root", type=Path, default=Path("data/raw/rolling_cohorts"))
    a = ap.parse_args()
    out = Path(f"reports/assets/handover_{a.region}")
    out.mkdir(parents=True, exist_ok=True)
    reg = pd.read_csv(a.registry_root / f"youtube_cohort_registry_{a.region}.csv", dtype={"video_id": "string"})
    reg.to_csv(out / "registry.csv", index=False, encoding="utf-8-sig")
    (out / "quality_summary.json").write_text(json.dumps(quality_summary(reg), ensure_ascii=False, indent=2), encoding="utf-8")
    rows = []
    for m in sorted((a.cohort_root / a.region).glob("*/manifest.json")):
        d = json.loads(m.read_text(encoding="utf-8-sig"))
        rows.append({"batch_id": d.get("batch_id"), "status": d.get("status"), "confirmed": d.get("video_ids_confirmed"),
                     "created_at_utc": d.get("created_at_utc"), "manifest_sha256": sha256(m)})
    pd.DataFrame(rows).to_csv(out / "manifest_list.csv", index=False, encoding="utf-8-sig")
    lines = [f"{sha256(p)}  {p.name}" for p in sorted(out.iterdir()) if p.name != "SHA256SUMS.txt"]
    (out / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Handover written to", out, "| rows:", len(reg))


if __name__ == "__main__":
    main()
