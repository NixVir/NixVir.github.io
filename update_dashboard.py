#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated Economic Dashboard Data Updater
Fetches latest economic indicators and market data from public APIs
"""
import json
import os
import sys
from datetime import datetime, timedelta
import urllib.request
import urllib.error
import time
import tempfile

# API endpoints
# Check environment variable first, then fall back to local config file
FRED_API_KEY = os.environ.get('FRED_API_KEY', '')
EIA_API_KEY = os.environ.get('EIA_API_KEY', '')

# Try reading from local config file (for local development)
config_path = os.path.join(os.path.dirname(__file__), '.api_keys')
if os.path.exists(config_path):
    with open(config_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith('FRED_API_KEY=') and not FRED_API_KEY:
                FRED_API_KEY = line.split('=', 1)[1].strip()
            elif line.startswith('EIA_API_KEY=') and not EIA_API_KEY:
                EIA_API_KEY = line.split('=', 1)[1].strip()

def print_safe(msg):
    """Print with safe encoding for Windows"""
    try:
        print(msg)
    except:
        print(msg.encode('ascii', 'replace').decode('ascii'))

def fetch_json(url, error_msg="Error fetching data"):
    """Fetch JSON data from URL with error handling"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print_safe(f"{error_msg}: HTTP {e.code}")
        return None
    except Exception as e:
        print_safe(f"{error_msg}: {e}")
        return None

def fetch_gold_price():
    """Fetch daily gold prices from FreeGoldAPI.com (USD per troy ounce)"""
    url = "https://freegoldapi.com/data/latest.json"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())

        # Get the most recent ~260 trading days of data
        # Data is already sorted by date ascending
        recent_data = data[-260:] if len(data) > 260 else data

        # Convert to our format
        gold_prices = []
        for record in recent_data:
            if 'date' in record and 'price' in record:
                try:
                    gold_prices.append({
                        'date': record['date'],
                        'value': float(record['price'])
                    })
                except (ValueError, TypeError):
                    continue

        return gold_prices
    except Exception as e:
        print_safe(f"Error fetching gold price: {e}")
        return None

def fetch_fred_data(series_id, limit=12):
    """Fetch data from Federal Reserve Economic Data (FRED)"""
    if not FRED_API_KEY:
        print_safe(f"  ! Skipping {series_id} - No FRED API key")
        return []

    url = f"https://api.stlouisfed.org/fred/series/observations"
    params = f"?series_id={series_id}&api_key={FRED_API_KEY}&file_type=json&sort_order=desc&limit={limit}"

    data = fetch_json(url + params, f"Error fetching {series_id}")
    if not data or 'observations' not in data:
        return []

    observations = []
    for obs in reversed(data['observations']):
        if obs['value'] != '.':
            observations.append({
                'date': obs['date'],
                'series_id': series_id,
                'value': float(obs['value']),
                'realtime_start': obs['realtime_start'],
                'realtime_end': obs['realtime_end']
            })

    return observations

def fetch_eia_electricity(state_id, sector='ALL', limit=24):
    """
    Fetch electricity retail price data from EIA API v2

    Args:
        state_id: Two-letter state code (e.g., 'CO', 'VT', 'CA') or 'US' for national
        sector: 'RES' (residential), 'COM' (commercial), 'IND' (industrial), 'ALL' (total)
        limit: Number of monthly observations to fetch

    Returns:
        List of {date, value} dicts with price in cents/kWh
    """
    if not EIA_API_KEY:
        print_safe(f"  ! Skipping EIA {state_id} - No EIA API key")
        return []

    # EIA API v2 endpoint for electricity retail sales
    base_url = "https://api.eia.gov/v2/electricity/retail-sales/data/"

    # Build query parameters
    params = {
        'api_key': EIA_API_KEY,
        'frequency': 'monthly',
        'data[0]': 'price',  # Average retail price (cents/kWh)
        'facets[stateid][]': state_id,
        'facets[sectorid][]': sector,
        'sort[0][column]': 'period',
        'sort[0][direction]': 'desc',
        'length': str(limit)
    }

    # Build URL with parameters
    param_str = '&'.join(f"{k}={v}" for k, v in params.items())
    url = f"{base_url}?{param_str}"

    data = fetch_json(url, f"Error fetching EIA {state_id}")
    if not data or 'response' not in data or 'data' not in data['response']:
        return []

    observations = []
    for record in reversed(data['response']['data']):
        if record.get('price') is not None:
            # Convert period (YYYY-MM) to date format (YYYY-MM-01)
            period = record.get('period', '')
            if len(period) == 7:  # YYYY-MM format
                date_str = f"{period}-01"
            else:
                date_str = period

            observations.append({
                'date': date_str,
                'value': float(record['price']),  # Already in cents/kWh
                'state': record.get('stateid', state_id),
                'sector': record.get('sectorid', sector)
            })

    return observations

def fetch_news_sentiment():
    """Fetch Daily News Sentiment Index from SF Fed Excel file"""
    # The URL pattern includes a cache-busting date parameter
    url = "https://www.frbsf.org/wp-content/uploads/news_sentiment_data.xlsx"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as response:
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                tmp.write(response.read())
                tmp_path = tmp.name

        # Try to parse Excel file using openpyxl
        try:
            from openpyxl import load_workbook
            wb = load_workbook(tmp_path, read_only=True, data_only=True)
            ws = wb.active

            # Read data - typically date in column A, sentiment in column B
            observations = []
            for row in ws.iter_rows(min_row=2, values_only=True):  # Skip header
                if row[0] is None:
                    continue
                date_val = row[0]
                sentiment_val = row[1] if len(row) > 1 else None

                if sentiment_val is None:
                    continue

                # Handle date formatting
                if hasattr(date_val, 'strftime'):
                    date_str = date_val.strftime('%Y-%m-%d')
                else:
                    date_str = str(date_val)

                try:
                    observations.append({
                        'date': date_str,
                        'value': float(sentiment_val)
                    })
                except (ValueError, TypeError):
                    continue

            wb.close()
            os.unlink(tmp_path)

            # Return last 365 days of data for sparkline
            if observations:
                # Sort by date and get recent data
                observations.sort(key=lambda x: x['date'])
                return observations[-365:]
            return []

        except ImportError:
            print_safe("  ! openpyxl not installed, skipping News Sentiment")
            os.unlink(tmp_path)
            return []

    except Exception as e:
        print_safe(f"  ! News Sentiment unavailable: {e}")
        return []


def fetch_market_data_yahoo(symbol, historical=False):
    """Fetch market data from Yahoo Finance"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 if historical else 7)

    period1 = int(start_date.timestamp())
    period2 = int(end_date.timestamp())

    url = f"https://query1.finance.yahoo.com/v7/finance/download/{symbol}"
    url += f"?period1={period1}&period2={period2}&interval=1d&events=history"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            csv_data = response.read().decode('utf-8')
            lines = csv_data.strip().split('\n')

            if len(lines) < 2:
                return None

            if historical:
                # Return all data points for sparkline
                history = []
                for line in lines[1:]:  # Skip header
                    parts = line.split(',')
                    if len(parts) >= 7:
                        try:
                            history.append({
                                'date': parts[0],
                                'close': float(parts[4])
                            })
                        except:
                            continue
                return {
                    'symbol': symbol,
                    'current_date': history[-1]['date'] if history else None,
                    'current_close': history[-1]['close'] if history else None,
                    'history': history
                }
            else:
                # Just return latest value
                last_line = lines[-1].split(',')
                return {
                    'symbol': symbol,
                    'date': last_line[0],
                    'close': float(last_line[4]),
                    'volume': int(float(last_line[6])) if last_line[6] != 'null' else 0
                }
    except Exception as e:
        print_safe(f"  ! {symbol} unavailable")
        return None

def update_dashboard():
    """Main function to update dashboard data"""
    print_safe("Starting dashboard update...")
    print_safe(f"Timestamp: {datetime.now().isoformat()}")

    dashboard_data = {
        'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # 1. Consumer Confidence
    print_safe("\nFetching Consumer Confidence...")
    consumer_confidence = fetch_fred_data('UMCSENT', limit=12)
    if consumer_confidence:
        dashboard_data['consumer_confidence'] = consumer_confidence
        print_safe(f"  OK Latest: {consumer_confidence[-1]['value']} ({consumer_confidence[-1]['date']})")

    # 2. Market Data - Using FRED S&P 500 Index
    print_safe("\nFetching Market Data (S&P 500 from FRED)...")
    sp500_data = fetch_fred_data('SP500', limit=12)
    if sp500_data:
        # Format to match expected structure
        markets = [{
            'symbol': 'SPY',
            'current_date': sp500_data[-1]['date'],
            'current_close': sp500_data[-1]['value'],
            'history': [{'date': d['date'], 'close': d['value']} for d in sp500_data]
        }]
        dashboard_data['markets'] = markets
        print_safe(f"  OK S&P 500: {sp500_data[-1]['value']:.2f} ({len(sp500_data)} data points)")

    # 2b. Dow Jones Industrial Average (Daily - fetch ~1 year of trading days)
    print_safe("\nFetching Dow Jones Industrial Average...")
    djia_data = fetch_fred_data('DJIA', limit=260)
    if djia_data:
        dashboard_data['djia'] = djia_data
        print_safe(f"  OK DJIA: {djia_data[-1]['value']:.2f} ({len(djia_data)} data points)")

    # 2c. NASDAQ Composite Index (Daily - fetch ~1 year of trading days)
    print_safe("\nFetching NASDAQ Composite Index...")
    nasdaq_data = fetch_fred_data('NASDAQCOM', limit=260)
    if nasdaq_data:
        dashboard_data['nasdaq'] = nasdaq_data
        print_safe(f"  OK NASDAQ: {nasdaq_data[-1]['value']:.2f} ({len(nasdaq_data)} data points)")

    # 2d. Hotel & Lodging REITs - use FRED NASDAQ REIT Index
    # NASDAQNQUSB351020 = Nasdaq US Benchmark Real Estate Investment Trusts Index
    print_safe("\nFetching Hotel & Lodging REITs (Nasdaq REIT Index)...")
    reit_data = fetch_fred_data('NASDAQNQUSB351020', limit=260)
    if reit_data:
        dashboard_data['hotel_reits'] = reit_data
        print_safe(f"  OK REITs: {reit_data[-1]['value']:.2f} ({len(reit_data)} data points)")

    # 2e. VIX Volatility Index (Daily - fetch ~1 year of trading days)
    print_safe("\nFetching VIX Volatility Index...")
    vix_data = fetch_fred_data('VIXCLS', limit=260)
    if vix_data:
        dashboard_data['vix'] = vix_data
        print_safe(f"  OK VIX: {vix_data[-1]['value']:.2f} ({len(vix_data)} data points)")

    # 3. Fed Funds Rate (Daily - fetch ~1 year of trading days)
    print_safe("\nFetching Fed Funds Rate...")
    fed_rate = fetch_fred_data('DFF', limit=260)
    if fed_rate:
        dashboard_data['fed_funds_rate'] = fed_rate
        print_safe(f"  OK Latest: {fed_rate[-1]['value']}% ({len(fed_rate)} data points)")

    # 4. Unemployment Rate
    print_safe("\nFetching Unemployment Rate...")
    unemployment = fetch_fred_data('UNRATE', limit=12)
    if unemployment:
        dashboard_data['unemployment'] = unemployment
        print_safe(f"  OK Latest: {unemployment[-1]['value']}% ({len(unemployment)} data points)")

    # 5. CPI (Consumer Price Index)
    print_safe("\nFetching CPI...")
    cpi_data = fetch_fred_data('CPIAUCSL', limit=12)
    if cpi_data:
        dashboard_data['cpi'] = cpi_data
        print_safe(f"  OK Latest: {cpi_data[-1]['value']} ({len(cpi_data)} data points)")

    # 6. Employment (Total Nonfarm Payroll)
    print_safe("\nFetching Employment...")
    employment_data = fetch_fred_data('PAYEMS', limit=12)
    if employment_data:
        dashboard_data['employment'] = employment_data
        print_safe(f"  OK Latest: {employment_data[-1]['value']} thousand ({len(employment_data)} data points)")

    # 7. Average Hourly Earnings (Wages)
    print_safe("\nFetching Wages...")
    wages_data = fetch_fred_data('CES0500000003', limit=12)
    if wages_data:
        dashboard_data['wages'] = wages_data
        print_safe(f"  OK Latest: ${wages_data[-1]['value']} ({len(wages_data)} data points)")

    # 8. GDP (Quarterly)
    print_safe("\nFetching GDP...")
    gdp_data = fetch_fred_data('GDP', limit=12)
    if gdp_data:
        dashboard_data['gdp'] = gdp_data
        print_safe(f"  OK Latest: ${gdp_data[-1]['value']} billion ({len(gdp_data)} data points)")

    # 9. Housing Starts (Monthly)
    print_safe("\nFetching Housing Starts...")
    housing_data = fetch_fred_data('HOUST', limit=12)
    if housing_data:
        dashboard_data['housing_starts'] = housing_data
        print_safe(f"  OK Latest: {housing_data[-1]['value']} thousand units ({len(housing_data)} data points)")

    # 9b. Bankruptcy Activity (PPI - Producer Price Index for Bankruptcy Legal Services)
    # PCU541110541110903 = PPI for Offices of Lawyers: Bankruptcy and Other Business Legal Services
    print_safe("\nFetching Bankruptcy Activity (PPI)...")
    bankruptcy_data = fetch_fred_data('PCU541110541110903', limit=12)
    if bankruptcy_data:
        dashboard_data['bankruptcy_ppi'] = bankruptcy_data
        print_safe(f"  OK Latest: {bankruptcy_data[-1]['value']} ({len(bankruptcy_data)} data points)")

    # =========================================================================
    # ELECTRICITY PRICING INDICATORS (Ski Region Focus)
    # Using EIA API for state-level data (cents/kWh, commercial sector)
    # =========================================================================

    print_safe("\n--- Electricity Pricing (EIA State-Level, Commercial Sector) ---")

    # Key ski states with their regions:
    # - Colorado (CO): Rockies
    # - Utah (UT): Rockies/Wasatch
    # - California (CA): Tahoe/Mammoth
    # - Vermont (VT): New England
    # - New Hampshire (NH): New England
    # - Washington (WA): Pacific Northwest
    # - Wyoming (WY): Jackson Hole

    ski_states = [
        ('US', 'U.S. Average'),
        ('CO', 'Colorado'),
        ('UT', 'Utah'),
        ('CA', 'California'),
        ('VT', 'Vermont'),
        ('NH', 'New Hampshire'),
        ('WA', 'Washington'),
        ('WY', 'Wyoming'),
    ]

    for state_id, state_name in ski_states:
        print_safe(f"\nFetching {state_name} Electricity (Commercial)...")
        # Use commercial sector (COM) - most relevant for ski operations
        elec_data = fetch_eia_electricity(state_id, sector='COM', limit=24)
        if elec_data:
            key = f'electricity_{state_id.lower()}'
            dashboard_data[key] = elec_data
            # EIA returns cents/kWh, display as such
            print_safe(f"  OK {state_id}: {elec_data[-1]['value']:.2f} cents/kWh ({len(elec_data)} data points)")
        else:
            print_safe(f"  ! {state_id}: No data available")

    # 10. 10-Year Treasury Yield (Daily - fetch ~1 year of trading days)
    print_safe("\nFetching 10-Year Treasury Yield...")
    treasury_data = fetch_fred_data('DGS10', limit=260)
    if treasury_data:
        dashboard_data['treasury_10y'] = treasury_data
        print_safe(f"  OK Latest: {treasury_data[-1]['value']}% ({len(treasury_data)} data points)")

    # 11. Currency Exchange Rates (Daily - fetch ~1 year of trading days)
    # All rates stored as "units of foreign currency per 1 USD" so UP = stronger USD
    print_safe("\nFetching Currency Exchange Rates...")

    # USD/CAD (Canadian Dollars per USD) - DEXCAUS is CAD per USD, so up = stronger USD
    usd_cad = fetch_fred_data('DEXCAUS', limit=260)
    if usd_cad:
        dashboard_data['usd_cad'] = usd_cad
        print_safe(f"  OK USD/CAD: {usd_cad[-1]['value']} ({len(usd_cad)} data points)")

    # EUR/USD - DEXUSEU is USD per EUR, need to INVERT so up = stronger USD
    eur_usd_raw = fetch_fred_data('DEXUSEU', limit=260)
    if eur_usd_raw:
        # Invert: store as EUR per USD (1/rate)
        usd_eur = [{
            'date': d['date'],
            'value': round(1.0 / d['value'], 4) if d['value'] != 0 else 0
        } for d in eur_usd_raw]
        dashboard_data['usd_eur'] = usd_eur
        print_safe(f"  OK USD/EUR: {usd_eur[-1]['value']} ({len(usd_eur)} data points) [inverted]")

    # USD/JPY (Yen per USD) - DEXJPUS is JPY per USD, so up = stronger USD
    usd_jpy = fetch_fred_data('DEXJPUS', limit=260)
    if usd_jpy:
        dashboard_data['usd_jpy'] = usd_jpy
        print_safe(f"  OK USD/JPY: {usd_jpy[-1]['value']} ({len(usd_jpy)} data points)")

    # USD/MXN (Pesos per USD) - DEXMXUS is MXN per USD, so up = stronger USD
    usd_mxn = fetch_fred_data('DEXMXUS', limit=260)
    if usd_mxn:
        dashboard_data['usd_mxn'] = usd_mxn
        print_safe(f"  OK USD/MXN: {usd_mxn[-1]['value']} ({len(usd_mxn)} data points)")

    # USD/GBP - DEXUSUK is USD per GBP, need to INVERT so up = stronger USD
    gbp_usd_raw = fetch_fred_data('DEXUSUK', limit=260)
    if gbp_usd_raw:
        # Invert: store as GBP per USD (1/rate)
        usd_gbp = [{
            'date': d['date'],
            'value': round(1.0 / d['value'], 4) if d['value'] != 0 else 0
        } for d in gbp_usd_raw]
        dashboard_data['usd_gbp'] = usd_gbp
        print_safe(f"  OK USD/GBP: {usd_gbp[-1]['value']} ({len(usd_gbp)} data points) [inverted]")

    # USD/AUD - DEXUSAL is USD per AUD, need to INVERT so up = stronger USD
    aud_usd_raw = fetch_fred_data('DEXUSAL', limit=260)
    if aud_usd_raw:
        # Invert: store as AUD per USD (1/rate)
        usd_aud = [{
            'date': d['date'],
            'value': round(1.0 / d['value'], 4) if d['value'] != 0 else 0
        } for d in aud_usd_raw]
        dashboard_data['usd_aud'] = usd_aud
        print_safe(f"  OK USD/AUD: {usd_aud[-1]['value']} ({len(usd_aud)} data points) [inverted]")

    # USD/CNY (Yuan per USD) - DEXCHUS is CNY per USD, so up = stronger USD
    usd_cny = fetch_fred_data('DEXCHUS', limit=260)
    if usd_cny:
        dashboard_data['usd_cny'] = usd_cny
        print_safe(f"  OK USD/CNY: {usd_cny[-1]['value']} ({len(usd_cny)} data points)")

    # USD/INR (Rupees per USD) - DEXINUS is INR per USD, so up = stronger USD
    usd_inr = fetch_fred_data('DEXINUS', limit=260)
    if usd_inr:
        dashboard_data['usd_inr'] = usd_inr
        print_safe(f"  OK USD/INR: {usd_inr[-1]['value']} ({len(usd_inr)} data points)")

    # USD/RUB (Russian Rubles per USD) - Monthly OECD data (no daily FRED series available)
    usd_rub = fetch_fred_data('CCUSMA02RUM618N', limit=24)  # Monthly, last 2 years
    if usd_rub:
        dashboard_data['usd_rub'] = usd_rub
        print_safe(f"  OK USD/RUB: {usd_rub[-1]['value']} ({len(usd_rub)} data points) [monthly]")

    # Fed Trade-Weighted Dollar Index (Broad) - DTWEXBGS
    # Measures USD against 26 major trading partners, weighted by trade volume
    # More representative than DXY for actual trade relationships
    print_safe("\nFetching Dollar Strength Indices...")
    trade_weighted = fetch_fred_data('DTWEXBGS', limit=260)
    if trade_weighted:
        dashboard_data['trade_weighted_usd'] = trade_weighted
        print_safe(f"  OK Trade-Weighted USD: {trade_weighted[-1]['value']} ({len(trade_weighted)} data points)")

    # Real Trade-Weighted Dollar Index (inflation-adjusted)
    real_trade_weighted = fetch_fred_data('RTWEXBGS', limit=260)
    if real_trade_weighted:
        dashboard_data['real_trade_weighted_usd'] = real_trade_weighted
        print_safe(f"  OK Real Trade-Weighted USD: {real_trade_weighted[-1]['value']} ({len(real_trade_weighted)} data points)")

    # 12. Commodities (Daily prices)
    print_safe("\nFetching Commodity Prices...")

    # Gold Price (USD per troy ounce) from FreeGoldAPI.com
    # FRED discontinued LBMA gold prices in Jan 2022, using free alternative API
    gold_data = fetch_gold_price()
    if gold_data:
        dashboard_data['gold'] = gold_data
        print_safe(f"  OK Gold: ${gold_data[-1]['value']:.2f}/oz ({len(gold_data)} data points)")
    else:
        print_safe("  ! Gold data unavailable")

    # Crude Oil WTI (USD per barrel)
    oil_data = fetch_fred_data('DCOILWTICO', limit=260)
    if oil_data:
        dashboard_data['crude_oil'] = oil_data
        print_safe(f"  OK Crude Oil WTI: ${oil_data[-1]['value']:.2f}/bbl ({len(oil_data)} data points)")

    # Natural Gas Henry Hub (USD per MMBtu)
    natgas_data = fetch_fred_data('DHHNGSP', limit=260)
    if natgas_data:
        dashboard_data['natural_gas'] = natgas_data
        print_safe(f"  OK Natural Gas: ${natgas_data[-1]['value']:.2f}/MMBtu ({len(natgas_data)} data points)")

    # Copper Price - FRED PCOPPUSDM is USD per metric ton, convert to USD per pound
    # 1 metric ton = 2204.62 pounds
    copper_data_raw = fetch_fred_data('PCOPPUSDM', limit=12)  # Monthly data
    if copper_data_raw:
        # Convert from USD/metric ton to USD/lb
        copper_data = [{
            'date': d['date'],
            'value': round(d['value'] / 2204.62, 2)
        } for d in copper_data_raw]
        dashboard_data['copper'] = copper_data
        print_safe(f"  OK Copper: ${copper_data[-1]['value']:.2f}/lb ({len(copper_data)} data points)")

    # 13. Daily News Sentiment Index (from SF Fed - updates weekly)
    print_safe("\nFetching News Sentiment Index...")
    news_sentiment = fetch_news_sentiment()
    if news_sentiment:
        dashboard_data['news_sentiment'] = news_sentiment
        print_safe(f"  OK Latest: {news_sentiment[-1]['value']:.3f} ({news_sentiment[-1]['date']}) ({len(news_sentiment)} data points)")

    # Write to file
    output_path = 'static/data/dashboard.json'
    print_safe(f"\nWriting data to {output_path}...")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(dashboard_data, f, indent=2)

    print_safe("\nOK Dashboard update complete!")
    print_safe(f"Updated {len([k for k in dashboard_data.keys() if k != 'updated'])} categories")

    return dashboard_data

if __name__ == '__main__':
    try:
        update_dashboard()
    except Exception as e:
        print_safe(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
