# Economic Dashboard Automation Setup

## Overview

Your Economic & Market Dashboard is now set up to automatically update daily with the latest economic indicators and market data.

## How It Works

### Data Sources (All Free!)

1. **Federal Reserve Economic Data (FRED)** - St. Louis Fed
   - Consumer Confidence (UMCSENT)
   - Fed Funds Rate (DFF)
   - Unemployment Rate (UNRATE)
   - Free API with generous rate limits

2. **Yahoo Finance** - Market data
   - S&P 500 (SPY, ^GSPC)
   - Dow Jones (^DJI)
   - VIX (^VIX)
   - No API key required!

3. **Bureau of Labor Statistics (BLS)**
   - CPI (Consumer Price Index)
   - Employment data
   - Average hourly wages
   - Public API, 25 requests/day limit

### Automation Schedule

**GitHub Actions runs automatically**:
- **Daily at 9 AM EST** (2 PM UTC)
- **Weekdays only** (Monday-Friday)
- **Manual trigger available** - Run anytime from GitHub Actions tab

## Setup Instructions

### Step 1: Get API Keys (Optional but Recommended)

#### FRED API Key (Recommended)
1. Visit: https://fred.stlouisfed.org/docs/api/api_key.html
2. Create free account
3. Request API key (instant)
4. Copy your API key

#### Alpha Vantage API Key (Optional)
Currently not required, but useful for backup market data:
1. Visit: https://www.alphavantage.co/support/#api-key
2. Get free API key
3. Copy your API key

### Step 2: Add API Keys to GitHub Secrets

1. Go to your GitHub repository: https://github.com/NixVir/NixVir.github.io

2. Click **Settings** → **Secrets and variables** → **Actions**

3. Click **New repository secret**

4. Add each secret:

   **Secret 1:**
   - Name: `FRED_API_KEY`
   - Value: [Your FRED API key]

   **Secret 2 (Optional):**
   - Name: `ALPHA_VANTAGE_KEY`
   - Value: [Your Alpha Vantage API key]

### Step 3: Enable GitHub Actions

1. Go to **Actions** tab in your GitHub repository

2. If prompted, click **"I understand my workflows, go ahead and enable them"**

3. You should see "Update Economic Dashboard" workflow

### Step 4: Test the Automation

#### Option A: Manual Trigger (Recommended)

1. Go to **Actions** tab
2. Click **"Update Economic Dashboard"** workflow
3. Click **"Run workflow"** dropdown
4. Click green **"Run workflow"** button
5. Wait 1-2 minutes for completion
6. Check the run results

#### Option B: Test Locally

```bash
# Install Python (if needed)
python --version  # Should be 3.7+

# Run the update script
python update_dashboard.py

# Check the output
cat static/data/dashboard.json
```

## Files Created

| File | Purpose |
|------|---------|
| `update_dashboard.py` | Python script to fetch latest data |
| `.github/workflows/update-dashboard.yml` | GitHub Actions automation |
| `DASHBOARD_AUTOMATION_SETUP.md` | This file - setup instructions |

## How Data Updates Work

```
┌─────────────────────────────────────┐
│  GitHub Actions (Daily 9 AM EST)   │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   update_dashboard.py runs          │
│   - Fetches FRED data               │
│   - Fetches Yahoo Finance data      │
│   - Fetches BLS data                │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  Updates dashboard.json             │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  Commits & pushes to GitHub         │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  Netlify auto-deploys website       │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  Dashboard shows latest data! 🎉    │
└─────────────────────────────────────┘
```

## Monitoring

### Check Last Update

Visit your dashboard: https://confident-jang-4183f9.netlify.app/dashboard/

The "Last updated" timestamp shows when data was last refreshed.

### View Automation Runs

1. Go to **Actions** tab in GitHub
2. Click on any workflow run to see details
3. View logs for debugging if needed

### Check for Errors

If automation fails:
1. Check **Actions** tab for error messages
2. Common issues:
   - API rate limits exceeded
   - Network timeout
   - API key invalid/missing
3. Re-run workflow manually after fixing

## Data Update Frequency

| Data Source | Update Frequency | Notes |
|-------------|------------------|-------|
| Market Data | Daily | Live during market hours |
| Consumer Confidence | Monthly | University of Michigan |
| Unemployment | Monthly | First Friday of month |
| CPI | Monthly | Mid-month |
| Fed Funds Rate | Changes during FOMC meetings | ~8 times/year |
| Employment | Monthly | First Friday of month |

## Customization

### Change Update Schedule

Edit `.github/workflows/update-dashboard.yml`:

```yaml
schedule:
  - cron: '0 14 * * 1-5'  # Daily at 2 PM UTC (9 AM EST)
```

Common schedules:
- `0 */6 * * *` - Every 6 hours
- `0 0 * * *` - Daily at midnight UTC
- `0 14 * * 1` - Weekly on Mondays at 2 PM UTC

### Add More Data Sources

Edit `update_dashboard.py`:

1. Find the data source API
2. Add fetch function
3. Add to `update_dashboard()` function
4. Update dashboard display in `content/dashboard.md`

## Troubleshooting

### "No changes to dashboard data"

**Cause**: Data hasn't changed since last run
**Solution**: Normal behavior, no action needed

### "API rate limit exceeded"

**Cause**: Too many requests to free API
**Solution**:
- Add API keys (increases limits)
- Reduce update frequency
- Use alternative data sources

### "Network timeout"

**Cause**: API slow to respond
**Solution**: Re-run workflow manually

### Dashboard shows old data

**Check**:
1. GitHub Actions ran successfully
2. Netlify deployed successfully
3. Browser cache (hard refresh: Ctrl+Shift+R)

## API Rate Limits

| Service | Limit | Solution |
|---------|-------|----------|
| FRED | 120 requests/60 seconds | Add API key for higher limits |
| Yahoo Finance | No official limit | Respectful usage recommended |
| BLS | 25 requests/day (no key) | Add API key for 500/day |

## Security Notes

- ✅ API keys stored as GitHub Secrets (encrypted)
- ✅ Never commit API keys to repository
- ✅ All data sources are free/public APIs
- ✅ No sensitive financial data stored

## Cost

**Total cost: $0/month** 🎉

All services are free with generous limits for this use case.

## Next Steps

1. ✅ Get FRED API key (5 minutes)
2. ✅ Add to GitHub Secrets (2 minutes)
3. ✅ Enable GitHub Actions (1 minute)
4. ✅ Test manual workflow run (2 minutes)
5. ✅ Wait for automatic daily updates!

## Support

**FRED API Documentation**: https://fred.stlouisfed.org/docs/api/
**GitHub Actions Documentation**: https://docs.github.com/en/actions
**BLS API Documentation**: https://www.bls.gov/developers/

---

**Status**: Ready to deploy! Just add API keys and enable Actions.
