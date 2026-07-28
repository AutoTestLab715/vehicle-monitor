/**
 * ESP32 数据模拟 - 无硬件电脑演示
 * 用法: node simulate-esp32.js
 * 前提: 先启动 start-server.bat
 *
 * 安全机制始终运行；手动关闭后约 1s 若仍危险会重新触发
 */

const http = require('http');

const BASE_URL = 'http://localhost:3000';
const DEVICE_ID = 'vehicle-001';
const INTERVAL_MS = 4000;
const SAFETY_OVERRIDE_SEC = 1.0;

const actuatorState = {
  fan: false,
  alarm: false,
  windowOpen: false,
  lastVoiceCmd: ''
};

const safetyBlockUntil = {
  fan: 0,
  alarm: 0,
  window: 0
};

const scenarios = [
  {
    name: '正常行驶',
    data: {
      distanceCm: 80, temperature: 26, humidity: 55, smokeRaw: 600,
      alerts: { distanceWarn: false, distanceDanger: false, tempWarn: false, humidityWarn: false, smokeWarn: false, smokeDanger: false }
    }
  },
  {
    name: '距离预警 - 接近障碍物',
    data: {
      distanceCm: 28, temperature: 26, humidity: 55, smokeRaw: 600,
      alerts: { distanceWarn: true, distanceDanger: false, tempWarn: false, humidityWarn: false, smokeWarn: false, smokeDanger: false }
    }
  },
  {
    name: '碰撞危险 - 距离过近',
    data: {
      distanceCm: 12, temperature: 26, humidity: 55, smokeRaw: 600,
      alerts: { distanceWarn: true, distanceDanger: true, tempWarn: false, humidityWarn: false, smokeWarn: false, smokeDanger: false }
    }
  },
  {
    name: '温度过高 - 自动开风扇',
    data: {
      distanceCm: 80, temperature: 37, humidity: 65, smokeRaw: 700,
      alerts: { distanceWarn: false, distanceDanger: false, tempWarn: true, humidityWarn: false, smokeWarn: false, smokeDanger: false }
    }
  },
  {
    name: '烟雾危险 - 自动开窗',
    data: {
      distanceCm: 80, temperature: 30, humidity: 60, smokeRaw: 2900,
      alerts: { distanceWarn: false, distanceDanger: false, tempWarn: false, humidityWarn: false, smokeWarn: true, smokeDanger: true }
    }
  },
  {
    name: '恢复正常',
    data: {
      distanceCm: 100, temperature: 25, humidity: 50, smokeRaw: 500,
      alerts: { distanceWarn: false, distanceDanger: false, tempWarn: false, humidityWarn: false, smokeWarn: false, smokeDanger: false }
    }
  }
];

function httpRequest(method, path, body) {
  return new Promise((resolve, reject) => {
    const payload = body ? JSON.stringify(body) : null;
    const url = new URL(path, BASE_URL);
    const req = http.request(url, {
      method,
      headers: payload ? {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload)
      } : undefined
    }, (res) => {
      let raw = '';
      res.on('data', (chunk) => { raw += chunk; });
      res.on('end', () => resolve({ status: res.statusCode, body: raw }));
    });
    req.on('error', reject);
    if (payload) req.write(payload);
    req.end();
  });
}

function applyCommand(cmd) {
  const { action, value = true } = cmd;
  const now = Date.now() / 1000;

  switch (action) {
    case 'fan':
      actuatorState.fan = !!value;
      if (!value) safetyBlockUntil.fan = now + SAFETY_OVERRIDE_SEC;
      break;
    case 'alarm':
      actuatorState.alarm = !!value;
      if (!value) safetyBlockUntil.alarm = now + SAFETY_OVERRIDE_SEC;
      break;
    case 'window':
      actuatorState.windowOpen = !!value;
      if (!value) safetyBlockUntil.window = now + SAFETY_OVERRIDE_SEC;
      break;
    case 'toggleFan':
      actuatorState.fan = !actuatorState.fan;
      if (!actuatorState.fan) safetyBlockUntil.fan = now + SAFETY_OVERRIDE_SEC;
      break;
    case 'toggleAlarm':
      actuatorState.alarm = !actuatorState.alarm;
      if (!actuatorState.alarm) safetyBlockUntil.alarm = now + SAFETY_OVERRIDE_SEC;
      break;
    case 'toggleWindow':
      actuatorState.windowOpen = !actuatorState.windowOpen;
      if (!actuatorState.windowOpen) safetyBlockUntil.window = now + SAFETY_OVERRIDE_SEC;
      break;
    default:
      break;
  }
}

function applySafety(scene) {
  const alerts = scene.data.alerts || {};
  const now = Date.now() / 1000;
  const danger = alerts.distanceDanger || alerts.smokeDanger;
  const warn = alerts.distanceWarn || alerts.tempWarn || alerts.humidityWarn || alerts.smokeWarn;

  const needFan = danger || alerts.tempWarn;
  const needAlarm = danger || warn;
  const needWindow = alerts.smokeDanger;

  if (needFan && now >= safetyBlockUntil.fan) {
    actuatorState.fan = true;
  } else if (!needFan && now >= safetyBlockUntil.fan) {
    actuatorState.fan = false;
  }

  if (needAlarm && now >= safetyBlockUntil.alarm) {
    actuatorState.alarm = true;
  } else if (!needAlarm && !warn && now >= safetyBlockUntil.alarm) {
    actuatorState.alarm = false;
  }

  if (needWindow && now >= safetyBlockUntil.window) {
    actuatorState.windowOpen = true;
  } else if (!needWindow && now >= safetyBlockUntil.window) {
    actuatorState.windowOpen = false;
  }
}

function mergeScenario(scene) {
  applySafety(scene);
  return {
    ...scene.data,
    deviceId: DEVICE_ID,
    fan: actuatorState.fan,
    alarm: actuatorState.alarm,
    windowOpen: actuatorState.windowOpen,
    autoMode: true,
    safetyActive: true,
    lastVoiceCmd: actuatorState.lastVoiceCmd,
    wifiRssi: -55
  };
}

async function pollCommands() {
  const res = await httpRequest('GET', `/api/commands/${DEVICE_ID}`);
  if (res.status === 200 && res.body) {
    try {
      const cmd = JSON.parse(res.body);
      applyCommand(cmd);
      console.log(`  [远程指令] ${cmd.action}${cmd.value !== undefined ? ' = ' + cmd.value : ''}`);
    } catch {
      // ignore malformed payload
    }
  }
}

async function postTelemetry(data) {
  const res = await httpRequest('POST', `/api/telemetry/${DEVICE_ID}`, data);
  if (res.status !== 200) {
    throw new Error(`HTTP ${res.status}: ${res.body}`);
  }
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function main() {
  console.log('========================================');
  console.log('  ESP32 数据模拟演示 (Ctrl+C 停止)');
  console.log('  请先启动: start-server.bat');
  console.log('  浏览器: http://localhost:3000');
  console.log('  安全机制始终生效，手动关闭约 1s 后重检');
  console.log('========================================\n');

  let round = 0;
  while (true) {
    round++;
    for (const scene of scenarios) {
      try {
        await pollCommands();
        const payload = mergeScenario(scene);
        await postTelemetry(payload);
        const t = new Date().toLocaleTimeString('zh-CN');
        console.log(`[${t}] 场景: ${scene.name}`);
        console.log(`  距离=${payload.distanceCm}cm  温度=${payload.temperature}C  烟雾=${payload.smokeRaw}`);
        console.log(`  风扇=${payload.fan ? '开' : '关'}  警报=${payload.alarm ? '开' : '关'}  车窗=${payload.windowOpen ? '开' : '关'}`);
      } catch (err) {
        console.error('\n[错误] 无法连接后端，请先双击 start-server.bat 启动服务');
        console.error('详情:', err.message);
        process.exit(1);
      }
      await sleep(INTERVAL_MS);
    }
    console.log(`\n--- 第 ${round} 轮演示完成，循环播放 ---\n`);
  }
}

main();
