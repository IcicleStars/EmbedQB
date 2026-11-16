import serial
import csv
import time
import os
import matplotlib.pyplot as plt

# Serial configs
SERIAL_PORT = '/dev/cu.usbmodem0E76A5EF3'
BAUD_RATE = 115200
SAMPLE_COUNT = 400

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")
FIGURE_DIR = os.path.join(BASE_DIR, "../figures")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FIGURE_DIR, exist_ok=True)

# Data and figures for "before filter", "after filter", energy, and threshold
CSV_BEFORE = os.path.join(DATA_DIR, "data_before.csv")
CSV_AFTER = os.path.join(DATA_DIR, "data_after.csv")
CSV_ENERGY = os.path.join(DATA_DIR, "energy.csv")
CSV_THRS = os.path.join(DATA_DIR, "threshhold.csv")

FIG_BEFORE = os.path.join(FIGURE_DIR, "plot_before.png")  # Fixed overwrite bug
FIG_AFTER = os.path.join(FIGURE_DIR, "plot_after.png")
FIG_ENERGY = os.path.join(FIGURE_DIR, "energy.png")
FIG_THRS = os.path.join(FIGURE_DIR, "threshhold.png")


def collect_data(port):
    print(f"Connecting to {port} at {BAUD_RATE} baud...")
    ser = None
    records_before = []
    records_after = []
    records_dsp = []  # Stores [timestamp_ms, window_energy, event_detected] from MCU

    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=2.0)
        time.sleep(2.0)
        ser.reset_input_buffer()
        print("Listening for incoming IMU and on-device DSP packets...")

        start_time = None
        while len(records_before) < SAMPLE_COUNT:
            raw_line = ser.readline()
            if not raw_line:
                continue

            line = raw_line.decode('utf-8', errors='ignore').strip()
            parts = line.split(',')

            # Expecting 17 fields from the updated src.ino
            if len(parts) >= 17:
                try:
                    timestamp = float(parts[0])

                    # Unfiltered measurements + on-device raw magnitude
                    ax = float(parts[1])
                    ay = float(parts[2])
                    az = float(parts[3])
                    gx = float(parts[4])
                    gy = float(parts[5])
                    gz = float(parts[6])
                    a_total_raw = float(parts[7])

                    # Filtered measurements + on-device filtered magnitude
                    f_ax = float(parts[8])
                    f_ay = float(parts[9])
                    f_az = float(parts[10])
                    f_gx = float(parts[11])
                    f_gy = float(parts[12])
                    f_gz = float(parts[13])
                    a_total_filt = float(parts[14])

                    # On-device windowed energy and threshold event detection
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
        print(f"Done collecting {len(records_before)} samples (~{hz:.1f} Hz)")

    finally:
        if ser and ser.is_open:
            ser.close()
            print("Serial port closed")

    return records_before, records_after, records_dsp


def plot(records, csv_path, fig_path, title_label):
    if not records:
        print("No records to plot")
        return

    with open(csv_path, mode='w', newline='') as f:
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

    ax_acc.plot(norm_time, ax, label='Accel X', alpha=0.7)
    ax_acc.plot(norm_time, ay, label='Accel Y', alpha=0.7)
    ax_acc.plot(norm_time, az, label='Accel Z', alpha=0.7)
    ax_acc.plot(norm_time, a_total, label='Total Magnitude', color='black', linewidth=1.5, linestyle='--')
    ax_acc.set_title(f"IMU Data - ({title_label})")
    ax_acc.set_ylabel("Linear Acceleration (g)")
    ax_acc.grid(True, linestyle='--', alpha=0.6)
    ax_acc.legend(loc='upper right')

    ax_gyro.plot(norm_time, gx, label='Gyro X (Pitch Rate)', alpha=0.7)
    ax_gyro.plot(norm_time, gy, label='Gyro Y (Roll Rate)', alpha=0.7)
    ax_gyro.plot(norm_time, gz, label='Gyro Z (Yaw Rate)', alpha=0.7)
    ax_gyro.set_xlabel("Elapsed Time (ms)")
    ax_gyro.set_ylabel("Angular Velocity (°/s)")
    ax_gyro.grid(True, linestyle='--', alpha=0.6)
    ax_gyro.legend(loc='upper right')

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

    # Save energy.csv
    with open(CSV_ENERGY, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_ms", "energy"])
        for t, e in zip(timestamps, energy):
            writer.writerow([t, e])

    # Save threshhold.csv
    with open(CSV_THRS, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_ms", "event_detected"])
        for t, det in zip(timestamps, threshold):
            writer.writerow([t, det])

    # Plot on-device Window Energy
    plt.figure(figsize=(10, 4))
    plt.plot(norm_time, energy, color='orange')
    plt.title("On-Device Filtered Window Energy (E[k])")
    plt.xlabel("Elapsed Time (ms)")
    plt.ylabel("Energy")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(FIG_ENERGY, dpi=300)
    plt.close()

    # Plot on-device Event Detection
    plt.figure(figsize=(10, 4))
    plt.plot(norm_time, threshold, color='red')
    plt.title("On-Device Event Detection")
    plt.xlabel("Elapsed Time (ms)")
    plt.ylabel("Detection (0 or 1)")
    plt.yticks([0, 1])
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig(FIG_THRS, dpi=300)
    plt.close()

    print("Saved on-device Energy and Event Detection CSVs and figures to data/ and figures/")


if __name__ == "__main__":
    raw_data, filtered_data, dsp_data = collect_data(SERIAL_PORT)
    plot(raw_data, CSV_BEFORE, FIG_BEFORE, "Before")
    plot(filtered_data, CSV_AFTER, FIG_AFTER, "After")
    save_and_plot_dsp(dsp_data)