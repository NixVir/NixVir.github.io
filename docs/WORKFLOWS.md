# GitHub Actions Workflow Documentation

## Overview

NixVir uses 6 scheduled GitHub Actions workflows to automatically update data for the website. All workflows commit directly to the `master` branch, triggering Netlify auto-deploys.

**Recent Improvements** (Jan 2026):
- Removed pip caching to eliminate intermittent checkout failures
- Added JSON validation before all commits
- Added data quality sanity checks
- Added automatic GitHub issue creation on failures
- Added retry logic (3 attempts with 30s delay)
- Added data backups before overwrites
- Consolidated 3 Canadian snow workflows into 1

## Workflow Summary

| Workflow | Schedule | Data Source | Output File(s) | Secrets Required |
|----------|----------|-------------|----------------|------------------|
| update-snotel | Daily 2 PM UTC | NRCS AWDB | `snotel-snowpack.json` | None |
| update-snow-cover | 2x daily (11 AM, 11 PM UTC) | NOHRSC, NOAA IMS | `snow-cover.json`, `snow-globe.png` | None |
| **update-canadian-snow** | 2x daily (6 AM, 6 PM UTC) | BC/AB/QC sources | `bc-snow-basins.json`, `alberta-snow-pillows.json`, `quebec-snow-stations.json` | None |
| update-dashboard | Weekdays 2 PM UTC | FRED, Alpha Vantage, EIA | `dashboard.json` | FRED_API_KEY, ALPHA_VANTAGE_KEY, EIA_API_KEY |
| update-ski-news | Daily 11 AM UTC | RSS feeds | `ski-news.json` | ANTHROPIC_API_KEY |
| update-airport-data | Monthly 15th, 1 PM UTC | BTS T-100, SLC scraper | `airport_passengers.json` | None |

**Legacy workflows** (manual trigger only, schedules disabled):
- `update-bc-snowpack.yml` - Individual BC data fetch
- `update-alberta-snow.yml` - Individual Alberta data fetch
- `update-quebec-snow.yml` - Individual Quebec data fetch

## Detailed Workflow Analysis

### 1. update-snotel.yml
**Purpose**: Fetch SNOTEL snowpack data for Western US stations

**Schedule**: Daily at 2 PM UTC (6 AM PST)

**Python Script**: `fetch_snotel_data.py`

**Dependencies**: `requests`

**Output**: `static/data/snotel-snowpack.json`

**Commit Message Format**: `Update SNOTEL data - Mean: X% of normal (N stations)`

**Failure Modes**:
- Script not tracked in git (FIXED: 2026-01-21)
- NRCS API timeout or unavailability
- JSON path errors in commit message extraction

---

### 2. update-snow-cover.yml
**Purpose**: Fetch North American snow cover data and generate globe visualization

**Schedule**: Twice daily at 11 AM and 11 PM UTC

**Python Scripts**:
- `update_snow_cover.py`
- `generate_snow_globe.py`

**Dependencies**: `requests`, `numpy`, `matplotlib`, `cartopy`

**Outputs**:
- `static/data/snow-cover.json`
- `static/images/snow-globe.png`
- `static/images/snow-globe.json`

**Commit Message Format**: `Update snow cover data & globe - Combined: X%, USA: Y%, Canada: Z% (YYYY-MM-DD)`

**Failure Modes**:
- Pip cache lookup failures (intermittent - no requirements.txt found)
- Cartopy/matplotlib rendering issues
- NOHRSC or IMS data source unavailability
- Heavy dependencies (cartopy) cause longer install times

**Recent Failures**: Jan 13-15, 19-20 (intermittent)

---

### 3. update-bc-snowpack.yml
**Purpose**: Fetch BC Snow Basin Index data

**Schedule**: Daily at 12 PM UTC (4 AM PST)

**Python Script**: `fetch_bc_sbi_data.py`

**Dependencies**: `requests`

**Output**: `static/data/bc-snow-basins.json`

**Commit Message Format**: `Update BC snowpack data - Mean SBI: X% (N basins)`

**Failure Modes**:
- BC government API changes or unavailability
- SSL certificate issues with gov.bc.ca endpoints

---

### 4. update-alberta-snow.yml
**Purpose**: Fetch Alberta snow pillow data

**Schedule**: Twice daily at 2 PM and 10 PM UTC

**Python Script**: `fetch_alberta_snow_pillows.py`

**Dependencies**: `requests`

**Output**: `static/data/alberta-snow-pillows.json`

**Commit Message Format**: `Update Alberta snow data - Mean SWE: Xmm (N stations)`

**Failure Modes**:
- Alberta rivers.alberta.ca API changes
- JSON schema changes in source data

---

### 5. update-quebec-snow.yml
**Purpose**: Fetch Hydro-Québec snow station data

**Schedule**: Twice daily at 6 AM and 6 PM UTC

**Python Script**: `fetch_quebec_snow_data.py`

**Dependencies**: `requests`

**Output**: `static/data/quebec-snow-stations.json`

**Commit Message Format**: `Update Quebec snow data - Mean SWE: Xmm (N stations)`

**Failure Modes**:
- Hydro-Québec API changes
- French/English encoding issues

---

### 6. update-dashboard.yml
**Purpose**: Update economic dashboard with market data

**Schedule**: Weekdays at 2 PM UTC (9 AM EST, after market open)

**Python Script**: `update_dashboard.py`

**Dependencies**: `openpyxl`

**Output**: `static/data/dashboard.json`

**Required Secrets**:
- `FRED_API_KEY` - Federal Reserve Economic Data
- `ALPHA_VANTAGE_KEY` - Stock market data
- `EIA_API_KEY` - Energy Information Administration

**Commit Message Format**: `Update dashboard data - YYYY-MM-DD`

**Failure Modes**:
- Missing or expired API keys
- API rate limits exceeded
- Market holidays (no new data, but won't fail)

**Additional Triggers**: Also runs on push to `update_dashboard.py` or workflow file

**Recent Failures**: Jan 19-20 (3 consecutive)

---

### 7. update-ski-news.yml
**Purpose**: Aggregate and filter ski industry news from RSS feeds

**Schedule**: Daily at 11 AM UTC (6 AM EST)

**Python Script**: `update_ski_news.py`

**Dependencies**: None specified in workflow (uses feedparser, beautifulsoup4, requests)

**Required Secrets**:
- `ANTHROPIC_API_KEY` - For AI-powered news filtering/summarization

**Outputs**:
- `static/data/ski-news.json`
- `static/data/ski-news-review.json`

**Commit Message Format**: `Update ski news - YYYY-MM-DD HH:MM`

**Failure Modes**:
- Missing ANTHROPIC_API_KEY
- API rate limits or service outages
- RSS feed format changes
- Missing dependencies (not installing feedparser/beautifulsoup4)

**Recent Failures**: Jan 19-20

---

### 8. update-airport-data.yml
**Purpose**: Scrape airport passenger statistics

**Schedule**: Monthly on the 15th at 1 PM UTC

**Python Scripts**:
- `scrape_slc.py` (with `|| echo` fallback for partial failures)
- `generate_airport_output.py`

**Dependencies**: `pdfplumber`, `requests`

**Outputs**:
- `static/data/airport_passengers.json`
- `static/data/slc-monthly.json`
- `static/data/airport-monthly.json`

**Commit Message Format**: `Update airport passenger data - N airports, latest: YYYY-MM`

**Failure Modes**:
- PDF format changes on airport websites
- SLC scraper has explicit failure tolerance (`|| echo`)
- BTS T-100 data lag (2-3 months behind)

---

## Common Issues Identified

### 1. Missing Script Files
**Problem**: Python scripts not tracked in git cause `[Errno 2] No such file or directory`

**Affected Files** (currently untracked but potentially needed):
- `fetch_bc_snow_data.py` (vs tracked `fetch_bc_sbi_data.py`)
- `backfill_*.py` scripts
- `scrape_jac.py`
- `optimize_images.py`

**Solution**: Ensure all scripts referenced in workflows are committed to git

### 2. Dependency Installation Issues
**Problem**: `cache: 'pip'` option fails when requirements.txt not found during checkout

**Solution Options**:
- Remove `cache: 'pip'` from workflows
- Ensure requirements.txt is always committed
- Add explicit `pip cache` step after checkout succeeds

### 3. Missing Dependencies in Workflows
**Problem**: Some workflows don't install all required packages

**Examples**:
- `update-ski-news.yml` doesn't install `feedparser` or `beautifulsoup4`
- Dependencies listed in `requirements.txt` but not used by pip install step

### 4. No Error Notifications
**Problem**: Workflow failures are silent - no alerts sent

**Solution**: Add Slack/Discord/email notification step on failure

### 5. No JSON Validation
**Problem**: Corrupt JSON can be committed and break the website

**Solution**: Add JSON schema validation step before commit

### 6. No Rollback Mechanism
**Problem**: Bad data commits can only be fixed by manual revert

**Solution**:
- Keep previous version as backup before overwriting
- Add sanity checks (e.g., file size, required fields present)

---

## Recommended Improvements

### High Priority (Risk Reduction)
1. **Add JSON validation** before each commit
2. **Add notification** on workflow failures
3. **Verify all referenced scripts** are tracked in git
4. **Install all dependencies** explicitly in each workflow

### Medium Priority (Reliability)
5. **Add retry logic** for transient API failures
6. **Remove pip cache** to avoid intermittent failures
7. **Add data sanity checks** (min records, required fields)

### Low Priority (Optimization)
8. **Consolidate Canadian snow workflows** into single workflow
9. **Add manual re-run documentation**
10. **Create requirements-{workflow}.txt** files for explicit dependencies

---

## Workflow Execution Order

Typical daily execution (all times UTC):

| Time | Workflow |
|------|----------|
| 06:00 | update-quebec-snow |
| 11:00 | update-ski-news |
| 11:00 | update-snow-cover |
| 12:00 | update-bc-snowpack |
| 14:00 | update-snotel |
| 14:00 | update-dashboard (weekdays) |
| 14:00 | update-alberta-snow |
| 18:00 | update-quebec-snow |
| 22:00 | update-alberta-snow |
| 23:00 | update-snow-cover |

Monthly: `update-airport-data` (15th)

---

## Manual Triggering

All workflows support `workflow_dispatch` for manual triggering:

```bash
gh workflow run update-snotel.yml
gh workflow run update-snow-cover.yml
gh workflow run update-bc-snowpack.yml
gh workflow run update-alberta-snow.yml
gh workflow run update-quebec-snow.yml
gh workflow run update-dashboard.yml
gh workflow run update-ski-news.yml
gh workflow run update-airport-data.yml
```

Check status:
```bash
gh run list --limit 10
gh run view <run-id> --log
```

---

## Implementation Roadmap

### Phase 1: Quick Wins (High Impact, Low Effort)

#### 1.1 Remove Pip Caching
The `cache: 'pip'` option causes intermittent failures when `requirements.txt` isn't found during checkout timing issues.

**Change in all workflow files:**
```yaml
# Before
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'

# After
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'
```

**Affected files**: All 8 workflow YAMLs

#### 1.2 Add JSON Validation Step
Add validation before committing JSON files to catch corruption early.

**Add this step before "Commit and push":**
```yaml
- name: Validate JSON output
  run: |
    python -c "import json; json.load(open('static/data/OUTPUT_FILE.json'))"
```

### Phase 2: Error Visibility (Medium Effort)

#### 2.1 Add Failure Notifications
Create a reusable notification step for workflow failures.

**Option A: GitHub Issues** (No external services needed)
```yaml
- name: Create issue on failure
  if: failure()
  uses: actions/github-script@v7
  with:
    script: |
      const title = `Workflow Failed: ${{ github.workflow }}`;
      const body = `**Run ID**: ${{ github.run_id }}\n**Time**: ${new Date().toISOString()}\n**Logs**: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}`;
      await github.rest.issues.create({
        owner: context.repo.owner,
        repo: context.repo.repo,
        title: title,
        body: body,
        labels: ['workflow-failure']
      });
```

**Option B: Email via GitHub Actions** (Requires email setup)

#### 2.2 Add Data Sanity Checks
Verify output files have reasonable content before committing.

```yaml
- name: Verify data quality
  run: |
    # Check file exists and has content
    test -s static/data/snotel-snowpack.json || exit 1

    # Check minimum record count
    COUNT=$(python -c "import json; d=json.load(open('static/data/snotel-snowpack.json')); print(len(d.get('stations', [])))")
    if [ "$COUNT" -lt 100 ]; then
      echo "ERROR: Only $COUNT stations found (expected 700+)"
      exit 1
    fi
```

### Phase 3: Consolidation (Medium Effort)

#### 3.1 Combine Canadian Snow Workflows
BC, Alberta, and Quebec workflows could be combined into a single `update-canadian-snow.yml`:

**Benefits**:
- Single failure notification for all Canadian data
- Coordinated commit with all Canadian updates
- Reduced workflow maintenance

**Implementation**: Create new workflow that calls all 3 scripts sequentially

### Phase 4: Robustness (Higher Effort)

#### 4.1 Add Retry Logic for API Calls
Wrap critical Python scripts with retry capability:

```yaml
- name: Fetch data with retry
  run: |
    for i in 1 2 3; do
      python fetch_snotel_data.py && break
      echo "Attempt $i failed, retrying in 30s..."
      sleep 30
    done
```

#### 4.2 Backup Previous Data
Keep a backup of the previous version before overwriting:

```yaml
- name: Backup previous data
  run: |
    if [ -f static/data/snotel-snowpack.json ]; then
      cp static/data/snotel-snowpack.json static/data/snotel-snowpack.backup.json
    fi
```

---

## Failure History Analysis

Based on recent run history:

| Workflow | Failures (Last 30 Days) | Primary Cause |
|----------|------------------------|---------------|
| update-snow-cover | 6 | Pip cache timing issues |
| update-dashboard | 3 | API key/rate limit issues |
| update-ski-news | 2 | Unknown (needs investigation) |
| update-snotel | 1 | Script not in git (FIXED) |
| update-bc-snowpack | 1 | Unknown |
| Others | 0 | Stable |

**Pattern**: Failures clustered on Jan 19-20 suggest possible GitHub Actions infrastructure issue or coordinated API outages.

---

## Monitoring Checklist

Daily:
- [ ] Check `gh run list --limit 10` for failures
- [ ] Verify Netlify deploy succeeded

Weekly:
- [ ] Review `gh run list --status failure --limit 20`
- [ ] Check data file timestamps are recent

Monthly:
- [ ] Review API usage/limits for FRED, Alpha Vantage, EIA
- [ ] Verify ANTHROPIC_API_KEY is valid
