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
content/
  manual-news/                # CMS-managed manual news stories
    _index.md                 # Section config (enables JSON output)
    *.md                      # Individual story files
static/admin/
  config.yml                  # Sveltia CMS configuration
  index.html                  # CMS entry point
layouts/
  manual-news/
    list.json                 # Hugo template generating /manual-news/index.json
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

## Accessibility Standards (WCAG 2.1 AA)

The site follows WCAG 2.1 Level AA standards. Key requirements:

### Color Contrast (WCAG 1.4.3)
All text must meet 4.5:1 minimum contrast ratio against backgrounds:

```css
/* Shared theme colors - verified for contrast */
--text-secondary: #9ca3b0;  /* 4.5:1 on --bg-card (#111820) */
--text-muted: #8a919e;      /* 4.5:1 on --bg-elevated (#1a2230) */
--success: #34d399;         /* 4.5:1 on dark backgrounds */
--warning: #fbbf24;         /* 4.5:1 on dark backgrounds */
--danger: #f87171;          /* 4.5:1 on dark backgrounds */
```

**When adding new colors**: Always verify contrast ratio using a tool like WebAIM Contrast Checker before committing.

### Focus Indicators (WCAG 2.4.7)
All interactive elements must have visible focus states:

```css
/* Standard focus indicator - defined in shared-theme.css */
button:focus-visible,
select:focus-visible,
input:focus-visible,
a:focus-visible {
    outline: 2px solid var(--accent-cold-bright);
    outline-offset: 2px;
}
```

**Never use `outline: none`** without providing an alternative visible focus indicator.

### Heading Hierarchy (WCAG 1.3.1)
Headings must follow sequential order: H1 → H2 → H3. Never skip levels.

| Page | Structure |
|------|-----------|
| Dashboard | H1 (visually hidden) → H2 (accordion sections) → H3 (metric cards) |
| Snow Cover | H1 (banner title) → H2 (chart titles) |
| Ski News | H1 (banner title) → H3 (article titles in cards) |

### Screen Reader Support
Use the `.sr-only` class (defined in `shared-theme.css`) for visually hidden content that should be accessible to screen readers:

```html
<h1 class="sr-only">Ski Markets Economic Dashboard</h1>
```

### Skip Links (WCAG 2.4.1)
- Hugo templates include skip links via `layouts/_default/baseof.html`
- Static HTML pages should include: `<a href="#main-content" class="skip-link">Skip to main content</a>`

### Charts Accessibility (WCAG 1.1.1)
Canvas charts should have:
```html
<canvas id="chart-name" role="img" aria-label="Description of chart data">
```

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
10. **Removing focus outlines** - Never use `outline: none` without providing visible `:focus-visible` alternative
11. **Skipping heading levels** - Always use sequential H1 → H2 → H3 hierarchy
12. **Low contrast text** - All text needs 4.5:1 contrast ratio minimum

## SNOTEL Snowpack Page (`static/snotel.html`)

Interactive map visualization of snowpack conditions across Western North America.

### Data Sources
- **US SNOTEL**: NRCS via `fetch_snotel_data.py` → `static/data/snotel-snowpack.json`
- **BC Snow Stations**: BC Ministry of Environment via `fetch_bc_snow_data.py` → `static/data/bc-snow-stations.json`
- **Alberta Snow Pillows**: Alberta Environment via `fetch_alberta_snow_pillows.py` → `static/data/alberta-snow-pillows.json`
  - API: `https://rivers.alberta.ca/EnvironmentalDataService/ReadManifest`
  - 14 mountain pillow stations with real-time SWE
  - Updated 2x daily (2 PM & 10 PM UTC)
- **Quebec Snow Stations**: Hydro-Québec via `fetch_quebec_snow_stations.py` → `static/data/quebec-snow-stations.json`
- **Watersheds**: `static/data/huc2-watersheds.json` (major regions), `static/data/huc4-snowbasins.json` (snowbasins with aggregated stats)

### Key Features
1. **HUC4 Snowbasins**: Color-coded polygons showing mean % of normal snowpack
2. **Permanent Labels**: Each snowbasin displays its % value directly on the polygon using `L.divIcon` markers
3. **Hover Tooltips**: Basin name and % of normal shown on hover (separate from permanent labels)
4. **Click Popups**: Detailed info including HUC4 code, range, station count, area
5. **BC Integration**: BC stations shown in cyan (no % of normal available, only raw SWE)
6. **Alberta Integration**: Alberta snow pillows shown in orange/amber with real-time SWE
7. **Quebec Integration**: Quebec stations shown in purple
8. **State Click Detail**: Clicking a state in sidebar shows all stations with their values
9. **Auto-Zoom**: Clicking BC/AB/QC toggle buttons auto-zooms to that region

### Snowbasin Label Implementation
Labels use `L.divIcon` (not tooltips) to allow BOTH permanent labels AND hover tooltips:
```javascript
const labelIcon = L.divIcon({
    className: 'snowbasin-label',
    html: `${pct}%`,
    iconSize: [40, 16],
    iconAnchor: [20, 8]
});
const marker = L.marker(center, { icon: labelIcon, interactive: false });
```

CSS uses white text with black text-shadow outline for visibility on colored backgrounds.

### BC Snow Data Notes
- Station locations from WFS: `openmaps.gov.bc.ca/geo/pub/wfs`
- SWE data from CSV: `env.gov.bc.ca/wsd/data_searches/snow/asws/data/SW.csv`
- CSV header format: "1A01P Yellowhead Lake" (station ID is first part before space)
- Script finds most complete row from last 48 hours (recent rows may be incomplete)

### Color Scale
```
< 50%  → Red (drought)
50-75% → Orange (below)
75-90% → Yellow (low)
90-110% → Green (normal)
110-130% → Light blue (above)
> 130% → Blue (exceptional)
null   → Gray (#475569)
```

See `docs/SNOTEL_PAGE_SUMMARY.md` for full implementation details.

## Ski Business News (`static/ski-news.html`)

RSS aggregator for ski industry business news, with CMS-managed manual story injection.

### Key Files
- **Script**: `update_ski_news.py` - Main aggregation and scoring pipeline
- **Config**: `config/ski-news-config.yaml` - Configurable settings
- **Output**: `static/data/ski-news.json` - Final article feed (automated)
- **Manual Stories**: `content/manual-news/*.md` - CMS-managed stories → `/manual-news/index.json`
- **CMS**: `static/admin/config.yml` - Sveltia CMS configuration
- **Documentation**: `docs/SKI_NEWS_SCRAPING_DOCUMENTATION.md` - Full system docs

### Pipeline Overview
1. **Fetch**: Pull articles from 40+ RSS feeds
2. **Pre-filter**: Two-tier filtering with PRIMARY_SKI_TERMS + SECONDARY_BUSINESS_TERMS
3. **Source diversity cap**: Limit articles per source during processing (default: 5)
4. **Score**: Keyword-based scoring (LLM scoring available but disabled by default)
5. **Deduplicate**: Title similarity + lead paragraph comparison + source suffix stripping
6. **Interleave**: Round-robin source distribution for output diversity
7. **Output**: JSON feed for frontend display

### Manual News Stories (CMS)

Manual stories are added via Sveltia CMS at `/admin/` and stored as markdown files in `content/manual-news/`. Hugo generates `/manual-news/index.json` at build time.

**Data flow**: CMS save → git commit to master → Netlify build (~1-3 min) → live on site

**Display**: Both the ski-news page AND the front page fetch `/manual-news/index.json` and merge manual stories into the automated feed. Manual stories:
- Are prepended to the feed (appear first)
- Support pinning with configurable duration (1-30 days)
- Can be article, podcast, or video content types
- Can be deactivated without deleting via the `active` toggle

**Frontmatter fields**: `title`, `story_url`, `source`, `category`, `content_type`, `description`, `pub_date`, `pin_days`, `active`

### Source Diversity & Interleaving
The output uses round-robin interleaving to prevent source clustering:

```python
# Instead of: sort by date → cap per source (clusters same-source articles)
# We do: group by source → round-robin interleave (distributes sources evenly)
```

This prevents the feed from appearing to copy from just a few aggregator sites. Each round takes one article from each source, prioritizing sources with fresher content.

**Key constants**:
- `MAX_ARTICLES_PER_SOURCE = 5` - Cap during processing
- `MAX_PER_SOURCE_OUTPUT = 3` - Cap in final output
- `MAX_ARTICLES_OUTPUT = 50` - Total articles in feed

### Deduplication

The pipeline deduplicates at two levels:

1. **Pipeline** (`update_ski_news.py`): Title similarity (0.85 threshold) with source suffix stripping via `_strip_source_suffix()` to catch Google News variants like "Article Title - The Cool Down" vs "Article Title - Source B". Also compares lead paragraphs (0.80 threshold).

2. **Front page** (`layouts/index.html`): Normalizes aggregator sources (all `Google News - *` → `Google News` for source-based dedup) and checks title prefix similarity (40+ shared characters = duplicate).

### Common Mistakes to Avoid
1. **Sorting by date before source cap** - Creates source clustering; always interleave
2. **Modifying files outside ski news scope** - The script is self-contained; don't touch config.toml, .gitignore, or other site files when working on news scraping
3. **Ignoring source health** - Check `static/data/ski-news-source-health.json` for failing feeds
4. **Front page missing manual stories** - Both `layouts/index.html` and `layouts/page/ski-news.html` must fetch `/manual-news/index.json`

## Related Projects

Region boundary work and additional data sources exist in:
- `d:\projects\winter_outlook\` - Winter outlook analysis with boundary downloads
- `d:\projects\PBF_mining\` - Ski area data compilation
- `d:\projects\backup\nixvir\jobs\2025\Whistler-Blackcomb\` - Canadian regional analysis (R scripts)
