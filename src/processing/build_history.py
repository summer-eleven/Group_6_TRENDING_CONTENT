"""N2 - Ghép các snapshot US thành một bảng lịch sử.

Chạy từ thư mục gốc dự án:
    uv run python src/processing/build_history.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = ROOT / "data" / "raw" / "snapshots" / "US"
OUTPUT = ROOT / "data" / "processed" / "youtube_history_US.csv"

REGION = "US"
REQUIRED = ["video_id", "region_code", "collected_at",
            "view_count", "like_count", "comment_count"]
COUNT_COLS = ["view_count", "like_count", "comment_count"]
MIN_SNAPSHOTS = 3


def main() -> None:
    # Hỗ trợ JSON của crawler nhóm (youtube_snapshot_US_*.json) và CSV (youtube_US_*.csv).
    files = sorted(
        list(SNAPSHOT_DIR.glob("youtube_snapshot*.json"))
        + list(SNAPSHOT_DIR.glob("youtube_US_*.csv"))
    )
    if not files:
        raise SystemExit(f"Không tìm thấy snapshot trong {SNAPSHOT_DIR}")

    frames = []
    for f in files:
        df = pd.read_json(f, dtype=False) if f.suffix == ".json" else pd.read_csv(f)
        missing = [c for c in REQUIRED if c not in df.columns]
        if missing:
            raise SystemExit(f"{f.name} thiếu cột: {missing}")
        df["source_file"] = f.name
        frames.append(df)

    history = pd.concat(frames, ignore_index=True)

    # Chỉ giữ dữ liệu US, không lẫn VN/JP.
    other = history["region_code"] != REGION
    if other.any():
        print(f"CẢNH BÁO: bỏ {other.sum()} dòng có region_code != {REGION}")
        history = history[~other]

    history["collected_at"] = pd.to_datetime(
        history["collected_at"], utc=True, errors="coerce")
    bad_time = history["collected_at"].isna().sum()
    if bad_time:
        print(f"CẢNH BÁO: bỏ {bad_time} dòng có collected_at không hợp lệ")
        history = history.dropna(subset=["collected_at"])

    # Ép kiểu số; giá trị lỗi/thiếu thành <NA>, không gán 0.
    for col in COUNT_COLS:
        history[col] = pd.to_numeric(history[col], errors="coerce").astype("Int64")

    history = history.drop_duplicates(
        subset=["video_id", "region_code", "collected_at"])
    history = history.sort_values(["video_id", "collected_at"]).reset_index(drop=True)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    history.to_csv(OUTPUT, index=False, encoding="utf-8-sig")

    n_times = history["collected_at"].nunique()
    obs = history.groupby("video_id").size()
    print("Snapshot files:", len(files))
    print("Thời điểm thu thập khác nhau:", n_times)
    print("History rows:", len(history))
    print("Số video:", obs.shape[0], "| video xuất hiện >= 2 lần:", int((obs >= 2).sum()))
    if n_times < MIN_SNAPSHOTS:
        print(f"CẢNH BÁO: cần ít nhất {MIN_SNAPSHOTS} snapshot ở các thời điểm khác nhau "
              "trước khi kiểm tra growth.")


if __name__ == "__main__":
    main()