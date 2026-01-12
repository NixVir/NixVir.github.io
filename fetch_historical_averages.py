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


def fetch_five_year_seasonal_average():
    """
    Fetch 5-year average snow cover data for the full ski season (Oct 1 - Apr 30).
    """
    print_safe("=" * 60)
    print_safe("Fetching 5-year seasonal averages (Oct 1 - Apr 30)")
    print_safe("=" * 60)

    today = datetime.now()
    current_year = today.year

    # Determine which 5 winters to use
    # If we're after Apr 30, include the just-completed winter
    if today.month >= 5:
        last_complete_winter_end_year = current_year
    else:
        last_complete_winter_end_year = current_year - 1

    # The 5 complete winters
    years_to_fetch = []
    for i in range(5, 0, -1):
        winter_start_year = last_complete_winter_end_year - i
        years_to_fetch.append(winter_start_year)

    print_safe(f"Using winters: {', '.join([f'{y}/{y+1}' for y in years_to_fetch])}")

    # Generate all dates in the ski season (Oct 1 to Apr 30)
    season_dates = []

    # Oct 1 to Dec 31
    ref_year = 2024  # Leap year to include Feb 29
    date = datetime(ref_year, 10, 1)
    while date.month >= 10:
        season_dates.append((date.month, date.day))
        date += timedelta(days=1)

    # Jan 1 to Apr 30
    date = datetime(ref_year + 1, 1, 1)
    while date.month <= 4:
        season_dates.append((date.month, date.day))
        date += timedelta(days=1)

    print_safe(f"Season spans {len(season_dates)} days (Oct 1 - Apr 30)")

    # Dictionary to accumulate values for each day
    daily_data = {d: [] for d in season_dates}

    # Track data by year for debugging
    yearly_stats = {y: {'fetched': 0, 'missing': 0} for y in years_to_fetch}

    total_requests = len(season_dates) * len(years_to_fetch)
    completed = 0
    start_time = time.time()

    for winter_start_year in years_to_fetch:
        print_safe(f"\nFetching {winter_start_year}/{winter_start_year + 1} winter...")

        for month, day in season_dates:
            # Skip Feb 29 for non-leap years
            if month == 2 and day == 29:
                year_to_check = winter_start_year + 1
                if not (year_to_check % 4 == 0 and (year_to_check % 100 != 0 or year_to_check % 400 == 0)):
                    completed += 1
                    continue

            # Determine the actual year for this date
            if month >= 10:
                year = winter_start_year
            else:
                year = winter_start_year + 1

            data = fetch_nohrsc_historical(year, month, day)

            if data is not None and data['cover'] is not None:
                daily_data[(month, day)].append(data['cover'])
                yearly_stats[winter_start_year]['fetched'] += 1
            else:
                yearly_stats[winter_start_year]['missing'] += 1

            completed += 1

            # Progress update every 25 requests
            if completed % 25 == 0:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                remaining = (total_requests - completed) / rate if rate > 0 else 0
                print_safe(f"  Progress: {completed}/{total_requests} ({100*completed//total_requests}%) - ETA: {remaining:.0f}s")

            # Small delay to be nice to the server
            time.sleep(0.1)

    # Calculate averages for each day
    seasonal_avg = []
    for month, day in season_dates:
        values = daily_data[(month, day)]
        if values:
            avg = round(sum(values) / len(values), 1)
        else:
            avg = None

        seasonal_avg.append({
            'date': f'{month:02d}-{day:02d}',
            'value': avg,
            'count': len(values)
        })

    # Summary stats
    print_safe("\n" + "=" * 40)
    print_safe("SUMMARY")
    print_safe("=" * 40)

    for year in years_to_fetch:
        stats = yearly_stats[year]
        print_safe(f"  {year}/{year+1}: {stats['fetched']} fetched, {stats['missing']} missing")

    valid_days = [d for d in seasonal_avg if d['value'] is not None]
    print_safe(f"\nSeasonal average computed for {len(valid_days)}/{len(season_dates)} days")

    if valid_days:
        avg_cover = sum(d['value'] for d in valid_days) / len(valid_days)
        print_safe(f"Overall season average: {avg_cover:.1f}%")

    elapsed = time.time() - start_time
    print_safe(f"Total time: {elapsed:.1f} seconds")

    return seasonal_avg, years_to_fetch


def main():
    """Main entry point"""
    print_safe(f"Starting historical data fetch at {datetime.now().isoformat()}\n")

    usa_seasonal_avg, years_used = fetch_five_year_seasonal_average()

    # Fetch REAL Canada averages from IMS satellite data - NO DERIVATION!
    print_safe("\n" + "=" * 60)
    print_safe("Fetching REAL Canada historical averages from NOAA IMS...")
    print_safe("=" * 60)

    canada_bounds = REGION_BOUNDS.get('canada')

    # Build Canada seasonal averages from real IMS data
    # Use same date format (MM-DD) and average across the same years
    canada_seasonal_avg = []

    for entry in usa_seasonal_avg:
        date_key = entry['date']  # MM-DD format

        # Collect values from each year
        canada_values = []

        for year_start in years_used:
            # Determine actual date based on season
            month = int(date_key.split('-')[0])
            day = int(date_key.split('-')[1])

            if month >= 10:  # Oct, Nov, Dec
                actual_year = year_start
            else:  # Jan, Feb, Mar, Apr
                actual_year = year_start + 1

            try:
                date_obj = datetime(actual_year, month, day)
                doy = date_obj.timetuple().tm_yday

                # Fetch IMS grid
                grid = fetch_ims_file(actual_year, doy)
                if grid and canada_bounds:
                    stats = calculate_snow_cover_percentage(grid, canada_bounds)
                    if stats:
                        canada_values.append(stats['cover'])
            except Exception as e:
                pass  # Skip invalid dates or fetch errors

            time.sleep(0.05)  # Small delay for IMS server

        # Calculate average if we have values
        if canada_values:
            canada_avg = round(sum(canada_values) / len(canada_values), 1)
        else:
            canada_avg = None

        canada_seasonal_avg.append({
            'date': date_key,
            'value': canada_avg,
            'count': len(canada_values)
        })

        # Progress update
        if len(canada_seasonal_avg) % 30 == 0:
            print_safe(f"  Canada progress: {len(canada_seasonal_avg)}/{len(usa_seasonal_avg)} days processed")

    print_safe(f"Canada historical data complete: {len([e for e in canada_seasonal_avg if e['value'] is not None])}/{len(canada_seasonal_avg)} days with data")

    # Build output data
    data = {
        'generated': datetime.now().strftime('%Y-%m-%d %H:%M') + ' UTC',
        'description': '5-year average snow cover for ski season (Oct 1 - Apr 30)',
        'winters_included': [f'{y}/{y+1}' for y in years_used],
        'usa': usa_seasonal_avg,
        'canada': canada_seasonal_avg
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
