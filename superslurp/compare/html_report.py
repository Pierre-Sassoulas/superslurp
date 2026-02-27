# pylint: disable=too-many-lines
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
  .chart-row { display: flex; gap: 1rem; }
  .chart-row > .chart-container { flex: 1; min-width: 0; }
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
  #sessionDetail th { background: #f9fafb; position: sticky; top: 0; cursor: pointer; user-select: none; }
  #sessionDetail th:hover { background: #eef2ff; }
  #sessionDetail th .sort-arrow { font-size: 0.7em; margin-left: 0.3em; opacity: 0.4; }
  #sessionDetail th.sort-active .sort-arrow { opacity: 1; }
  #sessionDetail td.num { text-align: right; font-variant-numeric: tabular-nums; }
  #sessionDetail .close-btn { float: right; cursor: pointer; background: none; border: none;
                               font-size: 1.2rem; color: #666; }
  #sessionDetail .close-btn:hover { color: #333; }
  .product-link { color: #2563eb; text-decoration: none; cursor: pointer; }
  .product-link:hover { text-decoration: underline; }
  #productDetail table { width: 100%%; border-collapse: collapse; font-size: 0.9rem; }
  #productDetail th, #productDetail td { text-align: left; padding: 0.3rem 0.6rem;
                                          border-bottom: 1px solid #eee; }
  #productDetail th { background: #f9fafb; position: sticky; top: 0; cursor: pointer; user-select: none; }
  #productDetail th:hover { background: #eef2ff; }
  #productDetail th .sort-arrow { font-size: 0.7em; margin-left: 0.3em; opacity: 0.4; }
  #productDetail th.sort-active .sort-arrow { opacity: 1; }
  #productDetail td.num { text-align: right; font-variant-numeric: tabular-nums; }
  .session-link { color: #2563eb; text-decoration: none; cursor: pointer; }
  .session-link:hover { text-decoration: underline; }
  #shrinkflation { background: #fff; border-radius: 8px; padding: 1rem; margin-bottom: 1rem;
                   box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  #shrinkflation table { width: 100%%; border-collapse: collapse; font-size: 0.9rem; }
  #shrinkflation th, #shrinkflation td { text-align: left; padding: 0.3rem 0.6rem;
                                          border-bottom: 1px solid #eee; }
  #shrinkflation th { background: #f9fafb; position: sticky; top: 0; cursor: pointer; user-select: none; }
  #shrinkflation th:hover { background: #eef2ff; }
  #shrinkflation th .sort-arrow { font-size: 0.7em; margin-left: 0.3em; opacity: 0.4; }
  #shrinkflation th.sort-active .sort-arrow { opacity: 1; }
  #shrinkflation td.num { text-align: right; font-variant-numeric: tabular-nums; }
  .shrink-pct { color: #dc2626; font-weight: 600; }
  #allItems { background: #fff; border-radius: 8px; padding: 1rem; margin-bottom: 1rem;
              box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  #allItems table { width: 100%%; border-collapse: collapse; font-size: 0.9rem; }
  #allItems th, #allItems td { text-align: left; padding: 0.3rem 0.6rem;
                                border-bottom: 1px solid #eee; }
  #allItems th { background: #f9fafb; position: sticky; top: 0; cursor: pointer; user-select: none; }
  #allItems th:hover { background: #eef2ff; }
  #allItems th .sort-arrow { font-size: 0.7em; margin-left: 0.3em; opacity: 0.4; }
  #allItems th.sort-active .sort-arrow { opacity: 1; }
  #allItems td.num { text-align: right; font-variant-numeric: tabular-nums; }
  #allItems .item-row { cursor: pointer; }
  #allItems .item-row:hover { background: #f0f4ff; }
  #allItems .item-row td:first-child::before { content: "\\25B6 "; font-size: 0.7em; color: #999; }
  #allItems .item-row.expanded td:first-child::before { content: "\\25BC "; }
  #allItems .detail-row { background: #fafbfc; }
  #allItems .detail-row td { padding-left: 1.8rem; font-size: 0.85rem; color: #555; }
  .tabs { display: flex; gap: 0; margin-top: 1.5rem; border-bottom: 2px solid #e5e7eb; }
  .tab-btn { padding: 0.5rem 1.2rem; background: none; border: none; border-bottom: 2px solid transparent;
             margin-bottom: -2px; cursor: pointer; font-size: 1rem; color: #666; }
  .tab-btn:hover { color: #333; }
  .tab-btn.active { color: #2563eb; border-bottom-color: #2563eb; font-weight: 600; }
  .tab-panel { display: none; padding-top: 0.5rem; }
  .tab-panel.active { display: block; }
</style>
</head>
<body>
<h1>SuperSlurp — Price Dashboard</h1>

<h2>Session totals over time</h2>
<div class="chart-container">
  <canvas id="sessionChart"></canvas>
</div>
<div id="sessionDetail" class="hidden"></div>

<div class="tabs">
  <button class="tab-btn active" data-tab="tab-allitems">All items</button>
  <button class="tab-btn" data-tab="tab-products">Product price, weight and quality evolution</button>
  <button class="tab-btn" data-tab="tab-shrinkflation">Product degradation</button>
</div>

<div id="tab-products" class="tab-panel">
  <h2>Product price, weight and quality evolution</h2>
  <div class="product-select">
    <input id="productInput" list="productList" placeholder="Search for a product...">
    <datalist id="productList"></datalist>
  </div>
  <div class="chart-row">
    <div class="chart-container">
      <canvas id="priceChart"></canvas>
    </div>
    <div id="gramsSection" class="chart-container hidden">
      <canvas id="gramsChart"></canvas>
    </div>
    <div id="fatSection" class="chart-container hidden">
      <canvas id="fatChart"></canvas>
    </div>
    <div id="volumeSection" class="chart-container hidden">
      <canvas id="volumeChart"></canvas>
    </div>
  </div>
  <div id="productDetail" class="chart-container hidden"></div>
</div>

<div id="tab-shrinkflation" class="tab-panel">
  <h2>Product degradation detected</h2>
  <div id="shrinkflation" class="hidden"></div>
</div>

<div id="tab-allitems" class="tab-panel active">
  <h2>All items</h2>
  <div id="allItems"></div>
</div>

<script>
const DATA = __DATA_JSON__;

// --- Lookup maps ---
const storeMap = {};
DATA.stores.forEach(s => { storeMap[s.id] = s; });
const sessionMap = {};
DATA.sessions.forEach(s => { sessionMap[s.id] = s; });

// --- Tabs ---
function switchTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  const btn = document.querySelector('.tab-btn[data-tab="' + tabId + '"]');
  if (btn) btn.classList.add("active");
  document.getElementById(tabId).classList.add("active");
}
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.onclick = function() { switchTab(this.getAttribute("data-tab")); };
});

// --- Session items index: session_id -> [{name, obs}] ---
const sessionItems = {};
DATA.products.forEach(p => {
  p.observations.forEach(obs => {
    if (!sessionItems[obs.session_id]) sessionItems[obs.session_id] = [];
    sessionItems[obs.session_id].push({ name: p.canonical_name, obs: obs });
  });
});

// --- Session totals (pre-computed in Python) ---
const sessionTotalsRaw = DATA.session_totals;
function buildSessionTotals() {
  return sessionTotalsRaw.map(e => {
    const session = sessionMap[e.session_id];
    const store = session && session.store_id
      ? storeMap[session.store_id] : null;
    return {
      sessionId: e.session_id,
      date: session ? session.date : e.date,
      total: e.total,
      label: store ? store.location : "?"
    };
  });
}

function sortTable(table, colIdx, type) {
  const thead = table.querySelector("thead");
  const th = thead.querySelectorAll("th")[colIdx];
  const prev = th.getAttribute("data-sort");
  const dir = prev === "asc" ? "desc" : "asc";
  thead.querySelectorAll("th").forEach(h => {
    h.classList.remove("sort-active");
    h.removeAttribute("data-sort");
    h.querySelector(".sort-arrow").textContent = "\\u2195";
  });
  th.classList.add("sort-active");
  th.setAttribute("data-sort", dir);
  th.querySelector(".sort-arrow").textContent = dir === "asc" ? "\\u25B2" : "\\u25BC";
  const tbody = table.querySelector("tbody");
  const rows = Array.from(tbody.querySelectorAll("tr"));
  rows.sort((a, b) => {
    const aText = a.children[colIdx].textContent;
    const bText = b.children[colIdx].textContent;
    if (type === "num") {
      const aVal = aText === "-" ? -Infinity : parseFloat(aText);
      const bVal = bText === "-" ? -Infinity : parseFloat(bText);
      return dir === "asc" ? aVal - bVal : bVal - aVal;
    }
    return dir === "asc"
      ? aText.localeCompare(bText)
      : bText.localeCompare(aText);
  });
  rows.forEach(r => tbody.appendChild(r));
}

function makeSortableHeader(label, type) {
  return '<th data-type="' + type + '">'
    + label + '<span class="sort-arrow">\\u2195</span></th>';
}

function bindSortHandlers(container) {
  const table = container.querySelector("table");
  if (!table) return;
  table.querySelectorAll("thead th").forEach((th, idx) => {
    th.onclick = function() {
      sortTable(table, idx, th.getAttribute("data-type"));
    };
  });
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
  html += '<table><thead><tr>'
    + makeSortableHeader('Product', 'str')
    + makeSortableHeader('Qty', 'num')
    + makeSortableHeader('Price', 'num')
    + makeSortableHeader('Grams', 'num')
    + makeSortableHeader('EUR/kg', 'num')
    + makeSortableHeader('Vol (mL)', 'num')
    + makeSortableHeader('EUR/L', 'num')
    + makeSortableHeader('Units', 'num')
    + makeSortableHeader('EUR/unit', 'num')
    + makeSortableHeader('Discount', 'num')
    + '</tr></thead><tbody>';
  items.forEach(it => {
    const o = it.obs;
    html += '<tr>';
    html += '<td><a href="#" class="product-link" data-name="'
      + it.name + '">' + it.name
      + (o.bio ? ' [BIO]' : '')
      + (o.milk_treatment ? ' [' + o.milk_treatment + ']' : '')
      + (o.production ? ' [' + o.production + ']' : '')
      + (o.brand ? ' [' + o.brand + ']' : '')
      + (o.label ? ' [' + o.label + ']' : '')
      + (o.packaging ? ' [' + o.packaging + ']' : '')
      + (o.origin ? ' [' + o.origin + ']' : '')
      + (o.affinage_months ? ' [' + o.affinage_months + ' mois]' : '') + '</a></td>';
    html += '<td class="num">' + o.quantity + '</td>';
    html += '<td class="num">' + o.price.toFixed(2) + '</td>';
    html += '<td class="num">' + (o.grams != null ? o.grams : '-') + '</td>';
    html += '<td class="num">' + (o.price_per_kg != null ? o.price_per_kg.toFixed(2) : '-') + '</td>';
    html += '<td class="num">' + (o.volume_ml != null ? o.volume_ml : '-') + '</td>';
    html += '<td class="num">' + (o.price_per_liter != null ? o.price_per_liter.toFixed(2) : '-') + '</td>';
    html += '<td class="num">' + o.unit_count + '</td>';
    html += '<td class="num">' + (o.price / o.unit_count).toFixed(4) + '</td>';
    html += '<td class="num">' + (o.discount != null ? o.discount.toFixed(2) : '-') + '</td>';
    html += '</tr>';
  });
  html += '</tbody></table>';
  panel.innerHTML = html;
  panel.classList.remove("hidden");
  bindSortHandlers(panel);
  document.getElementById("closeSession").onclick = function() {
    panel.classList.add("hidden");
  };
  panel.querySelectorAll(".product-link").forEach(link => {
    link.onclick = function(e) {
      e.preventDefault();
      const name = this.getAttribute("data-name");
      document.getElementById("productInput").value = name;
      showProduct(name);
      switchTab("tab-products");
      document.getElementById("priceChart")
        .scrollIntoView({ behavior: "smooth" });
    };
  });
  panel.scrollIntoView({ behavior: "smooth" });
}

const sessionTotals = buildSessionTotals();

// --- Category color palette ---
const CATEGORY_COLORS = {
  "Fruits & Legumes": "#22c55e",
  "Fromage": "#eab308",
  "Cremerie": "#06b6d4",
  "Viande & Charcuterie": "#ef4444",
  "Poisson": "#3b82f6",
  "Boulangerie": "#a855f7",
  "Epicerie": "#78716c",
  "Sucre": "#ec4899",
  "Boissons": "#14b8a6",
  "Surgeles": "#6366f1",
  "Bebe": "#f472b6",
  "Hygiene": "#8b5cf6",
  "Entretien": "#64748b",
  "Maison": "#d97706",
  "Textile": "#0ea5e9",
  "Autre": "#a3a3a3",
};

// --- Build stacked category datasets from rolling averages ---
const catRolling = DATA.category_rolling_averages || [];
const allCats = new Set();
catRolling.forEach(e => Object.keys(e.categories).forEach(c => allCats.add(c)));
// Stable ordering: match CATEGORY_COLORS key order, then alphabetical for extras
const catOrder = Object.keys(CATEGORY_COLORS);
const sortedCats = Array.from(allCats).sort((a, b) => {
  const ia = catOrder.indexOf(a);
  const ib = catOrder.indexOf(b);
  if (ia !== -1 && ib !== -1) return ia - ib;
  if (ia !== -1) return -1;
  if (ib !== -1) return 1;
  return a.localeCompare(b);
});

// x-labels: union of rolling avg dates + session dates, sorted
const allDates = new Set(catRolling.map(r => r.date));
sessionTotals.forEach(e => allDates.add(e.date.slice(0, 10)));
const xLabels = Array.from(allDates).sort();

const catDatasets = sortedCats.map(cat => ({
  label: cat,
  type: "line",
  data: xLabels.map(d => {
    const entry = catRolling.find(e => e.date === d);
    if (!entry) return null;
    return entry.categories[cat] || 0;
  }),
  borderColor: CATEGORY_COLORS[cat] || "#a3a3a3",
  backgroundColor: (CATEGORY_COLORS[cat] || "#a3a3a3") + "40",
  fill: true,
  stack: "categories",
  tension: 0.3,
  spanGaps: true,
  pointRadius: 0,
  borderWidth: 1.5,
  order: 10,
}));

// Session dots dataset index = catDatasets.length (after all category datasets)
const sessionDsIndex = catDatasets.length;

const sessionChart = new Chart(document.getElementById("sessionChart"), {
  type: "line",
  data: {
    labels: xLabels,
    datasets: [
      ...catDatasets,
      {
        label: "Session total (click for details)",
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
        stack: false,
        fill: false,
        order: 1,
      },
    ]
  },
  options: {
    responsive: true,
    interaction: {
      mode: "nearest",
      intersect: false,
    },
    onClick: function(evt, elements) {
      const sessionEls = elements.filter(
        el => el.datasetIndex === sessionDsIndex
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
          return item.raw !== null && item.raw !== 0;
        },
        callbacks: {
          label: function(ctx) {
            const val = ctx.raw;
            if (val == null) return null;
            return ctx.dataset.label + ": " + val.toFixed(2) + " EUR";
          },
          afterLabel: function(ctx) {
            if (ctx.datasetIndex === sessionDsIndex) {
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
      },
      legend: {
        position: "top",
        labels: { usePointStyle: true, boxWidth: 8, font: { size: 11 } },
      },
    },
    scales: {
      y: {
        stacked: true,
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
let fatChartInstance = null;
let volumeChartInstance = null;

function showProduct(name) {
  const product = DATA.products.find(p => p.canonical_name === name);
  if (!product) return;

  const points = product.observations
    .map(obs => {
      const session = sessionMap[obs.session_id];
      const store = session.store_id ? storeMap[session.store_id] : null;
      return {
        sessionId: obs.session_id,
        date: session.date,
        price: obs.price,
        grams: obs.grams,
        price_per_kg: obs.price_per_kg,
        volume_ml: obs.volume_ml,
        price_per_liter: obs.price_per_liter,
        unit_count: obs.unit_count,
        discount: obs.discount,
        fat_pct: obs.fat_pct,
        bio: obs.bio || false,
        milk_treatment: obs.milk_treatment || null,
        production: obs.production || null,
        brand: obs.brand || null,
        label: obs.label || null,
        packaging: obs.packaging || null,
        origin: obs.origin || null,
        affinage_months: obs.affinage_months || null,
        store: store ? store.location : "?",
        original_name: obs.original_name || name,
      };
    })
    .filter(p => p.date)
    .sort((a, b) => a.date.localeCompare(b.date));

  const labels = points.map(p => p.date.slice(0, 10));

  // Price chart — use price per unit when multi-pack
  const hasUnits = points.some(p => p.unit_count > 1);
  const priceLabel = hasUnits
    ? name + " — Price per unit (EUR)"
    : name + " — Price (EUR)";
  const priceData = points.map(p =>
    hasUnits ? p.price / p.unit_count : p.price
  );

  if (priceChartInstance) priceChartInstance.destroy();
  priceChartInstance = new Chart(document.getElementById("priceChart"), {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: priceLabel,
        data: priceData,
        borderColor: "#dc2626",
        backgroundColor: "rgba(220,38,38,0.1)",
        fill: true,
        tension: 0.2,
        pointRadius: 5,
        pointBackgroundColor: points.map(p => p.bio ? "#16a34a" : "#dc2626"),
        pointBorderColor: points.map(p => p.bio ? "#16a34a" : "#dc2626"),
      }]
    },
    options: {
      responsive: true,
      onClick: function(evt, elements) {
        if (elements.length > 0) {
          const p = points[elements[0].index];
          const session = sessionMap[p.sessionId];
          const store = session.store_id ? storeMap[session.store_id] : null;
          const totEntry = sessionTotalsRaw.find(e => e.session_id === p.sessionId);
          showSessionDetail({
            sessionId: p.sessionId,
            date: session.date,
            total: totEntry ? totEntry.total : 0,
            label: store ? store.location : "?"
          });
        }
      },
      plugins: {
        tooltip: {
          callbacks: {
            afterLabel: function(ctx) {
              const p = points[ctx.dataIndex];
              let info = p.store;
              if (p.original_name !== name) info += " | " + p.original_name;
              if (hasUnits) info += " | total: " + p.price.toFixed(2) + " EUR";
              if (p.price_per_kg != null) info += " | " + p.price_per_kg + " EUR/kg";
              if (p.price_per_liter != null) info += " | " + p.price_per_liter + " EUR/L";
              if (p.discount != null) info += " | discount: " + p.discount;
              if (p.bio) info += " | BIO";
              if (p.milk_treatment) info += " | " + p.milk_treatment;
              if (p.production) info += " | " + p.production;
              if (p.brand) info += " | " + p.brand;
              if (p.label) info += " | " + p.label;
              if (p.packaging) info += " | " + p.packaging;
              if (p.origin) info += " | " + p.origin;
              if (p.affinage_months) info += " | " + p.affinage_months + " mois";
              return info;
            }
          }
        }
      },
      scales: {
        y: { beginAtZero: true, title: { display: true, text: hasUnits ? "EUR/unit" : "EUR" } },
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
          label: name + (hasUnits ? " — Grams per unit" : " — Grams"),
          data: points.map(p => p.grams != null && hasUnits && p.unit_count
            ? p.grams / p.unit_count : p.grams),
          borderColor: "#16a34a",
          backgroundColor: "rgba(22,163,74,0.1)",
          fill: true,
          tension: 0.2,
          pointRadius: 4,
        }]
      },
      options: {
        responsive: true,
        onClick: function(evt, elements) {
          if (elements.length > 0) {
            const p = points[elements[0].index];
            const session = sessionMap[p.sessionId];
            const store = session.store_id ? storeMap[session.store_id] : null;
            const totEntry = sessionTotalsRaw.find(e => e.session_id === p.sessionId);
            showSessionDetail({
              sessionId: p.sessionId,
              date: session.date,
              total: totEntry ? totEntry.total : 0,
              label: store ? store.location : "?"
            });
          }
        },
        scales: {
          y: { beginAtZero: true, title: { display: true, text: hasUnits ? "Grams/unit" : "Grams" } },
          x: { title: { display: true, text: "Date" } }
        }
      }
    });
  } else {
    gramsSection.classList.add("hidden");
    if (gramsChartInstance) { gramsChartInstance.destroy(); gramsChartInstance = null; }
  }

  // Fat % chart
  const fatSection = document.getElementById("fatSection");
  const hasFat = points.some(p => p.fat_pct != null);
  if (hasFat) {
    fatSection.classList.remove("hidden");
    if (fatChartInstance) fatChartInstance.destroy();
    fatChartInstance = new Chart(document.getElementById("fatChart"), {
      type: "line",
      data: {
        labels: labels,
        datasets: [{
          label: name + " — Fat %%MG",
          data: points.map(p => p.fat_pct),
          borderColor: "#d97706",
          backgroundColor: "rgba(217,119,6,0.1)",
          fill: true,
          tension: 0.2,
          pointRadius: 4,
        }]
      },
      options: {
        responsive: true,
        onClick: function(evt, elements) {
          if (elements.length > 0) {
            const p = points[elements[0].index];
            const session = sessionMap[p.sessionId];
            const store = session.store_id ? storeMap[session.store_id] : null;
            const totEntry = sessionTotalsRaw.find(e => e.session_id === p.sessionId);
            showSessionDetail({
              sessionId: p.sessionId,
              date: session.date,
              total: totEntry ? totEntry.total : 0,
              label: store ? store.location : "?"
            });
          }
        },
        scales: {
          y: { beginAtZero: true, title: { display: true, text: "%%MG" } },
          x: { title: { display: true, text: "Date" } }
        }
      }
    });
  } else {
    fatSection.classList.add("hidden");
    if (fatChartInstance) { fatChartInstance.destroy(); fatChartInstance = null; }
  }

  // Volume chart
  const volumeSection = document.getElementById("volumeSection");
  const hasVolume = points.some(p => p.volume_ml != null);
  if (hasVolume) {
    volumeSection.classList.remove("hidden");
    if (volumeChartInstance) volumeChartInstance.destroy();
    volumeChartInstance = new Chart(document.getElementById("volumeChart"), {
      type: "line",
      data: {
        labels: labels,
        datasets: [{
          label: name + (hasUnits ? " — Volume per unit (mL)" : " — Volume (mL)"),
          data: points.map(p => p.volume_ml != null && hasUnits && p.unit_count
            ? p.volume_ml / p.unit_count : p.volume_ml),
          borderColor: "#7c3aed",
          backgroundColor: "rgba(124,58,237,0.1)",
          fill: true,
          tension: 0.2,
          pointRadius: 4,
        }]
      },
      options: {
        responsive: true,
        onClick: function(evt, elements) {
          if (elements.length > 0) {
            const p = points[elements[0].index];
            const session = sessionMap[p.sessionId];
            const store = session.store_id ? storeMap[session.store_id] : null;
            const totEntry = sessionTotalsRaw.find(e => e.session_id === p.sessionId);
            showSessionDetail({
              sessionId: p.sessionId,
              date: session.date,
              total: totEntry ? totEntry.total : 0,
              label: store ? store.location : "?"
            });
          }
        },
        scales: {
          y: { beginAtZero: true, title: { display: true, text: hasUnits ? "mL/unit" : "mL" } },
          x: { title: { display: true, text: "Date" } }
        }
      }
    });
  } else {
    volumeSection.classList.add("hidden");
    if (volumeChartInstance) { volumeChartInstance.destroy(); volumeChartInstance = null; }
  }

  // Observations table
  const detailDiv = document.getElementById("productDetail");
  let html = '<h3>Observations</h3>';
  html += '<table><thead><tr>'
    + makeSortableHeader('Date', 'str')
    + makeSortableHeader('Original name', 'str')
    + makeSortableHeader('Price', 'num')
    + makeSortableHeader('Grams', 'num')
    + makeSortableHeader('EUR/kg', 'num')
    + makeSortableHeader('Vol (mL)', 'num')
    + makeSortableHeader('EUR/L', 'num')
    + makeSortableHeader('Units', 'num')
    + makeSortableHeader('EUR/unit', 'num')
    + makeSortableHeader('%%MG', 'num')
    + makeSortableHeader('Discount', 'num')
    + makeSortableHeader('BIO', 'str')
    + makeSortableHeader('Milk', 'str')
    + makeSortableHeader('Production', 'str')
    + makeSortableHeader('Brand', 'str')
    + makeSortableHeader('Label', 'str')
    + makeSortableHeader('Packaging', 'str')
    + makeSortableHeader('Origin', 'str')
    + makeSortableHeader('Affinage', 'num')
    + '</tr></thead><tbody>';
  points.forEach(p => {
    html += '<tr>';
    html += '<td><a href="#" class="session-link" data-session-id="'
      + p.sessionId + '">' + p.date.slice(0, 10) + '</a></td>';
    html += '<td>' + p.original_name + '</td>';
    html += '<td class="num">' + p.price.toFixed(2) + '</td>';
    html += '<td class="num">' + (p.grams != null ? p.grams : '-') + '</td>';
    html += '<td class="num">' + (p.price_per_kg != null ? p.price_per_kg.toFixed(2) : '-') + '</td>';
    html += '<td class="num">' + (p.volume_ml != null ? p.volume_ml : '-') + '</td>';
    html += '<td class="num">' + (p.price_per_liter != null ? p.price_per_liter.toFixed(2) : '-') + '</td>';
    html += '<td class="num">' + p.unit_count + '</td>';
    html += '<td class="num">' + (p.price / p.unit_count).toFixed(4) + '</td>';
    html += '<td class="num">' + (p.fat_pct != null ? p.fat_pct : '-') + '</td>';
    html += '<td class="num">' + (p.discount != null ? p.discount.toFixed(2) : '-') + '</td>';
    html += '<td>' + (p.bio ? 'Yes' : '') + '</td>';
    html += '<td>' + (p.milk_treatment || '') + '</td>';
    html += '<td>' + (p.production || '') + '</td>';
    html += '<td>' + (p.brand || '') + '</td>';
    html += '<td>' + (p.label || '') + '</td>';
    html += '<td>' + (p.packaging || '') + '</td>';
    html += '<td>' + (p.origin || '') + '</td>';
    html += '<td class="num">' + (p.affinage_months ? p.affinage_months + ' mois' : '') + '</td>';
    html += '</tr>';
  });
  html += '</tbody></table>';
  detailDiv.innerHTML = html;
  detailDiv.classList.remove("hidden");
  bindSortHandlers(detailDiv);
  detailDiv.querySelectorAll(".session-link").forEach(link => {
    link.onclick = function(e) {
      e.preventDefault();
      const sid = this.getAttribute("data-session-id");
      const session = sessionMap[sid];
      const store = session.store_id ? storeMap[session.store_id] : null;
      const totEntry = sessionTotalsRaw.find(e => e.session_id === sid);
      showSessionDetail({
        sessionId: sid,
        date: session.date,
        total: totEntry ? totEntry.total : 0,
        label: store ? store.location : "?"
      });
      document.getElementById("sessionDetail")
        .scrollIntoView({ behavior: "smooth" });
    };
  });
}

document.getElementById("productInput").addEventListener("input", function() {
  showProduct(this.value);
});

// --- All items table ---
function renderAllItems() {
  // Build summary per product: aggregate totals across all observations
  const products = DATA.products.map(p => {
    const obs = p.observations.map(o => {
      const session = sessionMap[o.session_id];
      const store = session && session.store_id ? storeMap[session.store_id] : null;
      return { ...o, date: session ? session.date.slice(0, 10) : '', store: store ? store.location : '?' };
    }).sort((a, b) => b.date.localeCompare(a.date));
    let totalSpent = 0;
    let totalQty = 0;
    let totalUnits = 0;
    let totalGrams = 0;
    let hasGrams = false;
    let totalVolume = 0;
    let hasVolume = false;
    let hasUnits = false;
    obs.forEach(o => {
      totalSpent += o.price * o.quantity;
      totalQty += o.quantity;
      if (o.grams != null) { totalGrams += o.grams * o.quantity; hasGrams = true; }
      if (o.volume_ml != null) { totalVolume += o.volume_ml * o.quantity; hasVolume = true; }
      totalUnits += o.unit_count * o.quantity;
      if (o.unit_count > 1) hasUnits = true;
    });
    return {
      name: p.canonical_name,
      count: obs.length,
      totalSpent: totalSpent,
      totalQty: totalQty,
      totalGrams: hasGrams ? totalGrams : null,
      meanEurKg: hasGrams && totalGrams > 0 ? (totalSpent / totalGrams) * 1000 : null,
      totalVolume: hasVolume ? totalVolume : null,
      meanEurL: hasVolume && totalVolume > 0 ? (totalSpent / totalVolume) * 1000 : null,
      totalUnits: hasUnits ? totalUnits : null,
      meanEurUnit: hasUnits && totalUnits > 0 ? totalSpent / totalUnits : null,
      obs: obs,
    };
  });
  products.sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));

  const panel = document.getElementById("allItems");
  let html = '<table><thead><tr>'
    + makeSortableHeader('Product', 'str')
    + makeSortableHeader('Obs', 'num')
    + makeSortableHeader('Total spent', 'num')
    + makeSortableHeader('Qty bought', 'num')
    + makeSortableHeader('Total grams', 'num')
    + makeSortableHeader('Mean EUR/kg', 'num')
    + makeSortableHeader('Total vol (mL)', 'num')
    + makeSortableHeader('Mean EUR/L', 'num')
    + makeSortableHeader('Total units', 'num')
    + makeSortableHeader('Mean EUR/unit', 'num')
    + '</tr></thead><tbody>';
  products.forEach((p, idx) => {
    html += '<tr class="item-row" data-idx="' + idx + '">';
    html += '<td><a href="#" class="product-link" data-name="'
      + p.name + '">' + p.name + '</a></td>';
    html += '<td class="num">' + p.count + '</td>';
    html += '<td class="num">' + p.totalSpent.toFixed(2) + '</td>';
    html += '<td class="num">' + p.totalQty + '</td>';
    html += '<td class="num">' + (p.totalGrams != null ? p.totalGrams : '-') + '</td>';
    html += '<td class="num">' + (p.meanEurKg != null ? p.meanEurKg.toFixed(2) : '-') + '</td>';
    html += '<td class="num">' + (p.totalVolume != null ? p.totalVolume : '-') + '</td>';
    html += '<td class="num">' + (p.meanEurL != null ? p.meanEurL.toFixed(2) : '-') + '</td>';
    html += '<td class="num">' + (p.totalUnits != null ? p.totalUnits : '-') + '</td>';
    html += '<td class="num">' + (p.meanEurUnit != null ? p.meanEurUnit.toFixed(4) : '-') + '</td>';
    html += '</tr>';
  });
  html += '</tbody></table>';
  panel.innerHTML = html;
  bindSortHandlers(panel);

  // Product name click -> show price & weight evolution
  panel.querySelectorAll(".product-link").forEach(link => {
    link.onclick = function(e) {
      e.preventDefault();
      e.stopPropagation();
      const name = this.getAttribute("data-name");
      document.getElementById("productInput").value = name;
      showProduct(name);
      switchTab("tab-products");
      document.getElementById("priceChart")
        .scrollIntoView({ behavior: "smooth" });
    };
  });

  // Click to expand/collapse detail rows
  panel.querySelectorAll(".item-row").forEach(row => {
    row.onclick = function() {
      const idx = parseInt(this.getAttribute("data-idx"));
      const p = products[idx];
      const expanded = this.classList.toggle("expanded");
      // Remove existing detail rows for this product
      let next = this.nextElementSibling;
      while (next && next.classList.contains("detail-row")) {
        const toRemove = next;
        next = next.nextElementSibling;
        toRemove.remove();
      }
      if (!expanded) return;
      // Insert detail rows
      const tbody = this.parentNode;
      const ref = this.nextElementSibling;
      p.obs.forEach(o => {
        const tr = document.createElement("tr");
        tr.className = "detail-row";
        tr.innerHTML = '<td><a href="#" class="session-link" data-session-id="'
          + o.session_id + '">' + o.date + ' — ' + o.store + '</a></td>'
          + '<td class="num">' + o.quantity + '</td>'
          + '<td class="num">' + o.price.toFixed(2) + '</td>'
          + '<td class="num">' + (o.grams != null ? o.grams : '-') + '</td>'
          + '<td class="num">' + (o.price_per_kg != null ? o.price_per_kg.toFixed(2) : '-') + '</td>'
          + '<td class="num">' + (o.volume_ml != null ? o.volume_ml : '-') + '</td>'
          + '<td class="num">' + (o.price_per_liter != null ? o.price_per_liter.toFixed(2) : '-') + '</td>'
          + '<td class="num">' + o.unit_count + '</td>'
          + '<td class="num">' + (o.price / o.unit_count).toFixed(4) + '</td>';
        tbody.insertBefore(tr, ref);
        tr.querySelector(".session-link").onclick = function(e) {
          e.preventDefault();
          e.stopPropagation();
          const sid = this.getAttribute("data-session-id");
          const session = sessionMap[sid];
          const store = session.store_id ? storeMap[session.store_id] : null;
          const totEntry = sessionTotalsRaw.find(e => e.session_id === sid);
          showSessionDetail({
            sessionId: sid,
            date: session.date,
            total: totEntry ? totEntry.total : 0,
            label: store ? store.location : "?"
          });
          document.getElementById("sessionDetail")
            .scrollIntoView({ behavior: "smooth" });
        };
      });
    };
  });
}
renderAllItems();

// --- Product degradation detection ---
function detectDegradation() {
  const results = [];
  DATA.products.forEach(p => {
    const sorted = p.observations
      .filter(o => o.grams != null || o.fat_pct != null || o.volume_ml != null)
      .map(o => ({ ...o, date: sessionMap[o.session_id].date }))
      .sort((a, b) => a.date.localeCompare(b.date));
    if (sorted.length < 2) return;
    for (let i = sorted.length - 1; i >= 1; i--) {
      const prev = sorted[i - 1];
      const curr = sorted[i];
      if (curr.price < prev.price) continue;
      const gramsDown = curr.grams != null && prev.grams != null && curr.grams < prev.grams;
      const volumeDown = curr.volume_ml != null && prev.volume_ml != null && curr.volume_ml < prev.volume_ml;
      const fatDown = curr.fat_pct != null && prev.fat_pct != null && curr.fat_pct < prev.fat_pct;
      if (gramsDown || volumeDown || fatDown) {
        results.push({
          name: p.canonical_name,
          dateBefore: prev.date.slice(0, 10),
          dateAfter: curr.date.slice(0, 10),
          gramsBefore: prev.grams, gramsAfter: curr.grams,
          volumeBefore: prev.volume_ml, volumeAfter: curr.volume_ml,
          fatBefore: prev.fat_pct, fatAfter: curr.fat_pct,
          priceBefore: prev.price, priceAfter: curr.price,
          gramsDown: gramsDown, volumeDown: volumeDown, fatDown: fatDown,
        });
        break;
      }
    }
  });
  return results;
}

function renderDegradation() {
  const items = detectDegradation();
  const panel = document.getElementById("shrinkflation");
  if (items.length === 0) {
    panel.classList.add("hidden");
    return;
  }
  let html = '<table><thead><tr>'
    + makeSortableHeader('Product', 'str')
    + makeSortableHeader('Type', 'str')
    + makeSortableHeader('Date before', 'str')
    + makeSortableHeader('Date after', 'str')
    + makeSortableHeader('Before', 'str')
    + makeSortableHeader('After', 'str')
    + makeSortableHeader('Change', 'num')
    + makeSortableHeader('Price before', 'num')
    + makeSortableHeader('Price after', 'num')
    + '</tr></thead><tbody>';
  items.forEach(it => {
    const types = [];
    if (it.gramsDown) types.push('grams');
    if (it.volumeDown) types.push('volume');
    if (it.fatDown) types.push('%%MG');
    const typeStr = types.join(', ');
    // Show grams row
    if (it.gramsDown) {
      const pct = ((it.gramsAfter - it.gramsBefore) / it.gramsBefore * 100).toFixed(1);
      html += '<tr>';
      html += '<td><a href="#" class="product-link" data-name="'
        + it.name + '">' + it.name + '</a></td>';
      html += '<td>Grams</td>';
      html += '<td>' + it.dateBefore + '</td>';
      html += '<td>' + it.dateAfter + '</td>';
      html += '<td class="num">' + it.gramsBefore + 'g</td>';
      html += '<td class="num">' + it.gramsAfter + 'g</td>';
      html += '<td class="num shrink-pct">' + pct + '%%</td>';
      html += '<td class="num">' + it.priceBefore.toFixed(2) + '</td>';
      html += '<td class="num">' + it.priceAfter.toFixed(2) + '</td>';
      html += '</tr>';
    }
    // Show volume row
    if (it.volumeDown) {
      const pct = ((it.volumeAfter - it.volumeBefore) / it.volumeBefore * 100).toFixed(1);
      html += '<tr>';
      html += '<td><a href="#" class="product-link" data-name="'
        + it.name + '">' + it.name + '</a></td>';
      html += '<td>Volume</td>';
      html += '<td>' + it.dateBefore + '</td>';
      html += '<td>' + it.dateAfter + '</td>';
      html += '<td class="num">' + it.volumeBefore + 'mL</td>';
      html += '<td class="num">' + it.volumeAfter + 'mL</td>';
      html += '<td class="num shrink-pct">' + pct + '%%</td>';
      html += '<td class="num">' + it.priceBefore.toFixed(2) + '</td>';
      html += '<td class="num">' + it.priceAfter.toFixed(2) + '</td>';
      html += '</tr>';
    }
    // Show fat row
    if (it.fatDown) {
      const pct = ((it.fatAfter - it.fatBefore) / it.fatBefore * 100).toFixed(1);
      html += '<tr>';
      html += '<td><a href="#" class="product-link" data-name="'
        + it.name + '">' + it.name + '</a></td>';
      html += '<td>%%MG</td>';
      html += '<td>' + it.dateBefore + '</td>';
      html += '<td>' + it.dateAfter + '</td>';
      html += '<td class="num">' + it.fatBefore + '%%</td>';
      html += '<td class="num">' + it.fatAfter + '%%</td>';
      html += '<td class="num shrink-pct">' + pct + '%%</td>';
      html += '<td class="num">' + it.priceBefore.toFixed(2) + '</td>';
      html += '<td class="num">' + it.priceAfter.toFixed(2) + '</td>';
      html += '</tr>';
    }
  });
  html += '</tbody></table>';
  panel.innerHTML = html;
  panel.classList.remove("hidden");
  bindSortHandlers(panel);
  panel.querySelectorAll(".product-link").forEach(link => {
    link.onclick = function(e) {
      e.preventDefault();
      const name = this.getAttribute("data-name");
      document.getElementById("productInput").value = name;
      showProduct(name);
      switchTab("tab-products");
      document.getElementById("priceChart")
        .scrollIntoView({ behavior: "smooth" });
    };
  });
}
renderDegradation();
</script>
</body>
</html>
"""


def generate_html(data: dict[str, Any]) -> str:
    """Generate a self-contained HTML dashboard from compare result data."""
    data_json = json.dumps(data, ensure_ascii=False)
    return _HTML_TEMPLATE.replace("__DATA_JSON__", data_json)
