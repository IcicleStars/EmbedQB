#include <Arduino.h>
#include <Wire.h>
#include "LSM6DS3.h"

// hardware pins
const uint8_t IMU_PWR_PIN = PD5;

// initialize IMU instance
LSM6DS3 myIMU(I2C_MODE, 0x6A);

// setup and main loop 
void setup() {
  Serial.begin(115200);

  // delay to allow for connection
  while (!Serial && millis() < 3000) {
    delay(10);
  }

  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH); 

  // power on sensor
  pinMode(IMU_PWR_PIN, OUTPUT); 
  digitalWrite(IMU_PWR_PIN, HIGH);

  Wire.begin();

  // initialize IMU 
  if (myIMU.begin()) { 
    // light up because BROKEN!
    while (1) {
      digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
      delay(200);
    }
  }

  // circuit and sensor configuration: 416 Hz ODR, +/-16g scale, 2000 dps
  myIMU.writeRegister(LSM6DS3_ACC_GYRO_CTRL1_XL, 0x84);
  myIMU.writeRegister(LSM6DS3_ACC_GYRO_CTRL2_G, 0x8C);

}

// filter variables 
const float ALPHA = 0.50f; 
float filtered_ax = 0.0f;
float filtered_ay = 0.0f;
float filtered_az = 0.0f;
float filtered_gx = 0.0f;
float filtered_gy = 0.0f;
float filtered_gz = 0.0f;

inline float EWMA(float raw, float prev, float alpha) { 
  return (alpha * raw) + ((1.0f - alpha) * prev);
}

// main loop
void loop() { 
  // linear acceleration
  float ax = myIMU.readFloatAccelX();
  float ay = myIMU.readFloatAccelY();
  float az = myIMU.readFloatAccelZ();

  // gyroscope velocity
  float gx = myIMU.readFloatGyroX();
  float gy = myIMU.readFloatGyroY(); 
  float gz = myIMU.readFloatGyroZ();

  // filtered variables.
  filtered_ax = EWMA(ax, filtered_ax, ALPHA);
  filtered_ay = EWMA(ay, filtered_ay, ALPHA);
  filtered_az = EWMA(az, filtered_az, ALPHA);
  filtered_gx = EWMA(gx, filtered_gx, ALPHA);
  filtered_gy = EWMA(gy, filtered_gy, ALPHA);
  filtered_gz = EWMA(gz, filtered_gz, ALPHA);
  
  

  // print to serial output
  // NO FILTER 
  Serial.print(millis()); 
  Serial.print(", ");
  Serial.print(ax, 3); 
  Serial.print(", ");
  Serial.print(ay, 3); 
  Serial.print(", ");
  Serial.print(az, 3); 
  Serial.print(", ");
  Serial.print(gx, 3); 
  Serial.print(", ");
  Serial.print(gy, 3); 
  Serial.print(", ");
  Serial.print(gz, 3);
  // YES FILTER
  Serial.print(millis()); 
  Serial.print(", ");
  Serial.print(filtered_ax, 3); 
  Serial.print(", ");
  Serial.print(filtered_ay, 3); 
  Serial.print(", ");
  Serial.print(filtered_az, 3); 
  Serial.print(", ");
  Serial.print(filtered_gx, 3); 
  Serial.print(", ");
  Serial.print(filtered_gy, 3); 
  Serial.print(", ");
  Serial.println(filtered_gz, 3);

  delay(2);

}