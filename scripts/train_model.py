"""Antreneaza un RandomForest peste Crop_recommendation.csv si salveaza artefactele in data/.

Rulare:
    python -m scripts.train_model
sau:
    python scripts/train_model.py

Output:
    data/agrosmart_model.joblib       - bundle (model + label_encoder + feature_names)
    data/confusion_matrix.png         - matrice confuzie pe test set
    data/feature_importances.png      - importance bar chart
    data/metrics.json                 - {accuracy, f1_macro, top_features, n_classes, n_train, n_test}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CSV_PATH = DATA_DIR / "Crop_recommendation.csv"
MODEL_PATH = DATA_DIR / "agrosmart_model.joblib"
CONFUSION_PATH = DATA_DIR / "confusion_matrix.png"
FEATIMP_PATH = DATA_DIR / "feature_importances.png"
METRICS_PATH = DATA_DIR / "metrics.json"

FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
TARGET = "label"


def main() -> int:
    if not CSV_PATH.exists():
        print(f"[EROARE] Lipseste {CSV_PATH}.")
        print("Descarca: curl -sL -o data/Crop_recommendation.csv \\")
        print('  "https://raw.githubusercontent.com/AbhishekKandoi/Crop-Yield-Prediction-based-on-Indian-Agriculture/main/Crop%20Recommendation%20dataset.csv"')
        return 1

    print(f"[1/6] Citesc dataset: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    print(f"      {len(df)} randuri, {df[TARGET].nunique()} culturi, coloane={list(df.columns)}")

    X = df[FEATURES].values
    y_raw = df[TARGET].values

    le = LabelEncoder()
    y = le.fit_transform(y_raw)

    print("[2/6] Train/test split 80/20 stratified...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("[3/6] Antrenez RandomForest(n_estimators=300)...")
    model = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    print("[4/6] Evaluez pe test set...")
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1m = f1_score(y_test, y_pred, average="macro")
    print(f"      accuracy = {acc:.4f}")
    print(f"      f1_macro = {f1m:.4f}")
    print()
    print(classification_report(y_test, y_pred, target_names=le.classes_, digits=3))

    print(f"[5/6] Generez grafice in {DATA_DIR}/ ...")
    cm = confusion_matrix(y_test, y_pred)
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Greens",
        xticklabels=le.classes_,
        yticklabels=le.classes_,
        cbar=False,
        ax=ax,
    )
    ax.set_xlabel("Prezis")
    ax.set_ylabel("Real")
    ax.set_title(f"Confusion Matrix — accuracy {acc:.3f}")
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(CONFUSION_PATH, dpi=120)
    plt.close()

    importances = model.feature_importances_
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

    print(f"[6/6] Salvez model + metrice in {DATA_DIR}/ ...")
    bundle = {
        "model": model,
        "label_encoder": le,
        "features": FEATURES,
        "version": "1.0.0",
    }
    joblib.dump(bundle, MODEL_PATH)

    top_feats = [
        {"feature": FEATURES[i], "importance": float(importances[i])} for i in order
    ]
    metrics = {
        "accuracy": float(acc),
        "f1_macro": float(f1m),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "n_classes": int(len(le.classes_)),
        "classes": list(le.classes_),
        "top_features": top_feats,
        "model": "RandomForestClassifier(n_estimators=300, random_state=42)",
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2, ensure_ascii=False))

    print()
    print("=" * 60)
    print(f"OK. accuracy={acc:.4f}  f1_macro={f1m:.4f}")
    print(f"Model:    {MODEL_PATH}")
    print(f"Confuzie: {CONFUSION_PATH}")
    print(f"Imp.:     {FEATIMP_PATH}")
    print(f"Metrici:  {METRICS_PATH}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
