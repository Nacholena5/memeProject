let outcomesChart;
let metricsChart;

const fmtPct = (v) => `${(Number(v) * 100).toFixed(1)}%`;
const fmtNum = (v, d = 2) => Number(v).toFixed(d);

async function getJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function shortAddr(addr) {
  if (!addr) return "-";
  return `${addr.slice(0, 5)}...${addr.slice(-4)}`;
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function fillTable(bodyId, rows, scoreKey, cls) {
  const body = document.getElementById(bodyId);
  body.innerHTML = "";

  if (!rows || rows.length === 0) {
    body.innerHTML = '<tr><td colspan="4">Sin datos</td></tr>';
    return;
  }

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="${cls}">${shortAddr(row.token_address)}</td>
      <td>${fmtNum(row[scoreKey], 1)}</td>
      <td>${fmtNum(row.confidence, 2)}</td>
      <td>${new Date(row.ts).toLocaleTimeString()}</td>
    `;
    body.appendChild(tr);
  });
}

function renderOutcomesChart(rows) {
  const ctx = document.getElementById("outcomesChart");
  const labels = rows.slice(0, 40).map((r, i) => `${r.horizon}-${i + 1}`);
  const values = rows.slice(0, 40).map((r) => Number(r.ret_pct));

  if (outcomesChart) outcomesChart.destroy();
  outcomesChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "ret_pct",
        data: values,
        backgroundColor: values.map((v) => (v >= 0 ? "rgba(47,214,181,0.7)" : "rgba(255,111,111,0.7)")),
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { ticks: { color: "#8ea5b3" }, grid: { color: "rgba(255,255,255,0.08)" } },
        x: { ticks: { color: "#8ea5b3" }, grid: { display: false } },
      },
    },
  });
}

function renderMetricsChart(rows) {
  const ctx = document.getElementById("metricsChart");
  const sorted = [...rows].slice(0, 24).reverse();
  const labels = sorted.map((r) => `${r.horizon} ${new Date(r.ts).toLocaleDateString()}`);
  const win = sorted.map((r) => Number(r.win_rate) * 100);
  const exp = sorted.map((r) => Number(r.expectancy));

  if (metricsChart) metricsChart.destroy();
  metricsChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "win_rate %",
          data: win,
          borderColor: "#2fd6b5",
          backgroundColor: "rgba(47,214,181,0.15)",
          yAxisID: "y",
          tension: 0.25,
        },
        {
          label: "expectancy",
          data: exp,
          borderColor: "#f2b84b",
          backgroundColor: "rgba(242,184,75,0.15)",
          yAxisID: "y1",
          tension: 0.25,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: "#8ea5b3" } } },
      scales: {
        y: {
          position: "left",
          ticks: { color: "#8ea5b3" },
          grid: { color: "rgba(255,255,255,0.08)" },
        },
        y1: {
          position: "right",
          ticks: { color: "#8ea5b3" },
          grid: { drawOnChartArea: false },
        },
        x: { ticks: { color: "#8ea5b3" }, grid: { display: false } },
      },
    },
  });
}

async function refresh() {
  const [health, latest, topLong, topShort, outcomes, metricsLive, metricsReports] = await Promise.all([
    getJson("/health"),
    getJson("/signals/latest?limit=200"),
    getJson("/signals/top?decision=LONG_SETUP&limit=10"),
    getJson("/signals/top?decision=SHORT_SETUP&limit=10"),
    getJson("/outcomes/latest?limit=200"),
    getJson("/metrics/live?horizon=4h"),
    getJson("/metrics/reports/latest?limit=60"),
  ]);

  setText("kpiHealth", health.status || "-");
  setText("kpiSignals", latest.length);
  setText("kpiLong", latest.filter((x) => x.decision === "LONG_SETUP").length);
  setText("kpiShort", latest.filter((x) => x.decision === "SHORT_SETUP").length);

  if (metricsLive.status === "insufficient_data") {
    setText("kpiWinrate", "N/A");
    setText("kpiExpectancy", "N/A");
    setText("kpiPrecision", "N/A");
    setText("kpiDrawdown", "N/A");
  } else {
    setText("kpiWinrate", fmtPct(metricsLive.win_rate));
    setText("kpiExpectancy", fmtNum(metricsLive.expectancy, 2));
    setText("kpiPrecision", fmtPct(metricsLive.precision_top_decile));
    setText("kpiDrawdown", `${fmtNum(metricsLive.max_drawdown_proxy, 2)}%`);
  }

  fillTable("topLongBody", topLong, "long_score", "badge-long");
  fillTable("topShortBody", topShort, "short_score", "badge-short");
  renderOutcomesChart(outcomes);
  renderMetricsChart(metricsReports);

  setText("lastUpdate", `Actualizado: ${new Date().toLocaleString()}`);
}

document.getElementById("refreshBtn").addEventListener("click", async () => {
  try {
    await refresh();
  } catch (e) {
    console.error(e);
    alert("No se pudo actualizar el dashboard");
  }
});

refresh().catch((e) => {
  console.error(e);
  setText("lastUpdate", "Error cargando datos");
});
