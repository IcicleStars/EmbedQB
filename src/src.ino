#include <Arduino.h>
#include <Wire.h>
#include "LSM6DS3.h"

// Hardware pins
const uint8_t IMU_PWR_PIN = PD5;

// Initialize IMU instance
LSM6DS3 myIMU(I2C_MODE, 0x6A);

// Sampling timing: 416 Hz -> 1,000,000 / 416 = 2403.85 us
const unsigned long SAMPLE_INTERVAL_US = 2404;
unsigned long last_sample_us = 0;

// On-device DSP Configuration (Window = 20 samples / ~48ms, Threshold = 25.0)
const int WINDOW_SIZE = 20;
const float THRESHOLD_VAL = 25.0f;

// 2nd-Order Butterworth LPF Coefficients (fs = 416 Hz, fc = 12 Hz)
const float BW_B0 =  0.00726416f;
const float BW_B1 =  0.01452832f;
const float BW_B2 =  0.00726416f;
const float BW_A1 = -1.74484287f;
const float BW_A2 =  0.77389952f;

// Direct Form II Transposed Biquad Filter structure (2 state variables per axis)
struct ButterworthLPF {
  float z1 = 0.0f;
  float z2 = 0.0f;

  inline float update(float x) {
    float y = (BW_B0 * x) + z1;
    z1 = (BW_B1 * x) - (BW_A1 * y) + z2;
    z2 = (BW_B2 * x) - (BW_A2 * y);
    return y;
  }
};

ButterworthLPF filter_ax, filter_ay, filter_az;
ButterworthLPF filter_gx, filter_gy, filter_gz;

// Sliding window circular buffer for O(1) Energy calculation
float energy_RingBuffer[WINDOW_SIZE] = {0.0f};
int buffer_idx = 0;
float window_energy = 0.0f;

void setup() {
  Serial.begin(921600);

  // Delay to allow for serial connection
  while (!Serial && millis() < 3000) {
    delay(10);
  }

  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH); // Active-low LED off by default

  // Power on sensor
  pinMode(IMU_PWR_PIN, OUTPUT);
  digitalWrite(IMU_PWR_PIN, HIGH);

  Wire.begin();
  Wire.setClock(400000);

  // Initialize IMU
  if (myIMU.begin()) {
    while (1) {
      digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
      delay(200);
    }
  }

  // Circuit and sensor configuration: 416 Hz ODR, +/-16g scale, 2000 dps
  myIMU.writeRegister(LSM6DS3_ACC_GYRO_CTRL1_XL, 0x84);
  myIMU.writeRegister(LSM6DS3_ACC_GYRO_CTRL2_G, 0x8C);

  last_sample_us = micros();
}

void loop() {
  unsigned long now_us = micros();

  // Enforce 416 Hz sampling interval (2404 microseconds)
  if (now_us - last_sample_us < SAMPLE_INTERVAL_US) {
    return;
  }
  last_sample_us += SAMPLE_INTERVAL_US;

  unsigned long timestamp = millis();

  // Read raw 6-DOF IMU measurements
  float ax = myIMU.readFloatAccelX();
  float ay = myIMU.readFloatAccelY();
  float az = myIMU.readFloatAccelZ();

  float gx = myIMU.readFloatGyroX();
  float gy = myIMU.readFloatGyroY();
  float gz = myIMU.readFloatGyroZ();

  // 2nd-Order Butterworth Low-Pass Filter (fc = 12 Hz)
  float filtered_ax = filter_ax.update(ax);
  float filtered_ay = filter_ay.update(ay);
  float filtered_az = filter_az.update(az);
  float filtered_gx = filter_gx.update(gx);
  float filtered_gy = filter_gy.update(gy);
  float filtered_gz = filter_gz.update(gz);

  // Vector Magnitude calculations
  float a_total_raw_sq = (ax * ax) + (ay * ay) + (az * az);
  float a_total_raw = sqrtf(a_total_raw_sq);

  float a_total_filt_sq = (filtered_ax * filtered_ax) +
                          (filtered_ay * filtered_ay) +
                          (filtered_az * filtered_az);
  float a_total_filt = sqrtf(a_total_filt_sq);

  // Sliding Window Energy (20-sample rolling sum)
  window_energy -= energy_RingBuffer[buffer_idx];
  energy_RingBuffer[buffer_idx] = a_total_filt_sq;
  window_energy += a_total_filt_sq;
  buffer_idx = (buffer_idx + 1) % WINDOW_SIZE;

  if (window_energy < 0.0f) {
    window_energy = 0.0f;
  }

  // Event Detection via Threshold
  int event_detected = (window_energy > THRESHOLD_VAL) ? 1 : 0;
  digitalWrite(LED_BUILTIN, event_detected ? LOW : HIGH);

  // Transmits 17-field CSV line over Serial
  Serial.print(timestamp);
  Serial.print(",");
  Serial.print(ax, 3);
  Serial.print(",");
  Serial.print(ay, 3);
  Serial.print(",");
  Serial.print(az, 3);
  Serial.print(",");
  Serial.print(gx, 3);
  Serial.print(",");
  Serial.print(gy, 3);
  Serial.print(",");
  Serial.print(gz, 3);
  Serial.print(",");
  Serial.print(a_total_raw, 3);
  Serial.print(",");
  Serial.print(filtered_ax, 3);
  Serial.print(",");
  Serial.print(filtered_ay, 3);
  Serial.print(",");
  Serial.print(filtered_az, 3);
  Serial.print(",");
  Serial.print(filtered_gx, 3);
  Serial.print(",");
  Serial.print(filtered_gy, 3);
  Serial.print(",");
  Serial.print(filtered_gz, 3);
  Serial.print(",");
  Serial.print(a_total_filt, 3);
  Serial.print(",");
  Serial.print(window_energy, 3);
  Serial.print(",");
  Serial.println(event_detected);
}