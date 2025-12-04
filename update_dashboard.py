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

# API endpoints
FRED_API_KEY = os.environ.get('FRED_API_KEY', '')

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

    # 3. Fed Funds Rate
    print_safe("\nFetching Fed Funds Rate...")
    fed_rate = fetch_fred_data('DFF', limit=12)
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

    # 10. 10-Year Treasury Yield (Daily)
    print_safe("\nFetching 10-Year Treasury Yield...")
    treasury_data = fetch_fred_data('DGS10', limit=30)
    if treasury_data:
        dashboard_data['treasury_10y'] = treasury_data
        print_safe(f"  OK Latest: {treasury_data[-1]['value']}% ({len(treasury_data)} data points)")

    # 11. Currency Exchange Rates
    print_safe("\nFetching Currency Exchange Rates...")

    # USD/CAD
    usd_cad = fetch_fred_data('DEXCAUS', limit=30)
    if usd_cad:
        dashboard_data['usd_cad'] = usd_cad
        print_safe(f"  OK USD/CAD: {usd_cad[-1]['value']} ({len(usd_cad)} data points)")

    # USD/EUR
    usd_eur = fetch_fred_data('DEXUSEU', limit=30)
    if usd_eur:
        dashboard_data['usd_eur'] = usd_eur
        print_safe(f"  OK USD/EUR: {usd_eur[-1]['value']} ({len(usd_eur)} data points)")

    # USD/JPY
    usd_jpy = fetch_fred_data('DEXJPUS', limit=30)
    if usd_jpy:
        dashboard_data['usd_jpy'] = usd_jpy
        print_safe(f"  OK USD/JPY: {usd_jpy[-1]['value']} ({len(usd_jpy)} data points)")

    # USD/MXN
    usd_mxn = fetch_fred_data('DEXMXUS', limit=30)
    if usd_mxn:
        dashboard_data['usd_mxn'] = usd_mxn
        print_safe(f"  OK USD/MXN: {usd_mxn[-1]['value']} ({len(usd_mxn)} data points)")

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
