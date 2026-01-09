# Ski Resort Currency Dashboard Framework

## Overview

Segmented currency monitoring for North American ski resort operators, with specific views optimized for:
1. **US resort operators** (Aspen, etc.) — attracting international visitors
2. **Canadian resort operators** (Whistler, etc.) — attracting US/international visitors + retaining domestic skiers
3. **Luxury segment tracking** — deviation-based metrics for ultra-high-net-worth feeder markets

---

## Dashboard Structure

### View 1: Volume Markets (US Resort Perspective)

**Core question:** "How attractive is skiing in the US for international visitors?"

| Currency | Display Metric | Thresholds | Signal |
|----------|---------------|------------|--------|
| CAD | USD per 100 CAD | >$80: favorable | Canadian cross-border trips |
| MXN | USD per 100 MXN | >$5.50: favorable | Mexican destination travel |
| EUR | USD per 100 EUR | >$110: favorable | European long-haul |
| GBP | USD per 100 GBP | >$130: favorable | UK long-haul |
| BRL | USD per 100 BRL | >$22: favorable | South American (Aspen focus) |

**Key reframe:** Flip from "foreign per USD" to "USD purchasing power of visitor currency" — higher = better for you.

---

### View 2: Volume Markets (Canadian Resort Perspective)

**Core question:** "How attractive is skiing in Canada vs alternatives?"

| Metric | Display | Thresholds | Signal |
|--------|---------|------------|--------|
| CAD per 100 USD | e.g., "C$137" | >C$140: very attractive | US visitor value perception |
| CAD vs EUR | Indexed | CAD weaker = favorable | Competitive vs Alps |
| CAD vs JPY | Indexed | CAD weaker = favorable | Competitive vs Niseko |
| CAD vs AUD | Direct cross | - | Australian visitor flow |

---

### View 3: Domestic Retention (Canadian Operators)

**Core question:** "Will Canadians ski at home or drive to the US?"

| USD/CAD Level | Retention Signal | Action |
|---------------|-----------------|--------|
| ≥1.40 | Strong retention | Emphasize value messaging |
| 1.25–1.40 | Neutral | Standard marketing |
| ≤1.25 | Weak retention (leakage risk) | Compete on experience, not price |

---

### View 4: Luxury Feeder Markets

**Core question:** "Is the USD cheap or expensive vs what advisors/clients expect?"

| Currency | Primary Destination | Key Metric |
|----------|--------------------| -----------|
| HKD | Whistler + Aspen | % vs 3-year avg |
| SGD | Whistler + Aspen | % vs 3-year avg |
| AED | Aspen | % vs 3-year avg |
| BRL | Aspen | % vs 3-year avg |
| RUB | Both (ultra-luxury) | % vs 3-year avg |
| INR | Both (emerging) | % vs 3-year avg |
| CNY | Whistler | % vs 3-year avg |
| JPY | Whistler | % vs 3-year avg |

**Threshold logic:**
- **≤-10% vs 3yr avg:** "USD is cheap" → favorable, worth noting to clients
- **≥+10% vs 3yr avg:** "USD is expensive" → headwind
- **Within ±10%:** Normal range, not a conversation driver

---

### View 5: Competitive Destination Comparison

**For Whistler specifically:** How does CAD stack up against competing luxury ski destinations?

| Destination | Currency | "What $100 USD buys" |
|-------------|----------|---------------------|
| Whistler | CAD | C$137 |
| Chamonix/St. Anton | EUR | €85 |
| Zermatt/Verbier | CHF | CHF 88 |
| Niseko | JPY | ¥15,672 |

*Display as indexed "relative value" score normalized to a baseline period.*

---

## Visual Design Recommendations

### Color Coding
- **Green (#2E7D32):** Favorable for your resort
- **Gray (#757575):** Neutral / within normal range
- **Red (#C62828):** Unfavorable / headwind

### Trend Indicators
- **90-day directional arrow:** More actionable than YoY for booking windows
- **Volatility flag:** High volatility = harder to market on price

### Layout
```
┌─────────────────────────────────────────────────────────────────┐
│  VOLUME MARKETS                                                 │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │   CAD   │ │   MXN   │ │   EUR   │ │   GBP   │ │   AUD   │   │
│  │  $72.81 │ │  $5.59  │ │ $117.38 │ │ $134.81 │ │  $66.84 │   │
│  │ per 100 │ │ per 100 │ │ per 100 │ │ per 100 │ │ per 100 │   │
│  │   ↑ 4%  │ │  ↑ 12%  │ │  ↑ 11%  │ │  ↑ 7%   │ │  ↑ 7%   │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  LUXURY FEEDER MARKETS (% vs 3-year average)                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │   HKD   │ │   SGD   │ │   AED   │ │   BRL   │ │   CNY   │   │
│  │  -2.1%  │ │  -4.8%  │ │   0.0%  │ │ +12.3%  │ │  -6.2%  │   │
│  │ neutral │ │ neutral │ │ neutral │ │  ↑ warn │ │ neutral │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  CANADIAN DOMESTIC RETENTION          │  COMPETITIVE POSITION  │
│  USD/CAD: 1.3738                       │  vs Alps: CAD -8%      │
│  Status: NEUTRAL                       │  vs Niseko: CAD +3%    │
│  C$100 USD trip costs: $137.38 CAD     │  vs Swiss: CAD -12%    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Sources

### Real-time / Daily
- **Fed H.10 release:** Trade-weighted indices, major currencies
- **Bank of Canada:** Official CAD crosses
- **OANDA / XE API:** Full currency coverage

### Historical (for deviation calcs)
- Minimum 3 years daily data for luxury segment deviation metrics
- 5 years preferred for baseline "normal range" calculations

---

## Implementation Notes

1. **Caching:** Luxury deviation calcs are compute-heavy; pre-calculate daily
2. **Alerting:** Consider threshold-breach notifications for key currencies
3. **Client-specific views:** Whistler and Aspen have different feeder market weightings — consider parameterized dashboard
4. **Seasonality:** Weight recent winter seasons more heavily for "typical" range calculations
