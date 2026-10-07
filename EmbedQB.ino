#include <Arduino.h>
#include <Wire.h>
#include "LSM6DS3.h"

// hardware pins

// setup and main loop 
void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LET_BUILTIN, HIGH); 
}

// main loop
void loop() { 

  Serial.println("i am doing stuff\n");
  delay(1000);

}