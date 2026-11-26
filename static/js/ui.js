const MODES = ["monitor", "collect", "inference"];

export function renderStatus(state) {
  const badge = document.getElementById("status-badge");
  const mockBtn = document.getElementById("btn-mock");
  const isMocking = state.source === "mock";

  mockBtn.textContent = isMocking ? "Stop Mock" : "Enable Mock";
  badge.className =
    "badge " +
    (state.source === "wired" || state.source === "ble"
      ? "connected"
      : isMocking
      ? "mock"
      : "offline");

  badge.textContent =
    state.source === "disconnected"
      ? "Disconnected"
      : `${state.source.toUpperCase()}: ${state.device || ""}`;
}

export function setActiveModeButton(activeMode) {
  MODES.forEach((m) => {
    document.getElementById(`btn-${m}`).classList.toggle("active", m === activeMode);
  });
}

export function updateThresholdDisplay(val) {
  document.getElementById("thresh-val").textContent = val;
}

export function renderDatasetStats(counts) {
  const html = Object.entries(counts)
    .map(([k, v]) => `<span class="badge">${k}: ${v}</span>`)
    .join(" ");
  document.getElementById("dataset-stats").innerHTML =
    html || "<span class='badge'>No trials yet</span>";
}

export function renderThrowFeedback(eventData) {
  const m = eventData.metrics;
  let html =
    `<strong>Peak Gyro:</strong> ${m.peak_angular_velocity_dps} dps &nbsp;|&nbsp; ` +
    `<strong>Peak Energy:</strong> ${m.peak_energy} &nbsp;|&nbsp; ` +
    `<strong>Cross-Axis Var:</strong> ${m.cross_axis_variance}`;

  if (eventData.saved_label) {
    html += `<br/><span style="color:#86efac;">Saved to dataset as: <strong>${eventData.saved_label}</strong></span>`;
  }
  if (eventData.prediction) {
    const conf = (eventData.prediction.confidence * 100).toFixed(1);
    html +=
      `<br/><span style="color:#f5cba7;">Prediction: <strong>${eventData.prediction.predicted_label}</strong> (${conf}%)</span>` +
      `<br/><em>${eventData.prediction.feedback}</em>`;
  }
  if (eventData.error) {
    html += `<br/><span style="color:#fca5a5;">${eventData.error}</span>`;
  }

  document.getElementById("feedback-box").innerHTML = html;
}

export function prependHistoryRow(eventData) {
  const tbody = document.getElementById("history-body");
  if (tbody.firstElementChild && tbody.firstElementChild.children.length === 1) {
    tbody.innerHTML = "";
  }

  const m = eventData.metrics;
  let outcome = "Monitored";
  if (eventData.saved_label) outcome = `Saved (${eventData.saved_label})`;
  if (eventData.prediction) {
    outcome = `${eventData.prediction.predicted_label} (${(eventData.prediction.confidence * 100).toFixed(0)}%)`;
  }

  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td>${eventData.timestamp || ""}</td>
    <td>${m.peak_angular_velocity_dps} dps</td>
    <td>${m.peak_energy}</td>
    <td>${m.cross_axis_variance}</td>
    <td><strong>${outcome}</strong></td>
  `;
  tbody.prepend(tr);
  while (tbody.children.length > 10) tbody.removeChild(tbody.lastChild);
}

export function renderTrainStatus(message) {
  document.getElementById("train-output").textContent = message;
}

export function renderTrainResults(data) {
  document.getElementById("train-output").innerHTML =
    `<p>CV Accuracy: <strong>${data.cv_accuracy}%</strong> | Event F1: <strong>${data.event_detection.f1}%</strong></p>`;
  const img = document.getElementById("cm-img");
  img.src = `/figures/confusion_matrix.png?t=${Date.now()}`;
  img.style.display = "block";
}