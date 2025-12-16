# NixVir.com Maintenance Guide

This document describes the automated data pipelines and manual maintenance procedures for nixvir.com.

## Architecture Overview

```
Data Sources          Python Scripts           JSON Data Files         Hugo Site
─────────────────────────────────────────────────────────────────────────────────
NOHRSC/Rutgers  ──►  update_snow_cover.py  ──►  snow-cover.json    ──►
FRED/SF Fed     ──►  update_dashboard.py   ──►  dashboard.json     ──►  Netlify
RSS Feeds       ──►  update_ski_news.py    ──►  ski-news.json      ──►  (auto-deploy)
```

## Automated Schedules (GitHub Actions)

| Workflow | Script | Schedule | Data Sources |
|----------|--------|----------|--------------|
| `update-snow-cover.yml` | `update_snow_cover.py` | Daily 6 AM & 6 PM EST | NOHRSC, Rutgers Global Snow Lab |
| `update-dashboard.yml` | `update_dashboard.py` | Weekdays 9 AM EST | FRED API, SF Fed News Sentiment |
| `update-ski-news.yml` | `update_ski_news.py` | Daily 6 AM EST | RSS feeds (various ski news sources) |

All workflows can also be triggered manually from GitHub Actions.

## Required GitHub Secrets

Set these in: GitHub repo > Settings > Secrets and variables > Actions

| Secret | Required For | How to Obtain |
|--------|--------------|---------------|
| `FRED_API_KEY` | Dashboard economic indicators | https://fred.stlouisfed.org/docs/api/api_key.html |
| `ANTHROPIC_API_KEY` | Ski news AI categorization | https://console.anthropic.com/ |
| `ALPHA_VANTAGE_KEY` | (Optional) Additional market data | https://www.alphavantage.co/support/#api-key |

## Manual Update Procedures

### Snow Cover Data
```powershell
cd c:\nixvir\nixvirweb
python update_snow_cover.py
```
- Fetches USA snow cover from NOHRSC (National Operational Hydrologic Remote Sensing Center)
- Calculates Canada snow cover using historical ratios
- Updates metro area snow coverage for 20 major cities
- Includes 30-day history and prior year comparisons

### Dashboard Data
```powershell
cd c:\nixvir\nixvirweb
# Requires FRED_API_KEY environment variable
python update_dashboard.py
```
- Fetches economic indicators: unemployment, GDP, inflation, housing starts, etc.
- Fetches gold prices
- Fetches SF Fed Daily News Sentiment Index (requires openpyxl)

### Ski News
```powershell
cd c:\nixvir\nixvirweb
# Optional: ANTHROPIC_API_KEY for AI-enhanced categorization
python update_ski_news.py
```
- Aggregates RSS feeds from ski industry news sources
- Categorizes articles by topic (resorts, business, equipment, etc.)
- Falls back to keyword-based scoring if no API key

## Deployment Flow

1. **Data Update**: Python scripts update JSON files in `static/data/`
2. **Git Commit**: Changes committed and pushed to GitHub
3. **Auto-Deploy**: Netlify detects push and rebuilds Hugo site
4. **Live**: Site updates at nixvir.com within ~2 minutes

## Local Development

### Prerequisites
- Python 3.11+
- Hugo (extended version recommended)
- Git

### Local Server
```powershell
C:\nixvir\hugo\hugo.exe server -s c:\nixvir\nixvirweb
```
Site available at http://localhost:1313

### Build Site
```powershell
C:\nixvir\hugo\hugo.exe --gc -s c:\nixvir\nixvirweb
```
Output goes to `public/` directory.

## Troubleshooting

### Snow Cover Shows Stale Data
1. Check if NOHRSC is accessible: https://www.nohrsc.noaa.gov/
2. Run `python update_snow_cover.py` manually
3. Check for errors in script output

### Dashboard Missing Economic Data
1. Verify `FRED_API_KEY` is set:
   ```powershell
   echo $env:FRED_API_KEY
   ```
2. If not set locally, add to Windows environment variables
3. For GitHub Actions, verify secret is configured

### Ski News Miscategorized
1. Check `update_ski_news.py` category keywords (line ~88)
2. Articles with generic keywords may need more specific patterns
3. Review `static/data/ski-news-review.json` for categorization audit

### Netlify Not Deploying
1. Check Netlify dashboard for build errors
2. Verify GitHub push succeeded: `git log --oneline -3`
3. Check Netlify build logs for Hugo errors

## File Locations

```
c:\nixvir\nixvirweb\
├── .github\workflows\         # GitHub Actions automation
│   ├── update-dashboard.yml
│   ├── update-ski-news.yml
│   └── update-snow-cover.yml
├── content\                   # Hugo content pages
├── layouts\                   # Hugo templates
│   └── partials\
│       └── site-navigation.html  # Snow widget code
├── static\data\               # JSON data files
│   ├── dashboard.json
│   ├── ski-news.json
│   ├── ski-news-review.json
│   └── snow-cover.json
├── update_dashboard.py        # Economic data fetcher
├── update_ski_news.py         # News aggregator
└── update_snow_cover.py       # Snow cover fetcher
```

## Data Sources Reference

### Snow Cover
- **NOHRSC**: https://www.nohrsc.noaa.gov/snow_model/ (USA official)
- **Rutgers GSL**: https://climate.rutgers.edu/snowcover/ (North America extent)

### Economic Indicators
- **FRED**: https://fred.stlouisfed.org/ (Federal Reserve Economic Data)
- **SF Fed Sentiment**: https://www.frbsf.org/research-and-insights/data-and-indicators/daily-news-sentiment-index/

### Ski News
- Various RSS feeds configured in `update_ski_news.py`
