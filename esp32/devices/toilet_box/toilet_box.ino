#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <networkHelper.h>
#include <cameraSetup.h>
#include "WavPlayer.h"

NetworkConfig networkConfig;

const int CAPTURE_BUTTON_PIN = 14;
const int URGENT_BUTTON_PIN = 47;
const int WAV_FILE_SHIFT = 4; // 便便類型的位移量，對應音檔索引


int captureState = LOW;
int urgentState = LOW;

String deviceID = "toilet_1"; // 設備 ID
String wavCountUrl; // 取得音檔數量
String wavDownloadUrl; // 音檔下載
String checkPooUrl; // 檢查便便
String urgentCallUrl; // 緊急呼叫

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  bool wav_ok = true;
  bool network_ok = true;
  bool camera_ok = true;

  pinMode(CAPTURE_BUTTON_PIN, INPUT);
  pinMode(URGENT_BUTTON_PIN,  INPUT);
  
  if (!loadWavFromSD()) {
    Serial.println("Failed to load wav files from SD card!");
    wav_ok = false;
  }

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
  
  if (wav_ok && network_ok && camera_ok) {
    Serial.println("All devices initialized successfully.");
  } else {
    Serial.println("Initialization failed, restart after 10 seconds...");
    delay(10000);
    ESP.restart();
  }
}

void loop() {
  captureState = digitalRead(CAPTURE_BUTTON_PIN);
  urgentState = digitalRead(URGENT_BUTTON_PIN);

  // Serial.print("captureState: ");
  // Serial.println(captureState);
  // Serial.print("urgentState: ");
  // Serial.println(urgentState);

  if (captureState == HIGH) {
    playWAV("button-press");

    String pooType = "unknown";
    while (pooType == "unknown") {
      playWAV("capture");
      delay(1000);

      playWAV("uploading");
      delay(1000);

      pooType = checkPoo(); // 拍照並上傳便便，取得類型
      Serial.printf("Poo checking finished, type: %s\n", pooType);
      if (pooType == "unknown") {
        playWAV("try-again");
        delay(1000);
      }
    }

    playWAV(pooType); // 播放對應的便便音檔
    delay(1000);

    playWAV("flush");
    delay(1000);
  } else if (urgentState == HIGH) {
    Serial.println("urgentState == HIGH");
    if (urgentCall()) {
      playWAV("urgent-call");
      delay(1000);
    }
  }

  delay(100);
}

String checkPoo() {
    // 1. 拍照
    unsigned long captureStart = millis();

    camera_fb_t* fb = esp_camera_fb_get();

    if (!fb) {
        Serial.println("Camera capture failed");
        return "unknown";
    }

    unsigned long captureTime = millis() - captureStart;

    Serial.printf("Capture OK\n");
    Serial.printf("JPEG size: %u bytes\n", fb->len);
    Serial.printf("Capture time: %lu ms\n", captureTime);

    // 確認目前拿到的是 JPEG
    if (fb->format != PIXFORMAT_JPEG) {
        Serial.println("Captured image is not JPEG");
        esp_camera_fb_return(fb);
        return "unknown";
    }

    // 2. 建立 HTTP Client
    WiFiClient client;
    HTTPClient http;

    Serial.printf("Uploading to: %s\n", checkPooUrl.c_str());
    if (!http.begin(client, checkPooUrl)) {
        Serial.println("HTTP begin failed");
        esp_camera_fb_return(fb);
        return "unknown";
    }

    // 3. 告訴 Server：Body 就是一張 JPEG
    http.addHeader("X-Device-ID", deviceID);
    http.addHeader("Content-Type", "image/jpeg");

    // 4. 直接把 framebuffer 當 POST body
    unsigned long uploadStart = millis();

    int httpCode = http.POST(fb->buf, fb->len);

    unsigned long uploadTime = millis() - uploadStart;

    // 5. 檢查結果
    String pooType = "unknown";
    if (httpCode > 0) {
        Serial.printf("HTTP response: %d\n", httpCode);
        Serial.printf("Upload time: %lu ms\n", uploadTime);

        pooType = http.getString();
        Serial.printf("Server response: %s\n", pooType);
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

bool urgentCall() {
    WiFiClient client;
    HTTPClient http;

    Serial.printf("Querying: %s\n", urgentCallUrl.c_str());
    if (!http.begin(client, urgentCallUrl)) {
        Serial.println("HTTP begin failed");
        return false;
    }

    http.addHeader("X-Device-ID", deviceID);

    int httpCode = http.GET();
    if (httpCode > 0) {
        Serial.printf("HTTP response: %d\n", httpCode);

        String response = http.getString();
        Serial.printf("Server response: %s\n", response.c_str());
    }
    else {
        Serial.printf(
            "HTTP POST failed: %s\n",
            http.errorToString(httpCode).c_str()
        );
    }

    http.end();
    return true;
}
