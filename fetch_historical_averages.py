#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-time script to fetch 5-year historical snow cover averages.

This fetches:
- NOHRSC data for USA for the full ski season (Oct 1 - Apr 30)
- NOAA IMS satellite data for Canada (REAL data, NOT derived)

for the past 5 complete winters and computes daily averages.

Output is saved to static/data/snow-cover-historical.json and should
only need to be run once per year (after April 30) to include the
newly completed season.

Usage:
    python fetch_historical_averages.py
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

# Import IMS fetcher for REAL Canada data
from fetch_ims_snow_data import (
    fetch_ims_file,
    calculate_snow_cover_percentage,
    REGION_BOUNDS
)


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


def fetch_nohrsc_historical(year, month, day):
    """
    Fetch historical NOHRSC snow cover for a specific date.
    Returns dict with 'cover', or None if not available.
    """
    url = f"https://www.nohrsc.noaa.gov/nsa/index.html?year={year}&month={month}&day={day}"
    content = fetch_url(url, timeout=15)

    if not content:
        return None

    # Look for "Area Covered By Snow" pattern
    match = re.search(
        r'Area\s+Covered\s+By\s+Snow[:\s]*</td>\s*<td[^>]*>\s*(\d+(?:\.\d+)?)\s*%',
        content, re.IGNORECASE
    )
    if match:
        return {'cover': float(match.group(1))}

    # Fallback pattern
    match = re.search(
        r'Area\s+Covered[^<]*<[^>]*>[^<]*(\d+(?:\.\d+)?)\s*%',
        content, re.IGNORECASE
    )
    if match:
        return {'cover': float(match.group(1))}

    return None


def main():
    """Main entry point"""
    print_safe(f"Starting historical data fetch at {datetime.now().isoformat()}\n")

    # Determine which 5 winters to use
    today = datetime.now()
    current_year = today.year
    if today.month >= 5:
        last_complete_winter_end_year = current_year
    else:
        last_complete_winter_end_year = current_year - 1

    years_used = []
    for i in range(5, 0, -1):
        winter_start_year = last_complete_winter_end_year - i
        years_used.append(winter_start_year)

    print_safe(f"Using winters: {', '.join([f'{y}/{y+1}' for y in years_used])}")

    # Generate all dates in the ski season (Oct 1 to Apr 30)
    season_dates = []
    ref_year = 2024  # Leap year to include Feb 29
    date = datetime(ref_year, 10, 1)
    while date.month >= 10:
        season_dates.append((date.month, date.day))
        date += timedelta(days=1)
    date = datetime(ref_year + 1, 1, 1)
    while date.month <= 4:
        season_dates.append((date.month, date.day))
        date += timedelta(days=1)

    print_safe(f"Season spans {len(season_dates)} days (Oct 1 - Apr 30)")

    canada_bounds = REGION_BOUNDS.get('canada')

    # Store raw daily values for each (date, year) combination
    # This allows us to compute USA, Canada, and Combined averages without re-fetching
    usa_raw = {}    # (month, day, year) -> value
    canada_raw = {} # (month, day, year) -> value

    # =========================================================================
    # PHASE 1: Fetch all USA data
    # =========================================================================
    print_safe("\n" + "=" * 60)
    print_safe("Phase 1: Fetching USA historical data from NOHRSC...")
    print_safe("=" * 60)

    total_requests = len(season_dates) * len(years_used)
    completed = 0
    start_time = time.time()

    for winter_start_year in years_used:
        print_safe(f"\nFetching {winter_start_year}/{winter_start_year + 1} winter...")

        for month, day in season_dates:
            # Skip Feb 29 for non-leap years
            if month == 2 and day == 29:
                year_to_check = winter_start_year + 1
                if not (year_to_check % 4 == 0 and (year_to_check % 100 != 0 or year_to_check % 400 == 0)):
                    completed += 1
                    continue

            if month >= 10:
                year = winter_start_year
            else:
                year = winter_start_year + 1

            data = fetch_nohrsc_historical(year, month, day)
            if data is not None and data['cover'] is not None:
                usa_raw[(month, day, year)] = data['cover']

            completed += 1
            if completed % 50 == 0:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                remaining = (total_requests - completed) / rate if rate > 0 else 0
                print_safe(f"  Progress: {completed}/{total_requests} ({100*completed//total_requests}%) - ETA: {remaining:.0f}s")

            time.sleep(0.1)

    print_safe(f"\nUSA: {len(usa_raw)} daily values collected")

    # =========================================================================
    # PHASE 2: Fetch all Canada data
    # =========================================================================
    print_safe("\n" + "=" * 60)
    print_safe("Phase 2: Fetching Canada historical data from NOAA IMS...")
    print_safe("=" * 60)

    completed = 0
    start_time = time.time()

    for winter_start_year in years_used:
        print_safe(f"\nFetching {winter_start_year}/{winter_start_year + 1} winter...")

        for month, day in season_dates:
            # Skip Feb 29 for non-leap years
            if month == 2 and day == 29:
                year_to_check = winter_start_year + 1
                if not (year_to_check % 4 == 0 and (year_to_check % 100 != 0 or year_to_check % 400 == 0)):
                    completed += 1
                    continue

            if month >= 10:
                year = winter_start_year
            else:
                year = winter_start_year + 1

            try:
                date_obj = datetime(year, month, day)
                doy = date_obj.timetuple().tm_yday
                grid = fetch_ims_file(year, doy)
                if grid and canada_bounds:
                    stats = calculate_snow_cover_percentage(grid, canada_bounds)
                    if stats:
                        canada_raw[(month, day, year)] = stats['cover']
            except Exception:
                pass

            completed += 1
            if completed % 50 == 0:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                remaining = (total_requests - completed) / rate if rate > 0 else 0
                print_safe(f"  Progress: {completed}/{total_requests} ({100*completed//total_requests}%) - ETA: {remaining:.0f}s")

            time.sleep(0.05)

    print_safe(f"\nCanada: {len(canada_raw)} daily values collected")

    # =========================================================================
    # PHASE 3: Compute averages from stored raw data (NO re-fetching)
    # =========================================================================
    print_safe("\n" + "=" * 60)
    print_safe("Phase 3: Computing seasonal averages from collected data...")
    print_safe("=" * 60)

    usa_seasonal_avg = []
    canada_seasonal_avg = []
    combined_seasonal_avg = []

    for month, day in season_dates:
        date_key = f'{month:02d}-{day:02d}'

        # Collect values for this date across all years
        usa_values = []
        canada_values = []
        combined_values = []

        for year_start in years_used:
            if month >= 10:
                year = year_start
            else:
                year = year_start + 1

            usa_val = usa_raw.get((month, day, year))
            canada_val = canada_raw.get((month, day, year))

            if usa_val is not None:
                usa_values.append(usa_val)
            if canada_val is not None:
                canada_values.append(canada_val)

            # Combined requires BOTH values for that specific day
            if usa_val is not None and canada_val is not None:
                combined_values.append((usa_val + canada_val) / 2)

        # USA average
        usa_seasonal_avg.append({
            'date': date_key,
            'value': round(sum(usa_values) / len(usa_values), 1) if usa_values else None,
            'count': len(usa_values)
        })

        # Canada average
        canada_seasonal_avg.append({
            'date': date_key,
            'value': round(sum(canada_values) / len(canada_values), 1) if canada_values else None,
            'count': len(canada_values)
        })

        # Combined average (from raw daily pairs, not from country averages)
        combined_seasonal_avg.append({
            'date': date_key,
            'value': round(sum(combined_values) / len(combined_values), 1) if combined_values else None,
            'count': len(combined_values)
        })

    # Summary
    print_safe(f"\nUSA: {len([e for e in usa_seasonal_avg if e['value'] is not None])}/{len(season_dates)} days with data")
    print_safe(f"Canada: {len([e for e in canada_seasonal_avg if e['value'] is not None])}/{len(season_dates)} days with data")
    print_safe(f"Combined: {len([e for e in combined_seasonal_avg if e['value'] is not None])}/{len(season_dates)} days with data")

    # Build output data
    data = {
        'generated': datetime.now().strftime('%Y-%m-%d %H:%M') + ' UTC',
        'description': '5-year average snow cover for ski season (Oct 1 - Apr 30)',
        'winters_included': [f'{y}/{y+1}' for y in years_used],
        'usa': usa_seasonal_avg,
        'canada': canada_seasonal_avg,
        'combined': combined_seasonal_avg
    }

    # Save to file
    output_path = 'static/data/snow-cover-historical.json'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print_safe(f"\nData saved to: {output_path}")
    print_safe("Done!")

    return 0


if __name__ == '__main__':
    sys.exit(main())
