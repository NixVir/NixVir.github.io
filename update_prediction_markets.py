#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prediction Markets Data Fetcher
Fetches prediction market data from Kalshi API for economic indicators
"""
import json
import os
from datetime import datetime
import urllib.request
import urllib.error

KALSHI_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

def print_safe(msg):
    """Print with safe encoding for Windows"""
    try:
        print(msg)
    except:
        print(msg.encode('ascii', 'replace').decode('ascii'))

def fetch_json(url, error_msg="Error fetching data"):
    """Fetch JSON data from URL with error handling"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; ski-resort-monitor)'})
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print_safe(f"  ! {error_msg}: HTTP {e.code}")
        return None
    except Exception as e:
        print_safe(f"  ! {error_msg}: {e}")
        return None

def fetch_kalshi_markets(series_ticker, status="open"):
    """Fetch markets for a given series"""
    url = f"{KALSHI_BASE_URL}/markets?series_ticker={series_ticker}&status={status}"
    data = fetch_json(url, f"Error fetching {series_ticker}")
    if data and 'markets' in data:
        return data['markets']
    return []

def process_inflation_markets(markets):
    """Process annual inflation markets to extract implied probability distribution"""
    if not markets:
        return None

    # Sort by strike price
    sorted_markets = []
    for m in markets:
        ticker = m.get('ticker', '')
        # Extract strike from ticker like KXACPI-2025-2.8
        parts = ticker.split('-')
        if len(parts) >= 3:
            try:
                strike = float(parts[-1])
                sorted_markets.append({
                    'ticker': ticker,
                    'strike': strike,
                    'title': m.get('title', ''),
                    'yes_bid': m.get('yes_bid', 0) / 100,  # Convert cents to dollars
                    'yes_ask': m.get('yes_ask', 0) / 100,
                    'volume': m.get('volume', 0),
                    'open_interest': m.get('open_interest', 0),
                    'close_time': m.get('close_time', '')
                })
            except (ValueError, IndexError):
                continue

    sorted_markets.sort(key=lambda x: x['strike'])

    # Find the "at the money" strike - highest yes_bid
    atm_market = max(sorted_markets, key=lambda x: x['yes_bid']) if sorted_markets else None

    # Calculate implied expected inflation using probability-weighted average
    total_prob = 0
    weighted_sum = 0
    for m in sorted_markets:
        mid_price = (m['yes_bid'] + m['yes_ask']) / 2 if m['yes_ask'] > 0 else m['yes_bid']
        if mid_price > 0:
            # This represents P(inflation > strike)
            # To get the PDF, we need the difference between adjacent strikes
            pass

    return {
        'series': 'KXACPI',
        'name': '2025 Annual Inflation',
        'markets': sorted_markets,
        'consensus_strike': atm_market['strike'] if atm_market else None,
        'consensus_probability': atm_market['yes_bid'] if atm_market else None,
        'total_volume': sum(m['volume'] for m in sorted_markets),
        'updated': datetime.now().isoformat()
    }

def process_payrolls_markets(markets):
    """Process payroll/jobs markets"""
    if not markets:
        return None

    # Group by month
    by_month = {}
    for m in markets:
        ticker = m.get('ticker', '')
        # Extract month and strike from ticker like KXPAYROLLS-26JAN-T50000
        parts = ticker.split('-')
        if len(parts) >= 3:
            month_key = parts[1]  # e.g., "26JAN"
            strike_part = parts[2]  # e.g., "T50000"
            try:
                strike = int(strike_part.replace('T', ''))
                if month_key not in by_month:
                    by_month[month_key] = []
                by_month[month_key].append({
                    'ticker': ticker,
                    'strike': strike,
                    'yes_bid': m.get('yes_bid', 0) / 100,
                    'yes_ask': m.get('yes_ask', 0) / 100,
                    'volume': m.get('volume', 0),
                    'close_time': m.get('close_time', '')
                })
            except (ValueError, IndexError):
                continue

    # Find the nearest month with trading activity
    result_months = []
    for month_key, month_markets in sorted(by_month.items()):
        month_markets.sort(key=lambda x: x['strike'])
        total_volume = sum(m['volume'] for m in month_markets)

        # Find the strike where probability crosses 50%
        median_strike = None
        for m in month_markets:
            if m['yes_bid'] >= 0.45:  # Close to 50%
                median_strike = m['strike']
                break

        result_months.append({
            'month': month_key,
            'markets': month_markets,
            'median_strike': median_strike,
            'total_volume': total_volume
        })

    # Only include months with some activity
    active_months = [m for m in result_months if m['total_volume'] > 0]

    return {
        'series': 'KXPAYROLLS',
        'name': 'Monthly Payrolls',
        'months': active_months[:3],  # Show next 3 active months
        'updated': datetime.now().isoformat()
    }

def process_treasury_markets(markets):
    """Process 10-Year Treasury yield weekly markets"""
    if not markets:
        return None

    sorted_markets = []
    for m in markets:
        ticker = m.get('ticker', '')
        # Extract strike from ticker like KXTNOTEW-25DEC26-T4.32 or KXTNOTEW-25DEC26-B4.31
        parts = ticker.split('-')
        if len(parts) >= 3:
            week_key = parts[1]  # e.g., "25DEC26"
            strike_part = parts[2]  # e.g., "T4.32" or "B4.31"
            try:
                is_above = strike_part.startswith('T')
                strike = float(strike_part[1:])
                sorted_markets.append({
                    'ticker': ticker,
                    'week': week_key,
                    'strike': strike,
                    'is_above': is_above,
                    'yes_bid': m.get('yes_bid', 0) / 100,
                    'yes_ask': m.get('yes_ask', 0) / 100,
                    'volume': m.get('volume', 0)
                })
            except (ValueError, IndexError):
                continue

    # Find the consensus range (highest probability)
    if sorted_markets:
        active = [m for m in sorted_markets if m['yes_bid'] > 0 or m['yes_ask'] > 0]
        if active:
            # Find the highest bid market
            best = max(active, key=lambda x: x['yes_bid'])
            return {
                'series': 'KXTNOTEW',
                'name': '10Y Treasury Yield',
                'week': best['week'],
                'consensus_strike': best['strike'],
                'consensus_probability': best['yes_bid'],
                'markets': sorted_markets[:10],  # Limit for display
                'updated': datetime.now().isoformat()
            }

    return None

def fetch_recession_markets():
    """Fetch recession probability markets"""
    # Try searching events for recession-related markets
    url = f"{KALSHI_BASE_URL}/events?status=open&limit=200"
    data = fetch_json(url, "Error fetching events")

    if not data or 'events' not in data:
        return None

    recession_events = []
    for event in data['events']:
        title = event.get('title', '').lower()
        ticker = event.get('ticker', '')
        if any(term in title for term in ['recession', 'gdp', 'unemployment', 'economic']):
            recession_events.append({
                'ticker': ticker,
                'title': event.get('title', ''),
                'category': event.get('category', '')
            })

    return recession_events if recession_events else None

def update_prediction_markets():
    """Main function to update prediction markets data"""
    print_safe("Starting prediction markets update...")
    print_safe(f"Timestamp: {datetime.now().isoformat()}")

    prediction_data = {
        'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # 1. Annual Inflation Markets
    print_safe("\nFetching Annual Inflation Markets (KXACPI)...")
    inflation_markets = fetch_kalshi_markets('KXACPI')
    if inflation_markets:
        processed = process_inflation_markets(inflation_markets)
        if processed:
            prediction_data['inflation'] = processed
            print_safe(f"  OK {len(inflation_markets)} markets, consensus: {processed.get('consensus_strike', 'N/A')}%")
    else:
        print_safe("  ! No inflation markets found")

    # 2. Payrolls/Jobs Markets
    print_safe("\nFetching Payrolls Markets (KXPAYROLLS)...")
    payrolls_markets = fetch_kalshi_markets('KXPAYROLLS')
    if payrolls_markets:
        processed = process_payrolls_markets(payrolls_markets)
        if processed:
            prediction_data['payrolls'] = processed
            print_safe(f"  OK {len(payrolls_markets)} markets across {len(processed.get('months', []))} months")
    else:
        print_safe("  ! No payrolls markets found")

    # 3. Treasury Yield Markets
    print_safe("\nFetching Treasury 10Y Weekly Markets (KXTNOTEW)...")
    treasury_markets = fetch_kalshi_markets('KXTNOTEW')
    if treasury_markets:
        processed = process_treasury_markets(treasury_markets)
        if processed:
            prediction_data['treasury'] = processed
            print_safe(f"  OK {len(treasury_markets)} markets")
    else:
        print_safe("  ! No treasury markets found")

    # 4. Core CPI Markets
    print_safe("\nFetching Core CPI Markets (KXECONSTATCPICORE)...")
    core_cpi_markets = fetch_kalshi_markets('KXECONSTATCPICORE')
    if core_cpi_markets:
        # Just store the count and next month's data
        prediction_data['core_cpi'] = {
            'series': 'KXECONSTATCPICORE',
            'name': 'Core CPI Month-over-Month',
            'market_count': len(core_cpi_markets),
            'updated': datetime.now().isoformat()
        }
        print_safe(f"  OK {len(core_cpi_markets)} markets")
    else:
        print_safe("  ! No core CPI markets found")

    # Write to file
    output_path = 'static/data/prediction-markets.json'
    print_safe(f"\nWriting data to {output_path}...")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(prediction_data, f, indent=2)

    print_safe("\nOK Prediction markets update complete!")
    print_safe(f"Updated {len([k for k in prediction_data.keys() if k != 'updated'])} categories")

    return prediction_data

if __name__ == '__main__':
    try:
        update_prediction_markets()
    except Exception as e:
        print_safe(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
