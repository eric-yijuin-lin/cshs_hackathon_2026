
#include <ESP32Servo.h>

const int MOTOR_IA = 16;
const int MOTOR_IB = 17;
const int SERVO_PIN = 18;

const int PWM_FREQ = 20000;
const int PWM_RES = 8;

Servo myServo;

// 設定 N20 馬達速度（-100 ~ 100%）
void setMotorSpeed(int speed) {
  speed = constrain(speed, -100, 100);
  int duty = map(abs(speed), 0, 100, 0, 255);

  Serial.printf("[N20] speed=%d%%, duty=%d\n", speed, duty);

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

  Serial.printf("[N20] PWM write: IA=%s, IB=%s\n",
                iaOK ? "OK" : "FAIL",
                ibOK ? "OK" : "FAIL");
}

// 設定 SG90 角度
void setServoAngle(int angle) {
  angle = constrain(angle, 0, 180);

  Serial.printf("[SG90] Set angle = %d\n", angle);

  myServo.write(angle);

  Serial.printf("[SG90] Read angle = %d\n", myServo.read());
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
}


void loop() {
  // 1. 90 度，前進 2 秒
  setServoAngle(90);
  setMotorSpeed(80);
  delay(2000);

  // 2. 保持 90 度，後退 2 秒
  setMotorSpeed(0);
  delay(300);
  setMotorSpeed(-80);
  delay(2000);

  // 3. 45 度，前進 2 秒
  setMotorSpeed(0);
  setServoAngle(45);
  delay(500);
  setMotorSpeed(80);
  delay(2000);

  // 4. 保持 45 度，後退 2 秒
  setMotorSpeed(0);
  delay(300);
  setMotorSpeed(-80);
  delay(2000);

  // 5. 135 度，前進 2 秒
  setMotorSpeed(0);
  setServoAngle(135);
  delay(500);
  setMotorSpeed(80);
  delay(2000);

  // 6. 保持 135 度，後退 2 秒
  setMotorSpeed(0);
  delay(300);
  setMotorSpeed(-80);
  delay(2000);

  // 結束一輪，停止 1 秒
  setMotorSpeed(0);
  delay(1000);
}
