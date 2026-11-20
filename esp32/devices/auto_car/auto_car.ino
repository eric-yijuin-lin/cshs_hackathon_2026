#include <ESP32Servo.h>
#include <WiFiClient.h>
#include <HTTPClient.h>
#include <networkHelper.h>
#include "SoundLevel.h"

const int MOTOR_IA = 16;
const int MOTOR_IB = 17;
const int SERVO_PIN = 18;

const int PWM_FREQ = 20000;
const int PWM_RES = 8;

String policeArea = "A";

Servo myServo;

NetworkConfig networkConfig;

struct PathNode {
    String start;
    String end;
    int weight;
    float direction;
};

PathNode bestPathNodes[10] = {};

// 設定 N20 馬達速度（-100 ~ 100%）
void setMotorSpeed(int speed) {
  speed = constrain(speed, -100, 100);
  int duty = map(abs(speed), 0, 100, 0, 255);

//   Serial.printf("[N20] speed=%d%%, duty=%d\n", speed, duty);

  bool iaOK, ibOK;

  if (speed > 0) {
    ibOK = ledcWrite(MOTOR_IB, 0);
    iaOK = ledcWrite(MOTOR_IA, duty);
  }
  else if (speed < 0) {
    iaOK = ledcWrite(MOTOR_IA, 0);
    ibOK = ledcWrite(MOTOR_IB, duty);
  }
  else {
    iaOK = ledcWrite(MOTOR_IA, 0);
    ibOK = ledcWrite(MOTOR_IB, 0);
  }

//   Serial.printf("[N20] PWM write: IA=%s, IB=%s\n",
//                 iaOK ? "OK" : "FAIL",
//                 ibOK ? "OK" : "FAIL");
}

// 設定 SG90 角度
void setServoAngle(int angle) {
  angle = constrain(angle, 0, 180);

//   Serial.printf("[SG90] Set angle = %d\n", angle);

  myServo.write(angle);

//   Serial.printf("[SG90] Read angle = %d\n", myServo.read());
}

// ===== Sound Level =====
SoundLevel sound(26, 25, 33, 104.0, 104.0);

// ===== Audio Data =====
struct AudioData
{
    SoundReading micA;
    SoundReading micB;
};

// FreeRTOS Queue
QueueHandle_t audioQueue = nullptr;


// ===== Audio Task =====
void audioTask(void* parameter)
{
    AudioData data;

    while (true)
    {
        if (sound.update(data.micA, data.micB))
        {
            // 將最新結果放入 Queue
            // Queue 長度為 1，覆蓋上一筆資料
            xQueueOverwrite(audioQueue, &data);
        }
    }
}

bool loadBestPath(NetworkConfig networkConfig) {
    WiFiClient client;
    HTTPClient http;
    String queryUrl = networkConfig.api_urls[0] // purpose 為 auto_car，使用 api_urls[0] 為取得最佳路徑
        + "?police=" + policeArea;
    
    Serial.printf("Querying: %s\n", queryUrl.c_str());
        if (!http.begin(client, queryUrl)) {
            Serial.println("HTTP begin failed");
            return false;
        }
        
    int httpCode = http.GET();
    if (httpCode > 0) {
        Serial.printf("HTTP response: %d\n", httpCode);

        String payload = http.getString();
        if (payload.isEmpty()) {
            Serial.println("Failed to load best path, payload is empty.");
            return false;
        }
        
        Serial.printf("Response payload: %s\n", payload.c_str());
        if (!deserializePathNodes(payload)) {
            Serial.println("Failed to deserialize path nodes.");
            return false;
        }
    }
    else {
        Serial.printf(
            "HTTP GET failed: %s\n",
            http.errorToString(httpCode).c_str()
        );
    }
    
    Serial.println("Deserialized path nodes:");
    printPathNodes();

    http.end();
    return true;
}

bool deserializePathNodes(String payload) {
  JsonDocument outJsonDoc;
  Serial.println("refresh bestPathNodes.");
  for (int i = 0; i < 10; i++) {
    bestPathNodes[i] = {};
  }

  Serial.println("Deserializing payload.");
  DeserializationError error = deserializeJson(outJsonDoc, payload);
  if (error) {
    Serial.println("Failed to deserialize payload.");
    return false;
  }
  if (!outJsonDoc.is<JsonArray>()) {
    Serial.println("Payload is not a json array");
    return false;
  }

  JsonArray array = outJsonDoc.as<JsonArray>();
  int nodeCount = 0;

  serializeJson(array, Serial);
  Serial.println();
  for (JsonObject obj : array) {
      if (nodeCount >= 10) break;

      // serializeJson(obj, Serial);
      // Serial.println();
      // Serial.printf("Assigning Nodes [%d]\n", nodeCount);
      // Serial.println(obj["start"].as<String>());
      // Serial.println(obj["end"].as<String>());
      // Serial.println(obj["weight"].as<int>());
      // Serial.println(obj["direction"].as<float>());

      bestPathNodes[nodeCount].start = obj["start"].as<String>();
      bestPathNodes[nodeCount].end = obj["end"].as<String>();
      bestPathNodes[nodeCount].weight = obj["weight"].as<int>();
      bestPathNodes[nodeCount].direction = obj["direction"].as<float>();

      nodeCount++;
  }
  return true;
}

void printPathNodes() {
  for(PathNode node : bestPathNodes) {
    Serial.printf("[PathNode] start: %s end: %s weight: %d direction: %f\n",
      node.start,
      node.end,
      node.weight,
      node.direction
    );
  }
}

void autoDrive() {
    for(PathNode node : bestPathNodes) {
        Serial.printf("Driving from %s to %s, weight: %d, degree: %f\n",
            node.start,
            node.end,
            node.weight,
            node.direction
        );
        turnDirection(node.direction);
        // setMotorSpeed(80);
        Serial.printf("Turn direction finished, go strait for %d ms.\n", node.weight * 500);
        delay(node.weight * 800); // 目前以 0.6 秒為單位
    }
}

void turnDirection(float origDegree) {
    int delayMs = (int)3000/90 * origDegree; // 以 3 秒轉 90 度測試 (1 度 2 ms)
    if (origDegree == 0) {
        return;
    }
    else if (origDegree > 0) {
        setServoAngle(45); // 目前以 90 度為直線，135 度為左轉
        Serial.printf("orgDegree = %f, turning right, delay = %d\n", origDegree, delayMs);
    }
    else {
        setServoAngle(135); // 目前以 90 度為直線，45 度為右轉
        delayMs *= -1; // 負號反正才能當 delay 參數
        Serial.printf("orgDegree = %f, turning left, delay = %d\n", origDegree, delayMs);
    }
    setMotorSpeed(80);
    delay(delayMs); 
    setServoAngle(90); // 回正
}

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println("===== ESP32 Motor Debug Start =====");

  // 1. 先初始化 SG90
  Serial.println("[INIT] Initializing SG90...");

  myServo.setPeriodHertz(50);
  myServo.attach(SERVO_PIN, 1000, 2000);

  Serial.printf("[INIT] Servo attached: %s\n",
                myServo.attached() ? "YES" : "NO");

  setServoAngle(90);

  // 2. 再初始化 N20
  Serial.println("[INIT] Initializing N20 PWM...");

  bool iaOK = ledcAttach(MOTOR_IA, PWM_FREQ, PWM_RES);
  bool ibOK = ledcAttach(MOTOR_IB, PWM_FREQ, PWM_RES);

  Serial.printf("[INIT] IA attach: %s\n",
                iaOK ? "OK" : "FAIL");
  Serial.printf("[INIT] IB attach: %s\n",
                ibOK ? "OK" : "FAIL");

  setMotorSpeed(0);

  // 3. 顯示實際 PWM 頻率
  Serial.printf("[DEBUG] IA freq: %lu Hz\n",
                ledcReadFreq(MOTOR_IA));
  Serial.printf("[DEBUG] IB freq: %lu Hz\n",
                ledcReadFreq(MOTOR_IB));
  Serial.printf("[DEBUG] SG90 freq: %lu Hz\n",
                ledcReadFreq(SERVO_PIN));

  Serial.println("[INIT] Setup completed.");

  // ========= 分貝相關 =============
  if (!sound.begin())
  {
      Serial.println("I2S init failed");
      while (true) delay(1000);
  }

  // 建立只能存放一筆 AudioData 的 Queue
  audioQueue = xQueueCreate(1, sizeof(AudioData));

  if (audioQueue == nullptr)
  {
      Serial.println("Queue creation failed");
      while (true) delay(1000);
  }

  // 建立 Audio Task
  BaseType_t result = xTaskCreatePinnedToCore(
      audioTask,
      "AudioTask",
      4096,
      nullptr,
      1,
      nullptr,
      0
  );

  if (result != pdPASS)
  {
      Serial.println("Audio Task creation failed");
      while (true) delay(1000);
  }

  // 初始化網路
  if (!initNetwork("auto_car", networkConfig)) { // 連接 wifi
    Serial.println("Failed to initialize network. Restart after 10 seconds");
    delay(10000);
    ESP.restart();
  }
  delay(1000);

  // 取得巡邏輔助最佳路徑
  if(!loadBestPath(networkConfig)) {
    Serial.println("Failed to load best path. Restart after 10 seconds");
    delay(10000);
    ESP.restart();
  }
  
  Serial.println("Starting auto driving.");
  autoDrive();
  Serial.println("Auto driving finished. Slow down for sound tracking.");
  setMotorSpeed(50);
  delay(1000);
  setMotorSpeed(20);
  delay(1000);
  setMotorSpeed(0);
  delay(1000);
}

void loop() {
  AudioData data;
  // 不等待音訊，直接讀取 Queue 中的最新資料
  if (xQueuePeek(audioQueue, &data, 0) == pdTRUE)
  {
      // ===== 這裡就是 Control 取得音訊資料的位置 =====
      double dbA = data.micA.rmsDbFS;
      double dbB = data.micB.rmsDbFS;
      double difference = dbA - dbB;

    //   printf("[DEBUG] Mic A: %.1f dB, Mic B: %.1f dB, Difference: %.1f dB\n",
    //             dbA, dbB, difference);

      if (difference > 5) {
          Serial.println("[CONTROL] Mic A louder than Mic B");
          setServoAngle(135);
      }
      else if (difference < -5) 
      {
          Serial.println("[CONTROL] Mic B louder than Mic A");
          setServoAngle(45);
      }
      else 
      {
          // Serial.println("[CONTROL] Mic A and Mic B are similar");
          setServoAngle(90);
      }
  }

  setMotorSpeed(80);
  delay(1000);
}
