import argparse
import csv
import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Directory Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")
MODEL_DIR = os.path.join(BASE_DIR, "../models")
os.makedirs(MODEL_DIR, exist_ok=True)

# Dataset Path
DEFAULT_DATASET = os.path.join(DATA_DIR, "dataset.csv")
DEFAULT_MODEL_PATH = os.path.join(MODEL_DIR, "throw_classifier.joblib")

FEATURE_COLUMNS = [
    "duration_ms",
    "peak_angular_velocity_dps",
    "deceleration_slope_dps2",
    "cross_axis_variance",
    "peak_accel_g",
    "peak_energy",
]

def load_dataset(dataset_path=DEFAULT_DATASET):
    """Loads feature matrix X and string labels y from data/dataset.csv."""
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found at {dataset_path}. Record trials with analysis.py --label first.")

    X, y, rows = [], [], []
    with open(dataset_path, mode="r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                features = [float(row[col]) for col in FEATURE_COLUMNS]
                label = row["label"].strip()
                if not label:
                    continue
                X.append(features)
                y.append(label)
                rows.append(row)
            except (KeyError, ValueError):
                continue

    if not X:
        raise ValueError(f"No valid training rows found in {dataset_path}.")

    return np.array(X, dtype=float), np.array(y, dtype=str), rows


def generate_synthetic_dataset(output_path=DEFAULT_DATASET, n_per_class=25, seed=42):
    """Generates a synthetic dataset for pipeline testing prior to hip-mounted data collection."""
    rng = np.random.default_rng(seed)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fieldnames = [
        "recorded_at", "label", "trial_file", "event_id", "start_ms", "end_ms",
        "duration_ms", "peak_angular_velocity_dps", "deceleration_slope_dps2",
        "cross_axis_variance", "peak_accel_g", "peak_energy", "threshold_triggered",
    ]

    profiles = {
        # Goof form detected by strong, clean hip rotation with sharp follow-through and low off-axis wobble
        "good_form": {
            "duration_ms": (380, 45),
            "peak_angular_velocity_dps": (520, 55),
            "deceleration_slope_dps2": (-1450, 200),
            "cross_axis_variance": (4200, 900),
            "peak_accel_g": (6.2, 0.8),
            "peak_energy": (480, 75),
            "triggered": 1,
        },
        # Poor form detected by arm-dominant / poor hip rotation: lower angular velocity, higher off-axis variance
        "bad_form": {
            "duration_ms": (520, 80),
            "peak_angular_velocity_dps": (280, 50),
            "deceleration_slope_dps2": (-650, 180),
            "cross_axis_variance": (11500, 2200),
            "peak_accel_g": (3.8, 0.7),
            "peak_energy": (185, 55),
            "triggered": 1,
        },
        # Resting or walking movement
        "idle": {
            "duration_ms": (950, 100),
            "peak_angular_velocity_dps": (45, 20),
            "deceleration_slope_dps2": (-40, 25),
            "cross_axis_variance": (250, 120),
            "peak_accel_g": (1.15, 0.12),
            "peak_energy": (20.5, 2.5),
            "triggered": 0,
        },
    }

    with open(output_path, mode="w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for label, p in profiles.items():
            for idx in range(n_per_class):
                duration = max(50.0, float(rng.normal(*p["duration_ms"])))
                writer.writerow({
                    "recorded_at": "2026-11-21T00:00:00",
                    "label": label,
                    "trial_file": f"synthetic_{label}_{idx}.csv",
                    "event_id": 1,
                    "start_ms": 0.0,
                    "end_ms": round(duration, 2),
                    "duration_ms": round(duration, 2),
                    "peak_angular_velocity_dps": round(max(5.0, float(rng.normal(*p["peak_angular_velocity_dps"]))), 3),
                    "deceleration_slope_dps2": round(float(rng.normal(*p["deceleration_slope_dps2"])), 3),
                    "cross_axis_variance": round(max(10.0, float(rng.normal(*p["cross_axis_variance"]))), 3),
                    "peak_accel_g": round(max(0.5, float(rng.normal(*p["peak_accel_g"]))), 3),
                    "peak_energy": round(max(1.0, float(rng.normal(*p["peak_energy"]))), 3),
                    "threshold_triggered": p["triggered"],
                })

    print(f"Generated synthetic dataset ({n_per_class * len(profiles)} rows) at {output_path}")

# method for TRAINING MODEL !
def train_model(dataset_path=DEFAULT_DATASET, model_path=DEFAULT_MODEL_PATH):
    """Trains and serializes the Random Forest form classifier."""
    X, y, _ = load_dataset(dataset_path)
    unique_classes = np.unique(y)
    if len(unique_classes) < 2:
        raise ValueError(f"Need at least 2 distinct labels to train; found only: {unique_classes.tolist()}")

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, class_weight="balanced")),
    ])
    pipeline.fit(X, y)

    artifact = {
        "pipeline": pipeline,
        "feature_columns": FEATURE_COLUMNS,
        "classes": pipeline.classes_.tolist(),
    }
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(artifact, model_path)
    print(f"Trained model on {len(X)} samples across classes {artifact['classes']} -> saved to {model_path}")
    return artifact

# Method for generating feedback for user
def generate_coaching_feedback(label, metrics):
    """Produces an immediate, actionable form cue based on extracted throw metrics."""
    if label == "idle":
        return "No active throw detected."
    if label == "good_form":
        return "Strong, consistent hip rotation and controlled follow-through."

    cues = []
    if float(metrics.get("peak_angular_velocity_dps", 0.0)) < 350.0:
        cues.append("Low peak hip velocity—drive your hips through faster before arm release.")
    if float(metrics.get("cross_axis_variance", 0.0)) > 8500.0:
        cues.append("High off-axis wobble—keep your torso level during rotation.")
    if float(metrics.get("deceleration_slope_dps2", 0.0)) > -800.0:
        cues.append("Gradual deceleration—focus on a firmer plant leg to transfer torque.")

    return " ".join(cues) if cues else "Inconsistent hip mechanics detected—review rotation timing."

def predict_throw(metrics, model_path=DEFAULT_MODEL_PATH):
    """Predicts throwing form class, confidence, and coaching cue for a single event dict."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Trained model not found at {model_path}. Run src/ml_model.py first.")

    artifact = joblib.load(model_path)
    pipeline = artifact["pipeline"]
    feature_vec = np.array([[float(metrics.get(col, 0.0)) for col in artifact["feature_columns"]]], dtype=float)

    pred_label = str(pipeline.predict(feature_vec)[0])
    probs = pipeline.predict_proba(feature_vec)[0]
    confidence = float(np.max(probs))

    return {
        "predicted_label": pred_label,
        "confidence": round(confidence, 4),
        "feedback": generate_coaching_feedback(pred_label, metrics),
    }

# Main Method
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train EmbedQB Hip Rotation Form Classifier")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Path to labeled dataset.csv")
    parser.add_argument("--model-out", default=DEFAULT_MODEL_PATH, help="Output path for trained .joblib model")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Generate a synthetic dataset before training (for testing without hardware)",
    )
    args = parser.parse_args()

    if args.synthetic:
        generate_synthetic_dataset(args.dataset)

    train_model(args.dataset, args.model_out)