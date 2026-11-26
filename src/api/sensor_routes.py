import asyncio
import collections
import json
import math
import os
import queue
import random
import threading
import time

from flask import Blueprint, Response, jsonify, request
import serial
from serial.tools import list_ports

import analysis
import ml_model

try:
    from bleak import BleakScanner
    BLE_AVAILABLE = True
except ImportError:
    BLE_AVAILABLE = False

sensor_bp = Blueprint("sensor_api", __name__)

# Shared runtime state (imported by ml_routes.py)
state_lock = threading.Lock()
app_state = {
    "mode": "monitor",
    "label": "good_form",
    "source": "disconnected",
    "device": None,
    "mock_profile": "mixed",
}

# Rolling buffers (~1s at 416 Hz) and session log
recent_after = collections.deque(maxlen=416)
recent_dsp = collections.deque(maxlen=416)
throw_history = collections.deque(maxlen=25)

# Connected SSE clients
subscribers = []
subscribers_lock = threading.Lock()

# Background worker control
active_stop_event = threading.Event()
active_thread = None

# ----- FOR CONNECTION TO XIAO via BLE -----

def broadcast(event_type, payload):
    msg = f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
    with subscribers_lock:
        dead = []
        for q in subscribers:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            subscribers.remove(q)

def handle_completed_window(records_after, records_dsp, forced_label=None):
    """Extracts metrics and routes to dataset collection or live ML inference."""
    metrics_list = analysis.compute_form_metrics(records_after, records_dsp, analysis.CSV_METRICS)
    if not metrics_list:
        return

    metrics = metrics_list[0]
    with state_lock:
        mode = app_state["mode"]
        label = forced_label or app_state["label"]

    result = {
        "timestamp": time.strftime("%H:%M:%S"),
        "mode": mode,
        "metrics": metrics,
    }

    if mode == "collect" or forced_label is not None:
        trial_path = analysis.save_trial_archive(records_after, records_dsp, label)
        analysis.append_to_dataset(
            [metrics],
            label,
            dataset_path=analysis.CSV_DATASET,
            trial_file=os.path.basename(trial_path) if trial_path else "",
        )
        result["saved_label"] = label
    elif mode == "inference":
        try:
            result["prediction"] = ml_model.predict_throw(metrics, ml_model.DEFAULT_MODEL_PATH)
        except FileNotFoundError as exc:
            result["error"] = str(exc)

    throw_history.appendleft(result)
    broadcast("throw_event", result)

def process_packet(parts):
    """Parses a 17-field CSV packet from src.ino into filtered & DSP records."""
    timestamp = float(parts[0])
    f_ax, f_ay, f_az = float(parts[8]), float(parts[9]), float(parts[10])
    f_gx, f_gy, f_gz = float(parts[11]), float(parts[12]), float(parts[13])
    a_total_filt = float(parts[14])
    window_energy = float(parts[15])
    event_detected = int(parts[16])

    rec_after = [timestamp, f_ax, f_ay, f_az, f_gx, f_gy, f_gz, a_total_filt]
    rec_dsp = [timestamp, window_energy, event_detected]
    gyro_mag = math.sqrt(f_gx**2 + f_gy**2 + f_gz**2)
    return rec_after, rec_dsp, gyro_mag

def stop_active_worker():
    global active_thread
    active_stop_event.set()
    if active_thread and active_thread.is_alive():
        active_thread.join(timeout=2.0)
    active_stop_event.clear()
    with state_lock:
        app_state["source"] = "disconnected"
        app_state["device"] = None

def find_xiao_serial_port():
    """Prioritizes Seeed XIAO MG24 / USB modem ports over generic ports."""
    ports = list(list_ports.comports())
    if not ports:
        return None

    keywords = ("xiao", "seeed", "silicon", "usbmodem", "ttyacm")
    for p in ports:
        haystack = f"{p.device} {p.description} {p.hwid}".lower()
        if any(k in haystack for k in keywords):
            return p.device
    return ports[0].device

def find_xiao_ble_device():
    """Optional BLE scan fallback if bleak is installed."""
    if not BLE_AVAILABLE:
        return None

    async def _scan():
        devices = await BleakScanner.discover(timeout=3.0)
        for d in devices:
            name = (d.name or "").lower()
            if "embedqb" in name or "xiao" in name or "mg24" in name:
                return d.address
        return None

    try:
        return asyncio.run(_scan())
    except Exception:
        return None

def make_ingestor():
    in_event = False
    event_after = []
    event_dsp = []
    sample_counter = 0

    def ingest(rec_after, rec_dsp, gyro_mag):
        nonlocal in_event, event_after, event_dsp, sample_counter
        recent_after.append(rec_after)
        recent_dsp.append(rec_dsp)
        detected = rec_dsp[2]

        if detected == 1:
            in_event = True
            event_after.append(rec_after)
            event_dsp.append(rec_dsp)
        elif in_event:
            in_event = False
            if len(event_after) >= 3:
                handle_completed_window(event_after, event_dsp)
            event_after, event_dsp = [], []

        sample_counter += 1
        if sample_counter % 16 == 0:
            broadcast("telemetry", {
                "t": round(rec_after[0], 1),
                "energy": round(rec_dsp[1], 2),
                "gyro_mag": round(gyro_mag, 1),
                "accel_mag": round(rec_after[7], 2),
                "detected": detected,
            })

    return ingest

# ----- FOR WIRED CONNECTION TO XIAO ----- 

def wired_worker(port, baud, stop_event):
    ingest = make_ingestor()
    ser = None
    try:
        ser = serial.Serial(port, baud, timeout=1.0)
        time.sleep(1.5)
        ser.reset_input_buffer()
        with state_lock:
            app_state["source"] = "wired"
            app_state["device"] = port
        broadcast("status", dict(app_state))

        while not stop_event.is_set():
            raw_line = ser.readline()
            if not raw_line:
                continue
            parts = raw_line.decode("utf-8", errors="ignore").strip().split(",")
            if len(parts) < 17:
                continue
            try:
                rec_after, rec_dsp, gyro_mag = process_packet(parts)
                ingest(rec_after, rec_dsp, gyro_mag)
            except ValueError:
                continue
    except serial.SerialException:
        pass
    finally:
        if ser and ser.is_open:
            ser.close()
        with state_lock:
            if app_state["source"] == "wired":
                app_state["source"] = "disconnected"
                app_state["device"] = None
        broadcast("status", dict(app_state))


def mock_worker(stop_event):
    ingest = make_ingestor()
    with state_lock:
        app_state["source"] = "mock"
        app_state["device"] = "Virtual XIAO MG24"
    broadcast("status", dict(app_state))

    t_ms = 0.0
    cycle_type = "good_form"

    while not stop_event.is_set():
        phase = t_ms % 3200.0
        if phase < 3.0:
            with state_lock:
                prof = app_state["mock_profile"]
            cycle_type = random.choice(["good_form", "bad_form"]) if prof == "mixed" else prof

        is_throw = cycle_type != "idle" and (1100.0 <= phase <= 1520.0)
        if is_throw:
            progress = (phase - 1100.0) / 420.0
            bell = math.sin(progress * math.pi)
            if cycle_type == "good_form":
                gyro = 40.0 + 500.0 * bell + random.uniform(-10, 10)
                wobble = random.uniform(-20, 20)
                energy = 20.0 + 440.0 * bell
                accel = 1.0 + 5.2 * bell
            else:
                gyro = 40.0 + 240.0 * bell + random.uniform(-15, 15)
                wobble = random.uniform(-110, 110)
                energy = 20.0 + 165.0 * bell
                accel = 1.0 + 2.8 * bell
            rec_after = [t_ms, 0.2, 0.3, accel, wobble, wobble * 0.8, gyro, accel]
        else:
            energy = 19.5 + random.uniform(-1.5, 1.5)
            gyro = 25.0 + random.uniform(-8, 8)
            rec_after = [t_ms, 0.05, 0.05, 1.0, 5.0, 5.0, gyro, 1.0]

        det = 1 if energy > analysis.THRESHHOLD_VAL else 0
        rec_dsp = [t_ms, energy, det]
        ingest(rec_after, rec_dsp, abs(gyro))
        t_ms += 2.404
        time.sleep(0.0024)

# ----- API ROUTING FOR SENSORS -----  

@sensor_bp.route("/stream")
def stream():
    q = queue.Queue(maxsize=100)
    with subscribers_lock:
        subscribers.append(q)

    def event_generator():
        try:
            while True:
                yield q.get()
        except GeneratorExit:
            with subscribers_lock:
                if q in subscribers:
                    subscribers.remove(q)

    return Response(event_generator(), mimetype="text/event-stream")


@sensor_bp.route("/api/connect", methods=["POST"])
def connect_sensor():
    """Scans wired USB first, then falls back to BLE if available."""
    global active_thread
    data = request.get_json(silent=True) or {}
    preferred_port = data.get("port")

    stop_active_worker()

    port = preferred_port or find_xiao_serial_port()
    if port:
        active_thread = threading.Thread(
            target=wired_worker, args=(port, analysis.DEFAULT_BAUD, active_stop_event), daemon=True
        )
        active_thread.start()
        return jsonify({"status": "connecting", "source": "wired", "device": port})

    ble_addr = find_xiao_ble_device()
    if ble_addr:
        with state_lock:
            app_state["source"] = "ble"
            app_state["device"] = ble_addr
        return jsonify({
            "status": "found_ble",
            "source": "ble",
            "device": ble_addr,
            "note": "BLE device detected; ensure BLE UART characteristic is enabled in src.ino.",
        })

    return jsonify({
        "error": "No wired XIAO MG24 Sense or BLE device found. Plug in via USB-C and click Scan again, or enable Mock Mode."
    }), 404

@sensor_bp.route("/api/disconnect", methods=["POST"])
def disconnect_sensor():
    stop_active_worker()
    return jsonify({"status": "disconnected", "state": app_state})


@sensor_bp.route("/api/mock", methods=["POST"])
def toggle_mock():
    global active_thread
    data = request.get_json(silent=True) or {}
    enable = data.get("enable", True)
    profile = data.get("profile")

    if profile:
        with state_lock:
            app_state["mock_profile"] = profile

    if enable:
        if app_state["source"] != "mock":
            stop_active_worker()
            active_thread = threading.Thread(target=mock_worker, args=(active_stop_event,), daemon=True)
            active_thread.start()
    else:
        if app_state["source"] == "mock":
            stop_active_worker()

    return jsonify(app_state)