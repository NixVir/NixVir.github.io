"""
Fetch SNOTEL Snow Water Equivalent Data
Downloads current snowpack conditions from NRCS AWDB for all western US stations

Data Source: NRCS National Water and Climate Center
API: https://wcc.sc.egov.usda.gov/reportGenerator/

Output: static/data/snotel-snowpack.json
"""

import requests
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from io import StringIO

# Configuration
OUTPUT_DIR = Path(__file__).parent / "static" / "data"
OUTPUT_FILE = OUTPUT_DIR / "snotel-snowpack.json"

# NRCS Report Generator API
BASE_URL = "https://wcc.sc.egov.usda.gov/reportGenerator/view_csv"

# Query for all active SNOTEL stations with SWE data
# network=SNTL (SNOTEL), element=WTEQ (Snow Water Equivalent)
# outServiceDate=2100-01-01 filters to only active stations
STATION_QUERY = (
    "customMultipleStationReport/daily/"
    "network=%22SNTL%22%20AND%20element=%22WTEQ%22%20AND%20outServiceDate=%222100-01-01%22%7Cname/"
    "0,0/"  # Today only
    "stationId,state,name,latitude,longitude,elevation,"
    "WTEQ::value,WTEQ::pctOfMedian_1991"
    "?fitToScreen=false"
)


def fetch_snotel_data():
    """Fetch current SNOTEL data from NRCS"""
    print("Fetching SNOTEL data from NRCS...")

    url = f"{BASE_URL}/{STATION_QUERY}"
    print(f"  URL: {url[:100]}...")

    try:
        response = requests.get(url, timeout=120)
        response.raise_for_status()

        # Parse CSV, skipping comment lines
        lines = response.text.split('\n')
        data_lines = [line for line in lines if not line.startswith('#') and line.strip()]

        if not data_lines:
            print("  ERROR: No data received")
            return None

        # Parse CSV
        reader = csv.DictReader(data_lines)
        stations = []

        for row in reader:
            try:
                # Parse station data
                station = {
                    'id': row.get('Station Id', '').strip(),
                    'state': row.get('State', '').strip(),
                    'name': row.get('Station Name', '').strip(),
                    'lat': float(row.get('Latitude', 0)),
                    'lon': float(row.get('Longitude', 0)),
                    'elevation_ft': int(float(row.get('Elevation (ft)', 0) or 0)),
                }

                # SWE value (inches)
                swe_str = row.get('Snow Water Equivalent (in) Start of Day Values', '').strip()
                station['swe_inches'] = float(swe_str) if swe_str else None

                # Percent of median
                pct_str = row.get('Snow Water Equivalent % of Median (1991-2020)', '').strip()
                station['pct_median'] = int(float(pct_str)) if pct_str else None

                # Skip stations without coordinates
                if station['lat'] and station['lon']:
                    stations.append(station)

            except (ValueError, KeyError) as e:
                # Skip malformed rows
                continue

        print(f"  Fetched {len(stations)} stations")
        return stations

    except requests.RequestException as e:
        print(f"  ERROR: {e}")
        return None


def calculate_statistics(stations):
    """Calculate summary statistics by state and region"""

    # Filter stations with valid percent median data
    valid_stations = [s for s in stations if s['pct_median'] is not None]

    if not valid_stations:
        return {}

    # Overall statistics
    pct_values = [s['pct_median'] for s in valid_stations]
    overall = {
        'count': len(valid_stations),
        'mean_pct': round(sum(pct_values) / len(pct_values), 1),
        'median_pct': sorted(pct_values)[len(pct_values) // 2],
        'min_pct': min(pct_values),
        'max_pct': max(pct_values),
        'below_normal': len([p for p in pct_values if p < 90]),
        'normal': len([p for p in pct_values if 90 <= p <= 110]),
        'above_normal': len([p for p in pct_values if p > 110]),
    }

    # By state
    by_state = {}
    states = set(s['state'] for s in valid_stations)

    for state in sorted(states):
        state_stations = [s for s in valid_stations if s['state'] == state]
        state_pcts = [s['pct_median'] for s in state_stations]

        by_state[state] = {
            'count': len(state_stations),
            'mean_pct': round(sum(state_pcts) / len(state_pcts), 1),
            'below_normal': len([p for p in state_pcts if p < 90]),
            'normal': len([p for p in state_pcts if 90 <= p <= 110]),
            'above_normal': len([p for p in state_pcts if p > 110]),
        }

    # Define ski regions (matching NSAA regions)
    region_states = {
        'Rocky Mountain': ['CO', 'UT', 'WY', 'MT', 'ID', 'NM'],
        'Pacific Northwest': ['WA', 'OR'],
        'Pacific Southwest': ['CA', 'NV', 'AZ'],
        'Intermountain': ['UT', 'ID', 'WY', 'NV'],
    }

    by_region = {}
    for region, region_state_list in region_states.items():
        region_stations = [s for s in valid_stations if s['state'] in region_state_list]
        if region_stations:
            region_pcts = [s['pct_median'] for s in region_stations]
            by_region[region] = {
                'count': len(region_stations),
                'mean_pct': round(sum(region_pcts) / len(region_pcts), 1),
                'states': region_state_list,
            }

    return {
        'overall': overall,
        'by_state': by_state,
        'by_region': by_region,
    }


def generate_output(stations, stats):
    """Generate JSON output file"""

    output = {
        'generated': datetime.now().isoformat(),
        'source': 'NRCS National Water and Climate Center',
        'source_url': 'https://www.nrcs.usda.gov/wps/portal/wcc/home/',
        'baseline': '1991-2020 median',
        'units': {
            'swe': 'inches',
            'pct_median': 'percent of 1991-2020 median',
            'elevation': 'feet',
        },
        'statistics': stats,
        'stations': stations,
    }

    return output


def main():
    print("="*60)
    print("SNOTEL Snowpack Data Fetch")
    print("="*60)
    print()

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Fetch data
    stations = fetch_snotel_data()

    if not stations:
        print("\nFailed to fetch SNOTEL data")
        return

    # Calculate statistics
    print("\nCalculating statistics...")
    stats = calculate_statistics(stations)

    # Print summary
    if stats.get('overall'):
        overall = stats['overall']
        print(f"\n=== Overall Summary ===")
        print(f"  Stations with data: {overall['count']}")
        print(f"  Mean % of median: {overall['mean_pct']}%")
        print(f"  Below normal (<90%): {overall['below_normal']} stations")
        print(f"  Normal (90-110%): {overall['normal']} stations")
        print(f"  Above normal (>110%): {overall['above_normal']} stations")

    if stats.get('by_state'):
        print(f"\n=== By State ===")
        for state, data in sorted(stats['by_state'].items(), key=lambda x: x[1]['mean_pct']):
            print(f"  {state}: {data['mean_pct']}% ({data['count']} stations)")

    # Generate output
    output = generate_output(stations, stats)

    # Save to file
    print(f"\nSaving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    file_size = OUTPUT_FILE.stat().st_size
    print(f"  Size: {file_size:,} bytes")

    print("\n" + "="*60)
    print("Done!")
    print("="*60)


if __name__ == '__main__':
    main()
