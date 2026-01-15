#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch IMS (Interactive Multisensor Snow and Ice Mapping System) data.

This script downloads and processes NOAA IMS snow cover data which covers
the entire Northern Hemisphere including Canada (unlike NOHRSC which is USA-only).

Data source: https://nsidc.org/data/g02156
Data access: https://noaadata.apps.nsidc.org/NOAA/G02156/

IMS Grid Values:
  0 = Outside Northern Hemisphere
  1 = Sea/Ocean
  2 = Land (no snow)
  3 = Sea Ice
  4 = Snow

Grid specifications (24km resolution):
  - 1024 x 1024 grid
  - Polar stereographic projection centered at 90°N
  - Vertical longitude: 80°W
  - Standard parallel: 60°N

Usage:
    python fetch_ims_snow_data.py [--date YYYY-MM-DD] [--output FILE]
"""

import os
import sys
import gzip
import math
import json
import urllib.request
import urllib.error
import ssl
from datetime import datetime, timedelta
from io import BytesIO


# IMS Grid constants (24km resolution)
IMS_NCOLS = 1024
IMS_NROWS = 1024
IMS_RESOLUTION_KM = 24

# Polar stereographic projection parameters
IMS_CENTER_LAT = 90.0  # North Pole
IMS_CENTER_LON = -80.0  # 80°W vertical
IMS_STANDARD_PARALLEL = 60.0
IMS_EARTH_RADIUS_KM = 6371.228

# Grid cell values
IMS_OUTSIDE = 0
IMS_SEA = 1
IMS_LAND = 2
IMS_SEA_ICE = 3
IMS_SNOW = 4


def print_safe(msg):
    """Print with flush for real-time output"""
    print(msg, flush=True)


def lat_lon_to_ims_grid(lat, lon):
    """
    Convert latitude/longitude to IMS grid coordinates (row, col).

    Uses polar stereographic projection:
    - True at 60°N
    - Centered on North Pole
    - Vertical longitude at 80°W

    Returns (row, col) or None if outside grid.
    """
    # Convert to radians
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    center_lon_rad = math.radians(IMS_CENTER_LON)
    std_parallel_rad = math.radians(IMS_STANDARD_PARALLEL)

    # Polar stereographic projection formulas
    # Scale factor at standard parallel
    k0 = (1 + math.sin(std_parallel_rad)) / 2

    # Compute the scale at the latitude
    if lat >= 90:
        x = 0
        y = 0
    else:
        # Distance from pole
        t = math.tan(math.pi/4 - lat_rad/2)
        rho = 2 * IMS_EARTH_RADIUS_KM * k0 * t

        # Compute x, y in km from pole
        delta_lon = lon_rad - center_lon_rad
        x = rho * math.sin(delta_lon)
        y = -rho * math.cos(delta_lon)

    # Convert km to grid cells
    # Grid is centered, so (512, 512) is approximately the pole
    col = int(IMS_NCOLS / 2 + x / IMS_RESOLUTION_KM)
    row = int(IMS_NROWS / 2 + y / IMS_RESOLUTION_KM)

    # Check bounds
    if 0 <= row < IMS_NROWS and 0 <= col < IMS_NCOLS:
        return (row, col)
    return None


def ims_grid_to_lat_lon(row, col):
    """
    Convert IMS grid coordinates to latitude/longitude.
    Inverse of lat_lon_to_ims_grid.
    """
    # Convert grid to km from center
    x = (col - IMS_NCOLS / 2) * IMS_RESOLUTION_KM
    y = (row - IMS_NROWS / 2) * IMS_RESOLUTION_KM

    # Polar stereographic inverse
    center_lon_rad = math.radians(IMS_CENTER_LON)
    std_parallel_rad = math.radians(IMS_STANDARD_PARALLEL)
    k0 = (1 + math.sin(std_parallel_rad)) / 2

    rho = math.sqrt(x*x + y*y)
    if rho == 0:
        return (90.0, 0.0)  # At pole

    c = 2 * math.atan(rho / (2 * IMS_EARTH_RADIUS_KM * k0))
    lat = math.asin(math.cos(c))
    lon = center_lon_rad + math.atan2(x, -y)

    return (math.degrees(lat), math.degrees(lon))


def fetch_ims_file(year, day_of_year, resolution='24km'):
    """
    Fetch IMS ASCII data for a specific date.

    Args:
        year: Year (e.g., 2025)
        day_of_year: Day of year (1-366)
        resolution: '24km', '4km', or '1km'

    Returns:
        2D list of grid values, or None if fetch failed
    """
    # Format day of year with leading zeros
    doy_str = f"{day_of_year:03d}"

    # Build URL
    base_url = "https://noaadata.apps.nsidc.org/NOAA/G02156"
    filename = f"ims{year}{doy_str}_00UTC_{resolution}_v1.3.asc.gz"
    url = f"{base_url}/{resolution}/{year}/{filename}"

    try:
        # Create SSL context that doesn't verify (NSIDC sometimes has cert issues)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python Snow Cover Tool'
        })

        with urllib.request.urlopen(req, timeout=60, context=ctx) as response:
            compressed_data = response.read()

        # Decompress
        decompressed = gzip.decompress(compressed_data)
        content = decompressed.decode('ascii', errors='ignore')

        # Parse ASCII grid
        lines = content.strip().split('\n')

        # Skip header lines (look for first line that's all digits)
        data_start = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and all(c in '01234' for c in stripped):
                data_start = i
                break

        # Parse grid data
        grid = []
        for line in lines[data_start:]:
            row = [int(c) for c in line.strip() if c in '01234']
            if len(row) > 0:
                grid.append(row)

        # Verify dimensions
        if len(grid) != IMS_NROWS:
            print_safe(f"  Warning: Expected {IMS_NROWS} rows, got {len(grid)}")

        return grid

    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None  # Data not available for this date
        print_safe(f"  HTTP Error {e.code}: {url}")
        return None
    except Exception as e:
        print_safe(f"  Error fetching {url}: {e}")
        return None


def calculate_snow_cover_percentage(grid, region_bounds=None):
    """
    Calculate snow cover percentage from IMS grid.

    Args:
        grid: 2D list of IMS values
        region_bounds: Optional dict with 'min_lat', 'max_lat', 'min_lon', 'max_lon'
                      If None, calculates for entire grid

    Returns:
        Dict with 'cover' percentage, 'snow_cells', 'land_cells'
    """
    if not grid:
        return None

    snow_cells = 0
    land_cells = 0  # Land includes snow-covered land

    for row_idx, row in enumerate(grid):
        for col_idx, val in enumerate(row):
            # If region specified, check bounds
            if region_bounds:
                lat, lon = ims_grid_to_lat_lon(row_idx, col_idx)
                if not (region_bounds['min_lat'] <= lat <= region_bounds['max_lat'] and
                        region_bounds['min_lon'] <= lon <= region_bounds['max_lon']):
                    continue

            if val == IMS_LAND:
                land_cells += 1
            elif val == IMS_SNOW:
                snow_cells += 1
                land_cells += 1  # Snow is on land

    if land_cells == 0:
        return {'cover': 0, 'snow_cells': 0, 'land_cells': 0}

    cover = round(100 * snow_cells / land_cells, 1)
    return {
        'cover': cover,
        'snow_cells': snow_cells,
        'land_cells': land_cells
    }


# Pre-defined region bounds for countries/regions
REGION_BOUNDS = {
    'usa': {
        'min_lat': 24.5,  # Southern tip of Florida Keys
        'max_lat': 49.0,  # Northern border (excluding Alaska)
        'min_lon': -125.0,  # Western coast
        'max_lon': -66.5   # Eastern coast
    },
    'usa_with_alaska': {
        'min_lat': 24.5,
        'max_lat': 71.5,  # Northern Alaska
        'min_lon': -180.0,
        'max_lon': -66.5
    },
    'canada': {
        'min_lat': 41.5,  # Southern Ontario
        'max_lat': 83.0,  # Northern islands
        'min_lon': -141.0,  # Yukon border
        'max_lon': -52.5   # Newfoundland
    },
    # Canadian provinces
    'british_columbia': {
        'min_lat': 48.3, 'max_lat': 60.0,
        'min_lon': -139.0, 'max_lon': -114.0
    },
    'alberta': {
        'min_lat': 49.0, 'max_lat': 60.0,
        'min_lon': -120.0, 'max_lon': -110.0
    },
    'saskatchewan': {
        'min_lat': 49.0, 'max_lat': 60.0,
        'min_lon': -110.0, 'max_lon': -101.5
    },
    'manitoba': {
        'min_lat': 49.0, 'max_lat': 60.0,
        'min_lon': -102.0, 'max_lon': -88.5
    },
    'ontario': {
        'min_lat': 41.5, 'max_lat': 56.9,
        'min_lon': -95.2, 'max_lon': -74.3
    },
    'quebec': {
        'min_lat': 45.0, 'max_lat': 62.5,
        'min_lon': -79.8, 'max_lon': -57.1
    },
    'atlantic': {  # NB, NS, PEI, NL combined
        'min_lat': 43.4, 'max_lat': 60.4,
        'min_lon': -67.5, 'max_lon': -52.5
    },
    # NSAA regions (approximate bounds)
    'rocky_mountain': {
        'min_lat': 31.0, 'max_lat': 49.0,
        'min_lon': -117.0, 'max_lon': -102.0
    },
    'pacific_northwest': {
        'min_lat': 42.0, 'max_lat': 49.0,
        'min_lon': -125.0, 'max_lon': -116.5
    },
    'pacific_southwest': {
        'min_lat': 32.0, 'max_lat': 42.0,
        'min_lon': -125.0, 'max_lon': -114.0
    },
    'midwest': {
        'min_lat': 36.5, 'max_lat': 49.0,
        'min_lon': -104.0, 'max_lon': -80.5
    },
    'northeast': {
        'min_lat': 38.5, 'max_lat': 47.5,
        'min_lon': -80.5, 'max_lon': -66.5
    },
    'southeast': {
        'min_lat': 24.5, 'max_lat': 39.0,
        'min_lon': -91.5, 'max_lon': -75.0
    }
}


def get_metro_snow_cover(grid, lat, lon, radius_km=50):
    """
    Get snow cover percentage around a metro area.

    Args:
        grid: IMS data grid
        lat, lon: Metro center coordinates
        radius_km: Radius to check (default 50km = ~2 grid cells at 24km)

    Returns:
        Snow cover percentage (0-100) or None if location outside grid
    """
    if not grid:
        return None

    center = lat_lon_to_ims_grid(lat, lon)
    if not center:
        return None

    center_row, center_col = center

    # Calculate grid cell radius
    cell_radius = max(1, int(radius_km / IMS_RESOLUTION_KM))

    snow_cells = 0
    land_cells = 0

    for dr in range(-cell_radius, cell_radius + 1):
        for dc in range(-cell_radius, cell_radius + 1):
            row = center_row + dr
            col = center_col + dc

            if 0 <= row < len(grid) and 0 <= col < len(grid[row]):
                val = grid[row][col]
                if val == IMS_LAND:
                    land_cells += 1
                elif val == IMS_SNOW:
                    snow_cells += 1
                    land_cells += 1

    if land_cells == 0:
        return 0

    return round(100 * snow_cells / land_cells, 1)


def fetch_ims_for_date(date, regions=None):
    """
    Fetch IMS data for a specific date and calculate snow cover for regions.

    Args:
        date: datetime object
        regions: List of region names to calculate, or None for all

    Returns:
        Dict with region snow cover percentages
    """
    year = date.year
    day_of_year = date.timetuple().tm_yday

    grid = fetch_ims_file(year, day_of_year)
    if not grid:
        return None

    if regions is None:
        regions = list(REGION_BOUNDS.keys())

    results = {
        'date': date.strftime('%Y-%m-%d'),
        'regions': {}
    }

    for region in regions:
        if region in REGION_BOUNDS:
            bounds = REGION_BOUNDS[region]
            stats = calculate_snow_cover_percentage(grid, bounds)
            if stats:
                results['regions'][region] = stats['cover']

    return results


def main():
    """Test IMS data fetching"""
    print_safe("IMS Snow Data Fetcher")
    print_safe("=" * 50)

    # Test with today's date
    today = datetime.now()
    yesterday = today - timedelta(days=1)

    print_safe(f"\nFetching IMS data for {yesterday.strftime('%Y-%m-%d')}...")

    # Get day of year
    year = yesterday.year
    doy = yesterday.timetuple().tm_yday

    print_safe(f"Year: {year}, Day of Year: {doy}")

    grid = fetch_ims_file(year, doy)

    if grid:
        print_safe(f"Grid loaded: {len(grid)} rows x {len(grid[0])} cols")

        # Calculate for key regions
        print_safe("\nSnow cover by region:")
        for region_name, bounds in REGION_BOUNDS.items():
            if region_name in ['usa', 'canada', 'british_columbia', 'ontario', 'quebec']:
                stats = calculate_snow_cover_percentage(grid, bounds)
                if stats:
                    print_safe(f"  {region_name}: {stats['cover']}% ({stats['snow_cells']:,} snow / {stats['land_cells']:,} land cells)")

        # Test metro lookup
        print_safe("\nMetro snow cover:")
        metros = [
            ('Denver', 39.7392, -104.9903),
            ('Toronto', 43.6532, -79.3832),
            ('Vancouver', 49.2827, -123.1207),
            ('Calgary', 51.0447, -114.0719),
            ('Montreal', 45.5017, -73.5673),
            ('Chicago', 41.8781, -87.6298),
        ]
        for name, lat, lon in metros:
            cover = get_metro_snow_cover(grid, lat, lon)
            print_safe(f"  {name}: {cover}%")
    else:
        print_safe("Failed to fetch IMS data")

    return 0


if __name__ == '__main__':
    sys.exit(main())
