Where to change esp32 code . Here it is:

#include <WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <DHT.h>

// ==========================================
// 1. NETWORK CONFIGURATION
// ==========================================
// const char* ssid = "TALHA-AFZAL 9922";
// const char* password = "1/e7357Y";
const char* ssid = "Talha's Galaxy A32";
const char* password = "123456789";

// The IP Address of your Laptop on the Hotspot network
// const char* laptopIP = "192.168.1.113"; 
const char* laptopIP = "192.168.133.81"; 
const int udpPort = 4210;
WiFiUDP udp;

// ==========================================
// 2. HARDWARE PINS
// ==========================================
const int motorIN1 = 13;
const int motorIN2 = 12;
const int motorIN3 = 14;
const int motorIN4 = 27;

const int trigPin = 5;
const int echoPin = 18;
const int dhtPin = 19;
#define DHTTYPE DHT11 
DHT dht(dhtPin, DHTTYPE);
Adafruit_MPU6050 mpu;

// --- NEW: ENCODER PINS (Change these to match your wiring!) ---
const int encLeftPin = 4; 
const int encRightPin = 16; 

// ==========================================
// 3. HARDWARE INTERRUPT COUNTERS
// ==========================================
// 'volatile' prevents the compiler from deleting these variables to save memory
volatile long encoderLeftCount = 0;
volatile long encoderRightCount = 0;

// IRAM_ATTR loads this function into the ESP32's RAM for microsecond execution
void IRAM_ATTR isrLeft() {
  encoderLeftCount++;
}

void IRAM_ATTR isrRight() {
  encoderRightCount++;
}

// ==========================================
// 4. TIMERS
// ==========================================
unsigned long lastTelemetryTime = 0;
unsigned long lastTempTime = 0;
float currentTemp = 0.0;

void setup() {
  Serial.begin(115200);

  pinMode(motorIN1, OUTPUT); 
  pinMode(motorIN2, OUTPUT);
  pinMode(motorIN3, OUTPUT); 
  pinMode(motorIN4, OUTPUT);
  pinMode(trigPin, OUTPUT); 
  pinMode(echoPin, INPUT);

  // --- NEW: ATTACH ENCODER INTERRUPTS ---
  pinMode(encLeftPin, INPUT_PULLUP);
  pinMode(encRightPin, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(encLeftPin), isrLeft, RISING);
  attachInterrupt(digitalPinToInterrupt(encRightPin), isrRight, RISING);

  dht.begin();
  
  // --- RE-ACTIVATED MPU6050 ---
   if (!mpu.begin()) {
    Serial.println("Failed to find MPU6050 chip!");
   } else {
     mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
     mpu.setGyroRange(MPU6050_RANGE_500_DEG);
     mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
   }

 Serial.print("Connecting to Wi-Fi");
 WiFi.begin(ssid, password);
 while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
 Serial.println("\nConnected!");

 udp.begin(udpPort);
}

void loop() {
  unsigned long currentMillis = millis();

// A. ULTRASONIC REFLEX
  long duration, distance;
  digitalWrite(trigPin, LOW); delayMicroseconds(2);
  digitalWrite(trigPin, HIGH); delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  duration = pulseIn(echoPin, HIGH);
  distance = duration * 0.034 / 2;

  // Flag the hazard, but DO NOT stop the motors blindly yet!
  bool reflexTriggered = false;
  if (distance > 0 && distance < 15) { 
    reflexTriggered = true; 
  }

  // B. RECEIVE COMMANDS FROM PYTHON
  int packetSize = udp.parsePacket();
  if (packetSize) {
    char incomingPacket[255];
    int len = udp.read(incomingPacket, 255);
    if (len > 0) incomingPacket[len] = '\0';
    
    char cmd = incomingPacket[0];
    
    // --- THE TACTICAL EVASION FILTER ---
    if (reflexTriggered && cmd == 'F') {
      stopMotors(); // Block Forward commands
    } else {
      // Unrestricted movement for turning and reversing
      if (cmd == 'F') driveForward();
      else if (cmd == 'B') driveBackward();
      else if (cmd == 'L') turnLeft();
      else if (cmd == 'R') turnRight();
      else if (cmd == 'S') stopMotors();
    }
  } 
  // --- THE HARDWARE SAFETY NET ---
  // If an obstacle appears between network packets, check if we are currently driving forward
  else if (reflexTriggered) {
    // IN2 and IN3 are only both HIGH when driving straight forward
    if (digitalRead(motorIN2) == HIGH && digitalRead(motorIN3) == HIGH) {
      stopMotors(); 
    }
  }

  // C. READ TEMPERATURE (Slow)
  if (currentMillis - lastTempTime >= 2000) {
    float t = dht.readTemperature();
    if (!isnan(t)) currentTemp = t;
    lastTempTime = currentMillis;
  }

  // D. TRANSMIT TELEMETRY (Fast - 100ms)
   if (currentMillis - lastTelemetryTime >= 100) {
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);

    // Build the SLAM-ready JSON Packet
    StaticJsonDocument<256> doc;
    doc["dist"] = distance;
    doc["temp"] = currentTemp;
    doc["override"] = reflexTriggered;
    
    // THE SLAM FUEL:
    doc["enc_l"] = encoderLeftCount;
    doc["enc_r"] = encoderRightCount;
    doc["gyro_z"] = g.gyro.z; // Angular velocity (rad/s)
    doc["accel_x"] = a.acceleration.x;

    udp.beginPacket(laptopIP, udpPort);
    serializeJson(doc, udp);
    udp.endPacket();

    lastTelemetryTime = currentMillis;
 }
}
// // ==========================================
// // 4. MOTOR CONTROL LOGIC
// // ==========================================
void driveForward() {
  digitalWrite(motorIN1, LOW); 
  digitalWrite(motorIN2, HIGH);
  digitalWrite(motorIN3, HIGH); 
  digitalWrite(motorIN4, LOW);
}
void driveBackward() {
  digitalWrite(motorIN1, HIGH); 
  digitalWrite(motorIN2, LOW);
  digitalWrite(motorIN3, LOW); 
  digitalWrite(motorIN4, HIGH);
}
void turnLeft() {
  // Left side stop
  digitalWrite(motorIN1, LOW); 
  digitalWrite(motorIN2, LOW);

  // Right side forward
  digitalWrite(motorIN3, HIGH); 
  digitalWrite(motorIN4, LOW);
}

void turnRight() {
  // Left side forward
  digitalWrite(motorIN1, LOW); 
  digitalWrite(motorIN2, HIGH);

  // Right side stop
  digitalWrite(motorIN3, LOW); 
  digitalWrite(motorIN4, LOW);
}
void stopMotors() {
  digitalWrite(motorIN1, LOW); 
  digitalWrite(motorIN2, LOW);
  digitalWrite(motorIN3, LOW); 
  digitalWrite(motorIN4, LOW);
}