/*
 * ESP32 Welding Sensor Firmware
 * 
 * Expected libraries (subject to change):
 * - ArduinoJson (serialization)
 * - Adafruit_Sensor (sensor abstraction)
 * - Wire / SPI (hardware interfaces)
 *
 * CRITICAL RULES:
 * - Firmware must remain deterministic
 * - No dynamic allocation
 * - No sensor-side interpretation
 * - All calibration, filtering, and scoring happens server-side
 */

void setup() {
  // TODO: Initialize sensors and WiFi/BLE
}

void loop() {
  // TODO: Read sensors, timestamp, buffer, transmit
  // Raw sensor values only - no interpretation
}
