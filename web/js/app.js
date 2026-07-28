/**

 * 车载监控 Web / 手机端前端

 * Flask-SocketIO 实时数据 + REST 控制 + MySQL 历史/日志

 */



const state = {

  deviceId: 'vehicle-001',

  telemetry: null,

  socket: null,

  activeChart: 'distance',

  activeLog: 'alarms',

  history: {

    distance: [],

    temperature: [],

    humidity: []

  },

  maxHistory: 60

};



const $ = (sel) => document.querySelector(sel);

const $$ = (sel) => document.querySelectorAll(sel);



function init() {

  state.deviceId = $('#deviceId').value;

  connectSocket();

  bindEvents();

  fetchDevices();

  fetchHistory();

  fetchLogs();

  setInterval(checkOnline, 3000);

  setInterval(fetchLogs, 8000);

}



function connectSocket() {

  state.socket = io({ transports: ['websocket', 'polling'] });



  state.socket.on('connect', () => {

    updateConnStatus(true);

    state.socket.emit('subscribe', state.deviceId);

  });



  state.socket.on('disconnect', () => updateConnStatus(false));



  state.socket.on('telemetry', (data) => {

    if (data.deviceId === state.deviceId) {

      updateUI(data);

    }

    refreshDeviceList(data);

  });

}



function bindEvents() {

  $('#deviceId').addEventListener('change', (e) => {

    state.deviceId = e.target.value;

    state.telemetry = null;

    resetHistory();

    state.socket.emit('subscribe', state.deviceId);

    fetchDeviceState();

    fetchHistory();

    fetchLogs();

  });



  $$('.ctrl-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const action = btn.dataset.action;
      const current = state.telemetry?.[action === 'window' ? 'windowOpen' : action];
      sendControl(action, !current);
    });
  });



  $$('.chart-tab').forEach((btn) => {

    btn.addEventListener('click', () => {

      $$('.chart-tab').forEach((b) => b.classList.remove('active'));

      btn.classList.add('active');

      state.activeChart = btn.dataset.chart;

      drawChart();

    });

  });



  $$('.log-tab').forEach((btn) => {

    btn.addEventListener('click', () => {

      $$('.log-tab').forEach((b) => b.classList.remove('active'));

      btn.classList.add('active');

      state.activeLog = btn.dataset.log;

      fetchLogs();

    });

  });

}



function resetHistory() {

  state.history = { distance: [], temperature: [], humidity: [] };

  drawChart();

}



async function fetchDevices() {

  try {

    const res = await fetch('/api/devices');

    const list = await res.json();

    const sel = $('#deviceId');

    const current = sel.value;

    sel.innerHTML = '';

    if (list.length === 0) {

      sel.innerHTML = '<option value="vehicle-001">vehicle-001</option>';

    } else {

      list.forEach((d) => {

        const opt = document.createElement('option');

        opt.value = d.deviceId;

        opt.textContent = d.deviceId;

        sel.appendChild(opt);

      });

    }

    sel.value = list.find((d) => d.deviceId === current)?.deviceId || list[0]?.deviceId || 'vehicle-001';

    state.deviceId = sel.value;

    fetchDeviceState();

  } catch (e) {

    console.warn('fetch devices failed', e);

  }

}



function refreshDeviceList(data) {

  const sel = $('#deviceId');

  if (![...sel.options].some((o) => o.value === data.deviceId)) {

    const opt = document.createElement('option');

    opt.value = data.deviceId;

    opt.textContent = data.deviceId;

    sel.appendChild(opt);

  }

}



async function fetchDeviceState() {

  try {

    const res = await fetch(`/api/devices/${state.deviceId}`);

    if (res.ok) updateUI(await res.json());

  } catch (e) {

    console.warn('fetch device failed', e);

  }

}



async function fetchHistory() {

  try {

    const res = await fetch(`/api/history/sensors?deviceId=${state.deviceId}&limit=${state.maxHistory}`);

    if (!res.ok) return;

    const rows = await res.json();

    resetHistory();

    rows.forEach((row) => {

      pushHistory('distance', row.distanceCm);

      pushHistory('temperature', row.temperature);

      pushHistory('humidity', row.humidity);

    });

    drawChart();

  } catch (e) {

    console.warn('fetch history failed', e);

  }

}



async function fetchLogs() {

  const endpoints = {

    alarms: '/api/alarms',

    operations: '/api/operations',

    voice: '/api/voice-commands'

  };

  const path = endpoints[state.activeLog];

  if (!path) return;



  try {

    const res = await fetch(`${path}?deviceId=${state.deviceId}&limit=20`);

    if (!res.ok) return;

    renderLogs(await res.json());

  } catch (e) {

    console.warn('fetch logs failed', e);

  }

}



function renderLogs(rows) {

  const list = $('#logList');

  list.innerHTML = '';

  if (!rows.length) {

    list.innerHTML = '<li class="log-empty">暂无记录</li>';

    return;

  }



  rows.forEach((row) => {

    const li = document.createElement('li');

    if (state.activeLog === 'alarms') {

      li.className = 'log-item ' + (row.level || '');

      li.innerHTML = `

        <span class="log-time">${fmtTime(row.createdAt)}</span>

        <span class="log-msg">${row.message}</span>

      `;

    } else if (state.activeLog === 'operations') {

      li.className = 'log-item';

      li.innerHTML = `

        <span class="log-time">${fmtTime(row.createdAt)}</span>

        <span class="log-msg">${row.action} = ${row.value ? '开' : '关'} (${row.source})</span>

      `;

    } else {

      li.className = 'log-item';

      li.innerHTML = `

        <span class="log-time">${fmtTime(row.createdAt)}</span>

        <span class="log-msg">${row.commandText}</span>

      `;

    }

    list.appendChild(li);

  });

}



async function sendControl(action, value) {
  try {
    const res = await fetch(`/api/devices/${state.deviceId}/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, value, source: 'web' })
    });
    if (!res.ok) throw new Error('control failed');

    if (!state.telemetry) {
      state.telemetry = {
        deviceId: state.deviceId,
        fan: false,
        alarm: false,
        windowOpen: false
      };
    }
    if (action === 'window') state.telemetry.windowOpen = value;
    else state.telemetry[action] = value;

    updateControlButtons(state.telemetry);
    fetchLogs();
  } catch (e) {
    alert('控制失败，请检查网络');
  }
}



function updateConnStatus(connected) {

  const el = $('#connStatus');

  el.className = 'status-badge ' + (connected ? 'connected' : 'disconnected');

  el.querySelector('span:last-child').textContent = connected ? '已连接' : '已断开';

}



function checkOnline() {

  if (!state.telemetry?.updatedAt) return;

  const online = Date.now() - state.telemetry.updatedAt < 10000;

  const tag = $('#deviceOnline');

  tag.textContent = online ? '在线' : '离线';

  tag.className = 'online-tag ' + (online ? 'online' : 'offline');

}



function updateUI(data) {

  state.telemetry = data;



  $('#valDistance').textContent = fmt(data.distanceCm, 1);

  $('#valTemp').textContent = fmt(data.temperature, 1);

  $('#valHumidity').textContent = fmt(data.humidity, 1);

  $('#valSmoke').textContent = data.smokeRaw ?? '--';

  $('#valVoice').textContent = data.lastVoiceCmd || '无';

  $('#valRssi').textContent = (data.wifiRssi ?? '--') + ' dBm';

  $('#valUpdated').textContent = data.updatedAt

    ? new Date(data.updatedAt).toLocaleTimeString('zh-CN')

    : '--';



  updateMetricCard('cardDistance', data.alerts?.distanceWarn, data.alerts?.distanceDanger);

  updateMetricCard('cardTemp', data.alerts?.tempWarn, false);

  updateMetricCard('cardHumidity', data.alerts?.humidityWarn, false);

  updateMetricCard('cardSmoke', data.alerts?.smokeWarn, data.alerts?.smokeDanger);



  updateAlertBanner(data);

  updateControlButtons(data);

  pushHistory('distance', data.distanceCm);

  pushHistory('temperature', data.temperature);

  pushHistory('humidity', data.humidity);

  drawChart();

  checkOnline();

}



function fmt(v, d) {

  if (v == null || isNaN(v)) return '--';

  return Number(v).toFixed(d);

}



function fmtTime(ts) {

  if (!ts) return '--';

  return new Date(ts).toLocaleString('zh-CN', {

    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit'

  });

}



function updateMetricCard(id, warn, danger) {

  const el = document.getElementById(id);

  el.classList.remove('warn', 'danger');

  if (danger) el.classList.add('danger');

  else if (warn) el.classList.add('warn');

}



function updateAlertBanner(data) {

  const banner = $('#alertBanner');

  const alerts = data.alerts || {};

  const msgs = [];

  if (alerts.distanceDanger) msgs.push('⚠️ 碰撞危险！距离过近');

  else if (alerts.distanceWarn) msgs.push('距离预警');

  if (alerts.smokeDanger) msgs.push('🔥 烟雾危险！');

  else if (alerts.smokeWarn) msgs.push('烟雾预警');

  if (alerts.tempWarn) msgs.push('温度过高');

  if (alerts.humidityWarn) msgs.push('湿度过高');



  if (msgs.length === 0) {

    banner.className = 'alert-banner hidden';

    return;

  }

  banner.className = 'alert-banner ' + (data.alertLevel || 'warn');

  $('#alertText').textContent = msgs.join(' · ');

}



function updateControlButtons(data) {
  setBtnState('#btnFan', data.fan);
  setBtnState('#btnAlarm', data.alarm);
  setBtnState('#btnWindow', data.windowOpen);
}



function setBtnState(sel, on) {

  const btn = $(sel);

  btn.classList.toggle('active', on);

  const st = btn.querySelector('.ctrl-state');

  st.textContent = on ? '开' : '关';

  st.className = 'ctrl-state ' + (on ? 'on' : 'off');

}



function pushHistory(key, v) {

  if (v == null || isNaN(v)) return;

  if (key === 'distance' && v > 400) return;

  state.history[key].push(v);

  if (state.history[key].length > state.maxHistory) state.history[key].shift();

}



function drawChart() {

  const canvas = $('#chartMain');

  const ctx = canvas.getContext('2d');

  const dpr = window.devicePixelRatio || 1;

  const w = canvas.clientWidth;

  const h = canvas.clientHeight;

  canvas.width = w * dpr;

  canvas.height = h * dpr;

  ctx.scale(dpr, dpr);

  ctx.clearRect(0, 0, w, h);



  const data = state.history[state.activeChart] || [];

  if (data.length < 2) return;



  const max = Math.max(...data, state.activeChart === 'distance' ? 100 : 50);

  const min = Math.min(...data, 0);

  const pad = 8;

  const range = max - min || 1;



  ctx.strokeStyle = '#334155';

  ctx.lineWidth = 1;

  ctx.beginPath();

  ctx.moveTo(pad, h - pad);

  ctx.lineTo(w - pad, h - pad);

  ctx.stroke();



  const colors = { distance: '#3b82f6', temperature: '#ef4444', humidity: '#22c55e' };

  ctx.strokeStyle = colors[state.activeChart] || '#3b82f6';

  ctx.lineWidth = 2;

  ctx.beginPath();

  data.forEach((v, i) => {

    const x = pad + (i / (data.length - 1)) * (w - pad * 2);

    const y = h - pad - ((v - min) / range) * (h - pad * 2);

    if (i === 0) ctx.moveTo(x, y);

    else ctx.lineTo(x, y);

  });

  ctx.stroke();



  if (state.activeChart === 'distance') {

    const warnY = h - pad - ((30 - min) / range) * (h - pad * 2);

    ctx.strokeStyle = '#f59e0b';

    ctx.setLineDash([4, 4]);

    ctx.beginPath();

    ctx.moveTo(pad, warnY);

    ctx.lineTo(w - pad, warnY);

    ctx.stroke();

    ctx.setLineDash([]);

  }

}



document.addEventListener('DOMContentLoaded', init);

window.addEventListener('resize', () => {

  if ((state.history[state.activeChart] || []).length >= 2) drawChart();

});

