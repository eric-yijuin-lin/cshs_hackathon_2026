#include <Arduino.h>
#include <WiFi.h>
#include <networkHelper.h>
#include "WavPlayer.h"

NetworkConfig networkConfig;

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  if (!initNetwork("toilet_box", networkConfig)) { // 連接 wifi
    Serial.println("Failed to initialize network. Restart after 5 seconds.");
    delay(5000);
    ESP.restart();
  }

  String WAV_URL = networkConfig.api_urls[0];
  if (downloadWAV(WAV_URL)) {
    playWAV();
    releaseWAV();
  } else {
    Serial.println("Failed to download WAV");
  }
}

void loop() {
}
