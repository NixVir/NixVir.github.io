#!/usr/bin/env python3
"""
Fetch monthly T-100 airport passenger data from BTS TranStats.

This script downloads monthly T-100 Domestic Segment data and extracts
passenger counts for ski gateway airports, enabling month-over-month
year-over-year comparisons.

Data source: Bureau of Transportation Statistics (BTS)
https://www.transtats.bts.gov/
"""

import json
import os
import csv
import io
import re
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.parse
import zipfile
import tempfile

# Ski gateway airports to track
# Primary mountain airports + California drive-to markets
SKI_GATEWAY_AIRPORTS = [
    # Major hubs
    'DEN', 'SLC', 'RNO',
    # Montana/Wyoming
    'BZN', 'JAC', 'FCA', 'MSO',
    # Colorado mountain airports
    'EGE', 'ASE', 'HDN', 'MTJ', 'DRO', 'GUC',
    # Idaho
    'SUN',
    # California mountain/drive-to
    'MMH', 'FAT', 'PSP',
    # Note: TEX (Telluride) removed - too small, often no scheduled service
]

# Canadian airports - not in T-100 Domestic, would need T-100 International
# 'YYC', 'YVR', 'YLW', 'YXC'

# Output file
OUTPUT_FILE = Path(__file__).parent / 'static' / 'data' / 'airport-monthly.json'


def fetch_t100_monthly_from_bts():
    """
    Attempt to fetch T-100 monthly data using BTS Socrata API.

    The T-100 data on data.bts.gov may have monthly breakdowns in certain datasets.
    """
    # Try the T-100 Domestic Segment dataset
    # This dataset may have monthly data embedded
    base_url = "https://data.bts.gov/resource/r495-tyji.json"

    all_data = []

    for airport in SKI_GATEWAY_AIRPORTS:
        url = f"{base_url}?origin_airport_code={airport}&$limit=50000"
        print(f"  Fetching {airport}...")

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode())

            for record in data:
                year = record.get('year', '')
                passengers = int(float(record.get('total_passengers', 0) or 0))
                domestic = int(float(record.get('domestic_passengers', 0) or 0))

                all_data.append({
                    'airport': airport,
                    'year': year,
                    'passengers': passengers,
                    'domestic_passengers': domestic
                })

        except Exception as e:
            print(f"    Error fetching {airport}: {e}")

    return all_data


def try_alternative_monthly_source():
    """
    Try to find monthly airport data from alternative BTS sources.

    The T-100 data often comes in annual aggregates, but there may be
    monthly datasets available through different endpoints.
    """
    # Check if there's a monthly T-100 dataset
    monthly_endpoints = [
        # T-100 Domestic Market (might have monthly)
        "https://data.bts.gov/resource/hxqj-qyye.json",
        # Try alternate T-100 segment IDs
        "https://data.bts.gov/resource/6yih-h6jn.json",
    ]

    for endpoint in monthly_endpoints:
        try:
            url = f"{endpoint}?$limit=5"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
                if data:
                    print(f"  Found data at {endpoint}")
                    # Check if it has month field
                    if data and 'month' in data[0]:
                        print(f"    Has monthly data!")
                        return endpoint
        except Exception as e:
            continue

    return None


def download_from_transtats_manual():
    """
    Instructions for manual download from TranStats.

    Since TranStats requires session authentication for direct downloads,
    this function provides instructions for manual data acquisition.
    """
    instructions = """
    ============================================================
    MANUAL DOWNLOAD REQUIRED
    ============================================================

    The BTS TranStats T-100 monthly data requires manual download:

    1. Go to: https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoession_VQ=FGK

    2. Select "T-100 Domestic Segment (All Carriers)"

    3. Choose fields:
       - YEAR
       - MONTH
       - ORIGIN (airport code)
       - PASSENGERS
       - DEPARTURES_PERFORMED

    4. Filter by airports (optional):
       DEN, SLC, RNO, BZN, JAC, FCA, MSO, EGE, ASE, HDN, MTJ, DRO, SUN, GUC, TEX, MMH

    5. Download as CSV

    6. Save to: data/t100_monthly_raw.csv

    7. Re-run this script to process the data
    ============================================================
    """
    return instructions


def parse_manual_csv(csv_path):
    """
    Parse manually downloaded T-100 CSV file.
    """
    if not os.path.exists(csv_path):
        return None

    monthly_data = {}

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            airport = row.get('ORIGIN', '').strip()
            if airport not in SKI_GATEWAY_AIRPORTS:
                continue

            year = row.get('YEAR', '').strip()
            month = row.get('MONTH', '').strip()
            passengers = int(float(row.get('PASSENGERS', 0) or 0))

            key = f"{airport}_{year}_{month}"

            if key not in monthly_data:
                monthly_data[key] = {
                    'airport': airport,
                    'year': int(year),
                    'month': int(month),
                    'passengers': 0
                }

            monthly_data[key]['passengers'] += passengers

    return list(monthly_data.values())


def calculate_yoy_comparisons(monthly_data):
    """
    Calculate month-over-month year-over-year comparisons.

    For each airport and month, compare current year to prior year.
    """
    # Organize by airport -> year -> month -> passengers
    by_airport = {}
    for record in monthly_data:
        airport = record['airport']
        year = record['year']
        month = record['month']
        passengers = record['passengers']

        if airport not in by_airport:
            by_airport[airport] = {}
        if year not in by_airport[airport]:
            by_airport[airport][year] = {}

        by_airport[airport][year][month] = passengers

    # Calculate YoY for each airport
    results = {}

    for airport, years in by_airport.items():
        sorted_years = sorted(years.keys(), reverse=True)
        if len(sorted_years) < 2:
            continue

        current_year = sorted_years[0]
        prior_year = sorted_years[1]

        current_months = years[current_year]
        prior_months = years[prior_year]

        # Find common months
        common_months = set(current_months.keys()) & set(prior_months.keys())

        if not common_months:
            continue

        # Calculate YoY for each common month
        monthly_yoy = {}
        total_current = 0
        total_prior = 0

        for month in sorted(common_months):
            current_pax = current_months[month]
            prior_pax = prior_months[month]

            total_current += current_pax
            total_prior += prior_pax

            if prior_pax > 0:
                yoy_pct = ((current_pax - prior_pax) / prior_pax) * 100
            else:
                yoy_pct = None

            monthly_yoy[month] = {
                'current': current_pax,
                'prior': prior_pax,
                'yoy_pct': round(yoy_pct, 1) if yoy_pct is not None else None
            }

        # Overall YTD comparison
        if total_prior > 0:
            ytd_yoy_pct = ((total_current - total_prior) / total_prior) * 100
        else:
            ytd_yoy_pct = None

        results[airport] = {
            'current_year': current_year,
            'prior_year': prior_year,
            'months_compared': len(common_months),
            'monthly': monthly_yoy,
            'ytd': {
                'current': total_current,
                'prior': total_prior,
                'yoy_pct': round(ytd_yoy_pct, 1) if ytd_yoy_pct is not None else None
            },
            'latest_month': max(common_months)
        }

    return results


def main():
    print("=" * 60)
    print("T-100 MONTHLY AIRPORT DATA FETCH")
    print("=" * 60)
    print()

    # Check for manually downloaded CSV first
    manual_csv_path = Path(__file__).parent / 'data' / 't100_monthly_raw.csv'

    if manual_csv_path.exists():
        print(f"Found manual CSV: {manual_csv_path}")
        print("Parsing monthly data...")

        monthly_data = parse_manual_csv(manual_csv_path)

        if monthly_data:
            print(f"  Parsed {len(monthly_data)} monthly records")

            # Calculate YoY comparisons
            print("\nCalculating YoY comparisons...")
            yoy_results = calculate_yoy_comparisons(monthly_data)

            # Build output
            output = {
                'updated': datetime.utcnow().isoformat() + 'Z',
                'source': 'BTS T-100 Domestic Segment',
                'airports': yoy_results,
                'raw_monthly': monthly_data
            }

            # Save output
            OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(output, f, indent=2)

            print(f"\nOutput saved to: {OUTPUT_FILE}")

            # Print summary
            print("\nSUMMARY:")
            print("-" * 40)
            for airport, data in sorted(yoy_results.items()):
                ytd = data['ytd']
                print(f"  {airport}: {ytd['current']:,} pax ({ytd['yoy_pct']:+.1f}% YoY, {data['months_compared']} months)")

            return

    # Try API sources
    print("No manual CSV found. Trying API sources...")
    print()

    # Try alternative monthly source
    print("Checking for monthly data endpoints...")
    monthly_endpoint = try_alternative_monthly_source()

    if not monthly_endpoint:
        print("\nNo monthly API endpoint found.")
        print(download_from_transtats_manual())
        return

    print(f"\nFound monthly endpoint: {monthly_endpoint}")
    # Would continue with API fetch here...


if __name__ == '__main__':
    main()
