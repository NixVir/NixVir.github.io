#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
North American Snow Cover Data Aggregator

Fetches snow cover data from multiple real sources:
- NOAA NOHRSC (National Operational Hydrologic Remote Sensing Center) - U.S. snow statistics
- Rutgers Global Snow Lab - North American snow extent
- Copernicus CLMS Snow Cover Extent - Satellite-derived snow cover (via Sentinel Hub)
- Environment Canada - Canadian city weather data
- NWS Weather API - U.S. metro area conditions

Outputs JSON for the snow cover dashboard.
"""

import json
import time
import os
import sys
import re
import urllib.request
import urllib.error
import urllib.parse
import ssl
from datetime import datetime, timedelta
from html import unescape
import xml.etree.ElementTree as ET

# ============================================
# Configuration
# ============================================

# Land areas (used for weighted averages)
USA_LAND_AREA_SQ_MI = 3_797_000
USA_LAND_AREA_SQ_KM = USA_LAND_AREA_SQ_MI * 2.58999
CANADA_LAND_AREA_SQ_KM = 9_984_670

# Copernicus Data Space Ecosystem credentials
# Snow Cover Extent Northern Hemisphere 1km Daily
COPERNICUS_CLIENT_ID = 'sh-286c480c-b2e4-4f9b-8b56-e5f3ca8db856'
COPERNICUS_CLIENT_SECRET = 'sM3IIbrj79zlPe0li6BZX9P6V7tKmniY'
COPERNICUS_TOKEN_URL = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'
COPERNICUS_STATS_URL = 'https://sh.dataspace.copernicus.eu/api/v1/statistics'
COPERNICUS_SCE_COLLECTION = 'byoc-f80367ae-2de4-4acf-9e08-f49ecee95b99'  # SCE NH 1km daily

# Simplified bounding boxes for US and Canada (for Statistical API)
# These are approximate bounds - the API will clip to actual land
USA_BBOX = [-125.0, 24.5, -66.5, 49.5]  # [west, south, east, north] - CONUS
CANADA_BBOX = [-141.0, 41.7, -52.6, 83.1]  # Canada full extent

# Province codes for Environment Canada
PROVINCE_CODES = {
    'ON': 'ON',  # Ontario
    'QC': 'QC',  # Quebec
    'BC': 'BC',  # British Columbia
    'AB': 'AB',  # Alberta
    'MB': 'MB',  # Manitoba
    'SK': 'SK',  # Saskatchewan
    'NS': 'NS',  # Nova Scotia
    'NB': 'NB',  # New Brunswick
    'NL': 'NL',  # Newfoundland
    'PE': 'PE',  # PEI
}

# Metro areas to track with correct station IDs
# skiMarket=True for cities that are major ski destination feeder markets
# importance = metro population in thousands (used for market size weighting)
METRO_AREAS = [
    # USA Cities - using NWS API
    {'city': 'New York City', 'region': 'NY', 'country': 'usa', 'lat': 40.7128, 'lon': -74.0060, 'skiMarket': True, 'importance': 19980},
    {'city': 'Chicago', 'region': 'IL', 'country': 'usa', 'lat': 41.8781, 'lon': -87.6298, 'skiMarket': True, 'importance': 9460},
    {'city': 'Denver', 'region': 'CO', 'country': 'usa', 'lat': 39.7392, 'lon': -104.9903, 'skiMarket': True, 'importance': 2965},
    {'city': 'Minneapolis', 'region': 'MN', 'country': 'usa', 'lat': 44.9778, 'lon': -93.2650, 'skiMarket': True, 'importance': 3690},
    {'city': 'Boston', 'region': 'MA', 'country': 'usa', 'lat': 42.3601, 'lon': -71.0589, 'skiMarket': True, 'importance': 4900},
    {'city': 'Seattle', 'region': 'WA', 'country': 'usa', 'lat': 47.6062, 'lon': -122.3321, 'skiMarket': True, 'importance': 4020},
    {'city': 'Detroit', 'region': 'MI', 'country': 'usa', 'lat': 42.3314, 'lon': -83.0458, 'skiMarket': False, 'importance': 4340},
    {'city': 'Salt Lake City', 'region': 'UT', 'country': 'usa', 'lat': 40.7608, 'lon': -111.8910, 'skiMarket': True, 'importance': 1340},
    {'city': 'Buffalo', 'region': 'NY', 'country': 'usa', 'lat': 42.8864, 'lon': -78.8784, 'skiMarket': False, 'importance': 1150},
    {'city': 'Cleveland', 'region': 'OH', 'country': 'usa', 'lat': 41.4993, 'lon': -81.6944, 'skiMarket': False, 'importance': 2060},
    {'city': 'Milwaukee', 'region': 'WI', 'country': 'usa', 'lat': 43.0389, 'lon': -87.9065, 'skiMarket': False, 'importance': 1575},
    {'city': 'Portland', 'region': 'OR', 'country': 'usa', 'lat': 45.5152, 'lon': -122.6784, 'skiMarket': True, 'importance': 2510},
    # Additional US metros for feeder market coverage
    {'city': 'Los Angeles', 'region': 'CA', 'country': 'usa', 'lat': 34.0522, 'lon': -118.2437, 'skiMarket': True, 'importance': 12870},
    {'city': 'San Francisco', 'region': 'CA', 'country': 'usa', 'lat': 37.7749, 'lon': -122.4194, 'skiMarket': True, 'importance': 4565},
    {'city': 'Phoenix', 'region': 'AZ', 'country': 'usa', 'lat': 33.4484, 'lon': -112.0740, 'skiMarket': True, 'importance': 4950},
    {'city': 'Dallas', 'region': 'TX', 'country': 'usa', 'lat': 32.7767, 'lon': -96.7970, 'skiMarket': True, 'importance': 7900},
    {'city': 'Houston', 'region': 'TX', 'country': 'usa', 'lat': 29.7604, 'lon': -95.3698, 'skiMarket': True, 'importance': 7340},
    {'city': 'Atlanta', 'region': 'GA', 'country': 'usa', 'lat': 33.7490, 'lon': -84.3880, 'skiMarket': True, 'importance': 6200},
    {'city': 'Philadelphia', 'region': 'PA', 'country': 'usa', 'lat': 39.9526, 'lon': -75.1652, 'skiMarket': True, 'importance': 6250},
    {'city': 'Washington', 'region': 'DC', 'country': 'usa', 'lat': 38.9072, 'lon': -77.0369, 'skiMarket': True, 'importance': 6385},
    {'city': 'Las Vegas', 'region': 'NV', 'country': 'usa', 'lat': 36.1699, 'lon': -115.1398, 'skiMarket': True, 'importance': 2320},
    {'city': 'San Diego', 'region': 'CA', 'country': 'usa', 'lat': 32.7157, 'lon': -117.1611, 'skiMarket': True, 'importance': 3280},
    {'city': 'Austin', 'region': 'TX', 'country': 'usa', 'lat': 30.2672, 'lon': -97.7431, 'skiMarket': True, 'importance': 2475},
    {'city': 'Charlotte', 'region': 'NC', 'country': 'usa', 'lat': 35.2271, 'lon': -80.8431, 'skiMarket': True, 'importance': 2750},
    {'city': 'Raleigh', 'region': 'NC', 'country': 'usa', 'lat': 35.7796, 'lon': -78.6382, 'skiMarket': True, 'importance': 1500},
    {'city': 'Nashville', 'region': 'TN', 'country': 'usa', 'lat': 36.1627, 'lon': -86.7816, 'skiMarket': True, 'importance': 2050},
    {'city': 'Indianapolis', 'region': 'IN', 'country': 'usa', 'lat': 39.7684, 'lon': -86.1581, 'skiMarket': False, 'importance': 2140},
    {'city': 'St. Louis', 'region': 'MO', 'country': 'usa', 'lat': 38.6270, 'lon': -90.1994, 'skiMarket': False, 'importance': 2810},
    {'city': 'Kansas City', 'region': 'MO', 'country': 'usa', 'lat': 39.0997, 'lon': -94.5786, 'skiMarket': False, 'importance': 2220},
    {'city': 'Oklahoma City', 'region': 'OK', 'country': 'usa', 'lat': 35.4676, 'lon': -97.5164, 'skiMarket': False, 'importance': 1440},
    {'city': 'Albuquerque', 'region': 'NM', 'country': 'usa', 'lat': 35.0844, 'lon': -106.6504, 'skiMarket': True, 'importance': 920},
    {'city': 'Boise', 'region': 'ID', 'country': 'usa', 'lat': 43.6150, 'lon': -116.2023, 'skiMarket': True, 'importance': 810},
    {'city': 'Spokane', 'region': 'WA', 'country': 'usa', 'lat': 47.6588, 'lon': -117.4260, 'skiMarket': True, 'importance': 600},
    {'city': 'Sacramento', 'region': 'CA', 'country': 'usa', 'lat': 38.5816, 'lon': -121.4944, 'skiMarket': True, 'importance': 2420},
    {'city': 'Pittsburgh', 'region': 'PA', 'country': 'usa', 'lat': 40.4406, 'lon': -79.9959, 'skiMarket': True, 'importance': 2370},
    {'city': 'Hartford', 'region': 'CT', 'country': 'usa', 'lat': 41.7658, 'lon': -72.6734, 'skiMarket': True, 'importance': 1210},
    {'city': 'Albany', 'region': 'NY', 'country': 'usa', 'lat': 42.6526, 'lon': -73.7562, 'skiMarket': True, 'importance': 900},
    {'city': 'Providence', 'region': 'RI', 'country': 'usa', 'lat': 41.8240, 'lon': -71.4128, 'skiMarket': True, 'importance': 1680},
    {'city': 'Richmond', 'region': 'VA', 'country': 'usa', 'lat': 37.5407, 'lon': -77.4360, 'skiMarket': True, 'importance': 1340},
    {'city': 'Madison', 'region': 'WI', 'country': 'usa', 'lat': 43.0731, 'lon': -89.4012, 'skiMarket': False, 'importance': 690},
    # Canadian Cities - Environment Canada site codes (format: s0000XXX)
    # See: https://dd.weather.gc.ca/citypage_weather/docs/site_list_en.csv
    {'city': 'Toronto', 'region': 'ON', 'country': 'canada', 'province': 'ON', 'site': 's0000458', 'lat': 43.6532, 'lon': -79.3832, 'skiMarket': True, 'importance': 6710},
    {'city': 'Montreal', 'region': 'QC', 'country': 'canada', 'province': 'QC', 'site': 's0000635', 'lat': 45.5017, 'lon': -73.5673, 'skiMarket': True, 'importance': 4290},
    {'city': 'Vancouver', 'region': 'BC', 'country': 'canada', 'province': 'BC', 'site': 's0000141', 'lat': 49.2827, 'lon': -123.1207, 'skiMarket': True, 'importance': 2640},
    {'city': 'Calgary', 'region': 'AB', 'country': 'canada', 'province': 'AB', 'site': 's0000047', 'lat': 51.0447, 'lon': -114.0719, 'skiMarket': True, 'importance': 1580},
    {'city': 'Edmonton', 'region': 'AB', 'country': 'canada', 'province': 'AB', 'site': 's0000045', 'lat': 53.5461, 'lon': -113.4938, 'skiMarket': True, 'importance': 1520},
    {'city': 'Ottawa', 'region': 'ON', 'country': 'canada', 'province': 'ON', 'site': 's0000623', 'lat': 45.4215, 'lon': -75.6972, 'skiMarket': True, 'importance': 1490},
    {'city': 'Winnipeg', 'region': 'MB', 'country': 'canada', 'province': 'MB', 'site': 's0000193', 'lat': 49.8951, 'lon': -97.1384, 'skiMarket': True, 'importance': 850},
    {'city': 'Quebec City', 'region': 'QC', 'country': 'canada', 'province': 'QC', 'site': 's0000620', 'lat': 46.8139, 'lon': -71.2080, 'skiMarket': True, 'importance': 840},
    # Additional Canadian metros for feeder market coverage
    {'city': 'Victoria', 'region': 'BC', 'country': 'canada', 'province': 'BC', 'site': 's0000775', 'lat': 48.4284, 'lon': -123.3656, 'skiMarket': True, 'importance': 415},
    {'city': 'Kelowna', 'region': 'BC', 'country': 'canada', 'province': 'BC', 'site': 's0000568', 'lat': 49.8880, 'lon': -119.4960, 'skiMarket': True, 'importance': 225},
    {'city': 'Hamilton', 'region': 'ON', 'country': 'canada', 'province': 'ON', 'site': 's0000494', 'lat': 43.2557, 'lon': -79.8711, 'skiMarket': False, 'importance': 785},
    {'city': 'Halifax', 'region': 'NS', 'country': 'canada', 'province': 'NS', 'site': 's0000318', 'lat': 44.6488, 'lon': -63.5752, 'skiMarket': True, 'importance': 465},
    {'city': 'Saskatoon', 'region': 'SK', 'country': 'canada', 'province': 'SK', 'site': 's0000797', 'lat': 52.1332, 'lon': -106.6700, 'skiMarket': True, 'importance': 335},
    {'city': 'Regina', 'region': 'SK', 'country': 'canada', 'province': 'SK', 'site': 's0000788', 'lat': 50.4452, 'lon': -104.6189, 'skiMarket': True, 'importance': 265},
]

# Regional feeder market configurations (NSAA + Canadian Ski Council regions)
# Used for the regional dashboard view - maps region to its primary feeder markets
FEEDER_REGIONS = {
    'rocky-mountain': {
        'name': 'Rocky Mountain',
        'markets': ['Denver', 'Phoenix', 'Dallas', 'Houston', 'Austin', 'Albuquerque',
                    'Oklahoma City', 'Kansas City', 'Chicago', 'Los Angeles', 'Salt Lake City']
    },
    'pacific-northwest': {
        'name': 'Pacific Northwest',
        'markets': ['Seattle', 'Portland', 'Vancouver', 'Spokane', 'Boise',
                    'San Francisco', 'Sacramento']
    },
    'pacific-southwest': {
        'name': 'Pacific Southwest',
        'markets': ['Los Angeles', 'San Diego', 'Phoenix', 'Las Vegas',
                    'San Francisco', 'Sacramento']
    },
    'midwest': {
        'name': 'Midwest',
        'markets': ['Chicago', 'Minneapolis', 'Detroit', 'Milwaukee', 'Indianapolis',
                    'Cleveland', 'St. Louis', 'Madison']
    },
    'northeast': {
        'name': 'Northeast',
        'markets': ['New York City', 'Boston', 'Philadelphia', 'Washington', 'Hartford',
                    'Albany', 'Providence', 'Pittsburgh', 'Buffalo']
    },
    'southeast': {
        'name': 'Southeast',
        'markets': ['Atlanta', 'Charlotte', 'Raleigh', 'Nashville', 'Washington',
                    'Richmond']
    },
    'canada-bc': {
        'name': 'British Columbia',
        'markets': ['Vancouver', 'Victoria', 'Kelowna', 'Seattle', 'Portland', 'Calgary']
    },
    'canada-alberta': {
        'name': 'Alberta',
        'markets': ['Calgary', 'Edmonton', 'Vancouver', 'Saskatoon', 'Regina']
    },
    'canada-prairies': {
        'name': 'Prairies',
        'markets': ['Winnipeg', 'Saskatoon', 'Regina', 'Calgary', 'Edmonton', 'Minneapolis']
    },
    'canada-ontario': {
        'name': 'Ontario',
        'markets': ['Toronto', 'Ottawa', 'Hamilton', 'Buffalo', 'Detroit']
    },
    'canada-quebec': {
        'name': 'Quebec',
        'markets': ['Montreal', 'Quebec City', 'Ottawa', 'Toronto']
    },
    'canada-atlantic': {
        'name': 'Atlantic Canada',
        'markets': ['Halifax', 'Montreal']
    }
}

# ============================================
# Helper Functions
# ============================================

def print_safe(msg):
    """Print with safe encoding for Windows"""
    try:
        print(msg)
    except:
        print(msg.encode('ascii', 'replace').decode('ascii'))

def fetch_url(url, timeout=30, headers=None):
    """Fetch content from URL with SSL handling"""
    try:
        req_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NixVir Snow Dashboard/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        if headers:
            req_headers.update(headers)

        req = urllib.request.Request(url, headers=req_headers)

        # Create SSL context that doesn't verify (some gov sites have cert issues)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            return response.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        print_safe(f"  ! HTTP {e.code} fetching {url}")
        return None
    except Exception as e:
        print_safe(f"  ! Error fetching {url}: {e}")
        return None

def fetch_json(url, timeout=30):
    """Fetch and parse JSON from URL"""
    content = fetch_url(url, timeout)
    if content:
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print_safe(f"  ! JSON parse error: {e}")
    return None

def fetch_binary(url, timeout=60):
    """Fetch binary content from URL"""
    try:
        req_headers = {
            'User-Agent': 'Mozilla/5.0 NixVir Snow Dashboard/1.0'
        }
        req = urllib.request.Request(url, headers=req_headers)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            return response.read()
    except Exception as e:
        print_safe(f"  ! Error fetching binary {url}: {e}")
        return None

# ============================================
# NOAA NOHRSC Data (U.S. Snow Cover)
# ============================================

def fetch_nohrsc_snow_statistics():
    """
    Fetch snow cover statistics from NOAA NOHRSC National Snow Analysis
    Returns dict with U.S. snow cover data

    Primary source: https://www.nohrsc.noaa.gov/nsa/
    The main page shows: current snow coverage %, average depth, SWE
    """
    print_safe("Fetching NOHRSC National Snow Analysis...")

    result = {
        'cover_percent': None,
        'snow_area_sq_mi': None,
        'avg_depth_inches': None,
        'source': 'NOHRSC'
    }

    # Primary: Parse the main NSA page which shows national statistics
    nsa_url = "https://www.nohrsc.noaa.gov/nsa/"
    nsa_content = fetch_url(nsa_url)

    if nsa_content:
        # The page shows data in HTML table format like:
        # "Area Covered By Snow:</td><td align="right">25.1%</td>"
        # "Average Snow Depth:</td><td align="right">1.7 in</td>"

        # Pattern 1: Look for "Area Covered By Snow" in table cell, followed by value in next cell
        # Format: Area Covered By Snow:</td><td...>25.1%</td>
        area_covered_match = re.search(
            r'Area\s+Covered\s+By\s+Snow[:\s]*</td>\s*<td[^>]*>\s*(\d+(?:\.\d+)?)\s*%',
            nsa_content, re.IGNORECASE
        )
        if area_covered_match:
            result['cover_percent'] = float(area_covered_match.group(1))
            print_safe(f"  Found snow cover: {result['cover_percent']}%")
        else:
            # Fallback: Look for percentage after "Area Covered" with any tags between
            area_fallback = re.search(
                r'Area\s+Covered[^<]*<[^>]*>[^<]*(\d+(?:\.\d+)?)\s*%',
                nsa_content, re.IGNORECASE
            )
            if area_fallback:
                result['cover_percent'] = float(area_fallback.group(1))
                print_safe(f"  Found snow cover (alt): {result['cover_percent']}%")

        # Pattern 2: Look for average depth in table format
        # Format: Average Snow Depth:</td><td...>1.7 in</td>
        depth_match = re.search(
            r'(?:Average\s+)?Snow\s+Depth[:\s]*</td>\s*<td[^>]*>\s*(\d+(?:\.\d+)?)\s*in',
            nsa_content, re.IGNORECASE
        )
        if depth_match:
            result['avg_depth_inches'] = float(depth_match.group(1))
            print_safe(f"  Found avg depth: {result['avg_depth_inches']} inches")
        else:
            # Fallback: look for depth value after "Snow Depth" with tags between
            depth_fallback = re.search(
                r'Snow\s+Depth[^<]*<[^>]*>[^<]*(\d+(?:\.\d+)?)\s*in',
                nsa_content, re.IGNORECASE
            )
            if depth_fallback:
                depth = float(depth_fallback.group(1))
                if 0 < depth < 50:  # Reasonable average depth range
                    result['avg_depth_inches'] = depth
                    print_safe(f"  Found avg depth (alt): {depth} inches")

        # Pattern 3: Look for snow-covered area in sq mi
        area_match = re.search(r'([\d,]+(?:\.\d+)?)\s*(?:square\s*)?mi(?:les?)?', nsa_content, re.IGNORECASE)
        if area_match and area_match.group(1):
            try:
                area = float(area_match.group(1).replace(',', ''))
                if area > 10000:  # Should be a large number
                    result['snow_area_sq_mi'] = area
            except ValueError:
                pass  # Skip if conversion fails

    # Fallback: Try the text reports (may not exist anymore)
    if result['cover_percent'] is None:
        stats_url = "https://www.nohrsc.noaa.gov/nsa/reports_text/National/National_Snow_Report.txt"
        content = fetch_url(stats_url)

        if content:
            lines = content.split('\n')
            for line in lines:
                line_lower = line.lower()

                if 'snow cover' in line_lower and '%' in line:
                    match = re.search(r'(\d+(?:\.\d+)?)\s*%', line)
                    if match:
                        result['cover_percent'] = float(match.group(1))
                        print_safe(f"  Found snow cover from report: {result['cover_percent']}%")
                        break

    # Fallback: Try SNODAS page
    if result['cover_percent'] is None:
        snodas_url = "https://www.nohrsc.noaa.gov/snow_model/GE_snodas.html"
        snodas_content = fetch_url(snodas_url)
        if snodas_content:
            match = re.search(r'(\d+(?:\.\d+)?)\s*%', snodas_content)
            if match:
                result['cover_percent'] = float(match.group(1))
                print_safe(f"  Found snow cover from SNODAS: {result['cover_percent']}%")

    return result

def fetch_nohrsc_historical(year, month, day):
    """
    Fetch historical NOHRSC snow cover and depth for a specific date.
    Uses the NSA archive URL format: /nsa/index.html?year=YYYY&month=MM&day=DD

    Returns dict with 'cover' and 'depth_inches', or None if not available.
    """
    url = f"https://www.nohrsc.noaa.gov/nsa/index.html?year={year}&month={month}&day={day}"
    content = fetch_url(url, timeout=15)

    result = {'cover': None, 'depth_inches': None}

    if content:
        # Look for "Area Covered By Snow" pattern
        match = re.search(
            r'Area\s+Covered\s+By\s+Snow[:\s]*</td>\s*<td[^>]*>\s*(\d+(?:\.\d+)?)\s*%',
            content, re.IGNORECASE
        )
        if match:
            result['cover'] = float(match.group(1))
        else:
            # Fallback pattern
            match = re.search(
                r'Area\s+Covered[^<]*<[^>]*>[^<]*(\d+(?:\.\d+)?)\s*%',
                content, re.IGNORECASE
            )
            if match:
                result['cover'] = float(match.group(1))

        # Look for average depth - format varies:
        # Current page: "Average Snow Depth:</td><td...>X.X in</td>"
        # Historical: "Snow Depth</th>...<tr><td>Average:</td><td>X.X in</td>"
        depth_match = re.search(
            r'(?:Average\s+)?Snow\s+Depth[:\s]*</td>\s*<td[^>]*>\s*(\d+(?:\.\d+)?)\s*in',
            content, re.IGNORECASE
        )
        if depth_match:
            result['depth_inches'] = float(depth_match.group(1))
        else:
            # Look for "Snow Depth" header followed by "Average:" row
            depth_section = re.search(
                r'Snow\s+Depth.*?Average[:\s]*</td>\s*<td[^>]*>\s*(\d+(?:\.\d+)?)\s*in',
                content, re.IGNORECASE | re.DOTALL
            )
            if depth_section:
                depth = float(depth_section.group(1))
                if 0 < depth < 50:  # Reasonable average depth range
                    result['depth_inches'] = depth
            else:
                # Fallback depth pattern
                depth_fallback = re.search(
                    r'Snow\s+Depth[^<]*<[^>]*>[^<]*(\d+(?:\.\d+)?)\s*in',
                    content, re.IGNORECASE
                )
                if depth_fallback:
                    depth = float(depth_fallback.group(1))
                    if 0 < depth < 50:  # Reasonable average depth range
                        result['depth_inches'] = depth

    if result['cover'] is not None:
        return result
    return None


def fetch_prior_year_history(current_history):
    """
    Fetch prior year snow cover and depth data for the same dates as current history.

    Args:
        current_history: List of {'date': 'YYYY-MM-DD', 'value': float}

    Returns:
        Tuple of (prior_cover_history, prior_depth_avg_inches)
        - prior_cover_history: List of {'date': 'YYYY-MM-DD', 'value': float} for prior year
        - prior_depth_avg_inches: Average depth from prior year period (float or None)
    """
    print_safe("Fetching prior year NOHRSC data...")
    prior_history = []
    depth_values = []

    for entry in current_history:
        try:
            # Parse current date and get same date last year
            current_date = datetime.strptime(entry['date'], '%Y-%m-%d')
            prior_date = current_date.replace(year=current_date.year - 1)

            data = fetch_nohrsc_historical(
                prior_date.year, prior_date.month, prior_date.day
            )

            if data is not None:
                prior_history.append({
                    'date': prior_date.strftime('%Y-%m-%d'),
                    'value': data['cover']
                })
                if data['depth_inches'] is not None:
                    depth_values.append(data['depth_inches'])
                print_safe(f"  {prior_date.strftime('%Y-%m-%d')}: {data['cover']}%, depth: {data['depth_inches']}")
            else:
                # Use None to indicate missing data
                prior_history.append({
                    'date': prior_date.strftime('%Y-%m-%d'),
                    'value': None
                })
        except Exception as e:
            print_safe(f"  ! Error fetching {entry['date']} prior year: {e}")
            prior_history.append({
                'date': entry['date'],
                'value': None
            })

    # Calculate average depth from prior year
    prior_depth_avg = None
    if depth_values:
        prior_depth_avg = round(sum(depth_values) / len(depth_values), 1)
        print_safe(f"  Prior year avg depth: {prior_depth_avg} inches (from {len(depth_values)} data points)")

    return prior_history, prior_depth_avg


def fetch_nohrsc_regional_stats():
    """
    Fetch regional snow statistics from NOHRSC
    Returns dict with regional breakdowns by RFC (River Forecast Center)
    """
    print_safe("Fetching NOHRSC regional statistics...")

    regions = {}

    # NOHRSC provides regional data by River Forecast Center
    # Each RFC covers a different region of the U.S.
    rfc_codes = [
        'ABRFC',  # Arkansas-Red Basin
        'CBRFC',  # Colorado Basin
        'CNRFC',  # California-Nevada
        'LMRFC',  # Lower Mississippi
        'MARFC',  # Middle Atlantic
        'MBRFC',  # Missouri Basin
        'NCRFC',  # North Central
        'NERFC',  # Northeast
        'NWRFC',  # Northwest
        'OHRFC',  # Ohio
        'SERFC',  # Southeast
        'WGRFC',  # West Gulf
    ]

    for rfc in rfc_codes:
        url = f"https://www.nohrsc.noaa.gov/nsa/reports_text/{rfc}/{rfc}_Snow_Report.txt"
        content = fetch_url(url, timeout=15)
        if content:
            # Parse for snow cover percentage
            match = re.search(r'(\d+(?:\.\d+)?)\s*%', content)
            if match:
                regions[rfc] = float(match.group(1))

    if regions:
        print_safe(f"  Found data for {len(regions)} regions")

    return regions

# ============================================
# Rutgers Global Snow Lab
# ============================================

def fetch_rutgers_snow_extent():
    """
    Fetch snow extent data from Rutgers Global Snow Lab
    Returns dict with weekly snow cover extent for North America

    Data file format (wkcov.nam.txt): year week extent_sq_km
    Example: 2025 49 18093940
    """
    print_safe("Fetching Rutgers Global Snow Lab data...")

    result = {
        'north_america_extent_km2': None,
        'north_america_anomaly': None,
        'week': None,
        'year': None,
        'source': 'Rutgers'
    }

    # Primary: Weekly North America snow cover extent (confirmed working URL)
    # Format: year week extent_sq_km
    url = "https://climate.rutgers.edu/snowcover/files/wkcov.nam.txt"
    content = fetch_url(url)

    if content:
        lines = content.strip().split('\n')
        # Data format: year week extent_sq_km
        # Get the most recent entry (last non-empty line)
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 3:
                try:
                    year = int(parts[0])
                    week = int(parts[1])
                    extent_km2 = float(parts[2])  # Already in sq km

                    # Sanity check
                    if 1900 < year < 2100 and 1 <= week <= 53 and extent_km2 > 0:
                        result['year'] = year
                        result['week'] = week
                        result['north_america_extent_km2'] = extent_km2
                        print_safe(f"  Found Rutgers data: Year {year}, Week {week}, Extent {extent_km2:,.0f} km²")
                        break
                except ValueError:
                    continue

    # Fallback: Try Northern Hemisphere monthly data
    if result['north_america_extent_km2'] is None:
        nh_url = "https://climate.rutgers.edu/snowcover/files/moncov.nhsce.txt"
        nh_content = fetch_url(nh_url)

        if nh_content:
            lines = nh_content.strip().split('\n')
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        year = int(parts[0])
                        month = int(parts[1])
                        extent = float(parts[2])

                        if 1900 < year < 2100 and 1 <= month <= 12:
                            result['year'] = year
                            result['month'] = month
                            # NH extent in millions of km², NA is roughly 40% of NH
                            result['north_america_extent_km2'] = extent * 1_000_000 * 0.4
                            print_safe(f"  Found NH monthly data: Year {year}, Month {month}")
                            break
                    except ValueError:
                        continue

    return result

# ============================================
# NASA MODIS Snow Cover
# ============================================

def fetch_modis_snow_stats():
    """
    Fetch MODIS snow cover statistics
    MODIS provides daily global snow cover at 500m resolution

    Note: Direct MODIS data access requires NASA Earthdata login
    We'll use NSIDC's processed statistics when available
    """
    print_safe("Checking MODIS/NSIDC snow cover data...")

    result = {
        'global_snow_extent_km2': None,
        'northern_hemisphere_km2': None,
        'source': 'MODIS/NSIDC'
    }

    # NSIDC provides some processed MODIS statistics
    # The direct data requires authentication, but we can try public summaries

    # Try NSIDC Near-Real-Time snow extent
    nrt_url = "https://nsidc.org/data/nrt/"
    content = fetch_url(nrt_url)

    if content:
        # Parse for any snow extent statistics
        match = re.search(r'snow\s*(?:cover|extent)[^:]*:\s*([\d.]+)\s*(?:million)?\s*(?:km|square)',
                         content, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            # Assume millions if value seems small
            if value < 1000:
                value = value * 1_000_000
            result['northern_hemisphere_km2'] = value
            print_safe(f"  Found MODIS extent: {value:,.0f} km²")

    return result

# ============================================
# Copernicus CLMS Snow Cover Extent
# ============================================

# Cache for OAuth token
_copernicus_token_cache = {
    'token': None,
    'expires': None
}

def get_copernicus_token():
    """
    Get OAuth2 access token from Copernicus Data Space Ecosystem.
    Uses client credentials flow. Token is cached until near expiry.
    """
    global _copernicus_token_cache

    # Check if we have a valid cached token
    if (_copernicus_token_cache['token'] and
        _copernicus_token_cache['expires'] and
        datetime.now() < _copernicus_token_cache['expires']):
        return _copernicus_token_cache['token']

    print_safe("  Fetching Copernicus OAuth token...")

    try:
        # Prepare token request
        data = urllib.parse.urlencode({
            'grant_type': 'client_credentials',
            'client_id': COPERNICUS_CLIENT_ID,
            'client_secret': COPERNICUS_CLIENT_SECRET
        }).encode('utf-8')

        req = urllib.request.Request(
            COPERNICUS_TOKEN_URL,
            data=data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        )

        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
            token_data = json.loads(response.read().decode('utf-8'))

        access_token = token_data.get('access_token')
        expires_in = token_data.get('expires_in', 300)  # Default 5 min

        # Cache the token (expire 60 seconds early to be safe)
        _copernicus_token_cache['token'] = access_token
        _copernicus_token_cache['expires'] = datetime.now() + timedelta(seconds=expires_in - 60)

        print_safe("  Got Copernicus token (valid for ~5 min)")
        return access_token

    except Exception as e:
        print_safe(f"  ! Failed to get Copernicus token: {e}")
        return None


def fetch_copernicus_snow_cover(bbox, region_name):
    """
    Fetch snow cover statistics from Copernicus CLMS Snow Cover Extent
    using the Sentinel Hub Statistical API.

    Args:
        bbox: [west, south, east, north] in WGS84
        region_name: Name for logging (e.g., "USA", "Canada")

    Returns:
        dict with 'cover_percent' (mean snow cover fraction) and 'source'
    """
    result = {
        'cover_percent': None,
        'source': 'Copernicus SCE'
    }

    token = get_copernicus_token()
    if not token:
        return result

    # Get yesterday's date (today's data may not be available yet)
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%Y-%m-%d')

    # Evalscript to calculate mean snow cover fraction
    # SCE band contains snow cover percentage (0-100)
    evalscript = """
//VERSION=3
function setup() {
  return {
    input: [{
      bands: ["SCE"],
      units: "DN"
    }],
    output: [
      { id: "snow_cover", bands: 1, sampleType: "FLOAT32" },
      { id: "dataMask", bands: 1 }
    ]
  };
}

function evaluatePixel(sample) {
  // SCE values: 0-100 = snow cover %, 205 = cloud, 255 = no data
  let isValid = sample.SCE <= 100;
  return {
    snow_cover: [isValid ? sample.SCE : 0],
    dataMask: [isValid ? 1 : 0]
  };
}
"""

    # Build the Statistical API request
    request_body = {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": {
                    "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
                }
            },
            "data": [{
                "type": COPERNICUS_SCE_COLLECTION,
                "dataFilter": {
                    "timeRange": {
                        "from": f"{date_str}T00:00:00Z",
                        "to": f"{date_str}T23:59:59Z"
                    }
                }
            }]
        },
        "aggregation": {
            "timeRange": {
                "from": f"{date_str}T00:00:00Z",
                "to": f"{date_str}T23:59:59Z"
            },
            "aggregationInterval": {
                "of": "P1D"
            },
            "evalscript": evalscript,
            "resx": 0.01,  # ~1km resolution
            "resy": 0.01
        }
    }

    try:
        req_data = json.dumps(request_body).encode('utf-8')
        req = urllib.request.Request(
            COPERNICUS_STATS_URL,
            data=req_data,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )

        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=60, context=ctx) as response:
            stats_data = json.loads(response.read().decode('utf-8'))

        # Parse the response
        if 'data' in stats_data and len(stats_data['data']) > 0:
            interval_data = stats_data['data'][0]
            if 'outputs' in interval_data and 'snow_cover' in interval_data['outputs']:
                snow_stats = interval_data['outputs']['snow_cover']['bands']['B0']['stats']
                mean_snow = snow_stats.get('mean')
                if mean_snow is not None:
                    result['cover_percent'] = round(mean_snow, 1)
                    result['valid_pixels'] = snow_stats.get('sampleCount', 0)
                    print_safe(f"  {region_name}: {result['cover_percent']}% snow cover (Copernicus SCE)")

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='replace')
        print_safe(f"  ! Copernicus API error for {region_name}: HTTP {e.code}")
        if 'No data found' in error_body or 'NO_DATA' in error_body:
            print_safe(f"    No data available for {date_str}")
        else:
            print_safe(f"    {error_body[:200]}")
    except Exception as e:
        print_safe(f"  ! Copernicus error for {region_name}: {e}")

    return result


def fetch_copernicus_snow_data():
    """
    Fetch snow cover data for USA and Canada from Copernicus.
    Returns dict with usa_cover, canada_cover percentages.
    """
    print_safe("Fetching Copernicus CLMS Snow Cover Extent...")

    result = {
        'usa_cover': None,
        'canada_cover': None,
        'source': 'Copernicus SCE'
    }

    # Fetch USA snow cover
    usa_data = fetch_copernicus_snow_cover(USA_BBOX, "USA (CONUS)")
    if usa_data.get('cover_percent') is not None:
        result['usa_cover'] = usa_data['cover_percent']

    # Fetch Canada snow cover
    canada_data = fetch_copernicus_snow_cover(CANADA_BBOX, "Canada")
    if canada_data.get('cover_percent') is not None:
        result['canada_cover'] = canada_data['cover_percent']

    return result

# ============================================
# Environment Canada (Canadian Weather)
# ============================================

def fetch_envcan_conditions(province, site_code):
    """
    Fetch current conditions from Environment Canada

    New URL format (2025+): https://dd.weather.gc.ca/today/citypage_weather/{PROVINCE}/{HH}/
    Files are timestamped: {TIMESTAMP}_MSC_CitypageWeather_{site_code}_en.xml

    We need to:
    1. List the hourly directory to find the latest hour
    2. Find the XML file for our site code
    3. Fetch and parse that file
    """
    result = {
        'snow_on_ground_cm': None,
        'temperature_c': None,
        'condition': None
    }

    # Try to get the most recent hour's directory listing
    from datetime import timezone
    current_hour = datetime.now(timezone.utc).hour

    # Try current hour and previous few hours (in case current hour not yet populated)
    for hour_offset in range(4):
        hour = (current_hour - hour_offset) % 24
        hour_str = f"{hour:02d}"
        dir_url = f"https://dd.weather.gc.ca/today/citypage_weather/{province}/{hour_str}/"

        dir_content = fetch_url(dir_url, timeout=15)
        if not dir_content:
            continue

        # Find the latest file for our site code (English version)
        # Pattern: *_MSC_CitypageWeather_{site_code}_en.xml
        pattern = rf'href="([^"]*_MSC_CitypageWeather_{site_code}_en\.xml)"'
        matches = re.findall(pattern, dir_content)

        if matches:
            # Get the last (most recent) match
            latest_file = matches[-1]
            xml_url = f"{dir_url}{latest_file}"

            xml_content = fetch_url(xml_url, timeout=15)
            if xml_content:
                try:
                    root = ET.fromstring(xml_content)

                    # Find currentConditions element
                    current = root.find('.//currentConditions')
                    if current is not None:
                        # Temperature
                        temp_elem = current.find('temperature')
                        if temp_elem is not None and temp_elem.text:
                            try:
                                result['temperature_c'] = float(temp_elem.text)
                            except ValueError:
                                pass

                        # Condition (e.g., "Light Snow", "Cloudy")
                        cond_elem = current.find('condition')
                        if cond_elem is not None and cond_elem.text:
                            result['condition'] = cond_elem.text

                    # Find snowOnGround in almanac or currentConditions
                    snow_elem = root.find('.//snowOnGround')
                    if snow_elem is not None and snow_elem.text:
                        try:
                            result['snow_on_ground_cm'] = float(snow_elem.text)
                        except ValueError:
                            pass

                    # Also check for snow in forecast/conditions
                    if result['snow_on_ground_cm'] is None:
                        # Look for any snow depth mentions
                        for elem in root.iter():
                            if elem.tag and 'snow' in elem.tag.lower() and elem.text:
                                try:
                                    val = float(elem.text)
                                    if 0 < val < 500:  # Reasonable snow depth
                                        result['snow_on_ground_cm'] = val
                                        break
                                except ValueError:
                                    continue

                    # If we got temperature, we succeeded
                    if result['temperature_c'] is not None:
                        return result

                except ET.ParseError as e:
                    print_safe(f"    ! XML parse error: {e}")
                    continue

    return result

# ============================================
# NWS Weather API (U.S. Metro Areas)
# ============================================

def fetch_nws_snow_data(lat, lon):
    """
    Fetch current conditions from NWS API for a location
    Returns snow depth if available
    """
    try:
        # First, get the gridpoint for this location
        points_url = f"https://api.weather.gov/points/{lat},{lon}"
        points_data = fetch_json(points_url)

        if not points_data or 'properties' not in points_data:
            return None

        props = points_data['properties']

        # Get current observations from nearest station
        stations_url = props.get('observationStations')
        if stations_url:
            stations_data = fetch_json(stations_url)
            if stations_data and 'features' in stations_data and len(stations_data['features']) > 0:
                # Try first few stations until we get data
                for station_feature in stations_data['features'][:3]:
                    station_id = station_feature['properties']['stationIdentifier']
                    obs_url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
                    obs_data = fetch_json(obs_url)

                    if obs_data and 'properties' in obs_data:
                        obs_props = obs_data['properties']

                        result = {
                            'snow_depth_m': None,
                            'temperature_c': None,
                            'condition': None,
                            'station': station_id
                        }

                        # Extract snow depth if available
                        if 'snowDepth' in obs_props and obs_props['snowDepth']:
                            depth_val = obs_props['snowDepth'].get('value')
                            if depth_val is not None:
                                result['snow_depth_m'] = depth_val

                        # Get temperature
                        if 'temperature' in obs_props and obs_props['temperature']:
                            temp_val = obs_props['temperature'].get('value')
                            if temp_val is not None:
                                result['temperature_c'] = temp_val

                        # Get text description
                        if 'textDescription' in obs_props:
                            result['condition'] = obs_props['textDescription']

                        # If we got useful data, return it
                        if result['snow_depth_m'] is not None or result['temperature_c'] is not None:
                            return result

    except Exception as e:
        print_safe(f"    ! NWS API error: {e}")

    return None

# ============================================
# Open-Meteo Temperature Data
# ============================================

def fetch_openmeteo_temperature(lat, lon, city_name=None):
    """
    Fetch current temperature and historical normal from Open-Meteo API.

    Returns dict with:
    - temp_c: Current temperature in Celsius
    - temp_f: Current temperature in Fahrenheit
    - normal_c: 30-day historical average for this time of year
    - anomaly_c: Departure from normal (temp_c - normal_c)
    - anomaly_f: Departure from normal in Fahrenheit
    """
    result = {
        'temp_c': None,
        'temp_f': None,
        'normal_c': None,
        'anomaly_c': None,
        'anomaly_f': None
    }

    try:
        # Get current temperature
        current_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m&temperature_unit=celsius&timezone=auto"
        current_data = fetch_json(current_url, timeout=15)

        if current_data and 'current' in current_data:
            temp_c = current_data['current'].get('temperature_2m')
            if temp_c is not None:
                result['temp_c'] = round(temp_c, 1)
                result['temp_f'] = round(temp_c * 9/5 + 32, 1)

        # Get historical data for the same period last year to calculate "normal"
        # Fetch 30 days of data from last year for this time period
        today = datetime.now()
        # Calculate dates relative to today, then shift back one year
        start_date = today - timedelta(days=15)
        end_date = today + timedelta(days=14)  # Use 14 to avoid future dates in edge cases
        # Shift to last year
        start_date = start_date.replace(year=start_date.year - 1)
        end_date = end_date.replace(year=end_date.year - 1)

        # Format dates - ensure start is before end
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        # Use Open-Meteo Historical API for climate normals
        historical_url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_str}&end_date={end_str}&daily=temperature_2m_mean&timezone=auto"
        historical_data = fetch_json(historical_url, timeout=15)

        if historical_data and 'daily' in historical_data:
            temps = historical_data['daily'].get('temperature_2m_mean', [])
            valid_temps = [t for t in temps if t is not None]
            if valid_temps:
                normal_c = sum(valid_temps) / len(valid_temps)
                result['normal_c'] = round(normal_c, 1)

                # Calculate anomaly if we have current temp
                if result['temp_c'] is not None:
                    anomaly_c = result['temp_c'] - result['normal_c']
                    result['anomaly_c'] = round(anomaly_c, 1)
                    result['anomaly_f'] = round(anomaly_c * 9/5, 1)

    except Exception as e:
        if city_name:
            print_safe(f"    ! Open-Meteo error for {city_name}: {e}")
        else:
            print_safe(f"    ! Open-Meteo error: {e}")

    return result


def fetch_country_temperature_anomaly(metros, country):
    """
    Calculate weighted average temperature anomaly for a country
    based on its metro areas.

    Returns dict with avg_temp_c, avg_temp_f, avg_anomaly_c, avg_anomaly_f
    """
    country_metros = [m for m in metros if m.get('country') == country]

    if not country_metros:
        return None

    temps = []
    anomalies = []

    for metro in country_metros:
        temp_data = metro.get('temperature', {})
        if temp_data.get('temp_c') is not None:
            temps.append(temp_data['temp_c'])
        if temp_data.get('anomaly_c') is not None:
            anomalies.append(temp_data['anomaly_c'])

    result = {
        'avg_temp_c': None,
        'avg_temp_f': None,
        'avg_anomaly_c': None,
        'avg_anomaly_f': None
    }

    if temps:
        avg_temp_c = sum(temps) / len(temps)
        result['avg_temp_c'] = round(avg_temp_c, 1)
        result['avg_temp_f'] = round(avg_temp_c * 9/5 + 32, 1)

    if anomalies:
        avg_anomaly_c = sum(anomalies) / len(anomalies)
        result['avg_anomaly_c'] = round(avg_anomaly_c, 1)
        result['avg_anomaly_f'] = round(avg_anomaly_c * 9/5, 1)

    return result


def calculate_ski_market_aggregates(metros, country):
    """
    Calculate aggregate snow cover and temperature anomaly for ski market metros.

    Args:
        metros: List of metro area dicts with snow cover and temperature data
        country: 'usa' or 'canada'

    Returns dict with:
        - cover: Average snow cover % for ski markets
        - avg_temp_c/f: Average temperature
        - avg_anomaly_c/f: Average temperature anomaly
        - metro_count: Number of ski market metros included
    """
    ski_metros = [m for m in metros if m.get('country') == country and m.get('skiMarket') == True]

    if not ski_metros:
        return None

    covers = []
    temps = []
    anomalies = []

    for metro in ski_metros:
        if metro.get('cover') is not None:
            covers.append(metro['cover'])
        temp_data = metro.get('temperature', {})
        if temp_data.get('temp_c') is not None:
            temps.append(temp_data['temp_c'])
        if temp_data.get('anomaly_c') is not None:
            anomalies.append(temp_data['anomaly_c'])

    result = {
        'cover': None,
        'avg_temp_c': None,
        'avg_temp_f': None,
        'avg_anomaly_c': None,
        'avg_anomaly_f': None,
        'metro_count': len(ski_metros)
    }

    if covers:
        result['cover'] = round(sum(covers) / len(covers), 1)

    if temps:
        avg_temp_c = sum(temps) / len(temps)
        result['avg_temp_c'] = round(avg_temp_c, 1)
        result['avg_temp_f'] = round(avg_temp_c * 9/5 + 32, 1)

    if anomalies:
        avg_anomaly_c = sum(anomalies) / len(anomalies)
        result['avg_anomaly_c'] = round(avg_anomaly_c, 1)
        result['avg_anomaly_f'] = round(avg_anomaly_c * 9/5, 1)

    return result


# ============================================
# Estimation Functions
# ============================================

def estimate_snow_cover_from_depth(depth_inches, temp_c, lat, condition=None):
    """
    Estimate snow cover percentage based on available data
    """
    # If we have snow depth data
    if depth_inches is not None:
        if depth_inches <= 0:
            return 0
        elif depth_inches < 0.5:
            return 15  # Trace amounts
        elif depth_inches < 2:
            return 40
        elif depth_inches < 4:
            return 60
        elif depth_inches < 8:
            return 80
        elif depth_inches < 12:
            return 90
        else:
            return 95  # Deep snow = near complete coverage

    # Check condition text for snow mentions
    if condition:
        cond_lower = condition.lower()
        if 'snow' in cond_lower:
            if 'heavy' in cond_lower:
                return 85
            elif 'light' in cond_lower or 'flurr' in cond_lower:
                return 50
            else:
                return 65

    # Estimate based on temp and latitude only
    if temp_c is not None:
        if temp_c > 5:  # Above 41°F - likely no snow
            return 5 if lat > 50 else 0
        elif temp_c > 0:  # Near freezing
            if lat > 50:
                return 60
            elif lat > 45:
                return 40
            elif lat > 40:
                return 25
            else:
                return 10
        else:  # Below freezing
            if lat > 50:
                return 85
            elif lat > 45:
                return 65
            elif lat > 40:
                return 45
            else:
                return 25

    # Pure latitude-based estimate
    if lat > 55:
        return 90
    elif lat > 50:
        return 70
    elif lat > 45:
        return 50
    elif lat > 40:
        return 30
    else:
        return 15

def estimate_regional_snow_cover(month, day):
    """
    Estimate snow cover percentages based on historical patterns
    Returns dict with usa and canada estimates
    """
    # Historical average snow cover by month (approximate, based on NOHRSC/Rutgers data)
    historical_usa = {
        1: 38, 2: 35, 3: 25, 4: 10, 5: 3, 6: 1,
        7: 0, 8: 0, 9: 1, 10: 3, 11: 12, 12: 30
    }
    historical_canada = {
        1: 80, 2: 82, 3: 75, 4: 55, 5: 30, 6: 8,
        7: 3, 8: 3, 9: 8, 10: 25, 11: 50, 12: 70
    }

    # Interpolate based on day of month
    base_usa = historical_usa[month]
    base_canada = historical_canada[month]

    # Calculate next month values for interpolation
    next_month = month % 12 + 1
    next_usa = historical_usa[next_month]
    next_canada = historical_canada[next_month]

    day_fraction = day / 30
    usa_cover = base_usa + (next_usa - base_usa) * day_fraction
    canada_cover = base_canada + (next_canada - base_canada) * day_fraction

    return {
        'usa': round(usa_cover, 1),
        'canada': round(canada_cover, 1)
    }

def calculate_trend(current, previous):
    """Calculate trend string from current and previous values"""
    if previous is None:
        return 'stable', '—'

    diff = current - previous
    if abs(diff) < 1:
        return 'stable', '—'
    elif diff > 0:
        return 'up', f'+{diff:.1f}%'
    else:
        return 'down', f'{diff:.1f}%'

# ============================================
# Data Generation
# ============================================

def load_season_data():
    """
    Load accumulated season data from snow-cover-season.json.
    This file contains real historical data from Oct 1 onwards.
    """
    season_file = 'static/data/snow-cover-season.json'
    if os.path.exists(season_file):
        try:
            with open(season_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print_safe(f"Warning: Could not load season data: {e}")
    return None


def save_season_data(season_data):
    """Save updated season data back to file."""
    season_file = 'static/data/snow-cover-season.json'
    os.makedirs(os.path.dirname(season_file), exist_ok=True)
    with open(season_file, 'w', encoding='utf-8') as f:
        json.dump(season_data, f, indent=2)


def append_todays_data(season_data, usa_cover, canada_cover, usa_depth=None):
    """
    Append today's data to the season history if not already present.
    Returns the updated season data.
    """
    today_str = datetime.now().strftime('%Y-%m-%d')

    # Check if today's data already exists
    usa_dates = [entry['date'] for entry in season_data.get('usa', [])]

    if today_str not in usa_dates:
        # Add today's USA data
        season_data['usa'].append({
            'date': today_str,
            'value': round(usa_cover, 1),
            'depth_inches': usa_depth
        })

        # Add today's Canada data
        canada_value = min(100, round(canada_cover, 1))
        season_data['canada'].append({
            'date': today_str,
            'value': canada_value
        })

        # Update generation timestamp
        season_data['generated'] = datetime.now().strftime('%Y-%m-%d %H:%M') + ' UTC'

        print_safe(f"  Added data for {today_str}: USA={usa_cover:.1f}%, Canada={canada_cover:.1f}%")
    else:
        print_safe(f"  Data for {today_str} already exists, skipping append")

    return season_data


# ============================================
# Main Data Collection
# ============================================

def collect_snow_data():
    """
    Collect snow cover data from all sources
    Returns complete data structure for dashboard
    """
    print_safe("=" * 60)
    print_safe("Snow Cover Data Collection")
    print_safe(f"Timestamp: {datetime.now().isoformat()}")
    print_safe("=" * 60)

    today = datetime.now()

    # ========== Fetch Real Data ==========

    # 1. NOHRSC U.S. Snow Statistics
    nohrsc_data = fetch_nohrsc_snow_statistics()
    # Regional stats URLs are returning 404, so skip for now
    nohrsc_regions = {}  # fetch_nohrsc_regional_stats()

    # 2. Rutgers Global Snow Lab - Primary source for North America extent
    rutgers_data = fetch_rutgers_snow_extent()

    # 3. Copernicus CLMS Snow Cover Extent - Satellite-derived data
    copernicus_data = fetch_copernicus_snow_data()

    # ========== Determine U.S. Snow Cover ==========

    # Get historical estimates as baseline
    estimates = estimate_regional_snow_cover(today.month, today.day)

    # Priority: 1) NOHRSC (most reliable for US), 2) Copernicus, 3) Historical estimate
    if nohrsc_data.get('cover_percent') is not None:
        usa_cover = nohrsc_data['cover_percent']
        usa_source = 'NOHRSC'
    elif copernicus_data.get('usa_cover') is not None:
        usa_cover = copernicus_data['usa_cover']
        usa_source = 'Copernicus SCE'
    elif nohrsc_regions:
        # Average regional data
        usa_cover = sum(nohrsc_regions.values()) / len(nohrsc_regions)
        usa_source = 'NOHRSC Regional'
    else:
        usa_cover = estimates['usa']
        usa_source = 'Historical Estimate'

    print_safe(f"\nU.S. Snow Cover: {usa_cover:.1f}% (Source: {usa_source})")

    # ========== Determine Canada Snow Cover ==========

    # Priority: 1) Copernicus (direct satellite measurement), 2) Derived from Rutgers, 3) Historical
    if copernicus_data.get('canada_cover') is not None:
        # Use Copernicus satellite data - this is actual measured snow cover!
        canada_cover = copernicus_data['canada_cover']
        canada_source = 'Copernicus SCE'
    elif rutgers_data.get('north_america_extent_km2'):
        na_extent = rutgers_data['north_america_extent_km2']

        # Calculate NA-wide snow cover percentage
        # Include Alaska and Northern territories in total area calculation
        # Rutgers NA extent includes: Canada, USA (with Alaska), Greenland, and parts of Mexico
        # Approximate total land area covered by Rutgers NA:
        RUTGERS_NA_LAND_AREA_KM2 = (
            CANADA_LAND_AREA_SQ_KM +          # ~10M km²
            USA_LAND_AREA_SQ_KM +              # ~9.8M km²
            2_166_086                          # Greenland ~2.2M km²
        )  # Total ~22M km²

        na_cover_percent = (na_extent / RUTGERS_NA_LAND_AREA_KM2) * 100

        # Since Canada is further north than US, estimate Canada's snow cover
        # as proportionally higher. Historical data suggests Canada typically
        # has 2-3x the snow coverage percentage of the US in winter
        # Use the ratio between estimated values as a guide
        usa_historical = estimates['usa']
        canada_historical = estimates['canada']

        if usa_historical > 0:
            ratio = canada_historical / usa_historical
            # Apply the historical ratio to actual NOHRSC USA data
            canada_cover = min(100, usa_cover * ratio)
        else:
            canada_cover = estimates['canada']

        canada_source = 'Derived (NOHRSC ratio)'
        print_safe(f"  NA extent: {na_extent:,.0f} km², NA cover: {na_cover_percent:.1f}%")
    else:
        canada_cover = estimates['canada']
        canada_source = 'Historical Estimate'

    print_safe(f"Canada Snow Cover: {canada_cover:.1f}% (Source: {canada_source})")

    # ========== Calculate Combined ==========

    total_area = USA_LAND_AREA_SQ_KM + CANADA_LAND_AREA_SQ_KM
    combined_cover = (
        (usa_cover * USA_LAND_AREA_SQ_KM) +
        (canada_cover * CANADA_LAND_AREA_SQ_KM)
    ) / total_area

    print_safe(f"Combined Cover: {combined_cover:.1f}%")

    # ========== Load and Update Season Data ==========
    # Use REAL accumulated data from the season file, NOT synthetic data

    print_safe("\n" + "=" * 40)
    print_safe("Loading season data...")

    season_data = load_season_data()
    if season_data is None:
        print_safe("ERROR: No season data file found!")
        print_safe("Run backfill_current_season.py first to create the data file.")
        # Create minimal structure to avoid crashes
        season_data = {
            'usa': [],
            'canada': [],
            'season': '2025-2026'
        }

    # Get depth from NOHRSC if available
    usa_depth = nohrsc_data.get('avg_depth_inches')

    # Append today's real data to the season file
    season_data = append_todays_data(season_data, usa_cover, canada_cover, usa_depth)

    # Save updated season data
    save_season_data(season_data)

    # Get history from real accumulated data
    usa_history = [{'date': e['date'], 'value': e['value']} for e in season_data.get('usa', [])]
    canada_history = [{'date': e['date'], 'value': e['value']} for e in season_data.get('canada', [])]

    print_safe(f"Season data: {len(usa_history)} days (from {usa_history[0]['date'] if usa_history else 'N/A'} to {usa_history[-1]['date'] if usa_history else 'N/A'})")
    print_safe("=" * 40 + "\n")

    # Calculate week-over-week change from REAL data
    usa_last_week = usa_history[-8]['value'] if len(usa_history) >= 8 else usa_cover
    canada_last_week = canada_history[-8]['value'] if len(canada_history) >= 8 else canada_cover

    usa_trend, usa_change = calculate_trend(usa_cover, usa_last_week)
    canada_trend, canada_change = calculate_trend(canada_cover, canada_last_week)

    # ========== Collect Metro Area Data ==========

    print_safe(f"\nCollecting metro area data...")
    metros = []

    for metro in METRO_AREAS:
        city_name = metro['city']
        print_safe(f"  {city_name}...", )

        snow_data = None
        depth_inches = 0  # Store numeric depth in inches for sorting
        cover = 0

        if metro['country'] == 'usa':
            # Use NWS API
            snow_data = fetch_nws_snow_data(metro['lat'], metro['lon'])

            if snow_data:
                depth_m = snow_data.get('snow_depth_m')
                temp_c = snow_data.get('temperature_c')
                condition = snow_data.get('condition')

                if depth_m is not None:
                    depth_inches = depth_m * 39.37
                    cover = estimate_snow_cover_from_depth(depth_inches, temp_c, metro['lat'], condition)
                else:
                    cover = estimate_snow_cover_from_depth(None, temp_c, metro['lat'], condition)
                    # Estimate depth from cover
                    if cover == 0:
                        depth_inches = 0
                    elif cover < 20:
                        depth_inches = 0.25  # Trace
                    elif cover < 50:
                        depth_inches = int(1 + cover/20)
                    else:
                        depth_inches = int(4 + cover/15)
            else:
                # Fallback estimate
                cover = estimate_snow_cover_from_depth(None, None, metro['lat'])
                if cover == 0:
                    depth_inches = 0
                elif cover < 30:
                    depth_inches = 0.25  # Trace
                else:
                    depth_inches = int(2 + cover/20)

        else:  # Canada
            # Use Environment Canada
            province = metro.get('province', 'ON')
            site = metro.get('site', '')

            snow_data = fetch_envcan_conditions(province, site)

            if snow_data and snow_data.get('snow_on_ground_cm') is not None:
                depth_cm = snow_data['snow_on_ground_cm']
                temp_c = snow_data.get('temperature_c')
                condition = snow_data.get('condition')

                depth_inches = depth_cm / 2.54
                cover = estimate_snow_cover_from_depth(depth_inches, temp_c, metro['lat'], condition)
            elif snow_data and snow_data.get('temperature_c') is not None:
                temp_c = snow_data['temperature_c']
                condition = snow_data.get('condition')
                cover = estimate_snow_cover_from_depth(None, temp_c, metro['lat'], condition)

                if cover == 0:
                    depth_inches = 0
                elif cover < 30:
                    depth_inches = 0.25  # Trace
                else:
                    depth_inches = (5 + cover/8) / 2.54  # Convert estimated cm to inches
            else:
                # Fallback estimate
                cover = estimate_snow_cover_from_depth(None, None, metro['lat'])
                if cover == 0:
                    depth_inches = 0
                elif cover < 30:
                    depth_inches = 0.25  # Trace
                else:
                    depth_inches = (10 + cover/5) / 2.54  # Convert estimated cm to inches

        # Determine trend based on season patterns (deterministic, not random)
        # In winter months, snow is building; in spring, melting
        if today.month in [11, 12, 1]:
            metro_trend = 'up'  # Winter accumulation
        elif today.month in [3, 4]:
            metro_trend = 'down'  # Spring melt
        else:
            metro_trend = 'stable'  # Transitional periods

        # Store numeric depth in both inches and cm for sorting and display
        depth_cm = round(depth_inches * 2.54, 1)

        # Metro history is not used for sparklines anymore - we use national data
        # Keep empty list for backwards compatibility
        metro_history = []

        # Fetch temperature and anomaly data from Open-Meteo
        temp_data = fetch_openmeteo_temperature(metro['lat'], metro['lon'], city_name)
        # Small delay to avoid rate limiting (Open-Meteo is free but has soft limits)
        time.sleep(0.3)

        metros.append({
            'city': city_name,
            'region': metro['region'],
            'country': metro['country'],
            'lat': metro['lat'],
            'lng': metro['lon'],  # Use 'lng' to match D3 prototype convention
            'cover': round(cover),
            'depthInches': round(depth_inches, 1),  # Numeric for sorting
            'depthCm': depth_cm,  # Numeric for sorting
            'trend': metro_trend,
            'history': metro_history,
            'temperature': temp_data,
            'skiMarket': metro.get('skiMarket', False),
            'importance': metro.get('importance', 100)  # Population in thousands
        })

    # Sort metros by snow cover descending
    metros.sort(key=lambda x: x['cover'], reverse=True)

    # ========== Fetch Prior Year History (Real Data) ==========
    # Fetch real prior year data from NOHRSC for comparison
    print_safe("\nFetching prior year data for comparison...")
    usa_prior_year_history, usa_prior_depth_avg = fetch_prior_year_history(usa_history[-30:] if len(usa_history) > 30 else usa_history)

    # For Canada, use the same dates but we don't have direct historical data
    # So we'll derive from USA ratio
    canada_prior_year_history = []
    if usa_prior_year_history:
        for entry in usa_prior_year_history:
            if entry['value'] is not None:
                # Apply historical USA/Canada ratio (Canada typically ~2x USA)
                canada_value = min(100, round(entry['value'] * 2.0, 1))
            else:
                canada_value = None
            canada_prior_year_history.append({
                'date': entry['date'],
                'value': canada_value
            })

    # ========== Build Output ==========

    # Calculate snow-covered area in both units
    usa_snow_area_sq_mi = int(USA_LAND_AREA_SQ_MI * usa_cover / 100)
    usa_snow_area_sq_km = int(usa_snow_area_sq_mi * 2.58999)
    canada_snow_area_sq_km = int(CANADA_LAND_AREA_SQ_KM * canada_cover / 100)
    canada_snow_area_sq_mi = int(canada_snow_area_sq_km / 2.58999)

    # Estimate average depths in both units
    usa_avg_depth_inches = nohrsc_data.get('avg_depth_inches')
    if usa_avg_depth_inches is None:
        usa_avg_depth_inches = max(1, int(2 + usa_cover / 12))
    usa_avg_depth_cm = round(usa_avg_depth_inches * 2.54, 1)

    canada_avg_depth_cm = max(5, int(8 + canada_cover / 6))
    canada_avg_depth_inches = round(canada_avg_depth_cm / 2.54, 1)

    # Estimate Canada prior year depth from USA ratio (using real USA prior depth data)
    canada_prior_depth_avg = None
    if usa_prior_depth_avg is not None and usa_avg_depth_inches is not None and usa_avg_depth_inches > 0:
        # Use current Canada/USA depth ratio to estimate Canada prior year depth
        depth_ratio = canada_avg_depth_inches / usa_avg_depth_inches if usa_avg_depth_inches > 0 else 1.5
        canada_prior_depth_avg = round(usa_prior_depth_avg * depth_ratio, 1)

    # Calculate country-level temperature anomalies from metro data
    usa_temp = fetch_country_temperature_anomaly(metros, 'usa')
    canada_temp = fetch_country_temperature_anomaly(metros, 'canada')

    # Calculate ski market aggregates for header widget
    usa_ski = calculate_ski_market_aggregates(metros, 'usa')
    canada_ski = calculate_ski_market_aggregates(metros, 'canada')

    print_safe(f"\nSki Market Aggregates:")
    if usa_ski:
        print_safe(f"  USA Ski Markets ({usa_ski['metro_count']} metros): {usa_ski['cover']}% cover, {usa_ski['avg_anomaly_f']}°F anomaly")
    if canada_ski:
        print_safe(f"  Canada Ski Markets ({canada_ski['metro_count']} metros): {canada_ski['cover']}% cover, {canada_ski['avg_anomaly_f']}°F anomaly")

    # Calculate combined North America temperature anomaly
    combined_temp = None
    if usa_temp and canada_temp:
        all_temps = []
        all_anomalies = []
        for m in metros:
            t = m.get('temperature', {})
            if t.get('temp_c') is not None:
                all_temps.append(t['temp_c'])
            if t.get('anomaly_c') is not None:
                all_anomalies.append(t['anomaly_c'])
        if all_temps or all_anomalies:
            combined_temp = {
                'avg_temp_c': round(sum(all_temps) / len(all_temps), 1) if all_temps else None,
                'avg_temp_f': round((sum(all_temps) / len(all_temps)) * 9/5 + 32, 1) if all_temps else None,
                'avg_anomaly_c': round(sum(all_anomalies) / len(all_anomalies), 1) if all_anomalies else None,
                'avg_anomaly_f': round((sum(all_anomalies) / len(all_anomalies)) * 9/5, 1) if all_anomalies else None
            }

    data = {
        'updated': today.strftime('%Y-%m-%d %H:%M') + ' UTC',
        'data_sources': {
            'usa': usa_source,
            'canada': canada_source,
            'rutgers_available': rutgers_data.get('north_america_extent_km2') is not None,
            'copernicus_available': copernicus_data.get('usa_cover') is not None or copernicus_data.get('canada_cover') is not None
        },
        'combined': {
            'cover': round(combined_cover, 1),
            'change': usa_change if usa_trend != 'stable' else canada_change,
            'context': f'Approximately {round(combined_cover)}% of North American land area currently has visible snow cover',
            'temperature': combined_temp
        },
        'skiMarkets': {
            'usa': usa_ski,
            'canada': canada_ski
        },
        'usa': {
            'cover': round(usa_cover, 1),
            'change': usa_change,
            'areaSqMi': usa_snow_area_sq_mi,
            'areaSqKm': usa_snow_area_sq_km,
            'avgDepthInches': usa_avg_depth_inches,
            'avgDepthCm': usa_avg_depth_cm,
            'priorYearAvgDepthInches': usa_prior_depth_avg,
            'priorYearAvgDepthCm': round(usa_prior_depth_avg * 2.54, 1) if usa_prior_depth_avg else None,
            'history': usa_history,
            'priorYearHistory': usa_prior_year_history,
            'temperature': usa_temp
        },
        'canada': {
            'cover': round(canada_cover, 1),
            'change': canada_change,
            'areaSqMi': canada_snow_area_sq_mi,
            'areaSqKm': canada_snow_area_sq_km,
            'avgDepthInches': canada_avg_depth_inches,
            'avgDepthCm': canada_avg_depth_cm,
            'priorYearAvgDepthInches': canada_prior_depth_avg,
            'priorYearAvgDepthCm': round(canada_prior_depth_avg * 2.54, 1) if canada_prior_depth_avg else None,
            'history': canada_history,
            'priorYearHistory': canada_prior_year_history,
            'temperature': canada_temp
        },
        'metros': metros,
        'feederRegions': FEEDER_REGIONS
    }

    return data

def save_snow_data(data):
    """Save snow cover data to JSON file"""
    output_path = 'static/data/snow-cover.json'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print_safe(f"\nData saved to: {output_path}")
    return output_path

# ============================================
# Main
# ============================================

def main():
    """Main entry point"""
    try:
        data = collect_snow_data()
        output_path = save_snow_data(data)

        print_safe("\n" + "=" * 60)
        print_safe("SUMMARY")
        print_safe("=" * 60)
        print_safe(f"Combined snow cover: {data['combined']['cover']}%")
        print_safe(f"USA: {data['usa']['cover']}% ({data['data_sources']['usa']})")
        print_safe(f"Canada: {data['canada']['cover']}% ({data['data_sources']['canada']})")
        print_safe(f"Metro areas tracked: {len(data['metros'])}")
        print_safe(f"Output: {output_path}")
        print_safe("=" * 60)

        return 0
    except Exception as e:
        print_safe(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
