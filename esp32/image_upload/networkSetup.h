#include <ArduinoJson.h>

struct NetworkConfig {
  String ssid;
  String password;
  String server_url;
};


bool initNetwork(NetworkConfig& config);
bool fetchConfigFromBootServer(JsonDocument& outJsonDoc);