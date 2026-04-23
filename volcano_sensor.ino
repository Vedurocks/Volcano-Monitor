// ============================================
// VOLCANO ERUPTION SYSTEM
// Arduino Uno + HC-SR04 + Vibration Sensor
// ============================================

// SENSORS - Digital Pins
const int TRIG = 2;       // HC-SR04 Trigger
const int ECHO = 4;       // HC-SR04 Echo
const int VIBRATION = 5;  // SW-180P Vibration Sensor

// OUTPUTS - Digital Pins
const int LED = 10;       // Alert LED
const int BUZZER = 13;    // Alert Buzzer

// THRESHOLDS (Changeable from PC)
float MIN_ULTRASONIC = 10.0;    // cm - distance threshold
int MIN_VIBRATION = 3;          // count - vibration threshold per second

// VARIABLES
float currentDist = 0;          // Current distance reading
int vibrationCount = 0;         // Current vibration count
bool systemActive = false;      // System ON/OFF state
bool killSwitchActive = false;  // Kill switch state

// ============================================
// SETUP
// ============================================
void setup() {
  // Pin modes
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);
  pinMode(VIBRATION, INPUT);
  pinMode(LED, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  
  // Initial states
  digitalWrite(LED, LOW);
  noTone(BUZZER);
  
  // Start serial communication
  Serial.begin(9600);
  
  // Wait for serial connection
  while (!Serial) { ; }
  
  // Send initial thresholds to PC
  Serial.print("MIN_ULTRA:");
  Serial.print(MIN_ULTRASONIC);
  Serial.print(",MIN_VIB:");
  Serial.println(MIN_VIBRATION);
}

// ============================================
// MAIN LOOP
// ============================================
void loop() {
  // Check for commands from PC
  checkSerialCommands();
  
  // Read sensors (always)
  currentDist = measureDistance();
  vibrationCount = countVibrations(1000); // 1 second sample
  
  // Determine alert states
  bool distanceAlert = (currentDist < MIN_ULTRASONIC);
  bool vibrationAlert = (vibrationCount >= MIN_VIBRATION);
  bool dualAlert = distanceAlert && vibrationAlert;
  
  // Send data to PC (always)
  sendDataToPC(distanceAlert, vibrationAlert, dualAlert);
  
  // Control outputs (only if system active)
  if (systemActive) {
    controlOutputs(dualAlert);
  } else {
    // System off - everything off
    digitalWrite(LED, LOW);
    noTone(BUZZER);
  }
  
  delay(500); // 500ms loop delay
}

// ============================================
// SENSOR FUNCTIONS
// ============================================

// Measure distance with HC-SR04
float measureDistance() {
  // Clear trigger
  digitalWrite(TRIG, LOW);
  delayMicroseconds(2);
  
  // Send 10us pulse
  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);
  
  // Read echo duration (30ms timeout)
  long duration = pulseIn(ECHO, HIGH, 30000);
  
  // Timeout check
  if (duration == 0) return -1;
  
  // Calculate distance: speed of sound = 0.034 cm/us
  // Divide by 2 for round trip
  float distance = duration * 0.034 / 2;
  
  return distance;
}

// Count vibrations in sample time (milliseconds)
int countVibrations(int sampleTime) {
  int count = 0;
  unsigned long startTime = millis();
  
  while (millis() - startTime < sampleTime) {
    if (digitalRead(VIBRATION) == HIGH) {
      count++;
      // Wait for signal to go low (debounce)
      while (digitalRead(VIBRATION) == HIGH && millis() - startTime < sampleTime);
    }
  }
  
  return count;
}

// ============================================
// OUTPUT CONTROL
// ============================================

void controlOutputs(bool dualAlert) {
  if (killSwitchActive) {
    // Kill switch active - check if can reset
    if (!dualAlert) {
      killSwitchActive = false; // Auto-reset when safe
      digitalWrite(LED, LOW);
      noTone(BUZZER);
    } else {
      // Kill switch holding - suppress alarm
      digitalWrite(LED, LOW);
      noTone(BUZZER);
    }
  }
  else if (dualAlert) {
    // BOTH sensors triggered - FULL ALERT
    digitalWrite(LED, HIGH);
    tone(BUZZER, 1000); // 1kHz tone
  }
  else {
    // No dual alert - safe
    digitalWrite(LED, LOW);
    noTone(BUZZER);
  }
}

// ============================================
// SERIAL COMMUNICATION
// ============================================

void checkSerialCommands() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    // Ignore empty or numeric-only strings (sensor data)
    if (command.length() == 0) return;
    if (isDigit(command.charAt(0))) return;
    
    // Process command
    processCommand(command);
  }
}

void processCommand(String cmd) {
  cmd.toLowerCase();
  
  if (cmd == "on") {
    systemActive = true;
    Serial.println("CMD_OK:SYSTEM_ON");
  }
  else if (cmd == "off") {
    systemActive = false;
    digitalWrite(LED, LOW);
    noTone(BUZZER);
    Serial.println("CMD_OK:SYSTEM_OFF");
  }
  else if (cmd == "kill") {
    killSwitchActive = true;
    Serial.println("CMD_OK:KILL_ON");
  }
  else if (cmd == "reset") {
    killSwitchActive = false;
    Serial.println("CMD_OK:KILL_OFF");
  }
  else if (cmd == "456") {
    // Force test alarm
    Serial.println("CMD_OK:TEST_ALARM");
    digitalWrite(LED, HIGH);
    tone(BUZZER, 2000);
    delay(2000);
    noTone(BUZZER);
    digitalWrite(LED, LOW);
  }
  else if (cmd.startsWith("min ult ")) {
    // Change ultrasonic threshold
    String val = cmd.substring(8);
    MIN_ULTRASONIC = val.toFloat();
    Serial.print("CMD_OK:MIN_ULTRA:");
    Serial.println(MIN_ULTRASONIC);
  }
  else if (cmd.startsWith("min vib ")) {
    // Change vibration threshold
    String val = cmd.substring(8);
    MIN_VIBRATION = val.toInt();
    Serial.print("CMD_OK:MIN_VIB:");
    Serial.println(MIN_VIBRATION);
  }
  else {
    Serial.print("CMD_ERROR:");
    Serial.println(cmd);
  }
}

void sendDataToPC(bool distAlert, bool vibAlert, bool dualAlert) {
  // Format: distance,vibration,dist_status,vib_status,dual_status,kill,sys,min_ultra,min_vib
  
  Serial.print(currentDist);
  Serial.print(",");
  Serial.print(vibrationCount);
  Serial.print(",");
  Serial.print(distAlert ? "DIST_ALERT" : "DIST_OK");
  Serial.print(",");
  Serial.print(vibAlert ? "VIB_ALERT" : "VIB_OK");
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
}
