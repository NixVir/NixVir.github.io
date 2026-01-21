# Ski Business News Scraping System - Technical Documentation

This document provides comprehensive technical documentation for the automated ski business news aggregation system used on the NixVir website's Ski Business News section.

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Data Flow](#data-flow)
4. [RSS Sources](#rss-sources)
5. [Article Filtering](#article-filtering)
6. [Keyword-Based Scoring](#keyword-based-scoring)
7. [Category Assignment](#category-assignment)
8. [LLM Scoring (Optional)](#llm-scoring-optional)
9. [Output Files](#output-files)
10. [GitHub Actions Automation](#github-actions-automation)
11. [Frontend Display](#frontend-display)
12. [Source Code Reference](#source-code-reference)

---

## System Overview

The ski news scraping system is an automated pipeline that:

1. **Fetches** articles from 30+ curated RSS feeds covering ski industry news
2. **Filters** articles using keyword-based relevance checks
3. **Scores** articles to determine quality and relevance (1-10 scale)
4. **Categorizes** articles into 10 predefined categories
5. **Stores** approved articles in JSON format for frontend consumption
6. **Runs automatically** once daily via GitHub Actions

**Primary Script**: `update_ski_news.py` (1,175 lines)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GitHub Actions                                │
│                   (Scheduled: Daily 6 AM EST)                        │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     update_ski_news.py                               │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                │
│  │ Fetch RSS   │ → │ Pre-Filter  │ → │ Score       │                │
│  │ Feeds       │   │ (Keywords)  │   │ Articles    │                │
│  └─────────────┘   └─────────────┘   └─────────────┘                │
│         │                                   │                        │
│         ▼                                   ▼                        │
│  ┌─────────────┐                    ┌─────────────┐                 │
│  │ Parse RSS/  │                    │ Categorize  │                 │
│  │ Atom XML    │                    │ Articles    │                 │
│  └─────────────┘                    └─────────────┘                 │
│                                            │                        │
│                                            ▼                        │
│                                    ┌─────────────┐                  │
│                                    │ Save JSON   │                  │
│                                    │ Output      │                  │
│                                    └─────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Output Files                                     │
│  ┌──────────────────────────┐  ┌───────────────────────────────┐    │
│  │ static/data/ski-news.json│  │static/data/ski-news-review.json│   │
│  │ (Approved Articles)      │  │ (Pending + Rejected)          │    │
│  └──────────────────────────┘  └───────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Frontend Display                                 │
│               layouts/page/ski-news.html                             │
│  (JavaScript fetches ski-news.json and renders cards)                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. RSS Feed Fetching

The system iterates through all configured RSS sources and fetches their XML content:

```python
def fetch_url(url, timeout=30):
    """Fetch content from URL"""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode('utf-8', errors='replace')
    except Exception as e:
        print_safe(f"  ! Error fetching {url}: {e}")
        return None
```

### 2. RSS Parsing

Both RSS 2.0 and Atom feed formats are supported:

```python
def parse_rss_feed(xml_content, source_name):
    """Parse RSS feed and extract articles"""
    articles = []
    root = ET.fromstring(xml_content)

    # Handle both RSS and Atom feeds
    namespaces = {
        'atom': 'http://www.w3.org/2005/Atom',
        'content': 'http://purl.org/rss/1.0/modules/content/'
    }

    # Try RSS format first
    items = root.findall('.//item')

    # Try Atom format if no RSS items found
    if not items:
        items = root.findall('.//atom:entry', namespaces)
```

### 3. Article Structure

Each parsed article contains:

```python
article = {
    'id': 'md5_hash_12chars',      # Unique ID from URL hash
    'source': 'Source Name',        # RSS source name
    'title': 'Article Title',       # Cleaned title
    'url': 'https://...',           # Original article URL
    'description': 'First 500...',  # Truncated description
    'content': 'First 1000...',     # Truncated content
    'pub_date': 'RFC 2822 date',    # Publication date
    'score': 8,                     # Relevance score (1-10)
    'score_details': {},            # Scoring breakdown
    'approved_date': '2026-01-15',  # When approved
    'category': 'business-investment',        # Primary category
    'secondary_categories': ['canada', ...]   # Secondary categories
}
```

---

## RSS Sources

The system pulls from **30+ RSS feeds** organized by category:

### Major Publications (Boost: +3)
| Source | URL | Notes |
|--------|-----|-------|
| New York Times - Travel | `rss.nytimes.com/.../Travel.xml` | Premium journalism |
| Reuters Business | `reutersagency.com/feed/...` | Wire service |
| Washington Post | `feeds.washingtonpost.com/rss/business` | |
| The Atlantic | `theatlantic.com/feed/all/` | |
| Financial Times | `ft.com/rss/home` | |
| Bloomberg Markets | `feeds.bloomberg.com/markets/news.rss` | Financial journalism |
| Christian Science Monitor | `rss.csmonitor.com/feeds/all` | Quality journalism |

### Canadian Publications (Boost: +2-3)
| Source | URL | Notes |
|--------|-----|-------|
| Globe and Mail - Business | `theglobeandmail.com/.../business/` | Canada's national paper |
| CBC News - Business | `cbc.ca/webfeed/rss/rss-business` | Public broadcaster |

### Google News Aggregators (Boost: +1-2)
| Source | Query | Notes |
|--------|-------|-------|
| Ski Industry | `ski+resort+business+OR+ski+industry` | Broad coverage |
| Canada Ski | `canada+ski+resort+OR+whistler+OR+banff` | Canadian focus |
| Vail/Alterra | `Vail+Resorts+OR+Alterra+Mountain+ski` | Major companies |
| Ski Business | `"ski+resort"+business+OR+investment` | Business focus |
| Ski Pass Prices | `ski+pass+price+OR+Epic+Pass+OR+Ikon` | Pricing news |
| 2026 Winter Olympics | `2026+Winter+Olympics+Milan+Cortina+skiing` | Olympics coverage |

### Industry Publications (Boost: +2)
| Source | URL | Notes |
|--------|-----|-------|
| Outside Business Journal | `outsidebusinessjournal.com/feed/` | Business journalism |
| Snowsports Industries America | `snowsports.org/feed/` | Industry association |
| Snow Industry News | `snowindustrynews.com/rss` | Trade publication |
| Ski Area Management | `saminfo.com/.../rss` | Since 1962 |

### Ski News Sites (Boost: +2)
| Source | URL | Notes |
|--------|-----|-------|
| Unofficial Networks | `unofficialnetworks.com/feed/` | Ski-dedicated |
| SnowBrains | `snowbrains.com/feed/` | Ski-dedicated |

### International (Boost: +1)
| Source | URL | Notes |
|--------|-----|-------|
| PlanetSKI | `planetski.eu/feed/` | European coverage |
| The Ski Guru | `the-ski-guru.com/feed/` | European Alps |

### Mountain Community Papers (Boost: +1)
| Source | Coverage Area |
|--------|---------------|
| Summit Daily News | Breckenridge/Summit County |
| Vail Daily | Vail Valley |
| Aspen Times | Aspen/Roaring Fork |
| Park Record | Park City |
| Jackson Hole News & Guide | Jackson Hole |
| Tahoe Daily Tribune | Lake Tahoe |

### Government Statistics (Boost: +3)
| Source | URL | Notes |
|--------|-----|-------|
| U.S. Census Bureau | `census.gov/.../indicator.xml` | Economic indicators |
| Statistics Canada | `statcan.gc.ca/.../homepage-eng.xml` | Travel & tourism |

---

## Article Filtering

### Pre-Filter (Basic Relevance)

Articles must contain at least one keyword from `BUSINESS_KEYWORDS` to proceed:

```python
BUSINESS_KEYWORDS = [
    # Core ski terms
    'ski', 'skiing', 'skier', 'snowboard', 'snowboarding', 'powder', 'slopes',

    # Resort/destination business
    'resort', 'ski area', 'mountain', 'lift', 'investment', 'acquisition',
    'merger', 'expansion', 'revenue', 'profit', 'loss', 'earnings', ...

    # Weather and climate
    'snowfall', 'snow forecast', 'winter forecast', 'la nina', 'el nino',
    'climate change', 'global warming', 'snow drought', 'snowpack', ...

    # Canadian ski areas
    'whistler', 'blackcomb', 'banff', 'lake louise', 'revelstoke', ...

    # International markets
    'europe', 'european', 'alps', 'japan', 'international', ...

    # Lodging and hospitality
    'hotel', 'lodge', 'lodging', 'inn', 'resort hotel', 'slopeside', ...

    # Air travel
    'airport', 'airline', 'flight', 'air service', 'nonstop', ...
]
```

```python
def basic_relevance_filter(article):
    """Quick keyword-based pre-filter before scoring"""
    text = f"{article.get('title', '')} {article.get('description', '')}".lower()

    for keyword in BUSINESS_KEYWORDS:
        if keyword.lower() in text:
            return True
    return False
```

---

## Keyword-Based Scoring

The primary scoring system uses comprehensive keyword analysis:

### Score Thresholds

```python
AUTO_APPROVE_THRESHOLD = 6   # Score >= 6: Auto-approved
AUTO_REJECT_THRESHOLD = 3    # Score <= 3: Auto-rejected
# Scores 4-5: Queued for manual review
```

### Core Ski Relevance Check

Articles **must** contain at least one core ski keyword to be considered:

```python
core_ski_keywords = [
    'ski', 'skiing', 'skier', 'slope', 'slopes', 'chairlift', 'gondola', 'lift',
    'snowboard', 'snowboarding', 'powder', 'alpine', 'downhill', 'terrain park',
    # Major resorts
    'whistler', 'blackcomb', 'vail', 'aspen', 'park city', 'deer valley', ...
    # Industry terms
    'skier visit', 'ski industry', 'resort operator', 'lift ticket', 'season pass'
]

if not any(kw in text for kw in core_ski_keywords):
    return 2, {"reason": "No ski industry relevance detected"}
```

### Score Boosters

| Category | Keywords | Title Match | Body Match |
|----------|----------|-------------|------------|
| Resort Business | acquisition, merger, investment, earnings, expansion... | +3 | +2 |
| Weather/Climate | snowfall, snow forecast, la nina, el nino, climate change... | +3 | +2 |
| International Markets | europe, alps, japan, australia, worldwide... | +2 | +2 |
| Canadian Ski | canada, whistler, banff, british columbia, quebec... | +3 | +2 |
| Opening/Closing | opening day, first chair, closing day, season opening... | +3 | +2 |
| Real Estate | real estate, housing development, condo, zoning... | +3 | +2 |
| Lodging | hotel occupancy, room rate, airbnb, ski-in ski-out... | +3 | +2 |
| Air Travel | airport, airline, air service, nonstop flight... | +3 | +2 |
| Currency/Tourism | exchange rate, international visitor, tourism statistics... | +3 | +2 |

### Score Penalties

| Category | Keywords | Penalty |
|----------|----------|---------|
| Promotional | buy now, save up to, discount, deal, sale ends, promo code... | -5 |
| Fluff/Listicles | best runs, trip report, gear review, top 10, bucket list... | -4 |
| Product Focus | gear guide, product review, best skis, buying guide... | -3 |
| Off-Topic | tick, mosquito, bug spray, lyme disease... | -3 to -5 |
| Feel-Good Fluff | heartwarming, viral video, adorable, wholesome... | -3 |

### Source Quality Boost

Each RSS source has a boost value (0-3) that's added to the final score:

```python
score += source_boost  # From RSS_SOURCES configuration
```

### Final Score Calculation

```python
def basic_keyword_score(article):
    text = f"{article.get('title', '')} {article.get('description', '')} {article.get('content', '')}".lower()
    title = article.get('title', '').lower()

    # Check core ski relevance first
    if not any(kw in text for kw in core_ski_keywords):
        return 2, {"reason": "No ski industry relevance detected"}

    score = 5  # Base score

    # Apply boosters and penalties...
    # ... (detailed logic above)

    # Add source boost
    for src in RSS_SOURCES:
        if src['name'] == article.get('source'):
            score += src.get('boost', 0)
            break

    return max(1, min(10, score)), {"reason": f"Keyword scoring (boost: {source_boost})"}
```

---

## Category Assignment

Articles are assigned one primary category and up to 3 secondary categories:

### Available Categories

```python
ARTICLE_CATEGORIES = {
    'resort-operations': {
        'name': 'Resort Operations',
        'keywords': ['lift', 'chairlift', 'gondola', 'snowmaking', 'terrain expansion',
                     'new trail', 'mountain operations', 'ski patrol', 'grooming',
                     'base lodge', 'summit lodge', 'ticket', 'pass', 'opening day', ...]
    },
    'business-investment': {
        'name': 'Business & Investment',
        'keywords': ['acquisition', 'merger', 'investment', 'earnings', 'revenue',
                     'profit', 'loss', 'ipo', 'bankruptcy', 'layoff', 'ceo', ...]
    },
    'weather-snow': {
        'name': 'Weather & Snow',
        'keywords': ['snowfall', 'snow forecast', 'winter forecast', 'la nina',
                     'climate change', 'snowpack', 'blizzard', 'cold front', ...]
    },
    'transportation': {
        'name': 'Transportation',
        'keywords': ['airport', 'airline', 'flight', 'air service', 'highway',
                     'traffic', 'shuttle', 'bus service', 'parking', 'train', ...]
    },
    'winter-sports': {
        'name': 'Winter Sports',
        'keywords': ['world cup ski', 'winter olympics', 'fis alpine', 'ski race',
                     'slalom', 'downhill race', 'x games ski', 'freestyle skiing', ...]
    },
    'safety-incidents': {
        'name': 'Safety',
        'keywords': ['accident', 'injury', 'death', 'fatality', 'avalanche',
                     'rescue', 'collision', 'lawsuit', 'emergency', 'hazard', ...]
    },
    'canada': {
        'name': 'Canada',
        'keywords': ['canada', 'canadian', 'whistler', 'blackcomb', 'banff',
                     'lake louise', 'revelstoke', 'british columbia', 'quebec', ...]
    },
    'international': {
        'name': 'International',
        'keywords': ['europe', 'european', 'alps', 'japan', 'australia',
                     'chamonix', 'zermatt', 'niseko', 'worldwide', 'global market', ...]
    },
    'ski-history': {
        'name': 'Ski History',
        'keywords': ['abandoned ski', 'historic ski', 'ski history', 'anniversary',
                     'ski pioneer', 'vintage ski', 'ski museum', 'ski heritage', ...]
    },
    'hospitality': {
        'name': 'Hospitality',
        'keywords': ['hotel', 'lodging', 'accommodation', 'resort hotel',
                     'ski-in ski-out', 'vacation rental', 'airbnb', 'occupancy', ...]
    }
}
```

### Category Assignment Logic

```python
def assign_categories(article):
    """Assign primary and secondary categories based on keyword matching."""
    text = f"{article.get('title', '')} {article.get('description', '')} {article.get('content', '')}".lower()
    title = article.get('title', '').lower()

    category_scores = {}

    for cat_id, cat_info in ARTICLE_CATEGORIES.items():
        score = 0
        for keyword in cat_info['keywords']:
            # Title matches count 3x more
            if keyword.lower() in title:
                score += 3
            elif keyword.lower() in text:
                score += 1
        category_scores[cat_id] = score

    # Sort categories by score
    sorted_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)

    # Primary = highest score (default: 'resort-operations')
    primary = sorted_cats[0][0] if sorted_cats[0][1] > 0 else 'resort-operations'

    # Secondary = next highest scoring categories (max 3, score > 0)
    secondary = [cat_id for cat_id, score in sorted_cats[1:4] if score > 0]

    return primary, secondary
```

---

## LLM Scoring (Optional)

The system includes optional LLM-based scoring using Claude or OpenAI APIs. This is currently **disabled** to avoid API costs, but the code is preserved:

### Claude API Scoring

```python
def score_with_claude(article):
    """Score article using Claude API"""
    if not ANTHROPIC_API_KEY:
        return None, "No API key"

    prompt = f"""Score this ski industry news article on a scale of 1-10...

    STRICTLY EXCLUDE (score 1-2):
    - Promotional content: ticket deals, pass sales, resort marketing...
    - Product advertisements, gear reviews, or buying guides...

    INCLUDE AND PRIORITIZE (score 8-10):
    - Major ski resort business news: acquisitions, mergers, investments...
    - Real estate development in ski communities...
    - Canadian ski industry news...

    Respond with ONLY a JSON object:
    {{"relevance": X, "news_value": X, "quality": X, "overall": X, "reason": "..."}}
    """

    # API call to claude-haiku-4-5-20251001
    data = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}]
    })
```

When LLM scoring was enabled, thresholds were higher:
- `AUTO_APPROVE_THRESHOLD = 8`
- `AUTO_REJECT_THRESHOLD = 4`

---

## Output Files

### `static/data/ski-news.json`

The primary output file containing approved articles:

```json
{
  "updated": "2026-01-15 11:13:41",
  "total_articles": 50,
  "articles": [
    {
      "source": "Ski Area Management",
      "title": "Report Details Economic Impact of Idaho Ski Areas",
      "url": "https://www.saminfo.com/news/...",
      "description": "Idaho ski areas recorded 2.4 million skier visits...",
      "content": "Idaho ski areas recorded 2.4 million skier visits...",
      "pub_date": "Wed, 17 Dec 2025 14:25:08 -0500",
      "id": "ac67e2740e2b",
      "score": 8,
      "score_details": {
        "reason": "Keyword scoring (boost: 2)"
      },
      "approved_date": "2026-01-09",
      "category": "business-investment",
      "secondary_categories": []
    },
    // ... up to 50 articles
  ]
}
```

### `static/data/ski-news-review.json`

Articles pending manual review or rejected:

```json
{
  "pending": [
    // Articles with scores 4-5
  ],
  "rejected": [
    // Articles with scores 1-3 (last 100 kept)
  ]
}
```

---

## GitHub Actions Automation

### Workflow File: `.github/workflows/update-ski-news.yml`

```yaml
name: Update Ski Business News

on:
  schedule:
    # Run once daily at 6 AM EST (11 AM UTC)
    - cron: '0 11 * * *'
  workflow_dispatch:  # Allow manual triggering

jobs:
  update-ski-news:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Update ski news data
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python update_ski_news.py

      - name: Commit and push if changed
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add static/data/ski-news.json static/data/ski-news-review.json

          if git diff --staged --quiet; then
            echo "No changes to ski news data"
          else
            git commit -m "Update ski news - $(date +'%Y-%m-%d %H:%M')"
            git push
          fi
```

### Schedule

- **Frequency**: Once daily
- **Time**: 6:00 AM EST (11:00 UTC)
- **Manual Trigger**: Available via GitHub Actions UI

---

## Frontend Display

### Layout File: `layouts/page/ski-news.html`

The frontend loads `ski-news.json` via JavaScript and renders article cards:

```javascript
async function loadSkiNews() {
  const response = await fetch('/data/ski-news.json');
  const data = await response.json();
  skiNewsData = data;

  // Update timestamp
  updateSpan.textContent = new Date(data.updated).toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
  });

  renderSkiNews();
}

function renderSkiNews() {
  // Filter by category
  let articles = skiNewsData.articles;
  if (filterBy !== 'all') {
    articles = articles.filter(a => a.category === filterBy);
  }

  // Sort by date (default) or category
  if (sortBy === 'category') {
    articles.sort((a, b) => a.category.localeCompare(b.category));
  } else {
    articles.sort((a, b) => new Date(b.pub_date) - new Date(a.pub_date));
  }

  // Render HTML cards
  articles.forEach(article => {
    html += `
      <div class="ski-news-card">
        <div class="ski-news-header">
          <img src="${catMeta.icon}" class="ski-news-icon" />
          <div class="ski-news-content">
            <h3><a href="${article.url}" target="_blank">${article.title}</a></h3>
            <div class="ski-news-meta">
              ${article.source} &bull; ${pubDate}
              <span class="ski-news-category cat-${category}">${catMeta.name}</span>
            </div>
            <div class="ski-news-desc">${desc}</div>
          </div>
        </div>
      </div>
    `;
  });
}
```

### Category Icons

Each category has an SVG icon at `/images/ski-news-icons/{category}.svg`:

```javascript
const CATEGORY_META = {
  'resort-operations': { name: 'Resort Operations', icon: '/images/ski-news-icons/resort-operations.svg' },
  'business-investment': { name: 'Business & Investment', icon: '/images/ski-news-icons/business-investment.svg' },
  'weather-snow': { name: 'Weather & Snow', icon: '/images/ski-news-icons/weather-snow.svg' },
  // ... etc
};
```

### Category Color Scheme

```css
.cat-resort-operations { background: #dbeafe; color: #2563eb; }
.cat-business-investment { background: #d1fae5; color: #059669; }
.cat-weather-snow { background: #e0f2fe; color: #0ea5e9; }
.cat-transportation { background: #ede9fe; color: #8b5cf6; }
.cat-winter-sports { background: #fee2e2; color: #ef4444; }
.cat-safety-incidents { background: #fecaca; color: #dc2626; }
.cat-canada { background: #fce7f3; color: #e11d48; }
.cat-international { background: #e0e7ff; color: #6366f1; }
.cat-ski-history { background: #f5f5f4; color: #78716c; }
.cat-hospitality { background: #ccfbf1; color: #14b8a6; }
```

---

## Source Code Reference

### Main Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `update_ski_news()` | Line 1033 | Main orchestration function |
| `fetch_url()` | Line 432 | HTTP request wrapper |
| `parse_rss_feed()` | Line 456 | RSS/Atom XML parser |
| `basic_relevance_filter()` | Line 528 | Keyword pre-filter |
| `basic_keyword_score()` | Line 760 | Primary scoring algorithm |
| `assign_categories()` | Line 537 | Category assignment |
| `score_with_claude()` | Line 579 | Claude API scoring (disabled) |
| `score_with_openai()` | Line 679 | OpenAI API scoring (disabled) |
| `load_existing_articles()` | Line 1003 | Load previous articles |
| `save_review_queue()` | Line 1026 | Save pending/rejected |

### Key Data Structures

| Variable | Line | Purpose |
|----------|------|---------|
| `RSS_SOURCES` | Line 115 | RSS feed configuration |
| `BUSINESS_KEYWORDS` | Line 366 | Pre-filter keywords |
| `ARTICLE_CATEGORIES` | Line 24 | Category definitions |
| `AUTO_APPROVE_THRESHOLD` | Line 111 | Score threshold (6) |
| `AUTO_REJECT_THRESHOLD` | Line 112 | Rejection threshold (3) |

### File Locations

| File | Purpose |
|------|---------|
| `update_ski_news.py` | Main scraping script |
| `.github/workflows/update-ski-news.yml` | GitHub Actions workflow |
| `static/data/ski-news.json` | Approved articles output |
| `static/data/ski-news-review.json` | Review queue |
| `layouts/page/ski-news.html` | Frontend template |
| `content/ski-news.md` | Hugo content page |

---

## Maintenance Notes

### Adding New RSS Sources

Add to `RSS_SOURCES` list in `update_ski_news.py`:

```python
{
    'name': 'New Source Name',
    'url': 'https://example.com/feed.xml',
    'category': 'news',  # or 'local', 'industry', 'major_publication', etc.
    'boost': 1  # Score boost (0-3)
}
```

### Adjusting Score Thresholds

Modify at the top of the script:

```python
AUTO_APPROVE_THRESHOLD = 6  # Lower = more articles approved
AUTO_REJECT_THRESHOLD = 3   # Higher = fewer rejections
```

### Adding New Categories

1. Add to `ARTICLE_CATEGORIES` dictionary
2. Add CSS class in `ski-news.html`
3. Add option to filter dropdown
4. Create SVG icon at `/images/ski-news-icons/{category}.svg`
5. Add to `CATEGORY_META` in frontend JavaScript

### Re-enabling LLM Scoring

1. Set `ANTHROPIC_API_KEY` environment variable
2. Set `ENABLE_LLM_SCORING=true` environment variable, OR set `enable_llm: true` in config file
3. Thresholds are configured in `config/ski-news-config.yaml`

---

## Recent Improvements (January 2026)

### Source Diversity Controls
- Added `MAX_ARTICLES_PER_SOURCE` cap (default: 5) to prevent any single source from dominating
- Configurable via `config/ski-news-config.yaml`

### Macro Relevance Pathway
- Secondary pre-filter pathway for adjacent stories affecting ski industry
- Requires BOTH a macro relevance term (climate change, airline, labor shortage, etc.) AND a mountain region geographic term
- Macro relevance articles get lower priority and slightly lower base score

### Improved Deduplication
- Increased similarity threshold from 70% to 85%
- Added lead paragraph comparison to catch same story with different headlines
- Configurable thresholds in config file

### ropeways.net HTML Scraper
- Added direct HTML scraping for ropeways.net media clipping page
- Captures ropeway/lift industry news not available via RSS

### Configuration File
- New YAML configuration file: `config/ski-news-config.yaml`
- Allows customization without code changes
- See `docs/SKI_NEWS_CONFIG.md` for full documentation

### Focus Topics
- Configurable topic boosts for trending/important subjects
- Title matches get additional +1 boost
- Useful for earnings seasons, events, breaking news

### Run Logging
- Detailed run statistics saved to `static/data/ski-news-run-log.json`
- Tracks article counts at each pipeline stage
- Records approved articles with scores
- Keeps history of last 30 runs (configurable)

---

*Last updated: January 2026*
