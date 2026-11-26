# evaluation.py acts as the event detection and classifier evaluation suite \ 
# The file measures accuracy, precision, F1, and runs stratified k-fold \ 
# cross-validation on the Random Forest classfiers.
import argparse
import os
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml_model import DEFAULT_DATASET, load_dataset

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURE_DIR = os.path.join(BASE_DIR, "../figures")
os.makedirs(FIGURE_DIR, exist_ok=True)
FIG_CM = os.path.join(FIGURE_DIR, "confusion_matrix.png")


def evaluate_event_detection(rows):
    """Evaluates on-device threshold event detection against ground-truth labels (idle=0, throw=1)."""
    y_true = [0 if r["label"].strip().lower() == "idle" else 1 for r in rows]
    y_pred = [int(float(r.get("threshold_triggered", 0))) for r in rows]

    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    print("=== Event Detection Accuracy (On-Device Threshold) ===")
    print(f"Accuracy:  {acc * 100:.2f}%")
    print(f"Precision: {prec * 100:.2f}%")
    print(f"Recall:    {rec * 100:.2f}%")
    print(f"F1-Score:  {f1 * 100:.2f}%\n")
    return {"accuracy": acc, "precision": prec, "recall": rec, "f1": f1}


def evaluate_ml_classifier(X, y, fig_path=FIG_CM):
    """Runs stratified k-fold CV for ML Classification Accuracy and saves a confusion matrix."""
    classes, counts = np.unique(y, return_counts=True)
    min_class_count = int(np.min(counts))
    n_splits = min(5, min_class_count)

    if n_splits < 2:
        raise ValueError(
            f"Need at least 2 samples per class for cross-validation; class counts: {dict(zip(classes, counts))}"
        )

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, class_weight="balanced")),
    ])

    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    y_pred = cross_val_predict(pipeline, X, y, cv=cv)

    acc = accuracy_score(y, y_pred)
    print(f"=== ML Classification Accuracy ({n_splits}-Fold Stratified CV) ===")
    print(f"Overall Accuracy: {acc * 100:.2f}%\n")
    print(classification_report(y, y_pred, zero_division=0))

    cm = confusion_matrix(y, y_pred, labels=classes)
    fig, ax = plt.subplots(figsize=(6, 5))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=classes)
    disp.plot(ax=ax, cmap="Blues", colorbar=False)
    ax.set_title(f"EmbedQB Form Classifier ({n_splits}-Fold CV: {acc * 100:.1f}%)")
    plt.tight_layout()
    plt.savefig(fig_path, dpi=300)
    plt.close()
    print(f"Saved confusion matrix to {fig_path}")
    return acc

# Main Method
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate EmbedQB Event Detection and ML Classifier")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Path to labeled dataset.csv")
    parser.add_argument("--fig-out", default=FIG_CM, help="Output path for confusion matrix PNG")
    args = parser.parse_args()

    X, y, rows = load_dataset(args.dataset)
    evaluate_event_detection(rows)
    evaluate_ml_classifier(X, y, fig_path=args.fig_out)