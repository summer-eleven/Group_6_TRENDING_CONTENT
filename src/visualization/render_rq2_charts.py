"""Render High-Resolution Visualizations for RQ2 JP (HT-05 / HT-07)."""
import os
import tempfile
from pathlib import Path

# Set writable MPLCONFIGDIR for sandboxed execution
os.environ["MPLCONFIGDIR"] = tempfile.gettempdir()

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["figure.dpi"] = 300

ASSETS_DIR = Path("reports/assets/rq2")
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

df_video = pd.read_csv("data/processed/rq2_video_sentiment_JP.csv")
df_comments = pd.read_csv("data/processed/comments_sentiment_JP.csv")


def plot_sentiment_distribution():
    counts = df_comments["sentiment"].value_counts()
    labels = ["Positive", "Negative", "Neutral"]
    vals = [counts.get("positive", 0), counts.get("negative", 0), counts.get("neutral", 0)]
    colors = ["#2ecc71", "#e74c3c", "#95a5a6"]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, vals, color=colors, width=0.5, edgecolor="black", linewidth=1.2)

    total = sum(vals)
    for bar, val in zip(bars, vals):
        pct = (val / total) * 100
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 50,
            f"{val:,}\n({pct:.1f}%)",
            ha="center",
            va="bottom",
            fontweight="bold",
            fontsize=11,
        )

    ax.set_ylim(0, max(vals) * 1.18)
    ax.set_title("Comment Sentiment Distribution in Japan (XLM-RoBERTa)", fontsize=14, fontweight="bold", pad=15)
    ax.set_ylabel("Number of Comments", fontsize=12)
    ax.set_xlabel("Sentiment Category", fontsize=12)
    plt.tight_layout()
    out_path = ASSETS_DIR / "rq2_sentiment_distribution_jp.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"Saved: {out_path}")


def plot_negative_vs_views():
    valid = df_video[df_video["view_count"] > 0].copy()
    fig, ax = plt.subplots(figsize=(8, 5))

    scatter = ax.scatter(
        valid["negative_ratio"],
        valid["log_view_count"],
        c=valid["positive_ratio"],
        cmap="coolwarm",
        s=valid["sample_comment_count"] * 1.5,
        alpha=0.75,
        edgecolors="black",
        linewidths=0.5,
    )

    # Linear trendline
    m, b = np.polyfit(valid["negative_ratio"], valid["log_view_count"], 1)
    x_seq = np.linspace(valid["negative_ratio"].min(), valid["negative_ratio"].max(), 100)
    ax.plot(x_seq, m * x_seq + b, color="#c0392b", linestyle="--", linewidth=2.2, label=f"Trendline (slope={m:+.2f})")

    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Positive Ratio", fontsize=11)

    ax.set_title("Negative Comment Ratio vs. Log View Count (Japan)", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Negative Ratio (negative_count / total_comments)", fontsize=12)
    ax.set_ylabel("Log(1 + View Count)", fontsize=12)
    ax.legend(frameon=True)
    plt.tight_layout()
    out_path = ASSETS_DIR / "rq2_negative_vs_views_jp.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"Saved: {out_path}")


def plot_category_boxplots():
    valid = df_video[df_video["view_count"] > 0].copy()
    cat_names = {
        "10": "Music (10)",
        "20": "Gaming (20)",
        "22": "People & Blogs (22)",
        "24": "Entertainment (24)",
        "1": "Film & Animation (1)",
        "26": "Howto & Style (26)",
    }
    valid["cat_label"] = valid["category_id"].astype(str).map(lambda c: cat_names.get(c, f"Category {c}"))
    top_cats = valid["cat_label"].value_counts()[lambda x: x >= 3].index.tolist()
    sub_df = valid[valid["cat_label"].isin(top_cats)]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    grouped_data = [sub_df[sub_df["cat_label"] == cat]["log_view_count"].values for cat in top_cats]

    bplot = ax.boxplot(grouped_data, tick_labels=top_cats, patch_artist=True, vert=False)
    colors = ["#3498db", "#9b59b6", "#e67e22", "#1abc9c", "#f39c12", "#e74c3c"]
    for patch, color in zip(bplot["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_title("Log View Count Distribution by YouTube Category (Japan)", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Log(1 + View Count)", fontsize=12)
    ax.set_ylabel("Content Category", fontsize=12)
    plt.tight_layout()
    out_path = ASSETS_DIR / "rq2_category_boxplots_jp.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    plot_sentiment_distribution()
    plot_negative_vs_views()
    plot_category_boxplots()
    print("All RQ2 charts generated successfully.")
