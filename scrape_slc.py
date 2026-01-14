#!/usr/bin/env python3
"""
Salt Lake City Airport (SLC) Monthly Passenger Data Scraper

Downloads and parses monthly Air Traffic Statistics PDFs from slcairport.com
to extract passenger enplanement data for year-over-year comparisons.

Data source: https://slcairport.com/about-the-airport/airport-overview/air-traffic-statistics/
"""

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import urllib.error

# Try to import pdfplumber, fall back to basic extraction
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    print("Warning: pdfplumber not installed. Install with: pip install pdfplumber")
    print("Falling back to basic text extraction...")

# Output paths
OUTPUT_DIR = Path(__file__).parent / 'static' / 'data'
OUTPUT_FILE = OUTPUT_DIR / 'slc-monthly.json'
RAW_PDF_DIR = OUTPUT_DIR / 'raw' / 'slc'

# Base URL for SLC PDFs
BASE_URL = "https://slcairport.com/assets/pdfDocuments/Air-Traffic-Statistics/"

# Month names for URL patterns
MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]


def get_pdf_url_patterns(year, month_name):
    """
    Generate possible URL patterns for SLC PDFs.
    SLC naming conventions vary by year and aren't consistent.
    """
    patterns = [
        # Current patterns (2024-2025)
        f"{month_name}-{year}-Air-Traffic-Statistics.pdf",
        f"Air-Traffic-Statistics-{month_name}-{year}.pdf",
        f"Air-Traffic-Statistics-{year}-{month_name}.pdf",
        # Alternative patterns
        f"{month_name}{year}-Air-Traffic-Statistics.pdf",
        f"{month_name.lower()}-{year}-air-traffic-statistics.pdf",
        f"Air-Traffic-Statistics-{month_name.lower()}-{year}.pdf",
        # Patterns with dashes
        f"{month_name}-{year}.pdf",
        f"{year}-{month_name}-Air-Traffic-Statistics.pdf",
    ]
    return [BASE_URL + p for p in patterns]


def get_annual_summary_patterns(year):
    """
    Generate URL patterns for annual summary PDFs.
    These contain monthly breakdowns for the full year.
    """
    patterns = [
        f"{year}CY-Summary-final.pdf",
        f"{year}-CY-Summary.pdf",
        f"{year}CY-Summary.pdf",
        f"CY-{year}-Summary.pdf",
        f"{year}-annual-summary.pdf",
    ]
    return [BASE_URL + p for p in patterns]


def download_pdf(year, month):
    """
    Download SLC PDF for given year and month.
    Returns PDF bytes if successful, None otherwise.
    """
    month_name = MONTHS[month - 1]
    urls = get_pdf_url_patterns(year, month_name)

    for url in urls:
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    print(f"  Found: {url}")
                    return response.read(), url
        except urllib.error.HTTPError as e:
            if e.code != 404:
                print(f"  HTTP Error {e.code}: {url}")
            continue
        except Exception as e:
            continue

    return None, None


def extract_passengers_with_pdfplumber(pdf_path):
    """
    Extract passenger data using pdfplumber's table extraction.

    SLC PDFs typically contain tables with:
    - Total passengers (enplaned + deplaned)
    - Domestic vs international breakdown
    - Cargo statistics
    """
    data = {
        'total_passengers': None,
        'enplaned': None,
        'deplaned': None,
        'domestic': None,
        'international': None,
        'current_month': None,
        'prior_year_month': None,
        'yoy_pct': None,
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            tables = []

            for page in pdf.pages:
                text += page.extract_text() or ""
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)

            # Parse text for key metrics
            # Look for patterns like "Total Passengers: 2,150,000"

            # Pattern 1: Look for "Passengers" followed by numbers
            passenger_patterns = [
                r'Total\s+Passengers[:\s]+([0-9,]+)',
                r'Enplaned\s+Passengers[:\s]+([0-9,]+)',
                r'TOTAL\s+PASSENGERS[:\s]+([0-9,]+)',
                r'Total\s+Enplanements[:\s]+([0-9,]+)',
            ]

            for pattern in passenger_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = int(match.group(1).replace(',', ''))
                    if data['total_passengers'] is None or value > data['total_passengers']:
                        data['total_passengers'] = value

            # Pattern 2: Look for enplaned specifically
            enplaned_match = re.search(r'Enplaned[:\s]+([0-9,]+)', text, re.IGNORECASE)
            if enplaned_match:
                data['enplaned'] = int(enplaned_match.group(1).replace(',', ''))

            # Pattern 3: Look for YoY percentage
            yoy_patterns = [
                r'([-+]?\d+\.?\d*)\s*%\s*(?:change|vs|compared)',
                r'Year[- ]over[- ]Year[:\s]+([-+]?\d+\.?\d*)\s*%',
                r'YoY[:\s]+([-+]?\d+\.?\d*)\s*%',
            ]

            for pattern in yoy_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data['yoy_pct'] = float(match.group(1))
                    break

            # Pattern 4: Parse tables for structured data
            for table in tables:
                if not table:
                    continue

                for row in table:
                    if not row:
                        continue

                    # Convert row to strings
                    row_str = [str(cell).strip() if cell else '' for cell in row]
                    row_text = ' '.join(row_str).lower()

                    # Look for passenger-related rows
                    if 'passenger' in row_text or 'enplan' in row_text:
                        # Find numeric values in row
                        for cell in row_str:
                            # Remove commas and try to parse as number
                            clean = cell.replace(',', '').replace(' ', '')
                            if clean.isdigit() and int(clean) > 100000:
                                if data['total_passengers'] is None:
                                    data['total_passengers'] = int(clean)

            # Also store raw text for debugging
            data['_raw_text_preview'] = text[:500] if text else None

    except Exception as e:
        print(f"    Error parsing PDF: {e}")
        return None

    return data


def extract_passengers_basic(pdf_path):
    """
    Basic text extraction when pdfplumber is not available.
    Uses PyPDF2 or similar basic extraction.
    """
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""

        # Look for passenger numbers in text
        data = {'total_passengers': None, 'yoy_pct': None}

        # Find large numbers that look like passenger counts
        numbers = re.findall(r'([0-9,]{7,})', text)
        for num in numbers:
            value = int(num.replace(',', ''))
            if 100000 < value < 50000000:  # Reasonable passenger range
                if data['total_passengers'] is None or value > data['total_passengers']:
                    data['total_passengers'] = value

        return data

    except ImportError:
        print("    Error: PyPDF2 not installed. Cannot extract PDF text.")
        return None
    except Exception as e:
        print(f"    Error with basic extraction: {e}")
        return None


def download_annual_summary(year):
    """
    Download annual summary PDF for a given year.
    Returns PDF bytes if successful, None otherwise.
    """
    urls = get_annual_summary_patterns(year)

    for url in urls:
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    print(f"  Found annual summary: {url.split('/')[-1]}")
                    return response.read(), url
        except urllib.error.HTTPError:
            continue
        except Exception:
            continue

    return None, None


def extract_annual_summary(pdf_path):
    """
    Extract monthly data from annual summary PDF.

    SLC annual summaries have a text format like:
    "Total Passengers 2,232,571 2,194,717 2,497,838 ... 28,364,610"

    The values are in order: Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec YTD
    """
    if not HAS_PDFPLUMBER:
        return []

    results = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Get text from first page (summary stats)
            text = pdf.pages[0].extract_text() or ""

            # Find the "Total Passengers" line
            for line in text.split('\n'):
                if 'Total Passengers' in line:
                    # Extract all numbers from this line
                    # Format: "Total Passengers 2,232,571 2,194,717 ... YTD_TOTAL"
                    numbers = re.findall(r'[\d,]+', line)

                    # Convert to integers, filtering out small numbers
                    values = []
                    for num in numbers:
                        try:
                            val = int(num.replace(',', ''))
                            # Monthly passengers for SLC are 1.9M - 2.6M range
                            if val > 1000000:
                                values.append(val)
                        except ValueError:
                            pass

                    # We expect 13 values: 12 months + YTD total
                    # The last value is the YTD total (largest), skip it
                    if len(values) >= 12:
                        # Sort to find YTD (largest) and exclude it
                        monthly_values = sorted(values)[:-1] if len(values) == 13 else values[:12]

                        # But we need them in original order (Jan-Dec)
                        # Re-extract in order
                        monthly_values = values[:12]

                        for month_idx, passengers in enumerate(monthly_values):
                            results.append({
                                'month': month_idx + 1,
                                'passengers': passengers
                            })

                        print(f"    Found 12 months: {[r['passengers'] for r in results[:3]]}...")
                    break

    except Exception as e:
        print(f"    Error parsing annual summary: {e}")

    return results


def fetch_slc_monthly_data(start_year=2023, end_year=None):
    """
    Fetch monthly passenger data for SLC across multiple years.
    """
    if end_year is None:
        end_year = datetime.now().year

    current_month = datetime.now().month
    current_year = datetime.now().year

    results = []

    print("=" * 60)
    print("SLC AIRPORT MONTHLY DATA SCRAPER")
    print("=" * 60)
    print(f"\nFetching data for {start_year} to {end_year}")
    print()

    # Ensure raw PDF directory exists
    RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)

    # First, try to get annual summaries for historical data
    print("Checking for annual summaries...")
    for year in range(start_year, end_year):  # Don't include current year
        cached_annual = RAW_PDF_DIR / f"SLC-{year}-annual.pdf"

        if cached_annual.exists():
            print(f"  Using cached {year} annual summary")
            annual_content = cached_annual.read_bytes()
        else:
            annual_content, annual_url = download_annual_summary(year)
            if annual_content:
                cached_annual.write_bytes(annual_content)

        if annual_content:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(annual_content)
                tmp_path = tmp.name

            try:
                monthly = extract_annual_summary(tmp_path)
                for m in monthly:
                    results.append({
                        'airport': 'SLC',
                        'year': year,
                        'month': m['month'],
                        'passengers': m['passengers'],
                        'source': f'{year} annual summary',
                        'extracted': datetime.now(timezone.utc).isoformat()
                    })
                if monthly:
                    print(f"    Extracted {len(monthly)} months from {year} annual summary")
            finally:
                os.unlink(tmp_path)

    print()

    # Then try individual monthly PDFs
    for year in range(start_year, end_year + 1):
        print(f"\n{year}:")
        print("-" * 40)

        # Determine which months to try
        if year == current_year:
            # For current year, try up to previous month (data lag)
            max_month = current_month - 1
            if max_month < 1:
                continue
        else:
            max_month = 12

        for month in range(1, max_month + 1):
            # Skip if we already have data from annual summary
            existing = [r for r in results if r['year'] == year and r['month'] == month]
            if existing:
                print(f"  {MONTHS[month - 1]} {year}... (from annual summary: {existing[0]['passengers']:,})")
                continue

            month_name = MONTHS[month - 1]
            print(f"  {month_name} {year}...")

            # Check if we already have cached PDF
            cached_pdf = RAW_PDF_DIR / f"SLC-{year}-{str(month).zfill(2)}.pdf"

            if cached_pdf.exists():
                print(f"    Using cached PDF")
                pdf_content = cached_pdf.read_bytes()
                pdf_url = f"(cached: {cached_pdf.name})"
            else:
                # Download PDF
                pdf_content, pdf_url = download_pdf(year, month)

                if pdf_content:
                    # Save to cache
                    cached_pdf.write_bytes(pdf_content)
                    print(f"    Cached to {cached_pdf.name}")

            if not pdf_content:
                print(f"    Not found")
                continue

            # Parse PDF
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(pdf_content)
                tmp_path = tmp.name

            try:
                if HAS_PDFPLUMBER:
                    data = extract_passengers_with_pdfplumber(tmp_path)
                else:
                    data = extract_passengers_basic(tmp_path)

                if data and data.get('total_passengers'):
                    results.append({
                        'airport': 'SLC',
                        'year': year,
                        'month': month,
                        'passengers': data['total_passengers'],
                        'enplaned': data.get('enplaned'),
                        'yoy_pct': data.get('yoy_pct'),
                        'source_url': pdf_url,
                        'extracted': datetime.now(timezone.utc).isoformat()
                    })
                    print(f"    Passengers: {data['total_passengers']:,}")
                    if data.get('yoy_pct'):
                        print(f"    YoY: {data['yoy_pct']:+.1f}%")
                else:
                    print(f"    Could not extract passenger data")

            finally:
                os.unlink(tmp_path)

    return results


def calculate_yoy_from_data(results):
    """
    Calculate year-over-year percentages from extracted monthly data.
    """
    # Build lookup by airport/year/month
    lookup = {}
    for r in results:
        key = (r['airport'], r['year'], r['month'])
        lookup[key] = r['passengers']

    # Calculate YoY for each record
    for r in results:
        if r.get('yoy_pct') is None:
            prior_key = (r['airport'], r['year'] - 1, r['month'])
            prior_passengers = lookup.get(prior_key)

            if prior_passengers and prior_passengers > 0:
                yoy = ((r['passengers'] - prior_passengers) / prior_passengers) * 100
                r['yoy_pct'] = round(yoy, 2)

    return results


def save_results(results):
    """
    Save results to JSON file.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output = {
        'generated': datetime.now(timezone.utc).isoformat(),
        'source': 'Salt Lake City International Airport - Air Traffic Statistics',
        'source_url': 'https://slcairport.com/about-the-airport/airport-overview/air-traffic-statistics/',
        'airport': 'SLC',
        'monthly': sorted(results, key=lambda x: (x['year'], x['month']), reverse=True),
        'summary': {}
    }

    # Build summary by year
    by_year = {}
    for r in results:
        year = r['year']
        if year not in by_year:
            by_year[year] = {'passengers': 0, 'months': 0}
        by_year[year]['passengers'] += r['passengers']
        by_year[year]['months'] += 1

    output['summary'] = {
        str(year): {
            'total_passengers': data['passengers'],
            'months_available': data['months'],
            'is_complete': data['months'] == 12
        }
        for year, data in sorted(by_year.items(), reverse=True)
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nOutput saved to: {OUTPUT_FILE}")
    return output


def main():
    # Fetch data for recent years
    results = fetch_slc_monthly_data(start_year=2023)

    if not results:
        print("\nNo data extracted. Check if pdfplumber is installed:")
        print("  pip install pdfplumber")
        return

    # Calculate YoY where missing
    results = calculate_yoy_from_data(results)

    # Save results
    output = save_results(results)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for year, summary in output['summary'].items():
        status = "Complete" if summary['is_complete'] else f"{summary['months_available']}/12 months"
        print(f"  {year}: {summary['total_passengers']:,} passengers ({status})")

    print("\nLatest months:")
    for r in output['monthly'][:6]:
        month_name = MONTHS[r['month'] - 1][:3]
        yoy = f"{r['yoy_pct']:+.1f}%" if r.get('yoy_pct') else "N/A"
        print(f"  {month_name} {r['year']}: {r['passengers']:,} ({yoy} YoY)")


if __name__ == '__main__':
    main()
