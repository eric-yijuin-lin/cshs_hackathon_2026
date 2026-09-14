#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
// #include <WiFiClient.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "esp_camera.h"

const char* device_id = "TEST01";
const char* boot_ssid     = "iPhone-YJL";
const char* boot_password = "12345678";
String working_ssid = "";
String working_password = "";
String serverUrl = "";

const int serverPort = 80;
const int cameraInitRetry = 10;

// freenove ESP32S3 屬於 CAMERA_MODEL_ESP32S3_EYE
#define PWDN_GPIO_NUM -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 15
#define SIOD_GPIO_NUM 4
#define SIOC_GPIO_NUM 5
#define Y2_GPIO_NUM 11
#define Y3_GPIO_NUM 9
#define Y4_GPIO_NUM 8
#define Y5_GPIO_NUM 10
#define Y6_GPIO_NUM 12
#define Y7_GPIO_NUM 18
#define Y8_GPIO_NUM 17
#define Y9_GPIO_NUM 16
#define VSYNC_GPIO_NUM 6
#define HREF_GPIO_NUM 7
#define PCLK_GPIO_NUM 13


const int httpInterval = 500;

void setupCamera();
void avoidBrownOut(int seconds);
void initNetwork();
String getServerName();
bool takeAndUploadPhoto();

void setup() {
  Serial.begin(115200);
  // setupCamera(); // 設定並初始化相機
  avoidBrownOut(5); // 等待數秒避免電壓不穩
  initNetwork(); // 連接 wifi
}

void loop() {
  // takeAndUploadPhoto();
  delay(httpInterval);
}

void setupCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 10000000;
  config.frame_size = FRAMESIZE_SVGA;
  config.pixel_format = PIXFORMAT_JPEG; // for streaming
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 2;

  // if PSRAM IC present, init with UXGA resolution and higher JPEG quality
  // for larger pre-allocated frame buffer.
  if(psramFound()){
    Serial.printf("PARAM found, setting higher quality.");
    config.jpeg_quality = 4;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
  } else {
    // Limit the frame size when PSRAM is not available
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }
  
  // camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    delay(1000);
    ESP.restart();
  }
}

void avoidBrownOut(int seconds) {
  // 不關閉 brown out detector，避免電壓不夠 esp32 硬撐找不到 bug
  // WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); 
  Serial.print("waiting for a moment, avoiding brown out");
  for (int i=0; i<seconds; i++)
  {
    Serial.print(".");
    delay(1000);
  }
  Serial.println();
}

void initNetwork() {
  WiFi.mode(WIFI_STA);
  Serial.print("Connecting to ");
  Serial.println(boot_ssid);
  WiFi.begin(boot_ssid, boot_password);  
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }

  JsonDocument networkInfo;
  if (getNetworkInfo(networkInfo)) {
    String ssid = networkInfo["ssid"] | "";
    String password = networkInfo["password"] | "";
    String server_url = networkInfo["server_url"] | "";
    serverUrl = server_url;

    if (!ssid.isEmpty() && !password.isEmpty() && ssid != boot_ssid) {
      Serial.printf("Switching to working network: %s\n", ssid);
      WiFi.disconnect();
      WiFi.begin(ssid, password);
      while (WiFi.status() != WL_CONNECTED) {
        Serial.print(".");
        delay(500);
      }
    }
  }

  Serial.println();
  Serial.print("ESP32-CAM IP Address: ");
  Serial.println(WiFi.localIP());
}

bool getNetworkInfo(JsonDocument& doc) {
  String server_url = "https://example.com/get-server-info";
  WiFiClientSecure client;
  client.setInsecure();
  HTTPClient http;

  Serial.println();
  Serial.printf("Fetching server info from: %s\n", server_url.c_str());
  if (!http.begin(client, server_url)) {
      Serial.println("HTTP begin failed");
      return false;
  }

  int httpCode = http.GET();
  Serial.printf(
      "HTTP status code: %d\n",
      httpCode
  );

  if (httpCode > 0) {
      String payload = http.getString();
      DeserializationError error = deserializeJson(doc, payload);

      if (error) {
          Serial.print("JSON parse failed: ");
          Serial.println(error.c_str());
          return false;
      }

      printf("Server info received: %s\n", payload.c_str());
  } else {
      Serial.printf(
          "GET failed: %s\n",
          http.errorToString(httpCode).c_str()
      );
      return false;
  }
  http.end();
  return true;
}

bool takeAndUploadPhoto() {
    // 1. 拍照
    unsigned long captureStart = millis();

    camera_fb_t* fb = esp_camera_fb_get();

    if (!fb) {
        Serial.println("Camera capture failed");
        return false;
    }

    unsigned long captureTime = millis() - captureStart;

    Serial.printf("Capture OK\n");
    Serial.printf("JPEG size: %u bytes\n", fb->len);
    Serial.printf("Capture time: %lu ms\n", captureTime);

    // 確認目前拿到的是 JPEG
    if (fb->format != PIXFORMAT_JPEG) {
        Serial.println("Captured image is not JPEG");
        esp_camera_fb_return(fb);
        return false;
    }

    // 2. 建立 HTTP Client
    WiFiClient client;
    HTTPClient http;
    Serial.println("[debug] in takePhoto");
    Serial.println(serverUrl);
    String uploadUrl = serverUrl + "/esp32/image-upload";

    if (!http.begin(client, uploadUrl)) {
        Serial.println("HTTP begin failed");
        esp_camera_fb_return(fb);
        return false;
    }

    // 3. 告訴 Server：Body 就是一張 JPEG
    http.addHeader("Content-Type", "image/jpeg");
    http.addHeader("X-Device-ID", device_id);

    // 4. 直接把 framebuffer 當 POST body
    unsigned long uploadStart = millis();

    int httpCode = http.POST(fb->buf, fb->len);

    unsigned long uploadTime = millis() - uploadStart;

    // 5. 檢查結果
    if (httpCode > 0) {
        Serial.printf("HTTP response: %d\n", httpCode);
        Serial.printf("Upload time: %lu ms\n", uploadTime);

        String response = http.getString();
        Serial.printf("Server response: %s\n", response.c_str());
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

    return httpCode >= 200 && httpCode < 300;
}