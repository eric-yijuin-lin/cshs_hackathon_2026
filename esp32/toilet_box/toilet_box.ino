#include <Arduino.h>
#include <WiFi.h>
#include "WavPlayer.h"

const char* WIFI_SSID = "iPhone-YJL";
const char* WIFI_PASSWORD = "12345678";

const char* WAV_URL = "https://demo.goattl.net/esp32/audio_download";

void setup() {
  Serial.begin(115200);
  delay(1000);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Connecting WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected!");

  if (downloadWAV(WAV_URL)) {
    playWAV();
    releaseWAV();
  } else {
    Serial.println("Failed to download WAV");
  }
}

void loop() {
}
