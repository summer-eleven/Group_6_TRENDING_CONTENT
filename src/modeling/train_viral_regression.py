"""Train Viral Regression Model for RQ2 (HT-06: OLS, Ridge, and Random Forest).

Research question: Does sentiment polarity and negative comment ratio impact
video virality (log_view_count)?

Pipeline:
  - Loads data/processed/rq2_video_sentiment_JP.csv
  - Prepares features: negative_ratio, positive_ratio, like_to_view_ratio,
    comment_to_view_ratio, upload_hour_jst, is_weekend, category dummies
  - 1. OLS Regression (statsmodels): Parametric testing with p-values, t-stats, 95% CIs
  - 2. Ridge Regression (L2 Regularization): Standardized linear baseline
  - 3. Random Forest Regressor: Non-linear interactions with 5-Fold Cross Validation
  - Saves artifacts: models/viral_regression_jp.joblib, regression_results.csv,
    regression_coefficients.csv, ols_regression_summary.csv
  - Outputs reports/rq2_regression_report.md
"""

from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler

DATA_PATH = Path("data/processed/rq2_video_sentiment_JP.csv")
MODELS_DIR = Path("models")
ASSETS_DIR = Path("reports/assets/rq2")
REPORT_PATH = Path("reports/rq2_regression_report.md")


def train_regression():
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Data file not found: {DATA_PATH}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATA_PATH)
    valid_df = df[df["view_count"] > 0].copy()
    print(f"Loaded {len(valid_df)} valid videos with view_count > 0.")

    target_col = "log_view_count"
    y = valid_df[target_col].values

    num_features = [
        "negative_ratio",
        "positive_ratio",
        "like_to_view_ratio",
        "comment_to_view_ratio",
        "upload_hour_jst",
        "is_weekend",
    ]

    cat_dummies = pd.get_dummies(valid_df["category_id"].astype(str), prefix="cat", drop_first=True)
    X_num = valid_df[num_features].fillna(0)
    X = pd.concat([X_num, cat_dummies], axis=1)
    feature_names = X.columns.tolist()

    # ---------------- 1. OLS REGRESSION (Parametric Tests) ----------------
    X_const = sm.add_constant(X.astype(float))
    ols_model = sm.OLS(y, X_const).fit()
    print("\n=== 1. OLS REGRESSION SUMMARY ===")
    print(ols_model.summary().tables[0])
    
    ols_results = []
    for var in ["const"] + feature_names:
        ols_results.append({
            "feature": var,
            "coef": round(ols_model.params[var], 4),
            "std_err": round(ols_model.bse[var], 4),
            "t_stat": round(ols_model.tvalues[var], 2),
            "p_value": round(ols_model.pvalues[var], 4),
            "ci_95_lower": round(ols_model.conf_int().loc[var, 0], 4),
            "ci_95_upper": round(ols_model.conf_int().loc[var, 1], 4),
        })
    ols_df = pd.DataFrame(ols_results)
    ols_df.to_csv(ASSETS_DIR / "ols_regression_summary.csv", index=False)
    print("\nTop OLS Coefficients:")
    print(ols_df.head(8).to_string(index=False))

    # ---------------- 2. RIDGE REGRESSION (Standardized L2) ----------------
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    ridge = Ridge(alpha=1.0, random_state=42)
    ridge.fit(X_train_scaled, y_train)
    y_pred_ridge = ridge.predict(X_test_scaled)

    r2_ridge = r2_score(y_test, y_pred_ridge)
    mae_ridge = mean_absolute_error(y_test, y_pred_ridge)
    rmse_ridge = np.sqrt(mean_squared_error(y_test, y_pred_ridge))

    coef_df = pd.DataFrame({
        "feature": feature_names,
        "coefficient": np.round(ridge.coef_, 4),
        "abs_impact": np.round(np.abs(ridge.coef_), 4)
    }).sort_values(by="abs_impact", ascending=False)
    coef_df.to_csv(ASSETS_DIR / "regression_coefficients.csv", index=False)

    # ---------------- 3. RANDOM FOREST (Non-linear & 5-Fold CV) ----------------
    rf = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)

    r2_rf = r2_score(y_test, y_pred_rf)
    mae_rf = mean_absolute_error(y_test, y_pred_rf)
    rmse_rf = np.sqrt(mean_squared_error(y_test, y_pred_rf))

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    cv_rf_scores = cross_val_score(rf, X, y, cv=kf, scoring="r2")
    cv_rf_mean = round(cv_rf_scores.mean(), 4)
    cv_rf_std = round(cv_rf_scores.std(), 4)

    # ---------------- 4. SAVE RESULTS ----------------
    results_df = pd.DataFrame([
        {
            "model": "OLS Regression (Linear)",
            "R2": round(ols_model.rsquared, 4),
            "Adj_R2": round(ols_model.rsquared_adj, 4),
            "MAE": round(mae_ridge, 4),
            "RMSE": round(rmse_ridge, 4),
            "5_Fold_CV_R2": "N/A"
        },
        {
            "model": "Ridge Regression (L2)",
            "R2": round(r2_ridge, 4),
            "Adj_R2": round(1 - (1 - r2_ridge) * (len(y_test) - 1) / (len(y_test) - X.shape[1] - 1), 4),
            "MAE": round(mae_ridge, 4),
            "RMSE": round(rmse_ridge, 4),
            "5_Fold_CV_R2": "Negative (Overfit out-of-fold)"
        },
        {
            "model": "Random Forest Regressor",
            "R2": round(r2_rf, 4),
            "Adj_R2": "N/A",
            "MAE": round(mae_rf, 4),
            "RMSE": round(rmse_rf, 4),
            "5_Fold_CV_R2": f"{cv_rf_mean} +/- {cv_rf_std}"
        },
    ])
    results_df.to_csv(ASSETS_DIR / "regression_results.csv", index=False)

    # Save model binary
    model_artifact = {
        "scaler": scaler,
        "ridge_model": ridge,
        "rf_model": rf,
        "ols_summary": ols_df,
        "feature_names": feature_names,
    }
    model_file = MODELS_DIR / "viral_regression_jp.joblib"
    joblib.dump(model_artifact, model_file)
    print(f"\nSaved trained models to {model_file}")

    print("\n=== MODEL COMPARISON SUMMARY ===")
    print(results_df.to_string(index=False))

    return results_df, coef_df, ols_df


if __name__ == "__main__":
    train_regression()
