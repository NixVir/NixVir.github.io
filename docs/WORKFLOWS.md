# GitHub Actions Workflow Documentation

## Overview

NixVir uses 6 scheduled GitHub Actions workflows to automatically update data for the website. All workflows commit directly to the `master` branch, triggering Netlify auto-deploys.

**Current Features** (Jan 2026):
- ✅ Removed pip caching (eliminates intermittent checkout failures)
- ✅ JSON validation before all commits
- ✅ Data quality sanity checks (minimum record counts, required fields)
- ✅ Automatic GitHub issue creation on failures (label: `workflow-failure`)
- ✅ Retry logic (3 attempts with 30s delay)
- ✅ Data backups before overwrites (`.backup.json` files)
- ✅ Hugo build verification after commits
- ✅ Consolidated Canadian snow workflows (BC/AB/QC in one workflow)

## Data Health Dashboard

Monitor the health of all data feeds at: **[nixvir.com/data-status](https://nixvir.com/data-status)**

The dashboard shows:
- Real-time status of each data feed (Healthy/Warning/Stale)
- Last update timestamp
- Expected update frequency

Alternative URLs: `/health`, `/status`

---

## Workflow Summary

| Workflow | Schedule | Data Source | Output File(s) |
|----------|----------|-------------|----------------|
| update-snotel | Daily 2 PM UTC | NRCS AWDB | `snotel-snowpack.json` |
| update-snow-cover | 2x daily (11 AM, 11 PM UTC) | NOHRSC, NOAA IMS | `snow-cover.json`, `snow-globe.png` |
| update-canadian-snow | 2x daily (6 AM, 6 PM UTC) | BC/AB/QC sources | `bc-snow-basins.json`, `alberta-snow-pillows.json`, `quebec-snow-stations.json` |
| update-dashboard | Weekdays 2 PM UTC | FRED, Alpha Vantage, EIA | `dashboard.json` |
| update-ski-news | Daily 11 AM UTC | RSS feeds | `ski-news.json` |
| update-airport-data | Monthly 15th, 1 PM UTC | BTS T-100 | `airport_passengers.json` |

### Required Secrets

| Workflow | Secrets |
|----------|---------|
| update-dashboard | `FRED_API_KEY`, `ALPHA_VANTAGE_KEY`, `EIA_API_KEY` |
| update-ski-news | `ANTHROPIC_API_KEY` |
| All others | None |

---

## Workflow Execution Order

Typical daily execution (all times UTC):

| Time | Workflow |
|------|----------|
| 06:00 | update-canadian-snow |
| 11:00 | update-ski-news |
| 11:00 | update-snow-cover |
| 14:00 | update-snotel |
| 14:00 | update-dashboard (weekdays only) |
| 18:00 | update-canadian-snow |
| 23:00 | update-snow-cover |

Monthly: `update-airport-data` (15th at 1 PM UTC)

---

## Workflow Details

### 1. update-snotel.yml
**Purpose**: Fetch SNOTEL snowpack data for Western US stations

**Script**: `fetch_snotel_data.py`

**Dependencies**: `requests`

**Output**: `static/data/snotel-snowpack.json`

**Quality Check**: Minimum 100 stations required

---

### 2. update-snow-cover.yml
**Purpose**: Fetch North American snow cover data and generate globe visualization

**Scripts**: `update_snow_cover.py`, `generate_snow_globe.py`

**Dependencies**: `requests`, `numpy`, `matplotlib`, `cartopy`

**Outputs**: `snow-cover.json`, `snow-globe.png`, `snow-globe.json`

**Quality Check**: Required fields: `usa`, `canada`, `combined`

---

### 3. update-canadian-snow.yml
**Purpose**: Consolidated Canadian snow data (replaces 3 separate workflows)

**Scripts**: `fetch_bc_sbi_data.py`, `fetch_alberta_snow_pillows.py`, `fetch_quebec_snow_data.py`

**Dependencies**: `requests`

**Outputs**: `bc-snow-basins.json`, `alberta-snow-pillows.json`, `quebec-snow-stations.json`

**Behavior**:
- Each source is fetched independently with `continue-on-error`
- Workflow only fails if ALL THREE sources fail
- Partial success commits available data

---

### 4. update-dashboard.yml
**Purpose**: Update economic dashboard with market data

**Script**: `update_dashboard.py`

**Dependencies**: `openpyxl`, `requests`

**Output**: `static/data/dashboard.json`

**Additional Triggers**: Also runs on push to `update_dashboard.py` or workflow file

---

### 5. update-ski-news.yml
**Purpose**: Aggregate ski industry news from RSS feeds

**Script**: `update_ski_news.py`

**Dependencies**: None (uses stdlib only)

**Outputs**: `ski-news.json`, `ski-news-review.json`

---

### 6. update-airport-data.yml
**Purpose**: Scrape airport passenger statistics

**Scripts**: `scrape_slc.py`, `generate_airport_output.py`

**Dependencies**: `pdfplumber`, `requests`

**Outputs**: `airport_passengers.json`, `slc-monthly.json`, `airport-monthly.json`

**Quality Check**: Minimum 1 airport required

---

## Standard Workflow Steps

All workflows follow this pattern:

1. **Checkout** - Get latest code
2. **Setup Python** - Python 3.11 (no pip cache)
3. **Install Dependencies** - pip install as needed
4. **Backup Previous Data** - Copy `.json` to `.backup.json`
5. **Fetch Data with Retry** - 3 attempts, 30s delay between
6. **Validate JSON** - Ensure valid JSON output
7. **Verify Data Quality** - Check minimum records/required fields
8. **Commit and Push** - If data changed
9. **Verify Hugo Build** - Run `hugo --minify` to catch build errors
10. **Create Issue on Failure** - Auto-create GitHub issue with logs link

---

## Manual Triggering

All workflows support manual triggering via GitHub UI or CLI:

```bash
# Trigger a workflow
gh workflow run update-snotel.yml
gh workflow run update-canadian-snow.yml
gh workflow run update-snow-cover.yml
gh workflow run update-dashboard.yml
gh workflow run update-ski-news.yml
gh workflow run update-airport-data.yml

# Check recent runs
gh run list --limit 10

# View specific run logs
gh run view <run-id> --log

# List recent failures
gh run list --status failure --limit 10
```

---

## Failure Handling

### Automatic Issue Creation

When a workflow fails, it automatically creates a GitHub issue with:
- Workflow name
- Run ID
- Timestamp
- Link to full logs

Issues are labeled `workflow-failure` for easy filtering.

### Common Failure Causes

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `[Errno 2] No such file` | Script not tracked in git | `git add <script.py>` |
| `JSONDecodeError` | Upstream API returned error page | Check source API status |
| `Timeout` | API slow/down | Retry logic handles this |
| `KeyError` in commit message | JSON schema changed | Update path in workflow |

---

## Monitoring

### Data Health Dashboard

Visit **[nixvir.com/data-status](https://nixvir.com/data-status)** for real-time feed health.

### CLI Monitoring

```bash
# Quick health check
gh run list --limit 10

# Failures in last 30 days
gh run list --status failure --limit 30

# Specific workflow history
gh run list --workflow=update-snotel.yml --limit 10
```

### Staleness Thresholds

| Data Feed | Expected | Warning | Stale |
|-----------|----------|---------|-------|
| Snow cover | 12h | 18h | 24h |
| Canadian snow | 12h | 18h | 24h |
| SNOTEL | 24h | 36h | 48h |
| Dashboard | 48h | 72h | 96h |
| Ski news | 24h | 36h | 48h |
| Airport data | 35 days | 45 days | 60 days |

---

## File Structure

```
.github/workflows/
├── update-snotel.yml          # Western US snowpack
├── update-snow-cover.yml      # North America snow cover
├── update-canadian-snow.yml   # BC, Alberta, Quebec snow
├── update-dashboard.yml       # Economic indicators
├── update-ski-news.yml        # Industry news
└── update-airport-data.yml    # Passenger statistics

static/data/
├── snotel-snowpack.json
├── snow-cover.json
├── bc-snow-basins.json
├── alberta-snow-pillows.json
├── quebec-snow-stations.json
├── dashboard.json
├── ski-news.json
├── ski-news-review.json
├── airport_passengers.json
├── slc-monthly.json
└── airport-monthly.json
```

---

## Backup Files

Backup files (`*.backup.json`) are:
- Created in GitHub Actions runner before each data update
- NOT committed to git (added to `.gitignore`)
- Only persist for the duration of the workflow run
- Useful for debugging if new data is malformed

---

## Hugo Build Verification

After each successful data commit, workflows:
1. Install Hugo 0.139.0 (extended version)
2. Run `hugo --minify`
3. Fail and create issue if build errors

This catches template errors or data incompatibilities before Netlify deploy.
