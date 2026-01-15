# Claude Instructions for nixvirweb

## Core Principles

### 1. Data Integrity Over Display Coverage

**Never fabricate data at display time to fill gaps.**

When a value is needed but missing:
- First ask: "Why doesn't this data exist?"
- Fix the data pipeline to generate it properly
- Or display nothing ("--") rather than a derived substitute

Wrong approach:
```javascript
// BAD: Inventing combined average from country averages at display time
const combinedHistorical = (usaHistorical + canadaHistorical) / 2;
```

Right approach:
```javascript
// GOOD: Use real data if it exists, otherwise show nothing
const combinedHistorical = getHistoricalAverage('combined', dateMMDD);
// Returns null if no real data exists, card shows "--"
```

### 2. Display Logic vs. Data Generation

**Calculations at display time should only format or convert - never synthesize.**

Acceptable display-time operations:
- Unit conversion (°F to °C)
- Formatting (rounding, adding % signs)
- Color coding based on existing values

Unacceptable display-time operations:
- Deriving averages from component values
- Estimating missing data points
- Creating weighted combinations of other metrics

### 3. Missing Data is Information

Showing "--" for missing data is honest. Filling every field with something plausible-looking is deceptive. The absence of data tells users something meaningful about data availability.

### 4. National vs. Market-Level Data

**Always use national-level data for national statistics, not aggregated market data.**

The Regional Summary panel should show `snowData.combined.cover` (national land area coverage), NOT an average of individual metro market snow cover values. Metro markets skew toward urban areas with less snow coverage.

Wrong approach:
```javascript
// BAD: Averaging metro-level data for national stat
const avgSnowCover = markets.reduce((sum, m) => sum + m.snow_cover, 0) / markets.length;
// Result: ~15% (misleading - many metros have 0% snow)
```

Right approach:
```javascript
// GOOD: Use actual national combined data
const avgSnowCover = snowData?.combined?.cover ?? '--';
// Result: ~58% (accurate national land coverage)
```

## Terminology

**Never use "Feeder Markets"** - Use "Ski Markets" instead. The term "feeder" sounds jargony and unclear to users.

## Language Guidelines

**Avoid overly definitive or "AI-like" language in insight messages.**

Insight text should be factual and measured, not predictive or presumptuous about consumer behavior.

Wrong approach:
```javascript
// BAD: Too definitive
"Winter salience is likely high in these markets."
"Skiing is unlikely to be top-of-mind for consumers."
```

Right approach:
```javascript
// GOOD: Factual and measured
"All ski markets have snow on the ground and winter-like temperatures."
"Skiing may not be top-of-mind for consumers in these areas."
"X of Y markets have snow cover with seasonal temperatures."
```

Avoid words like: "likely", "unlikely", "definitely", "certainly", "will be", "won't be" when describing consumer sentiment or behavior.

## Data Sources

### Snow Cover Data
- **USA**: NOHRSC (National Operational Hydrologic Remote Sensing Center)
- **Canada**: NOAA IMS (Interactive Multisensor Snow and Ice Mapping System) - satellite data
- **Never derive** Canada data from USA data or vice versa

### Temperature Data
- **Source**: Open-Meteo Archive API
- **Metros**: 50 ski market metropolitan areas
- **Historical normals**: Computed from 30-year climate averages

### Historical Averages
- **File**: `static/data/snow-cover-historical.json`
- **Coverage**: 5 complete winters, Oct 1 - Apr 30
- **Required keys**: `usa`, `canada`, `combined` (all computed from real daily values)

## File Structure

```
static/
  data/
    snow-cover.json           # Current conditions
    snow-cover-historical.json # 5-year seasonal averages
    temperature-history.json   # Daily temperature anomalies by metro
```

## Pipeline Scripts

- `fetch_historical_averages.py` - Generates 5-year averages (run annually after Apr 30)
- `fetch_ims_snow_data.py` - Fetches real Canada snow data from NOAA IMS
- `backfill_current_season_temp.py` - Backfills temperature data gaps

## UI Components

### Snow Cover Dashboard (`static/snow-cover.html`)

#### Charts
- **Snow Cover Chart**: Full season (Oct 1 - Apr 30), USA + Canada current vs 5-year avg
- **Temperature Anomaly Chart**: Same x-axis, shows temp deviation from normal
- **Charts are synchronized**: Zoom/pan on one chart updates the other
- Both charts have reset buttons that reset BOTH charts together

#### Map with Regional Borders
The map displays NSAA and CSC ski regions with visible borders and labels:

**NSAA Regions (USA)**:
- Rocky Mountain (CO, UT, WY, MT, ID, NM)
- Pacific Northwest (WA, OR)
- Pacific Southwest (CA, NV, AZ)
- Midwest (MN, WI, MI, OH, IN, IL, IA, MO, ND, SD, NE, KS)
- Northeast (ME, NH, VT, MA, RI, CT, NY, NJ, PA, MD, DE, WV)
- Southeast (VA, NC, TN, GA, AL)

**CSC Regions (Canada)**:
- British Columbia
- Alberta
- Prairies (SK, MB)
- Ontario
- Quebec
- Atlantic Canada (NB, NS, PE, NL)

Region definitions are in `NSAA_REGIONS` and `CSC_REGIONS` objects with `stateIds` (FIPS codes) or `provinces` arrays.

#### Regional Summary Panel
Shows national-level statistics:
- Snow Cover: `snowData.combined.cover` (NOT market average)
- Temperature: `snowData.combined.temperature.avg_anomaly_f`
- Market count and conditions breakdown

#### Winter Salience Coloring
Map bubbles are colored by "winter salience" (how top-of-mind winter/skiing is for consumers), NOT by snow depth.

**Salience Levels**:
- **High (Green)**: Snow cover ≥50% AND temperature anomaly ≤5°F above normal
- **Moderate (Orange)**: Some snow cover OR temperature ≤8°F above normal
- **Low (Red)**: No snow cover AND warm temperatures, OR temperature ≥20°F above normal

**Critical Rule**: Temperature anomaly ≥20°F above normal always results in LOW salience, regardless of snow cover. Extremely warm weather overrides snow presence.

```javascript
// Winter salience calculation logic
if (tempAnomaly >= 20) {
    awareness = 'low';  // Extremely warm = low salience regardless of snow
} else if (snowCover >= 50 && tempAnomaly <= 5) {
    awareness = 'high';
} else if (snowCover > 0 || tempAnomaly <= 8) {
    awareness = 'moderate';
} else {
    awareness = 'low';
}
```

#### Temperature Display Styling
Temperature anomaly values in the VS NORMAL column use color classes:

```css
.temp-hot { color: #ef4444; }    /* Red - extremely warm (≥20°F above normal) */
.temp-warm { color: orange; }     /* Orange - warm (>8°F above normal) */
.temp-cool { color: blue; }       /* Blue - cool (<3°F above normal) */
.temp-normal { color: gray; }     /* Gray - near normal (3-8°F) */
```

The `temp-hot` class specifically highlights markets where winter feels distant due to extreme warmth.

## Common Mistakes to Avoid

1. **Prioritizing coverage over accuracy** - Don't invent data to fill display fields
2. **Treating display as the fix location** - Missing data is a pipeline problem
3. **Deriving country data from other countries** - Each region needs real measurements
4. **Assuming averages of averages equal the true average** - Compute from raw daily values
5. **Using market averages for national stats** - Metro data ≠ national land coverage
6. **Using "Feeder" terminology** - Always use "Ski Markets" instead
7. **Using definitive language about consumer behavior** - Say "may" not "will" or "likely"
8. **Forgetting temperature override** - ≥20°F above normal always means low salience
9. **Blaming browser cache for stale data** - When the user reports stale/old data on the website, the problem is almost never browser caching. Check: (1) Is the file committed to git? (2) Has it been pushed? (3) Is the Netlify deploy complete? (4) Is the correct file path being served? Don't suggest "try hard refresh" or "clear cache" - investigate the actual deployment pipeline first.

## Related Projects

Region boundary work and additional data sources exist in:
- `d:\projects\winter_outlook\` - Winter outlook analysis with boundary downloads
- `d:\projects\PBF_mining\` - Ski area data compilation
- `d:\projects\backup\nixvir\jobs\2025\Whistler-Blackcomb\` - Canadian regional analysis (R scripts)
