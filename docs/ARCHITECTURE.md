# NixVir.com Architecture

## Overview

NixVir.com is a static site built with Hugo, deployed on Netlify, with automated data pipelines running via GitHub Actions.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA SOURCES                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Snow Cover           Economic Data         News Feeds         Weather       │
│  ┌─────────────┐     ┌─────────────┐      ┌───────────┐     ┌───────────┐   │
│  │   NOHRSC    │     │    FRED     │      │  RSS/XML  │     │ Open-Meteo│   │
│  │  (USA)      │     │   API       │      │  Various  │     │   API     │   │
│  ├─────────────┤     ├─────────────┤      │  Sources  │     └───────────┘   │
│  │  NOAA IMS   │     │  SF Fed     │      └───────────┘                     │
│  │  (Canada)   │     │  Sentiment  │                                         │
│  └─────────────┘     └─────────────┘                                         │
│                                                                              │
└──────────────┬───────────────┬──────────────────┬───────────────────────────┘
               │               │                  │
               ▼               ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GITHUB ACTIONS                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐           │
│  │ update-snow-     │  │ update-          │  │ update-          │           │
│  │ cover.yml        │  │ dashboard.yml    │  │ ski-news.yml     │           │
│  │ 6AM & 6PM EST    │  │ 9AM EST (M-F)    │  │ 6AM EST daily    │           │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘           │
│           │                     │                     │                      │
│           ▼                     ▼                     ▼                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐           │
│  │ update_snow_     │  │ update_          │  │ update_          │           │
│  │ cover.py         │  │ dashboard.py     │  │ ski_news.py      │           │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘           │
│           │                     │                     │                      │
└───────────┼─────────────────────┼─────────────────────┼──────────────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STATIC DATA (static/data/)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐           │
│  │ snow-cover.json  │  │ dashboard.json   │  │ ski-news.json    │           │
│  │ snow-cover-      │  │                  │  │ ski-news-        │           │
│  │ historical.json  │  │                  │  │ review.json      │           │
│  │ temperature-     │  │                  │  │                  │           │
│  │ history.json     │  │                  │  │                  │           │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘           │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐           │
│  │ snotel-          │  │ bc-snow-         │  │ alberta-snow-    │           │
│  │ snowpack.json    │  │ stations.json    │  │ pillows.json     │           │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘           │
│                                                                              │
│  ┌──────────────────┐                                                       │
│  │ quebec-snow-     │                                                       │
│  │ stations.json    │                                                       │
│  └──────────────────┘                                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ git push
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HUGO BUILD                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         Content Sources                              │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │    │
│  │  │ content/   │  │ layouts/   │  │ static/    │  │ themes/    │    │    │
│  │  │  _index.md │  │  index.html│  │  *.html    │  │  ananke/   │    │    │
│  │  │  post/     │  │  partials/ │  │  css/      │  │            │    │    │
│  │  │  about/    │  │            │  │  js/       │  │            │    │    │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│                           ┌────────────────┐                                 │
│                           │   public/      │                                 │
│                           │   (410 MB)     │                                 │
│                           └────────────────┘                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ auto-deploy
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               NETLIFY CDN                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        www.nixvir.com                                │    │
│  │                                                                       │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │    │
│  │  │   /         │  │/snow-cover  │  │ /dashboard  │  │  /snotel    │ │    │
│  │  │  Homepage   │  │   .html     │  │   .html     │  │   .html     │ │    │
│  │  │ (Hugo)      │  │  (Static)   │  │  (Static)   │  │  (Static)   │ │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │    │
│  │                                                                       │    │
│  │  Security Headers: CSP, HSTS, X-Frame-Options, etc.                  │    │
│  │  Cache Headers: JSON (1hr), CSS/JS/Images (1yr immutable)            │    │
│  │                                                                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## File Structure

```
nixvirweb/
├── .github/workflows/          # GitHub Actions automation
│   ├── update-snow-cover.yml   # Snow cover data (2x daily)
│   ├── update-dashboard.yml    # Economic data (weekdays)
│   ├── update-ski-news.yml     # News aggregation (daily)
│   ├── update-snotel.yml       # US SNOTEL snowpack (daily)
│   ├── update-bc-snow.yml      # BC snow stations (daily)
│   ├── update-alberta-snow.yml # Alberta snow pillows (2x daily)
│   ├── update-quebec-snow.yml  # Quebec snow stations (daily)
│   └── update-airport-data.yml # Airport passenger data
│
├── content/                    # Hugo content (Markdown)
│   ├── _index.md              # Homepage intro
│   ├── post/                  # Data Insights articles
│   ├── manual-news/           # CMS-managed manual news stories
│   │   ├── _index.md         # Section config (enables JSON output)
│   │   └── *.md              # Individual stories → /manual-news/index.json
│   ├── about/                 # About page
│   └── *.md                   # Other pages
│
├── layouts/                   # Hugo templates
│   ├── _default/
│   │   └── baseof.html       # Base template (skip link, main)
│   ├── index.html            # Homepage (4-column layout)
│   ├── partials/
│   │   ├── head-additions.html  # Fonts, focus styles
│   │   ├── site-navigation.html # Header nav
│   │   └── schema.html          # JSON-LD structured data
│   ├── manual-news/
│   │   └── list.json         # Template: generates /manual-news/index.json
│   └── page/
│       ├── dashboard.html    # Hugo-rendered dashboard
│       └── ski-news.html     # Hugo-rendered news page
│
├── static/                   # Static assets
│   ├── css/
│   │   └── shared-theme.css  # Shared CSS variables & components
│   ├── js/
│   │   └── analytics.js      # Google Analytics (DNT-aware)
│   ├── data/                 # JSON data files
│   │   ├── snow-cover.json
│   │   ├── dashboard.json
│   │   ├── ski-news.json
│   │   └── ...
│   ├── images/               # Site images
│   ├── admin/                # Sveltia CMS
│   │   ├── index.html        # CMS entry point
│   │   └── config.yml        # CMS collections & fields
│   ├── snow-cover.html       # Interactive snow dashboard (4637 lines)
│   ├── snotel.html           # SNOTEL snowpack map (1548 lines)
│   └── dashboard.html        # Economic dashboard (2353 lines)
│
├── themes/gohugo-theme-ananke/  # Hugo theme
│
├── update_snow_cover.py      # Snow data fetcher
├── update_dashboard.py       # Economic data fetcher
├── update_ski_news.py        # News aggregator
├── fetch_snotel_data.py      # US SNOTEL snowpack fetcher
├── fetch_bc_snow_data.py     # BC snow station fetcher
├── fetch_alberta_snow_pillows.py  # Alberta snow pillow fetcher
├── fetch_quebec_snow_stations.py  # Quebec snow station fetcher
├── netlify.toml              # Netlify config & headers
├── config.toml               # Hugo config
├── CLAUDE.md                 # AI assistant instructions
└── MAINTENANCE.md            # Operations guide
```

## Data Flow

### Snow Cover Pipeline

```
NOHRSC/IMS APIs
      │
      ▼
update_snow_cover.py
      │
      ├──► snow-cover.json (current conditions)
      ├──► snow-globe.png (visualization)
      └──► snow-globe.json (metadata)
      │
      ▼
git commit & push
      │
      ▼
Netlify auto-deploy
      │
      ▼
snow-cover.html fetches /data/snow-cover.json
```

### Dashboard Pipeline

```
FRED API + SF Fed Excel
      │
      ▼
update_dashboard.py
      │
      └──► dashboard.json
      │
      ▼
git commit & push
      │
      ▼
Netlify auto-deploy
      │
      ▼
dashboard.html fetches /data/dashboard.json
```

## Page Types

### Hugo-Rendered Pages
- Homepage (`/`) - layouts/index.html (loads automated + manual news feeds)
- Data Insights (`/post/`) - content/post/*.md
- About (`/about/`) - content/about/_index.md
- CMS Admin (`/admin/`) - Sveltia CMS for blog posts and manual news stories

### Static HTML Pages
These are standalone HTML files that fetch JSON data client-side:

| Page | File | Lines | Purpose |
|------|------|-------|---------|
| Snow Cover | static/snow-cover.html | 4,637 | Interactive map, charts, market table |
| SNOTEL | static/snotel.html | 1,548 | Snowpack map with Leaflet |
| Dashboard | static/dashboard.html | 2,353 | Economic indicators |

## Key Technologies

| Component | Technology |
|-----------|------------|
| Static Site Generator | Hugo 0.139+ |
| Hosting/CDN | Netlify |
| CI/CD | GitHub Actions |
| Charts | Chart.js 4.x |
| Maps | D3.js + TopoJSON (snow-cover), Leaflet (snotel) |
| Fonts | DM Sans, JetBrains Mono (Google Fonts) |
| Analytics | Google Analytics 4 (with DNT support) |

## Shared Resources

### CSS (`/css/shared-theme.css`)
- CSS custom properties (design tokens)
- Reset styles
- Site banner & navigation
- Popup styles for map tooltips
- Accessibility: focus indicators, `.sr-only` utility class

### JavaScript (`/js/analytics.js`)
- Google Analytics with Do Not Track support
- Used by all static HTML pages

## Security

- **HTTPS**: Let's Encrypt wildcard certificate
- **Headers**: HSTS, CSP, X-Frame-Options, X-Content-Type-Options
- **CSP**: Whitelisted CDNs only, no inline scripts (except GA requirement)
- **Form**: Formspree with honeypot spam protection

See `SECURITY_AUDIT_REPORT.md` for full details.

## Accessibility (WCAG 2.1 AA)

- **Color Contrast**: All text meets 4.5:1 minimum ratio (verified Feb 2026)
- **Focus Indicators**: Visible `:focus-visible` outlines on all interactive elements
- **Heading Hierarchy**: Sequential H1 → H2 → H3 structure
- **Skip Links**: Hugo templates include skip navigation
- **Screen Reader**: `.sr-only` class for visually hidden content

See `docs/CSS_VARIABLES.md` for accessibility-compliant color values.
