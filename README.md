# EmbedQB
## Problem & Overview
Athletes training solo don’t have affordable real-time feedback to identify problems in their form when training solo, requiring them to take extra time to watch self-recordings of their practice to make corrections. This still lacks immediate response to the development of bad habits which can cause them to occur anyway. We hope to provide affordable and quantifiable feedback to prospective athletes to reduce injury risks and allows for solo training.

Our solution is to have a compact wearable that uses the Seeed Studio Xiao MG24 Sense’s IMU to capture motion data while throwing a football to process time-series signals locally. We intend for it to be a low-power, low-latency, low-cost and highly portable wearable that allows athletes to train solo with immediate feedback for correcting bad habits and reducing injury risk.

## Signal Acquisition Chain
1. 

## Prereqs/Installations: 
### Hardware
Seeed Studio XIAO MG24 (Sense)

### Python
Install all dependencies in a virtual environment: 
``` 
bash 
pip install -r requirements.txt
```
#### List of dependencies: 
- pyserial 3.5
- matplotlib 3.11.2

Other dependencies listed in requirements.txt are automatically installed by the listed dependencies.

### Arduino 
- Library `Seeed Arduino LSM6DS3 2.0.7` by Seeed Studio.
- Board manager `Arduino AVR Boards 1.8.8` by Arduino.

## How to run:
1. 

## Contributors: 
- Reykjavik Salvador
- Mehar Saini
- Pavan Sanagana
