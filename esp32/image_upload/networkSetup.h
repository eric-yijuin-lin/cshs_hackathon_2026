#include <WiFi.h>
#include <ArduinoJson.h>

struct NetworkConfig {
  String ssid;
  String password;
  String server_url;
};

const char* deviceID = "TEST01";
const char* bootSSID     = "iPhone-YJL";
const char* bootPassword = "12345678";

bool initNetwork(NetworkConfig& config);
bool getNetworkConfig(NetworkConfig& config);