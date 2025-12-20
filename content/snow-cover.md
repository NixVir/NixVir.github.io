---
title: "Snow Cover"
description: "Real-time North American snow coverage tracking for the United States and Canada, including major ski markets. Updated daily with year-over-year comparisons and temperature anomaly data."
featured_image: "images/mtnsky.jpg"
menu:
  main:
    weight: 3
---

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>

<style>
.snow-dashboard { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
.dashboard-updated { text-align: center; margin-bottom: 20px; color: #666; }
.country-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 25px; }
@media (max-width: 992px) { .country-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .country-grid { grid-template-columns: 1fr; } }
.country-card { background: #f9f9f9; border-radius: 12px; padding: 20px; border: 1px solid #ddd; }
.country-card.na { border-top: 4px solid #10b981; }
.country-card.na .country-percentage { color: #10b981; }
.country-card.usa { border-top: 4px solid #3b82f6; }
.country-card.canada { border-top: 4px solid #8b5cf6; }
.country-card.usa-ski { border-top: 4px solid #f97316; }
.country-card.canada-ski { border-top: 4px solid #14b8a6; }
.country-header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.country-flag { font-size: 1.8em; }
.country-name { font-size: 1.2em; font-weight: 600; color: #1e293b; }
.country-percentage { font-size: 2.5em; font-weight: 700; margin-bottom: 5px; }
.country-card.usa .country-percentage { color: #3b82f6; }
.country-card.canada .country-percentage { color: #8b5cf6; }
.country-card.usa-ski .country-percentage { color: #f97316; }
.country-card.canada-ski .country-percentage { color: #14b8a6; }
.country-change { font-size: 0.85em; margin-bottom: 12px; }
.change-up { color: #22c55e; }
.change-down { color: #ef4444; }
.change-stable { color: #64748b; }
.country-chart { height: 100px; margin-top: 10px; }
.country-stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-top: 12px; padding-top: 12px; border-top: 1px solid #e2e8f0; }
.stat-item { text-align: center; }
.stat-value { font-size: 1.1em; font-weight: 600; color: #1e293b; }
.stat-label { font-size: 0.7em; color: #64748b; text-transform: uppercase; }
.metro-section { background: #f9f9f9; border-radius: 12px; padding: 20px; border: 1px solid #ddd; margin-bottom: 25px; overflow-x: auto; }
.metro-table { table-layout: auto; min-width: 700px; }
.metro-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px; }
.metro-header h2 { font-size: 1.2em; color: #1e293b; margin: 0; }
.metro-controls { display: flex; align-items: center; gap: 15px; flex-wrap: wrap; }
.view-selector { display: flex; align-items: center; gap: 6px; }
.view-selector label { font-size: 0.8em; color: #64748b; font-weight: 500; }
.view-selector select { padding: 6px 10px; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.8em; background: white; cursor: pointer; color: #1e293b; }
.view-selector select:hover { border-color: #cbd5e1; }
.view-selector select:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2); }
.metro-filters { display: flex; gap: 8px; }
.filter-btn { padding: 6px 14px; border: 1px solid #e2e8f0; background: white; border-radius: 16px; cursor: pointer; font-size: 0.8em; transition: all 0.2s; }
.filter-btn:hover { background: #f1f5f9; }
.filter-btn.active { background: #3b82f6; color: white; border-color: #3b82f6; }
.metro-table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
.metro-table th { text-align: left; padding: 10px 12px; background: #f8fafc; font-size: 0.75em; text-transform: uppercase; color: #64748b; border-bottom: 2px solid #e2e8f0; }
.metro-table th.sortable { cursor: pointer; }
.metro-table th.sortable:hover { background: #f1f5f9; }
.metro-table td { padding: 10px 12px; border-bottom: 1px solid #e2e8f0; }
.metro-table tr:hover { background: #f8fafc; }
.city-info { display: flex; align-items: center; gap: 8px; min-width: 140px; }
.city-flag { font-size: 1.1em; flex-shrink: 0; }
.city-details { display: flex; flex-direction: column; }
.city-name { font-weight: 500; white-space: nowrap; }
.city-region { font-size: 0.75em; color: #64748b; white-space: nowrap; }
.snow-cover-cell { font-weight: 600; }
.cover-high { color: #3b82f6; }
.cover-medium { color: #64748b; }
.cover-low { color: #94a3b8; }
.trend-cell { font-size: 1.1em; }
.trend-up { color: #3b82f6; }
.trend-down { color: #f97316; }
.trend-stable { color: #64748b; }
.sparkline-cell { width: 80px; min-width: 80px; max-width: 80px; }
.sparkline-container { height: 30px; width: 80px; max-width: 80px; overflow: hidden; position: relative; }
@media (max-width: 600px) { .sparkline-cell { display: none; } }
.historical-section { background: #f9f9f9; border-radius: 12px; padding: 20px; border: 1px solid #ddd; }
.historical-section h2 { font-size: 1.2em; color: #1e293b; margin-bottom: 15px; }
.historical-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
@media (max-width: 768px) { .historical-grid { grid-template-columns: 1fr; } }
.historical-card { background: white; border-radius: 8px; padding: 15px; border: 1px solid #e2e8f0; }
.historical-card.usa { border-top: 3px solid #3b82f6; }
.historical-card.canada { border-top: 3px solid #8b5cf6; }
.historical-card h3 { font-size: 1em; color: #1e293b; margin: 0 0 10px 0; display: flex; align-items: center; gap: 8px; }
.historical-card h3 .flag { font-size: 1.2em; }
.historical-chart { height: 180px; }
.data-attribution { text-align: center; margin-top: 20px; padding: 12px; font-size: 0.8em; color: #64748b; }
.data-attribution a { color: #3b82f6; text-decoration: none; }
.data-attribution a:hover { text-decoration: underline; }
.yoy-comparison { font-size: 0.85em; margin-top: 4px; }
.yoy-up { color: #3b82f6; }
.yoy-down { color: #f97316; }
.yoy-neutral { color: #64748b; }
.yoy-label { color: #94a3b8; font-size: 0.9em; }
.metro-yoy { font-size: 0.8em; white-space: nowrap; }
.unit-toggle { display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 15px; }
.unit-toggle-label { font-size: 0.85em; color: #64748b; }
.unit-toggle-switch { display: flex; background: #e2e8f0; border-radius: 20px; padding: 3px; }
.unit-toggle-btn { padding: 6px 16px; border: none; background: transparent; border-radius: 17px; cursor: pointer; font-size: 0.85em; font-weight: 500; color: #64748b; transition: all 0.2s; }
.unit-toggle-btn.active { background: #3b82f6; color: white; }
.unit-toggle-btn:hover:not(.active) { background: #cbd5e1; }
.info-icon { display: inline-flex; align-items: center; justify-content: center; width: 14px; height: 14px; border-radius: 50%; background: #e2e8f0; color: #64748b; font-size: 10px; font-weight: 600; font-style: italic; font-family: Georgia, serif; cursor: help; margin-left: 4px; position: relative; vertical-align: middle; }
.info-icon:hover { background: #3b82f6; color: white; }
.info-tooltip { position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%); background: #1e293b; color: white; padding: 8px 12px; border-radius: 6px; font-size: 12px; font-weight: normal; font-style: normal; white-space: nowrap; z-index: 100; opacity: 0; visibility: hidden; transition: opacity 0.2s, visibility 0.2s; pointer-events: none; margin-bottom: 6px; max-width: 250px; white-space: normal; text-align: left; line-height: 1.4; }
.info-tooltip::after { content: ''; position: absolute; top: 100%; left: 50%; transform: translateX(-50%); border: 6px solid transparent; border-top-color: #1e293b; }
.info-icon:hover .info-tooltip { opacity: 1; visibility: visible; }
.stat-label .info-icon { width: 12px; height: 12px; font-size: 9px; }
.metro-table th .info-icon { margin-left: 3px; }
.temp-anomaly { display: flex; align-items: center; gap: 4px; margin-top: 8px; padding-top: 8px; border-top: 1px dashed #e2e8f0; font-size: 0.85em; }
.temp-anomaly-label { color: #64748b; }
.temp-anomaly-value { font-weight: 600; }
.temp-anomaly-value.warm { color: #ef4444; }
.temp-anomaly-value.cold { color: #3b82f6; }
.temp-anomaly-value.normal { color: #64748b; }
.temp-current { color: #1e293b; font-weight: 500; }
.metro-temp { font-size: 0.85em; white-space: nowrap; }
.metro-temp .temp-warm { color: #ef4444; }
.metro-temp .temp-cold { color: #3b82f6; }
.metro-temp .temp-normal { color: #64748b; }
</style>

<div class="snow-dashboard">
<div class="dashboard-updated">Last updated: <span id="last-update">Loading...</span></div>

<div class="unit-toggle">
<span class="unit-toggle-label">Units:</span>
<div class="unit-toggle-switch">
<button class="unit-toggle-btn active" data-unit="imperial">Inches / Sq Mi</button>
<button class="unit-toggle-btn" data-unit="metric">Centimeters / Sq Km</button>
</div>
</div>

<div class="country-grid">
<div class="country-card na">
<div class="country-header">
<span class="country-flag">&#127758;</span>
<span class="country-name">N. America</span>
</div>
<div class="country-percentage" id="na-percentage">--%</div>
<div class="country-change" id="na-change"><span class="change-stable">Loading...</span></div>
<div class="yoy-comparison" id="na-yoy"></div>
<div class="country-chart"><canvas id="na-chart"></canvas></div>
<div class="country-stats">
<div class="stat-item"><div class="stat-value" id="na-area">--</div><div class="stat-label" id="na-area-label">Sq Miles<span class="info-icon">i<span class="info-tooltip">Total land area currently covered by snow in North America (US + Canada).</span></span></div></div>
<div class="stat-item"><div class="stat-value" id="na-avg-depth">--</div><div class="stat-label" id="na-depth-label">Avg Depth<span class="info-icon">i<span class="info-tooltip">Weighted average snow depth across US and Canada.</span></span></div></div>
</div>
<div class="temp-anomaly" id="na-temp"></div>
</div>

<div class="country-card usa">
<div class="country-header">
<span class="country-flag">&#127482;&#127480;</span>
<span class="country-name">United States</span>
</div>
<div class="country-percentage" id="usa-percentage">--%</div>
<div class="country-change" id="usa-change"><span class="change-stable">Loading...</span></div>
<div class="yoy-comparison" id="usa-yoy"></div>
<div class="country-chart"><canvas id="usa-chart"></canvas></div>
<div class="country-stats">
<div class="stat-item"><div class="stat-value" id="usa-area">--</div><div class="stat-label" id="usa-area-label">Sq Miles<span class="info-icon">i<span class="info-tooltip">Total land area currently covered by snow in the United States.</span></span></div></div>
<div class="stat-item"><div class="stat-value" id="usa-avg-depth">--</div><div class="stat-label" id="usa-depth-label">Avg Depth<span class="info-icon">i<span class="info-tooltip">Average snow depth across all snow-covered areas. Source: NOAA NOHRSC.</span></span></div></div>
</div>
<div class="temp-anomaly" id="usa-temp"></div>
</div>

<div class="country-card canada">
<div class="country-header">
<span class="country-flag">&#127464;&#127462;</span>
<span class="country-name">Canada</span>
</div>
<div class="country-percentage" id="canada-percentage">--%</div>
<div class="country-change" id="canada-change"><span class="change-stable">Loading...</span></div>
<div class="yoy-comparison" id="canada-yoy"></div>
<div class="country-chart"><canvas id="canada-chart"></canvas></div>
<div class="country-stats">
<div class="stat-item"><div class="stat-value" id="canada-area">--</div><div class="stat-label" id="canada-area-label">Sq Km<span class="info-icon">i<span class="info-tooltip">Total land area currently covered by snow in Canada.</span></span></div></div>
<div class="stat-item"><div class="stat-value" id="canada-avg-depth">--</div><div class="stat-label" id="canada-depth-label">Avg Depth<span class="info-icon">i<span class="info-tooltip">Estimated average snow depth. Derived from coverage percentage (no direct source available).</span></span></div></div>
</div>
<div class="temp-anomaly" id="canada-temp"></div>
</div>

<div class="country-card usa-ski">
<div class="country-header">
<span class="country-flag">&#9975;</span>
<span class="country-name">US Ski Markets<span class="info-icon">i<span class="info-tooltip"><strong>8 Major US Ski Markets:</strong><br>Denver, Salt Lake City, Seattle, Portland, Boston, New York City, Chicago, Minneapolis</span></span></span>
</div>
<div class="country-percentage" id="usa-ski-percentage">--%</div>
<div class="country-change" id="usa-ski-change"><span class="change-stable">Loading...</span></div>
<div class="yoy-comparison" id="usa-ski-yoy"></div>
<div class="country-chart"><canvas id="usa-ski-chart"></canvas></div>
<div class="country-stats">
<div class="stat-item"><div class="stat-value" id="usa-ski-metros">--</div><div class="stat-label">Metro Areas<span class="info-icon">i<span class="info-tooltip">Number of major metropolitan areas included in ski market calculation.</span></span></div></div>
<div class="stat-item"><div class="stat-value" id="usa-ski-avg-cover">--</div><div class="stat-label">Avg Cover<span class="info-icon">i<span class="info-tooltip">Average snow cover percentage across all US ski market metros.</span></span></div></div>
</div>
<div class="temp-anomaly" id="usa-ski-temp"></div>
</div>

<div class="country-card canada-ski">
<div class="country-header">
<span class="country-flag">&#9975;</span>
<span class="country-name">Canada Ski Markets<span class="info-icon">i<span class="info-tooltip"><strong>6 Major Canada Ski Markets:</strong><br>Vancouver, Calgary, Edmonton, Toronto, Montreal, Quebec City</span></span></span>
</div>
<div class="country-percentage" id="canada-ski-percentage">--%</div>
<div class="country-change" id="canada-ski-change"><span class="change-stable">Loading...</span></div>
<div class="yoy-comparison" id="canada-ski-yoy"></div>
<div class="country-chart"><canvas id="canada-ski-chart"></canvas></div>
<div class="country-stats">
<div class="stat-item"><div class="stat-value" id="canada-ski-metros">--</div><div class="stat-label">Metro Areas<span class="info-icon">i<span class="info-tooltip">Number of major metropolitan areas included in ski market calculation.</span></span></div></div>
<div class="stat-item"><div class="stat-value" id="canada-ski-avg-cover">--</div><div class="stat-label">Avg Cover<span class="info-icon">i<span class="info-tooltip">Average snow cover percentage across all Canada ski market metros.</span></span></div></div>
</div>
<div class="temp-anomaly" id="canada-ski-temp"></div>
</div>
</div>

<section class="metro-section">
<div class="metro-header">
<h2 id="metro-section-title">&#127963; Metro Area Snow Cover</h2>
<div class="metro-controls">
<div class="view-selector">
<label for="view-mode">View:</label>
<select id="view-mode">
<option value="metros">Metro Areas</option>
<option value="states">States/Provinces</option>
</select>
</div>
<div class="metro-filters">
<button class="filter-btn active" data-filter="all">All</button>
<button class="filter-btn" data-filter="usa">U.S.</button>
<button class="filter-btn" data-filter="canada">Canada</button>
<button class="filter-btn" data-filter="ski">&#9975; Ski Markets</button>
</div>
</div>
</div>
<table class="metro-table">
<thead id="metro-table-head">
<tr>
<th class="sortable" data-sort="city">City</th>
<th class="sortable" data-sort="cover">Snow Cover<span class="info-icon">i<span class="info-tooltip">Percentage of the metro area currently covered by snow.</span></span></th>
<th class="sortable" data-sort="yoy">vs Last Year<span class="info-icon">i<span class="info-tooltip">Percent change compared to the average snow cover during this same period last year.</span></span></th>
<th class="sortable" data-sort="depth">Depth<span class="info-icon">i<span class="info-tooltip">Snow depth at a representative weather station in the metro area (point observation, not area average).</span></span></th>
<th class="sortable" data-sort="temp">Temp<span class="info-icon">i<span class="info-tooltip">Current temperature and departure from normal (30-day average for this time of year). Source: Open-Meteo.</span></span></th>
<th>Trend<span class="info-icon">i<span class="info-tooltip">Direction of snow cover change over the past week: increasing, decreasing, or stable.</span></span></th>
<th class="sparkline-cell">7-Day<span class="info-icon">i<span class="info-tooltip">Snow cover percentage for the past 7 days. Solid line = this year, dashed line = last year.</span></span></th>
</tr>
</thead>
<tbody id="metro-table-body">
<tr><td colspan="7" style="text-align:center; padding: 20px; color: #64748b;">Loading metro data...</td></tr>
</tbody>
</table>
</section>

<section class="historical-section">
<h2>&#128200; Snow Cover Trend (Past 30 Days)</h2>
<div class="historical-grid">
<div class="historical-card usa">
<h3><span class="flag">&#127482;&#127480;</span> United States</h3>
<div class="historical-chart"><canvas id="usa-historical-chart"></canvas></div>
</div>
<div class="historical-card canada">
<h3><span class="flag">&#127464;&#127462;</span> Canada</h3>
<div class="historical-chart"><canvas id="canada-historical-chart"></canvas></div>
</div>
</div>
</section>

<div class="data-attribution">
Data sources: <a href="https://www.nohrsc.noaa.gov/" target="_blank">NOAA NOHRSC</a>,
<a href="https://climate.rutgers.edu/snowcover/" target="_blank">Rutgers Global Snow Lab</a>,
<a href="https://weather.gc.ca/" target="_blank">Environment Canada</a>,
<a href="https://open-meteo.com/" target="_blank">Open-Meteo</a> (temperature)
<br>Updated daily. Snow cover represents visible snow on ground surface.
</div>
</div>

<script>
let naChart = null;
let usaChart = null;
let canadaChart = null;
let usaSkiChart = null;
let canadaSkiChart = null;
let usaHistoricalChart = null;
let canadaHistoricalChart = null;
const metroSparklines = {};
let snowData = null;
let currentFilter = 'all';
let currentSort = { field: 'cover', direction: 'desc' };
let currentUnit = 'imperial';
let currentViewMode = 'metros';

// Get current and prior year for labels
const currentYear = new Date().getFullYear();
const priorYear = currentYear - 1;

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(0) + 'K';
    return num.toFixed(0);
}

function calculateYoY(currentValue, priorYearHistory) {
    if (!priorYearHistory || priorYearHistory.length === 0) return null;
    var priorValues = priorYearHistory.map(function(h) {
        return typeof h === 'object' ? h.value : h;
    }).filter(function(v) { return v !== null && v !== undefined; });
    if (priorValues.length === 0) return null;
    var priorAvg = priorValues.reduce(function(a, b) { return a + b; }, 0) / priorValues.length;
    if (priorAvg === 0) return currentValue > 0 ? 100 : 0;
    return ((currentValue - priorAvg) / priorAvg) * 100;
}

function formatYoY(yoyPercent) {
    if (yoyPercent === null) return { text: '--', class: 'yoy-neutral' };
    var sign = yoyPercent >= 0 ? '+' : '';
    var cls = yoyPercent > 5 ? 'yoy-up' : yoyPercent < -5 ? 'yoy-down' : 'yoy-neutral';
    return { text: sign + yoyPercent.toFixed(0) + '%', class: cls };
}

function formatTempAnomaly(temp, anomaly, isImperial) {
    if (temp === null || temp === undefined) return { tempText: '--', anomalyText: '', anomalyClass: 'normal' };
    var tempText = isImperial ? Math.round(temp * 9/5 + 32) + '\u00B0F' : Math.round(temp) + '\u00B0C';
    if (anomaly === null || anomaly === undefined) return { tempText: tempText, anomalyText: '', anomalyClass: 'normal' };
    var anomalyVal = isImperial ? Math.round(anomaly * 9/5) : Math.round(anomaly);
    var sign = anomalyVal >= 0 ? '+' : '';
    var anomalyText = sign + anomalyVal + '\u00B0';
    var anomalyClass = anomalyVal > 2 ? 'warm' : anomalyVal < -2 ? 'cold' : 'normal';
    return { tempText: tempText, anomalyText: anomalyText, anomalyClass: anomalyClass };
}

function renderTempAnomaly(elementId, tempData, label) {
    var el = document.getElementById(elementId);
    if (!el || !tempData) return;
    var isImperial = currentUnit === 'imperial';
    var temp = isImperial ? tempData.avg_temp_f : tempData.avg_temp_c;
    var anomaly = isImperial ? tempData.avg_anomaly_f : tempData.avg_anomaly_c;
    if (temp === null || temp === undefined) {
        el.innerHTML = '';
        return;
    }
    var formatted = formatTempAnomaly(tempData.avg_temp_c, tempData.avg_anomaly_c, isImperial);
    var icon = formatted.anomalyClass === 'warm' ? '\u2600\uFE0F' : formatted.anomalyClass === 'cold' ? '\u2744\uFE0F' : '\u2601\uFE0F';
    el.innerHTML = '<span class="temp-anomaly-label">' + icon + ' ' + label + ':</span> ' +
        '<span class="temp-current">' + formatted.tempText + '</span> ' +
        '<span class="temp-anomaly-value ' + formatted.anomalyClass + '">(' + formatted.anomalyText + ' from normal)</span>';
}

function aggregateByStateProvince(metros) {
    var stateMap = {};
    metros.forEach(function(metro) {
        var key = metro.region + '|' + metro.country;
        if (!stateMap[key]) {
            stateMap[key] = {
                region: metro.region,
                country: metro.country,
                metros: [],
                totalCover: 0,
                totalDepthInches: 0,
                totalDepthCm: 0,
                history: [],
                priorYearHistory: []
            };
        }
        stateMap[key].metros.push(metro);
        stateMap[key].totalCover += metro.cover;
        stateMap[key].totalDepthInches += (metro.depthInches || 0);
        stateMap[key].totalDepthCm += (metro.depthCm || 0);
    });
    // Calculate averages and aggregate history
    var states = Object.values(stateMap).map(function(state) {
        var count = state.metros.length;
        var avgCover = Math.round(state.totalCover / count);
        var avgDepthInches = Math.round((state.totalDepthInches / count) * 10) / 10;
        var avgDepthCm = Math.round((state.totalDepthCm / count) * 10) / 10;
        // Aggregate history by averaging across metros
        var historyLen = state.metros[0].history ? state.metros[0].history.length : 0;
        var history = [];
        var priorYearHistory = [];
        for (var i = 0; i < historyLen; i++) {
            var sum = 0, priorSum = 0, priorCount = 0;
            state.metros.forEach(function(m) {
                if (m.history && m.history[i] !== undefined) sum += m.history[i];
                if (m.priorYearHistory && m.priorYearHistory[i] !== undefined) {
                    priorSum += m.priorYearHistory[i];
                    priorCount++;
                }
            });
            history.push(Math.round(sum / count));
            if (priorCount > 0) priorYearHistory.push(Math.round(priorSum / priorCount));
        }
        // Calculate trend from history
        var trend = 'stable';
        if (history.length >= 2) {
            var recent = history[history.length - 1];
            var earlier = history[0];
            if (recent > earlier + 5) trend = 'up';
            else if (recent < earlier - 5) trend = 'down';
        }
        return {
            region: state.region,
            country: state.country,
            cover: avgCover,
            depthInches: avgDepthInches,
            depthCm: avgDepthCm,
            trend: trend,
            metroCount: count,
            history: history,
            priorYearHistory: priorYearHistory
        };
    });
    return states;
}

async function loadSnowData() {
    try {
        const response = await fetch('/data/snow-cover.json');
        if (!response.ok) throw new Error('Data not available');
        snowData = await response.json();
        renderDashboard();
    } catch (error) {
        console.error('Failed to load snow data:', error);
        document.getElementById('na-change').innerHTML = '<span class="change-stable">Unable to load data</span>';
    }
}

function renderDashboard() {
    if (!snowData) return;
    document.getElementById('last-update').textContent = snowData.updated;
    renderNACard();
    renderCountryCard('usa');
    renderCountryCard('canada');
    renderSkiMarketCard('usa');
    renderSkiMarketCard('canada');
    renderMetroTable();
    renderHistoricalChart();
}

function renderNACard() {
    const combined = snowData.combined;
    const usaData = snowData.usa;
    const canadaData = snowData.canada;
    // Display combined percentage
    document.getElementById('na-percentage').textContent = combined.cover + '%';
    // Calculate week-over-week change (average of USA and Canada changes)
    var usaChange = parseFloat(usaData.change) || 0;
    var canadaChange = parseFloat(canadaData.change) || 0;
    var avgChange = ((usaChange + canadaChange) / 2).toFixed(1);
    var changeValue = parseFloat(avgChange);
    var changeClass = 'change-stable';
    var changeIcon = '\u2192';
    if (changeValue > 0) { changeClass = 'change-up'; changeIcon = '\u2191'; avgChange = '+' + avgChange; }
    else if (changeValue < 0) { changeClass = 'change-down'; changeIcon = '\u2193'; }
    document.getElementById('na-change').innerHTML = '<span class="' + changeClass + '">' + changeIcon + ' ' + avgChange + ' pts from last week</span>';
    // Calculate YoY comparison
    var usaYoY = calculateYoY(usaData.cover, usaData.priorYearHistory);
    var canadaYoY = calculateYoY(canadaData.cover, canadaData.priorYearHistory);
    var combinedYoY = null;
    if (usaYoY !== null && canadaYoY !== null) {
        combinedYoY = (usaYoY + canadaYoY) / 2;
    } else if (usaYoY !== null) {
        combinedYoY = usaYoY;
    } else if (canadaYoY !== null) {
        combinedYoY = canadaYoY;
    }
    var yoyFormatted = formatYoY(combinedYoY);
    var yoyEl = document.getElementById('na-yoy');
    if (combinedYoY !== null) {
        yoyEl.innerHTML = '<span class="yoy-label">vs last year:</span> <span class="' + yoyFormatted.class + '">' + yoyFormatted.text + '</span>';
    }
    // Calculate combined area (USA + Canada)
    var areaEl = document.getElementById('na-area');
    var depthEl = document.getElementById('na-avg-depth');
    var areaLabelEl = document.getElementById('na-area-label');
    var depthLabelEl = document.getElementById('na-depth-label');
    if (currentUnit === 'imperial') {
        var usaAreaSqMi = usaData.areaSqMi || 0;
        var canadaAreaSqMi = canadaData.areaSqKm ? canadaData.areaSqKm * 0.386102 : 0;
        var totalAreaSqMi = usaAreaSqMi + canadaAreaSqMi;
        areaEl.textContent = formatNumber(totalAreaSqMi);
        // Weighted average depth
        var usaDepth = usaData.avgDepthInches || 0;
        var canadaDepth = canadaData.avgDepthCm ? canadaData.avgDepthCm / 2.54 : 0;
        var avgDepth = usaAreaSqMi + canadaAreaSqMi > 0 ? ((usaDepth * usaAreaSqMi + canadaDepth * canadaAreaSqMi) / (usaAreaSqMi + canadaAreaSqMi)).toFixed(1) : '--';
        depthEl.textContent = avgDepth + '"';
        areaLabelEl.innerHTML = 'Sq Miles<span class="info-icon">i<span class="info-tooltip">Total land area currently covered by snow in North America (US + Canada).</span></span>';
        depthLabelEl.innerHTML = 'Avg Depth (in)<span class="info-icon">i<span class="info-tooltip">Weighted average snow depth across US and Canada.</span></span>';
    } else {
        var usaAreaSqKm = usaData.areaSqMi ? usaData.areaSqMi * 2.58999 : 0;
        var canadaAreaSqKm = canadaData.areaSqKm || 0;
        var totalAreaSqKm = usaAreaSqKm + canadaAreaSqKm;
        areaEl.textContent = formatNumber(totalAreaSqKm);
        // Weighted average depth
        var usaDepthCm = usaData.avgDepthInches ? usaData.avgDepthInches * 2.54 : 0;
        var canadaDepthCm = canadaData.avgDepthCm || 0;
        var avgDepthCm = usaAreaSqKm + canadaAreaSqKm > 0 ? ((usaDepthCm * usaAreaSqKm + canadaDepthCm * canadaAreaSqKm) / (usaAreaSqKm + canadaAreaSqKm)).toFixed(1) : '--';
        depthEl.textContent = avgDepthCm + ' cm';
        areaLabelEl.innerHTML = 'Sq Km<span class="info-icon">i<span class="info-tooltip">Total land area currently covered by snow in North America (US + Canada).</span></span>';
        depthLabelEl.innerHTML = 'Avg Depth (cm)<span class="info-icon">i<span class="info-tooltip">Weighted average snow depth across US and Canada.</span></span>';
    }
    // Render combined sparkline chart
    const ctx = document.getElementById('na-chart').getContext('2d');
    if (naChart) naChart.destroy();
    // Create combined history by averaging USA and Canada
    var combinedHistory = [];
    var combinedPriorHistory = [];
    var maxLen = Math.max(usaData.history.length, canadaData.history.length);
    for (var i = 0; i < maxLen; i++) {
        var usaVal = usaData.history[i] ? usaData.history[i].value : null;
        var canadaVal = canadaData.history[i] ? canadaData.history[i].value : null;
        if (usaVal !== null && canadaVal !== null) {
            combinedHistory.push({ date: usaData.history[i].date, value: Math.round((usaVal + canadaVal) / 2) });
        } else if (usaVal !== null) {
            combinedHistory.push({ date: usaData.history[i].date, value: usaVal });
        } else if (canadaVal !== null) {
            combinedHistory.push({ date: canadaData.history[i].date, value: canadaVal });
        }
        // Prior year
        var usaPrior = usaData.priorYearHistory && usaData.priorYearHistory[i] ? usaData.priorYearHistory[i].value : null;
        var canadaPrior = canadaData.priorYearHistory && canadaData.priorYearHistory[i] ? canadaData.priorYearHistory[i].value : null;
        if (usaPrior !== null && canadaPrior !== null) {
            combinedPriorHistory.push({ value: Math.round((usaPrior + canadaPrior) / 2) });
        } else if (usaPrior !== null) {
            combinedPriorHistory.push({ value: usaPrior });
        } else if (canadaPrior !== null) {
            combinedPriorHistory.push({ value: canadaPrior });
        }
    }
    const color = '#10b981';
    const bgColor = 'rgba(16, 185, 129, 0.1)';
    const priorColor = '#9ca3af';
    const datasets = [{
        label: 'This Year',
        data: combinedHistory.map(function(h) { return h.value; }),
        borderColor: color,
        backgroundColor: bgColor,
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        borderWidth: 2
    }];
    if (combinedPriorHistory.length > 0) {
        datasets.push({
            label: 'Last Year',
            data: combinedPriorHistory.map(function(h) { return h.value; }),
            borderColor: priorColor,
            backgroundColor: 'transparent',
            fill: false,
            tension: 0.4,
            pointRadius: 0,
            borderWidth: 1.5,
            borderDash: [4, 2]
        });
    }
    naChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: combinedHistory.map(function(h) { return h.date.slice(5); }),
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(ctx) {
                            var label = ctx.datasetIndex === 0 ? currentYear : priorYear;
                            return label + ': ' + ctx.parsed.y + '%';
                        }
                    }
                }
            },
            scales: { x: { display: false }, y: { display: false, min: 0, max: 100 } },
            interaction: { intersect: false, mode: 'index' }
        }
    });
    // Render temperature anomaly for N. America
    renderTempAnomaly('na-temp', combined.temperature, 'Avg Temp');
}

function renderCountryCard(country) {
    const data = snowData[country];
    document.getElementById(country + '-percentage').textContent = data.cover + '%';
    const changeEl = document.getElementById(country + '-change');
    const changeValue = parseFloat(data.change) || 0;
    let changeClass = 'change-stable';
    let changeIcon = '\u2192';
    if (changeValue > 0) { changeClass = 'change-up'; changeIcon = '\u2191'; }
    else if (changeValue < 0) { changeClass = 'change-down'; changeIcon = '\u2193'; }
    changeEl.innerHTML = '<span class="' + changeClass + '">' + changeIcon + ' ' + data.change + ' from last week</span>';
    // Add YoY comparison
    var yoyEl = document.getElementById(country + '-yoy');
    var yoY = calculateYoY(data.cover, data.priorYearHistory);
    var yoyFormatted = formatYoY(yoY);
    if (yoY !== null) {
        yoyEl.innerHTML = '<span class="yoy-label">vs last year:</span> <span class="' + yoyFormatted.class + '">' + yoyFormatted.text + '</span>';
    }
    var areaEl = document.getElementById(country + '-area');
    var depthEl = document.getElementById(country + '-avg-depth');
    var areaLabelEl = document.getElementById(country + '-area-label');
    var depthLabelEl = document.getElementById(country + '-depth-label');
    if (currentUnit === 'imperial') {
        if (data.areaSqMi !== undefined) { areaEl.textContent = formatNumber(data.areaSqMi); }
        else { areaEl.textContent = data.area || '--'; }
        if (data.avgDepthInches !== undefined) { depthEl.textContent = data.avgDepthInches + '"'; }
        else { depthEl.textContent = data.avgDepth || '--'; }
        areaLabelEl.textContent = 'Sq Miles';
        depthLabelEl.textContent = 'Avg Depth (in)';
    } else {
        if (data.areaSqKm !== undefined) { areaEl.textContent = formatNumber(data.areaSqKm); }
        else { areaEl.textContent = data.area || '--'; }
        if (data.avgDepthCm !== undefined) { depthEl.textContent = data.avgDepthCm + ' cm'; }
        else { depthEl.textContent = data.avgDepth || '--'; }
        areaLabelEl.textContent = 'Sq Km';
        depthLabelEl.textContent = 'Avg Depth (cm)';
    }
    const ctx = document.getElementById(country + '-chart').getContext('2d');
    if (country === 'usa' && usaChart) usaChart.destroy();
    if (country === 'canada' && canadaChart) canadaChart.destroy();
    const color = country === 'usa' ? '#3b82f6' : '#8b5cf6';
    const bgColor = country === 'usa' ? 'rgba(59, 130, 246, 0.1)' : 'rgba(139, 92, 246, 0.1)';
    const priorColor = '#9ca3af';
    const datasets = [{
        label: 'This Year',
        data: data.history.map(function(h) { return h.value; }),
        borderColor: color,
        backgroundColor: bgColor,
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        borderWidth: 2
    }];
    if (data.priorYearHistory && data.priorYearHistory.length > 0) {
        datasets.push({
            label: 'Last Year',
            data: data.priorYearHistory.map(function(h) { return h.value; }),
            borderColor: priorColor,
            backgroundColor: 'transparent',
            fill: false,
            tension: 0.4,
            pointRadius: 0,
            borderWidth: 1.5,
            borderDash: [4, 2]
        });
    }
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.history.map(function(h) { return h.date.slice(5); }),
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(ctx) {
                            var label = ctx.datasetIndex === 0 ? currentYear : priorYear;
                            return label + ': ' + ctx.parsed.y + '%';
                        }
                    }
                }
            },
            scales: { x: { display: false }, y: { display: false, min: 0, max: 100 } },
            interaction: { intersect: false, mode: 'index' }
        }
    });
    if (country === 'usa') usaChart = chart;
    else canadaChart = chart;
    // Render temperature anomaly
    renderTempAnomaly(country + '-temp', data.temperature, 'Avg Temp');
}

function renderSkiMarketCard(country) {
    const skiData = snowData.skiMarkets && snowData.skiMarkets[country];
    if (!skiData) return;
    const prefix = country + '-ski';
    // Display percentage
    document.getElementById(prefix + '-percentage').textContent = Math.round(skiData.cover) + '%';
    // Change indicator - compare to week ago using metro history average
    var changeEl = document.getElementById(prefix + '-change');
    var skiMetros = snowData.metros.filter(function(m) { return m.country === country && m.skiMarket === true; });
    var currentAvg = skiData.cover;
    var weekAgoAvg = 0;
    var validMetros = 0;
    skiMetros.forEach(function(m) {
        if (m.history && m.history.length >= 7) {
            weekAgoAvg += m.history[0];
            validMetros++;
        }
    });
    if (validMetros > 0) {
        weekAgoAvg = weekAgoAvg / validMetros;
        var change = (currentAvg - weekAgoAvg).toFixed(1);
        var changeValue = parseFloat(change);
        var changeClass = 'change-stable';
        var changeIcon = '\u2192';
        if (changeValue > 0) { changeClass = 'change-up'; changeIcon = '\u2191'; change = '+' + change; }
        else if (changeValue < 0) { changeClass = 'change-down'; changeIcon = '\u2193'; }
        changeEl.innerHTML = '<span class="' + changeClass + '">' + changeIcon + ' ' + change + ' pts from last week</span>';
    } else {
        changeEl.innerHTML = '<span class="change-stable">--</span>';
    }
    // YoY comparison
    var yoyEl = document.getElementById(prefix + '-yoy');
    var totalYoY = 0;
    var yoyCount = 0;
    skiMetros.forEach(function(m) {
        var yoy = calculateYoY(m.cover, m.priorYearHistory);
        if (yoy !== null) {
            totalYoY += yoy;
            yoyCount++;
        }
    });
    if (yoyCount > 0) {
        var avgYoY = totalYoY / yoyCount;
        var yoyFormatted = formatYoY(avgYoY);
        yoyEl.innerHTML = '<span class="yoy-label">vs last year:</span> <span class="' + yoyFormatted.class + '">' + yoyFormatted.text + '</span>';
    }
    // Stats: metro count and average cover
    document.getElementById(prefix + '-metros').textContent = skiData.metro_count;
    document.getElementById(prefix + '-avg-cover').textContent = Math.round(skiData.cover) + '%';
    // Render sparkline chart from aggregated metro history
    const ctx = document.getElementById(prefix + '-chart').getContext('2d');
    if (country === 'usa' && usaSkiChart) usaSkiChart.destroy();
    if (country === 'canada' && canadaSkiChart) canadaSkiChart.destroy();
    // Aggregate history from ski market metros
    var historyLen = skiMetros.length > 0 && skiMetros[0].history ? skiMetros[0].history.length : 0;
    var aggregatedHistory = [];
    var aggregatedPriorHistory = [];
    for (var i = 0; i < historyLen; i++) {
        var sum = 0, priorSum = 0, priorCount = 0;
        skiMetros.forEach(function(m) {
            if (m.history && m.history[i] !== undefined) sum += m.history[i];
            if (m.priorYearHistory && m.priorYearHistory[i] !== undefined) {
                priorSum += m.priorYearHistory[i];
                priorCount++;
            }
        });
        aggregatedHistory.push(Math.round(sum / skiMetros.length));
        if (priorCount > 0) aggregatedPriorHistory.push(Math.round(priorSum / priorCount));
    }
    const color = country === 'usa' ? '#f97316' : '#14b8a6';
    const bgColor = country === 'usa' ? 'rgba(249, 115, 22, 0.1)' : 'rgba(20, 184, 166, 0.1)';
    const priorColor = '#9ca3af';
    const datasets = [{
        label: 'This Year',
        data: aggregatedHistory,
        borderColor: color,
        backgroundColor: bgColor,
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        borderWidth: 2
    }];
    if (aggregatedPriorHistory.length > 0) {
        datasets.push({
            label: 'Last Year',
            data: aggregatedPriorHistory,
            borderColor: priorColor,
            backgroundColor: 'transparent',
            fill: false,
            tension: 0.4,
            pointRadius: 0,
            borderWidth: 1.5,
            borderDash: [4, 2]
        });
    }
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: aggregatedHistory.map(function(_, i) { return i; }),
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(ctx) {
                            var label = ctx.datasetIndex === 0 ? currentYear : priorYear;
                            return label + ': ' + ctx.parsed.y + '%';
                        }
                    }
                }
            },
            scales: { x: { display: false }, y: { display: false, min: 0, max: 100 } },
            interaction: { intersect: false, mode: 'index' }
        }
    });
    if (country === 'usa') usaSkiChart = chart;
    else canadaSkiChart = chart;
    // Render temperature anomaly
    var tempData = {
        avg_temp_c: skiData.avg_temp_c,
        avg_temp_f: skiData.avg_temp_f,
        avg_anomaly_c: skiData.avg_anomaly_c,
        avg_anomaly_f: skiData.avg_anomaly_f
    };
    renderTempAnomaly(prefix + '-temp', tempData, 'Avg Temp');
}

function renderMetroTable() {
    const tbody = document.getElementById('metro-table-body');
    const thead = document.getElementById('metro-table-head');
    const title = document.getElementById('metro-section-title');
    var items;
    var isStateView = currentViewMode === 'states';
    // Update title and table header based on view mode
    if (isStateView) {
        title.innerHTML = '&#127963; State/Province Snow Cover';
        thead.innerHTML = '<tr><th class="sortable" data-sort="city">State/Province</th><th class="sortable" data-sort="cover">Avg Snow Cover<span class="info-icon">i<span class="info-tooltip">Average snow cover percentage across metro areas in this state/province.</span></span></th><th class="sortable" data-sort="yoy">vs Last Year<span class="info-icon">i<span class="info-tooltip">Average percent change compared to the same period last year.</span></span></th><th class="sortable" data-sort="depth">Avg Depth<span class="info-icon">i<span class="info-tooltip">Average snow depth across metro areas in this state/province.</span></span></th><th>Trend<span class="info-icon">i<span class="info-tooltip">Overall direction of snow cover change over the past week.</span></span></th><th class="sparkline-cell">7-Day<span class="info-icon">i<span class="info-tooltip">Average snow cover for the past 7 days. Solid line = this year, dashed line = last year.</span></span></th></tr>';
        items = aggregateByStateProvince(snowData.metros);
    } else {
        title.innerHTML = '&#127963; Metro Area Snow Cover';
        thead.innerHTML = '<tr><th class="sortable" data-sort="city">City</th><th class="sortable" data-sort="cover">Snow Cover<span class="info-icon">i<span class="info-tooltip">Percentage of the metro area currently covered by snow.</span></span></th><th class="sortable" data-sort="yoy">vs Last Year<span class="info-icon">i<span class="info-tooltip">Percent change compared to the average snow cover during this same period last year.</span></span></th><th class="sortable" data-sort="depth">Depth<span class="info-icon">i<span class="info-tooltip">Snow depth at a representative weather station in the metro area (point observation, not area average).</span></span></th><th class="sortable" data-sort="temp">Temp<span class="info-icon">i<span class="info-tooltip">Current temperature and departure from normal. Source: Open-Meteo.</span></span></th><th>Trend<span class="info-icon">i<span class="info-tooltip">Direction of snow cover change over the past week: increasing, decreasing, or stable.</span></span></th><th class="sparkline-cell">7-Day<span class="info-icon">i<span class="info-tooltip">Snow cover percentage for the past 7 days. Solid line = this year, dashed line = last year.</span></span></th></tr>';
        items = snowData.metros;
    }
    // Apply filter (country or ski markets)
    if (currentFilter === 'ski') {
        items = items.filter(function(m) { return m.skiMarket === true; });
    } else if (currentFilter !== 'all') {
        items = items.filter(function(m) { return m.country === currentFilter; });
    }
    // Pre-calculate YoY for each item for sorting
    items = items.map(function(m) {
        var yoy = calculateYoY(m.cover, m.priorYearHistory);
        return Object.assign({}, m, { yoyValue: yoy !== null ? yoy : 0 });
    });
    // Sort items
    items = items.slice().sort(function(a, b) {
        var aVal, bVal;
        if (currentSort.field === 'depth') {
            aVal = a.depthInches !== undefined ? a.depthInches : 0;
            bVal = b.depthInches !== undefined ? b.depthInches : 0;
        } else if (currentSort.field === 'city') {
            aVal = isStateView ? a.region.toLowerCase() : a.city.toLowerCase();
            bVal = isStateView ? b.region.toLowerCase() : b.city.toLowerCase();
        } else if (currentSort.field === 'yoy') {
            aVal = a.yoyValue;
            bVal = b.yoyValue;
        } else if (currentSort.field === 'temp') {
            aVal = a.temperature && a.temperature.temp_c !== null ? a.temperature.temp_c : -999;
            bVal = b.temperature && b.temperature.temp_c !== null ? b.temperature.temp_c : -999;
        } else {
            aVal = a[currentSort.field];
            bVal = b[currentSort.field];
        }
        if (currentSort.direction === 'asc') return aVal > bVal ? 1 : -1;
        else return aVal < bVal ? 1 : -1;
    });
    // Calculate global max across all sparklines (current + prior year)
    var globalMax = 0;
    items.forEach(function(item) {
        if (item.history && item.history.length > 0) {
            var histMax = Math.max.apply(null, item.history);
            if (histMax > globalMax) globalMax = histMax;
        }
        if (item.priorYearHistory && item.priorYearHistory.length > 0) {
            var priorMax = Math.max.apply(null, item.priorYearHistory);
            if (priorMax > globalMax) globalMax = priorMax;
        }
    });
    // Add 10% padding to max, but cap at 100
    globalMax = Math.min(100, Math.ceil(globalMax * 1.1));
    if (globalMax < 10) globalMax = 10; // Minimum scale for visibility
    // Render table rows
    tbody.innerHTML = items.map(function(item, idx) {
        const flag = item.country === 'usa' ? '&#127482;&#127480;' : '&#127464;&#127462;';
        const coverClass = item.cover >= 60 ? 'cover-high' : item.cover >= 30 ? 'cover-medium' : 'cover-low';
        const trendClass = item.trend === 'up' ? 'trend-up' : item.trend === 'down' ? 'trend-down' : 'trend-stable';
        const trendIcon = item.trend === 'up' ? '\u2191' : item.trend === 'down' ? '\u2193' : '\u2192';
        var depthDisplay;
        if (currentUnit === 'imperial') {
            depthDisplay = item.depthInches !== undefined ? item.depthInches + '"' : (item.depth || '--');
        } else {
            depthDisplay = item.depthCm !== undefined ? item.depthCm + ' cm' : (item.depth || '--');
        }
        var yoy = calculateYoY(item.cover, item.priorYearHistory);
        var yoyFormatted = formatYoY(yoy);
        if (isStateView) {
            var metroCountText = item.metroCount > 1 ? ' (' + item.metroCount + ' metros)' : ' (1 metro)';
            return '<tr><td><div class="city-info"><span class="city-flag">' + flag + '</span><div class="city-details"><div class="city-name">' + item.region + '</div><div class="city-region">' + metroCountText + '</div></div></div></td><td class="snow-cover-cell ' + coverClass + '">' + item.cover + '%</td><td class="metro-yoy ' + yoyFormatted.class + '">' + yoyFormatted.text + '</td><td>' + depthDisplay + '</td><td class="trend-cell ' + trendClass + '">' + trendIcon + '</td><td class="sparkline-cell"><div class="sparkline-container"><canvas id="sparkline-' + idx + '"></canvas></div></td></tr>';
        } else {
            // Format temperature for metro view
            var tempDisplay = '--';
            var tempAnomalyClass = '';
            if (item.temperature && item.temperature.temp_c !== null) {
                var isImperial = currentUnit === 'imperial';
                var formatted = formatTempAnomaly(item.temperature.temp_c, item.temperature.anomaly_c, isImperial);
                tempDisplay = '<span class="temp-current">' + formatted.tempText + '</span>';
                if (formatted.anomalyText) {
                    tempDisplay += ' <span class="temp-' + formatted.anomalyClass + '">(' + formatted.anomalyText + ')</span>';
                }
            }
            return '<tr><td><div class="city-info"><span class="city-flag">' + flag + '</span><div class="city-details"><div class="city-name">' + item.city + '</div><div class="city-region">' + item.region + '</div></div></div></td><td class="snow-cover-cell ' + coverClass + '">' + item.cover + '%</td><td class="metro-yoy ' + yoyFormatted.class + '">' + yoyFormatted.text + '</td><td>' + depthDisplay + '</td><td class="metro-temp">' + tempDisplay + '</td><td class="trend-cell ' + trendClass + '">' + trendIcon + '</td><td class="sparkline-cell"><div class="sparkline-container"><canvas id="sparkline-' + idx + '"></canvas></div></td></tr>';
        }
    }).join('');
    // Render sparklines
    items.forEach(function(item, idx) {
        const canvas = document.getElementById('sparkline-' + idx);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const color = item.country === 'usa' ? '#3b82f6' : '#8b5cf6';
        const priorColor = '#9ca3af';
        if (metroSparklines['sparkline-' + idx]) metroSparklines['sparkline-' + idx].destroy();
        var datasets = [{
            data: item.history,
            borderColor: color,
            borderWidth: 1.5,
            pointRadius: 0,
            tension: 0.3
        }];
        if (item.priorYearHistory && item.priorYearHistory.length > 0) {
            datasets.push({
                data: item.priorYearHistory,
                borderColor: priorColor,
                borderWidth: 1,
                pointRadius: 0,
                tension: 0.3,
                borderDash: [2, 2]
            });
        }
        metroSparklines['sparkline-' + idx] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: item.history.map(function(_, i) { return i; }),
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(ctx) {
                                var label = ctx.datasetIndex === 0 ? currentYear : priorYear;
                                return label + ': ' + ctx.parsed.y + '%';
                            }
                        }
                    }
                },
                scales: { x: { display: false }, y: { display: false, min: 0, max: globalMax } },
                interaction: { intersect: false, mode: 'index' }
            }
        });
    });
    // Re-attach sort handlers after updating thead
    document.querySelectorAll('.metro-table th.sortable').forEach(function(th) {
        th.onclick = function() {
            const field = th.dataset.sort;
            if (currentSort.field === field) {
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.field = field;
                currentSort.direction = 'desc';
            }
            renderMetroTable();
        };
    });
}

function renderHistoricalChart() {
    // Render USA historical chart
    const usaCtx = document.getElementById('usa-historical-chart').getContext('2d');
    if (usaHistoricalChart) usaHistoricalChart.destroy();
    const usaData = snowData.usa.history;
    const usaPrior = snowData.usa.priorYearHistory || [];
    const usaDatasets = [{
        label: String(currentYear),
        data: usaData.map(function(h) { return h.value; }),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.15)',
        fill: true,
        tension: 0.3,
        borderWidth: 2,
        pointRadius: 2,
        pointHoverRadius: 4
    }];
    if (usaPrior.length > 0) {
        usaDatasets.push({
            label: String(priorYear),
            data: usaPrior.map(function(h) { return h.value; }),
            borderColor: '#93c5fd',
            backgroundColor: 'transparent',
            fill: false,
            tension: 0.3,
            borderWidth: 1.5,
            borderDash: [4, 2],
            pointRadius: 0
        });
    }
    usaHistoricalChart = new Chart(usaCtx, {
        type: 'line',
        data: {
            labels: usaData.map(function(h) {
                const date = new Date(h.date);
                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            }),
            datasets: usaDatasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top', labels: { usePointStyle: true, padding: 10, boxWidth: 6, font: { size: 11 } } },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: { label: function(ctx) { return ctx.dataset.label + ': ' + (ctx.parsed.y !== null ? ctx.parsed.y + '%' : 'N/A'); } }
                }
            },
            scales: {
                x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 8, font: { size: 10 } } },
                y: { min: 0, max: 100, ticks: { callback: function(v) { return v + '%'; }, font: { size: 10 } } }
            },
            interaction: { intersect: false, mode: 'index' }
        }
    });
    // Render Canada historical chart
    const canadaCtx = document.getElementById('canada-historical-chart').getContext('2d');
    if (canadaHistoricalChart) canadaHistoricalChart.destroy();
    const canadaData = snowData.canada.history;
    const canadaPrior = snowData.canada.priorYearHistory || [];
    const canadaDatasets = [{
        label: String(currentYear),
        data: canadaData.map(function(h) { return h.value; }),
        borderColor: '#8b5cf6',
        backgroundColor: 'rgba(139, 92, 246, 0.15)',
        fill: true,
        tension: 0.3,
        borderWidth: 2,
        pointRadius: 2,
        pointHoverRadius: 4
    }];
    if (canadaPrior.length > 0) {
        canadaDatasets.push({
            label: String(priorYear),
            data: canadaPrior.map(function(h) { return h.value; }),
            borderColor: '#c4b5fd',
            backgroundColor: 'transparent',
            fill: false,
            tension: 0.3,
            borderWidth: 1.5,
            borderDash: [4, 2],
            pointRadius: 0
        });
    }
    canadaHistoricalChart = new Chart(canadaCtx, {
        type: 'line',
        data: {
            labels: canadaData.map(function(h) {
                const date = new Date(h.date);
                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            }),
            datasets: canadaDatasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top', labels: { usePointStyle: true, padding: 10, boxWidth: 6, font: { size: 11 } } },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: { label: function(ctx) { return ctx.dataset.label + ': ' + (ctx.parsed.y !== null ? ctx.parsed.y + '%' : 'N/A'); } }
                }
            },
            scales: {
                x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 8, font: { size: 10 } } },
                y: { min: 0, max: 100, ticks: { callback: function(v) { return v + '%'; }, font: { size: 10 } } }
            },
            interaction: { intersect: false, mode: 'index' }
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // View mode selector (metros vs states/provinces)
    document.getElementById('view-mode').addEventListener('change', function(e) {
        currentViewMode = e.target.value;
        if (snowData) {
            renderMetroTable();
        }
    });
    // Unit toggle (imperial vs metric)
    document.querySelectorAll('.unit-toggle-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.unit-toggle-btn').forEach(function(b) { b.classList.remove('active'); });
            btn.classList.add('active');
            currentUnit = btn.dataset.unit;
            if (snowData) {
                renderNACard();
                renderCountryCard('usa');
                renderCountryCard('canada');
                renderSkiMarketCard('usa');
                renderSkiMarketCard('canada');
                renderMetroTable();
            }
        });
    });
    // Country filter
    document.querySelectorAll('.filter-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.filter-btn').forEach(function(b) { b.classList.remove('active'); });
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            renderMetroTable();
        });
    });
    // Initial sort handlers (will be re-attached in renderMetroTable when thead changes)
    document.querySelectorAll('.metro-table th.sortable').forEach(function(th) {
        th.addEventListener('click', function() {
            const field = th.dataset.sort;
            if (currentSort.field === field) {
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.field = field;
                currentSort.direction = 'desc';
            }
            renderMetroTable();
        });
    });
    loadSnowData();
});
setInterval(loadSnowData, 300000);
</script>
