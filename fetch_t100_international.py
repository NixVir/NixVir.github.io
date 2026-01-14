#!/usr/bin/env python3
"""
Fetch monthly T-100 International passenger data from BTS TranStats.

This script processes T-100 International Segment data for Canadian airports
that serve as ski gateways (YYC, YVR, YLW, YXC).

Data source: Bureau of Transportation Statistics (BTS)
https://www.transtats.bts.gov/

Note: T-100 International requires manual download from TranStats:
1. Go to https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoession_VQ=FHL
2. Select "T-100 International Segment (All Carriers)"
3. Choose fields: YEAR, MONTH, ORIGIN, DEST, PASSENGERS
4. Filter by country: Canada
5. Download as CSV
6. Save to: data/t100_international_raw.csv
"""

import json
import os
import csv
from datetime import datetime, timezone
from pathlib import Path

# Canadian ski gateway airports
CANADIAN_SKI_AIRPORTS = {
    'YYC': {'name': 'Calgary Intl', 'city': 'Calgary', 'resorts': 'Banff, Lake Louise, Kicking Horse', 'region': 'alberta'},
    'YVR': {'name': 'Vancouver Intl', 'city': 'Vancouver', 'resorts': 'Whistler Blackcomb', 'region': 'bc'},
    'YLW': {'name': 'Kelowna Intl', 'city': 'Kelowna', 'resorts': 'Big White, Silver Star', 'region': 'bc'},
    'YXC': {'name': 'Cranbrook/Kimberley', 'city': 'Cranbrook', 'resorts': 'Fernie, Kimberley', 'region': 'bc'},
    'YXE': {'name': 'Saskatoon', 'city': 'Saskatoon', 'resorts': 'Castle Mountain (drive)', 'region': 'prairies'},
    'YEG': {'name': 'Edmonton Intl', 'city': 'Edmonton', 'resorts': 'Marmot Basin, Jasper', 'region': 'alberta'},
}

OUTPUT_FILE = Path(__file__).parent / 'static' / 'data' / 'canadian-airports.json'


def parse_international_csv(csv_path):
    """
    Parse T-100 International CSV file.

    Returns monthly passenger totals for Canadian airports.
    """
    if not os.path.exists(csv_path):
        return None

    monthly_data = {}

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Check both origin and destination for Canadian airports
            origin = row.get('ORIGIN', '').strip()
            dest = row.get('DEST', '').strip()

            # We want passengers TO Canadian ski airports (from US)
            # OR from Canadian airports TO US (return trips)
            airport = None
            if dest in CANADIAN_SKI_AIRPORTS:
                airport = dest
            elif origin in CANADIAN_SKI_AIRPORTS:
                airport = origin
            else:
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

            # Accumulate passengers (inbound + outbound)
            monthly_data[key]['passengers'] += passengers

    return list(monthly_data.values())


def calculate_yoy_comparisons(monthly_data):
    """
    Calculate month-over-month year-over-year comparisons.
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
    print("T-100 INTERNATIONAL (CANADIAN) AIRPORT DATA")
    print("=" * 60)
    print()

    # Check for manually downloaded CSV
    csv_path = Path(__file__).parent / 'data' / 't100_international_raw.csv'

    if csv_path.exists():
        print(f"Found CSV: {csv_path}")
        print("Parsing international data...")

        monthly_data = parse_international_csv(csv_path)

        if monthly_data:
            print(f"  Parsed {len(monthly_data)} monthly records")

            # Calculate YoY comparisons
            print("\nCalculating YoY comparisons...")
            yoy_results = calculate_yoy_comparisons(monthly_data)

            # Build output structure matching US format
            output = {
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'data_source': 'BTS T-100 International Segment',
                'data_lag_note': 'BTS T-100 data typically 2-3 months behind.',
                'airports': {}
            }

            # Convert to the same format as US airports
            for record in monthly_data:
                airport = record['airport']
                month_key = f"{record['year']}-{record['month']:02d}"

                if airport not in output['airports']:
                    output['airports'][airport] = {}

                # Calculate YoY for this specific month
                prior_year_key = f"{record['year'] - 1}-{record['month']:02d}"
                prior_record = next(
                    (r for r in monthly_data
                     if r['airport'] == airport
                     and r['year'] == record['year'] - 1
                     and r['month'] == record['month']),
                    None
                )

                yoy_pct = None
                if prior_record and prior_record['passengers'] > 0:
                    yoy_pct = round(
                        ((record['passengers'] - prior_record['passengers']) / prior_record['passengers']) * 100,
                        2
                    )

                output['airports'][airport][month_key] = {
                    'passengers': record['passengers'],
                    'yoy_pct': yoy_pct
                }

            # Add data source info
            output['data_sources'] = {
                code: {
                    'source': 'BTS T-100 International',
                    'last_month_available': max(output['airports'].get(code, {}).keys(), default=None)
                }
                for code in output['airports']
            }

            # Save output
            OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(output, f, indent=2)

            print(f"\nOutput saved to: {OUTPUT_FILE}")

            # Print summary
            print("\nSUMMARY:")
            print("-" * 40)
            for airport in sorted(output['airports'].keys()):
                config = CANADIAN_SKI_AIRPORTS.get(airport, {})
                months = output['airports'][airport]
                latest_month = max(months.keys())
                latest = months[latest_month]
                yoy_str = f"{latest['yoy_pct']:+.1f}%" if latest['yoy_pct'] is not None else "N/A"
                print(f"  {airport} ({config.get('city', 'Unknown')}): {latest['passengers']:,} pax ({latest_month}, {yoy_str} YoY)")

            return

    # No CSV found - print instructions
    print("No T-100 International CSV found.")
    print("""
============================================================
MANUAL DOWNLOAD REQUIRED
============================================================

The BTS T-100 International data requires manual download:

1. Go to: https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoession_VQ=FHL

2. Select "T-100 International Segment (All Carriers)"

3. Choose fields:
   - YEAR
   - MONTH
   - ORIGIN (airport code)
   - DEST (airport code)
   - PASSENGERS

4. Filter by:
   - Origin Country: Canada OR
   - Dest Country: Canada

5. Download as CSV

6. Save to: data/t100_international_raw.csv

7. Re-run this script to process the data
============================================================
""")


if __name__ == '__main__':
    main()
