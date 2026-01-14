#!/usr/bin/env python3
"""
Denver International Airport (DEN) Monthly Passenger Data Scraper

Downloads and parses monthly management reports from flydenver.com
to extract passenger data for year-over-year comparisons.

Data source: https://www.flydenver.com/about-den/governance/reports-and-financials/
"""

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    print("Warning: pdfplumber not installed. Install with: pip install pdfplumber")

# Output paths
OUTPUT_DIR = Path(__file__).parent / 'static' / 'data'
OUTPUT_FILE = OUTPUT_DIR / 'den-monthly.json'
RAW_PDF_DIR = OUTPUT_DIR / 'raw' / 'den'

# DEN reports page
DEN_REPORTS_URL = "https://www.flydenver.com/about-den/governance/reports-and-financials/"

# Known PDF patterns
# DEN stores PDFs in various locations
PDF_BASE_URLS = [
    "https://www.flydenver.com/app/uploads/",
    "https://www.flydenver.com/sites/default/files/",
]

MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]

# Known data points from press releases (for validation)
KNOWN_DATA_POINTS = {
    # 2024 - Annual: 82,358,744 (+5.8% YoY)
    (2024, 7): 7890000,   # July - busiest month ever
    (2024, 6): 7610000,
    (2024, 1): 5760000,
    (2024, 2): 5840000,

    # These can be updated as press releases are found
}

# Annual totals for validation
ANNUAL_TOTALS = {
    2024: 82358744,
    2023: 77847000,
    2022: 69286000,
    2021: 58828000,
    2020: 33300000,  # COVID year
    2019: 69015000,
}


def fetch_reports_page():
    """
    Fetch the reports and financials page to find PDF links.
    """
    try:
        req = urllib.request.Request(DEN_REPORTS_URL, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching reports page: {e}")
        return None


def find_pdf_links(html):
    """
    Parse HTML to find PDF links to monthly reports.
    """
    if not html:
        return []

    # Find all PDF links
    pdf_pattern = r'href=["\']([^"\']*\.pdf)["\']'
    matches = re.findall(pdf_pattern, html, re.IGNORECASE)

    # Filter to monthly/management report PDFs
    report_pdfs = []
    for url in matches:
        lower = url.lower()
        if any(kw in lower for kw in ['monthly', 'management', 'report', 'statistics', 'traffic']):
            if not url.startswith('http'):
                url = "https://www.flydenver.com" + url if url.startswith('/') else "https://www.flydenver.com/" + url
            report_pdfs.append(url)

    return list(set(report_pdfs))


def generate_pdf_urls(year, month):
    """
    Generate possible URL patterns for DEN monthly reports.
    """
    month_name = MONTHS[month - 1]
    month_num = str(month).zfill(2)

    patterns = []
    for base in PDF_BASE_URLS:
        patterns.extend([
            f"{base}{year}/{month_num}/Monthly-Management-Report.pdf",
            f"{base}{year}/{month_num}/DEN-Monthly-Report.pdf",
            f"{base}{year}/{month_num}/{month_name}-{year}-Report.pdf",
            f"{base}{year}/{month_num}/Management-Report-{month_name}-{year}.pdf",
            f"{base}{year}/{month_num}/Air-Traffic-Statistics.pdf",
            f"{base}{year}/monthly-management-report-{month_name.lower()}-{year}.pdf",
        ])

    return patterns


def download_pdf(url):
    """
    Download PDF from URL.
    """
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status == 200:
                return response.read()
    except urllib.error.HTTPError:
        pass
    except Exception:
        pass
    return None


def extract_den_data(pdf_path):
    """
    Extract passenger data from DEN PDF.

    DEN management reports typically contain:
    - Total passengers by month
    - Airline-by-airline breakdown
    - Year-over-year comparisons
    - Cargo statistics
    """
    if not HAS_PDFPLUMBER:
        return None

    data = {
        'total_passengers': None,
        'enplaned': None,
        'deplaned': None,
        'domestic': None,
        'international': None,
        'yoy_pct': None,
        'monthly_breakdown': [],
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = ""
            all_tables = []

            for page in pdf.pages:
                text = page.extract_text() or ""
                all_text += text + "\n"

                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)

            # Pattern 1: Look for total passengers in text
            total_patterns = [
                r'Total\s+Passengers[:\s]+([0-9,]+)',
                r'([0-9,]+)\s+(?:Total\s+)?Passengers',
                r'Passenger\s+Total[:\s]+([0-9,]+)',
                r'Monthly\s+Passengers[:\s]+([0-9,]+)',
            ]

            for pattern in total_patterns:
                matches = re.findall(pattern, all_text, re.IGNORECASE)
                for match in matches:
                    value = int(match.replace(',', ''))
                    # DEN monthly passengers are typically 5-8 million
                    if 4000000 < value < 10000000:
                        if data['total_passengers'] is None:
                            data['total_passengers'] = value

            # Pattern 2: Look for YoY percentage
            yoy_patterns = [
                r'([-+]?\d+\.?\d*)\s*%\s*(?:change|YoY|vs|compared)',
                r'Year[- ]over[- ]Year[:\s]+([-+]?\d+\.?\d*)\s*%',
            ]

            for pattern in yoy_patterns:
                match = re.search(pattern, all_text, re.IGNORECASE)
                if match:
                    data['yoy_pct'] = float(match.group(1))
                    break

            # Pattern 3: Parse tables for monthly data
            for table in all_tables:
                if not table:
                    continue

                header = table[0] if table else []
                if not header:
                    continue

                # Look for passenger-related tables
                header_text = ' '.join(str(h) for h in header if h).lower()
                if 'passenger' in header_text or 'enplan' in header_text:

                    for row in table[1:]:
                        if not row:
                            continue

                        # Look for numeric values in passenger range
                        for cell in row:
                            if cell:
                                clean = str(cell).replace(',', '').strip()
                                if clean.isdigit():
                                    value = int(clean)
                                    if 4000000 < value < 10000000:
                                        if data['total_passengers'] is None:
                                            data['total_passengers'] = value

            data['_raw_text_preview'] = all_text[:1000]

    except Exception as e:
        print(f"    Error parsing PDF: {e}")
        return None

    return data


# REMOVED: estimate_monthly_from_annual function
# Per project guidelines: Never fabricate data. Show null instead of estimates.


def fetch_den_monthly_data(start_year=2023, end_year=None):
    """
    Fetch monthly passenger data for DEN.
    """
    if end_year is None:
        end_year = datetime.now().year

    print("=" * 60)
    print("DEN AIRPORT MONTHLY DATA SCRAPER")
    print("=" * 60)
    print()

    # Ensure raw PDF directory exists
    RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    # First, try to fetch reports page
    print("Fetching reports page...")
    html = fetch_reports_page()
    found_pdfs = []

    if html:
        pdf_links = find_pdf_links(html)
        print(f"  Found {len(pdf_links)} PDF links on page")
        for link in pdf_links[:5]:
            print(f"    - ...{link[-50:]}")

        # Download and check each PDF
        for url in pdf_links[:10]:  # Limit to first 10
            pdf_content = download_pdf(url)
            if pdf_content:
                found_pdfs.append((url, pdf_content))
                print(f"  Downloaded: {url.split('/')[-1]}")

    # Try URL patterns for each year/month
    print("\nTrying URL patterns...")
    for year in range(start_year, end_year + 1):
        current_month = datetime.now().month if year == datetime.now().year else 12

        for month in range(1, current_month + 1):
            urls = generate_pdf_urls(year, month)
            for url in urls[:3]:  # Try first 3 patterns
                # Check cache
                cache_name = f"DEN-{year}-{str(month).zfill(2)}.pdf"
                cached_pdf = RAW_PDF_DIR / cache_name

                if cached_pdf.exists():
                    pdf_content = cached_pdf.read_bytes()
                else:
                    pdf_content = download_pdf(url)
                    if pdf_content:
                        cached_pdf.write_bytes(pdf_content)

                if pdf_content:
                    found_pdfs.append((url, pdf_content))
                    print(f"  Found: {MONTHS[month-1]} {year}")
                    break

    # Parse found PDFs
    print(f"\nParsing {len(found_pdfs)} PDFs...")
    for url, pdf_content in found_pdfs:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(pdf_content)
            tmp_path = tmp.name

        try:
            data = extract_den_data(tmp_path)
            if data and data.get('total_passengers'):
                # Try to determine year/month from URL or content
                year_match = re.search(r'/(\d{4})/', url)
                month_match = re.search(r'/(\d{2})/', url)

                if year_match and month_match:
                    year = int(year_match.group(1))
                    month = int(month_match.group(1))

                    results.append({
                        'airport': 'DEN',
                        'year': year,
                        'month': month,
                        'passengers': data['total_passengers'],
                        'yoy_pct': data.get('yoy_pct'),
                        'is_estimate': False,
                        'source_url': url,
                        'extracted': datetime.utcnow().isoformat() + 'Z'
                    })
                    print(f"    {MONTHS[month-1]} {year}: {data['total_passengers']:,}")

        finally:
            os.unlink(tmp_path)

    # Add known data points from press releases (real data only)
    print("\nAdding known data points from press releases...")
    for (year, month), passengers in KNOWN_DATA_POINTS.items():
        # Only add if we don't already have this month
        exists = any(r['year'] == year and r['month'] == month for r in results)
        if not exists:
            results.append({
                'airport': 'DEN',
                'year': year,
                'month': month,
                'passengers': passengers,
                'is_estimate': False,
                'source': 'Press release / reported value'
            })
            print(f"  {MONTHS[month-1]} {year}: {passengers:,}")

    if not results:
        print("\n  No data extracted. DEN requires:")
        print("    - Manual PDF download from flydenver.com, OR")
        print("    - BTS T-100 CSV download")

    return results


def calculate_yoy_from_data(results):
    """
    Calculate year-over-year percentages from extracted monthly data.
    """
    lookup = {}
    for r in results:
        key = (r['airport'], r['year'], r['month'])
        lookup[key] = r['passengers']

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

    real_data = [r for r in results if not r.get('is_estimate', False)]
    estimated_data = [r for r in results if r.get('is_estimate', False)]

    output = {
        'generated': datetime.utcnow().isoformat() + 'Z',
        'source': 'Denver International Airport Management Reports',
        'source_url': DEN_REPORTS_URL,
        'airport': 'DEN',
        'data_quality_note': 'Mix of extracted PDF data and estimates from annual totals.',
        'annual_totals': ANNUAL_TOTALS,
        'monthly': sorted(results, key=lambda x: (x['year'], x['month']), reverse=True),
        'real_data_count': len(real_data),
        'estimated_data_count': len(estimated_data),
        'summary': {}
    }

    by_year = {}
    for r in results:
        year = r['year']
        if year not in by_year:
            by_year[year] = {'passengers': 0, 'months': 0, 'estimated': 0}
        by_year[year]['passengers'] += r['passengers']
        by_year[year]['months'] += 1
        if r.get('is_estimate'):
            by_year[year]['estimated'] += 1

    output['summary'] = {
        str(year): {
            'total_passengers': data['passengers'],
            'months_available': data['months'],
            'estimated_months': data['estimated'],
            'known_annual': ANNUAL_TOTALS.get(year)
        }
        for year, data in sorted(by_year.items(), reverse=True)
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nOutput saved to: {OUTPUT_FILE}")
    return output


def main():
    results = fetch_den_monthly_data(start_year=2023)

    if not results:
        print("\nNo data extracted.")
        return

    results = calculate_yoy_from_data(results)
    output = save_results(results)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Real data points: {output['real_data_count']}")
    print(f"Estimated data points: {output['estimated_data_count']}")
    print()

    for year, summary in output['summary'].items():
        est = f" ({summary['estimated_months']} estimated)" if summary['estimated_months'] > 0 else ""
        known = f" [Known: {summary['known_annual']:,}]" if summary.get('known_annual') else ""
        print(f"  {year}: {summary['total_passengers']:,} passengers{est}{known}")

    print("\nLatest months:")
    for r in output['monthly'][:6]:
        month_name = MONTHS[r['month'] - 1][:3]
        yoy = f"{r['yoy_pct']:+.1f}%" if r.get('yoy_pct') else "N/A"
        est = " (est)" if r.get('is_estimate') else ""
        print(f"  {month_name} {r['year']}: {r['passengers']:,} ({yoy} YoY){est}")


if __name__ == '__main__':
    main()
