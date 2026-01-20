"""
Fetch Hydro-Québec Snow Water Equivalent Data
Downloads current SWE and snow depth from Hydro-Québec's GMON sensor network.

Data Source: Hydro-Québec Open Data Portal
API: https://donnees.hydroquebec.com/explore/dataset/donnees-hydrometeorologiques/
License: CC BY-NC-SA 4.0

Output: static/data/quebec-snow-stations.json
"""

import requests
import json
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

# Configuration
OUTPUT_DIR = Path(__file__).parent / "static" / "data"
OUTPUT_FILE = OUTPUT_DIR / "quebec-snow-stations.json"

# Hydro-Québec OpenDataSoft API
BASE_URL = "https://donnees.hydroquebec.com/api/explore/v2.1/catalog/datasets/donnees-hydrometeorologiques/exports/json"

# Query for SWE data (Équivalent en eau de la neige)
SWE_QUERY = "composition_depil_type_point_donnee = 'Équivalent en eau de la neige'"

# Query for snow depth data (Épaisseur du manteau neigeux)
DEPTH_QUERY = "composition_depil_type_point_donnee = 'Épaisseur du manteau neigeux'"


def fetch_snow_data(query, data_type):
    """Fetch snow data from Hydro-Québec API"""
    print(f"Fetching {data_type} data from Hydro-Québec...")

    params = {
        'where': query,
        'limit': -1,  # No limit
        'timezone': 'UTC'
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=120)
        response.raise_for_status()
        data = response.json()
        print(f"  Fetched {len(data)} {data_type} records")
        return data
    except requests.exceptions.RequestException as e:
        print(f"  Error fetching {data_type}: {e}")
        return []


def process_stations(swe_data, depth_data):
    """Process and combine SWE and snow depth data by station"""

    # Group by station, keeping only the most recent reading
    stations = {}

    # Process SWE data
    for record in swe_data:
        station_id = record.get('identifiant')
        if not station_id:
            continue

        # Parse date and value
        date_str = record.get('date')
        value_str = record.get('valeur')

        # Skip header rows
        if date_str == 'Donnees' or not value_str:
            continue

        try:
            # Parse date: "2026/01/10 16:00:00Z"
            date_obj = datetime.strptime(date_str, "%Y/%m/%d %H:%M:%SZ")
            date_obj = date_obj.replace(tzinfo=timezone.utc)
            swe_mm = float(value_str)
        except (ValueError, TypeError):
            continue

        # Skip negative or unreasonable values
        if swe_mm < 0 or swe_mm > 2000:
            continue

        # Initialize or update station
        if station_id not in stations:
            stations[station_id] = {
                'id': station_id,
                'name': record.get('nom', '').strip(),
                'lat': record.get('ycoord'),
                'lon': record.get('xcoord'),
                'elevation_m': record.get('zcoord'),
                'region': record.get('regionqc'),
                'swe_mm': None,
                'swe_date': None,
                'snow_depth_cm': None,
                'depth_date': None
            }

        # Keep most recent SWE reading
        if stations[station_id]['swe_date'] is None or date_obj > stations[station_id]['swe_date']:
            stations[station_id]['swe_mm'] = swe_mm
            stations[station_id]['swe_date'] = date_obj

    # Process snow depth data
    for record in depth_data:
        station_id = record.get('identifiant')
        if not station_id or station_id not in stations:
            continue

        date_str = record.get('date')
        value_str = record.get('valeur')

        if date_str == 'Donnees' or not value_str:
            continue

        try:
            date_obj = datetime.strptime(date_str, "%Y/%m/%d %H:%M:%SZ")
            date_obj = date_obj.replace(tzinfo=timezone.utc)
            depth_cm = float(value_str)
        except (ValueError, TypeError):
            continue

        if depth_cm < 0 or depth_cm > 500:
            continue

        # Keep most recent depth reading
        if stations[station_id]['depth_date'] is None or date_obj > stations[station_id]['depth_date']:
            stations[station_id]['snow_depth_cm'] = depth_cm
            stations[station_id]['depth_date'] = date_obj

    return stations


def main():
    print("=" * 60)
    print("Hydro-Québec Snow Data Fetch")
    print("=" * 60)
    print()

    # Fetch both SWE and snow depth data
    swe_data = fetch_snow_data(SWE_QUERY, "SWE")
    depth_data = fetch_snow_data(DEPTH_QUERY, "snow depth")

    if not swe_data:
        print("ERROR: No SWE data retrieved")
        return

    # Process into stations
    stations = process_stations(swe_data, depth_data)

    # Filter to stations with valid SWE data
    valid_stations = []
    for station in stations.values():
        if station['swe_mm'] is not None and station['lat'] is not None:
            # Convert to output format
            output_station = {
                'id': station['id'],
                'name': station['name'],
                'lat': station['lat'],
                'lon': station['lon'],
                'elevation_m': station['elevation_m'],
                'region': station['region'],
                'swe_mm': round(station['swe_mm'], 1),
                'swe_inches': round(station['swe_mm'] / 25.4, 1),
                'snow_depth_cm': round(station['snow_depth_cm'], 1) if station['snow_depth_cm'] else None,
                'snow_depth_inches': round(station['snow_depth_cm'] / 2.54, 1) if station['snow_depth_cm'] else None,
                'timestamp': station['swe_date'].isoformat() if station['swe_date'] else None
            }
            valid_stations.append(output_station)

    # Sort by name
    valid_stations.sort(key=lambda x: x['name'])

    # Find most recent timestamp
    latest_timestamp = None
    for s in valid_stations:
        if s['timestamp']:
            ts = datetime.fromisoformat(s['timestamp'])
            if latest_timestamp is None or ts > latest_timestamp:
                latest_timestamp = ts

    # Calculate statistics
    swe_values = [s['swe_mm'] for s in valid_stations if s['swe_mm']]
    mean_swe = round(sum(swe_values) / len(swe_values), 1) if swe_values else 0

    # Group by region
    regions = defaultdict(int)
    for s in valid_stations:
        if s['region']:
            regions[s['region']] += 1

    # Build output
    output = {
        'generated': datetime.now(timezone.utc).isoformat(),
        'source': 'Hydro-Québec',
        'source_url': 'https://donnees.hydroquebec.com/explore/dataset/donnees-hydrometeorologiques/',
        'license': 'CC BY-NC-SA 4.0',
        'note': 'SWE from GMON gamma radiation sensors. Updated every 6 hours.',
        'data_timestamp': latest_timestamp.isoformat() if latest_timestamp else None,
        'statistics': {
            'count': len(valid_stations),
            'with_swe': len([s for s in valid_stations if s['swe_mm']]),
            'with_depth': len([s for s in valid_stations if s['snow_depth_cm']]),
            'mean_swe_mm': mean_swe,
            'regions': dict(regions)
        },
        'stations': valid_stations
    }

    # Print summary
    print(f"\n=== Summary ===")
    print(f"  Total stations with SWE data: {len(valid_stations)}")
    print(f"  Mean SWE: {mean_swe} mm ({round(mean_swe/25.4, 1)} in)")
    print(f"  Regions: {dict(regions)}")
    if latest_timestamp:
        print(f"  Latest data: {latest_timestamp.strftime('%Y-%m-%d %H:%M UTC')}")

    # Save to file
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nSaving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    file_size = OUTPUT_FILE.stat().st_size
    print(f"  Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")

    print()
    print("=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == '__main__':
    main()
