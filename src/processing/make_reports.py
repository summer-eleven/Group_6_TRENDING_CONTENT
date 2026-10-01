"""N5 - Sinh reports/growth_analysis_US.md từ growth_metrics_US.csv.

Chạy: uv run python src/processing/make_report.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "data" / "processed" / "growth_metrics_US.csv"
OUTPUT = ROOT / "reports" / "growth_analysis_US.md"
TOP_N = 10


def fmt(x, nd=2):
    return "n/a" if pd.isna(x) else f"{x:,.{nd}f}"


def main() -> None:
    df = pd.read_csv(INPUT)
    df["collected_at"] = pd.to_datetime(df["collected_at"], utc=True)
    has_speed = df.dropna(subset=["views_per_hour"])
    if has_speed.empty:
        raise SystemExit("Chưa có views_per_hour. Cần >= 2 snapshot cho cùng video.")

    acc = has_speed["view_acceleration"].dropna()
    summary = [
        ("Median views/hour", fmt(has_speed["views_per_hour"].median())),
        ("90th percentile views/hour", fmt(has_speed["views_per_hour"].quantile(0.90))),
        ("Median engagement_rate", fmt(df["engagement_rate"].median(), 4)),
        ("Median comments/hour", fmt(has_speed["comments_per_hour"].median())),
        ("Positive view_acceleration ratio",
         fmt((acc > 0).mean() * 100, 1) + "%" if len(acc) else "n/a"),
    ]

    # Top video theo tốc độ view cao nhất từng đạt được.
    idx = has_speed.groupby("video_id")["views_per_hour"].idxmax()
    top = has_speed.loc[idx].sort_values("views_per_hour", ascending=False).head(TOP_N)
    title_col = "title" if "title" in top.columns else None

    lines = [
        "# Growth Analysis - United States (US)",
        "",
        f"- Khoảng thời gian dữ liệu: {df['collected_at'].min():%Y-%m-%d %H:%M} "
        f"đến {df['collected_at'].max():%Y-%m-%d %H:%M} (UTC)",
        f"- Số snapshot (thời điểm khác nhau): {df['collected_at'].nunique()}",
        f"- Số video: {df['video_id'].nunique()} | Số quan sát có tốc độ: {len(has_speed)}",
        "",
        "## 1. Bảng tổng hợp (dùng cho so sánh VN - US - JP)",
        "",
        "| Chỉ số | Giá trị US |",
        "| --- | --- |",
        *[f"| {k} | {v} |" for k, v in summary],
        "",
        f"## 2. Top {len(top)} video tăng nhanh nhất (theo views/hour cao nhất)",
        "",
        "| # | video_id | " + ("Title | " if title_col else "")
        + "Views/hour | Likes/hour | Comments/hour | Engagement | View accel. |",
        "| --- | --- | " + ("--- | " if title_col else "") + "--- | --- | --- | --- | --- |",
    ]
    for i, (_, r) in enumerate(top.iterrows(), 1):
        t = f"{str(r['title'])[:60].replace('|', '/')} | " if title_col else ""
        lines.append(
            f"| {i} | {r['video_id']} | {t}{fmt(r['views_per_hour'])} | "
            f"{fmt(r['likes_per_hour'])} | {fmt(r['comments_per_hour'])} | "
            f"{fmt(r['engagement_rate'], 4)} | {fmt(r['view_acceleration'])} |")

    lines += [
        "",
        "## 3. Nhận xét từ số liệu",
        "",
        "> _Nguyên điền sau khi xem bảng trên: mô tả bằng số cụ thể vì sao 5-10 video này tăng nhanh "
        "(tốc độ, acceleration, engagement). Kết hợp sentiment của Hà nếu đã có._",
        "",
        "## 4. Lưu ý diễn giải",
        "",
        "- `high_growth_flag` là proxy mô tả: quan sát nằm trong top 10% `views_per_hour` của dữ liệu US hiện có.",
        "- Đây **không** chứng minh video chắc chắn viral và **không** giải thích nguyên nhân viral.",
        "- Tốc độ tính theo khoảng thời gian thực tế giữa hai snapshot (`hours_since_prev`).",
        "- So sánh giữa các nước nên dùng median/percentile, không dùng tổng view.",
        "- Mẫu là các video trending nên có thể lệch (selection bias).",
        "",
    ]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print("Đã ghi", OUTPUT)


if __name__ == "__main__":
    main()