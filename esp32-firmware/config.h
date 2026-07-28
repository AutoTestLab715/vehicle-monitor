#ifndef CONFIG_H
#define CONFIG_H

// ========== WiFi 配置（部署前修改） ==========
#define WIFI_SSID       "YourWiFiSSID"
#define WIFI_PASSWORD   "YourWiFiPassword"

// ========== 后端服务器地址（HTTP 备用通道） ==========
#define SERVER_HOST     "192.168.1.100"
#define SERVER_PORT     3000

// ========== MQTT Broker（主通道，与架构图一致） ==========
#define MQTT_BROKER     "192.168.1.100"
#define MQTT_PORT       1883
#define USE_MQTT        true

// ========== 设备 ID（多车时可区分） ==========
#define DEVICE_ID       "vehicle-001"

// ========== 引脚定义 ==========
#define PIN_ULTRASONIC_TRIG  5
#define PIN_ULTRASONIC_ECHO  18

#define PIN_DHT              4
#define DHT_TYPE             DHT22

#define PIN_SMOKE            34

#define PIN_BTN_FAN          0
#define PIN_BTN_ALARM        35

#define PIN_VOICE_RX         16
#define PIN_VOICE_TX         17
#define VOICE_BAUD           9600

#define PIN_FAN_RELAY        23
#define PIN_BUZZER           22
#define PIN_ALARM_LED        21
#define PIN_WINDOW_SERVO     19

// ========== 阈值与参数 ==========
#define DISTANCE_WARN_CM     30
#define DISTANCE_DANGER_CM   15
#define TEMP_WARN_C          35.0
#define HUMIDITY_WARN_PCT    80.0
#define SMOKE_WARN_RAW       2000
#define SMOKE_DANGER_RAW     2800

#define UPLOAD_INTERVAL_MS   2000
#define SENSOR_READ_MS       500
#define HTTP_TIMEOUT_MS      5000
#define MQTT_RECONNECT_MS    5000
#define OFFLINE_BUFFER_SIZE  5
#define SAFETY_OVERRIDE_MS   1000  // 手动关闭后，安全机制延迟重检时间

#define WINDOW_CLOSED_ANGLE  0
#define WINDOW_OPEN_ANGLE    90

#endif
