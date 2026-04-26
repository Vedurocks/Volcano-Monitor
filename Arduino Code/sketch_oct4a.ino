#include <LiquidCrystal.h>

LiquidCrystal lcd(12, 11, 6, 7, 8, 3);

// SENSORS - all digital pins
const int TRIG = 2;       // Ultrasonic trigger
const int ECHO = 4;       // Ultrasonic echo
const int VIBRATION = 5;  // Vibration sensor (digital pin)

// OUTPUTS - all digital pins
const int LED = 10;       // LED on digital pin
const int BUZZER = 13;    // Buzzer on digital pin (built-in LED pin)

// THRESHOLDS
float MIN_ULTRASONIC = 10.0;    // cm
int MIN_VIBRATION = 3;          // vibration count per second

// VARIABLES
float currentDist = 0;
int vibrationCount = 0;
bool systemActive = false;
bool killSwitchActive = false;

void setup() {
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);
  pinMode(VIBRATION, INPUT);
  pinMode(LED, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  
  digitalWrite(LED, LOW);
  noTone(BUZZER);
  
  lcd.begin(16, 2);
  Serial.begin(9600);
  while (!Serial) { ; }
  
  Serial.print("MIN_ULTRA:");
  Serial.print(MIN_ULTRASONIC);
  Serial.print(",MIN_VIB:");
  Serial.println(MIN_VIBRATION);
  
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
  
  // ALWAYS read both sensors
  currentDist = measureDistance();
  vibrationCount = countVibrations(1000);  // 1 second sample
  
  bool distanceAlert = (currentDist < MIN_ULTRASONIC);
  bool vibrationAlert = (vibrationCount >= MIN_VIBRATION);
  bool dualAlert = distanceAlert && vibrationAlert;
  
  // Send data to PC
  Serial.print(currentDist);
  Serial.print(",");
  Serial.print(vibrationCount);
  Serial.print(",");
  Serial.print(distanceAlert ? "DIST_ALERT" : "DIST_OK");
  Serial.print(",");
  Serial.print(vibrationAlert ? "VIB_ALERT" : "VIB_OK");
  Serial.print(",");
  Serial.print(dualAlert ? "DUAL_ALERT" : "DUAL_OK");
  Serial.print(",");
  Serial.print(killSwitchActive ? "KILL_ON" : "KILL_OFF");
  Serial.print(",");
  Serial.print(systemActive ? "SYS_ON" : "SYS_OFF");
  Serial.print(",");
  Serial.print(MIN_ULTRASONIC);
  Serial.print(",");
  Serial.println(MIN_VIBRATION);
  
  // LCD and outputs
  if (systemActive) {
    lcd.setCursor(0, 0);
    lcd.print("D:");
    lcd.print(currentDist, 0);
    lcd.print(" V:");
    lcd.print(vibrationCount);
    
    lcd.setCursor(0, 1);
    
    if (killSwitchActive) {
      if (!dualAlert) {
        killSwitchActive = false;
        lcd.print("KILL SW RESET   ");
        noTone(BUZZER);
      } else {
        lcd.print("KILL SWITCH OFF ");
        digitalWrite(LED, LOW);
        noTone(BUZZER);
      }
    }
    else if (dualAlert) {
      lcd.print("DUAL ALERT!     ");
      digitalWrite(LED, HIGH);
      tone(BUZZER, 1000);
    }
    else if (distanceAlert) {
      lcd.print("DIST ALERT ONLY ");
      digitalWrite(LED, LOW);
      noTone(BUZZER);
    }
    else if (vibrationAlert) {
      lcd.print("VIB ALERT ONLY  ");
      digitalWrite(LED, LOW);
      noTone(BUZZER);
    }
    else {
      lcd.print("OK              ");
      digitalWrite(LED, LOW);
      noTone(BUZZER);
    }
  } else {
    digitalWrite(LED, LOW);
    noTone(BUZZER);
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

int countVibrations(int sampleTime) {
  int count = 0;
  unsigned long start = millis();
  
  while (millis() - start < sampleTime) {
    if (digitalRead(VIBRATION) == HIGH) {
      count++;
      while (digitalRead(VIBRATION) == HIGH && millis() - start < sampleTime);
    }
  }
  return count;
}

void handleCommand(String cmd) {
  cmd.toLowerCase();
  
  if (cmd == "on") {
    systemActive = true;
    lcd.clear();
  }
  else if (cmd == "off") {
    systemActive = false;
    noTone(BUZZER);
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
    tone(BUZZER, 2000);
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
  else if (cmd.startsWith("min vib ")) {
    String val = cmd.substring(8);
    MIN_VIBRATION = val.toInt();
    Serial.print("NEW_MIN_VIB:");
    Serial.println(MIN_VIBRATION);
  }
}