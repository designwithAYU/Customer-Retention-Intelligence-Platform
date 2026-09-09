"""
churn_model.py
===============
Trains and evaluates two churn prediction models (Logistic Regression,
Random Forest) on the leakage-safe feature table produced by
feature_engineering.py, then scores every customer's churn probability,
assigns risk tiers, and computes a business retention-priority score.

Run:
    python src/churn_model.py
Outputs:
    outputs/model_results/model_comparison.csv
    outputs/model_results/feature_importance.csv
    outputs/model_results/customer_churn_risk.csv
    outputs/tables/retention_priority.csv
    outputs/figures/roc_curve.png
    outputs/figures/confusion_matrices.png
    outputs/figures/feature_importance.png
"""

import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                              roc_auc_score, roc_curve, confusion_matrix, classification_report)

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
FIG_DIR = ROOT / "outputs" / "figures"
TABLE_DIR = ROOT / "outputs" / "tables"
MODEL_DIR = ROOT / "outputs" / "model_results"
for d in (FIG_DIR, TABLE_DIR, MODEL_DIR):
    d.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42

# Configurable risk thresholds (Step 17 requirement: no hardcoded thresholds scattered around)
RISK_THRESHOLDS = {"high": 0.70, "medium": 0.40}


def risk_tier(p):
    if p >= RISK_THRESHOLDS["high"]:
        return "High"
    elif p >= RISK_THRESHOLDS["medium"]:
        return "Medium"
    return "Low"


def load_features():
    df = pd.read_csv(PROCESSED / "feature_table.csv")
    return df


def train_and_evaluate(df):
    numeric_features = [
        "age", "monthly_price", "discount_percentage", "premium_support",
        "tenure_days", "avg_sessions", "avg_session_minutes", "avg_feature_usage",
        "engagement_trend_ratio", "total_tickets", "avg_satisfaction",
        "avg_resolution_time", "unresolved_tickets", "total_revenue",
        "total_transactions", "recency_days",
    ]
    categorical_features = ["acquisition_channel", "plan_name", "billing_cycle"]

    X = df[numeric_features + categorical_features]
    y = df["churn"]

    X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
        X, y, df["customer_id"], test_size=0.25, random_state=RANDOM_SEED, stratify=y
    )

    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), numeric_features),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
    ])

    # Class imbalance note: churn rate ~20%, which is a moderate (not severe)
    # imbalance. Rather than blindly oversampling with SMOTE, we use
    # class_weight="balanced" in both models -- a simpler, well-understood
    # approach that re-weights the loss function without synthesizing data.
    models = {
        "Logistic Regression": Pipeline([
            ("prep", preprocessor),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=RANDOM_SEED)),
        ]),
        "Random Forest": Pipeline([
            ("prep", preprocessor),
            ("clf", RandomForestClassifier(
                n_estimators=300, max_depth=10, min_samples_leaf=5,
                class_weight="balanced", random_state=RANDOM_SEED, n_jobs=-1
            )),
        ]),
    }

    results = []
    roc_data = {}
    fitted_models = {}

    for name, pipe in models.items():
        pipe.fit(X_train, y_train)
        fitted_models[name] = pipe
        y_pred = pipe.predict(X_test)
        y_proba = pipe.predict_proba(X_test)[:, 1]

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred)
        rec = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_proba)
        cm = confusion_matrix(y_test, y_pred)

        results.append({
            "model": name, "accuracy": round(acc, 4), "precision": round(prec, 4),
            "recall": round(rec, 4), "f1_score": round(f1, 4), "roc_auc": round(auc, 4),
        })
        fpr, tpr, _ = roc_curve(y_test, y_proba)
        roc_data[name] = (fpr, tpr, auc)

        print(f"\n=== {name} ===")
        print(classification_report(y_test, y_pred, target_names=["Retained", "Churned"]))
        print("Confusion matrix:\n", cm)

    comparison_df = pd.DataFrame(results)
    comparison_df.to_csv(MODEL_DIR / "model_comparison.csv", index=False)
    print("\nModel comparison:\n", comparison_df.to_string(index=False))

    # --- ROC curve plot ---
    plt.figure(figsize=(7, 6))
    for name, (fpr, tpr, auc) in roc_data.items():
        plt.plot(fpr, tpr, label=f"{name} (AUC={auc:.3f})", linewidth=2)
    plt.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Random baseline")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve — Churn Prediction Models")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "roc_curve.png", dpi=120)
    plt.close()

    # --- Confusion matrices plot ---
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, (name, pipe) in zip(axes, fitted_models.items()):
        y_pred = pipe.predict(X_test)
        cm = confusion_matrix(y_test, y_pred)
        im = ax.imshow(cm, cmap="Blues")
        ax.set_title(name)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        ax.set_xticks([0, 1]); ax.set_xticklabels(["Retained", "Churned"])
        ax.set_yticks([0, 1]); ax.set_yticklabels(["Retained", "Churned"])
        for i in range(2):
            for j in range(2):
                ax.text(j, i, cm[i, j], ha="center", va="center",
                        color="white" if cm[i, j] > cm.max() / 2 else "black")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "confusion_matrices.png", dpi=120)
    plt.close()

    # --- Feature importance (Random Forest) ---
    rf_pipe = fitted_models["Random Forest"]
    ohe_cols = rf_pipe.named_steps["prep"].named_transformers_["cat"].get_feature_names_out(categorical_features)
    all_feature_names = numeric_features + list(ohe_cols)
    importances = rf_pipe.named_steps["clf"].feature_importances_
    fi_df = pd.DataFrame({"feature": all_feature_names, "importance": importances})
    fi_df = fi_df.sort_values("importance", ascending=False)
    fi_df.to_csv(MODEL_DIR / "feature_importance.csv", index=False)

    top_n = fi_df.head(15)
    plt.figure(figsize=(8, 6))
    plt.barh(top_n["feature"][::-1], top_n["importance"][::-1], color="#2E86AB")
    plt.xlabel("Importance")
    plt.title("Top 15 Feature Importances — Random Forest")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "feature_importance.png", dpi=120)
    plt.close()

    print("\nTop 10 features driving churn prediction:")
    print(fi_df.head(10).to_string(index=False))

    # decide "production" model = higher ROC-AUC
    best_name = comparison_df.sort_values("roc_auc", ascending=False).iloc[0]["model"]
    best_model = fitted_models[best_name]
    print(f"\nSelected model for scoring: {best_name}")

    return best_model, best_name, comparison_df, fi_df, (numeric_features, categorical_features)


def score_all_customers(df, model, feature_cols):
    numeric_features, categorical_features = feature_cols
    X_all = df[numeric_features + categorical_features]
    proba = model.predict_proba(X_all)[:, 1]
    df = df.copy()
    df["churn_probability"] = proba.round(4)
    df["risk_level"] = df["churn_probability"].apply(risk_tier)
    return df


def compute_revenue_at_risk(scored_active):
    scored_active = scored_active.copy()
    # annualize monthly recurring value as a simple "customer value" proxy
    scored_active["annualized_value"] = np.where(
        scored_active["billing_cycle"] == "Monthly",
        scored_active["monthly_price"] * 12,
        scored_active["monthly_price"]
    )
    scored_active["revenue_at_risk"] = (scored_active["annualized_value"] *
                                         scored_active["churn_probability"]).round(2)
    return scored_active


def compute_retention_priority(scored_active):
    df = scored_active.copy()
    value_median = df["annualized_value"].median()

    def priority(row):
        high_risk = row["churn_probability"] >= RISK_THRESHOLDS["high"]
        med_risk = row["churn_probability"] >= RISK_THRESHOLDS["medium"]
        high_value = row["annualized_value"] >= value_median
        if high_risk and high_value:
            return "Priority 1 - High Risk / High Value"
        if high_risk and not high_value:
            return "Priority 2 - High Risk / Medium-Low Value"
        if med_risk and high_value:
            return "Priority 3 - Medium Risk / High Value"
        return "Priority 4 - Low Risk"

    df["retention_priority"] = df.apply(priority, axis=1)
    return df


if __name__ == "__main__":
    print("Loading feature table...")
    df = load_features()
    print(f"Feature table: {df.shape}, churn rate: {df['churn'].mean():.4f}")

    best_model, best_name, comparison_df, fi_df, feature_cols = train_and_evaluate(df)

    print("\nScoring all customers with the selected model...")
    scored = score_all_customers(df, best_model, feature_cols)

    risk_summary = scored["risk_level"].value_counts()
    print("\nRisk tier distribution (all customers):")
    print(risk_summary)

    scored[["customer_id", "churn_probability", "risk_level"]].sort_values(
        "churn_probability", ascending=False
    ).to_csv(MODEL_DIR / "customer_churn_risk.csv", index=False)
    print(f"\nSaved churn risk scores to {MODEL_DIR / 'customer_churn_risk.csv'}")

    # Revenue at risk + retention priority only make sense for currently ACTIVE customers
    active = scored[scored["churn"] == 0].copy()  # churn==0 means their latest subscription is Active
    active_with_value = compute_revenue_at_risk(active)
    active_with_priority = compute_retention_priority(active_with_value)

    total_rar = active_with_value["revenue_at_risk"].sum()
    print(f"\nTotal Revenue at Risk (active customers): ${total_rar:,.2f}")

    priority_cols = ["customer_id", "plan_name", "annualized_value", "churn_probability",
                      "risk_level", "retention_priority"]
    active_with_priority[priority_cols].rename(
        columns={"annualized_value": "annualized_revenue"}
    ).sort_values("churn_probability", ascending=False).to_csv(
        TABLE_DIR / "retention_priority.csv", index=False
    )
    print(f"Saved retention priority list to {TABLE_DIR / 'retention_priority.csv'}")

    print("\nRetention priority distribution:")
    print(active_with_priority["retention_priority"].value_counts())

    # persist key metrics for use in reports (business_insights.md, executive_summary.md, README)
    summary_metrics = {
        "best_model": best_name,
        "model_comparison": comparison_df.to_dict(orient="records"),
        "total_revenue_at_risk": round(float(total_rar), 2),
        "high_risk_customers": int((scored["risk_level"] == "High").sum()),
        "medium_risk_customers": int((scored["risk_level"] == "Medium").sum()),
        "low_risk_customers": int((scored["risk_level"] == "Low").sum()),
        "risk_thresholds": RISK_THRESHOLDS,
    }
    with open(MODEL_DIR / "model_summary.json", "w") as f:
        json.dump(summary_metrics, f, indent=2)
    print(f"\nSaved model summary metrics to {MODEL_DIR / 'model_summary.json'}")
