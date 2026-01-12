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

## Common Mistakes to Avoid

1. **Prioritizing coverage over accuracy** - Don't invent data to fill display fields
2. **Treating display as the fix location** - Missing data is a pipeline problem
3. **Deriving country data from other countries** - Each region needs real measurements
4. **Assuming averages of averages equal the true average** - Compute from raw daily values
