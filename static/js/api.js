/**
 * api.js is the frontend API & SSE Interface Layer.
 * It raps all backend HTTP endpoints (fetch) and the Server-Sent Events (/stream) subscription
 * so UI and chart modules remain decoupled from network logic.
 */
async function requestJSON(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await res.json();
  if (!res.ok && !data.error) {
    return { error: `Request failed (${res.status})` };
  }
  return data;
}

export const connectSensor = () =>
  requestJSON("/api/connect", { method: "POST" });

export const disconnectSensor = () =>
  requestJSON("/api/disconnect", { method: "POST" });

export const setMock = (enable, profile) =>
  requestJSON("/api/mock", {
    method: "POST",
    body: JSON.stringify({ enable, profile }),
  });

export const setMode = (mode) =>
  requestJSON("/api/mode", {
    method: "POST",
    body: JSON.stringify({ mode }),
  });

export const setLabel = (label) =>
  requestJSON("/api/mode", {
    method: "POST",
    body: JSON.stringify({ label }),
  });

export const captureIdle = () =>
  requestJSON("/api/capture-idle", { method: "POST" });

export const seedSynthetic = () =>
  requestJSON("/api/seed-synthetic", { method: "POST" });

export const fetchStats = () =>
  requestJSON("/api/dataset/stats");

export const trainModel = () =>
  requestJSON("/api/train", { method: "POST" });

export function subscribeStream({ onStatus, onTelemetry, onThrowEvent }) {
  const evtSource = new EventSource("/stream");

  if (onStatus) {
    evtSource.addEventListener("status", (e) => onStatus(JSON.parse(e.data)));
  }
  if (onTelemetry) {
    evtSource.addEventListener("telemetry", (e) => onTelemetry(JSON.parse(e.data)));
  }
  if (onThrowEvent) {
    evtSource.addEventListener("throw_event", (e) => onThrowEvent(JSON.parse(e.data)));
  }

  return evtSource;
}