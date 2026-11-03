#include "networkHelper.h"

NetworkConfig networkConfig;

void setup() {
  Serial.begin(115200);
  if (!initNetwork("img_inference", networkConfig)) { // 連接 wifi
    Serial.println("Failed to initialize network. Restart after 10 seconds.");
    delay(10000);
    ESP.restart();
  }

  Serial.println("Network config: ");
  Serial.printf("SSID: %s\n", networkConfig.ssid.c_str());
  Serial.printf("Password: %s\n", networkConfig.password.c_str());
  Serial.printf( networkConfig.api_urls[0].c_str());

}

void loop() {
  // 這個範例程式不需要做任何事情，因為主要是測試網路連線與設定
  delay(1000);
}