#!/usr/bin/env python3
"""
Generate unified airport_passengers.json output file.

This script combines data from multiple sources:
- Tier 1: Individual airport scrapers (SLC, JAC, EGE, DEN)
- Tier 2: BTS T-100 manual CSV download
- Tier 3: Canadian sources (future)

Output: static/data/airport_passengers.json
"""

import json
from datetime import datetime, timezone
from pathlib import Path

# Paths
DATA_DIR = Path(__file__).parent / 'static' / 'data'
OUTPUT_FILE = DATA_DIR / 'airport_passengers.json'

# Individual airport data files
AIRPORT_FILES = {
    'SLC': DATA_DIR / 'slc-monthly.json',
    'JAC': DATA_DIR / 'jac-monthly.json',
    'EGE': DATA_DIR / 'ege-monthly.json',
    'DEN': DATA_DIR / 'den-monthly.json',
}

# T-100 combined file
T100_FILE = DATA_DIR / 'airport-monthly.json'

# Canadian airports file
CANADIAN_FILE = DATA_DIR / 'canadian-airports.json'

MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]


def load_airport_data(code, filepath):
    """
    Load data from individual airport JSON file.
    """
    if not filepath.exists():
        return None

    try:
        with open(filepath) as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading {code} data: {e}")
        return None


def load_t100_data():
    """
    Load data from BTS T-100 processed file.
    """
    if not T100_FILE.exists():
        return None

    try:
        with open(T100_FILE) as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading T-100 data: {e}")
        return None


def load_canadian_data():
    """
    Load data from BTS T-100 International (Canadian airports) processed file.
    """
    if not CANADIAN_FILE.exists():
        return None

    try:
        with open(CANADIAN_FILE) as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading Canadian airport data: {e}")
        return None


def merge_airport_data(airport_data, t100_data, canadian_data=None):
    """
    Merge data from individual airport files, T-100 data, and Canadian data.

    Priority: Individual airport files > T-100 (individual files are more current)
    """
    merged = {}

    # First, add Canadian data if available
    if canadian_data and 'airports' in canadian_data:
        for airport, months in canadian_data['airports'].items():
            if airport not in merged:
                merged[airport] = {'monthly': {}, 'source': 'BTS T-100 International'}

            for key, record in months.items():
                merged[airport]['monthly'][key] = {
                    'passengers': record['passengers'],
                    'yoy_pct': record.get('yoy_pct'),
                    'source': 'BTS T-100 International'
                }

    # Add T-100 data if available
    if t100_data and 'raw_monthly' in t100_data:
        for record in t100_data['raw_monthly']:
            airport = record['airport']
            year = record['year']
            month = record['month']
            key = f"{year}-{str(month).zfill(2)}"

            if airport not in merged:
                merged[airport] = {'monthly': {}, 'source': 'BTS T-100'}

            merged[airport]['monthly'][key] = {
                'passengers': record['passengers'],
                'source': 'BTS T-100'
            }

    # Then overlay with individual airport data (higher priority)
    for code, data in airport_data.items():
        if not data:
            continue

        if code not in merged:
            merged[code] = {'monthly': {}, 'source': data.get('source', 'Airport website')}
        else:
            # Upgrade source if we have direct airport data
            merged[code]['source'] = data.get('source', 'Airport website')

        monthly = data.get('monthly', [])
        for record in monthly:
            year = record['year']
            month = record['month']
            key = f"{year}-{str(month).zfill(2)}"

            # Individual airport data takes precedence
            merged[code]['monthly'][key] = {
                'passengers': record['passengers'],
                'yoy_pct': record.get('yoy_pct'),
                'is_estimate': record.get('is_estimate', False),
                'source': record.get('source', data.get('source', 'Airport website'))
            }

    return merged


def calculate_yoy(merged_data):
    """
    Calculate year-over-year percentages where missing.
    """
    for airport, data in merged_data.items():
        monthly = data.get('monthly', {})

        for key, record in monthly.items():
            if record.get('yoy_pct') is not None:
                continue

            # Parse year-month
            try:
                year, month = key.split('-')
                year = int(year)
                month = int(month)
            except ValueError:
                continue

            # Look for prior year same month
            prior_key = f"{year - 1}-{str(month).zfill(2)}"
            prior = monthly.get(prior_key)

            if prior and prior.get('passengers', 0) > 0:
                current = record.get('passengers', 0)
                prior_pax = prior['passengers']
                yoy = ((current - prior_pax) / prior_pax) * 100
                record['yoy_pct'] = round(yoy, 2)

    return merged_data


def determine_latest_month(merged_data):
    """
    Determine the latest month with data for each airport.
    """
    for airport, data in merged_data.items():
        monthly = data.get('monthly', {})
        if not monthly:
            continue

        # Sort keys and get latest
        sorted_keys = sorted(monthly.keys(), reverse=True)

        # Find latest non-estimate month
        latest_real = None
        for key in sorted_keys:
            if not monthly[key].get('is_estimate', False):
                latest_real = key
                break

        data['latest_month'] = sorted_keys[0] if sorted_keys else None
        data['latest_real_month'] = latest_real

    return merged_data


def build_output(merged_data):
    """
    Build final output JSON structure matching the specification.
    """
    output = {
        'last_updated': datetime.now(timezone.utc).isoformat(),
        'data_lag_note': 'BTS T-100 data typically 2-3 months behind. '
                        'Individual airport sources may be more current.',
        'data_sources': {},
        'airports': {}
    }

    for airport, data in merged_data.items():
        monthly = data.get('monthly', {})
        source = data.get('source', 'Unknown')
        latest = data.get('latest_real_month')

        # Data source info
        output['data_sources'][airport] = {
            'source': source,
            'last_month_available': latest
        }

        # Monthly data
        output['airports'][airport] = {}
        for key, record in sorted(monthly.items()):
            output['airports'][airport][key] = {
                'passengers': record.get('passengers'),
                'yoy_pct': record.get('yoy_pct'),
            }

            # Add estimate flag if present
            if record.get('is_estimate'):
                output['airports'][airport][key]['is_estimate'] = True

    return output


def print_summary(output):
    """
    Print a summary of the generated data.
    """
    print("\n" + "=" * 60)
    print("GENERATED AIRPORT DATA SUMMARY")
    print("=" * 60)
    print()

    for airport, info in sorted(output['data_sources'].items()):
        source = info.get('source', 'Unknown')
        latest = info.get('last_month_available', 'N/A')

        months_count = len(output['airports'].get(airport, {}))
        estimates = sum(1 for r in output['airports'].get(airport, {}).values()
                       if r.get('is_estimate'))

        print(f"  {airport}:")
        print(f"    Source: {source}")
        print(f"    Latest: {latest}")
        print(f"    Months: {months_count} ({estimates} estimated)")
        print()


def main():
    print("=" * 60)
    print("AIRPORT PASSENGER DATA GENERATOR")
    print("=" * 60)
    print()

    # Load individual airport data
    print("Loading airport data files...")
    airport_data = {}
    for code, filepath in AIRPORT_FILES.items():
        data = load_airport_data(code, filepath)
        if data:
            print(f"  {code}: Loaded {len(data.get('monthly', []))} months")
            airport_data[code] = data
        else:
            print(f"  {code}: No data file found")

    # Load T-100 data
    print("\nLoading T-100 data...")
    t100_data = load_t100_data()
    if t100_data:
        raw = t100_data.get('raw_monthly', [])
        print(f"  Loaded {len(raw)} T-100 records")
    else:
        print("  No T-100 data file found")

    # Load Canadian airport data
    print("\nLoading Canadian airport data...")
    canadian_data = load_canadian_data()
    if canadian_data:
        airports = canadian_data.get('airports', {})
        total_records = sum(len(m) for m in airports.values())
        print(f"  Loaded {total_records} records for {len(airports)} Canadian airports")
    else:
        print("  No Canadian data file found (run fetch_t100_international.py)")

    # Merge data
    print("\nMerging data sources...")
    merged = merge_airport_data(airport_data, t100_data, canadian_data)
    print(f"  {len(merged)} airports with data")

    # Calculate YoY
    print("\nCalculating YoY percentages...")
    merged = calculate_yoy(merged)

    # Determine latest months
    merged = determine_latest_month(merged)

    # Build output
    print("\nBuilding output...")
    output = build_output(merged)

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nOutput saved to: {OUTPUT_FILE}")

    # Print summary
    print_summary(output)

    # Provide guidance on what's missing
    print("=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("""
To get more data:

1. Run individual airport scrapers:
   python scrape_slc.py
   python scrape_jac.py
   python scrape_ege.py
   python scrape_den.py

2. For BTS T-100 Domestic data (US airports):
   - Download manually from TranStats
   - Save to data/t100_monthly_raw.csv
   - Run: python fetch_t100_monthly.py

3. For BTS T-100 International data (Canadian airports):
   - Download manually from TranStats (T-100 International)
   - Save to data/t100_international_raw.csv
   - Run: python fetch_t100_international.py

4. Re-run this script to combine all sources:
   python generate_airport_output.py
""")


if __name__ == '__main__':
    main()
