# Static HTML Pages Documentation

This document describes the three standalone HTML dashboards that fetch JSON data client-side.

---

## Overview

| Page | File | Lines | Purpose |
|------|------|-------|---------|
| Snow Cover | [static/snow-cover.html](../static/snow-cover.html) | ~4,637 | Interactive map, charts, market table |
| SNOTEL | [static/snotel.html](../static/snotel.html) | ~1,548 | Snowpack map with watersheds |
| Dashboard | [static/dashboard.html](../static/dashboard.html) | ~2,353 | Economic indicators |

All pages share common resources:
- `/css/shared-theme.css` - CSS custom properties, reset, navigation, popup styles
- `/js/analytics.js` - Google Analytics with DNT support
- Google Fonts (DM Sans, JetBrains Mono)

---

## Snow Cover Dashboard (`snow-cover.html`)

### Purpose
Displays current snow cover and temperature conditions across North American ski markets, comparing current values to 5-year historical averages.

### Data Sources
- `/data/snow-cover.json` - Current conditions
- `/data/snow-cover-historical.json` - 5-year seasonal averages
- `/data/temperature-history.json` - Daily temperature anomalies

### External Dependencies
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/topojson/3.0.2/topojson.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom"></script>
```

### Key Functions

| Function | Line | Purpose |
|----------|------|---------|
| `loadSnowData()` | 1882 | Fetches snow-cover.json and temperature-history.json |
| `loadGeoData()` | 1962 | Loads TopoJSON for USA/Canada map boundaries |
| `drawMap()` | 3624 | Renders D3.js map with state/province boundaries |
| `drawNationalChart()` | 2440 | Creates snow cover trend chart (Oct-Apr) |
| `drawTemperatureChart()` | 2805 | Creates temperature anomaly chart |
| `resetBothCharts()` | 2792 | Synchronizes zoom reset on both charts |
| `renderMarketTable()` | 4119 | Populates ski market table with sortable columns |
| `updateNationalOverview()` | 2227 | Updates regional summary panel |
| `getHistoricalAverage()` | 2300 | Looks up 5-year average for a given date |
| `selectRegion()` | 4378 | Filters display to specific NSAA/CSC region |
| `populateMarketList()` | 4450 | Builds market selector sidebar |

### UI Components

1. **Regional Summary Panel** - National-level statistics (NOT market averages)
2. **Interactive Map** - D3.js map with NSAA/CSC region borders and market bubbles
3. **Snow Cover Chart** - Full season (Oct 1 - Apr 30) with current vs 5-year average
4. **Temperature Chart** - Synchronized x-axis showing temperature anomalies
5. **Market Table** - Sortable table of 50 ski markets
6. **Market Selector Sidebar** - Custom market selection for filtered views

### Winter Salience Logic

Markets are colored by "winter salience" (consumer awareness of winter):

```javascript
if (tempAnomaly >= 20) {
    awareness = 'low';  // Extremely warm overrides everything
} else if (snowCover >= 50 && tempAnomaly <= 5) {
    awareness = 'high';
} else if (snowCover > 0 || tempAnomaly <= 8) {
    awareness = 'moderate';
} else {
    awareness = 'low';
}
```

### Region Definitions

**NSAA Regions (USA)**:
- Rocky Mountain, Pacific Northwest, Pacific Southwest, Midwest, Northeast, Southeast

**CSC Regions (Canada)**:
- British Columbia, Alberta, Prairies, Ontario, Quebec, Atlantic Canada

---

## SNOTEL Snowpack Page (`snotel.html`)

### Purpose
Interactive map visualization of snowpack conditions across Western North America using SNOTEL station data and HUC4 watershed aggregations.

### Data Sources
- `/data/snotel-snowpack.json` - US SNOTEL stations with SWE data
- `/data/bc-snow-stations.json` - BC Ministry stations
- `/data/huc2-watersheds.json` - Major watershed boundaries
- `/data/huc4-snowbasins.json` - Snowbasins with aggregated statistics

### External Dependencies
```html
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
```

### Key Functions

| Function | Line | Purpose |
|----------|------|---------|
| `loadData()` | 817 | Fetches all JSON data files |
| `initMap()` | 924 | Initializes Leaflet map centered on Western US |
| `loadWatershedBoundaries()` | 1020 | Loads HUC2 and HUC4 GeoJSON |
| `addHUC2Layer()` | 1050 | Renders major watershed boundaries |
| `addSnowbasinLayer()` | 1083 | Renders HUC4 snowbasins with color coding |
| `updateStations()` | 1205 | Plots US SNOTEL stations as circle markers |
| `updateBCStations()` | 1289 | Plots BC stations (cyan color) |
| `showStationDetails()` | 1380 | Opens station detail popup |
| `showStateDetail()` | 1420 | Shows all stations for clicked state |
| `getSnowpackColor()` | 798 | Returns color based on % of normal |
| `getSnowpackClass()` | 808 | Returns CSS class for % of normal |

### Color Scale

| % of Normal | Color | Class |
|-------------|-------|-------|
| < 50% | Red (#dc2626) | Drought |
| 50-75% | Orange (#f97316) | Below |
| 75-90% | Yellow (#facc15) | Low |
| 90-110% | Green (#22c55e) | Normal |
| 110-130% | Light Blue (#3b82f6) | Above |
| > 130% | Purple (#8b5cf6) | Exceptional |
| null | Gray (#475569) | No data |

### Snowbasin Labels

Each HUC4 polygon displays its % value as a permanent label using `L.divIcon`:

```javascript
const labelIcon = L.divIcon({
    className: 'snowbasin-label',
    html: `${pct}%`,
    iconSize: [40, 16],
    iconAnchor: [20, 8]
});
```

Labels use white text with black text-shadow for visibility on colored backgrounds.

---

## Economic Dashboard (`dashboard.html`)

### Purpose
Displays economic indicators relevant to ski industry planning, including consumer confidence, market performance, exchange rates, and travel data.

### Data Sources
- `/data/dashboard.json` - All economic metrics
- `/data/prediction-markets.json` - Prediction market data (optional)
- `/data/sports-betting.json` - Gaming metrics (optional)
- `/data/ski-airports.json` - Airport passenger data

### External Dependencies
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation"></script>
```

### Key Functions

| Function | Line | Purpose |
|----------|------|---------|
| `loadDashboard()` | 1391 | Fetches dashboard.json and renders all sections |
| `toggleSection()` | 944 | Accordion open/close functionality |
| `createChart()` | 1055 | Generic Chart.js line chart factory |
| `createChartWithThreshold()` | 1115 | Chart with horizontal threshold line |
| `createChartWithSkiSeason()` | 1211 | Chart with ski season shading |
| `createChartWithDualAxis()` | 1273 | Dual Y-axis chart for comparisons |
| `renderMetric()` | 1169 | Renders a metric card with sparkline |
| `renderMetricWithBaseline()` | 1185 | Metric with vs-2019 comparison |
| `renderCanadianOutbound()` | 1325 | Canadian travel departure stats |
| `renderBorderPorts()` | 1352 | US-Canada border crossing data |
| `renderSkiAirports()` | 1689 | Ski destination airport traffic |
| `loadPredictionMarkets()` | 1790 | Prediction market contracts |
| `loadSportsBetting()` | 2056 | Gaming industry metrics |
| `calcChange()` | 967 | Calculates period-over-period change |
| `calc30DayMomentum()` | 1001 | 30-day trend calculation |
| `getTrendArrow()` | 1013 | Returns up/down arrow based on change |

### Accordion Sections

1. **Economy Overview** - Consumer confidence, DJIA, unemployment
2. **Exchange Rates** - USD/CAD purchasing power
3. **Canadian Outbound Travel** - Departures to US
4. **Border Crossings** - Port of entry traffic
5. **Ski Airport Traffic** - Regional airport passenger data
6. **Prediction Markets** - Polymarket contracts (optional)
7. **Sports Betting** - Gaming handle and revenue (optional)

### Visual Variant

Dashboard uses a green accent gradient (vs blue/orange on snow pages):

```css
.bg-gradient {
    background:
        radial-gradient(ellipse at 15% 10%, rgba(59, 130, 246, 0.06) 0%, transparent 50%),
        radial-gradient(ellipse at 85% 90%, rgba(16, 185, 129, 0.04) 0%, transparent 50%),
        var(--bg-deep);
}
```

---

## Common Patterns

### Data Loading
All pages use async/await for data fetching:

```javascript
async function loadData() {
    try {
        const response = await fetch('/data/filename.json');
        const data = await response.json();
        // Process data
    } catch (error) {
        console.error('Error loading data:', error);
    }
}
```

### Error States
Pages display user-friendly error messages when data fails to load.

### Responsive Design
All pages use CSS Grid and Flexbox with media queries for mobile support.

### Accessibility
- Skip links for keyboard navigation
- ARIA labels on interactive elements
- Focus-visible outlines
- Semantic HTML structure

---

*Documentation generated: 2026-01-18*
