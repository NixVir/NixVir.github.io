"""
Fetch British Columbia Snow Basin Indices from BC River Forecast Centre

Downloads current snowpack conditions (% of normal) for BC snow basins.
Data source: BC River Forecast Centre via ArcGIS REST API

API Endpoint: https://services6.arcgis.com/ubm4tcTYICKBpist/arcgis/rest/services/Snow_Basins_Indices_View/FeatureServer/0

Output: static/data/bc-snow-basins.json (GeoJSON with SBI values)
"""

import requests
import json
from datetime import datetime
from pathlib import Path

# Configuration
OUTPUT_DIR = Path(__file__).parent / "static" / "data"
OUTPUT_FILE = OUTPUT_DIR / "bc-snow-basins.json"

# BC River Forecast Centre ArcGIS REST API
BC_SBI_URL = "https://services6.arcgis.com/ubm4tcTYICKBpist/arcgis/rest/services/Snow_Basins_Indices_View/FeatureServer/0/query"


def fetch_bc_basins():
    """Fetch BC snow basin polygons with SBI values from ArcGIS REST API"""
    print("Fetching BC Snow Basin Indices from ArcGIS REST API...")

    params = {
        'where': '1=1',  # All features
        'outFields': 'basinName,basinID,Snow_Basin_Index,Updated,Date_Calculated_For,Previous_Year_Index',
        'returnGeometry': 'true',
        'outSR': '4326',  # WGS84 for Leaflet compatibility
        'f': 'geojson'  # GeoJSON format
    }

    try:
        response = requests.get(BC_SBI_URL, params=params, timeout=60)
        response.raise_for_status()

        data = response.json()

        if 'features' not in data:
            print(f"  ERROR: No features in response")
            return None

        print(f"  Found {len(data['features'])} basins")
        return data

    except requests.RequestException as e:
        print(f"  ERROR fetching data: {e}")
        return None


def process_basin_data(geojson):
    """Process and normalize the basin data"""
    print("Processing basin data...")

    # Track statistics
    stats = {
        'count': 0,
        'with_data': 0,
        'below_normal': 0,
        'at_or_above_normal': 0,
        'mean_sbi': 0
    }

    sbi_values = []
    data_date = None

    for feature in geojson['features']:
        props = feature['properties']

        # Normalize property names for frontend compatibility
        sbi = props.get('Snow_Basin_Index')
        basin_name = props.get('basinName', 'Unknown')
        basin_id = props.get('basinID')

        # Convert timestamps (ArcGIS returns milliseconds since epoch)
        updated_ms = props.get('Updated')
        calc_date_ms = props.get('Date_Calculated_For')

        if calc_date_ms and not data_date:
            data_date = datetime.fromtimestamp(calc_date_ms / 1000).strftime('%Y-%m-%d')

        # Rename properties for consistency with US HUC4 data
        feature['properties'] = {
            'name': basin_name,
            'basin_id': basin_id,
            'mean_pct': int(round(sbi)) if sbi is not None else None,
            'previous_year_pct': props.get('Previous_Year_Index'),
            'updated': datetime.fromtimestamp(updated_ms / 1000).isoformat() if updated_ms else None,
            'data_date': data_date
        }

        stats['count'] += 1

        if sbi is not None:
            stats['with_data'] += 1
            sbi_values.append(sbi)

            if sbi < 90:
                stats['below_normal'] += 1
            else:
                stats['at_or_above_normal'] += 1

    # Calculate mean SBI
    if sbi_values:
        stats['mean_sbi'] = int(round(sum(sbi_values) / len(sbi_values)))

    return geojson, stats, data_date


def simplify_geometry(geojson, tolerance=0.01):
    """
    Simplify geometry to reduce file size.
    Note: This is a basic implementation. For production, consider using
    shapely or a proper geometry library for Douglas-Peucker simplification.
    """
    # For now, just reduce coordinate precision to 4 decimal places (~11m accuracy)
    # This is sufficient for visualization and significantly reduces file size

    def round_coords(coords):
        if isinstance(coords[0], (int, float)):
            # It's a point [lon, lat]
            return [round(coords[0], 4), round(coords[1], 4)]
        else:
            # It's a nested array
            return [round_coords(c) for c in coords]

    for feature in geojson['features']:
        geom = feature.get('geometry', {})
        if 'coordinates' in geom:
            geom['coordinates'] = round_coords(geom['coordinates'])

    return geojson


def main():
    print("=" * 60)
    print("BC Snow Basin Indices Data Fetch")
    print("=" * 60)
    print()

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Fetch basin data
    geojson = fetch_bc_basins()

    if not geojson:
        print("\nFailed to fetch basin data")
        return 1

    # Process and normalize
    geojson, stats, data_date = process_basin_data(geojson)

    # Simplify geometry to reduce file size
    geojson = simplify_geometry(geojson)

    # Add metadata
    output = {
        'type': 'FeatureCollection',
        'generated': datetime.now().isoformat(),
        'data_date': data_date,
        'source': 'BC River Forecast Centre',
        'source_url': 'https://www2.gov.bc.ca/gov/content/environment/air-land-water/water/drought-flooding-dikes-dams/river-forecast-centre',
        'statistics': stats,
        'features': geojson['features']
    }

    # Print summary
    print(f"\n=== Summary ===")
    print(f"  Total basins: {stats['count']}")
    print(f"  Basins with SBI data: {stats['with_data']}")
    print(f"  Mean SBI: {stats['mean_sbi']}%")
    print(f"  Below normal (<90%): {stats['below_normal']}")
    print(f"  At/above normal (>=90%): {stats['at_or_above_normal']}")
    print(f"  Data date: {data_date}")

    # Save to file
    print(f"\nSaving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f)  # No indent for smaller file size

    file_size = OUTPUT_FILE.stat().st_size
    print(f"  Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    exit(main())
