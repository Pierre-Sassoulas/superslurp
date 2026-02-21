from __future__ import annotations

import json
from typing import Any

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SuperSlurp — Price Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #f5f5f5; color: #333; padding: 1rem; }
  h1 { text-align: center; margin-bottom: 1rem; }
  h2 { margin: 1.5rem 0 0.5rem; }
  .chart-container { background: #fff; border-radius: 8px; padding: 1rem; margin-bottom: 1rem;
                     box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  canvas { width: 100%% !important; }
  .product-select { margin: 1rem 0; }
  .product-select input { width: 100%%; padding: 0.5rem; font-size: 1rem;
                          border: 1px solid #ccc; border-radius: 4px; }
  .hidden { display: none; }
  #sessionDetail { background: #fff; border-radius: 8px; padding: 1rem; margin-bottom: 1rem;
                   box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  #sessionDetail h3 { margin-bottom: 0.5rem; }
  #sessionDetail table { width: 100%%; border-collapse: collapse; font-size: 0.9rem; }
  #sessionDetail th, #sessionDetail td { text-align: left; padding: 0.3rem 0.6rem;
                                          border-bottom: 1px solid #eee; }
  #sessionDetail th { background: #f9fafb; position: sticky; top: 0; }
  #sessionDetail td.num { text-align: right; font-variant-numeric: tabular-nums; }
  #sessionDetail .close-btn { float: right; cursor: pointer; background: none; border: none;
                               font-size: 1.2rem; color: #666; }
  #sessionDetail .close-btn:hover { color: #333; }
  .product-link { color: #2563eb; text-decoration: none; }
  .product-link:hover { text-decoration: underline; }
</style>
</head>
<body>
<h1>SuperSlurp — Price Dashboard</h1>

<h2>Session totals over time</h2>
<div class="chart-container">
  <canvas id="sessionChart"></canvas>
</div>
<div id="sessionDetail" class="hidden"></div>

<h2>Product price evolution</h2>
<div class="product-select">
  <input id="productInput" list="productList" placeholder="Search for a product...">
  <datalist id="productList"></datalist>
</div>
<div class="chart-container">
  <canvas id="priceChart"></canvas>
</div>
<div id="gramsSection" class="chart-container hidden">
  <canvas id="gramsChart"></canvas>
</div>

<script>
const DATA = __DATA_JSON__;

// --- Lookup maps ---
const storeMap = {};
DATA.stores.forEach(s => { storeMap[s.id] = s; });
const sessionMap = {};
DATA.sessions.forEach(s => { sessionMap[s.id] = s; });

// --- Session items index: session_id -> [{name, obs}] ---
const sessionItems = {};
DATA.products.forEach(p => {
  p.observations.forEach(obs => {
    if (!sessionItems[obs.session_id]) sessionItems[obs.session_id] = [];
    sessionItems[obs.session_id].push({ name: p.canonical_name, obs: obs });
  });
});

// --- Session totals chart ---
function buildSessionTotals() {
  const totals = {};
  DATA.products.forEach(p => {
    p.observations.forEach(obs => {
      if (!totals[obs.session_id]) totals[obs.session_id] = 0;
      totals[obs.session_id] += obs.price * obs.quantity;
    });
  });
  const entries = Object.entries(totals)
    .map(([sid, total]) => {
      const sessionId = parseInt(sid);
      const session = sessionMap[sessionId];
      const store = session.store_id ? storeMap[session.store_id] : null;
      return {
        sessionId: sessionId,
        date: session.date,
        total: Math.round(total * 100) / 100,
        label: store ? store.location : "?"
      };
    })
    .filter(e => e.date)
    .sort((a, b) => a.date.localeCompare(b.date));

  return entries;
}

function showSessionDetail(entry) {
  const items = (sessionItems[entry.sessionId] || [])
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name));
  const panel = document.getElementById("sessionDetail");
  let html = '<button class="close-btn" id="closeSession">'
    + '&times;</button>';
  html += '<h3>' + entry.date.slice(0, 10) + ' — '
    + entry.label + ' — ' + entry.total + ' EUR</h3>';
  html += '<table><thead><tr><th>Product</th><th>Qty</th>'
    + '<th>Price</th><th>Grams</th><th>EUR/kg</th>'
    + '<th>Discount</th></tr></thead><tbody>';
  items.forEach(it => {
    const o = it.obs;
    html += '<tr>';
    html += '<td><a href="#" class="product-link" data-name="'
      + it.name + '">' + it.name
      + (o.bio ? ' [BIO]' : '') + '</a></td>';
    html += '<td class="num">' + o.quantity + '</td>';
    html += '<td class="num">' + o.price.toFixed(2) + '</td>';
    html += '<td class="num">' + (o.grams != null ? o.grams : '-') + '</td>';
    html += '<td class="num">' + (o.price_per_kg != null ? o.price_per_kg.toFixed(2) : '-') + '</td>';
    html += '<td class="num">' + (o.discount != null ? o.discount.toFixed(2) : '-') + '</td>';
    html += '</tr>';
  });
  html += '</tbody></table>';
  panel.innerHTML = html;
  panel.classList.remove("hidden");
  document.getElementById("closeSession").onclick = function() {
    panel.classList.add("hidden");
  };
  panel.querySelectorAll(".product-link").forEach(link => {
    link.onclick = function(e) {
      e.preventDefault();
      const name = this.getAttribute("data-name");
      document.getElementById("productInput").value = name;
      showProduct(name);
      document.getElementById("priceChart")
        .scrollIntoView({ behavior: "smooth" });
    };
  });
  panel.scrollIntoView({ behavior: "smooth" });
}

const sessionTotals = buildSessionTotals();

// Build EUR/month — only months that have sessions
function buildMonthlyRate(totals) {
  if (totals.length === 0) return [];
  const byMonth = {};
  totals.forEach(e => {
    const month = e.date.slice(0, 7);
    if (!byMonth[month]) byMonth[month] = 0;
    byMonth[month] += e.total;
  });
  return Object.entries(byMonth)
    .map(([month, sum]) => ({
      month: month,
      value: Math.round(sum * 100) / 100
    }))
    .sort((a, b) => a.month.localeCompare(b.month));
}

const monthlyRate = buildMonthlyRate(sessionTotals);

// x-labels: union of months + individual session dates, sorted
const allDates = new Set(monthlyRate.map(m => m.month));
sessionTotals.forEach(e => allDates.add(e.date.slice(0, 10)));
const xLabels = Array.from(allDates).sort();

const sessionChart = new Chart(document.getElementById("sessionChart"), {
  type: "bar",
  data: {
    labels: xLabels,
    datasets: [
      {
        label: "EUR/month",
        type: "line",
        data: xLabels.map(d => {
          const m = monthlyRate.find(m => m.month === d);
          return m ? m.value : null;
        }),
        borderColor: "#2563eb",
        backgroundColor: "rgba(37,99,235,0.08)",
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        borderWidth: 2,
        spanGaps: true,
        order: 2,
      },
      {
        label: "Session (click for details)",
        type: "line",
        data: xLabels.map(d => {
          const s = sessionTotals.find(
            e => e.date.slice(0, 10) === d
          );
          return s ? s.total : null;
        }),
        borderColor: "transparent",
        backgroundColor: "rgba(220,38,38,0.7)",
        pointRadius: 5,
        pointHoverRadius: 8,
        pointBackgroundColor: "rgba(220,38,38,0.7)",
        showLine: false,
        order: 1,
      }
    ]
  },
  options: {
    responsive: true,
    onClick: function(evt, elements) {
      const sessionEls = elements.filter(
        el => el.datasetIndex === 1
      );
      if (sessionEls.length > 0) {
        const date = xLabels[sessionEls[0].index];
        const entry = sessionTotals.find(
          e => e.date.slice(0, 10) === date
        );
        if (entry) showSessionDetail(entry);
      }
    },
    plugins: {
      tooltip: {
        filter: function(item) {
          return item.raw !== null;
        },
        callbacks: {
          afterLabel: function(ctx) {
            if (ctx.datasetIndex === 1) {
              const date = xLabels[ctx.dataIndex];
              const entry = sessionTotals.find(
                e => e.date.slice(0, 10) === date
              );
              return entry
                ? entry.label + " (click for details)"
                : "";
            }
            return "";
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        title: { display: true, text: "EUR" }
      },
      x: {
        title: { display: true, text: "Date" },
        ticks: { maxTicksLimit: 30 }
      }
    }
  }
});

// --- Product selector ---
const productNames = DATA.products.map(p => p.canonical_name).sort();
const datalist = document.getElementById("productList");
productNames.forEach(name => {
  const opt = document.createElement("option");
  opt.value = name;
  datalist.appendChild(opt);
});

let priceChartInstance = null;
let gramsChartInstance = null;

function showProduct(name) {
  const product = DATA.products.find(p => p.canonical_name === name);
  if (!product) return;

  const points = product.observations
    .map(obs => {
      const session = sessionMap[obs.session_id];
      const store = session.store_id ? storeMap[session.store_id] : null;
      return {
        date: session.date,
        price: obs.price,
        grams: obs.grams,
        price_per_kg: obs.price_per_kg,
        discount: obs.discount,
        bio: obs.bio || false,
        store: store ? store.location : "?",
      };
    })
    .filter(p => p.date)
    .sort((a, b) => a.date.localeCompare(b.date));

  const labels = points.map(p => p.date.slice(0, 10));

  // Price chart
  if (priceChartInstance) priceChartInstance.destroy();
  priceChartInstance = new Chart(document.getElementById("priceChart"), {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: name + " — Price (EUR)",
        data: points.map(p => p.price),
        borderColor: "#dc2626",
        backgroundColor: "rgba(220,38,38,0.1)",
        fill: true,
        tension: 0.2,
        pointRadius: 4,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        tooltip: {
          callbacks: {
            afterLabel: function(ctx) {
              const p = points[ctx.dataIndex];
              let info = p.store;
              if (p.price_per_kg != null) info += " | " + p.price_per_kg + " EUR/kg";
              if (p.discount != null) info += " | discount: " + p.discount;
              if (p.bio) info += " | BIO";
              return info;
            }
          }
        }
      },
      scales: {
        y: { beginAtZero: false, title: { display: true, text: "EUR" } },
        x: { title: { display: true, text: "Date" } }
      }
    }
  });

  // Grams chart
  const gramsSection = document.getElementById("gramsSection");
  const hasGrams = points.some(p => p.grams != null);
  if (hasGrams) {
    gramsSection.classList.remove("hidden");
    if (gramsChartInstance) gramsChartInstance.destroy();
    gramsChartInstance = new Chart(document.getElementById("gramsChart"), {
      type: "line",
      data: {
        labels: labels,
        datasets: [{
          label: name + " — Grams",
          data: points.map(p => p.grams),
          borderColor: "#16a34a",
          backgroundColor: "rgba(22,163,74,0.1)",
          fill: true,
          tension: 0.2,
          pointRadius: 4,
        }]
      },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: false, title: { display: true, text: "Grams" } },
          x: { title: { display: true, text: "Date" } }
        }
      }
    });
  } else {
    gramsSection.classList.add("hidden");
    if (gramsChartInstance) { gramsChartInstance.destroy(); gramsChartInstance = null; }
  }
}

document.getElementById("productInput").addEventListener("input", function() {
  showProduct(this.value);
});
</script>
</body>
</html>
"""


def generate_html(data: dict[str, Any]) -> str:
    """Generate a self-contained HTML dashboard from compare result data."""
    data_json = json.dumps(data, ensure_ascii=False)
    return _HTML_TEMPLATE.replace("__DATA_JSON__", data_json)
