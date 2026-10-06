#include <ArduinoJson.h>

struct NetworkConfig {
  String ssid;
  String password;
  String api_urls[5]; // 由各個模組的用途決定，最多 5 個 URL
};


bool initNetwork(String purpose, NetworkConfig& config);
bool fetchConfigFromBootServer(String purpose,JsonDocument& outJsonDoc);