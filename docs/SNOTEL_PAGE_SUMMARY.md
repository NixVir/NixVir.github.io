# SNOTEL Snowpack Visualization Page - Development Summary

## Overview

The SNOTEL page (`static/snotel.html`) provides an interactive map visualization of snowpack conditions across Western North America, combining US SNOTEL data with Canadian snow monitoring stations from BC, Alberta, and Quebec.

## Key Features Implemented

### 1. BC Snow Data Integration
**Files Created:**
- `fetch_bc_snow_data.py` - Fetches BC station data from BC Ministry of Environment

**Data Sources:**
- Station locations: BC Government WFS service (`openmaps.gov.bc.ca/geo/pub/wfs`)
- SWE data: `https://www.env.gov.bc.ca/wsd/data_searches/snow/asws/data/SW.csv`
- Snow depth: `https://www.env.gov.bc.ca/wsd/data_searches/snow/asws/data/SD.csv`

**Key Implementation Details:**
- WFS query fetches active stations only (`STATUS = 'Active'`)
- CSV data uses hourly rows; script finds most complete row from last 48 hours
- Station IDs in CSV header format: "1A01P Yellowhead Lake" (ID is first part before space)
- Output: `static/data/bc-snow-stations.json`

**BC stations displayed in cyan** since they don't have % of normal (no historical baseline available).

### 2. Alberta Snow Pillow Integration (Added January 2026)
**Files Created:**
- `fetch_alberta_snow_pillows.py` - Fetches real-time SWE from rivers.alberta.ca
- `.github/workflows/update-alberta-snow.yml` - Automated updates (2x daily)

**Data Source:**
- Alberta Environment API: `https://rivers.alberta.ca/EnvironmentalDataService/ReadManifest`
- Real-time JSON endpoints: `https://rivers.alberta.ca/apps/Basins/data/figures/river/abrivers/envdata/envdata_{station}_table.json`

**Key Implementation Details:**
- 14 mountain pillow stations with real-time SW (Snow Water Equivalent) data
- Stations identified by parameter_graphs with `parname === "SW"` and `parameter_data_status === "normal"`
- Output: `static/data/alberta-snow-pillows.json`

**Alberta stations displayed in orange/amber** to distinguish from BC (cyan) and US (color-coded).

**Station List:**
| Station ID | Name | Location |
|------------|------|----------|
| 05AA809 | Gardiner Creek | SW Alberta |
| 05AA817 | South Racehorse Creek | SW Alberta |
| 05AB814 | Sentinel Peak | SW Alberta |
| 05AD803 | Akamina Pass 2 | Waterton |
| 05BB803 | Sunshine Village | Banff |
| 05BF824 | Three Isle Lake | Kananaskis |
| 05BJ805 | Little Elbow Summit | Kananaskis |
| 05BL811 | Lost Creek South | SW Alberta |
| 05CA805 | Skoki Lodge | Lake Louise |
| 05DA807 | Whiterabbit Creek | Jasper area |
| 05DB802 | Limestone Ridge | Central Rockies |
| 05DD804 | Southesk | Jasper area |
| 07BB811 | Paddle Headwaters | Northern Alberta |
| 07BB814 | Twin Lakes | Northern Alberta |

### 3. Quebec Hydro-Québec Snow Station Integration
**Files Created:**
- `fetch_quebec_snow_stations.py` - Fetches SWE data from Hydro-Québec

**Data Source:**
- Hydro-Québec public snow monitoring network

**Key Implementation Details:**
- 19 stations across Quebec watersheds
- Output: `static/data/quebec-snow-stations.json`

**Quebec stations displayed in purple** to distinguish from other regions.

### 4. HUC4 Snowbasin Visualization
**Data File:** `static/data/huc4-snowbasins.json`

**Features:**
- Polygons color-coded by mean snowpack percentage
- Hover tooltip shows basin name and % of normal
- Click popup shows detailed info (HUC4 code, range, station count, area)
- Hover highlight effect (white border)

### 5. Permanent Snowbasin Labels
**Purpose:** Display % of normal value directly on each snowbasin polygon without hovering.

**Implementation:**
```javascript
// In addSnowbasinLayer():
const layersWithPct = [];  // Store layers during GeoJSON creation

// After creating snowbasinLayer, create label layer:
snowbasinLabelLayer = L.layerGroup();

layersWithPct.forEach(({ layer, pct }) => {
    const center = layer.getBounds().getCenter();  // Use Leaflet's bounds center

    const labelIcon = L.divIcon({
        className: 'snowbasin-label',
        html: `${pct}%`,
        iconSize: [40, 16],
        iconAnchor: [20, 8]
    });

    const marker = L.marker(center, {
        icon: labelIcon,
        interactive: false  // Don't block polygon clicks
    });

    snowbasinLabelLayer.addLayer(marker);
});
```

**CSS for Labels:**
```css
.snowbasin-label {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #fff;
    font-size: 11px;
    font-weight: bold;
    text-align: center;
    text-shadow:
        -1px -1px 0 #000,
        1px -1px 0 #000,
        -1px 1px 0 #000,
        1px 1px 0 #000,
        0 0 4px rgba(0,0,0,0.9);
    white-space: nowrap;
    pointer-events: none;
}
```

**Layer Control:** Labels can be toggled on/off via "Snowbasin Labels" in the layer control.

### 6. State Click Station Listing
**Feature:** Clicking a state in the sidebar shows a detailed panel listing all stations in that state.

**Functions:**
- `filterByState(stateCode)` - Handles click, zooms map to state bounds
- `showStateDetail(stateCode)` - Populates station list panel
- `zoomToStation(stationId, isBC)` - Zooms to individual station when clicked in list
- `closeStateDetail()` - Closes panel and resets view

**Sorting:**
- US SNOTEL: Sorted by % of median (ascending = worst conditions first)
- BC stations: Sorted by SWE (descending = highest snow first)

### 7. Toggle Buttons with Auto-Zoom
Filter bar includes toggle buttons for layer visibility. When enabled, Canadian region toggles auto-zoom to the region:

| Button | Layer | Color | Auto-Zoom Region |
|--------|-------|-------|------------------|
| US SNOTEL | US station markers | Color-coded by % | No |
| BC Stations | BC snow stations | Cyan | British Columbia |
| AB Pillows | Alberta snow pillows | Orange/Amber | Alberta Rockies |
| QC Stations | Quebec stations | Purple | Quebec |

## Data Files

| File | Description | Update Frequency |
|------|-------------|------------------|
| `static/data/snotel-snowpack.json` | US SNOTEL station data with SWE and % of median | Daily |
| `static/data/bc-snow-stations.json` | BC snow station data with SWE and snow depth | Daily |
| `static/data/alberta-snow-pillows.json` | Alberta real-time SWE from snow pillows | 2x daily |
| `static/data/quebec-snow-stations.json` | Quebec Hydro-Québec SWE data | Daily |
| `static/data/huc2-watersheds.json` | Major watershed region outlines | Static |
| `static/data/huc4-snowbasins.json` | Snowbasin polygons with aggregated snowpack stats | Daily |

## Color Scale

```javascript
function getSnowpackColor(pct) {
    if (pct === null || pct === undefined) return '#475569';  // Gray
    if (pct < 50) return '--swe-drought';   // Red (drought)
    if (pct < 75) return '--swe-below';     // Orange
    if (pct < 90) return '--swe-low';       // Yellow
    if (pct <= 110) return '--swe-normal';  // Green
    if (pct <= 130) return '--swe-above';   // Light blue
    return '--swe-high';                     // Blue (exceptional)
}
```

## Known Issues / Future Work

1. **BC % of Normal**: BC stations only show raw SWE values, not % of normal (no historical baseline data available from BC source)

2. **Label Density**: At low zoom levels, snowbasin labels may overlap. Consider:
   - Hiding labels below certain zoom level
   - Using clustering or label collision detection

3. **Missing logo**: `images/nixvir-logo.svg` returns 404 (minor cosmetic issue)

## Scripts

| Script | Purpose | Schedule |
|--------|---------|----------|
| `fetch_snotel_data.py` | Fetch US SNOTEL data | Daily |
| `fetch_bc_snow_data.py` | Fetch BC snow station data | Daily |
| `fetch_alberta_snow_pillows.py` | Fetch Alberta snow pillow SWE | 2x daily (2 PM & 10 PM UTC) |
| `fetch_quebec_snow_stations.py` | Fetch Quebec Hydro-Québec SWE | Daily |

## GitHub Actions Workflows

| Workflow | Purpose |
|----------|---------|
| `.github/workflows/update-snotel.yml` | US SNOTEL data updates |
| `.github/workflows/update-bc-snow.yml` | BC snow station updates |
| `.github/workflows/update-alberta-snow.yml` | Alberta snow pillow updates |
| `.github/workflows/update-quebec-snow.yml` | Quebec station updates |

## Architecture Notes

- **Leaflet.js** for interactive mapping
- **Layer groups** for organized layer management
- **GeoJSON** for watershed/snowbasin boundaries
- **divIcon markers** for permanent labels (not tooltips) to allow both labels AND hover tooltips
