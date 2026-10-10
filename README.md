# EmbedQB
## Problem & Overview
Athletes training solo don’t have affordable real-time feedback to identify problems in their form when training solo, requiring them to take extra time to watch self-recordings of their practice to make corrections. This still lacks immediate response to the development of bad habits which can cause them to occur anyway. We hope to provide affordable and quantifiable feedback to prospective athletes to reduce injury risks and allows for solo training.

Our solution is to have a compact wearable that uses the Seeed Studio Xiao MG24 Sense’s IMU to capture motion data while throwing a football to process time-series signals locally. We intend for it to be a low-power, low-latency, low-cost and highly portable wearable that allows athletes to train solo with immediate feedback for correcting bad habits and reducing injury risk.

## Signal Acquisition Chain
1. The pin `PD5` is driven HIGH to supply power to the onboard LSM6DS3 IMU, initializing the I2C interface at `0x6A`
2. The microcontroller continuously samples 6-DOF motion data (3-axis linear acceleration measured in gravity and 3-axis angular velocity measured in degrees/second) with a 2ms loop delay.
3. All 6 axes are also put through EWMA as an LTI filter with an alpha value of $\alpha = 0.50$, acting as a low-pass filter to attenuate high-frequency noise.
4. Packets are transmitted over a USB serial at 115200 baud formatted as `millis, ax, ay, az, gx, gy, gz, millis, f_ax, f_ay, f_az, f_gx, f_gy, f_gz`, 
5. `analysis.py` connects to serial port and acquires 400 valid samples and obtains the total magnitude of the linear acceleration.
6. Data is exported to `data/` directory and time-series subplots for acceleration and gyro rates are saved as a single `.png` file to `figures/` directory.

## Prereqs/Installations: 
### Hardware
Seeed Studio XIAO MG24 (Sense)

### Python
#### List of dependencies: 
- pyserial 3.5
- matplotlib 3.11.2

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
