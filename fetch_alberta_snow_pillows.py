#!/usr/bin/env python3
"""
Fetch real-time Alberta snow pillow data from rivers.alberta.ca

Outputs to static/data/alberta-snow-pillows.json for use in snotel.html
"""

import json
import requests
from datetime import datetime

# Configuration
BASE_URL = "https://rivers.alberta.ca"
MANIFEST_ENDPOINT = "/EnvironmentalDataService/ReadManifest"
OUTPUT_FILE = "static/data/alberta-snow-pillows.json"

# Alberta mountain pillow stations (from manifest analysis)
# These have real-time SW (Snow Water Equivalent) data
ALBERTA_PILLOW_STATIONS = [
    # Alberta EPA stations (05xx = South Saskatchewan, 07xx = Athabasca/Peace)
    "05AA809",  # Gardiner Creek
    "05AA817",  # South Racehorse Creek
    "05AB814",  # Sentinel Peak
    "05AD803",  # Akamina Pass 2
    "05BB803",  # Sunshine Village
    "05BF824",  # Three Isle Lake
    "05BJ805",  # Little Elbow Summit
    "05BL811",  # Lost Creek South
    "05CA805",  # Skoki Lodge
    "05DA807",  # Whiterabbit Creek
    "05DB802",  # Limestone Ridge
    "05DD804",  # Southesk
    "07BB811",  # Paddle Headwaters
    "07BB814",  # Twin Lakes
]


def fetch_manifest():
    """Fetch the environmental data manifest from rivers.alberta.ca"""
    url = f"{BASE_URL}{MANIFEST_ENDPOINT}"
    print(f"Fetching manifest from {url}...")

    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def get_station_json_url(station):
    """Extract the JSON data URL for a station"""
    datasets = station.get("datasets", [])
    for ds in datasets:
        if ds.get("dataset_location", "").endswith("_table.json"):
            return f"{BASE_URL}/apps/Basins/data/{ds['dataset_location']}"
    return None


def fetch_station_data(station_id, json_url):
    """Fetch real-time data for a single station"""
    try:
        response = requests.get(json_url, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Parse metadata to find SW column
        ts_metadata = data.get("ts_metadata", [])
        sw_col = None
        sd_col = None

        for i, meta in enumerate(ts_metadata):
            if meta.get("parameter_name") == "SW":
                sw_col = i
            elif meta.get("parameter_name") == "SD":
                sd_col = i

        if sw_col is None:
            return None

        # Get latest non-null SWE reading
        rows = data.get("data", [])
        for row in reversed(rows):
            values = row.get("values", [])
            if len(values) > sw_col + 1:
                timestamp = values[0]
                swe = values[sw_col + 1]
                sd = values[sd_col + 1] if sd_col is not None and len(values) > sd_col + 1 else None

                if swe is not None:
                    return {
                        "timestamp": timestamp,
                        "swe_mm": round(swe, 1) if swe else None,
                        "snow_depth_cm": round(sd, 1) if sd else None
                    }

        return None

    except Exception as e:
        print(f"  Error fetching {station_id}: {e}")
        return None


def main():
    print("=== Alberta Snow Pillow Data Fetch ===")
    print(f"Time: {datetime.utcnow().isoformat()}Z\n")

    # Fetch manifest
    manifest = fetch_manifest()
    stations = manifest.get("envdata_stations", [])
    print(f"Total stations in manifest: {len(stations)}")

    # Build lookup of stations by ID
    station_lookup = {s["station_number"]: s for s in stations}

    # Fetch data for Alberta pillow stations
    results = []

    print(f"\nFetching data for {len(ALBERTA_PILLOW_STATIONS)} Alberta pillow stations...")

    for station_id in ALBERTA_PILLOW_STATIONS:
        station = station_lookup.get(station_id)
        if not station:
            print(f"  [SKIP] {station_id} - not found in manifest")
            continue

        json_url = get_station_json_url(station)
        if not json_url:
            print(f"  [SKIP] {station_id} - no JSON endpoint")
            continue

        station_name = station.get("station_name", "Unknown")
        lat = station.get("station_latitude")
        lon = station.get("station_longitude")

        print(f"  [FETCH] {station_id} - {station_name}...", end=" ")

        data = fetch_station_data(station_id, json_url)

        if data:
            results.append({
                "station_id": station_id,
                "name": station_name,
                "lat": float(lat) if lat else None,
                "lon": float(lon) if lon else None,
                "swe_mm": data["swe_mm"],
                "snow_depth_cm": data["snow_depth_cm"],
                "timestamp": data["timestamp"]
            })
            print(f"SWE: {data['swe_mm']} mm")
        else:
            print("no data")

    # Calculate statistics
    swe_values = [r["swe_mm"] for r in results if r["swe_mm"] is not None]

    if swe_values:
        stats = {
            "count": len(swe_values),
            "mean_swe_mm": round(sum(swe_values) / len(swe_values), 1),
            "min_swe_mm": min(swe_values),
            "max_swe_mm": max(swe_values)
        }
    else:
        stats = {"count": 0}

    # Build output
    output = {
        "metadata": {
            "source": "rivers.alberta.ca",
            "fetched_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "description": "Real-time Snow Water Equivalent from Alberta mountain snow pillows"
        },
        "statistics": stats,
        "stations": results
    }

    # Write output
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n=== Summary ===")
    print(f"Stations with data: {stats.get('count', 0)}")
    if stats.get('count', 0) > 0:
        print(f"Mean SWE: {stats['mean_swe_mm']} mm")
        print(f"Range: {stats['min_swe_mm']} - {stats['max_swe_mm']} mm")
    print(f"\nOutput saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
