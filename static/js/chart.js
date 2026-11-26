export function createTelemetryChart(canvasId, initialThreshold, maxPoints = 100) {
  let threshold = Number(initialThreshold);
  const ctx = document.getElementById(canvasId).getContext("2d");

  const chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        { label: "Window Energy", data: [], borderColor: "#2E7D32", tension: 0.2, pointRadius: 0 },
        { label: "Gyro Mag (dps)", data: [], borderColor: "#F4F1EA", tension: 0.2, pointRadius: 0 },
        { label: "Threshold", data: [], borderColor: "#C82333", borderDash: [6, 4], pointRadius: 0 },
      ],
    },
    options: {
      animation: false,
      plugins: { legend: { labels: { color: "#F4F1EA" } } },
      scales: {
        x: { display: false },
        y: { ticks: { color: "#cbd5e1" }, grid: { color: "#2F3640" } },
      },
    },
  });

  return {
    setThreshold(val) {
      threshold = Number(val);
    },
    pushPoint({ t, energy, gyro_mag }) {
      chart.data.labels.push(t);
      chart.data.datasets[0].data.push(energy);
      chart.data.datasets[1].data.push(gyro_mag);
      chart.data.datasets[2].data.push(threshold);

      if (chart.data.labels.length > maxPoints) {
        chart.data.labels.shift();
        chart.data.datasets.forEach((ds) => ds.data.shift());
      }
      chart.update();
    },
  };
}