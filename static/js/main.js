/**
 * main.js is the dashboard application controller
 * It initializes the telemetry chart, binds UI event listeners, 
 * manages client-side mock state, and connects the live SSE 
 * stream to the chart and UI renderers.
 */
import * as api from "./api.js";
import { createTelemetryChart } from "./chart.js";
import * as ui from "./ui.js";

const initialThreshold = Number(document.body.dataset.threshold || 25);
const chart = createTelemetryChart("telemetryChart", initialThreshold);

let isMocking = false;

async function refreshStats() {
  const data = await api.fetchStats();
  if (data.state) {
    isMocking = data.state.source === "mock";
    ui.renderStatus(data.state);
  }
  if (data.counts) {
    ui.renderDatasetStats(data.counts);
  }
}

// Connection controls
document.getElementById("btn-connect").addEventListener("click", async () => {
  const data = await api.connectSensor();
  if (data.error) alert(data.error);
  refreshStats();
});

document.getElementById("btn-disconnect").addEventListener("click", async () => {
  await api.disconnectSensor();
  refreshStats();
});

document.getElementById("btn-mock").addEventListener("click", async () => {
  const profile = document.getElementById("mock-profile").value;
  const state = await api.setMock(!isMocking, profile);
  isMocking = state.source === "mock";
  ui.renderStatus(state);
});

document.getElementById("mock-profile").addEventListener("change", async (e) => {
  if (!isMocking) return;
  await api.setMock(true, e.target.value);
});

// Threshold preview slider
document.getElementById("thresh-slider").addEventListener("input", (e) => {
  chart.setThreshold(e.target.value);
  ui.updateThresholdDisplay(e.target.value);
});

// Workflow mode buttons
["monitor", "collect", "inference"].forEach((mode) => {
  document.getElementById(`btn-${mode}`).addEventListener("click", async () => {
    await api.setMode(mode);
    ui.setActiveModeButton(mode);
  });
});

// Labeling & dataset controls
document.getElementById("label-select").addEventListener("change", (e) => {
  api.setLabel(e.target.value);
});

document.getElementById("btn-capture-idle").addEventListener("click", async () => {
  const data = await api.captureIdle();
  if (data.error) alert(data.error);
  refreshStats();
});

document.getElementById("btn-seed").addEventListener("click", async () => {
  await api.seedSynthetic();
  refreshStats();
});

document.getElementById("btn-download").addEventListener("click", () => {
  window.location = "/api/dataset/download";
});

document.getElementById("btn-train").addEventListener("click", async () => {
  ui.renderTrainStatus("Training & running cross-validation...");
  const data = await api.trainModel();
  if (data.error) {
    ui.renderTrainStatus(`Error: ${data.error}`);
    return;
  }
  ui.renderTrainResults(data);
  refreshStats();
});

// Live SSE stream
api.subscribeStream({
  onStatus: (state) => {
    isMocking = state.source === "mock";
    ui.renderStatus(state);
  },
  onTelemetry: (point) => chart.pushPoint(point),
  onThrowEvent: (eventData) => {
    ui.renderThrowFeedback(eventData);
    ui.prependHistoryRow(eventData);
    if (eventData.saved_label) refreshStats();
  },
});

refreshStats();
setInterval(refreshStats, 5000);