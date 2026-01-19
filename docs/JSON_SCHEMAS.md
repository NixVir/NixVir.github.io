# JSON Data Schemas

This document describes the structure of JSON data files in `/static/data/`.

---

## Overview

| File | Size | Updated By | Purpose |
|------|------|------------|---------|
| `snow-cover.json` | ~50 KB | `update_snow_cover.py` | Current snow conditions |
| `snow-cover-historical.json` | ~15 KB | `fetch_historical_averages.py` | 5-year averages |
| `temperature-history.json` | ~100 KB | `update_snow_cover.py` | Daily temp anomalies |
| `dashboard.json` | ~30 KB | `update_dashboard.py` | Economic indicators |
| `ski-news.json` | ~80 KB | `update_ski_news.py` | Aggregated news |
| `snotel-snowpack.json` | ~150 KB | `fetch_snotel_data.py` | SNOTEL stations |
| `bc-snow-stations.json` | ~10 KB | `fetch_bc_snow_data.py` | BC snow stations |
| `huc4-snowbasins.json` | ~200 KB | Manual | Watershed boundaries |

---

## snow-cover.json

Current snow cover conditions for North America.

```json
{
  "updated": "2026-01-18 23:21 UTC",
  "data_sources": {
    "usa": "NOHRSC",
    "canada": "NOAA IMS",
    "rutgers_available": true,
    "copernicus_available": false
  },
  "combined": {
    "cover": 57.2,
    "change": "-1.1%",
    "context": "Approximately 57% of North American land area...",
    "temperature": {
      "avg_temp_c": -1.0,
      "avg_temp_f": 30.3,
      "avg_anomaly_c": 1.7,
      "avg_anomaly_f": 3.0
    }
  },
  "skiMarkets": {
    "usa": {
      "cover": 20.5,
      "avg_temp_c": 4.8,
      "avg_temp_f": 40.6,
      "avg_anomaly_c": 4.0,
      "avg_anomaly_f": 7.1,
      "metro_count": 31
    },
    "canada": { /* same structure */ }
  },
  "usa": {
    "cover": 24.2,
    "change": "-1.1%",
    "areaSqMi": 918874,
    "areaSqKm": 2379874,
    "avgDepthInches": null,
    "avgDepthCm": null,
    "priorYearAvgDepthInches": 2.2,
    "priorYearAvgDepthCm": 5.6,
    "history": [
      { "date": "2025-10-01", "value": 0.0 },
      { "date": "2025-10-02", "value": 0.0 }
      // ... daily values through current date
    ]
  },
  "canada": { /* same structure as usa */ },
  "metros": [
    {
      "name": "Denver-Aurora, CO",
      "state": "CO",
      "country": "usa",
      "lat": 39.7392,
      "lon": -104.9903,
      "snow_cover": 0,
      "temperature": {
        "temp_c": 8.5,
        "temp_f": 47.3,
        "normal_c": 1.2,
        "normal_f": 34.2,
        "anomaly_c": 7.3,
        "anomaly_f": 13.1
      },
      "awareness": "low"
    }
    // ... 50 markets total
  ]
}
```

### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `combined.cover` | number | % of North American land with snow |
| `combined.temperature.avg_anomaly_f` | number | Average temp deviation from normal (°F) |
| `skiMarkets.usa.cover` | number | Average snow cover across US metro markets |
| `usa.cover` | number | % of USA land area with snow (national) |
| `usa.history` | array | Daily values from Oct 1 through current date |
| `metros[].awareness` | string | Winter salience: "high", "moderate", "low" |

---

## snow-cover-historical.json

5-year seasonal averages for snow cover comparison.

```json
{
  "generated": "2026-01-12 13:45 UTC",
  "description": "5-year average snow cover for ski season (Oct 1 - Apr 30)",
  "winters_included": [
    "2020/2021", "2021/2022", "2022/2023", "2023/2024", "2024/2025"
  ],
  "usa": [
    { "date": "10-01", "value": 0.2, "count": 5 },
    { "date": "10-02", "value": 0.3, "count": 5 }
    // ... through "04-30"
  ],
  "canada": [ /* same structure */ ],
  "combined": [ /* same structure */ ]
}
```

### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `date` | string | Month-day format "MM-DD" |
| `value` | number | Average % snow cover for that day |
| `count` | number | Number of years with data (should be 5) |

---

## dashboard.json

Economic indicators for ski industry planning.

```json
{
  "updated": "2026-01-16 14:18:59",
  "consumer_confidence": [
    {
      "date": "2024-12-01",
      "series_id": "UMCSENT",
      "value": 74.0,
      "realtime_start": "2025-12-19",
      "realtime_end": "2025-12-19"
    }
  ],
  "markets": [
    {
      "symbol": "SPY",
      "current_date": "2026-01-15",
      "current_close": 6944.47,
      "history": [
        { "date": "2025-12-31", "close": 6845.5 }
      ]
    }
  ],
  "djia": [ /* FRED series data */ ],
  "unemployment": [ /* FRED series data */ ],
  "inflation": {
    "cpi": [ /* FRED series data */ ],
    "pce": [ /* FRED series data */ ]
  },
  "exchange_rates": {
    "usd_cad": [ /* daily rates */ ]
  },
  "canadian_outbound": {
    "us_departures": [ /* monthly data */ ],
    "overseas_departures": [ /* monthly data */ ]
  },
  "border_crossings": {
    "ports": [
      {
        "port_code": "0401",
        "port_name": "Champlain-Rouses Point, NY",
        "data": [ { "date": "2025-10", "passengers": 123456 } ]
      }
    ]
  }
}
```

### Data Sources

| Field | Source | Frequency |
|-------|--------|-----------|
| `consumer_confidence` | FRED UMCSENT | Monthly |
| `markets` | FRED SP500/DJI | Daily |
| `unemployment` | FRED UNRATE | Monthly |
| `exchange_rates` | FRED DEXCAUS | Daily |
| `canadian_outbound` | Statistics Canada | Monthly |
| `border_crossings` | BTS | Monthly |

---

## ski-news.json

Aggregated ski industry news articles.

```json
{
  "updated": "2026-01-18 11:11:10",
  "total_articles": 50,
  "scoring_method": "keyword",
  "articles": [
    {
      "source": "Snow Industry News",
      "title": "Article Title Here",
      "url": "https://example.com/article",
      "content": "First 1000 characters of article content...",
      "description": "Optional RSS description",
      "pub_date": "2026-01-17",
      "id": "0e5f98c70fb7",
      "prefilter_business_score": 0,
      "source_boost": 2,
      "score": 10,
      "score_details": {
        "reason": "Keyword scoring (boost: 2)",
        "method": "keyword"
      },
      "score_method": "keyword",
      "category": "winter-sports",
      "secondary_categories": ["hospitality", "international"],
      "approved_date": "2026-01-17",
      "other_sources": [
        { "source": "Another Source", "url": "https://..." }
      ]
    }
  ]
}
```

### Article Fields

| Field | Type | Description |
|-------|------|-------------|
| `source` | string | RSS feed source name |
| `title` | string | Article headline |
| `url` | string | Link to full article |
| `content` | string | Truncated article text |
| `pub_date` | string | Publication date (YYYY-MM-DD) |
| `id` | string | Unique hash ID |
| `score` | number | Relevance score (higher = more relevant) |
| `category` | string | Primary category |
| `secondary_categories` | array | Additional categories |
| `other_sources` | array | Deduplicated articles from other sources |

### Categories

- `winter-sports` - Skiing, snowboarding
- `resort-operations` - Ski area operations
- `hospitality` - Hotels, dining
- `weather-snow` - Conditions, forecasts
- `safety-incidents` - Accidents, incidents
- `real-estate` - Mountain property
- `canada` - Canadian ski industry
- `international` - Global ski news

---

## snotel-snowpack.json

SNOTEL station data with snowpack measurements.

```json
{
  "generated": "2026-01-16T11:54:39.697228",
  "source": "NRCS National Water and Climate Center",
  "source_url": "https://www.nrcs.usda.gov/wps/portal/wcc/home/",
  "baseline": "1991-2020 median",
  "units": {
    "swe": "inches",
    "pct_median": "percent of 1991-2020 median",
    "elevation": "feet"
  },
  "statistics": {
    "overall": {
      "count": 734,
      "mean_pct": 67.1,
      "median_pct": 63,
      "min_pct": 0,
      "max_pct": 181,
      "below_normal": 543,
      "normal": 96,
      "above_normal": 95
    },
    "by_state": {
      "CO": {
        "count": 102,
        "mean_pct": 58.0,
        "below_normal": 99,
        "normal": 3,
        "above_normal": 0
      }
    }
  },
  "stations": [
    {
      "triplet": "302:CO:SNTL",
      "name": "Berthoud Summit",
      "state": "CO",
      "huc": "10190005",
      "lat": 39.8,
      "lon": -105.78,
      "elevation_ft": 11315,
      "swe_in": 8.5,
      "median_in": 14.2,
      "pct_median": 60,
      "date": "2026-01-16"
    }
  ]
}
```

### Station Fields

| Field | Type | Description |
|-------|------|-------------|
| `triplet` | string | NRCS station ID (###:ST:SNTL) |
| `name` | string | Station name |
| `state` | string | Two-letter state code |
| `huc` | string | HUC8 watershed code |
| `lat`, `lon` | number | Station coordinates |
| `elevation_ft` | number | Elevation in feet |
| `swe_in` | number | Current snow water equivalent (inches) |
| `median_in` | number | 1991-2020 median SWE for this date |
| `pct_median` | number | Current as % of median (null if no median) |

---

## bc-snow-stations.json

British Columbia snow survey stations.

```json
{
  "generated": "2026-01-16T12:00:00",
  "source": "BC Ministry of Environment",
  "stations": [
    {
      "id": "1A01P",
      "name": "Yellowhead Lake",
      "lat": 52.88,
      "lon": -118.43,
      "elevation_m": 1067,
      "swe_mm": 245,
      "date": "2026-01-16"
    }
  ]
}
```

### Notes

- BC stations do NOT have % of normal data
- SWE is in millimeters (not inches)
- Displayed as cyan markers on SNOTEL map

---

## huc4-snowbasins.json

HUC4 watershed boundaries with aggregated statistics.

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "HUC4": "1401",
        "NAME": "Colorado Headwaters",
        "mean_pct": 58,
        "median_pct": 55,
        "station_count": 15,
        "min_pct": 32,
        "max_pct": 89
      },
      "geometry": {
        "type": "MultiPolygon",
        "coordinates": [ /* GeoJSON coordinates */ ]
      }
    }
  ]
}
```

### Properties

| Field | Type | Description |
|-------|------|-------------|
| `HUC4` | string | 4-digit watershed code |
| `NAME` | string | Watershed name |
| `mean_pct` | number | Mean % of normal for stations in basin |
| `median_pct` | number | Median % of normal |
| `station_count` | number | Number of SNOTEL stations |
| `min_pct`, `max_pct` | number | Range of station values |

---

## Data Pipeline Schedule

| File | Workflow | Schedule |
|------|----------|----------|
| snow-cover.json | update-snow-cover.yml | 6 AM & 6 PM EST |
| dashboard.json | update-dashboard.yml | 9 AM EST (M-F) |
| ski-news.json | update-ski-news.yml | 6 AM EST daily |
| snotel-snowpack.json | update-snotel.yml | 6 AM EST daily |

---

*Documentation generated: 2026-01-18*
