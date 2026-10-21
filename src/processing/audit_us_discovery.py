"""Thong ke hieu qua discovery US: quota, ty le confirmed, da dang channel, overlap thi truong.

Doc-chi (khong goi API/SQL). Dung de so sanh 2 batch truoc/sau khi doi nguon seed.

  uv run python -m src.processing.audit_us_discovery --region US
Ket qua: reports/assets/us_discovery_audit.csv
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd


def concentration_metrics(channel_ids: list) -> dict:
    """top1/top5 share va so channel hieu dung (1/HHI). Cang cao cang da dang."""
    counts = Counter(c for c in channel_ids if c)
    n = sum(counts.values())
    if n == 0:
        return {"channels": 0, "top1_share": None, "top5_share": None, "effective_channels": None}
    shares = sorted((v / n for v in counts.values()), reverse=True)
    hhi = sum(s * s for s in shares)
    return {"channels": len(counts), "top1_share": round(shares[0], 4),
            "top5_share": round(sum(shares[:5]), 4), "effective_channels": round(1 / hhi, 2)}


def batch_row(manifest: dict, t0_records: list, candidate_payload: dict | None) -> dict:
    cand_n = (candidate_payload or {}).get("candidate_count", manifest.get("candidates_selected"))
    confirmed = manifest.get("video_ids_confirmed", len(t0_records))
    disc_calls = (candidate_payload or {}).get("api_requests")
    detail_calls = manifest.get("api_calls")
    total_calls = (disc_calls or 0) + (detail_calls or 0)
    row = {"batch_id": manifest.get("batch_id"), "created_at_utc": manifest.get("created_at_utc"),
           "candidates": cand_n, "confirmed_new": confirmed,
           "confirmed_rate": round(confirmed / cand_n, 4) if cand_n else None,
           "discovery_requests": disc_calls, "details_requests": detail_calls,
           "requests_per_confirmed": round(total_calls / confirmed, 3) if confirmed else None}
    row.update(concentration_metrics([r.get("channel_id") for r in t0_records]))
    return row


def market_overlap(registry_root: Path, region: str) -> pd.DataFrame:
    sets = {}
    for r in ("VN", "US", "JP"):
        p = registry_root / f"youtube_cohort_registry_{r}.csv"
        if p.exists():
            sets[r] = set(pd.read_csv(p, usecols=["video_id"], dtype=str)["video_id"].dropna())
    rows = []
    if region in sets:
        for other, ids in sets.items():
            if other != region:
                both = sets[region] & ids
                rows.append({"region": region, "other": other, "region_unique": len(sets[region]),
                             "other_unique": len(ids), "shared_ids": len(both),
                             "shared_share_of_region": round(len(both) / len(sets[region]), 4)})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="US", choices=("VN", "US", "JP"))
    ap.add_argument("--cohort-root", type=Path, default=Path("data/raw/rolling_cohorts"))
    ap.add_argument("--registry-root", type=Path, default=Path("data/processed"))
    ap.add_argument("--output", type=Path, default=Path("reports/assets/us_discovery_audit.csv"))
    a = ap.parse_args()

    rows = []
    for mpath in sorted((a.cohort_root / a.region).glob("*/manifest.json")):
        manifest = json.loads(mpath.read_text(encoding="utf-8-sig"))
        t0 = json.loads((mpath.parent / "t0.json").read_text(encoding="utf-8-sig")).get("records", [])
        cand = None
        src = manifest.get("source_candidates_file")
        if src and Path(src).is_file():
            cand = json.loads(Path(src).read_text(encoding="utf-8-sig"))
        rows.append(batch_row(manifest, t0, cand))
    audit = pd.DataFrame(rows)
    if audit.empty:
        print(f"No {a.region} batches found under {a.cohort_root / a.region}")
        return
    a.output.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(a.output, index=False, encoding="utf-8-sig")
    print(audit.to_string(index=False))
    print("\nTotal confirmed new (sum of batches):", int(audit["confirmed_new"].sum()))
    ov = market_overlap(a.registry_root, a.region)
    if not ov.empty:
        print("\nCross-market overlap:\n", ov.to_string(index=False))
    print("\nSaved:", a.output)
    print("NOTE: candidate counts are NOT progress; only confirmed non-duplicate IDs count.")


if __name__ == "__main__":
    main()
