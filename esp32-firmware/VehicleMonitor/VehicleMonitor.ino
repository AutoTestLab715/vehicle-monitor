/**
 * ESP32 车载辅助监控系统 - 主控固件
 *
 * 安全机制始终运行（最高优先级）：
 *   危险时自动开风扇/警报/车窗
 * 按键/Web/语音/手机可随时控制执行器；
 *   手动关闭后 1s 内不强制，1s 后若仍危险则安全机制重新触发
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <ESP32Servo.h>
#include "config.h"

DHT dht(PIN_DHT, DHT_TYPE);
Servo windowServo;
HardwareSerial VoiceSerial(2);
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

struct SensorData {
  float distanceCm = 999;
  float temperature = 0;
  float humidity = 0;
  int smokeRaw = 0;
  bool valid = false;
} sensors;

struct ActuatorState {
  bool fan = false;
  bool alarm = false;
  bool windowOpen = false;
} actuators;

unsigned long safetyBlockFanUntil = 0;
unsigned long safetyBlockAlarmUntil = 0;
unsigned long safetyBlockWindowUntil = 0;

String lastVoiceCmd = "";
unsigned long lastUpload = 0;
unsigned long lastSensorRead = 0;
unsigned long lastWifiRetry = 0;
unsigned long lastMqttRetry = 0;
bool wifiConnected = false;
bool mqttConnected = false;

String telemetryTopic;
String commandTopic;

String offlineBuffer[OFFLINE_BUFFER_SIZE];
int offlineCount = 0;

struct SafetyDemand {
  bool danger = false;
  bool warn = false;
  bool fan = false;
  bool alarm = false;
  bool window = false;
};

void setupPins();
void connectWiFi();
void connectMqtt();
float readDistanceCm();
void readSensors();
void applyActuators();
void setFanState(bool on);
void setAlarmState(bool on);
void setWindowState(bool open);
void userSetFan(bool on);
void userSetAlarm(bool on);
void userSetWindow(bool open);
void toggleFan();
void toggleAlarm();
void toggleWindow();
SafetyDemand evaluateSafety();
void runAutoLogic();
void handleVoiceCommand(const String& cmd);
void pollVoiceModule();
void pollButtons();
void executeRemoteCommand(const String& action, bool value);
String buildTelemetryJson();
bool uploadTelemetryMqtt(const String& body);
bool uploadTelemetryHttp(const String& body);
void pushOffline(const String& body);
void flushOfflineBuffer();
void uploadTelemetry();
void pollRemoteCommands();
void mqttCallback(char* topic, byte* payload, unsigned int length);

void setupPins() {
  pinMode(PIN_ULTRASONIC_TRIG, OUTPUT);
  pinMode(PIN_ULTRASONIC_ECHO, INPUT);
  pinMode(PIN_BTN_FAN, INPUT_PULLUP);
  pinMode(PIN_BTN_ALARM, INPUT_PULLUP);
  pinMode(PIN_FAN_RELAY, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_ALARM_LED, OUTPUT);

  digitalWrite(PIN_FAN_RELAY, LOW);
  digitalWrite(PIN_BUZZER, LOW);
  digitalWrite(PIN_ALARM_LED, LOW);

  windowServo.setPeriodHertz(50);
  windowServo.attach(PIN_WINDOW_SERVO, 500, 2400);
  windowServo.write(WINDOW_CLOSED_ANGLE);

  VoiceSerial.begin(VOICE_BAUD, SERIAL_8N1, PIN_VOICE_RX, PIN_VOICE_TX);
}

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    return;
  }
  wifiConnected = false;
  mqttConnected = false;
  Serial.print("Connecting WiFi: ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 30) {
    delay(500);
    Serial.print(".");
    retry++;
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    Serial.print("WiFi OK, IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WiFi failed, running offline");
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, payload, length);
  if (err) return;
  if (!doc.containsKey("action")) return;
  String action = doc["action"].as<String>();
  bool value = doc["value"] | true;
  executeRemoteCommand(action, value);
}

void connectMqtt() {
  if (!USE_MQTT || !wifiConnected) return;
  if (mqttClient.connected()) {
    mqttConnected = true;
    return;
  }

  telemetryTopic = String("vehicle/") + DEVICE_ID + "/telemetry";
  commandTopic = String("vehicle/") + DEVICE_ID + "/commands";

  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setBufferSize(768);

  Serial.print("Connecting MQTT: ");
  Serial.println(MQTT_BROKER);
  if (mqttClient.connect(DEVICE_ID)) {
    mqttConnected = true;
    mqttClient.subscribe(commandTopic.c_str());
    Serial.println("MQTT OK");
    flushOfflineBuffer();
  } else {
    mqttConnected = false;
    Serial.print("MQTT failed, rc=");
    Serial.println(mqttClient.state());
  }
}

float readDistanceCm() {
  digitalWrite(PIN_ULTRASONIC_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_ULTRASONIC_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_ULTRASONIC_TRIG, LOW);

  long duration = pulseIn(PIN_ULTRASONIC_ECHO, HIGH, 30000);
  if (duration == 0) return 999;
  float cm = duration * 0.034 / 2;
  if (cm < 2 || cm > 400) return 999;
  return cm;
}

void readSensors() {
  sensors.distanceCm = readDistanceCm();
  sensors.temperature = dht.readTemperature();
  sensors.humidity = dht.readHumidity();
  sensors.smokeRaw = analogRead(PIN_SMOKE);
  sensors.valid = !isnan(sensors.temperature) && !isnan(sensors.humidity);
}

void applyActuators() {
  digitalWrite(PIN_FAN_RELAY, actuators.fan ? HIGH : LOW);
  digitalWrite(PIN_BUZZER, actuators.alarm ? HIGH : LOW);
  digitalWrite(PIN_ALARM_LED, actuators.alarm ? HIGH : LOW);
  windowServo.write(actuators.windowOpen ? WINDOW_OPEN_ANGLE : WINDOW_CLOSED_ANGLE);
}

void setFanState(bool on) {
  actuators.fan = on;
  applyActuators();
}

void setAlarmState(bool on) {
  actuators.alarm = on;
  applyActuators();
}

void setWindowState(bool open) {
  actuators.windowOpen = open;
  applyActuators();
}

void userSetFan(bool on) {
  setFanState(on);
  if (!on) {
    safetyBlockFanUntil = millis() + SAFETY_OVERRIDE_MS;
  }
}

void userSetAlarm(bool on) {
  setAlarmState(on);
  if (!on) {
    safetyBlockAlarmUntil = millis() + SAFETY_OVERRIDE_MS;
  }
}

void userSetWindow(bool open) {
  setWindowState(open);
  if (!open) {
    safetyBlockWindowUntil = millis() + SAFETY_OVERRIDE_MS;
  }
}

void toggleFan() { userSetFan(!actuators.fan); }
void toggleAlarm() { userSetAlarm(!actuators.alarm); }
void toggleWindow() { userSetWindow(!actuators.windowOpen); }

SafetyDemand evaluateSafety() {
  SafetyDemand demand;

  if (sensors.distanceCm <= DISTANCE_DANGER_CM) demand.danger = true;
  else if (sensors.distanceCm <= DISTANCE_WARN_CM) demand.warn = true;

  if (sensors.valid) {
    if (sensors.temperature >= TEMP_WARN_C || sensors.humidity >= HUMIDITY_WARN_PCT) {
      demand.warn = true;
      demand.fan = true;
    }
  }

  if (sensors.smokeRaw >= SMOKE_DANGER_RAW) demand.danger = true;
  else if (sensors.smokeRaw >= SMOKE_WARN_RAW) demand.warn = true;

  if (demand.danger) {
    demand.fan = true;
    demand.alarm = true;
    demand.window = true;
  } else if (demand.warn) {
    demand.alarm = true;
  }

  return demand;
}

void runAutoLogic() {
  SafetyDemand demand = evaluateSafety();
  unsigned long now = millis();

  if (demand.fan && now >= safetyBlockFanUntil) {
    setFanState(true);
  } else if (!demand.fan && now >= safetyBlockFanUntil) {
    if (sensors.valid &&
        sensors.temperature < TEMP_WARN_C - 2 &&
        sensors.humidity < HUMIDITY_WARN_PCT - 5) {
      setFanState(false);
    } else if (!demand.warn && !demand.danger) {
      setFanState(false);
    }
  }

  if (demand.alarm && now >= safetyBlockAlarmUntil) {
    setAlarmState(true);
  } else if (!demand.alarm && !demand.warn && now >= safetyBlockAlarmUntil) {
    setAlarmState(false);
  }

  if (demand.window && now >= safetyBlockWindowUntil) {
    setWindowState(true);
  } else if (!demand.window && now >= safetyBlockWindowUntil) {
    setWindowState(false);
  }
}

void handleVoiceCommand(const String& cmd) {
  lastVoiceCmd = cmd;
  Serial.print("Voice: ");
  Serial.println(cmd);

  if (cmd.indexOf("开风扇") >= 0 || cmd.indexOf("打开风扇") >= 0) {
    userSetFan(true);
  } else if (cmd.indexOf("关风扇") >= 0 || cmd.indexOf("关闭风扇") >= 0) {
    userSetFan(false);
  } else if (cmd.indexOf("开警报") >= 0 || cmd.indexOf("打开警报") >= 0) {
    userSetAlarm(true);
  } else if (cmd.indexOf("关警报") >= 0 || cmd.indexOf("关闭警报") >= 0) {
    userSetAlarm(false);
  } else if (cmd.indexOf("开窗") >= 0 || cmd.indexOf("打开车窗") >= 0) {
    userSetWindow(true);
  } else if (cmd.indexOf("关窗") >= 0 || cmd.indexOf("关闭车窗") >= 0) {
    userSetWindow(false);
  }
}

void pollVoiceModule() {
  static String buffer = "";
  while (VoiceSerial.available()) {
    char c = VoiceSerial.read();
    if (c == '\n' || c == '\r') {
      if (buffer.length() > 0) {
        handleVoiceCommand(buffer);
        buffer = "";
      }
    } else {
      buffer += c;
      if (buffer.length() > 64) buffer = "";
    }
  }
}

void pollButtons() {
  static unsigned long lastFanPress = 0;
  static unsigned long lastAlarmPress = 0;
  unsigned long now = millis();

  if (digitalRead(PIN_BTN_FAN) == LOW && now - lastFanPress > 300) {
    lastFanPress = now;
    toggleFan();
  }
  if (digitalRead(PIN_BTN_ALARM) == LOW && now - lastAlarmPress > 300) {
    lastAlarmPress = now;
    toggleAlarm();
  }
}

void executeRemoteCommand(const String& action, bool value) {
  if (action == "fan") userSetFan(value);
  else if (action == "alarm") userSetAlarm(value);
  else if (action == "window") userSetWindow(value);
  else if (action == "toggleFan") toggleFan();
  else if (action == "toggleAlarm") toggleAlarm();
  else if (action == "toggleWindow") toggleWindow();
}

String buildTelemetryJson() {
  StaticJsonDocument<768> doc;
  doc["deviceId"] = DEVICE_ID;
  doc["distanceCm"] = sensors.distanceCm;
  doc["temperature"] = sensors.temperature;
  doc["humidity"] = sensors.humidity;
  doc["smokeRaw"] = sensors.smokeRaw;
  doc["fan"] = actuators.fan;
  doc["alarm"] = actuators.alarm;
  doc["windowOpen"] = actuators.windowOpen;
  doc["autoMode"] = true;
  doc["safetyActive"] = true;
  doc["lastVoiceCmd"] = lastVoiceCmd;
  doc["wifiRssi"] = WiFi.RSSI();
  doc["timestamp"] = millis();

  JsonObject alerts = doc.createNestedObject("alerts");
  alerts["distanceWarn"] = sensors.distanceCm <= DISTANCE_WARN_CM;
  alerts["distanceDanger"] = sensors.distanceCm <= DISTANCE_DANGER_CM;
  alerts["tempWarn"] = sensors.valid && sensors.temperature >= TEMP_WARN_C;
  alerts["humidityWarn"] = sensors.valid && sensors.humidity >= HUMIDITY_WARN_PCT;
  alerts["smokeWarn"] = sensors.smokeRaw >= SMOKE_WARN_RAW;
  alerts["smokeDanger"] = sensors.smokeRaw >= SMOKE_DANGER_RAW;

  String body;
  serializeJson(doc, body);
  return body;
}

bool uploadTelemetryMqtt(const String& body) {
  if (!USE_MQTT || !mqttClient.connected()) return false;
  return mqttClient.publish(telemetryTopic.c_str(), body.c_str(), false);
}

bool uploadTelemetryHttp(const String& body) {
  if (!wifiConnected) return false;

  HTTPClient http;
  String url = String("http://") + SERVER_HOST + ":" + SERVER_PORT +
               "/api/telemetry/" + DEVICE_ID;

  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(HTTP_TIMEOUT_MS);
  int code = http.POST(body);
  http.end();
  return code == 200;
}

void pushOffline(const String& body) {
  if (offlineCount >= OFFLINE_BUFFER_SIZE) {
    for (int i = 1; i < OFFLINE_BUFFER_SIZE; i++) {
      offlineBuffer[i - 1] = offlineBuffer[i];
    }
    offlineCount = OFFLINE_BUFFER_SIZE - 1;
  }
  offlineBuffer[offlineCount++] = body;
}

void flushOfflineBuffer() {
  if (offlineCount == 0) return;
  Serial.printf("Flushing offline buffer (%d)\n", offlineCount);
  for (int i = 0; i < offlineCount; i++) {
    bool ok = uploadTelemetryMqtt(offlineBuffer[i]);
    if (!ok) ok = uploadTelemetryHttp(offlineBuffer[i]);
    if (!ok) break;
  }
  offlineCount = 0;
}

void uploadTelemetry() {
  String body = buildTelemetryJson();
  bool ok = false;

  if (USE_MQTT && mqttClient.connected()) {
    ok = uploadTelemetryMqtt(body);
  }
  if (!ok && wifiConnected) {
    ok = uploadTelemetryHttp(body);
  }
  if (!ok) {
    pushOffline(body);
  }
}

void pollRemoteCommands() {
  if (USE_MQTT && mqttClient.connected()) return;

  if (!wifiConnected) return;

  HTTPClient http;
  String url = String("http://") + SERVER_HOST + ":" + SERVER_PORT +
               "/api/commands/" + DEVICE_ID;

  http.begin(url);
  http.setTimeout(HTTP_TIMEOUT_MS);
  int code = http.GET();

  if (code == 200) {
    String payload = http.getString();
    StaticJsonDocument<256> doc;
    if (deserializeJson(doc, payload) == DeserializationError::Ok) {
      if (doc.containsKey("action")) {
        String action = doc["action"].as<String>();
        bool value = doc["value"] | true;
        executeRemoteCommand(action, value);
      }
    }
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n=== Vehicle Monitor ESP32 ===");

  setupPins();
  dht.begin();
  connectWiFi();
  connectMqtt();
}

void loop() {
  unsigned long now = millis();

  if (WiFi.status() != WL_CONNECTED) {
    wifiConnected = false;
    mqttConnected = false;
    if (now - lastWifiRetry >= 10000) {
      lastWifiRetry = now;
      connectWiFi();
    }
  } else {
    wifiConnected = true;
  }

  if (USE_MQTT && wifiConnected) {
    if (!mqttClient.connected()) {
      mqttConnected = false;
      if (now - lastMqttRetry >= MQTT_RECONNECT_MS) {
        lastMqttRetry = now;
        connectMqtt();
      }
    } else {
      mqttConnected = true;
      mqttClient.loop();
    }
  }

  if (now - lastSensorRead >= SENSOR_READ_MS) {
    lastSensorRead = now;
    readSensors();
    runAutoLogic();
  }

  pollVoiceModule();
  pollButtons();

  if (now - lastUpload >= UPLOAD_INTERVAL_MS) {
    lastUpload = now;
    if (wifiConnected) {
      pollRemoteCommands();
      uploadTelemetry();
    }
  }
}
