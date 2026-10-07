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

  // print to serial output
  Serial.print("Accel (g): "); 
  Serial.print(ax, 3); 
  Serial.print(", ");
  Serial.print(ay, 3); 
  Serial.print(", ");
  Serial.print(az, 3); 
  Serial.print("\n");
  Serial.print("Gyro (degrees/s): "); 
  Serial.print(gx, 3); 
  Serial.print(", ");
  Serial.print(gy, 3); 
  Serial.print(", ");
  Serial.print(gz, 3); 
  Serial.print("\n");

  delay(100);

}