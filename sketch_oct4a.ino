 #include <LiquidCrystal.h>
#include <math.h>

LiquidCrystal lcd(12, 11, 6, 7, 8, 3);

const int TRIG = 2;
const int ECHO = 4;
const int ACC_X = A2;
const int ACC_Y = A3;
const int ACC_Z = A4;

const int LED = A0;
const int BUZZER = A1;  // Buzzer pin (was POWER_PIN)

float MIN_ULTRASONIC = 10.0;
float MIN_SEISMIC = 1.5;

const float ZERO_G = 512.0;
const float SCALE = 102.3;

float currentDist = 0;
float seismicMagnitude = 0;
bool systemActive = false;
bool killSwitchActive = false;

void setup() {
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);
  pinMode(LED, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  
  digitalWrite(LED, LOW);
  noTone(BUZZER);  // Ensure buzzer off
  
  lcd.begin(16, 2);
  Serial.begin(9600);
  while (!Serial) { ; }
  
  Serial.print("MIN_ULTRA:");
  Serial.print(MIN_ULTRASONIC);
  Serial.print(",MIN_SEIS:");
  Serial.println(MIN_SEISMIC);
  
  lcd.print("Volcano Monitor");
  lcd.setCursor(0, 1);
  lcd.print("Send 'on' to start");
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    handleCommand(command);
  }
  
  currentDist = measureDistance();
  seismicMagnitude = readSeismicSensor();
  
  bool distanceAlert = (currentDist < MIN_ULTRASONIC);
  bool seismicAlert = (seismicMagnitude > MIN_SEISMIC);
  bool dualAlert = distanceAlert && seismicAlert;
  
  Serial.print(currentDist);
  Serial.print(",");
  Serial.print(seismicMagnitude);
  Serial.print(",");
  Serial.print(distanceAlert ? "DIST_ALERT" : "DIST_OK");
  Serial.print(",");
  Serial.print(seismicAlert ? "SEIS_ALERT" : "SEIS_OK");
  Serial.print(",");
  Serial.print(dualAlert ? "DUAL_ALERT" : "DUAL_OK");
  Serial.print(",");
  Serial.print(killSwitchActive ? "KILL_ON" : "KILL_OFF");
  Serial.print(",");
  Serial.print(systemActive ? "SYS_ON" : "SYS_OFF");
  Serial.print(",");
  Serial.print(MIN_ULTRASONIC);
  Serial.print(",");
  Serial.println(MIN_SEISMIC);
  
  if (systemActive) {
    lcd.setCursor(0, 0);
    lcd.print("D:");
    lcd.print(currentDist, 0);
    lcd.print(" S:");
    lcd.print(seismicMagnitude, 1);
    
    lcd.setCursor(0, 1);
    
    if (killSwitchActive) {
      if (!dualAlert) {
        killSwitchActive = false;
        lcd.print("KILL SW RESET   ");
        noTone(BUZZER);  // Buzzer off
      } else {
        lcd.print("KILL SWITCH OFF ");
        digitalWrite(LED, LOW);
        noTone(BUZZER);  // Buzzer off
      }
    }
    else if (dualAlert) {
      lcd.print("DUAL ALERT!     ");
      digitalWrite(LED, HIGH);
      tone(BUZZER, 1000);  // 1000Hz loud tone
    }
    else if (distanceAlert) {
      lcd.print("DIST ALERT ONLY ");
      digitalWrite(LED, LOW);
      noTone(BUZZER);  // Buzzer off
    }
    else if (seismicAlert) {
      lcd.print("SEIS ALERT ONLY ");
      digitalWrite(LED, LOW);
      noTone(BUZZER);  // Buzzer off
    }
    else {
      lcd.print("OK              ");
      digitalWrite(LED, LOW);
      noTone(BUZZER);  // Buzzer off
    }
  } else {
    digitalWrite(LED, LOW);
    noTone(BUZZER);  // Buzzer off
    lcd.setCursor(0, 0);
    lcd.print("SYSTEM OFF      ");
    lcd.setCursor(0, 1);
    lcd.print("Send 'on' to run");
  }
  
  delay(500);
}

float measureDistance() {
  digitalWrite(TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);
  long duration = pulseIn(ECHO, HIGH, 30000);
  if (duration == 0) return -1;
  return duration * 0.034 / 2;
}

float readSeismicSensor() {
  int xRaw = analogRead(ACC_X);
  int yRaw = analogRead(ACC_Y);
  int zRaw = analogRead(ACC_Z);
  
  float xG = (xRaw - ZERO_G) / SCALE;
  float yG = (yRaw - ZERO_G) / SCALE;
  float zG = (zRaw - ZERO_G) / SCALE;
  
  return sqrt(xG*xG + yG*yG + zG*zG);
}

void handleCommand(String cmd) {
  cmd.toLowerCase();
  
  if (cmd == "on") {
    systemActive = true;
    lcd.clear();
  }
  else if (cmd == "off") {
    systemActive = false;
    noTone(BUZZER);  // Ensure buzzer off
    lcd.clear();
  }
  else if (cmd == "kill") {
    killSwitchActive = true;
  }
  else if (cmd == "reset") {
    killSwitchActive = false;
  }
  else if (cmd == "456") {
    lcd.setCursor(0, 1);
    lcd.print("FORCED DUAL ALERT");
    digitalWrite(LED, HIGH);
    tone(BUZZER, 2000);  // High pitch test
    delay(2000);
    noTone(BUZZER);
    digitalWrite(LED, LOW);
  }
  else if (cmd.startsWith("min ult ")) {
    String val = cmd.substring(8);
    MIN_ULTRASONIC = val.toFloat();
    Serial.print("NEW_MIN_ULTRA:");
    Serial.println(MIN_ULTRASONIC);
  }
  else if (cmd.startsWith("min sei ")) {
    String val = cmd.substring(8);
    MIN_SEISMIC = val.toFloat();
    Serial.print("NEW_MIN_SEIS:");
    Serial.println(MIN_SEISMIC);
  }
}