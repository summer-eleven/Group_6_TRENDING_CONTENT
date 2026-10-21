"""Huan luyen + danh gia Classification (NG-05): Logistic Regression baseline va Random Forest.

  uv add scikit-learn          # lan dau (commit uv.lock)
  uv run python -m src.modeling.train_trending_classifier --dataset data/processed/classification/US/<version>/dataset.csv

Neu thieu du lieu/nhan (it hon --min-per-class mau moi lop) script KHONG tao metric gia:
no ghi model_card_classification.md voi trang thai BLOCKED va thoat voi ma 2.

Luu y: mo hinh dung de DU DOAN, khong chung minh quan he nhan qua cua upload time.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, balanced_accuracy_score,
                             confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.modeling.build_classification_dataset import CATEGORICAL_FEATURES, NUMERIC_FEATURES

SEED = 42


def make_preprocessor() -> ColumnTransformer:
    # Fit tren TRAIN only (vi nam trong Pipeline).
    num = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    cat = Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                    ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=2))])
    return ColumnTransformer([("num", num, NUMERIC_FEATURES), ("cat", cat, CATEGORICAL_FEATURES)])


def make_models() -> dict:
    return {
        "majority_baseline": Pipeline([("pre", make_preprocessor()),
                                       ("clf", DummyClassifier(strategy="most_frequent"))]),
        "logistic_regression": Pipeline([("pre", make_preprocessor()),
                                         ("clf", LogisticRegression(max_iter=2000, class_weight="balanced",
                                                                    random_state=SEED))]),
        "random_forest": Pipeline([("pre", make_preprocessor()),
                                   ("clf", RandomForestClassifier(n_estimators=300, min_samples_leaf=3,
                                                                  class_weight="balanced_subsample",
                                                                  random_state=SEED, n_jobs=-1))]),
    }


def time_split(df: pd.DataFrame, test_frac: float = 0.2):
    """Tach theo thoi gian (prediction_cutoff). Tra ve (train, test, method). Fallback: stratified theo video."""
    df = df.sort_values("prediction_cutoff").reset_index(drop=True)
    cut = int(len(df) * (1 - test_frac))
    train, test = df.iloc[:cut], df.iloc[cut:]
    if train["label"].nunique() == 2 and test["label"].nunique() == 2:
        return train, test, "time_based_80_20"
    if df["label"].value_counts().min() >= 2:          # moi video 1 hang -> khong lap video giua train/test
        tr, te = train_test_split(df, test_size=test_frac, stratify=df["label"], random_state=SEED)
        return tr, te, "stratified_random_by_video_FALLBACK (khong kiem duoc quá khứ→tương lai)"
    return None, None, "unsplittable"


def metrics_for(y_true, proba, pred) -> dict:
    both = len(set(y_true)) == 2
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    return {"accuracy": accuracy_score(y_true, pred), "balanced_accuracy": balanced_accuracy_score(y_true, pred),
            "precision": precision_score(y_true, pred, zero_division=0),
            "recall": recall_score(y_true, pred, zero_division=0), "f1": f1_score(y_true, pred, zero_division=0),
            "roc_auc": roc_auc_score(y_true, proba) if both else np.nan,
            "pr_auc": average_precision_score(y_true, proba) if both else np.nan,
            "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}


def feature_importance(model: Pipeline) -> pd.DataFrame:
    names = model.named_steps["pre"].get_feature_names_out()
    clf = model.named_steps["clf"]
    if hasattr(clf, "coef_"):
        vals, kind = clf.coef_[0], "coefficient (standardised)"
    elif hasattr(clf, "feature_importances_"):
        vals, kind = clf.feature_importances_, "impurity importance"
    else:
        return pd.DataFrame()
    return pd.DataFrame({"feature": names, "value": vals, "kind": kind}).sort_values(
        "value", key=np.abs, ascending=False)


def write_card(path, status, body):
    path.write_text(f"# Model card - Trending classifier\n\n**Trang thai:** {status}\n\n{body}\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, default=Path("reports/report_4/classification"))
    ap.add_argument("--min-per-class", type=int, default=10)
    ap.add_argument("--test-frac", type=float, default=0.2)
    a = ap.parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)
    card = a.output_dir / "model_card_classification.md"

    df = pd.read_csv(a.dataset, parse_dates=["prediction_cutoff"])
    counts = df["label"].value_counts().to_dict()
    n_pos, n_neg = int(counts.get(1, 0)), int(counts.get(0, 0))
    base = f"- Dataset: `{a.dataset}`\n- Rows: {len(df)} | positives: {n_pos} | negatives: {n_neg}\n"
    if min(n_pos, n_neg) < a.min_per_class:
        write_card(card, "BLOCKED - chua du nhan hop le",
                   base + f"\nMoi lop can >= {a.min_per_class} mau. KHONG co metric nao duoc bao cao.\n"
                   "Ke hoach thu nhan: giu chart monitor chay deu moi gio, doi cua so 24h ket thuc voi coverage 24/24 bins, "
                   "build lai rq1 dataset roi build_classification_dataset; bao Ha ve chinh sach nhan. "
                   "Khong gan nhan 0 tu UNKNOWN.")
        print("BLOCKED:", base)
        sys.exit(2)

    train, test, method = time_split(df, a.test_frac)
    if train is None:
        write_card(card, "BLOCKED - khong the tach train/test hop le", base)
        sys.exit(2)
    feats = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    Xtr, ytr, Xte, yte = train[feats], train["label"].astype(int), test[feats], test["label"].astype(int)

    rows, probas, preds, fitted = [], {}, {}, {}
    n_splits = int(min(5, ytr.value_counts().min()))
    for name, model in make_models().items():
        cv = (cross_val_score(model, Xtr, ytr, cv=StratifiedKFold(n_splits, shuffle=True, random_state=SEED),
                              scoring="average_precision").mean() if n_splits >= 2 and name != "majority_baseline" else np.nan)
        model.fit(Xtr, ytr)
        p = model.predict_proba(Xte)[:, 1]
        pred = (p >= 0.5).astype(int)
        probas[name], preds[name], fitted[name] = p, pred, model
        rows.append({"model": name, "split": method, "n_train": len(train), "n_test": len(test),
                     "test_positives": int(yte.sum()), "cv_pr_auc_train": cv, **metrics_for(yte, p, pred)})
    ev = pd.DataFrame(rows)
    ev.to_csv(a.output_dir / "evaluation_classification.csv", index=False, encoding="utf-8-sig")

    # confusion matrices
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
    for ax, (name, pred) in zip(axes, preds.items()):
        cm = confusion_matrix(yte, pred, labels=[0, 1])
        ax.imshow(cm, cmap="Blues")
        ax.set_title(name, fontsize=9)
        ax.set_xticks([0, 1], ["pred 0", "pred 1"]); ax.set_yticks([0, 1], ["true 0", "true 1"])
        for (i, j), v in np.ndenumerate(cm):
            ax.text(j, i, int(v), ha="center", va="center")
    fig.tight_layout(); fig.savefig(a.output_dir / "confusion_matrix.png", dpi=150); plt.close(fig)

    # feature importance + error analysis (theo category / office-hours) cho RF
    imp = pd.concat([feature_importance(fitted[m]).assign(model=m)
                     for m in ("logistic_regression", "random_forest")])
    imp.to_csv(a.output_dir / "feature_importance.csv", index=False, encoding="utf-8-sig")
    te = test.copy(); te["pred"] = preds["random_forest"]; te["y"] = yte.values
    te["error"] = np.select([(te.pred == 1) & (te.y == 0), (te.pred == 0) & (te.y == 1)], ["FP", "FN"], "correct")
    err = (te.groupby(["f_category_id", "f_is_office_hours", "error"]).size().unstack(fill_value=0).reset_index())
    err.to_csv(a.output_dir / "error_analysis.csv", index=False, encoding="utf-8-sig")

    best = ev.loc[ev["model"] != "majority_baseline"].sort_values("pr_auc", ascending=False).iloc[0]
    table = ev[["model", "precision", "recall", "f1", "roc_auc", "pr_auc"]].round(3).to_markdown(index=False) \
        if hasattr(ev, "to_markdown") else ev.round(3).to_string(index=False)
    body = (base + f"- Split: {method} | train {len(train)} / test {len(test)} | seed {SEED}\n"
            f"- Hyperparameters: LR(class_weight=balanced, max_iter=2000); RF(n_estimators=300, min_samples_leaf=3, "
            f"class_weight=balanced_subsample)\n- Tien xu ly fit tren train only (Pipeline).\n\n## Ket qua holdout\n\n{table}\n\n"
            f"Mo hinh tot nhat theo PR-AUC: **{best['model']}**. So voi baseline da so, chi co y nghia neu PR-AUC vuot ty le lop duong "
            f"trong test ({yte.mean():.3f}).\n\n## Gioi han\n"
            "- Nhan = quan sat tren chart mostPopular (category 0) trong 24h, khong dong nghia 'viral'.\n"
            "- Chart lay mau theo gio: co the bo sot lan xuat hien giua hai lan chup.\n"
            "- Mau it positives -> metric co khoang tin cay rong; khong ket luan nhan qua cua upload time.\n"
            "- Neu split la FALLBACK (stratified), KHONG duoc dien giai nhu kiem tra qua khu->tuong lai.\n")
    write_card(card, "COMPLETED", body)
    print(ev.round(3).to_string(index=False))
    print("Outputs in", a.output_dir)


if __name__ == "__main__":
    main()
