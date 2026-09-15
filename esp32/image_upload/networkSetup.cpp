#include "networkSetup.h"

bool initNetwork(NetworkConfig& config) {
  // 先連上 boot wifi，取得 server url 與 working wifi
  WiFi.mode(WIFI_STA);
  WiFi.disconnect(true); // 清除之前的 wifi 設定
  Serial.print("Connecting to ");
  Serial.println(bootSSID);
  WiFi.begin(bootSSID, bootPassword);  
  while (WiFi.status() != WL_CONNECTED) {
    Serial.println(WiFi.status());
    delay(500);
  }

  JsonDocument networkInfo;
  if (!getNetworkInfo(networkInfo)) {
    Serial.println("Failed to get network info");
    return false;
  }

  // 取得 working wifi 與 server url
  workingSSID = networkInfo["ssid"] | "";
  workingPassword = networkInfo["password"] | "";
  workingServerUrl = networkInfo["server_url"] | "";

  // 如果 working wifi 與 boot wifi 不同，切換到 working wifi
  if (!workingSSID.isEmpty() && !workingPassword.isEmpty() && workingSSID != bootSSID) {
    Serial.printf("Switching to working network: %s\n", workingSSID);
    WiFi.disconnect();
    WiFi.begin(workingSSID, workingPassword);
    while (WiFi.status() != WL_CONNECTED) {
      Serial.print(".");
      delay(500);
    }
  }

  Serial.println();
  Serial.print("ESP32-CAM IP Address: ");
  Serial.println(WiFi.localIP());
  return true;
}

bool getNetworkConfig(NetworkConfig& config) {
  JsonDocument doc;
  if (!getNetworkInfo(doc)) {
    return false;
  }

  config.ssid = doc["ssid"] | "";
  config.password = doc["password"] | "";
  config.server_url = doc["server_url"] | "";

  return true;

  Serial.println();
  Serial.printf("Fetching server info from: %s\n", boot_server_url.c_str());
  if (!http.begin(boot_client, boot_server_url)) {
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
