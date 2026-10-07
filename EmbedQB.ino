#include <Arduino.h>
#include <Wire.h>
#include "LSM6DS3.h"

// hardware pins
const uint8_t IMU_PWR_PIN = PD5;

// setup and main loop 
void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH); 

  // power on sensor
  pinMode(IMU_PWR_PIN, OUTPUT); 
  digitalWrite(IMU_PWR_PIN, HIGH);

  Wire.begin();
}

// main loop
void loop() { 

  Serial.println("i am doing stuff\n");
  delay(1000);

  

}