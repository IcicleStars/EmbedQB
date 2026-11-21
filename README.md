# EmbedQB

## Problem & Overview
Athletes training solo don't have affordable real-time feedback to identify problems in their form, requiring them to take extra time to watch self-recordings of their practice to make corrections. This still lacks immediate response to the development of bad habits which can cause them to occur anyway. We hope to provide affordable and quantifiable feedback to prospective athletes to reduce injury risks and allow for solo training.

Our solution is a compact wearable that uses the Seeed Studio XIAO MG24 Sense's IMU to capture motion data while throwing a football and process time-series signals locally. We intend for it to be a low-power, low-latency, low-cost, and highly portable wearable that allows athletes to train solo with immediate feedback for correcting bad habits and reducing injury risk.

## Signal Acquisition Chain
1. Pin `PD5` is driven `HIGH` to supply power to the onboard LSM6DS3 IMU, initializing the I2C interface at `0x6A` in fast mode (`400 kHz`).
2. A non-blocking `micros()` timer (`2404 µs` interval) continuously samples 6-DOF motion data (3-axis linear acceleration at $\pm 16\text{ g}$ and 3-axis angular velocity at $2000\text{ dps}$) at **416 Hz**.
3. All 6 axes are filtered on-device through a **2nd-order Butterworth low-pass filter** ($f_c = 12\text{ Hz}$, Direct Form II Transposed biquad) to attenuate high-frequency noise while preserving the target 1–15 Hz hip-rotation band.
4. On-device DSP computes raw and filtered linear acceleration magnitude, maintains an $O(1)$ **20-sample (~48 ms) circular buffer** for sliding-window energy ($E[k]$), and performs binary event detection (`1` when $E[k] > 25.0$, else `0`), toggling `LED_BUILTIN` during active throw events.
5. Unified 17-field CSV packets are transmitted over USB serial at **921600 baud**:
   `timestamp, ax, ay, az, gx, gy, gz, a_total_raw, f_ax, f_ay, f_az, f_gx, f_gy, f_gz, a_total_filt, window_energy, event_detected`
6. `src/analysis.py` reads the serial stream, exports CSVs to `data/` (unfiltered, filtered, energy, threshold, and extracted form metrics), and saves time-series, energy, event-detection, FFT spectrum, and STFT spectrogram plots to `figures/`. Passing `--label` archives each full trial waveform to `data/trials/` and appends the extracted feature vector to `data/dataset.csv` for ML training.

## Prereqs / Installations

### Hardware
- Seeed Studio XIAO MG24 (Sense)

### Python
#### List of dependencies:
- `pyserial 3.5`
- `matplotlib 3.11.2`
- `numpy 2.5.3`

Other dependencies listed in requirements.txt are automatically installed by the listed dependencies or by Python. It's recommended to install all dependencies in a virtual environment: 
``` 
bash 
pip install -r requirements.txt
```

### Arduino 
- Library `Seeed Arduino LSM6DS3 2.0.7` by Seeed Studio.
- Board manager `Arduino AVR Boards 1.8.8` by Arduino.

## How to run:
1. Connect the Seeed Studio Xiao MG24 Sense to your device via USB-C cable.
2. Open `EmbedQB.ino` in the Arduino IDE and upload the program to the board.
3. Set up and activate virtual environment:
   - **macOS / Linux:**
     ```
     bash
     python3 -m venv venv
     source venv/bin/activate
     pip install -r requirements.txt
     ```
   - **Windows:**
     ```
     To be filled . . .
     ```
4. Check the board's serial port identifier
   - **macOS**: Click `tools` in the menu bar and look for the port, which should show `/dev/cu.usbmodem...`
   - **Linux**: Click `tools` in the menu bar and look for the port, which should show `/dev/ttyACM0` or similar.
   - **Windows**: To be filled . . .

   *Note for Linux:* If you encounter a `Permission denied` error, add your user to the `dialout` group via `sudo usermod -aG dialout $USER`, then log out and log back in.
6. Update `SERIAL_PORT` in `analysis.py` with the system's port name.
7. Run the collection script (Make sure to close the Serial Monitor / Plotter in the Arduino IDE!)
   ```
   bash
   python analysis.py
   ```
8. Recorded data will be saved to `data/` and `figures/` which will automatically be created by the python file.

## Contributors: 
- Reykjavik Salvador
- Mehar Saini
- Pavan Sanagana
