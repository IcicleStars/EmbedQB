import serial
import serial.tools.list_ports
import csv
import time
import os
import matplotlib.pyplot as plt

# configs
SERIAL_PORT = '/dev/cu.usbmodem0E76A5EF3'
BAUD_RATE = 115200
SAMPLE_COUNT = 400;

# paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FIGURE_DIR  = os.path.join(BASE_DIR, "figures")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FIGURE_DIR, exist_ok=True)

# data and figures for "before filter" and "after filter"
CSV_BEFORE = os.path.join(DATA_DIR, "data_before.csv")
CSV_AFTER = os.path.join(DATA_DIR, "data_after.csv")
FIG_BEFORE = os.path.join(FIGURE_DIR, "plot_after.png")
FIG_AFTER = os.path.join(FIGURE_DIR, "plot_after.png")

# get data
def collect_data(port): 
    print(f"connecting to {port} at {BAUD_RATE} baud. . .")
    ser = None
    records_before = []
    records_after = []

    try: 
        ser = serial.Serial(port, BAUD_RATE, timeout = 2.0)
        time.sleep(2.0)
        ser.reset_input_buffer()
        print("Listening for incoming IMU. . .")

        start_time = None
        while len(records_before) < SAMPLE_COUNT: 
            raw_line = ser.readline()
            if not raw_line: 
                continue 

            # ignore malformed data or whatever
            line = raw_line.decode('utf-8', errors='ignore').strip() 

            # get csv lines
            parts = line.split(',')
            if len(parts) >= 14: 
                try: 
                    # raw packets
                    timestamp_raw = float(parts[0])
                    ax = float(parts[1])
                    ay = float(parts[2])
                    az = float(parts[3])
                    gx = float(parts[4])
                    gy = float(parts[5])
                    gz = float(parts[6])

                    # filtered packets
                    timestamp_filt = float(parts[7])
                    f_ax = float(parts[8])
                    f_ay = float(parts[9])
                    f_az = float(parts[10])
                    f_gx = float(parts[11])
                    f_gy = float(parts[12])
                    f_gz = float(parts[13])

                    # calculate acc magnitude
                    a_total_raw = (ax**2 + ay**2 + az**2)**0.5
                    a_total_filt = (f_ax**2 + f_ay**2 + f_az**2)**0.5

                    if start_time is None: 
                        start_time = time.time()

                    records_before.append([timestamp_raw, ax, ay, az, gx, gy, gz, a_total_raw])
                    records_after.append([timestamp_filt, f_ax, f_ay, f_az, f_gx, f_gy, f_gz, a_total_filt])

                except ValueError: 
                    continue;

        total_wall_time = time.time()-start_time 
        hz = len(records_before) / total_wall_time if total_wall_time > 0 else 0
        print("done collecting samples")

    finally: 
        if ser and ser.is_open: 
            ser.close()
            print("serial port closed")

    return records_before, records_after

# save data and plot
def plot(records, csv_path, fig_path, title_label): 

    # nothing recorded
    if not records: 
        print("no records")
        return; 

    # write data file
    with open(csv_path, mode='w', newline='') as f: 
        writer = csv.writer(f)
        writer.writerow(["timestamp_ms", "ax_g", "ay_g", "az_g", "gx_dps", "gy_dps", "gz_dps", "magnitude_g"])
        writer.writerows(records)
    print(f"saved data to {csv_path}")

    # extract stuff for plotting
    timestamps = [r[0] for r in records]
    norm_time = [t - timestamps[0] for t in timestamps]
    ax = [r[1] for r in records]
    ay = [r[2] for r in records]
    az = [r[3] for r in records]
    gx = [r[4] for r in records]
    gy = [r[5] for r in records]
    gz = [r[6] for r in records]
    a_total = [r[7] for r in records]

    # dual-panel figure
    fig, (ax_acc, ax_gyro) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    # plot acceleration
    ax_acc.plot(norm_time, ax, label='Accel X', alpha=0.7)
    ax_acc.plot(norm_time, ay, label='Accel Y', alpha=0.7)
    ax_acc.plot(norm_time, az, label='Accel Z', alpha=0.7)
    ax_acc.plot(norm_time, a_total, label='Total Magnitude', color='black', linewidth=1.5, linestyle='--')
    ax_acc.set_title(f"IMU Data - ({title_label})")
    ax_acc.set_ylabel("Linear Acceleration (g)")
    ax_acc.grid(True, linestyle='--', alpha=0.6)
    ax_acc.legend(loc='upper right')

    # plot gyro
    ax_gyro.plot(norm_time, gx, label='Gyro X (Pitch Rate)', alpha=0.7)
    ax_gyro.plot(norm_time, gy, label='Gyro Y (Roll Rate)', alpha=0.7)
    ax_gyro.plot(norm_time, gz, label='Gyro Z (Yaw Rate)', alpha=0.7)
    ax_gyro.set_xlabel("Elapsed Time (ms)")
    ax_gyro.set_ylabel("Angular Velocity (°/s)")
    ax_gyro.grid(True, linestyle='--', alpha=0.6)
    ax_gyro.legend(loc='upper right')

    # save fig
    plt.tight_layout()
    plt.savefig(fig_path, dpi=300)
    print(f"Saved figure to {fig_path}")
    plt.close()

# main func 
if __name__ == "__main__": 
    raw_data, filtered_data = collect_data(SERIAL_PORT)
    plot(raw_data, CSV_BEFORE, FIG_BEFORE, "Before")
    plot(filtered_data, CSV_AFTER, FIG_AFTER, "After")