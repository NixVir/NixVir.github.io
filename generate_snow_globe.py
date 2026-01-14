#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Snow Cover Difference Globe Visualization

Creates a visually compelling globe image showing the difference between
current snow cover and same-day-last-year snow cover.

Colors:
- Blue: Snow exists this year but NOT last year (improved conditions)
- Red: Snow existed last year but NOT this year (worse conditions)
- White: Snow in both years (unchanged)
- Dark terrain: No snow either year

Requires: matplotlib, cartopy, numpy, pillow
Install: pip install matplotlib cartopy numpy pillow

Output: static/images/snow-globe.png
"""

import os
import sys
import json
import math
import gzip
import urllib.request
import ssl
from datetime import datetime, timedelta
from io import BytesIO

# Try to import visualization libraries
try:
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for server use
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, ListedColormap
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    HAS_VISUALIZATION = True
except ImportError as e:
    print(f"Warning: Missing visualization libraries: {e}")
    print("Install with: pip install matplotlib cartopy numpy")
    HAS_VISUALIZATION = False


# IMS Grid constants (24km resolution)
IMS_NCOLS = 1024
IMS_NROWS = 1024
IMS_RESOLUTION_KM = 24

# Polar stereographic projection parameters
IMS_CENTER_LAT = 90.0
IMS_CENTER_LON = -80.0
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


def ims_grid_to_lat_lon(row, col):
    """Convert IMS grid coordinates to latitude/longitude."""
    x = (col - IMS_NCOLS / 2) * IMS_RESOLUTION_KM
    y = (row - IMS_NROWS / 2) * IMS_RESOLUTION_KM

    center_lon_rad = math.radians(IMS_CENTER_LON)
    std_parallel_rad = math.radians(IMS_STANDARD_PARALLEL)
    k0 = (1 + math.sin(std_parallel_rad)) / 2

    rho = math.sqrt(x*x + y*y)
    if rho == 0:
        return (90.0, 0.0)

    c = 2 * math.atan(rho / (2 * IMS_EARTH_RADIUS_KM * k0))
    lat = math.asin(math.cos(c))
    lon = center_lon_rad + math.atan2(x, -y)

    return (math.degrees(lat), math.degrees(lon))


def fetch_ims_file(year, day_of_year, resolution='24km'):
    """Fetch IMS ASCII data for a specific date."""
    doy_str = f"{day_of_year:03d}"
    base_url = "https://noaadata.apps.nsidc.org/NOAA/G02156"
    filename = f"ims{year}{doy_str}_00UTC_{resolution}_v1.3.asc.gz"
    url = f"{base_url}/{resolution}/{year}/{filename}"

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NixVir Snow Globe Generator'
        })

        with urllib.request.urlopen(req, timeout=120, context=ctx) as response:
            compressed_data = response.read()

        decompressed = gzip.decompress(compressed_data)
        content = decompressed.decode('ascii', errors='ignore')

        lines = content.strip().split('\n')

        # Skip header lines
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

        return grid

    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        print_safe(f"  HTTP Error {e.code}: {url}")
        return None
    except Exception as e:
        print_safe(f"  Error fetching {url}: {e}")
        return None


def get_ims_grid_for_date(target_date):
    """Fetch IMS grid for a specific date, trying multiple days if needed."""
    for days_offset in range(5):  # Try target date and up to 4 days back
        check_date = target_date - timedelta(days=days_offset)
        year = check_date.year
        doy = check_date.timetuple().tm_yday

        print_safe(f"  Trying {check_date.strftime('%Y-%m-%d')} (DOY {doy})...")
        grid = fetch_ims_file(year, doy)

        if grid:
            print_safe(f"  Got data for {check_date.strftime('%Y-%m-%d')}")
            return grid, check_date

    return None, None


def compute_difference_grid(current_grid, prior_grid):
    """
    Compute difference between current and prior year snow cover.

    Returns numpy array with values:
    -1: Snow lost (was there, now gone) - RED
     0: No change (either no snow both years, or snow both years)
    +1: Snow gained (wasn't there, now is) - BLUE
     2: Snow both years - WHITE
    """
    if not current_grid or not prior_grid:
        return None

    rows = min(len(current_grid), len(prior_grid))
    cols = min(len(current_grid[0]), len(prior_grid[0]))

    diff = np.zeros((rows, cols), dtype=np.int8)

    for r in range(rows):
        for c in range(cols):
            curr_val = current_grid[r][c] if c < len(current_grid[r]) else 0
            prior_val = prior_grid[r][c] if c < len(prior_grid[r]) else 0

            curr_snow = curr_val == IMS_SNOW
            prior_snow = prior_val == IMS_SNOW
            curr_land = curr_val in [IMS_LAND, IMS_SNOW]
            prior_land = prior_val in [IMS_LAND, IMS_SNOW]

            # Only consider land areas
            if not (curr_land or prior_land):
                diff[r, c] = -99  # Not land
            elif curr_snow and prior_snow:
                diff[r, c] = 2  # Snow both years
            elif curr_snow and not prior_snow:
                diff[r, c] = 1  # Snow gained
            elif not curr_snow and prior_snow:
                diff[r, c] = -1  # Snow lost
            else:
                diff[r, c] = 0  # No snow either year

    return diff


def generate_globe_image(diff_grid, output_path, current_date, prior_date, snow_stats):
    """
    Generate a clean globe visualization - just the map with a simple legend.
    Stats are displayed via HTML overlay, not baked into the image.
    Image is square for clean display in widget.
    """
    if not HAS_VISUALIZATION:
        print_safe("Cannot generate image - missing visualization libraries")
        return False

    print_safe("Generating globe visualization...")

    # Build lat/lon arrays from IMS grid
    rows, cols = diff_grid.shape
    lats = np.zeros((rows, cols))
    lons = np.zeros((rows, cols))

    print_safe("  Converting grid coordinates to lat/lon...")
    for r in range(rows):
        for c in range(cols):
            lat, lon = ims_grid_to_lat_lon(r, c)
            lats[r, c] = lat
            lons[r, c] = lon

    # Filter to North America region
    na_mask = (lats >= 20) & (lats <= 75) & (lons >= -170) & (lons <= -50)

    # Create square figure - globe fills most of it
    fig = plt.figure(figsize=(6, 6), facecolor='#0f1a2e')

    # Create axes for the globe - nearly full figure, with room for legend at bottom
    # Use NearsidePerspective for more zoom control, centered on North America
    projection = ccrs.NearsidePerspective(
        central_longitude=-95,  # Center on US/Canada
        central_latitude=45,    # Center latitude
        satellite_height=4500000  # Lower = more zoomed in (default is ~35M)
    )
    ax = fig.add_axes([0.02, 0.12, 0.96, 0.86], projection=projection, facecolor='#0f1a2e')

    # Set global extent (projection handles the zoom)
    ax.set_global()

    # Add ocean with dark color
    ax.add_feature(cfeature.OCEAN, facecolor='#0d2137', zorder=0)

    # Add land with dark terrain color
    ax.add_feature(cfeature.LAND, facecolor='#1a3a2a', zorder=1)

    # Add subtle coastlines
    ax.add_feature(cfeature.COASTLINE, edgecolor='#3a6a5a', linewidth=0.5, zorder=3)

    # Add country borders
    ax.add_feature(cfeature.BORDERS, edgecolor='#4a7a6a', linewidth=0.3, zorder=3)

    # Create custom colormap for the difference
    # -1 = red (snow lost), 0 = transparent, 1 = blue (snow gained), 2 = white (both years)
    colors_list = [
        (0.9, 0.25, 0.25, 0.85),  # -1: Red (snow lost) - brighter
        (0.0, 0.0, 0.0, 0.0),     # 0: Transparent (no snow either year)
        (0.25, 0.55, 0.95, 0.85), # 1: Blue (snow gained) - brighter
        (0.98, 0.98, 1.0, 0.95)   # 2: White (snow both years)
    ]

    # Create discrete colormap
    cmap = ListedColormap(colors_list)

    # Plot the difference data
    print_safe("  Rendering snow difference layer...")

    # Mask out non-land and non-NA areas
    masked_diff = np.ma.masked_where(
        (diff_grid == -99) | ~na_mask,
        diff_grid
    )

    # Plot using pcolormesh
    ax.pcolormesh(
        lons, lats, masked_diff,
        cmap=cmap,
        vmin=-1.5, vmax=2.5,
        transform=ccrs.PlateCarree(),
        zorder=2,
        alpha=0.9
    )

    # Add globe outline/limb - thicker for visibility
    ax.spines['geo'].set_edgecolor('#5a9a8a')
    ax.spines['geo'].set_linewidth(3)

    # === SIMPLE LEGEND AT BOTTOM - Large colored squares with short labels ===
    legend_y = 0.04
    legend_items = [
        ('#4090f0', 'More'),
        ('#f8f8ff', 'Same'),
        ('#f05050', 'Less'),
    ]

    # Center the legend horizontally
    total_legend_width = 0.7
    item_spacing = total_legend_width / len(legend_items)
    start_x = (1.0 - total_legend_width) / 2

    for i, (color, label) in enumerate(legend_items):
        x_pos = start_x + i * item_spacing + 0.02
        # Draw colored square - large enough to see
        fig.patches.append(plt.Rectangle((x_pos, legend_y - 0.015), 0.05, 0.05,
                                         facecolor=color, edgecolor='#6aaa9a',
                                         linewidth=1.5, transform=fig.transFigure))
        # Label next to square - large and bold
        fig.text(x_pos + 0.07, legend_y + 0.01, label, ha='left', va='center',
                 fontsize=16, color='white', fontweight='bold', fontfamily='sans-serif')

    # Save at high DPI for crisp rendering at small sizes
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=200, facecolor='#0f1a2e',
                edgecolor='none', bbox_inches='tight', pad_inches=0.02)
    plt.close()

    print_safe(f"  Saved globe image to {output_path}")
    return True


def calculate_stats_from_grids(current_grid, prior_grid):
    """Calculate snow cover statistics from the grids."""

    # USA bounds (CONUS)
    usa_bounds = {
        'min_lat': 24.5, 'max_lat': 49.0,
        'min_lon': -125.0, 'max_lon': -66.5
    }

    # Canada bounds
    canada_bounds = {
        'min_lat': 41.5, 'max_lat': 83.0,
        'min_lon': -141.0, 'max_lon': -52.5
    }

    def calc_cover(grid, bounds):
        """Calculate snow cover for a region."""
        snow_cells = 0
        land_cells = 0

        for r, row in enumerate(grid):
            for c, val in enumerate(row):
                lat, lon = ims_grid_to_lat_lon(r, c)

                if not (bounds['min_lat'] <= lat <= bounds['max_lat'] and
                        bounds['min_lon'] <= lon <= bounds['max_lon']):
                    continue

                if val == IMS_LAND:
                    land_cells += 1
                elif val == IMS_SNOW:
                    snow_cells += 1
                    land_cells += 1

        if land_cells == 0:
            return None
        return round(100 * snow_cells / land_cells, 1)

    usa_cover = calc_cover(current_grid, usa_bounds)
    canada_cover = calc_cover(current_grid, canada_bounds)

    # Calculate combined (weighted by land area)
    usa_area = 3797000  # sq mi
    canada_area = 3855000  # sq mi (approximate land area)

    if usa_cover is not None and canada_cover is not None:
        combined = (usa_cover * usa_area + canada_cover * canada_area) / (usa_area + canada_area)
        combined = round(combined, 1)
    else:
        combined = usa_cover or canada_cover

    # Calculate prior year stats for comparison
    usa_prior = calc_cover(prior_grid, usa_bounds) if prior_grid else None
    canada_prior = calc_cover(prior_grid, canada_bounds) if prior_grid else None

    return {
        'usa_cover': usa_cover,
        'canada_cover': canada_cover,
        'combined_cover': combined,
        'usa_prior': usa_prior,
        'canada_prior': canada_prior,
        'usa_change': round(usa_cover - usa_prior, 1) if usa_cover and usa_prior else None,
        'canada_change': round(canada_cover - canada_prior, 1) if canada_cover and canada_prior else None
    }


def save_globe_metadata(output_path, current_date, prior_date, snow_stats):
    """Save metadata JSON alongside the globe image."""
    metadata = {
        'generated': datetime.now().strftime('%Y-%m-%d %H:%M UTC'),
        'current_date': current_date.strftime('%Y-%m-%d'),
        'prior_date': prior_date.strftime('%Y-%m-%d'),
        'stats': snow_stats
    }

    json_path = output_path.replace('.png', '.json')
    with open(json_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print_safe(f"  Saved metadata to {json_path}")


def main():
    """Main entry point."""
    print_safe("=" * 60)
    print_safe("Snow Cover Difference Globe Generator")
    print_safe("=" * 60)

    if not HAS_VISUALIZATION:
        print_safe("\nERROR: Missing required libraries.")
        print_safe("Install with: pip install matplotlib cartopy numpy")
        return 1

    # Determine dates
    today = datetime.now()
    prior_year_date = today.replace(year=today.year - 1)

    print_safe(f"\nCurrent date target: {today.strftime('%Y-%m-%d')}")
    print_safe(f"Prior year target: {prior_year_date.strftime('%Y-%m-%d')}")

    # Fetch current data
    print_safe("\nFetching current snow cover data...")
    current_grid, current_actual_date = get_ims_grid_for_date(today)

    if not current_grid:
        print_safe("ERROR: Could not fetch current IMS data")
        return 1

    # Fetch prior year data
    print_safe("\nFetching prior year snow cover data...")
    prior_grid, prior_actual_date = get_ims_grid_for_date(prior_year_date)

    if not prior_grid:
        print_safe("ERROR: Could not fetch prior year IMS data")
        return 1

    # Compute difference
    print_safe("\nComputing snow cover difference...")
    diff_grid = compute_difference_grid(current_grid, prior_grid)

    if diff_grid is None:
        print_safe("ERROR: Could not compute difference grid")
        return 1

    # Calculate statistics
    print_safe("\nCalculating statistics...")
    snow_stats = calculate_stats_from_grids(current_grid, prior_grid)
    print_safe(f"  USA: {snow_stats['usa_cover']}% (vs {snow_stats['usa_prior']}% last year)")
    print_safe(f"  Canada: {snow_stats['canada_cover']}% (vs {snow_stats['canada_prior']}% last year)")
    print_safe(f"  Combined: {snow_stats['combined_cover']}%")

    # Generate globe image
    output_path = 'static/images/snow-globe.png'
    success = generate_globe_image(
        diff_grid,
        output_path,
        current_actual_date,
        prior_actual_date,
        snow_stats
    )

    if not success:
        print_safe("ERROR: Failed to generate globe image")
        return 1

    # Save metadata
    save_globe_metadata(output_path, current_actual_date, prior_actual_date, snow_stats)

    print_safe("\n" + "=" * 60)
    print_safe("SUCCESS - Globe visualization generated")
    print_safe("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
