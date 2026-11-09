#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <networkHelper.h>
#include <cameraSetup.h>
#include "WavPlayer.h"

NetworkConfig networkConfig;

const int BUTTON_PIN = 47;
const int WAV_FILE_SHIFT = 4; // 便便類型的位移量，對應音檔索引

String wavCountUrl; // 取得音檔數量
String wavDownloadUrl; // 音檔下載
String checkPooUrl; // 檢查便便
String urgentCallUrl; // 緊急呼叫

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  bool network_ok = true;
  bool camera_ok = true;
  bool wav_ok = true;

  if (!initNetwork("toilet_box", networkConfig)) { // 連接 wifi
    Serial.println("Failed to initialize network.");
    network_ok = false;
  }
  delay(1000);
  
  if (!initCamera()) { 
    Serial.println("Failed to initialize camera.");
    camera_ok = false;
  }
  delay(1000);

  wavCountUrl = networkConfig.api_urls[0];
  wavDownloadUrl = networkConfig.api_urls[1];
  checkPooUrl = networkConfig.api_urls[2];
  urgentCallUrl = networkConfig.api_urls[3];

  if (!downloadAllWav()) {
    Serial.println("Failed to download WAV files, restart after 5 seconds.");
    wav_ok = false;
  }
  
  if (network_ok && camera_ok && wav_ok) {
    Serial.println("All devices initialized successfully.");
  } else {
    Serial.println("Initialization failed, restart after 10 seconds...");
    delay(10000);
    ESP.restart();
  }
}

void loop() {
  int state = digitalRead(BUTTON_PIN);
  if (state == HIGH) {
    playWAV(0); // 播放第一個音檔 (button-press)
    delay(3000);

    int pooType = -1;
    while (pooType < 0) {
      playWAV(1); // 播放第二個音檔 (capture)
      delay(1000);

      playWAV(2); // 播放第三個音檔 (uploading)
      delay(1000);

      pooType = checkPoo(); // 拍照並上傳便便，取得類型
      if (pooType < 0) {
        playWAV(3); // 播放第四個音檔 (try-again)
        delay(1000);
      }
    }

    playWAV(pooType + WAV_FILE_SHIFT); // 播放對應的便便音檔
    delay(1000);

    playWAV(10); // 播放第十個音檔 (flush)
    delay(1000);
  }
  delay(100);
}

bool downloadAllWav() {
  int wavCount = getWavFileCount(wavCountUrl);
  if (wavCount < 0) {
    Serial.println("Failed to get WAV file count");
    return false;
  }

  for (int i = 0; i < wavCount; i++) {
    if (!downloadWAV(wavDownloadUrl, i)) {
      Serial.printf("Failed to download WAV [%d]\n", i);
      return false;
    }
  }
  return true;
}

int checkPoo() {
    // 1. 拍照
    unsigned long captureStart = millis();

    camera_fb_t* fb = esp_camera_fb_get();

    if (!fb) {
        Serial.println("Camera capture failed");
        return -1;
    }

    unsigned long captureTime = millis() - captureStart;

    Serial.printf("Capture OK\n");
    Serial.printf("JPEG size: %u bytes\n", fb->len);
    Serial.printf("Capture time: %lu ms\n", captureTime);

    // 確認目前拿到的是 JPEG
    if (fb->format != PIXFORMAT_JPEG) {
        Serial.println("Captured image is not JPEG");
        esp_camera_fb_return(fb);
        return -1;
    }

    // 2. 建立 HTTP Client
    WiFiClient client;
    HTTPClient http;

    Serial.printf("Uploading to: %s\n", checkPooUrl.c_str());
    if (!http.begin(client, checkPooUrl)) {
        Serial.println("HTTP begin failed");
        esp_camera_fb_return(fb);
        return -1;
    }

    // 3. 告訴 Server：Body 就是一張 JPEG
    http.addHeader("Content-Type", "image/jpeg");

    // 4. 直接把 framebuffer 當 POST body
    unsigned long uploadStart = millis();

    int httpCode = http.POST(fb->buf, fb->len);

    unsigned long uploadTime = millis() - uploadStart;

    // 5. 檢查結果
    int pooType = -1;
    if (httpCode > 0) {
        Serial.printf("HTTP response: %d\n", httpCode);
        Serial.printf("Upload time: %lu ms\n", uploadTime);

        pooType = http.getString().toInt();
        Serial.printf("Server response: %d\n", pooType);
    }
    else {
        Serial.printf(
            "HTTP POST failed: %s\n",
            http.errorToString(httpCode).c_str()
        );
    }

    // 6. 關閉 HTTP
    http.end();

    // 7. 非常重要：把 framebuffer 還給 Camera
    esp_camera_fb_return(fb);

    return pooType;
}
