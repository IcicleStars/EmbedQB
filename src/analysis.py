import serial
import csv
import time
import os
import matplotlib.pyplot as plt
import argparse
from datetime import datetime
import numpy as np

# Default Hardware & DSP Configurations
DEFAULT_PORT = os.environ.get("EMBEDQB_PORT", "/dev/cu.usbmodem0E76A5EF3")
DEFAULT_BAUD = int(os.environ.get("EMBEDQB_BAUD", "921600"))
DEFAULT_SAMPLES = int(os.environ.get("EMBEDQB_SAMPLES", "400"))

FS_HZ = 416.0          # Target sampling rate (Hz)
WINDOW_SIZE = 20       # 20 samples (~48 ms at 416 Hz)
THRESHHOLD_VAL = 25.0  # Event detection threshold

# Directory Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")
TRIALS_DIR = os.path.join(DATA_DIR, "trials")
FIGURE_DIR = os.path.join(BASE_DIR, "../figures")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TRIALS_DIR, exist_ok=True)
os.makedirs(FIGURE_DIR, exist_ok=True)

# Output CSV Paths
CSV_BEFORE = os.path.join(DATA_DIR, "data_before.csv")
CSV_AFTER = os.path.join(DATA_DIR, "data_after.csv")
CSV_ENERGY = os.path.join(DATA_DIR, "energy.csv")
CSV_THRS = os.path.join(DATA_DIR, "threshhold.csv")
CSV_METRICS = os.path.join(DATA_DIR, "form_metrics.csv")
CSV_DATASET = os.path.join(DATA_DIR, "dataset.csv")

# Output Figure Paths
FIG_BEFORE = os.path.join(FIGURE_DIR, "plot_before.png")
FIG_AFTER = os.path.join(FIGURE_DIR, "plot_after.png")
FIG_ENERGY = os.path.join(FIGURE_DIR, "energy.png")
FIG_THRS = os.path.join(FIGURE_DIR, "threshhold.png")
FIG_FFT = os.path.join(FIGURE_DIR, "fft_analysis.png")
FIG_STFT = os.path.join(FIGURE_DIR, "stft_spectrogram.png")

METRICS_FIELDS = [
    "event_id",
    "start_ms",
    "end_ms",
    "duration_ms",
    "peak_angular_velocity_dps",
    "deceleration_slope_dps2",
    "cross_axis_variance",
    "peak_accel_g",
    "peak_energy",
    "threshold_triggered",
]


def collect_data(port, baud_rate=DEFAULT_BAUD, sample_count=DEFAULT_SAMPLES):
    print(f"Connecting to {port} at {baud_rate} baud...")
    ser = None
    records_before = []
    records_after = []
    records_dsp = []  # [timestamp_ms, window_energy, event_detected]

    try:
        ser = serial.Serial(port, baud_rate, timeout=2.0)
        time.sleep(2.0)
        ser.reset_input_buffer()
        print(f"Listening for {sample_count} incoming IMU + on-device DSP packets...")

        start_time = None
        while len(records_before) < sample_count:
            raw_line = ser.readline()
            if not raw_line:
                continue

            line = raw_line.decode("utf-8", errors="ignore").strip()
            parts = line.split(",")

            # Expecting 17 comma-separated values from src.ino
            if len(parts) >= 17:
                try:
                    timestamp = float(parts[0])

                    # Unfiltered 6-DOF + on-device raw acceleration magnitude
                    ax, ay, az = float(parts[1]), float(parts[2]), float(parts[3])
                    gx, gy, gz = float(parts[4]), float(parts[5]), float(parts[6])
                    a_total_raw = float(parts[7])

                    # Butterworth-filtered 6-DOF + on-device filtered magnitude
                    f_ax, f_ay, f_az = float(parts[8]), float(parts[9]), float(parts[10])
                    f_gx, f_gy, f_gz = float(parts[11]), float(parts[12]), float(parts[13])
                    a_total_filt = float(parts[14])

                    # On-device sliding window energy and threshold detection
                    window_energy = float(parts[15])
                    event_detected = int(parts[16])

                    if start_time is None:
                        start_time = time.time()

                    records_before.append([timestamp, ax, ay, az, gx, gy, gz, a_total_raw])
                    records_after.append([timestamp, f_ax, f_ay, f_az, f_gx, f_gy, f_gz, a_total_filt])
                    records_dsp.append([timestamp, window_energy, event_detected])

                except ValueError:
                    continue

        total_wall_time = time.time() - start_time if start_time else 0
        hz = len(records_before) / total_wall_time if total_wall_time > 0 else 0
        print(f"Done collecting {len(records_before)} samples (~{hz:.1f} Hz effective rate)")

    finally:
        if ser and ser.is_open:
            ser.close()
            print("Serial port closed")

    return records_before, records_after, records_dsp


def plot(records, csv_path, fig_path, title_label):
    if not records:
        print("No records to plot")
        return

    with open(csv_path, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_ms", "ax_g", "ay_g", "az_g", "gx_dps", "gy_dps", "gz_dps", "magnitude_g"])
        writer.writerows(records)
    print(f"Saved data to {csv_path}")

    timestamps = [r[0] for r in records]
    norm_time = [t - timestamps[0] for t in timestamps]

    ax = [r[1] for r in records]
    ay = [r[2] for r in records]
    az = [r[3] for r in records]
    gx = [r[4] for r in records]
    gy = [r[5] for r in records]
    gz = [r[6] for r in records]
    a_total = [r[7] for r in records]

    fig, (ax_acc, ax_gyro) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    ax_acc.plot(norm_time, ax, label="Accel X", alpha=0.7)
    ax_acc.plot(norm_time, ay, label="Accel Y", alpha=0.7)
    ax_acc.plot(norm_time, az, label="Accel Z", alpha=0.7)
    ax_acc.plot(norm_time, a_total, label="Total Magnitude", color="black", linewidth=1.5, linestyle="--")
    ax_acc.set_title(f"IMU Data - ({title_label})")
    ax_acc.set_ylabel("Linear Acceleration (g)")
    ax_acc.grid(True, linestyle="--", alpha=0.6)
    ax_acc.legend(loc="upper right")

    ax_gyro.plot(norm_time, gx, label="Gyro X (Pitch Rate)", alpha=0.7)
    ax_gyro.plot(norm_time, gy, label="Gyro Y (Roll Rate)", alpha=0.7)
    ax_gyro.plot(norm_time, gz, label="Gyro Z (Yaw Rate)", alpha=0.7)
    ax_gyro.set_xlabel("Elapsed Time (ms)")
    ax_gyro.set_ylabel("Angular Velocity (°/s)")
    ax_gyro.grid(True, linestyle="--", alpha=0.6)
    ax_gyro.legend(loc="upper right")

    plt.tight_layout()
    plt.savefig(fig_path, dpi=300)
    print(f"Saved figure to {fig_path}")
    plt.close()


def save_and_plot_dsp(records_dsp):
    if not records_dsp:
        return

    timestamps = [r[0] for r in records_dsp]
    norm_time = [t - timestamps[0] for t in timestamps]
    energy = [r[1] for r in records_dsp]
    threshold = [r[2] for r in records_dsp]

    with open(CSV_ENERGY, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_ms", "energy"])
        for t, e in zip(timestamps, energy):
            writer.writerow([t, e])

    with open(CSV_THRS, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_ms", "event_detected"])
        for t, det in zip(timestamps, threshold):
            writer.writerow([t, det])

    plt.figure(figsize=(10, 4))
    plt.plot(norm_time, energy, color="orange")
    plt.title("Filtered Window Energy (E[k])")
    plt.xlabel("Elapsed Time (ms)")
    plt.ylabel("Energy")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(FIG_ENERGY, dpi=300)
    plt.close()

    plt.figure(figsize=(10, 4))
    plt.plot(norm_time, threshold, color="red")
    plt.title(f"Event Detection (Threshold = {THRESHHOLD_VAL})")
    plt.xlabel("Elapsed Time (ms)")
    plt.ylabel("Detection (0 or 1)")
    plt.yticks([0, 1])
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(FIG_THRS, dpi=300)
    plt.close()

    print("Saved Energy and Event Detection CSVs and figures to data/ and figures/")


def plot_fft(records, fig_path=FIG_FFT, fs=FS_HZ):
    """Computes and plots FFT for Linear Acceleration and Angular Velocity Magnitude."""
    if not records or len(records) < 4:
        return

    n = len(records)
    acc_mag = np.array([r[7] for r in records], dtype=float)
    gyro_mag = np.array([(r[4] ** 2 + r[5] ** 2 + r[6] ** 2) ** 0.5 for r in records], dtype=float)

    # Subtract DC offset (gravity / static bias) to highlight 1-15 Hz motion frequencies
    acc_zero_mean = acc_mag - np.mean(acc_mag)
    gyro_zero_mean = gyro_mag - np.mean(gyro_mag)

    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    acc_fft = (2.0 / n) * np.abs(np.fft.rfft(acc_zero_mean))
    gyro_fft = (2.0 / n) * np.abs(np.fft.rfft(gyro_zero_mean))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    ax1.plot(freqs, acc_fft, color="darkblue", linewidth=1.5)
    ax1.set_title("FFT: Linear Acceleration Magnitude")
    ax1.set_xlabel("Frequency (Hz)")
    ax1.set_ylabel("Amplitude (g)")
    ax1.grid(True, linestyle="--", alpha=0.6)

    ax2.plot(freqs, gyro_fft, color="purple", linewidth=1.5)
    ax2.set_title("FFT: Angular Velocity Magnitude")
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("Amplitude (dps)")
    ax2.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()
    plt.savefig(fig_path, dpi=300)
    print(f"Saved FFT figure to {fig_path}")
    plt.close()


def plot_stft(records, fig_path=FIG_STFT, fs=FS_HZ):
    """Computes and plots STFT spectrograms (0-50 Hz) for Acceleration and Gyro Magnitude."""
    if not records or len(records) < WINDOW_SIZE:
        return

    acc_mag = np.array([r[7] for r in records], dtype=float)
    gyro_mag = np.array([(r[4] ** 2 + r[5] ** 2 + r[6] ** 2) ** 0.5 for r in records], dtype=float)

    acc_zero_mean = acc_mag - np.mean(acc_mag)
    gyro_zero_mean = gyro_mag - np.mean(gyro_mag)

    nperseg = min(WINDOW_SIZE, len(records))
    noverlap = max(1, int(nperseg * 0.75))
    pad_to = max(128, nperseg * 4)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    _, _, _, im1 = ax1.specgram(
        acc_zero_mean, NFFT=nperseg, Fs=fs, noverlap=noverlap, pad_to=pad_to, cmap="viridis", mode="psd"
    )
    ax1.set_title("STFT Spectrogram: Linear Acceleration")
    ax1.set_xlabel("Time (seconds)")
    ax1.set_ylabel("Frequency (Hz)")
    ax1.set_ylim(0, 50)
    cbar1 = fig.colorbar(im1, ax=ax1)
    cbar1.set_label("Power (dB)")

    _, _, _, im2 = ax2.specgram(
        gyro_zero_mean, NFFT=nperseg, Fs=fs, noverlap=noverlap, pad_to=pad_to, cmap="plasma", mode="psd"
    )
    ax2.set_title("STFT Spectrogram: Angular Velocity")
    ax2.set_xlabel("Time (seconds)")
    ax2.set_ylabel("Frequency (Hz)")
    ax2.set_ylim(0, 50)
    cbar2 = fig.colorbar(im2, ax=ax2)
    cbar2.set_label("Power (dB)")

    plt.tight_layout()
    plt.savefig(fig_path, dpi=300)
    print(f"Saved STFT spectrogram to {fig_path}")
    plt.close()


def detect_event_windows(records_dsp):
    """Finds contiguous sample index windows where event_detected == 1."""
    events = []
    in_event = False
    start_idx = 0

    for i, dsp_row in enumerate(records_dsp):
        detected = int(dsp_row[2])
        if detected == 1 and not in_event:
            in_event = True
            start_idx = i
        elif detected == 0 and in_event:
            in_event = False
            if i - start_idx >= 3:
                events.append((start_idx, i - 1))

    if in_event and (len(records_dsp) - start_idx) >= 3:
        events.append((start_idx, len(records_dsp) - 1))

    return events


def save_trial_archive(records_after, records_dsp, label, trials_dir=TRIALS_DIR):
    """Saves a timestamped trial waveform CSV so multi-trial recordings are never overwritten."""
    if not records_after or not records_dsp:
        return None

    os.makedirs(trials_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trial_path = os.path.join(trials_dir, f"{label}_{stamp}.csv")

    with open(trial_path, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp_ms", "ax_g", "ay_g", "az_g",
            "gx_dps", "gy_dps", "gz_dps", "magnitude_g",
            "energy", "event_detected", "label",
        ])
        for rec, dsp in zip(records_after, records_dsp):
            writer.writerow(list(rec) + [dsp[1], dsp[2], label])

    print(f"Archived labeled trial waveform to {trial_path}")
    return trial_path


def append_to_dataset(metrics_list, label, dataset_path=CSV_DATASET, trial_file=""):
    """Appends extracted throw feature vectors with a ground-truth label to the ML dataset CSV."""
    if not metrics_list:
        return

    fieldnames = ["recorded_at", "label", "trial_file"] + METRICS_FIELDS
    file_exists = os.path.exists(dataset_path) and os.path.getsize(dataset_path) > 0
    recorded_at = datetime.now().isoformat(timespec="seconds")

    with open(dataset_path, mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for m in metrics_list:
            row = {"recorded_at": recorded_at, "label": label, "trial_file": trial_file}
            row.update(m)
            writer.writerow(row)

    print(f"Appended {len(metrics_list)} labeled event(s) ('{label}') to {dataset_path}")


def compute_form_metrics(records_after, records_dsp, csv_path=CSV_METRICS):
    """Extracts Peak Angular Velocity, Deceleration Slope, Cross-Axis Variance, Peak Accel & Energy."""
    if not records_after or not records_dsp:
        return []

    events = detect_event_windows(records_dsp)
    triggered = bool(events)

    # Fallback: if no event crossed the threshold, evaluate the full recording window
    if not events:
        events = [(0, len(records_after) - 1)]

    metrics_list = []
    for event_id, (s_idx, e_idx) in enumerate(events, start=1):
        segment = records_after[s_idx:e_idx + 1]
        dsp_segment = records_dsp[s_idx:e_idx + 1]
        times_sec = np.array([(r[0] - segment[0][0]) / 1000.0 for r in segment], dtype=float)

        gx = np.array([r[4] for r in segment], dtype=float)
        gy = np.array([r[5] for r in segment], dtype=float)
        gz = np.array([r[6] for r in segment], dtype=float)
        gyro_mag = np.sqrt(gx**2 + gy**2 + gz**2)

        peak_idx = int(np.argmax(gyro_mag))
        peak_angular_vel = float(gyro_mag[peak_idx])

        if peak_idx < len(segment) - 1:
            dt = times_sec[-1] - times_sec[peak_idx]
            decel_slope = float((gyro_mag[-1] - peak_angular_vel) / dt) if dt > 1e-6 else 0.0
        else:
            decel_slope = 0.0

        cross_axis_var = float(np.mean([np.var(gx), np.var(gy), np.var(gz)]))
        peak_accel_g = float(max(r[7] for r in segment))
        peak_energy = float(max(d[1] for d in dsp_segment))
        duration_ms = float(segment[-1][0] - segment[0][0])

        metrics = {
            "event_id": event_id,
            "start_ms": float(segment[0][0]),
            "end_ms": float(segment[-1][0]),
            "duration_ms": round(duration_ms, 2),
            "peak_angular_velocity_dps": round(peak_angular_vel, 3),
            "deceleration_slope_dps2": round(decel_slope, 3),
            "cross_axis_variance": round(cross_axis_var, 3),
            "peak_accel_g": round(peak_accel_g, 3),
            "peak_energy": round(peak_energy, 3),
            "threshold_triggered": int(triggered),
        }
        metrics_list.append(metrics)

    with open(csv_path, mode="w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=METRICS_FIELDS)
        writer.writeheader()
        writer.writerows(metrics_list)

    print(f"Saved Form Assessment Metrics ({len(metrics_list)} event(s)) to {csv_path}")
    for m in metrics_list:
        print(
            f"  [Event {m['event_id']}] Peak Gyro: {m['peak_angular_velocity_dps']} dps | "
            f"Decel Slope: {m['deceleration_slope_dps2']} dps^2 | "
            f"Cross-Axis Var: {m['cross_axis_variance']} | Peak Energy: {m['peak_energy']}"
        )
    return metrics_list


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EmbedQB Serial Data Acquisition & DSP Analysis")
    parser.add_argument("--port", default=DEFAULT_PORT, help="Serial port identifier")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help="Serial baud rate")
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES, help="Number of samples to record")
    parser.add_argument(
        "--label",
        default=None,
        help="Optional ground-truth label (e.g., good_form, bad_form, idle) to append to ML dataset",
    )
    parser.add_argument("--dataset", default=CSV_DATASET, help="Master labeled dataset CSV path")
    args = parser.parse_args()

    raw_data, filtered_data, dsp_data = collect_data(args.port, args.baud, args.samples)
    plot(raw_data, CSV_BEFORE, FIG_BEFORE, "Before")
    plot(filtered_data, CSV_AFTER, FIG_AFTER, "After")
    save_and_plot_dsp(dsp_data)
    plot_fft(filtered_data, FIG_FFT)
    plot_stft(filtered_data, FIG_STFT)
    metrics = compute_form_metrics(filtered_data, dsp_data, CSV_METRICS)

    if args.label:
        trial_path = save_trial_archive(filtered_data, dsp_data, args.label)
        append_to_dataset(
            metrics,
            args.label,
            dataset_path=args.dataset,
            trial_file=os.path.basename(trial_path) if trial_path else "",
        )