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

def fetch_market_data_yahoo(symbol):
    """Fetch market data from Yahoo Finance"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

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

    # 2. Market Data
    print_safe("\nFetching Market Data...")
    markets = []
    symbols = ['SPY', '^DJI', '^GSPC', '^VIX']
    for symbol in symbols:
        market_data = fetch_market_data_yahoo(symbol)
        if market_data:
            markets.append(market_data)
            print_safe(f"  OK {symbol}: ${market_data['close']:.2f}")
        time.sleep(1)  # Rate limiting

    if markets:
        dashboard_data['markets'] = markets

    # 3. Fed Funds Rate
    print_safe("\nFetching Fed Funds Rate...")
    fed_rate = fetch_fred_data('DFF', limit=1)
    if fed_rate:
        dashboard_data['fed_funds_rate'] = fed_rate
        print_safe(f"  OK Latest: {fed_rate[0]['value']}%")

    # 4. Unemployment Rate
    print_safe("\nFetching Unemployment Rate...")
    unemployment = fetch_fred_data('UNRATE', limit=1)
    if unemployment:
        dashboard_data['unemployment'] = unemployment
        print_safe(f"  OK Latest: {unemployment[0]['value']}%")

    # Simplified CPI and Employment (using existing data as fallback)
    print_safe("\nUsing existing CPI and Employment data...")
    try:
        with open('static/data/dashboard.json', 'r') as f:
            existing = json.load(f)
            if 'cpi' in existing:
                dashboard_data['cpi'] = existing['cpi']
            if 'employment' in existing:
                dashboard_data['employment'] = existing['employment']
            if 'wages' in existing:
                dashboard_data['wages'] = existing['wages']
    except:
        pass

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
