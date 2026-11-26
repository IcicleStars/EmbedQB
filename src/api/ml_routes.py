# ml_routes.py is the API routing blueprint for ML and dataset management

import os
from flask import Blueprint, jsonify, request, send_file
import analysis
import evaluation
import ml_model
from api.sensor_routes import (
    app_state,
    handle_completed_window,
    recent_after,
    recent_dsp,
    state_lock,
    throw_history,
)

ml_bp = Blueprint("ml_api", __name__)

@ml_bp.route("/api/mode", methods=["POST"])
def set_mode():
    data = request.get_json(force=True)
    with state_lock:
        if "mode" in data:
            app_state["mode"] = data["mode"]
        if "label" in data:
            app_state["label"] = data["label"]
        return jsonify(app_state)

@ml_bp.route("/api/capture-idle", methods=["POST"])
def capture_idle():
    if len(recent_after) < 10:
        return jsonify({"error": "Not enough buffered samples yet. Connect sensor or enable Mock Mode."}), 400
    handle_completed_window(list(recent_after), list(recent_dsp), forced_label="idle")
    return jsonify({"status": "captured", "samples": len(recent_after)})

@ml_bp.route("/api/seed-synthetic", methods=["POST"])
def seed_synthetic():
    ml_model.generate_synthetic_dataset(analysis.CSV_DATASET, n_per_class=25)
    return jsonify({"status": "seeded", "path": analysis.CSV_DATASET})


@ml_bp.route("/api/dataset/download", methods=["GET"])
def download_dataset():
    if not os.path.exists(analysis.CSV_DATASET):
        return jsonify({"error": "No dataset.csv found yet."}), 404
    return send_file(analysis.CSV_DATASET, as_attachment=True, download_name="embedqb_dataset.csv")


@ml_bp.route("/api/dataset/stats", methods=["GET"])
def dataset_stats():
    counts = {}
    if os.path.exists(analysis.CSV_DATASET):
        try:
            _, y, _ = ml_model.load_dataset(analysis.CSV_DATASET)
            for label in y:
                counts[str(label)] = counts.get(str(label), 0) + 1
        except (ValueError, FileNotFoundError):
            pass
    return jsonify({
        "counts": counts,
        "total": sum(counts.values()),
        "model_ready": os.path.exists(ml_model.DEFAULT_MODEL_PATH),
        "state": app_state,
        "history": list(throw_history)[:10],
    })

@ml_bp.route("/api/train", methods=["POST"])
def train():
    try:
        artifact = ml_model.train_model(analysis.CSV_DATASET, ml_model.DEFAULT_MODEL_PATH)
        X, y, rows = ml_model.load_dataset(analysis.CSV_DATASET)
        ev_metrics = evaluation.evaluate_event_detection(rows)
        cv_acc = evaluation.evaluate_ml_classifier(X, y, fig_path=evaluation.FIG_CM)
        return jsonify({
            "classes": artifact["classes"],
            "cv_accuracy": round(cv_acc * 100, 2),
            "event_detection": {k: round(v * 100, 2) for k, v in ev_metrics.items()},
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

@ml_bp.route("/figures/confusion_matrix.png")
def confusion_matrix_img():
    if not os.path.exists(evaluation.FIG_CM):
        return "", 404
    return send_file(evaluation.FIG_CM, mimetype="image/png")