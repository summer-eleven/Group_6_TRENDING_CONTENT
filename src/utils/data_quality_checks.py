"""
data_quality_checks.py  –  Lightweight Data-Quality Validation (Week 3 / Task A3)
==================================================================================
Author : Hà
Purpose: Engineering validation checks for the YouTube trending dataset.
         NOT a full EDA (that comes in Weeks 5-6).

Usage:
    # As a standalone script – validates data/processed/youtube_clean.csv
    python -m src.utils.data_quality_checks

    # As a reusable module
    from src.utils.data_quality_checks import run_all_checks
    report = run_all_checks("data/processed/youtube_clean.csv")
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EXPECTED_COLUMNS: list[str] = [
    "video_id",
    "title",
    "channel",
    "views",
    "published",
    "url",
    "search_query",
]

YOUTUBE_URL_PATTERN = re.compile(
    r"^https?://(www\.)?youtube\.com/watch\?v=[\w-]{11}$"
)

# ---------------------------------------------------------------------------
# Individual check functions (reusable)
# ---------------------------------------------------------------------------

def check_duplicate_video_ids(df: pd.DataFrame) -> dict:
    """Detect duplicate video_id values.

    Returns
    -------
    dict with keys:
        count        – number of duplicated video_id entries
        duplicates   – DataFrame of the duplicated rows (all occurrences)
    """
    dup_mask = df["video_id"].duplicated(keep=False)
    dup_df = df.loc[dup_mask].sort_values("video_id")
    return {
        "count": df["video_id"].duplicated(keep="first").sum(),
        "duplicates": dup_df,
    }


def check_missing_critical_fields(df: pd.DataFrame) -> dict:
    """Check for missing (NaN / empty-string) title, channel, or url.

    Returns
    -------
    dict mapping field name → DataFrame of rows with missing values
    """
    results: dict[str, pd.DataFrame] = {}
    for col in ("title", "channel", "url"):
        if col not in df.columns:
            results[col] = pd.DataFrame()
            continue
        mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
        results[col] = df.loc[mask]
    return results


def check_invalid_views(df: pd.DataFrame) -> dict:
    """Find rows where views are non-numeric or negative.

    Returns
    -------
    dict with keys:
        non_numeric  – DataFrame of rows that cannot be parsed as numbers
        negative     – DataFrame of rows with views < 0
    """
    views_numeric = pd.to_numeric(df["views"], errors="coerce")
    non_numeric_mask = views_numeric.isna() & df["views"].notna()
    negative_mask = views_numeric < 0

    return {
        "non_numeric": df.loc[non_numeric_mask],
        "negative": df.loc[negative_mask],
    }


def check_malformed_urls(df: pd.DataFrame) -> dict:
    """Identify URLs that do not match expected YouTube watch URL format.

    Returns
    -------
    dict with keys:
        count        – number of malformed URLs
        malformed    – DataFrame of affected rows
    """
    if "url" not in df.columns:
        return {"count": 0, "malformed": pd.DataFrame()}

    # Treat NaN / empty as already caught by missing-fields check;
    # here we focus on non-empty values that look wrong.
    non_empty = df["url"].fillna("").astype(str).str.strip()
    mask = (non_empty != "") & (~non_empty.str.match(YOUTUBE_URL_PATTERN))
    return {
        "count": mask.sum(),
        "malformed": df.loc[mask],
    }


def check_unexpected_columns(
    df: pd.DataFrame,
    expected: list[str] | None = None,
) -> dict:
    """Compare actual columns against expected schema.

    Returns
    -------
    dict with keys:
        missing  – columns in expected but absent from df
        extra    – columns in df but not in expected
        match    – True if columns match exactly
    """
    if expected is None:
        expected = EXPECTED_COLUMNS

    actual = list(df.columns)
    missing = [c for c in expected if c not in actual]
    extra = [c for c in actual if c not in expected]
    return {
        "missing": missing,
        "extra": extra,
        "match": (len(missing) == 0 and len(extra) == 0),
    }

# ---------------------------------------------------------------------------
# Aggregated runner
# ---------------------------------------------------------------------------

def run_all_checks(
    filepath: str | Path,
    expected_columns: list[str] | None = None,
) -> dict:
    """Run every validation check and return a structured report dict.

    Parameters
    ----------
    filepath : str | Path
        Path to the CSV file to validate.
    expected_columns : list[str], optional
        Override the default EXPECTED_COLUMNS list.

    Returns
    -------
    dict  –  keyed by check name, each value is the individual result dict.
    """
    df = pd.read_csv(filepath)
    report: dict = {"_meta": {"file": str(filepath), "total_rows": len(df)}}

    report["duplicate_video_ids"] = check_duplicate_video_ids(df)
    report["missing_fields"] = check_missing_critical_fields(df)
    report["invalid_views"] = check_invalid_views(df)
    report["malformed_urls"] = check_malformed_urls(df)
    report["unexpected_columns"] = check_unexpected_columns(df, expected_columns)

    return report

# ---------------------------------------------------------------------------
# Human-readable summary
# ---------------------------------------------------------------------------

_PASS = "✅ PASS"
_FAIL = "❌ FAIL"
_WARN = "⚠️  WARN"


def format_summary(report: dict) -> str:
    """Render a human-readable validation summary from *report*.

    Returns a multi-line string suitable for printing or saving to a file.
    """
    lines: list[str] = []
    meta = report["_meta"]
    lines.append("=" * 70)
    lines.append("  DATA-QUALITY VALIDATION REPORT")
    lines.append("=" * 70)
    lines.append(f"  File   : {meta['file']}")
    lines.append(f"  Rows   : {meta['total_rows']:,}")
    lines.append("=" * 70)

    # 1. Duplicate video_id
    dup = report["duplicate_video_ids"]
    status = _PASS if dup["count"] == 0 else _FAIL
    lines.append(f"\n[1] Duplicate video_id            {status}")
    lines.append(f"    Duplicated entries : {dup['count']}")
    if dup["count"] > 0:
        sample = dup["duplicates"]["video_id"].unique()[:10]
        lines.append(f"    Sample IDs         : {', '.join(sample)}")

    # 2. Missing critical fields
    miss = report["missing_fields"]
    for col, missing_df in miss.items():
        count = len(missing_df)
        status = _PASS if count == 0 else _FAIL
        lines.append(f"\n[2] Missing '{col}'                {status}")
        lines.append(f"    Missing rows : {count}")
        if count > 0 and "video_id" in missing_df.columns:
            sample_ids = missing_df["video_id"].head(5).tolist()
            lines.append(f"    Sample IDs   : {sample_ids}")

    # 3. Invalid views
    iv = report["invalid_views"]
    nn = len(iv["non_numeric"])
    neg = len(iv["negative"])
    status_nn = _PASS if nn == 0 else _FAIL
    status_neg = _PASS if neg == 0 else _FAIL
    lines.append(f"\n[3] Non-numeric views              {status_nn}")
    lines.append(f"    Count : {nn}")
    lines.append(f"\n[4] Negative views                 {status_neg}")
    lines.append(f"    Count : {neg}")
    if neg > 0:
        sample = iv["negative"][["video_id", "views"]].head(5)
        lines.append(f"    Sample:\n{sample.to_string(index=False)}")

    # 4. Malformed URLs
    mu = report["malformed_urls"]
    status = _PASS if mu["count"] == 0 else _WARN
    lines.append(f"\n[5] Malformed URLs                 {status}")
    lines.append(f"    Count : {mu['count']}")
    if mu["count"] > 0:
        sample_urls = mu["malformed"]["url"].head(5).tolist()
        for u in sample_urls:
            lines.append(f"      → {u}")

    # 5. Unexpected columns
    uc = report["unexpected_columns"]
    status = _PASS if uc["match"] else _FAIL
    lines.append(f"\n[6] Unexpected column changes      {status}")
    if uc["missing"]:
        lines.append(f"    Missing columns : {uc['missing']}")
    if uc["extra"]:
        lines.append(f"    Extra columns   : {uc['extra']}")
    if uc["match"]:
        lines.append("    Schema matches expected columns.")

    lines.append("\n" + "=" * 70)
    lines.append("  END OF REPORT")
    lines.append("=" * 70)
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main(filepath: Optional[str] = None) -> None:
    """Run validation on the given CSV (or default processed file) and print."""
    if filepath is None:
        # Resolve relative to project root
        project_root = Path(__file__).resolve().parents[2]
        filepath = str(project_root / "data" / "processed" / "youtube_clean.csv")

    report = run_all_checks(filepath)
    summary = format_summary(report)
    print(summary)

    # Also write the summary next to the data file for easy review
    output_path = Path(filepath).parent / "validation_report.txt"
    output_path.write_text(summary, encoding="utf-8")
    print(f"\n📄 Report saved to: {output_path}")


if __name__ == "__main__":
    csv_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(csv_arg)
