"""Train the real UK repeat-purchase benchmark and separate sandbox choice models."""
import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, f1_score, log_loss, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from download_datasets import ROOT, update

sys.path.insert(0, str(ROOT / "ml-engine"))
from demandtwin_ml.choice import train
from demandtwin_ml.synthetic import sample

ARTIFACTS = ROOT / "artifacts"
RESULTS = ROOT / "research/results"
SEED = 42


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def track(name, data, artifact_paths):
    try:
        import mlflow
    except ImportError:
        print("MLflow unavailable. JSON run metadata was saved.")
        return
    (ROOT / "data/runtime").mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI") or f"sqlite:///{(ROOT / 'data/runtime/mlflow.db').as_posix()}")
    mlflow.set_experiment(name)
    for model, metrics in data["metrics"].items():
        with mlflow.start_run(run_name=model):
            mlflow.log_params({"seed": SEED, "dataset_version": data["dataset_version"], "model": model})
            mlflow.log_metrics({key: value for key, value in metrics.items() if isinstance(value, (int, float))})
            for path in artifact_paths:
                mlflow.log_artifact(str(path))


def snapshot(frame, date):
    cutoff = pd.Timestamp(date)
    previous = frame.loc[frame.InvoiceDate.between(cutoff - pd.Timedelta(days=90), cutoff, inclusive="left")]
    future = frame.loc[frame.InvoiceDate.between(cutoff, cutoff + pd.Timedelta(days=30), inclusive="left")]
    grouped = previous.groupby("CustomerID")
    features = grouped.agg(invoices=("InvoiceNo", "nunique"), stock_codes=("StockCode", "nunique"),
                           units=("Quantity", "sum"), spend_gbp=("gross_line_gbp", "sum"), latest=("InvoiceDate", "max"))
    features["recency_days"] = (cutoff - features.pop("latest")).dt.total_seconds() / 86400
    y = features.index.isin(future.CustomerID).astype(int)
    return np.log1p(features), y


def fingerprint(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def retail():
    path = ROOT / "data/processed/uk_retail_purchases.parquet"
    lines = pd.read_parquet(path)
    x_train, y_train = snapshot(lines, "2011-08-01")
    x_test, y_test = snapshot(lines, "2011-10-01")
    ids = sorted(set(x_train.index) | set(x_test.index))
    held_out = set(np.random.default_rng(SEED).permutation(ids)[:len(ids) // 4])
    train_mask, test_mask = ~x_train.index.isin(held_out), x_test.index.isin(held_out)
    x_train, y_train = x_train.loc[train_mask], y_train[train_mask]
    x_test, y_test = x_test.loc[test_mask], y_test[test_mask]
    models = {
        "logistic_regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=SEED)),
        "random_forest": RandomForestClassifier(n_estimators=250, min_samples_leaf=12, n_jobs=2, random_state=SEED),
        "xgboost": XGBClassifier(n_estimators=180, max_depth=3, learning_rate=0.035, subsample=0.9, n_jobs=2, random_state=SEED),
    }
    metrics = {}
    artifacts = []
    for name, model in models.items():
        model.fit(x_train, y_train)
        probability = model.predict_proba(x_test)[:, 1]
        label = probability >= 0.5
        fraction, confidence = calibration_curve(y_test, probability, n_bins=10)
        metrics[name] = {
            "accuracy": accuracy_score(y_test, label), "precision": precision_score(y_test, label),
            "recall": recall_score(y_test, label), "f1": f1_score(y_test, label),
            "roc_auc": roc_auc_score(y_test, probability), "log_loss": log_loss(y_test, probability),
            "brier": brier_score_loss(y_test, probability),
            "calibration": [{"confidence": float(p), "observed": float(y)} for p, y in zip(confidence, fraction, strict=True)],
        }
        artifact = ARTIFACTS / "retail" / (name + ".joblib")
        artifact.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, artifact)
        artifacts.append(artifact)
    if os.getenv("DEMANDTWIN_SHAP") == "1":
        import shap
        explanation = shap.TreeExplainer(models["xgboost"])(x_test)
        write_json(RESULTS / "uk_retail_shap.json", {
            "model": "xgboost", "population": "UK benchmark holdout", "units": "raw log-odds",
            "mean_absolute_contribution": dict(zip(x_test.columns, np.abs(explanation.values).mean(axis=0).tolist(), strict=True)),
        })
    result = {
        "dataset_version": fingerprint(ROOT / "data/raw/online_retail/online_retail.zip"),
        "data_snapshot_sha256": fingerprint(path),
        "source": "UCI Online Retail, CC BY 4.0", "target": "any observed invoice in next 30 days",
        "split": "disjoint customers, 2011-08-01 train snapshot and 2011-10-01 test snapshot; 90-day lookback",
        "train_n": len(y_train), "test_n": len(y_test), "train_positive_rate": float(y_train.mean()),
        "test_positive_rate": float(y_test.mean()), "metrics": metrics, "seed": SEED,
        "features": x_train.columns.tolist(), "feature_version": "retail-repeat-v1",
        "model_config": {name: {key: value for key, value in model.get_params().items() if isinstance(value, (str, int, float, bool)) and (not isinstance(value, float) or np.isfinite(value))} for name, model in models.items()},
        "artifacts": [path.relative_to(ROOT).as_posix() for path in artifacts],
        "software_versions": {pkg: version(pkg) for pkg in ("scikit-learn", "xgboost", "pandas")},
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    report = RESULTS / "uk_retail_benchmark.json"
    write_json(report, result)
    track("DemandTwin / UK retail benchmark", result, [report, *artifacts])


def sandbox():
    rows = sample()
    path = ROOT / "data/synthetic/choices.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps({"synthetic": True, "evidence_type": "hypothetical_choice", **asdict(row)}) + "\n")
    update("synthetic", bytes=path.stat().st_size, records=len(rows), columns=6, sha256=fingerprint(path),
           dtypes={"synthetic": "boolean", "evidence_type": "string", "participant": "string",
                   "segment": "string", "alternatives": "array", "chosen": "integer"}, missing={})
    artifact, result = train(rows, SEED)
    result.update(synthetic=True, dataset_version=fingerprint(path), feature_version=artifact["feature_version"],
                  artifact="artifacts/choice/synthetic_model.json", trained_at=datetime.now(timezone.utc).isoformat(),
                  software_versions={pkg: version(pkg) for pkg in ("numpy", "scipy")})
    artifact_path, report = ARTIFACTS / "choice/synthetic_model.json", RESULTS / "sandbox_choice_benchmark.json"
    write_json(artifact_path, artifact)
    write_json(report, result)
    track("DemandTwin / synthetic choice", result, [report, artifact_path])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", default="all", choices=["all", "retail", "sandbox"])
    selection = parser.parse_args().track
    if selection in {"all", "retail"}:
        retail()
    if selection in {"all", "sandbox"}:
        sandbox()
