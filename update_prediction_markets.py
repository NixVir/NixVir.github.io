#!/usr/bin/env python3
"""
Fetch prediction market data from Kalshi and Polymarket APIs.
No authentication required for public market data.

Output: static/data/prediction-markets.json
"""

import json
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

# Kalshi API configuration
KALSHI_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

# Polymarket API configuration
POLYMARKET_BASE_URL = "https://gamma-api.polymarket.com"

# Kalshi market series to fetch
KALSHI_SERIES = [
    {"series": "KXRECSSNBER", "category": "recession", "display_name": "US Recession"},
    {"series": "KXGDP", "category": "gdp", "display_name": "GDP Growth"},
    {"series": "KXGDPYEAR", "category": "gdp", "display_name": "Annual GDP"},
    {"series": "KXFEDDECISION", "category": "fed_policy", "display_name": "Fed Decision"},
    {"series": "KXFED", "category": "fed_policy", "display_name": "Fed Funds Rate"},
    {"series": "KXRATECUTCOUNT", "category": "fed_policy", "display_name": "Rate Cuts Count"},
    {"series": "KXCPI", "category": "inflation", "display_name": "Monthly CPI"},
    {"series": "KXINFLY", "category": "inflation", "display_name": "Annual Inflation"},
    {"series": "KXPCECORE", "category": "inflation", "display_name": "Core PCE"},
    {"series": "KXWTIW", "category": "energy", "display_name": "WTI Oil Weekly"},
    {"series": "KXWTIMAX", "category": "energy", "display_name": "WTI Yearly High"},
    {"series": "KXAAAGASW", "category": "energy", "display_name": "Gas Price Direction"},
]

# Polymarket slugs to fetch
POLYMARKET_SLUGS = [
    {"slug": "us-recession-in-2025", "category": "recession", "display_name": "US Recession 2025"},
    {"slug": "how-many-fed-rate-cuts-in-2026", "category": "fed_policy", "display_name": "Fed Rate Cuts 2026"},
    {"slug": "will-trump-fire-powell-in-2025", "category": "policy_risk", "display_name": "Trump Fires Powell"},
]


def fetch_kalshi_series(series_ticker):
    """
    Fetch Kalshi market data by series ticker.
    Returns list of markets in the series.
    """
    url = f"{KALSHI_BASE_URL}/markets"
    params = {
        "series_ticker": series_ticker,
        "status": "open"
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        markets = []
        for m in data.get("markets", []):
            # API returns last_price in cents (0-99), yes_bid/yes_ask for order book
            last_price = m.get("last_price", 0) or 0
            yes_bid = m.get("yes_bid", 0) or 0
            yes_ask = m.get("yes_ask", 0) or 0
            # Use last_price as primary, or midpoint of bid/ask
            if last_price > 0:
                yes_price = last_price
            elif yes_bid > 0 and yes_ask > 0:
                yes_price = (yes_bid + yes_ask) / 2
            else:
                yes_price = yes_bid or yes_ask or 0

            markets.append({
                "ticker": m.get("ticker"),
                "title": m.get("title"),
                "yes_price": yes_price,
                "no_price": 100 - yes_price if yes_price else 0,
                "yes_probability": yes_price / 100,
                "yes_bid": yes_bid,
                "yes_ask": yes_ask,
                "volume": m.get("volume"),
                "volume_24h": m.get("volume_24h"),
                "open_interest": m.get("open_interest"),
                "close_time": m.get("close_time"),
            })

        return markets

    except requests.exceptions.RequestException as e:
        print(f"  Error fetching Kalshi {series_ticker}: {e}")
        return []


def fetch_polymarket_market(slug):
    """
    Fetch Polymarket market data by slug.
    Returns market data dict or None.
    """
    url = f"{POLYMARKET_BASE_URL}/markets"
    params = {"slug": slug}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data or len(data) == 0:
            return None

        m = data[0]

        # Parse outcome prices (JSON string like "[0.05, 0.95]")
        prices = json.loads(m.get("outcomePrices", "[0, 0]"))
        yes_prob = float(prices[0]) if len(prices) > 0 else 0
        no_prob = float(prices[1]) if len(prices) > 1 else 0

        return {
            "slug": m.get("slug"),
            "title": m.get("question"),
            "yes_probability": yes_prob,
            "no_probability": no_prob,
            "volume": m.get("volume"),
            "volume_24h": m.get("volume24hr"),
            "last_trade_price": m.get("lastTradePrice"),
            "end_date": m.get("endDate"),
        }

    except requests.exceptions.RequestException as e:
        print(f"  Error fetching Polymarket {slug}: {e}")
        return None
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"  Error parsing Polymarket {slug}: {e}")
        return None


def collect_all_markets():
    """
    Collect all prediction market data from Kalshi and Polymarket.
    Returns structured data for dashboard display.
    """
    result = {
        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "kalshi": {},
        "polymarket": {},
        "summary": {}
    }

    # Fetch Kalshi markets
    print("Fetching Kalshi markets...")
    for config in KALSHI_SERIES:
        series = config["series"]
        category = config["category"]
        display_name = config["display_name"]

        time.sleep(0.5)  # Rate limiting
        markets = fetch_kalshi_series(series)

        if markets:
            # Store in result
            if category not in result["kalshi"]:
                result["kalshi"][category] = []

            result["kalshi"][category].append({
                "series": series,
                "display_name": display_name,
                "markets": markets
            })
            print(f"  OK {series}: {len(markets)} market(s)")
        else:
            print(f"  -- {series}: no open markets")

    # Fetch Polymarket markets
    print("\nFetching Polymarket markets...")
    for config in POLYMARKET_SLUGS:
        slug = config["slug"]
        category = config["category"]
        display_name = config["display_name"]

        time.sleep(0.5)  # Rate limiting
        market = fetch_polymarket_market(slug)

        if market:
            if category not in result["polymarket"]:
                result["polymarket"][category] = []

            market["display_name"] = display_name
            result["polymarket"][category].append(market)
            print(f"  OK {slug}: {market['yes_probability']*100:.1f}% yes")
        else:
            print(f"  -- {slug}: not found or closed")

    # Build summary for quick dashboard display
    result["summary"] = build_summary(result)

    return result


def build_summary(data):
    """
    Build summary metrics for dashboard display.
    Groups data into "Guest Demand Signals" and "Operating Cost Drivers".
    """
    summary = {
        "guest_demand_signals": [],
        "operating_cost_drivers": []
    }

    # Guest Demand Signals: Recession, GDP, Fed policy

    # Recession probability (average Kalshi + Polymarket if both available)
    recession_probs = []

    # Check Kalshi recession
    if "recession" in data["kalshi"]:
        for series_data in data["kalshi"]["recession"]:
            for market in series_data.get("markets", []):
                if market.get("yes_probability"):
                    recession_probs.append({
                        "source": "kalshi",
                        "value": market["yes_probability"],
                        "title": market["title"],
                        "resolves": market.get("close_time")
                    })

    # Check Polymarket recession
    if "recession" in data["polymarket"]:
        for market in data["polymarket"]["recession"]:
            if market.get("yes_probability"):
                recession_probs.append({
                    "source": "polymarket",
                    "value": market["yes_probability"],
                    "title": market["title"],
                    "resolves": market.get("end_date")
                })

    if recession_probs:
        avg_prob = sum(p["value"] for p in recession_probs) / len(recession_probs)
        summary["guest_demand_signals"].append({
            "metric": "Recession Probability",
            "value": avg_prob,
            "format": "percent",
            "sources": recession_probs,
            "interpretation": "lower_better"
        })

    # Fed decision (next meeting only)
    if "fed_policy" in data["kalshi"]:
        for series_data in data["kalshi"]["fed_policy"]:
            if series_data["series"] == "KXFEDDECISION":
                markets = series_data.get("markets", [])
                if markets:
                    # Group markets by meeting date (extract from ticker like KXFEDDECISION-26JAN-H25)
                    meetings = {}
                    for m in markets:
                        ticker = m.get("ticker", "")
                        # Extract meeting ID (e.g., "26JAN" from "KXFEDDECISION-26JAN-H25")
                        parts = ticker.split("-")
                        if len(parts) >= 2:
                            meeting_id = parts[1]  # e.g., "26JAN", "26MAR"
                            if meeting_id not in meetings:
                                meetings[meeting_id] = []
                            meetings[meeting_id].append(m)

                    # Find the earliest meeting (sort by close_time)
                    earliest_meeting = None
                    earliest_close = None
                    for meeting_id, meeting_markets in meetings.items():
                        close_time = meeting_markets[0].get("close_time", "")
                        if earliest_close is None or close_time < earliest_close:
                            earliest_close = close_time
                            earliest_meeting = meeting_id

                    if earliest_meeting and earliest_meeting in meetings:
                        next_meeting_markets = meetings[earliest_meeting]

                        # Aggregate cut/hold/hike for just this meeting
                        # Ticker format: -C25 = cut 25bps, -C26 = cut >25bps, -H0 = hold (hike 0bps), -H25 = hike 25bps
                        fed_summary = {"cut": 0, "hold": 0, "hike": 0}
                        for m in next_meeting_markets:
                            ticker = m.get("ticker", "")
                            prob = m.get("yes_probability", 0)
                            outcome_code = ticker.split("-")[-1] if "-" in ticker else ""

                            if outcome_code.startswith("C"):
                                fed_summary["cut"] += prob
                            elif outcome_code == "H0":
                                fed_summary["hold"] += prob
                            elif outcome_code.startswith("H"):
                                fed_summary["hike"] += prob

                        # Determine most likely outcome
                        if sum(fed_summary.values()) > 0:
                            most_likely = max(fed_summary, key=fed_summary.get)
                            # Extract meeting month from meeting_id (e.g., "26JAN" -> "January 2026")
                            meeting_month = earliest_meeting
                            summary["guest_demand_signals"].append({
                                "metric": "Fed Rate Decision",
                                "meeting": meeting_month,
                                "value": fed_summary[most_likely],
                                "format": "percent",
                                "outcome": most_likely.title(),
                                "all_outcomes": fed_summary,
                                "interpretation": "cut_good" if most_likely == "cut" else "neutral",
                                "resolves": earliest_close
                            })
                break

    # Rate cuts count
    if "fed_policy" in data["kalshi"]:
        for series_data in data["kalshi"]["fed_policy"]:
            if series_data["series"] == "KXRATECUTCOUNT":
                markets = series_data.get("markets", [])
                if markets:
                    # Find expected number of cuts
                    cuts_dist = []
                    latest_close = None
                    for m in markets:
                        cuts_dist.append({
                            "title": m.get("title"),
                            "probability": m.get("yes_probability", 0)
                        })
                        # Track the latest close time (when this series resolves)
                        close_time = m.get("close_time")
                        if close_time and (latest_close is None or close_time > latest_close):
                            latest_close = close_time
                    if cuts_dist:
                        summary["guest_demand_signals"].append({
                            "metric": "Rate Cuts This Year",
                            "distribution": cuts_dist,
                            "format": "distribution",
                            "resolves": latest_close
                        })
                break

    # Operating Cost Drivers: Inflation, Energy

    # Annual inflation
    if "inflation" in data["kalshi"]:
        for series_data in data["kalshi"]["inflation"]:
            if series_data["series"] == "KXINFLY":
                markets = series_data.get("markets", [])
                if markets:
                    # Get inflation range expectations
                    inflation_dist = []
                    for m in markets:
                        inflation_dist.append({
                            "title": m.get("title"),
                            "probability": m.get("yes_probability", 0)
                        })
                    if inflation_dist:
                        summary["operating_cost_drivers"].append({
                            "metric": "Annual Inflation",
                            "distribution": inflation_dist,
                            "format": "distribution",
                            "interpretation": "lower_better"
                        })
                break

    # WTI Oil
    if "energy" in data["kalshi"]:
        for series_data in data["kalshi"]["energy"]:
            if series_data["series"] == "KXWTIW":
                markets = series_data.get("markets", [])
                if markets:
                    oil_dist = []
                    earliest_close = None
                    for m in markets:
                        oil_dist.append({
                            "title": m.get("title"),
                            "probability": m.get("yes_probability", 0)
                        })
                        # WTI weekly resolves at end of week - get earliest close
                        close_time = m.get("close_time")
                        if close_time and (earliest_close is None or close_time < earliest_close):
                            earliest_close = close_time
                    if oil_dist:
                        summary["operating_cost_drivers"].append({
                            "metric": "WTI Oil Price",
                            "distribution": oil_dist,
                            "format": "distribution",
                            "interpretation": "lower_better",
                            "resolves": earliest_close
                        })
                break

    # Gas price outlook - show current gas price expectation
    if "energy" in data["kalshi"]:
        for series_data in data["kalshi"]["energy"]:
            if series_data["series"] == "KXAAAGASW":
                markets = series_data.get("markets", [])
                if markets:
                    # Gas markets are "above $X" format
                    # Find the price level with ~50% probability (market consensus)
                    gas_levels = []
                    earliest_close = None
                    for m in markets:
                        title = m.get("title", "")
                        # Extract price like "$2.830" from title
                        import re
                        price_match = re.search(r'\$(\d+\.\d+)', title)
                        if price_match:
                            gas_levels.append({
                                "price": float(price_match.group(1)),
                                "probability": m.get("yes_probability", 0),
                                "title": title
                            })
                        # Track earliest close time
                        close_time = m.get("close_time")
                        if close_time and (earliest_close is None or close_time < earliest_close):
                            earliest_close = close_time

                    if gas_levels:
                        # Sort by price
                        gas_levels.sort(key=lambda x: x["price"])
                        # Find price with probability closest to 50% (consensus point)
                        closest = min(gas_levels, key=lambda x: abs(x["probability"] - 0.5))
                        summary["operating_cost_drivers"].append({
                            "metric": "Gas Price Outlook",
                            "value": closest["price"],
                            "probability": closest["probability"],
                            "format": "price",
                            "levels": gas_levels,
                            "interpretation": "lower_better",
                            "resolves": earliest_close
                        })
                break

    return summary


def main():
    """Main entry point."""
    print("=" * 60)
    print("Prediction Markets Data Fetcher")
    print("=" * 60)
    print()

    # Collect all market data
    data = collect_all_markets()

    # Save to JSON file
    output_path = Path("static/data/prediction-markets.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print()
    print(f"Saved to {output_path}")
    print(f"Fetched at: {data['fetched_at']}")

    # Print summary
    print()
    print("Summary:")
    summary = data.get("summary", {})

    print("  Guest Demand Signals:")
    for item in summary.get("guest_demand_signals", []):
        if item.get("format") == "percent":
            print(f"    - {item['metric']}: {item['value']*100:.1f}%")
        elif item.get("format") == "distribution":
            print(f"    - {item['metric']}: {len(item.get('distribution', []))} outcomes")

    print("  Operating Cost Drivers:")
    for item in summary.get("operating_cost_drivers", []):
        if item.get("format") == "percent":
            print(f"    - {item['metric']}: {item['value']*100:.1f}%")
        elif item.get("format") == "distribution":
            print(f"    - {item['metric']}: {len(item.get('distribution', []))} outcomes")

    print()
    print("Done!")


if __name__ == "__main__":
    main()
