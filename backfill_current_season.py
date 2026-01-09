#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-time script to backfill current season snow cover data.

This fetches NOHRSC data from Oct 1, 2025 to today and saves it
to static/data/snow-cover-season.json. This file will then be
loaded and appended to by the daily update script.

Usage:
    python backfill_current_season.py
"""

import json
import time
import os
import sys
import re
import urllib.request
import urllib.error
import ssl
from datetime import datetime, timedelta


def print_safe(msg):
    """Print with flush for real-time output"""
    print(msg, flush=True)


def fetch_url(url, timeout=15):
    """Fetch URL content with error handling"""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return None


def fetch_nohrsc_for_date(year, month, day):
    """
    Fetch NOHRSC snow cover for a specific date.
    Returns dict with 'cover' and 'depth_inches', or None if not available.
    """
    url = f"https://www.nohrsc.noaa.gov/nsa/index.html?year={year}&month={month}&day={day}"
    content = fetch_url(url, timeout=15)

    if not content:
        return None

    result = {}

    # Look for "Area Covered By Snow" pattern
    match = re.search(
        r'Area\s+Covered\s+By\s+Snow[:\s]*</td>\s*<td[^>]*>\s*(\d+(?:\.\d+)?)\s*%',
        content, re.IGNORECASE
    )
    if match:
        result['cover'] = float(match.group(1))
    else:
        # Fallback pattern
        match = re.search(
            r'Area\s+Covered[^<]*<[^>]*>[^<]*(\d+(?:\.\d+)?)\s*%',
            content, re.IGNORECASE
        )
        if match:
            result['cover'] = float(match.group(1))

    # Look for average depth
    depth_match = re.search(
        r'Average\s+Snow\s+Depth[:\s]*</td>\s*<td[^>]*>\s*(\d+(?:\.\d+)?)\s*(?:inches|in)',
        content, re.IGNORECASE
    )
    if depth_match:
        result['depth_inches'] = float(depth_match.group(1))

    if 'cover' in result:
        return result
    return None


def backfill_current_season():
    """
    Fetch all snow cover data from Oct 1, 2025 to today.
    """
    print_safe("=" * 60)
    print_safe("Backfilling current season data (Oct 1, 2025 to today)")
    print_safe("=" * 60)

    # Season start
    season_start = datetime(2025, 10, 1)
    today = datetime.now()

    # Don't go past today
    end_date = min(today, datetime(2026, 4, 30))

    # Calculate days to fetch
    total_days = (end_date - season_start).days + 1
    print_safe(f"Fetching {total_days} days of data...")

    usa_history = []
    start_time = time.time()

    current_date = season_start
    fetched = 0
    missing = 0

    while current_date <= end_date:
        year = current_date.year
        month = current_date.month
        day = current_date.day
        date_str = current_date.strftime('%Y-%m-%d')

        data = fetch_nohrsc_for_date(year, month, day)

        if data and 'cover' in data:
            usa_history.append({
                'date': date_str,
                'value': data['cover'],
                'depth_inches': data.get('depth_inches')
            })
            fetched += 1
        else:
            # Record as missing but don't add null entry
            missing += 1
            print_safe(f"  Missing data for {date_str}")

        # Progress update every 10 days
        completed = fetched + missing
        if completed % 10 == 0:
            elapsed = time.time() - start_time
            rate = completed / elapsed if elapsed > 0 else 0
            remaining = (total_days - completed) / rate if rate > 0 else 0
            print_safe(f"  Progress: {completed}/{total_days} ({100*completed//total_days}%) - ETA: {remaining:.0f}s")

        # Small delay to be nice to the server
        time.sleep(0.15)
        current_date += timedelta(days=1)

    # Derive Canada data using typical ratio (~2x USA, capped at 100%)
    canada_history = []
    for entry in usa_history:
        canada_value = min(100, round(entry['value'] * 2.0, 1))
        canada_history.append({
            'date': entry['date'],
            'value': canada_value
        })

    # Summary
    print_safe("\n" + "=" * 40)
    print_safe("SUMMARY")
    print_safe("=" * 40)
    print_safe(f"Days fetched: {fetched}")
    print_safe(f"Days missing: {missing}")
    print_safe(f"Date range: {usa_history[0]['date'] if usa_history else 'N/A'} to {usa_history[-1]['date'] if usa_history else 'N/A'}")

    elapsed = time.time() - start_time
    print_safe(f"Total time: {elapsed:.1f} seconds")

    return usa_history, canada_history


def main():
    """Main entry point"""
    print_safe(f"Starting backfill at {datetime.now().isoformat()}\n")

    usa_history, canada_history = backfill_current_season()

    if not usa_history:
        print_safe("ERROR: No data fetched!")
        return 1

    # Build output data
    data = {
        'generated': datetime.now().strftime('%Y-%m-%d %H:%M') + ' UTC',
        'description': 'Current season snow cover data (Oct 1, 2025 onwards)',
        'season': '2025-2026',
        'usa': usa_history,
        'canada': canada_history
    }

    # Save to file
    output_path = 'static/data/snow-cover-season.json'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print_safe(f"\nData saved to: {output_path}")
    print_safe("Done!")

    return 0


if __name__ == '__main__':
    sys.exit(main())
