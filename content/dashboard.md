---
title: "Economic & Market Dashboard"
description: "Real-time economic indicators and market data"
menu:
  main:
    weight: 2
---

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>

<style>
.dashboard-updated { text-align: center; margin-bottom: 20px; color: #666; }
.section-title { font-size: 1.3em; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 8px; margin: 25px 0 15px 0; }
.dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; margin-bottom: 30px; }
.metric-card { border: 1px solid #ddd; padding: 15px; border-radius: 8px; background: #f9f9f9; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
.metric-card h4 { margin: 0 0 8px 0; color: #333; font-size: 1em; }
.value { font-size: 1.8em; font-weight: bold; color: #2c3e50; }
.period { color: #7f8c8d; font-size: 0.85em; margin-top: 3px; }
.chart-container { height: 120px; margin-top: 12px; }
.positive { color: #27ae60; }
.negative { color: #e74c3c; }
.neutral { color: #3498db; }
.change-indicator { font-size: 0.85em; margin-top: 4px; }
.change-indicator .arrow { font-weight: bold; margin-right: 3px; }
.change-indicator .yoy { margin-right: 8px; }
.change-indicator .momentum { font-size: 0.9em; color: #7f8c8d; }
</style>

<div id="dashboard-container">
  <div class="dashboard-updated">Last updated: <span id="last-update">Loading...</span></div>

  <h3 class="section-title">Economic Indicators</h3>
  <div class="dashboard-grid">
    <div class="metric-card">
      <h4>GDP (Quarterly)</h4>
      <div id="gdp">Loading...</div>
      <div class="chart-container"><canvas id="chart-gdp"></canvas></div>
    </div>
    <div class="metric-card">
      <h4>Consumer Confidence</h4>
      <div id="consumer-confidence">Loading...</div>
      <div class="chart-container"><canvas id="chart-cc"></canvas></div>
    </div>
    <div class="metric-card">
      <h4>CPI (Consumer Price Index)</h4>
      <div id="cpi">Loading...</div>
      <div class="chart-container"><canvas id="chart-cpi"></canvas></div>
    </div>
    <div class="metric-card">
      <h4>Unemployment Rate</h4>
      <div id="unemployment">Loading...</div>
      <div class="chart-container"><canvas id="chart-unemp"></canvas></div>
    </div>
    <div class="metric-card">
      <h4>Employment (Thousands)</h4>
      <div id="employment">Loading...</div>
      <div class="chart-container"><canvas id="chart-emp"></canvas></div>
    </div>
    <div class="metric-card">
      <h4>Average Hourly Wages</h4>
      <div id="wages">Loading...</div>
      <div class="chart-container"><canvas id="chart-wages"></canvas></div>
    </div>
    <div class="metric-card">
      <h4>Housing Starts (Thousands)</h4>
      <div id="housing">Loading...</div>
      <div class="chart-container"><canvas id="chart-housing"></canvas></div>
    </div>
  </div>

  <h3 class="section-title">Markets & Interest Rates</h3>
  <div class="dashboard-grid">
    <div class="metric-card">
      <h4>S&P 500 Index</h4>
      <div id="sp500">Loading...</div>
      <div class="chart-container"><canvas id="chart-spy"></canvas></div>
    </div>
    <div class="metric-card">
      <h4>Fed Funds Rate</h4>
      <div id="fed-rate">Loading...</div>
      <div class="chart-container"><canvas id="chart-fed"></canvas></div>
    </div>
    <div class="metric-card">
      <h4>10-Year Treasury Yield</h4>
      <div id="treasury">Loading...</div>
      <div class="chart-container"><canvas id="chart-treasury"></canvas></div>
    </div>
  </div>

  <h3 class="section-title">Currency Exchange Rates (USD Strength)</h3>
  <div class="dashboard-grid">
    <div class="metric-card">
      <h4>USD / Canadian Dollar</h4>
      <div id="usd-cad">Loading...</div>
      <div class="chart-container"><canvas id="chart-cad"></canvas></div>
    </div>
    <div class="metric-card">
      <h4>USD / Euro</h4>
      <div id="usd-eur">Loading...</div>
      <div class="chart-container"><canvas id="chart-eur"></canvas></div>
    </div>
    <div class="metric-card">
      <h4>USD / Japanese Yen</h4>
      <div id="usd-jpy">Loading...</div>
      <div class="chart-container"><canvas id="chart-jpy"></canvas></div>
    </div>
    <div class="metric-card">
      <h4>USD / Mexican Peso</h4>
      <div id="usd-mxn">Loading...</div>
      <div class="chart-container"><canvas id="chart-mxn"></canvas></div>
    </div>
  </div>
</div>

<script>
const charts = {};

function formatDate(dateStr) {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
}

function formatShortDate(dateStr) {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Calculate year-over-year or period change
function calcChange(data, isPercent = false) {
  if (!data || data.length < 2) return null;
  const latest = data[data.length - 1].value;
  const oldest = data[0].value;
  if (oldest === 0) return null;

  if (isPercent) {
    // For metrics already in percent (unemployment, rates), show point change
    const change = latest - oldest;
    return { change: change, pctChange: null, isPointChange: true };
  } else {
    // For other metrics, show percent change
    const pctChange = ((latest - oldest) / oldest) * 100;
    return { change: latest - oldest, pctChange: pctChange, isPointChange: false };
  }
}

// Calculate 30-day momentum for daily data
function calc30DayMomentum(data, isPercent = false) {
  if (!data || data.length < 30) return null;
  const latest = data[data.length - 1].value;
  const thirtyDaysAgo = data[data.length - 30].value;
  if (thirtyDaysAgo === 0) return null;

  if (isPercent) {
    return { change: latest - thirtyDaysAgo, isPointChange: true };
  } else {
    const pctChange = ((latest - thirtyDaysAgo) / thirtyDaysAgo) * 100;
    return { pctChange: pctChange, isPointChange: false };
  }
}

// Get trend arrow based on change
function getTrendArrow(change) {
  if (change > 0.5) return { arrow: '\u2191', class: 'positive' };  // Up arrow
  if (change < -0.5) return { arrow: '\u2193', class: 'negative' }; // Down arrow
  return { arrow: '\u2192', class: 'neutral' };  // Right arrow (stable)
}

// Format change indicator HTML
function formatChangeIndicator(changeData, momentumData = null, invertColors = false) {
  if (!changeData) return '';

  const change = changeData.pctChange !== null ? changeData.pctChange : changeData.change;
  const trend = getTrendArrow(change);

  // Some metrics are "bad" when they go up (unemployment), so invert colors
  let colorClass = trend.class;
  if (invertColors) {
    if (colorClass === 'positive') colorClass = 'negative';
    else if (colorClass === 'negative') colorClass = 'positive';
  }

  let changeText;
  if (changeData.isPointChange) {
    const sign = changeData.change >= 0 ? '+' : '';
    changeText = `${sign}${changeData.change.toFixed(2)} pts YoY`;
  } else {
    const sign = changeData.pctChange >= 0 ? '+' : '';
    changeText = `${sign}${changeData.pctChange.toFixed(1)}% YoY`;
  }

  let html = `<div class="change-indicator">`;
  html += `<span class="arrow ${colorClass}">${trend.arrow}</span>`;
  html += `<span class="yoy ${colorClass}">${changeText}</span>`;

  if (momentumData) {
    const momChange = momentumData.pctChange !== null ? momentumData.pctChange : momentumData.change;
    const momTrend = getTrendArrow(momChange);
    let momColorClass = momTrend.class;
    if (invertColors) {
      if (momColorClass === 'positive') momColorClass = 'negative';
      else if (momColorClass === 'negative') momColorClass = 'positive';
    }

    let momText;
    if (momentumData.isPointChange) {
      const sign = momentumData.change >= 0 ? '+' : '';
      momText = `(${sign}${momentumData.change.toFixed(2)} pts 30d)`;
    } else {
      const sign = momentumData.pctChange >= 0 ? '+' : '';
      momText = `(${sign}${momentumData.pctChange.toFixed(1)}% 30d)`;
    }
    html += `<span class="momentum ${momColorClass}">${momText}</span>`;
  }

  html += `</div>`;
  return html;
}

function createChart(canvasId, labels, values, color = '#3498db', options = {}) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (charts[canvasId]) charts[canvasId].destroy();

  charts[canvasId] = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        borderColor: color,
        backgroundColor: color + '20',
        borderWidth: 2,
        fill: true,
        pointRadius: 2,
        pointHoverRadius: 5,
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: 'index',
          intersect: false,
          displayColors: false,
          callbacks: {
            label: function(context) {
              const prefix = options.prefix || '';
              const suffix = options.suffix || '';
              return prefix + context.parsed.y.toLocaleString(undefined, {
                minimumFractionDigits: options.decimals || 2,
                maximumFractionDigits: options.decimals || 2
              }) + suffix;
            }
          }
        }
      },
      scales: {
        x: {
          display: true,
          ticks: { maxRotation: 45, minRotation: 45, font: { size: 9 }, color: '#7f8c8d', maxTicksLimit: 5 },
          grid: { display: false }
        },
        y: {
          display: true,
          ticks: { font: { size: 9 }, color: '#7f8c8d' },
          grid: { color: '#ecf0f1' }
        }
      }
    }
  });
}

async function loadDashboard() {
  try {
    const response = await fetch("/data/dashboard.json");
    const data = await response.json();

    document.getElementById("last-update").textContent = new Date(data.updated).toLocaleString();

    // GDP
    if(data.gdp && Array.isArray(data.gdp) && data.gdp.length > 0) {
      const latest = data.gdp[data.gdp.length - 1];
      const gdpChange = calcChange(data.gdp);
      document.getElementById("gdp").innerHTML = `<div class="value">$${Number(latest.value).toLocaleString()}B</div><div class="period">${formatDate(latest.date)}</div>${formatChangeIndicator(gdpChange)}`;
      createChart('chart-gdp', data.gdp.map(d => formatDate(d.date)), data.gdp.map(d => d.value), '#2ecc71', { prefix: '$', suffix: 'B', decimals: 0 });
    }

    // Consumer Confidence
    if(data.consumer_confidence && data.consumer_confidence.length > 0) {
      const cc = data.consumer_confidence[data.consumer_confidence.length - 1];
      const ccChange = calcChange(data.consumer_confidence);
      document.getElementById("consumer-confidence").innerHTML = `<div class="value">${Number(cc.value).toFixed(1)}</div><div class="period">${formatDate(cc.date)}</div>${formatChangeIndicator(ccChange)}`;
      createChart('chart-cc', data.consumer_confidence.map(d => formatDate(d.date)), data.consumer_confidence.map(d => d.value), '#3498db', { decimals: 1 });
    }

    // S&P 500
    if(data.markets) {
      const sp = data.markets.find(m => m.symbol === "SPY");
      if (sp) {
        const currentClose = sp.current_close || sp.close;
        const currentDate = sp.current_date || sp.date;
        // Convert history to the format expected by calcChange
        const spData = sp.history ? sp.history.map(h => ({value: h.close, date: h.date})) : [];
        const spChange = calcChange(spData);
        document.getElementById("sp500").innerHTML = `<div class="value positive">${Number(currentClose).toLocaleString(undefined, {minimumFractionDigits: 2})}</div><div class="period">${formatDate(currentDate)}</div>${formatChangeIndicator(spChange)}`;
        if (sp.history && sp.history.length > 0) {
          createChart('chart-spy', sp.history.map(d => formatShortDate(d.date)), sp.history.map(d => d.close), '#27ae60', { decimals: 2 });
        }
      }
    }

    // CPI
    if(data.cpi && Array.isArray(data.cpi) && data.cpi.length > 0) {
      const latestCpi = data.cpi[data.cpi.length - 1];
      const cpiChange = calcChange(data.cpi);
      document.getElementById("cpi").innerHTML = `<div class="value">${Number(latestCpi.value).toFixed(1)}</div><div class="period">${formatDate(latestCpi.date)}</div>${formatChangeIndicator(cpiChange)}`;
      createChart('chart-cpi', data.cpi.map(d => formatDate(d.date)), data.cpi.map(d => d.value), '#9b59b6', { decimals: 1 });
    }

    // Fed Rate (daily - show YoY + 30-day momentum)
    if(data.fed_funds_rate && Array.isArray(data.fed_funds_rate) && data.fed_funds_rate.length > 0) {
      const latestFed = data.fed_funds_rate[data.fed_funds_rate.length - 1];
      const fedChange = calcChange(data.fed_funds_rate, true);  // isPercent=true for point change
      const fedMomentum = calc30DayMomentum(data.fed_funds_rate, true);
      document.getElementById("fed-rate").innerHTML = `<div class="value neutral">${Number(latestFed.value).toFixed(2)}%</div><div class="period">${formatShortDate(latestFed.date)}</div>${formatChangeIndicator(fedChange, fedMomentum)}`;
      createChart('chart-fed', data.fed_funds_rate.map(d => formatShortDate(d.date)), data.fed_funds_rate.map(d => d.value), '#e74c3c', { suffix: '%', decimals: 2 });
    }

    // Unemployment (invert colors - up is bad)
    if(data.unemployment && Array.isArray(data.unemployment) && data.unemployment.length > 0) {
      const latestUnemp = data.unemployment[data.unemployment.length - 1];
      const unempChange = calcChange(data.unemployment, true);  // isPercent=true for point change
      document.getElementById("unemployment").innerHTML = `<div class="value">${Number(latestUnemp.value).toFixed(1)}%</div><div class="period">${formatDate(latestUnemp.date)}</div>${formatChangeIndicator(unempChange, null, true)}`;
      createChart('chart-unemp', data.unemployment.map(d => formatDate(d.date)), data.unemployment.map(d => d.value), '#f39c12', { suffix: '%', decimals: 1 });
    }

    // Employment
    if(data.employment && Array.isArray(data.employment) && data.employment.length > 0) {
      const latestEmp = data.employment[data.employment.length - 1];
      const empChange = calcChange(data.employment);
      document.getElementById("employment").innerHTML = `<div class="value">${Number(latestEmp.value).toLocaleString()}</div><div class="period">${formatDate(latestEmp.date)}</div>${formatChangeIndicator(empChange)}`;
      createChart('chart-emp', data.employment.map(d => formatDate(d.date)), data.employment.map(d => d.value), '#1abc9c', { suffix: 'K', decimals: 0 });
    }

    // Wages
    if(data.wages && Array.isArray(data.wages) && data.wages.length > 0) {
      const latestWages = data.wages[data.wages.length - 1];
      const wagesChange = calcChange(data.wages);
      document.getElementById("wages").innerHTML = `<div class="value">$${Number(latestWages.value).toFixed(2)}</div><div class="period">${formatDate(latestWages.date)}</div>${formatChangeIndicator(wagesChange)}`;
      createChart('chart-wages', data.wages.map(d => formatDate(d.date)), data.wages.map(d => d.value), '#16a085', { prefix: '$', decimals: 2 });
    }

    // Housing Starts
    if(data.housing_starts && Array.isArray(data.housing_starts) && data.housing_starts.length > 0) {
      const latestHousing = data.housing_starts[data.housing_starts.length - 1];
      const housingChange = calcChange(data.housing_starts);
      document.getElementById("housing").innerHTML = `<div class="value">${Number(latestHousing.value).toLocaleString()}</div><div class="period">${formatDate(latestHousing.date)}</div>${formatChangeIndicator(housingChange)}`;
      createChart('chart-housing', data.housing_starts.map(d => formatDate(d.date)), data.housing_starts.map(d => d.value), '#8e44ad', { suffix: 'K', decimals: 0 });
    }

    // 10-Year Treasury (daily - show YoY + 30-day momentum)
    if(data.treasury_10y && Array.isArray(data.treasury_10y) && data.treasury_10y.length > 0) {
      const latestTreasury = data.treasury_10y[data.treasury_10y.length - 1];
      const treasuryChange = calcChange(data.treasury_10y, true);  // isPercent=true for point change
      const treasuryMomentum = calc30DayMomentum(data.treasury_10y, true);
      document.getElementById("treasury").innerHTML = `<div class="value neutral">${Number(latestTreasury.value).toFixed(2)}%</div><div class="period">${formatShortDate(latestTreasury.date)}</div>${formatChangeIndicator(treasuryChange, treasuryMomentum)}`;
      createChart('chart-treasury', data.treasury_10y.map(d => formatShortDate(d.date)), data.treasury_10y.map(d => d.value), '#c0392b', { suffix: '%', decimals: 2 });
    }

    // USD/CAD (daily - show YoY + 30-day momentum)
    if(data.usd_cad && Array.isArray(data.usd_cad) && data.usd_cad.length > 0) {
      const latest = data.usd_cad[data.usd_cad.length - 1];
      const cadChange = calcChange(data.usd_cad);
      const cadMomentum = calc30DayMomentum(data.usd_cad);
      document.getElementById("usd-cad").innerHTML = `<div class="value">${Number(latest.value).toFixed(4)}</div><div class="period">${formatShortDate(latest.date)} (CAD per USD)</div>${formatChangeIndicator(cadChange, cadMomentum)}`;
      createChart('chart-cad', data.usd_cad.map(d => formatShortDate(d.date)), data.usd_cad.map(d => d.value), '#e74c3c', { decimals: 4 });
    }

    // USD/EUR (daily - show YoY + 30-day momentum)
    if(data.usd_eur && Array.isArray(data.usd_eur) && data.usd_eur.length > 0) {
      const latest = data.usd_eur[data.usd_eur.length - 1];
      const eurChange = calcChange(data.usd_eur);
      const eurMomentum = calc30DayMomentum(data.usd_eur);
      document.getElementById("usd-eur").innerHTML = `<div class="value">${Number(latest.value).toFixed(4)}</div><div class="period">${formatShortDate(latest.date)} (USD per EUR)</div>${formatChangeIndicator(eurChange, eurMomentum)}`;
      createChart('chart-eur', data.usd_eur.map(d => formatShortDate(d.date)), data.usd_eur.map(d => d.value), '#3498db', { decimals: 4 });
    }

    // USD/JPY (daily - show YoY + 30-day momentum)
    if(data.usd_jpy && Array.isArray(data.usd_jpy) && data.usd_jpy.length > 0) {
      const latest = data.usd_jpy[data.usd_jpy.length - 1];
      const jpyChange = calcChange(data.usd_jpy);
      const jpyMomentum = calc30DayMomentum(data.usd_jpy);
      document.getElementById("usd-jpy").innerHTML = `<div class="value">${Number(latest.value).toFixed(2)}</div><div class="period">${formatShortDate(latest.date)} (JPY per USD)</div>${formatChangeIndicator(jpyChange, jpyMomentum)}`;
      createChart('chart-jpy', data.usd_jpy.map(d => formatShortDate(d.date)), data.usd_jpy.map(d => d.value), '#9b59b6', { decimals: 2 });
    }

    // USD/MXN (daily - show YoY + 30-day momentum)
    if(data.usd_mxn && Array.isArray(data.usd_mxn) && data.usd_mxn.length > 0) {
      const latest = data.usd_mxn[data.usd_mxn.length - 1];
      const mxnChange = calcChange(data.usd_mxn);
      const mxnMomentum = calc30DayMomentum(data.usd_mxn);
      document.getElementById("usd-mxn").innerHTML = `<div class="value">${Number(latest.value).toFixed(2)}</div><div class="period">${formatShortDate(latest.date)} (MXN per USD)</div>${formatChangeIndicator(mxnChange, mxnMomentum)}`;
      createChart('chart-mxn', data.usd_mxn.map(d => formatShortDate(d.date)), data.usd_mxn.map(d => d.value), '#27ae60', { decimals: 2 });
    }

  } catch (error) {
    console.error("Failed to load dashboard:", error);
    document.getElementById("last-update").textContent = "Error loading data";
  }
}

loadDashboard();
setInterval(loadDashboard, 300000);
</script>
