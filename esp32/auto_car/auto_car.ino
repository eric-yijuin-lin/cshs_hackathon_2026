const int MOTOR_IA = 16;
const int MOTOR_IB = 17;

const int PWM_FREQ = 20000;
const int PWM_RES = 8;

// 設定馬達速度（0~100%）
void setMotorSpeed(int speed) {
  speed = constrain(speed, 0, 100);
  int duty = map(speed, 0, 100, 0, 255);
  ledcWrite(MOTOR_IA, duty);
}

void setup() {
  pinMode(MOTOR_IB, OUTPUT);
  digitalWrite(MOTOR_IB, LOW);

  ledcAttach(MOTOR_IA, PWM_FREQ, PWM_RES);

  setMotorSpeed(70);  // 設定 70% 速度
}

void loop() {
  setMotorSpeed(80);  // 80% 運轉 2 秒
  delay(2000);

  setMotorSpeed(40);  // 40% 運轉 2 秒
  delay(2000);

  setMotorSpeed(0);   // 停止 2 秒
  delay(2000);
}