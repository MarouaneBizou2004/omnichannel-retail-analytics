"""
Machine Learning Training & Optimization Engine
Trains, benchmarks, tunes, and evaluates customer churn prediction models.
Implements strict stratified splitting, PR-AUC / ROC-AUC prioritization,
permutation feature importance, and financial ROI decision threshold optimization.
"""

import sys
from pathlib import Path
import json
import logging
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate, GridSearchCV
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    brier_score_loss,
    confusion_matrix,
    classification_report,
    precision_recall_curve,
    roc_curve
)
from sklearn.inspection import permutation_importance

# Ensure project root is in sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    PROCESSED_DATA_DIR,
    MODELS_DIR,
    FIGURES_DIR,
    REPORTS_DIR,
    RANDOM_SEED,
    RETENTION_CAMPAIGN_COST_PER_CUSTOMER,
    AVERAGE_CUSTOMER_MARGIN_REVENUE,
    SUCCESSFUL_RETENTION_RATE
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MLTrainingEngine")

class ChurnModelTrainer:
    def __init__(self):
        self.data_path = PROCESSED_DATA_DIR / "customer_features_churn.parquet"
        self.models_dir = MODELS_DIR
        self.figures_dir = FIGURES_DIR
        self.reports_dir = REPORTS_DIR
        self.seed = RANDOM_SEED
        
        # Define feature taxonomy
        self.num_features = [
            "age", "tenure_days", "recency_days", "frequency",
            "total_net_spend", "avg_order_value", "max_order_value",
            "total_gross_profit", "total_items", "avg_items_per_order",
            "avg_discount_received", "return_rate", "cancellation_rate",
            "orders_last_30d", "orders_last_90d", "order_velocity_ratio",
            "distinct_categories", "gross_margin_ratio"
        ]
        
        self.cat_features = [
            "region", "acquisition_channel", "loyalty_tier",
            "primary_channel", "primary_payment", "income_bracket"
        ]
        
        self.target = "churn_90d"

    def load_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Loads feature matrix and isolates target."""
        logger.info(f"Loading feature dataset from {self.data_path}...")
        df = pd.read_parquet(self.data_path)
        
        X = df[self.num_features + self.cat_features]
        y = df[self.target]
        return X, y

    def build_preprocessor(self) -> ColumnTransformer:
        """Constructs scikit-learn ColumnTransformer for numerical and categorical pipelines."""
        num_transformer = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler())
        ])
        
        cat_transformer = Pipeline([
            ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
            ("encoder", OneHotEncoder(drop="first", handle_unknown="ignore", sparse_output=False))
        ])
        
        preprocessor = ColumnTransformer(
            transformers=[
                ("num", num_transformer, self.num_features),
                ("cat", cat_transformer, self.cat_features)
            ]
        )
        return preprocessor

    def benchmark_models(self, X_train: pd.DataFrame, y_train: pd.Series) -> Dict[str, Dict[str, float]]:
        """
        Cross-validates 4 candidate architectures across multiple business metrics:
        Dummy Baseline, Logistic Regression, Random Forest, HistGradientBoosting.
        """
        logger.info("Executing 5-Fold Stratified Cross-Validation Benchmark...")
        preprocessor = self.build_preprocessor()
        
        candidates = {
            "Baseline (Dummy)": DummyClassifier(strategy="stratified", random_state=self.seed),
            "Logistic Regression": LogisticRegression(class_weight="balanced", max_iter=1000, random_state=self.seed),
            "Random Forest": RandomForestClassifier(n_estimators=150, max_depth=7, class_weight="balanced", min_samples_leaf=4, random_state=self.seed),
            "Gradient Boosting": HistGradientBoostingClassifier(class_weight="balanced", max_iter=150, max_depth=5, learning_rate=0.05, random_state=self.seed)
        }
        
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.seed)
        scoring = ["roc_auc", "average_precision", "f1", "precision", "recall"]
        
        benchmark_results = {}
        for name, model in candidates.items():
            pipe = Pipeline([
                ("preprocessor", preprocessor),
                ("classifier", model)
            ])
            cv_out = cross_validate(pipe, X_train, y_train, cv=cv, scoring=scoring, n_jobs=-1)
            
            benchmark_results[name] = {
                "roc_auc_mean": round(float(np.mean(cv_out["test_roc_auc"])), 4),
                "roc_auc_std": round(float(np.std(cv_out["test_roc_auc"])), 4),
                "pr_auc_mean": round(float(np.mean(cv_out["test_average_precision"])), 4),
                "pr_auc_std": round(float(np.std(cv_out["test_average_precision"])), 4),
                "f1_mean": round(float(np.mean(cv_out["test_f1"])), 4),
                "precision_mean": round(float(np.mean(cv_out["test_precision"])), 4),
                "recall_mean": round(float(np.mean(cv_out["test_recall"])), 4)
            }
            logger.info(f"[{name}] ROC-AUC: {benchmark_results[name]['roc_auc_mean']:.4f} | PR-AUC: {benchmark_results[name]['pr_auc_mean']:.4f} | F1: {benchmark_results[name]['f1_mean']:.4f}")
            
        return benchmark_results

    def tune_champion_model(self, X_train: pd.DataFrame, y_train: pd.Series) -> Pipeline:
        """Fine-tunes the champion Gradient Boosting architecture using Grid Search CV."""
        logger.info("Tuning champion Gradient Boosting model with GridSearchCV...")
        preprocessor = self.build_preprocessor()
        
        base_pipe = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", HistGradientBoostingClassifier(class_weight="balanced", random_state=self.seed))
        ])
        
        param_grid = {
            "classifier__max_iter": [100, 150, 200],
            "classifier__learning_rate": [0.03, 0.05, 0.1],
            "classifier__max_depth": [4, 6, 8],
            "classifier__l2_regularization": [0.0, 1.0, 5.0]
        }
        
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.seed)
        grid_search = GridSearchCV(
            base_pipe,
            param_grid=param_grid,
            cv=cv,
            scoring="average_precision", # Optimize PR-AUC
            n_jobs=-1,
            verbose=0
        )
        grid_search.fit(X_train, y_train)
        
        logger.info(f"Best CV PR-AUC Score: {grid_search.best_score_:.4f}")
        logger.info(f"Best Hyperparameters: {grid_search.best_params_}")
        return grid_search.best_estimator_

    def evaluate_test_set(
        self,
        model: Pipeline,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Dict[str, Any]:
        """Evaluates tuned model on holdout test set across all standard and financial metrics."""
        logger.info("Evaluating champion model on holdout test set...")
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        y_pred_default = (y_pred_proba >= 0.5).astype(int)
        
        roc_auc = float(roc_auc_score(y_test, y_pred_proba))
        pr_auc = float(average_precision_score(y_test, y_pred_proba))
        f1 = float(f1_score(y_test, y_pred_default))
        prec = float(precision_score(y_test, y_pred_default))
        rec = float(recall_score(y_test, y_pred_default))
        brier = float(brier_score_loss(y_test, y_pred_proba))
        cm = confusion_matrix(y_test, y_pred_default).tolist()
        
        test_metrics = {
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
            "f1_score_at_0.5": round(f1, 4),
            "precision_at_0.5": round(prec, 4),
            "recall_at_0.5": round(rec, 4),
            "brier_score": round(brier, 4),
            "confusion_matrix_at_0.5": cm
        }
        
        logger.info(f"Test Set ROC-AUC: {roc_auc:.4f} | PR-AUC: {pr_auc:.4f} | F1: {f1:.4f} | Recall: {rec:.4f}")
        return test_metrics

    def plot_feature_importance(self, model: Pipeline, X_test: pd.DataFrame, y_test: pd.Series) -> None:
        """Computes and plots Permutation Feature Importance on holdout set."""
        logger.info("Computing Permutation Feature Importance...")
        perm_res = permutation_importance(
            model, X_test, y_test,
            n_repeats=10,
            random_state=self.seed,
            scoring="average_precision",
            n_jobs=-1
        )
        
        feature_names = self.num_features + self.cat_features
        importances_mean = perm_res.importances_mean
        
        df_imp = pd.DataFrame({
            "feature": feature_names,
            "importance": importances_mean
        }).sort_values(by="importance", ascending=True).tail(15)
        
        plt.figure(figsize=(10, 6))
        plt.barh(df_imp["feature"], df_imp["importance"], color="#2563EB", alpha=0.9)
        plt.xlabel("Permutation Importance (Drop in PR-AUC / Average Precision)", fontweight="bold")
        plt.title("Top 15 Predictive Churn Drivers (Permutation Importance)", pad=15)
        plt.tight_layout()
        
        out_path = self.figures_dir / "07_model_feature_importance.png"
        plt.savefig(out_path)
        plt.close()
        logger.info(f"Saved feature importance figure to {out_path}")

    def optimize_decision_threshold(
        self,
        model: Pipeline,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Dict[str, Any]:
        """
        Calculates expected financial ROI across decision thresholds t in [0.05, 0.95].
        Connects technical probabilities to actual business dollar value.
        """
        logger.info("Optimizing decision threshold for maximum retention net profit...")
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        thresholds = np.linspace(0.05, 0.95, 91)
        profits = []
        precisions = []
        recalls = []
        f1s = []
        
        cost_per_outreach = RETENTION_CAMPAIGN_COST_PER_CUSTOMER
        margin_recovered = AVERAGE_CUSTOMER_MARGIN_REVENUE
        accept_rate = SUCCESSFUL_RETENTION_RATE
        
        for t in thresholds:
            pred = (y_pred_proba >= t).astype(int)
            tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()
            
            # Net profit formula:
            # Value generated from true churners successfully saved:
            # TP * accept_rate * margin_recovered
            # Minus campaign cost spent on all targeted individuals (TP + FP):
            # (TP + FP) * cost_per_outreach
            total_targeted = tp + fp
            gross_benefit = tp * accept_rate * margin_recovered
            total_cost = total_targeted * cost_per_outreach
            net_profit = gross_benefit - total_cost
            
            profits.append(net_profit)
            precisions.append(precision_score(y_test, pred, zero_division=0))
            recalls.append(recall_score(y_test, pred, zero_division=0))
            f1s.append(f1_score(y_test, pred, zero_division=0))
            
        optimal_idx = int(np.argmax(profits))
        optimal_t = float(thresholds[optimal_idx])
        max_profit = float(profits[optimal_idx])
        profit_at_05 = float(profits[int(np.where(np.isclose(thresholds, 0.50))[0][0])])
        
        # Scaling to full annual customer base (x5 since test set is 20%)
        annual_scaled_profit = max_profit * 5.0
        annual_lift_over_default = (max_profit - profit_at_05) * 5.0
        
        # Plot Threshold Curve
        fig, ax1 = plt.subplots(figsize=(11, 5.5))
        
        color_profit = "#059669"
        ax1.plot(thresholds, profits, color=color_profit, linewidth=3, label="Net Retention Profit ($)")
        ax1.axvline(optimal_t, color="#DC2626", linestyle="--", linewidth=1.5, label=f"Optimal Threshold (t* = {optimal_t:.2f})")
        ax1.axvline(0.50, color="#94A3B8", linestyle=":", linewidth=1.5, label="Default Threshold (t = 0.50)")
        ax1.set_xlabel("Classification Decision Threshold (t)", fontweight="bold")
        ax1.set_ylabel("Net Campaign Profit on Test Cohort ($)", color=color_profit, fontweight="bold")
        ax1.tick_params(axis="y", labelcolor=color_profit)
        
        # Twin axis for Precision and Recall
        ax2 = ax1.twinx()
        ax2.plot(thresholds, precisions, color="#2563EB", linestyle="-.", label="Precision")
        ax2.plot(thresholds, recalls, color="#D97706", linestyle="--", label="Recall")
        ax2.set_ylabel("Metric Rate (0.0 to 1.0)", fontweight="bold")
        ax2.set_ylim(0, 1.05)
        ax2.grid(False)
        
        # Annotate peak
        ax1.annotate(f"Maximum Profit: ${max_profit:,.0f}\n(Annual Enterprise Value: ~${annual_scaled_profit:,.0f})",
                     xy=(optimal_t, max_profit),
                     xytext=(optimal_t - 0.25, max_profit - 2000),
                     arrowprops=dict(facecolor="#059669", shrink=0.08, width=1.5, headwidth=6),
                     fontsize=9, fontweight="bold", backgroundcolor="#ECFDF5")
        
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="lower left")
        
        plt.title("Retention Campaign Net Profit & Tradeoff vs Decision Threshold", pad=15)
        fig.tight_layout()
        out_path = self.figures_dir / "08_business_profit_threshold_curve.png"
        plt.savefig(out_path)
        plt.close()
        logger.info(f"Saved threshold optimization plot to {out_path}")
        
        threshold_summary = {
            "optimal_threshold": round(optimal_t, 2),
            "max_profit_test_cohort": round(max_profit, 2),
            "profit_at_default_05": round(profit_at_05, 2),
            "annual_scaled_net_profit": round(annual_scaled_profit, 2),
            "annual_lift_over_default": round(annual_lift_over_default, 2),
            "precision_at_optimal": round(float(precisions[optimal_idx]), 4),
            "recall_at_optimal": round(float(recalls[optimal_idx]), 4),
            "f1_at_optimal": round(float(f1s[optimal_idx]), 4)
        }
        return threshold_summary

    def run(self) -> None:
        print("=" * 60)
        print("Starting Machine Learning Pipeline & Optimization")
        print("=" * 60)
        
        X, y = self.load_data()
        
        # Stratified 80/20 train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, stratify=y, random_state=self.seed
        )
        logger.info(f"Train set: {len(X_train):,} samples | Test set: {len(X_test):,} samples")
        
        # 1. Benchmark Candidate Models
        benchmark_results = self.benchmark_models(X_train, y_train)
        
        # 2. Hyperparameter Tuning on Champion Model
        champion_pipeline = self.tune_champion_model(X_train, y_train)
        
        # 3. Test Set Evaluation
        test_metrics = self.evaluate_test_set(champion_pipeline, X_test, y_test)
        
        # 4. Permutation Feature Importance
        self.plot_feature_importance(champion_pipeline, X_test, y_test)
        
        # 5. Financial Decision Threshold Optimization
        roi_results = self.optimize_decision_threshold(champion_pipeline, X_test, y_test)
        
        # 6. Save Model Artifacts
        model_save_path = self.models_dir / "churn_pipeline.joblib"
        joblib.dump(champion_pipeline, model_save_path)
        logger.info(f"Saved trained production model pipeline to: {model_save_path}")
        
        # 7. Save Consolidated Metrics JSON
        full_evaluation_payload = {
            "cross_validation_benchmark": benchmark_results,
            "holdout_test_metrics": test_metrics,
            "business_threshold_optimization": roi_results,
            "features_used": {
                "numerical": self.num_features,
                "categorical": self.cat_features
            }
        }
        metrics_file = self.reports_dir / "model_evaluation_metrics.json"
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(full_evaluation_payload, f, indent=4)
        logger.info(f"Exported complete evaluation report to: {metrics_file}")
        
        print("=" * 60)
        print("Machine Learning Pipeline Completed Successfully!")
        print(f"Champion Test PR-AUC: {test_metrics['pr_auc']:.4f}")
        print(f"Optimal Threshold: {roi_results['optimal_threshold']} -> Annual Profit: ${roi_results['annual_scaled_net_profit']:,.0f}")
        print("=" * 60)

if __name__ == "__main__":
    trainer = ChurnModelTrainer()
    trainer.run()
