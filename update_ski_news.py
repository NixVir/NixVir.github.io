#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated Ski Business News Aggregator with LLM Scoring
Fetches RSS feeds from curated ski industry sources and uses LLM to score relevance/quality
"""
import json
import os
import sys
import re
import hashlib
from datetime import datetime, timedelta
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from html import unescape

# API Keys
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# Article categories with keywords for classification
# Note: 'canadian' renamed to 'canada', 'racing-events' renamed to 'winter-sports'
ARTICLE_CATEGORIES = {
    'resort-operations': {
        'name': 'Resort Operations',
        'keywords': ['lift', 'chairlift', 'gondola', 'snowmaking', 'terrain expansion',
                     'new trail', 'mountain operations', 'ski patrol', 'grooming',
                     'base lodge', 'summit lodge', 'ticket', 'pass', 'opening day',
                     'season opening', 'closing day', 'first chair', 'last chair',
                     'delayed opening', 'early opening', 'vertical drop', 'acreage',
                     'catskiing', 'cat skiing', 'heli-skiing', 'heliskiing', 'backcountry lodge',
                     'inaugural season', 'opens for', 'lodge opens']
    },
    'business-investment': {
        'name': 'Business & Investment',
        'keywords': ['acquisition', 'merger', 'investment', 'earnings', 'revenue',
                     'profit', 'loss', 'ipo', 'bankruptcy', 'layoff', 'ceo',
                     'executive', 'quarterly', 'annual report', 'partnership',
                     'financial', 'sold', 'buys', 'purchase', 'ownership',
                     'vail resorts', 'alterra', 'boyne', 'deal', 'billion', 'million']
    },
    'weather-snow': {
        'name': 'Weather & Snow',
        'keywords': ['snowfall', 'snow forecast', 'winter forecast', 'la nina', 'el nino',
                     'climate change', 'global warming', 'snow drought', 'snowpack',
                     'weather forecast', 'storm system', 'blizzard', 'cold front', 'warm winter',
                     'record snow', 'base depth', 'natural snow', 'atmospheric river']
    },
    'transportation': {
        'name': 'Transportation',
        'keywords': ['airport', 'airline', 'flight', 'air service', 'nonstop',
                     'eagle county', 'yampa valley', 'aspen airport', 'jackson hole airport',
                     'salt lake city', 'denver international', 'reno tahoe', 'bozeman',
                     'highway', 'road', 'i-70', 'traffic', 'shuttle', 'bus service',
                     'parking', 'train', 'rail']
    },
    'winter-sports': {
        'name': 'Winter Sports',
        'keywords': ['world cup', 'olympic', 'olympics', 'fis', 'ski race', 'ski racing',
                     'slalom', 'giant slalom', 'downhill race', 'super-g', 'combined',
                     'championship', 'ski competition', 'athlete', 'podium', 'medal',
                     'x games', 'dew tour', 'freestyle', 'halfpipe', 'slopestyle',
                     'nordic', 'cross-country', 'biathlon', 'ski jumping']
    },
    'safety-incidents': {
        'name': 'Safety',
        'keywords': ['accident', 'injury', 'death', 'fatality', 'avalanche',
                     'rescue', 'safety', 'collision', 'lawsuit', 'liability',
                     'ski patrol', 'emergency', 'closed', 'hazard', 'warning',
                     'altercation', 'fight', 'assault', 'arrest', 'charges', 'physical']
    },
    'canada': {
        'name': 'Canada',
        'keywords': ['canada', 'canadian', 'whistler', 'blackcomb', 'banff',
                     'lake louise', 'revelstoke', 'big white', 'sun peaks',
                     'silver star', 'fernie', 'kicking horse', 'mont tremblant',
                     'blue mountain', 'british columbia', 'alberta', 'quebec', 'ontario']
    },
    'international': {
        'name': 'International',
        'keywords': ['europe', 'european', 'alps', 'japan', 'japanese',
                     'australia', 'new zealand', 'south america', 'chile', 'argentina',
                     'chamonix', 'zermatt', 'st. moritz', 'courchevel', 'verbier',
                     'kitzbuhel', 'dolomites', 'perisher', 'thredbo', 'niseko',
                     'worldwide', 'global market']
    },
    'ski-history': {
        'name': 'Ski History',
        'keywords': ['abandoned ski', 'abandoned resort', 'historic ski', 'ski history',
                     'skiing history', 'resort history', '50th anniversary', '75th anniversary',
                     '100th anniversary', 'ski pioneer', 'skiing pioneer', 'vintage ski',
                     'ski legacy', 'ski memorial', 'ski museum', 'skiing museum',
                     'closed permanently', 'defunct ski', 'former ski area', 'old ski area',
                     'ski heritage', 'first ski lift', 'first chairlift', 'remains of ski',
                     'history of skiing', 'history of the resort', 'founded in 19']
    },
    'hospitality': {
        'name': 'Hospitality',
        'keywords': ['hotel', 'hotels', 'lodging', 'accommodation', 'resort hotel',
                     'ski-in ski-out', 'slopeside', 'inn', 'motel', 'vacation rental',
                     'airbnb', 'vrbo', 'condo', 'timeshare', 'bed and breakfast',
                     'room rates', 'occupancy', 'booking', 'reservations', 'hospitality',
                     'lodge', 'chalet', 'cabin rental', 'overnight', 'stay']
    }
}

# Scoring thresholds
# Without LLM: lower thresholds to let more through
AUTO_APPROVE_THRESHOLD = 6  # Was 8 for LLM scoring
AUTO_REJECT_THRESHOLD = 3   # Was 4 for LLM scoring

# Curated RSS sources for ski industry news
RSS_SOURCES = [
    # Major national/international publications (high credibility boost)
    {
        'name': 'New York Times - Travel',
        'url': 'https://rss.nytimes.com/services/xml/rss/nyt/Travel.xml',
        'category': 'major_publication',
        'boost': 3  # Premium journalism
    },
    {
        'name': 'Wall Street Journal',
        'url': 'https://feeds.wsj.com/rss/news',
        'category': 'major_publication',
        'boost': 3
    },
    {
        'name': 'The Economist',
        'url': 'https://www.economist.com/rss',
        'category': 'major_publication',
        'boost': 3
    },
    {
        'name': 'Washington Post',
        'url': 'https://feeds.washingtonpost.com/rss/business',
        'category': 'major_publication',
        'boost': 3
    },
    {
        'name': 'The Atlantic',
        'url': 'https://www.theatlantic.com/feed/all/',
        'category': 'major_publication',
        'boost': 3
    },
    {
        'name': 'Financial Times',
        'url': 'https://www.ft.com/rss/home',
        'category': 'major_publication',
        'boost': 3
    },
    {
        'name': 'Boston Globe',
        'url': 'https://www.bostonglobe.com/rss/feed',
        'category': 'major_publication',
        'boost': 3  # Strong New England ski coverage
    },
    {
        'name': 'Associated Press - Business',
        'url': 'https://rsshub.app/apnews/topics/business',
        'category': 'major_publication',
        'boost': 3  # Wire service - broad business coverage
    },
    {
        'name': 'Bloomberg Markets',
        'url': 'https://feeds.bloomberg.com/markets/news.rss',
        'category': 'major_publication',
        'boost': 3  # Premium financial journalism
    },
    {
        'name': 'Google News - Ski Industry',
        'url': 'https://news.google.com/rss/search?q=ski+resort+business+OR+ski+industry&hl=en-US&gl=US&ceid=US:en',
        'category': 'aggregator',
        'boost': 1  # Aggregator - catches stories from many sources
    },
    {
        'name': 'Christian Science Monitor',
        'url': 'https://rss.csmonitor.com/feeds/all',
        'category': 'major_publication',
        'boost': 3  # Quality journalism
    },
    # Major Canadian newspapers
    {
        'name': 'Globe and Mail - Business',
        'url': 'https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/business/',
        'category': 'canadian_publication',
        'boost': 3  # Canada's national newspaper
    },
    {
        'name': 'CBC News - Business',
        'url': 'https://www.cbc.ca/webfeed/rss/rss-business',
        'category': 'canadian_publication',
        'boost': 2  # Canadian public broadcaster
    },
    # Canadian ski organizations
    {
        'name': 'Canadian Ski Council',
        'url': 'https://www.skicanada.org/feed/',
        'category': 'canadian_industry',
        'boost': 2  # National ski industry association
    },
    # European ski news
    {
        'name': 'PlanetSKI',
        'url': 'https://planetski.eu/feed/',
        'category': 'international',
        'boost': 1  # European ski news coverage
    },
    {
        'name': 'The Ski Guru',
        'url': 'https://www.the-ski-guru.com/feed/',
        'category': 'international',
        'boost': 1  # European Alps coverage
    },
    # 2026 Winter Olympics coverage via Google News
    {
        'name': 'Google News - 2026 Winter Olympics Ski',
        'url': 'https://news.google.com/rss/search?q=2026+Winter+Olympics+Milan+Cortina+skiing&hl=en-US&gl=US&ceid=US:en',
        'category': 'aggregator',
        'boost': 1  # Milan-Cortina 2026 coverage
    },
    # Industry publications
    {
        'name': 'Outside Business Journal',
        'url': 'https://www.outsidebusinessjournal.com/feed/',
        'category': 'business',
        'boost': 2  # Higher quality business journalism
    },
    {
        'name': 'SIA - Snowsports Industries America',
        'url': 'https://snowsports.org/feed/',
        'category': 'industry',
        'boost': 2  # Official industry association
    },
    {
        'name': 'Snow Industry News',
        'url': 'https://www.snowindustrynews.com/rss',
        'category': 'industry',
        'boost': 2  # Dedicated ski industry trade publication
    },
    {
        'name': 'Ski Area Management',
        'url': 'https://www.saminfo.com/headline-news?format=feed&type=rss',
        'category': 'industry',
        'boost': 2  # Trade magazine for mountain resort industry since 1962
    },
    # Ski news sites
    {
        'name': 'Unofficial Networks',
        'url': 'https://unofficialnetworks.com/feed/',
        'category': 'news',
        'boost': 0
    },
    {
        'name': 'SnowBrains',
        'url': 'https://snowbrains.com/feed/',
        'category': 'news',
        'boost': 0
    },
    # Mountain community newspapers
    {
        'name': 'Summit Daily News',
        'url': 'https://www.summitdaily.com/feed/',
        'category': 'local',
        'boost': 1  # Breckenridge/Summit County
    },
    {
        'name': 'Vail Daily',
        'url': 'https://www.vaildaily.com/feed/',
        'category': 'local',
        'boost': 1
    },
    {
        'name': 'Aspen Times',
        'url': 'https://www.aspentimes.com/feed/',
        'category': 'local',
        'boost': 1
    },
    {
        'name': 'Park Record',
        'url': 'https://www.parkrecord.com/feed/',
        'category': 'local',
        'boost': 1  # Park City
    },
    {
        'name': 'Jackson Hole News & Guide',
        'url': 'https://www.jhnewsandguide.com/search/?f=rss&t=article&l=25',
        'category': 'local',
        'boost': 1
    },
    {
        'name': 'Tahoe Daily Tribune',
        'url': 'https://www.tahoedailytribune.com/feed/',
        'category': 'local',
        'boost': 1
    },
    {
        'name': 'Mountain Xpress',
        'url': 'https://mountainx.com/feed/',
        'category': 'local',
        'boost': 0  # Asheville area
    },
    # Environmental/Western news
    {
        'name': 'High Country News',
        'url': 'https://www.hcn.org/feed/',
        'category': 'environment',
        'boost': 1  # Climate/land use coverage
    },
    # Ski history
    {
        'name': 'International Skiing History Association',
        'url': 'https://www.skiinghistory.org/feed',
        'category': 'history',
        'boost': 1
    },
    # Colorado TV stations (good for breaking ski news)
    {
        'name': 'Denver7',
        'url': 'https://www.denver7.com/news/local-news.rss',
        'category': 'local_news',
        'boost': 1  # Colorado ski coverage
    },
    # Hospitality and hotel industry
    {
        'name': 'CoStar Hotels',
        'url': 'https://www.costar.com/rss/news/hotels',
        'category': 'hospitality',
        'boost': 2  # Hotel industry news for ski resort hospitality
    },
    # Government statistics (population, demographics, economic data)
    {
        'name': 'U.S. Census Bureau',
        'url': 'https://www.census.gov/economic-indicators/indicator.xml',
        'category': 'government',
        'boost': 3  # Official U.S. government statistics
    },
    {
        'name': 'Statistics Canada - Travel & Tourism',
        'url': 'https://www150.statcan.gc.ca/n1/dai-quo/ssi/homepage-eng.xml',
        'category': 'government',
        'boost': 3  # Official Canadian government statistics
    }
]

# Keywords for basic pre-filtering (must contain at least one)
# This is a broad filter - more specific scoring happens later
BUSINESS_KEYWORDS = [
    # Resort/destination business
    'resort', 'ski area', 'mountain', 'lift', 'investment', 'acquisition',
    'merger', 'expansion', 'revenue', 'profit', 'loss', 'earnings', 'quarterly',
    'annual', 'season pass', 'ikon', 'epic', 'vail', 'alterra', 'boyne',
    'aspen', 'employee', 'workforce', 'labor', 'snowmaking',
    'sustainability', 'hotel', 'lodging', 'retail', 'rental', 'terrain park',
    'gondola', 'chairlift', 'industry', 'market', 'growth', 'decline',
    'visitor', 'skier visits', 'bankruptcy',
    'ceo', 'executive', 'management', 'partnership',
    # Opening/closing dates
    'opening day', 'opens for', 'season opening', 'closing day', 'closes for',
    'season closing', 'first chair', 'last chair', 'opening date', 'closing date',
    # Real estate and development (ski community focus)
    'real estate', 'development', 'housing', 'condo', 'condominium',
    'affordable housing', 'workforce housing', 'zoning', 'planning',
    'construction', 'property', 'residential', 'commercial',
    'breckenridge', 'park city', 'jackson hole', 'telluride', 'steamboat',
    'whistler', 'tahoe', 'mammoth', 'big sky', 'deer valley',
    # Weather and climate (high priority per guidelines)
    'snowfall', 'snow forecast', 'winter forecast', 'la nina', 'el nino',
    'climate change', 'climate', 'global warming', 'snow drought', 'snowpack',
    'weather', 'forecast', 'storm', 'blizzard', 'cold front', 'warm winter',
    # Canadian ski areas and markets (high priority)
    'whistler', 'blackcomb', 'banff', 'lake louise', 'revelstoke', 'big white',
    'sun peaks', 'silver star', 'fernie', 'kicking horse', 'mont tremblant',
    'blue mountain', 'canadian', 'canada', 'british columbia', 'alberta', 'quebec',
    # International markets and travel
    'europe', 'european', 'alps', 'japan', 'international',
    'australia', 'new zealand', 'chile', 'argentina', 'worldwide',
    # Lodging and hospitality
    'hotel', 'lodge', 'lodging', 'inn', 'resort hotel', 'slopeside',
    'vacation rental', 'airbnb', 'vrbo', 'occupancy', 'room rate',
    'hospitality', 'accommodation', 'bed tax', 'lodging tax',
    # Air travel to ski destinations
    'airport', 'airline', 'flight', 'air service', 'nonstop',
    'eagle county', 'yampa valley', 'aspen airport', 'jackson hole airport',
    'salt lake city', 'denver international', 'reno tahoe', 'bozeman',
    'montrose', 'hayden', 'sun valley airport', 'mammoth airport',
    # Currency and international visitors
    'exchange rate', 'currency', 'canadian dollar', 'euro', 'strong dollar',
    'weak dollar', 'international visitor', 'foreign tourist', 'inbound tourism',
    'outbound tourism', 'cross-border', 'tourism statistics', 'visitor spending',
    # Ski history
    'ski history', 'historic', 'anniversary', 'founded', 'pioneer',
    # 2026 Winter Olympics
    'winter olympics', 'olympic', 'milan', 'cortina', 'milano cortina',
    '2026 games', 'olympic venue', 'alpine skiing', 'downhill',
    # European ski destinations
    'chamonix', 'zermatt', 'st. moritz', 'val d\'isere', 'courchevel',
    'verbier', 'kitzbuhel', 'st. anton', 'lech', 'ischgl', 'dolomites',
    # Australian ski
    'perisher', 'thredbo', 'falls creek', 'hotham', 'mt buller',
    # Additional Canadian
    'ontario ski', 'quebec ski', 'ski quebec', 'bromont', 'tremblant'
]

def print_safe(msg):
    """Print with safe encoding for Windows"""
    try:
        print(msg)
    except:
        print(msg.encode('ascii', 'replace').decode('ascii'))

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

def clean_html(text):
    """Remove HTML tags and clean text"""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Decode HTML entities
    text = unescape(text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_rss_feed(xml_content, source_name):
    """Parse RSS feed and extract articles"""
    articles = []
    try:
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

        for item in items:
            article = {'source': source_name}

            # RSS format
            title = item.find('title')
            link = item.find('link')
            description = item.find('description')
            pub_date = item.find('pubDate')
            content = item.find('content:encoded', namespaces)

            # Atom format fallbacks
            if title is None:
                title = item.find('atom:title', namespaces)
            if link is None:
                link_elem = item.find('atom:link', namespaces)
                if link_elem is not None:
                    article['url'] = link_elem.get('href', '')
            if description is None:
                description = item.find('atom:summary', namespaces)
            if pub_date is None:
                pub_date = item.find('atom:published', namespaces)
                if pub_date is None:
                    pub_date = item.find('atom:updated', namespaces)

            if title is not None:
                article['title'] = clean_html(title.text or '')

            if 'url' not in article and link is not None:
                article['url'] = link.text if link.text else ''

            if description is not None:
                article['description'] = clean_html(description.text or '')[:500]

            if content is not None:
                article['content'] = clean_html(content.text or '')[:1000]
            elif 'description' in article:
                article['content'] = article['description']

            if pub_date is not None and pub_date.text:
                article['pub_date'] = pub_date.text

            # Generate unique ID
            if article.get('url'):
                article['id'] = hashlib.md5(article['url'].encode()).hexdigest()[:12]
                articles.append(article)

    except ET.ParseError as e:
        print_safe(f"  ! XML parse error for {source_name}: {e}")
    except Exception as e:
        print_safe(f"  ! Error parsing {source_name}: {e}")

    return articles

def basic_relevance_filter(article):
    """Quick keyword-based pre-filter before LLM scoring"""
    text = f"{article.get('title', '')} {article.get('description', '')}".lower()

    for keyword in BUSINESS_KEYWORDS:
        if keyword.lower() in text:
            return True
    return False

def assign_categories(article):
    """Assign primary and secondary categories to an article based on keyword matching.
    Returns a tuple: (primary_category, list_of_secondary_categories)
    """
    text = f"{article.get('title', '')} {article.get('description', '')} {article.get('content', '')}".lower()
    title = article.get('title', '').lower()

    category_scores = {}

    for cat_id, cat_info in ARTICLE_CATEGORIES.items():
        score = 0
        for keyword in cat_info['keywords']:
            # Title matches count more
            if keyword.lower() in title:
                score += 3
            elif keyword.lower() in text:
                score += 1
        category_scores[cat_id] = score

    # Sort categories by score descending
    sorted_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)

    # Get primary category (highest score)
    primary = 'resort-operations'
    secondary = []

    if sorted_cats and sorted_cats[0][1] > 0:
        primary = sorted_cats[0][0]

        # Get secondary categories (score > 0, not primary, max 3)
        for cat_id, score in sorted_cats[1:]:
            if score > 0 and len(secondary) < 3:
                secondary.append(cat_id)

    return primary, secondary


def assign_category(article):
    """Assign a category to an article based on keyword matching (legacy single-category)"""
    primary, _ = assign_categories(article)
    return primary

def score_with_claude(article):
    """Score article using Claude API"""
    if not ANTHROPIC_API_KEY:
        return None, "No API key"

    prompt = f"""Score this ski industry news article on a scale of 1-10 for inclusion in a ski business news feed.

Title: {article.get('title', 'No title')}
Source: {article.get('source', 'Unknown')}
Content: {article.get('content', article.get('description', 'No content'))[:800]}

CONTENT GUIDELINES:

STRICTLY EXCLUDE (score 1-2):
- Promotional content: ticket deals, pass sales, resort marketing, "book now" messaging
- Product advertisements, gear reviews, or buying guides
- Personal trip reports, "best runs" listicles, or travel diary content
- General skiing tips, how-to guides, or beginner advice
- Feel-good human interest stories UNLESS they have significant business/industry angle
- Tangentially related outdoor content (hiking, camping, tick repellent, summer activities at ski areas)
- Lifestyle fluff pieces without substantive business news
- Event announcements without business context (concerts, festivals, races unless about economic impact)

EXCLUDE (score 3-4):
- Stories mentioning ski areas only in passing
- General outdoor recreation news not specifically about ski industry business
- Weather reports without business/operational impact analysis
- Local news that happens to be near a ski town but isn't about ski industry

INCLUDE AND PRIORITIZE (score 8-10):
- Major ski resort business news: acquisitions, mergers, investments, ownership changes, billion-dollar developments
- Real estate development in ski communities: housing projects, base village developments, luxury developments
- Industry-wide business trends: skier visit statistics, season performance, market analysis
- Resort financial news: earnings, revenue, profit/loss, bankruptcy, layoffs, executive changes
- Canadian ski industry news (any stories about Canadian resorts, markets, or developments)
- Climate change business impacts on ski industry (snowmaking investments, season length trends, adaptation strategies)
- Workforce and labor issues at ski areas (housing shortages, wage disputes, staffing challenges)
- 2026 Milan-Cortina Winter Olympics news with ski industry business relevance (venue construction, economic impact, tourism projections)
- International ski market news (European Alps, Australia, Japan, South America)

MODERATE PRIORITY (score 5-7):
- Resort opening and closing dates (season openings, delayed openings, early closures)
- Winter weather forecasts with clear ski industry relevance
- Lodging and hospitality business in ski markets (hotels, vacation rentals, occupancy rates)
- Air travel to ski destinations (new routes, airport capacity changes)
- Ski history and heritage stories with substantive content
- International ski market news and trends
- Currency/tourism statistics affecting ski travel
- Equipment/apparel industry BUSINESS news (not product reviews)

SOURCE QUALITY BONUS:
Articles from major publications (NYT, WSJ, Economist, Washington Post, Financial Times, Boston Globe, Atlantic) should be given extra consideration for quality journalism.

Scoring criteria (in order of importance):
1. Direct relevance to ski resort/destination BUSINESS operations
2. Substantive news value (not fluff or filler)
3. Quality of reporting (investigative journalism > press release rehash)
4. Timeliness and newsworthiness

Respond with ONLY a JSON object in this exact format:
{{"relevance": X, "news_value": X, "quality": X, "overall": X, "reason": "brief explanation"}}

The overall score should be your recommendation for inclusion (1-10). Be strict - only truly relevant ski business news should score 7+."""

    try:
        data = json.dumps({
            "model": "claude-3-haiku-20240307",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}]
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=data,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': ANTHROPIC_API_KEY,
                'anthropic-version': '2023-06-01'
            }
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            content = result['content'][0]['text']

            # Parse JSON from response
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                scores = json.loads(json_match.group())
                return scores.get('overall', 5), scores

    except Exception as e:
        print_safe(f"    ! Claude API error: {e}")

    return None, "API error"

def score_with_openai(article):
    """Score article using OpenAI API (fallback)"""
    if not OPENAI_API_KEY:
        return None, "No API key"

    prompt = f"""Score this ski industry news article on a scale of 1-10 for inclusion in a ski business news feed.

Title: {article.get('title', 'No title')}
Source: {article.get('source', 'Unknown')}
Content: {article.get('content', article.get('description', 'No content'))[:800]}

CONTENT GUIDELINES:

STRICTLY EXCLUDE (score 1-2):
- Promotional content: ticket deals, pass sales, resort marketing, "book now" messaging
- Product advertisements, gear reviews, or buying guides
- Personal trip reports, "best runs" listicles, or travel diary content
- General skiing tips, how-to guides, or beginner advice
- Feel-good human interest stories UNLESS they have significant business/industry angle
- Tangentially related outdoor content (hiking, camping, tick repellent, summer activities at ski areas)
- Lifestyle fluff pieces without substantive business news

EXCLUDE (score 3-4):
- Stories mentioning ski areas only in passing
- General outdoor recreation news not specifically about ski industry business
- Weather reports without business/operational impact analysis

INCLUDE AND PRIORITIZE (score 8-10):
- Major ski resort business news: acquisitions, mergers, investments, ownership changes, billion-dollar developments
- Real estate development in ski communities: housing projects, base village developments
- Industry-wide business trends: skier visit statistics, season performance, market analysis
- Resort financial news: earnings, revenue, profit/loss, bankruptcy, layoffs, executive changes
- Canadian ski industry news
- Climate change business impacts on ski industry
- Workforce and labor issues at ski areas
- 2026 Milan-Cortina Winter Olympics business news
- International ski market news (Europe, Australia, Japan)

MODERATE PRIORITY (score 5-7):
- Resort opening and closing dates
- Winter weather forecasts with clear ski industry relevance
- Lodging and hospitality business in ski markets
- Air travel to ski destinations
- Ski history and heritage stories with substantive content
- Equipment/apparel industry BUSINESS news (not product reviews)

Respond with ONLY a JSON object in this exact format:
{{"relevance": X, "news_value": X, "quality": X, "overall": X, "reason": "brief explanation"}}

Be strict - only truly relevant ski business news should score 7+."""

    try:
        data = json.dumps({
            "model": "gpt-3.5-turbo",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}]
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {OPENAI_API_KEY}'
            }
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            content = result['choices'][0]['message']['content']

            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                scores = json.loads(json_match.group())
                return scores.get('overall', 5), scores

    except Exception as e:
        print_safe(f"    ! OpenAI API error: {e}")

    return None, "API error"

def basic_keyword_score(article):
    """Score article using keyword analysis when no LLM available"""
    text = f"{article.get('title', '')} {article.get('description', '')} {article.get('content', '')}".lower()
    title = article.get('title', '').lower()

    score = 5  # Base score

    # HIGH PRIORITY: Resort/destination business news (in title = +3, in body = +2)
    resort_business = ['acquisition', 'merger', 'investment', 'earnings', 'expansion',
                       'revenue', 'profit', 'growth', 'ipo', 'bankruptcy', 'layoff',
                       'ceo', 'executive', 'quarterly', 'annual report', 'partnership',
                       'financial', 'closes', 'sold', 'buys', 'purchase', 'management']
    for kw in resort_business:
        if kw in title:
            score += 3
        elif kw in text:
            score += 2

    # HIGH PRIORITY: Weather and climate stories (+2-3)
    weather_climate = ['snowfall', 'snow forecast', 'winter forecast', 'la nina', 'el nino',
                       'climate change', 'global warming', 'snow drought', 'early season',
                       'late season', 'record snow', 'warm winter', 'cold winter',
                       'weather pattern', 'snowpack', 'water supply', 'drought']
    for kw in weather_climate:
        if kw in title:
            score += 3
        elif kw in text:
            score += 2

    # HIGH PRIORITY: International markets (+2)
    international = ['europe', 'european', 'alps', 'japan', 'japanese',
                     'australia', 'new zealand', 'south america', 'chile', 'argentina',
                     'china', 'chinese', 'international', 'global market', 'worldwide']
    for kw in international:
        if kw in text:
            score += 2
            break  # Only count once

    # HIGH PRIORITY: Canadian ski stories (+2-3)
    canadian = ['canada', 'canadian', 'whistler', 'blackcomb', 'banff', 'lake louise',
                'revelstoke', 'big white', 'sun peaks', 'silver star', 'fernie',
                'kicking horse', 'mont tremblant', 'blue mountain', 'british columbia',
                'alberta', 'quebec', 'ontario']
    for kw in canadian:
        if kw in title:
            score += 3
        elif kw in text:
            score += 2
            break  # Only count Canadian once if in body

    # HIGH PRIORITY: Opening/closing dates (+2-3)
    opening_closing = ['opening day', 'opens for season', 'season opening', 'first chair',
                       'closing day', 'closes for season', 'season closing', 'last chair',
                       'opening date', 'closing date', 'set to open', 'will open',
                       'announced opening', 'delayed opening', 'early opening']
    for kw in opening_closing:
        if kw in title:
            score += 3
        elif kw in text:
            score += 2

    # HIGH PRIORITY: Real estate/development in ski communities (+2-3)
    real_estate = ['real estate', 'development project', 'housing development', 'condo',
                   'condominium', 'affordable housing', 'workforce housing', 'zoning',
                   'planning commission', 'hotel development', 'mixed-use', 'residential',
                   'commercial development', 'construction project']
    for kw in real_estate:
        if kw in title:
            score += 3
        elif kw in text:
            score += 2

    # Ski community names boost (+1 when combined with development terms)
    ski_communities = ['breckenridge', 'park city', 'jackson hole', 'telluride', 'steamboat',
                       'whistler', 'tahoe', 'mammoth', 'big sky', 'deer valley', 'vail',
                       'aspen', 'snowmass', 'crested butte', 'durango', 'sun valley']
    has_community = any(c in text for c in ski_communities)
    has_development = any(d in text for d in ['development', 'housing', 'real estate', 'construction', 'zoning'])
    if has_community and has_development:
        score += 2

    # HIGH PRIORITY: Lodging and hospitality in ski markets (+2-3)
    lodging = ['hotel occupancy', 'room rate', 'lodging tax', 'bed tax', 'vacation rental',
               'airbnb', 'vrbo', 'resort hotel', 'slopeside lodging', 'ski-in ski-out',
               'hospitality industry', 'hotel development', 'lodge expansion']
    for kw in lodging:
        if kw in title:
            score += 3
        elif kw in text:
            score += 2

    # HIGH PRIORITY: Air travel to ski destinations (+2-3)
    air_travel = ['airport', 'airline', 'air service', 'nonstop flight', 'direct flight',
                  'eagle county airport', 'yampa valley', 'aspen airport', 'jackson hole airport',
                  'bozeman airport', 'montrose airport', 'hayden airport', 'sun valley airport',
                  'mammoth airport', 'reno tahoe', 'denver international']
    for kw in air_travel:
        if kw in title:
            score += 3
        elif kw in text:
            score += 2

    # HIGH PRIORITY: Currency and international visitors (+2-3)
    intl_tourism = ['exchange rate', 'currency', 'canadian dollar', 'strong dollar', 'weak dollar',
                    'international visitor', 'foreign tourist', 'inbound tourism', 'outbound tourism',
                    'cross-border', 'tourism statistics', 'visitor spending', 'travel ban',
                    'visa', 'border crossing', 'canadian visitor', 'european visitor']
    for kw in intl_tourism:
        if kw in title:
            score += 3
        elif kw in text:
            score += 2

    # MEDIUM PRIORITY: Resort operators and industry (+1 each)
    industry_kw = ['vail resorts', 'alterra', 'ikon', 'boyne', 'aspen skiing',
                   'skier visits', 'ski industry', 'resort operator', 'new lift',
                   'new chairlift', 'gondola', 'terrain expansion',
                   'hotel', 'lodging', 'tariff', 'workforce', 'employees']
    for kw in industry_kw:
        if kw in text:
            score += 1

    # LOWER PRIORITY: Equipment/apparel business (only +0.5, rounded)
    equipment_biz = ['manufacturer', 'brand', 'retailer', 'supply chain', 'distribution']
    equip_count = sum(1 for kw in equipment_biz if kw in text)
    score += equip_count // 2

    # PENALTIES: Promotional content (-4 to -5)
    promotional = ['buy now', 'save up to', 'discount', 'deal', 'sale ends',
                   'limited time', 'book now', 'reserve your', 'get your tickets',
                   'pass sale', 'early bird', 'promo code', 'coupon', '% off',
                   'starting at $', 'as low as', 'don\'t miss', 'shop now',
                   'order now', 'special offer', 'exclusive deal']
    for kw in promotional:
        if kw in text:
            score -= 5
            break  # One penalty is enough

    # PENALTIES: Fluff/listicle content (-3 to -4)
    fluff_kw = ['powder day', 'best runs', 'trip report', 'gear review',
                'how to ski', 'beginner tips', 'what to wear', 'packing list',
                'gift guide', 'top 10', 'best of', 'bucket list', 'must-visit',
                'hidden gem', 'insider tips', 'what i learned', 'things to do',
                'ultimate guide', 'complete guide', 'everything you need to know']
    for kw in fluff_kw:
        if kw in text:
            score -= 4
            break

    # PENALTY: Product-focused content (-3)
    product_focus = ['gear guide', 'product review', 'tested:', 'we tested',
                     'best skis', 'best boots', 'best jacket', 'buying guide',
                     'editor\'s pick', 'our favorite', 'we recommend']
    for kw in product_focus:
        if kw in text:
            score -= 3
            break

    # PENALTY: Tangentially related outdoor content
    # Only penalize if NOT in ski resort context (summer ops at resorts are relevant)
    ski_context_indicators = ['ski resort', 'ski area', 'mountain resort', 'ski season',
                              'lift', 'chairlift', 'gondola', 'slope', 'trail', 'terrain',
                              'snowmaking', 'base area', 'summit', 'vertical', 'ski town']
    has_ski_context = any(indicator in text for indicator in ski_context_indicators)

    # These are ALWAYS off-topic regardless of context
    always_penalize = ['tick', 'mosquito', 'bug spray', 'repellent', 'lyme disease']
    for kw in always_penalize:
        if kw in title.lower():
            score -= 5
            break
        elif kw in text:
            score -= 3
            break

    # These are only penalized if NOT in ski resort context
    if not has_ski_context:
        summer_activities = ['hiking trail', 'camping', 'mountain bike', 'golf course',
                             'zip line', 'alpine slide', 'water park', 'fishing', 'hunting',
                             'rock climbing', 'kayak', 'rafting']
        for kw in summer_activities:
            if kw in title.lower():
                score -= 5
                break
            elif kw in text:
                score -= 3
                break

    # PENALTY: Feel-good fluff without business angle (-3)
    feelgood_fluff = ['heartwarming', 'inspiring story', 'feel-good', 'amazing moment',
                      'viral video', 'cute', 'adorable', 'wholesome', 'incredible footage']
    for kw in feelgood_fluff:
        if kw in text:
            score -= 3
            break

    # Source boost
    source_boost = 0
    for src in RSS_SOURCES:
        if src['name'] == article.get('source'):
            source_boost = src.get('boost', 0)
            break
    score += source_boost

    return max(1, min(10, score)), {"reason": f"Keyword scoring (boost: {source_boost})"}

def score_article(article):
    """Score article using available LLM API"""
    # Try Claude first, then OpenAI
    if ANTHROPIC_API_KEY:
        return score_with_claude(article)
    elif OPENAI_API_KEY:
        return score_with_openai(article)
    else:
        return basic_keyword_score(article)

def load_existing_articles():
    """Load existing articles to avoid duplicates"""
    path = 'static/data/ski-news.json'
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {a['id']: a for a in data.get('articles', [])}
        except:
            pass
    return {}

def load_review_queue():
    """Load articles pending review"""
    path = 'static/data/ski-news-review.json'
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {'pending': [], 'rejected': []}

def save_review_queue(queue):
    """Save review queue"""
    path = 'static/data/ski-news-review.json'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(queue, f, indent=2)

def update_ski_news():
    """Main function to fetch and score ski news"""
    print_safe("=" * 60)
    print_safe("Ski Business News Aggregator")
    print_safe(f"Timestamp: {datetime.now().isoformat()}")
    print_safe("=" * 60)

    # Load existing data
    existing_articles = load_existing_articles()
    review_queue = load_review_queue()
    existing_ids = set(existing_articles.keys())
    existing_ids.update(a['id'] for a in review_queue.get('pending', []))
    existing_ids.update(a['id'] for a in review_queue.get('rejected', []))

    print_safe(f"\nExisting articles: {len(existing_articles)}")
    print_safe(f"Pending review: {len(review_queue.get('pending', []))}")

    all_articles = []

    # Fetch from all sources
    print_safe("\n--- Fetching RSS Feeds ---")
    for source in RSS_SOURCES:
        print_safe(f"\n{source['name']}...")
        content = fetch_url(source['url'])
        if content:
            articles = parse_rss_feed(content, source['name'])
            # Filter out already-seen articles
            new_articles = [a for a in articles if a.get('id') not in existing_ids]
            print_safe(f"  Found {len(articles)} articles, {len(new_articles)} new")
            all_articles.extend(new_articles)
        else:
            print_safe(f"  ! Failed to fetch")

    print_safe(f"\n--- Processing {len(all_articles)} New Articles ---")

    # Pre-filter with keywords
    filtered_articles = [a for a in all_articles if basic_relevance_filter(a)]
    print_safe(f"After keyword filter: {len(filtered_articles)} articles")

    approved = []
    pending = review_queue.get('pending', [])
    rejected = review_queue.get('rejected', [])

    # Score each article with LLM
    for i, article in enumerate(filtered_articles[:20]):  # Limit to 20 per run for cost control
        print_safe(f"\n[{i+1}/{min(len(filtered_articles), 20)}] {article.get('title', 'No title')[:60]}...")

        score, details = score_article(article)

        if score is None:
            print_safe(f"    ? Scoring failed, queuing for review")
            article['score'] = 5
            article['score_details'] = {"reason": "Scoring failed"}
            pending.append(article)
        elif score >= AUTO_APPROVE_THRESHOLD:
            print_safe(f"    + Score: {score} - AUTO APPROVED")
            article['score'] = score
            article['score_details'] = details
            article['approved_date'] = datetime.now().strftime('%Y-%m-%d')
            primary, secondary = assign_categories(article)
            article['category'] = primary
            article['secondary_categories'] = secondary
            cat_display = primary + (f" (+{', '.join(secondary)})" if secondary else "")
            print_safe(f"    Category: {cat_display}")
            approved.append(article)
        elif score <= AUTO_REJECT_THRESHOLD:
            print_safe(f"    - Score: {score} - REJECTED")
            article['score'] = score
            article['score_details'] = details
            rejected.append(article)
        else:
            print_safe(f"    ~ Score: {score} - PENDING REVIEW")
            article['score'] = score
            article['score_details'] = details
            pending.append(article)

    # Merge approved with existing
    for article in approved:
        existing_articles[article['id']] = article

    # Sort by date and keep last 50
    sorted_articles = sorted(
        existing_articles.values(),
        key=lambda x: x.get('pub_date', x.get('approved_date', '')),
        reverse=True
    )[:50]

    # Keep only last 100 rejected
    rejected = rejected[-100:]

    # Save results
    output_data = {
        'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_articles': len(sorted_articles),
        'articles': sorted_articles
    }

    output_path = 'static/data/ski-news.json'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)

    # Save review queue
    save_review_queue({'pending': pending, 'rejected': rejected})

    print_safe("\n" + "=" * 60)
    print_safe("SUMMARY")
    print_safe("=" * 60)
    print_safe(f"New articles approved: {len(approved)}")
    print_safe(f"Total approved articles: {len(sorted_articles)}")
    print_safe(f"Pending review: {len(pending)}")
    print_safe(f"Rejected: {len(rejected)}")
    print_safe(f"\nOutput: {output_path}")
    print_safe("=" * 60)

    return output_data

if __name__ == '__main__':
    # Check for API keys
    if not ANTHROPIC_API_KEY and not OPENAI_API_KEY:
        print_safe("WARNING: No LLM API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY")
        print_safe("Falling back to basic keyword scoring.\n")

    try:
        update_ski_news()
    except Exception as e:
        print_safe(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
