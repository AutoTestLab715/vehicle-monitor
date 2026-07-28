/**
 * [已弃用] 旧版 Node.js 后端 — 请使用 Flask 版: server/run.py
 *
 * 车载监控后端服务
 * - ESP32 POST 上报遥测数据
 * - ESP32 GET 拉取待执行指令（轮询）
 * - Web/手机端 WebSocket 实时推送 + REST 下发控制
 */

const express = require('express');
const http = require('http');
const cors = require('cors');
const { Server } = require('socket.io');
const path = require('path');

const PORT = process.env.PORT || 3000;

const VALID_ACTIONS = [
  'fan', 'alarm', 'window', 'autoMode',
  'toggleFan', 'toggleAlarm', 'toggleWindow'
];

// 内存存储（生产环境可换 Redis/数据库）
const devices = new Map();       // deviceId -> latest telemetry
const commandQueues = new Map(); // deviceId -> pending command

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: '*', methods: ['GET', 'POST'] }
});

app.use(cors());
app.use(express.json());

// 静态托管前端（web 目录）
app.use(express.static(path.join(__dirname, '../../web')));

// ---------- 工具函数 ----------
function getOrCreateQueue(deviceId) {
  if (!commandQueues.has(deviceId)) {
    commandQueues.set(deviceId, null);
  }
  return commandQueues;
}

function enrichTelemetry(data) {
  const alerts = data.alerts || {};
  const level = alerts.distanceDanger || alerts.smokeDanger ? 'danger'
    : (alerts.distanceWarn || alerts.tempWarn || alerts.humidityWarn || alerts.smokeWarn ? 'warn' : 'ok');
  return { ...data, alertLevel: level, serverTime: Date.now() };
}

function broadcastUpdate(deviceId, payload) {
  io.emit('telemetry', { deviceId, ...payload });
  io.emit(`telemetry:${deviceId}`, payload);
}

// ---------- ESP32 API ----------

/** POST /api/telemetry/:deviceId - ESP32 上报数据 */
app.post('/api/telemetry/:deviceId', (req, res) => {
  const { deviceId } = req.params;
  const body = req.body;

  const record = enrichTelemetry({
    deviceId,
    distanceCm: body.distanceCm ?? 0,
    temperature: body.temperature ?? 0,
    humidity: body.humidity ?? 0,
    smokeRaw: body.smokeRaw ?? 0,
    fan: !!body.fan,
    alarm: !!body.alarm,
    windowOpen: !!body.windowOpen,
    autoMode: body.autoMode !== false,
    lastVoiceCmd: body.lastVoiceCmd || '',
    wifiRssi: body.wifiRssi ?? 0,
    alerts: body.alerts || {},
    updatedAt: Date.now()
  });

  devices.set(deviceId, record);
  broadcastUpdate(deviceId, record);

  res.json({ ok: true, serverTime: Date.now() });
});

/** GET /api/commands/:deviceId - ESP32 轮询指令（取走后清空） */
app.get('/api/commands/:deviceId', (req, res) => {
  const { deviceId } = req.params;
  getOrCreateQueue(deviceId);
  const cmd = commandQueues.get(deviceId);
  commandQueues.set(deviceId, null);
  if (cmd) {
    res.json(cmd);
  } else {
    res.status(204).send();
  }
});

// ---------- Web / 手机端 API ----------

/** GET /api/devices - 所有在线设备 */
app.get('/api/devices', (req, res) => {
  const list = Array.from(devices.entries()).map(([id, data]) => ({
    deviceId: id,
    ...data,
    online: Date.now() - data.updatedAt < 10000
  }));
  res.json(list);
});

/** GET /api/devices/:deviceId - 单设备最新状态 */
app.get('/api/devices/:deviceId', (req, res) => {
  const data = devices.get(req.params.deviceId);
  if (!data) return res.status(404).json({ error: 'Device not found' });
  res.json({
    ...data,
    online: Date.now() - data.updatedAt < 10000
  });
});

/** POST /api/devices/:deviceId/control - 下发控制指令 */
app.post('/api/devices/:deviceId/control', (req, res) => {
  const { deviceId } = req.params;
  const { action, value } = req.body;

  if (!action || !VALID_ACTIONS.includes(action)) {
    return res.status(400).json({ error: 'Invalid action', validActions: VALID_ACTIONS });
  }

  const cmd = { action, value: value !== undefined ? !!value : true, queuedAt: Date.now() };
  getOrCreateQueue(deviceId);
  commandQueues.set(deviceId, cmd);

  io.emit('commandQueued', { deviceId, ...cmd });
  res.json({ ok: true, queued: cmd });
});

/** GET /api/health */
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    devices: devices.size,
    uptime: process.uptime()
  });
});

// ---------- WebSocket ----------
io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  // 新连接推送全部设备快照
  devices.forEach((data, deviceId) => {
    socket.emit('telemetry', { deviceId, ...data });
  });

  socket.on('subscribe', (deviceId) => {
    socket.join(`device:${deviceId}`);
    const data = devices.get(deviceId);
    if (data) socket.emit(`telemetry:${deviceId}`, data);
  });

  socket.on('control', ({ deviceId, action, value }) => {
    if (!deviceId || !action || !VALID_ACTIONS.includes(action)) return;
    getOrCreateQueue(deviceId);
    commandQueues.set(deviceId, { action, value: value !== undefined ? !!value : true, queuedAt: Date.now() });
    io.emit('commandQueued', { deviceId, action, value });
  });

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
  });
});

// SPA 回退（未知 API 返回 404）
app.get('*', (req, res) => {
  if (req.path.startsWith('/api')) {
    return res.status(404).json({ error: 'Not found' });
  }
  res.sendFile(path.join(__dirname, '../../web/index.html'));
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Vehicle Monitor Server running on http://0.0.0.0:${PORT}`);
  console.log(`Web UI: http://localhost:${PORT}`);
  console.log(`ESP32 telemetry: POST http://<server-ip>:${PORT}/api/telemetry/vehicle-001`);
});
