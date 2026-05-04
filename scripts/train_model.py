"""Antreneaza 4 modele ML peste Crop_recommendation.csv si salveaza un bundle multi-model.

Rulare:
    python -m scripts.train_model
sau:
    python scripts/train_model.py

Output:
    data/agrosmart_model.joblib    - bundle (toate modelele + label_encoder + features)
    data/confusion_matrix.png      - confuzie pentru cel mai bun model
    data/feature_importances.png   - importance bar chart (RandomForest)
    data/model_comparison.png      - bar chart comparatie acuratete intre modele
    data/metrics.json              - metrici detaliate per model
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CSV_PATH = DATA_DIR / "Crop_recommendation.csv"
MODEL_PATH = DATA_DIR / "agrosmart_model.joblib"
CONFUSION_PATH = DATA_DIR / "confusion_matrix.png"
FEATIMP_PATH = DATA_DIR / "feature_importances.png"
COMPARE_PATH = DATA_DIR / "model_comparison.png"
METRICS_PATH = DATA_DIR / "metrics.json"

FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
TARGET = "label"


def build_models() -> dict:
    """Returneaza dict de {nume: estimator} cu 4 modele diverse."""
    return {
        "RandomForest": RandomForestClassifier(
            n_estimators=300, random_state=42, n_jobs=-1
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=200, random_state=42, max_depth=4
        ),
        "ExtraTrees": ExtraTreesClassifier(
            n_estimators=300, random_state=42, n_jobs=-1
        ),
        "LogisticRegression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000, random_state=42, n_jobs=-1)),
        ]),
    }


def main() -> int:
    if not CSV_PATH.exists():
        print(f"[EROARE] Lipseste {CSV_PATH}.")
        print("Descarca: curl -sL -o data/Crop_recommendation.csv \\")
        print('  "https://raw.githubusercontent.com/AbhishekKandoi/Crop-Yield-Prediction-based-on-Indian-Agriculture/main/Crop%20Recommendation%20dataset.csv"')
        return 1

    print(f"[1/6] Citesc dataset: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    print(f"      {len(df)} randuri, {df[TARGET].nunique()} culturi")

    X = df[FEATURES].values
    y_raw = df[TARGET].values
    le = LabelEncoder()
    y = le.fit_transform(y_raw)

    print("[2/6] Train/test split 80/20 stratified...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("[3/6] Antrenez 4 modele...")
    models = build_models()
    results: dict[str, dict] = {}
    trained: dict[str, object] = {}

    for name, est in models.items():
        t0 = time.time()
        est.fit(X_train, y_train)
        train_time = time.time() - t0

        t0 = time.time()
        y_pred = est.predict(X_test)
        infer_time = (time.time() - t0) / len(X_test) * 1000  # ms per sample

        acc = accuracy_score(y_test, y_pred)
        f1m = f1_score(y_test, y_pred, average="macro")

        results[name] = {
            "accuracy": float(acc),
            "f1_macro": float(f1m),
            "train_time_s": round(train_time, 3),
            "inference_ms_per_sample": round(infer_time, 4),
        }
        trained[name] = est
        print(f"      {name:20s}  acc={acc:.4f}  f1={f1m:.4f}  train={train_time:.2f}s")

    best_name = max(results, key=lambda k: results[k]["accuracy"])
    print(f"      → Best: {best_name} ({results[best_name]['accuracy']:.4f})")

    print("[4/6] Generez grafice...")
    # Confusion matrix pentru best model
    best_pred = trained[best_name].predict(X_test)
    cm = confusion_matrix(y_test, best_pred)
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Greens",
        xticklabels=le.classes_, yticklabels=le.classes_,
        cbar=False, ax=ax,
    )
    ax.set_xlabel("Prezis")
    ax.set_ylabel("Real")
    ax.set_title(f"Confusion Matrix — {best_name} (acc={results[best_name]['accuracy']:.3f})")
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(CONFUSION_PATH, dpi=120)
    plt.close()

    # Feature importances (din RandomForest, daca exista)
    rf = trained.get("RandomForest")
    if rf is not None and hasattr(rf, "feature_importances_"):
        importances = rf.feature_importances_
        order = np.argsort(importances)[::-1]
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.barplot(
            x=importances[order],
            y=[FEATURES[i] for i in order],
            palette="viridis",
            ax=ax,
        )
        ax.set_title("Feature importances — RandomForest")
        ax.set_xlabel("Importance")
        plt.tight_layout()
        plt.savefig(FEATIMP_PATH, dpi=120)
        plt.close()

    # Model comparison chart
    names = list(results.keys())
    accs = [results[n]["accuracy"] for n in names]
    f1s = [results[n]["f1_macro"] for n in names]
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(names))
    w = 0.35
    ax.bar(x - w / 2, accs, w, label="Accuracy", color="#2C5F2D")
    ax.bar(x + w / 2, f1s, w, label="F1 macro", color="#97BC62")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=15)
    ax.set_ylim(0.85, 1.005)
    ax.set_ylabel("Scor")
    ax.set_title("Comparatie modele ML — AgroSmart AI")
    ax.legend()
    for i, (a, f) in enumerate(zip(accs, f1s)):
        ax.text(i - w / 2, a + 0.002, f"{a:.3f}", ha="center", fontsize=9)
        ax.text(i + w / 2, f + 0.002, f"{f:.3f}", ha="center", fontsize=9)
    plt.tight_layout()
    plt.savefig(COMPARE_PATH, dpi=120)
    plt.close()

    print("[5/6] Salvez bundle multi-model...")
    bundle = {
        "models": trained,
        "label_encoder": le,
        "features": FEATURES,
        "best_model": best_name,
        "version": "2.0.0-multi",
        "metrics": results,
    }
    joblib.dump(bundle, MODEL_PATH)

    # feature importances pentru top features
    if rf is not None:
        order = np.argsort(rf.feature_importances_)[::-1]
        top_feats = [
            {"feature": FEATURES[i], "importance": float(rf.feature_importances_[i])}
            for i in order
        ]
    else:
        top_feats = []

    metrics = {
        "best_model": best_name,
        "accuracy": results[best_name]["accuracy"],
        "f1_macro": results[best_name]["f1_macro"],
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "n_classes": int(len(le.classes_)),
        "classes": list(le.classes_),
        "top_features": top_feats,
        "models": results,
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2, ensure_ascii=False))

    print("[6/6] Sumar:")
    print(json.dumps(results, indent=2))
    print(f"Best: {best_name} → acc={results[best_name]['accuracy']:.4f}")
    print(f"Salvat in {MODEL_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
