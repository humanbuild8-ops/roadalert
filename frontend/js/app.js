/* RoadAlert — live console demo
 * Runs a self-contained highway simulation by default. If a RoadAlert
 * backend (see /backend) is reachable at ws://localhost:8000/ws/incidents,
 * it switches to rendering the real, backend-verified incident feed instead.
 */

const NS = 'http://www.w3.org/2000/svg';
const svgEl = (tag, attrs = {}) => {
  const el = document.createElementNS(NS, tag);
  for (const k in attrs) el.setAttribute(k, attrs[k]);
  return el;
};

const LANES = [32, 97, 162, 227];
const INCIDENT_X = 620;
const INCIDENT_LANE = 1;

const carsLayer   = document.getElementById('cars');
const alertZoneEl = document.getElementById('alertZone');
const divertPath  = document.getElementById('divertPath');
const incidentMark= document.getElementById('incidentMark');
const triggerBtn  = document.getElementById('triggerBtn');
const logEl       = document.getElementById('log');
const logEmpty    = document.getElementById('logEmpty');
const logCountEl  = document.getElementById('logCount');
const clockEl     = document.getElementById('clock');
const linkDot     = document.getElementById('linkDot');
const modeLabel   = document.getElementById('modeLabel');

const statActive   = document.getElementById('statActive');
const statVehicles = document.getElementById('statVehicles');
const statAlerts   = document.getElementById('statAlerts');
const statLatency  = document.getElementById('statLatency');
const sparkline    = document.getElementById('sparkline');

/* ---------------- clock ---------------- */
function tickClock() {
  const d = new Date();
  clockEl.textContent = d.toLocaleTimeString('en-GB', { hour12: false });
}
tickClock();
setInterval(tickClock, 1000);

/* ---------------- fleet of moving cars ---------------- */
let cars = [];
function makeCar(x) {
  const lane = LANES[Math.floor(Math.random() * LANES.length)];
  const g = svgEl('g', { class: 'car' });
  const body = svgEl('rect', {
    width: 30, height: 14, rx: 3,
    x: -15, y: -7,
    fill: '#F2A93B'
  });
  g.appendChild(body);
  carsLayer.appendChild(g);
  return {
    el: g, body, lane,
    x: x, baseSpeed: 46 + Math.random() * 30,
    speed: 0, alerted: false
  };
}
for (let i = 0; i < 11; i++) cars.push(makeCar(Math.random() * 1000 - 500));

let incidentActive = false;

function laneY(lane) { return lane; }

let lastTs = performance.now();
function frame(ts) {
  const dt = Math.min(0.05, (ts - lastTs) / 1000);
  lastTs = ts;

  cars.forEach(c => {
    const inZone = incidentActive && c.x < INCIDENT_X && c.x > INCIDENT_X - 320 && c.lane === LANES[INCIDENT_LANE];
    c.alerted = inZone;
    c.speed = inZone ? c.baseSpeed * 0.4 : c.baseSpeed;
    c.x += c.speed * dt;
    if (c.x > 1050) { c.x = -60; c.lane = LANES[Math.floor(Math.random() * LANES.length)]; }
    c.body.setAttribute('fill', c.alerted ? '#4C8DFF' : '#F2A93B');
    c.el.setAttribute('transform', `translate(${c.x}, ${laneY(c.lane)})`);
  });

  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

/* ---------------- incident log ---------------- */
let entries = [];
let alertsToday = 0;

function renderLog() {
  logEl.querySelectorAll('.log-row').forEach(n => n.remove());
  logEmpty.style.display = entries.length ? 'none' : 'block';
  logCountEl.textContent = `${entries.length} today`;
  entries.slice(0, 8).forEach(e => {
    const row = document.createElement('div');
    row.className = 'log-row';
    row.innerHTML = `
      <div class="log-row__top">
        <div>
          <div class="log-row__title">${e.title}</div>
          <div class="log-row__detail">${e.detail}</div>
        </div>
        <span class="log-row__status log-row__status--${e.status}">${e.statusLabel}</span>
      </div>
      <div class="log-row__time">${e.time}</div>`;
    logEl.insertBefore(row, logEl.firstChild.nextSibling || null);
    logEl.prepend(row);
  });
}

function addEntry(entry) { entries.unshift(entry); renderLog(); }
function updateEntry(id, patch) {
  const e = entries.find(x => x.id === id);
  if (e) Object.assign(e, patch);
  renderLog();
}

/* ---------------- incident sequence (local simulation) ---------------- */
function nowLabel() { return new Date().toLocaleTimeString('en-GB', { hour12: false }); }

function triggerIncident() {
  if (incidentActive) return;
  incidentActive = true;
  triggerBtn.disabled = true;
  triggerBtn.textContent = 'Incident on route…';

  incidentMark.setAttribute('transform', `translate(${INCIDENT_X}, ${LANES[INCIDENT_LANE]})`);
  incidentMark.setAttribute('opacity', 1);
  incidentMark.querySelectorAll('.incident-mark__ring').forEach(r => r.setAttribute('stroke', '#F2A93B'));

  const id = Date.now();
  addEntry({
    id, time: nowLabel(),
    title: 'Camera flagged possible collision',
    detail: `NH-44 · km 214 · confidence building`,
    status: 'pending', statusLabel: 'detecting'
  });

  statActive.textContent = '1';

  setTimeout(() => confirmIncident(id), 1400);
}

function confirmIncident(id) {
  incidentMark.querySelectorAll('.incident-mark__ring').forEach(r => r.setAttribute('stroke', '#E23B4E'));

  const zoneW = 320;
  alertZoneEl.innerHTML = '';
  alertZoneEl.appendChild(svgEl('rect', { x: INCIDENT_X - zoneW, y: 0, width: zoneW, height: 260 }));
  alertZoneEl.setAttribute('opacity', 1);

  divertPath.setAttribute('d', `M ${INCIDENT_X - 170} ${LANES[INCIDENT_LANE]} Q ${INCIDENT_X} ${LANES[INCIDENT_LANE] - 70} ${INCIDENT_X + 170} ${LANES[INCIDENT_LANE]}`);
  divertPath.setAttribute('opacity', 1);

  const driverCount = 6 + Math.floor(Math.random() * 9);
  alertsToday += driverCount;
  statAlerts.textContent = alertsToday;
  const latencyMs = 900 + Math.floor(Math.random() * 900);
  statLatency.textContent = (latencyMs / 1000).toFixed(1) + ' s';

  bumpSparkline();

  updateEntry(id, {
    title: 'Confirmed — alert sent',
    detail: `${driverCount} drivers behind the incident rerouted · detected in ${(latencyMs/1000).toFixed(1)} s`,
    status: 'confirmed', statusLabel: 'alert sent'
  });

  setTimeout(() => clearIncident(id), 9000);
}

function clearIncident(id) {
  incidentMark.setAttribute('opacity', 0);
  alertZoneEl.setAttribute('opacity', 0);
  divertPath.setAttribute('opacity', 0);
  incidentActive = false;
  triggerBtn.disabled = false;
  triggerBtn.textContent = 'Report accident now';
  statActive.textContent = '0';
  updateEntry(id, { status: 'cleared', statusLabel: 'road clear' });
}

triggerBtn.addEventListener('click', () => {
  if (window.__roadalertBackend) {
    postIncidentToBackend();
  } else {
    triggerIncident();
  }
});

/* auto-demo: something happens periodically even with no clicks */
setInterval(() => { if (!incidentActive && !window.__roadalertBackend) triggerIncident(); }, 16000);

/* ---------------- vehicles-connected counter ---------------- */
let vehicleCount = 412;
statVehicles.textContent = vehicleCount;
setInterval(() => {
  vehicleCount += Math.round((Math.random() - 0.5) * 6);
  statVehicles.textContent = Math.max(180, vehicleCount);
}, 2500);
statLatency.textContent = '1.8 s';

/* ---------------- sparkline: detections, last 12 hours ---------------- */
const hours = Array.from({ length: 12 }, (_, i) => {
  const base = [3,2,4,7,9,8,6,5,7,10,6,4][i];
  return base + Math.floor(Math.random() * 2);
});
function drawSparkline() {
  sparkline.innerHTML = '';
  const w = 240, h = 46, max = Math.max(...hours, 1);
  const pts = hours.map((v, i) => {
    const x = (i / (hours.length - 1)) * (w - 4) + 2;
    const y = h - 4 - (v / max) * (h - 10);
    return [x, y];
  });
  const line = pts.map(p => p.join(',')).join(' ');
  sparkline.appendChild(svgEl('polyline', { points: line, class: 'spark-line' }));
  const area = `2,${h-2} ${line} ${w-2},${h-2}`;
  sparkline.appendChild(svgEl('polygon', { points: area, class: 'spark-fill' }));
  const last = pts[pts.length - 1];
  sparkline.appendChild(svgEl('circle', { cx: last[0], cy: last[1], r: 3, class: 'spark-now' }));
}
function bumpSparkline() { hours[hours.length - 1] += 1; drawSparkline(); }
drawSparkline();

/* ---------------- optional live backend ---------------- */
function setMode(live) {
  modeLabel.textContent = live ? 'live backend feed' : 'simulated feed';
  linkDot.classList.toggle('is-down', false);
}

function postIncidentToBackend() {
  fetch('http://localhost:8000/api/incidents', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      lat: 12.9716, lng: 77.5946, heading_deg: 15,
      confidence: 0.82, incident_type: 'collision'
    })
  }).catch(() => {});
}

(function connectBackend() {
  let settled = false;
  const timeout = setTimeout(() => { if (!settled) { settled = true; setMode(false); } }, 1200);
  try {
    const ws = new WebSocket('ws://localhost:8000/ws/incidents');
    ws.onopen = () => {
      if (settled) return;
      settled = true; clearTimeout(timeout);
      window.__roadalertBackend = ws;
      setMode(true);
    };
    ws.onmessage = (msg) => {
      try {
        const evt = JSON.parse(msg.data);
        if (evt.event === 'incident.reported') triggerIncident();
        if (evt.event === 'incident.confirmed') { /* server-confirmed timing is authoritative */ }
      } catch (e) { /* ignore malformed frames */ }
    };
    ws.onerror = () => { if (!settled) { settled = true; clearTimeout(timeout); setMode(false); } };
    ws.onclose = () => { window.__roadalertBackend = null; setMode(false); };
  } catch (e) {
    settled = true; clearTimeout(timeout); setMode(false);
  }
})();
