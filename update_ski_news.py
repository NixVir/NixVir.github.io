#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated Ski Business News Aggregator with LLM Scoring

Fetches RSS feeds from curated ski industry sources and uses keyword-based
or LLM-based scoring to filter and categorize articles.

Improvements (Jan 2026):
- Two-stage filtering: strict pre-filter + scoring
- Story deduplication across sources
- Contextual penalty patterns (regex-based)
- Category priority system with phrase matching
- LLM scoring toggle (default OFF)
- Source health monitoring
- Enhanced article metadata
"""
import json
import os
import sys
import re
import hashlib
import difflib
from datetime import datetime, timedelta
from collections import defaultdict
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from html import unescape

# Try to import PyYAML for config file support
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


def load_config():
    """Load configuration from YAML file with fallback to defaults."""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'ski-news-config.yaml')
    defaults = {
        'scoring': {
            'enable_llm': False,
            'thresholds': {'llm': {'approve': 7, 'reject': 3}, 'keyword': {'approve': 6, 'reject': 3}}
        },
        'diversity': {'max_per_source': 5},
        'deduplication': {'title_similarity': 0.85, 'lead_paragraph_similarity': 0.80, 'min_lead_length': 50},
        'focus_topics': {},
        'output': {'max_articles': 75, 'max_rejected': 100, 'max_per_run': 50},
        'logging': {'enable_run_log': True, 'max_log_entries': 30}
    }

    if not YAML_AVAILABLE:
        return defaults

    if not os.path.exists(config_path):
        return defaults

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            user_config = yaml.safe_load(f) or {}

        # Deep merge user config with defaults
        def merge(base, override):
            result = base.copy()
            for k, v in override.items():
                if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                    result[k] = merge(result[k], v)
                else:
                    result[k] = v
            return result

        return merge(defaults, user_config)
    except Exception as e:
        print(f"Warning: Could not load config file: {e}")
        return defaults


# Load configuration
CONFIG = load_config()

# =============================================================================
# CONFIGURATION - Values loaded from config/ski-news-config.yaml or defaults
# =============================================================================

# LLM scoring toggle - can be overridden by environment variable
ENABLE_LLM_SCORING = (
    os.environ.get('ENABLE_LLM_SCORING', 'false').lower() == 'true' or
    CONFIG.get('scoring', {}).get('enable_llm', False)
)

# API Keys (only used if ENABLE_LLM_SCORING is True)
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# Scoring thresholds - from config or defaults
if ENABLE_LLM_SCORING:
    AUTO_APPROVE_THRESHOLD = CONFIG.get('scoring', {}).get('thresholds', {}).get('llm', {}).get('approve', 7)
    AUTO_REJECT_THRESHOLD = CONFIG.get('scoring', {}).get('thresholds', {}).get('llm', {}).get('reject', 3)
else:
    AUTO_APPROVE_THRESHOLD = CONFIG.get('scoring', {}).get('thresholds', {}).get('keyword', {}).get('approve', 6)
    AUTO_REJECT_THRESHOLD = CONFIG.get('scoring', {}).get('thresholds', {}).get('keyword', {}).get('reject', 3)

# Source diversity control - from config or default
MAX_ARTICLES_PER_SOURCE = CONFIG.get('diversity', {}).get('max_per_source', 5)

# Output settings - from config
MAX_ARTICLES_OUTPUT = CONFIG.get('output', {}).get('max_articles', 50)
MAX_REJECTED_KEEP = CONFIG.get('output', {}).get('max_rejected', 100)
MAX_PER_RUN = CONFIG.get('output', {}).get('max_per_run', 30)

# Focus topics - from config
FOCUS_TOPICS = CONFIG.get('focus_topics', {})

# =============================================================================
# ARTICLE EXPIRATION (prevents stale content from persisting)
# =============================================================================

# Maximum age for articles in the feed (in days)
MAX_ARTICLE_AGE_DAYS = 21

# =============================================================================
# MAJOR SOURCE WHITELIST (trusted sources bypass strict pre-filter)
# =============================================================================

# These sources produce high-quality content and don't publish fluff.
# Their articles bypass the strict ski-term pre-filter but still need
# either a ski term OR macro relevance terms to pass.
WHITELIST_SOURCES = {
    # Must match RSS_SOURCES 'name' field exactly
    'New York Times - Travel',
    'New York Times - Business',
    'New York Times - Climate',
    'New York Times - U.S.',
    'Washington Post',
    'Reuters Business',
    'Associated Press - Top News',
    'Bloomberg Markets',
    'Financial Times',
    'The Atlantic',
    'Globe and Mail - Business',
    'CBC News - Business',
    'Skift',
}

# =============================================================================
# STRICT PRE-FILTER TERMS (Two-tier system from improvement spec)
# =============================================================================

# Must match AT LEAST ONE from primary group to pass pre-filter
PRIMARY_SKI_TERMS = {
    # Core ski industry terms (these gate entry to the feed)
    'ski resort', 'ski area', 'ski mountain', 'ski industry',
    'lift ticket', 'season pass', 'skier visit', 'skier visits',
    'chairlift', 'gondola', 'snowmaking', 'ski patrol',
    'terrain park', 'ski slope', 'ski run', 'ski trail',

    # Major resort operators (business entities - high signal)
    'vail resorts', 'alterra mountain', 'epic pass', 'ikon pass',
    'boyne resorts', 'aspen skiing company', 'powdr corporation',
    'peak resorts', 'intrawest', 'cnt resorts',

    # Compound resort terms (require "resort" or "ski" for specificity)
    'whistler blackcomb', 'park city mountain', 'deer valley resort',
    'mammoth mountain', 'palisades tahoe', 'big sky resort',
    'jackson hole mountain', 'steamboat resort', 'telluride ski',
    'breckenridge ski', 'keystone resort', 'copper mountain resort',
    'winter park resort', 'vail mountain', 'beaver creek resort',
    'snowbird resort', 'killington resort', 'stowe mountain',
    'sugarbush resort', 'jay peak resort', 'sun valley resort',

    # Canadian resorts (compound forms)
    'whistler resort', 'banff sunshine', 'lake louise ski',
    'revelstoke mountain', 'sun peaks resort', 'big white ski',
    'mont tremblant', 'blue mountain resort',

    # Industry organizations and publications
    'nsaa', 'national ski areas association', 'canada west ski areas',
    'ski area management', 'snowsports industries', 'ski industry',
    'resort operator', 'mountain operator',

    # Business-specific ski terms
    'ski season', 'opening day', 'ski operations', 'mountain operations',
    'base lodge', 'summit lodge', 'lift upgrade', 'terrain expansion',
}

# REMOVED: Individual resort names that match too broadly (whistler, aspen, vail, etc.)
# These now require compound forms or are handled via RESORT_NAME_CONTEXT below

# Resort names that ONLY pass pre-filter when combined with business context
RESORT_NAME_CONTEXT_REQUIRED = {
    'whistler', 'blackcomb', 'aspen', 'vail', 'park city', 'deer valley',
    'jackson hole', 'mammoth', 'big sky', 'telluride', 'steamboat',
    'breckenridge', 'keystone', 'snowbird', 'alta', 'killington', 'stowe',
    'banff', 'lake louise', 'revelstoke', 'sun peaks', 'mont tremblant',
    'chamonix', 'zermatt', 'st. moritz', 'courchevel', 'verbier', 'niseko',
}

# Secondary terms boost score but don't gate entry
SECONDARY_BUSINESS_TERMS = {
    # Corporate actions
    'acquisition', 'merger', 'investment', 'earnings', 'revenue',
    'expansion', 'development', 'bankruptcy', 'restructuring',
    'ipo', 'private equity', 'venture capital', 'funding',
    # Leadership
    'ceo', 'cfo', 'coo', 'executive', 'board of directors', 'appointed',
    'general manager', 'president', 'vice president', 'management',
    # Financial
    'quarterly', 'annual report', 'financial', 'profit', 'loss',
    'ebitda', 'margin', 'stock', 'shares', 'dividend', 'forecast',
    # Operations
    'layoff', 'workforce', 'employee', 'staffing', 'hiring',
    'labor shortage', 'wage', 'h-2b', 'j-1 visa', 'seasonal worker',
    # Real estate and development
    'real estate', 'housing', 'property', 'land sale', 'zoning',
    'permit', 'construction', 'development project',
    # Tourism metrics
    'occupancy', 'visitation', 'visitor', 'tourism', 'destination',
    'air service', 'flight', 'airline', 'airport',
    # Legal
    'lawsuit', 'litigation', 'settlement', 'liability', 'regulatory',
    'compliance', 'insurance', 'claim',
    # Industry trends
    'market share', 'competition', 'consolidation', 'growth', 'decline',
}

# =============================================================================
# MACRO RELEVANCE TERMS (Adjacent stories affecting ski industry)
# =============================================================================
# These terms alone don't pass pre-filter, but combined with mountain region
# geography, they create a secondary pathway for industry-relevant stories

MACRO_RELEVANCE_TERMS = {
    # Climate and weather patterns
    'climate change', 'global warming', 'drought', 'water shortage', 'snowpack',
    'la nina', 'la niña', 'el nino', 'el niño', 'atmospheric river', 'winter forecast',
    # Travel and transportation
    'airline', 'air service', 'airport expansion', 'flight routes', 'tourism statistics',
    'travel demand', 'visitor spending', 'hotel occupancy', 'lodging rates',
    # Labor and economics
    'labor shortage', 'seasonal workers', 'h-2b visa', 'minimum wage', 'workforce',
    'housing crisis', 'affordable housing', 'employee housing',
    # Real estate and development
    'mountain development', 'resort community', 'second home', 'vacation home',
    # Regional economics
    'mountain town', 'mountain economy', 'resort town', 'tourism revenue',
    # Dashboard economic indicators (macro conditions affecting ski demand)
    'consumer confidence', 'consumer sentiment', 'consumer spending',
    'personal savings rate', 'savings rate', 'discretionary spending',
    'recreation spending', 'leisure spending', 'travel spending',
    'inflation rate', 'cpi', 'consumer price index', 'cost of living',
    'unemployment rate', 'job growth', 'jobs report', 'nonfarm payrolls',
    'wage growth', 'average hourly earnings', 'real wages',
    'interest rate', 'fed funds rate', 'federal reserve', 'rate cut', 'rate hike',
    'yield curve', 'treasury yield', 'inverted yield curve', 'recession signal',
    'gdp growth', 'economic growth', 'economic slowdown', 'recession',
    'housing starts', 'housing market', 'home prices', 'mortgage rate',
    # Dashboard commodity/energy indicators
    'oil price', 'crude oil', 'gasoline price', 'gas prices', 'fuel cost',
    'natural gas price', 'heating cost', 'energy cost', 'energy prices',
    'electricity price', 'electricity rates', 'utility costs',
    # Dashboard market indicators
    'stock market', 'market downturn', 'market rally', 'bear market', 'bull market',
    'vix', 'market volatility', 'sp 500', 's&p 500',
    # Currency/international visitor spending
    'strong dollar', 'weak dollar', 'exchange rate', 'currency',
    'canadian dollar', 'euro exchange', 'yen exchange',
    # Sports betting / prediction markets (dashboard section)
    'sports betting', 'prediction market', 'sports wagering',
}

# Geographic terms that activate macro relevance pathway
MOUNTAIN_REGION_TERMS = {
    'colorado', 'utah', 'montana', 'wyoming', 'idaho', 'california', 'nevada',
    'vermont', 'new hampshire', 'maine', 'new york', 'tahoe', 'rockies', 'rocky mountain',
    'sierra', 'cascades', 'british columbia', 'alberta', 'quebec', 'ontario',
    'alps', 'dolomites', 'pyrenees', 'japan alps', 'southern alps'
}

# =============================================================================
# CATEGORY DEFINITIONS WITH PRIORITY
# =============================================================================

# Categories in priority order (higher = takes precedence when tied)
CATEGORY_PRIORITY = {
    'business-investment': 10,  # Always prioritize business news
    'weather-snow': 7,
    'resort-operations': 6,
    'transportation': 5,
    'hospitality': 4,
    'safety-incidents': 4,       # Demoted - too many minor incident articles were crowding feed
    'winter-sports': 3,
    'canada': 2,                 # Geography is secondary
    'international': 2,
    'ski-history': 1
}

# Category-defining phrases (stronger signal than single keywords)
CATEGORY_PHRASES = {
    'business-investment': [
        'acquisition of', 'merger with', 'announces earnings', 'revenue of',
        'investment in', 'files for bankruptcy', 'names new ceo', 'layoffs at',
        'skier visits', 'visitation numbers', 'economic impact', 'quarterly results',
        'annual report', 'profit margin', 'revenue growth', 'market share',
        'stock price', 'investor', 'funding round', 'private equity',
        'sells to', 'buys', 'purchase agreement', 'deal worth'
    ],
    'safety-incidents': [
        'ski patrol', 'avalanche', 'injured', 'fatality', 'fatal',
        'accident', 'lawsuit filed', 'rescue operation', 'emergency response',
        'collision', 'safety investigation', 'death at', 'died at'
    ],
    'weather-snow': [
        'snow forecast', 'snowfall total', 'la nina', 'la niña', 'el nino', 'el niño',
        'snowpack', 'drought', 'climate change', 'winter storm', 'powder day',
        'inches of snow', 'feet of snow', 'snow report', 'base depth',
        'atmospheric river', 'winter weather'
    ],
    'resort-operations': [
        'opening day', 'closes for', 'season opening', 'first chair', 'last chair',
        'new lift', 'new chairlift', 'gondola project', 'terrain expansion',
        'snowmaking system', 'lift upgrade', 'base lodge', 'summit lodge'
    ],
    'transportation': [
        'new flight', 'air service', 'nonstop to', 'airport expansion',
        'shuttle service', 'bus route', 'traffic on i-70', 'highway closure'
    ],
    'hospitality': [
        'hotel opens', 'lodging', 'room rates', 'occupancy rate', 'vacation rental',
        'ski-in ski-out', 'slopeside', 'resort hotel'
    ],
    'winter-sports': [
        'world cup', 'fis', 'olympic', 'slalom', 'giant slalom', 'downhill race',
        'freestyle', 'halfpipe', 'slopestyle', 'ski cross', 'podium'
    ],
    'canada': [
        'canadian ski', 'ski canada', 'canada west', 'british columbia ski',
        'alberta ski', 'quebec ski', 'ontario ski'
    ],
    'international': [
        'european alps', 'japanese ski', 'ski japan', 'australian ski',
        'new zealand ski', 'south american ski', 'global ski market'
    ],
    'ski-history': [
        'ski history', 'historic', 'anniversary', 'founded in', 'pioneer',
        'museum', 'heritage', 'abandoned ski area', 'defunct resort'
    ]
}

# Standard category keywords (used as secondary signal)
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
        'keywords': ['world cup ski', 'winter olympic', 'winter olympics', 'fis ski', 'fis alpine', 'ski race', 'ski racing',
                     'slalom', 'giant slalom', 'downhill race', 'super-g', 'alpine combined',
                     'ski championship', 'ski competition', 'ski athlete', 'ski podium', 'ski medal',
                     'x games ski', 'x games snow', 'dew tour', 'freestyle skiing', 'ski halfpipe', 'ski slopestyle',
                     'nordic skiing', 'cross-country skiing', 'biathlon', 'ski jumping', 'snowboard competition',
                     'snowboard race', 'snowboard championship']
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

# =============================================================================
# CONTEXTUAL PENALTY PATTERNS (Regex-based for precision)
# =============================================================================

# Only penalize when these patterns appear (not just single words)
PROMOTIONAL_PATTERNS = [
    (r'\bsave\s+\$?\d+', -5),                    # "Save $50"
    (r'\bdeal\s+ends?\b', -5),                   # "Deal ends soon"
    (r'\b(top|best)\s+\d+\s+(ski|resort|run)', -4),  # "Top 10 ski resorts"
    (r'\bgear\s+(guide|review)', -4),
    (r'\bbuying\s+guide\b', -4),
    (r'\bpromo\s*code\b', -5),
    (r'\btrip\s+report\b', -3),
    (r'\bpowder\s+alert\b', -3),
    (r'\b\d+%\s+off\b', -5),                     # "20% off"
    (r'\bstarting\s+at\s+\$', -4),               # "Starting at $"
    (r'\bbook\s+now\b', -5),
    (r'\bshop\s+now\b', -5),
    (r'\blimited\s+time\b', -4),
    (r'\bearly\s+bird\s+(deal|special|price)', -4),
]

# Don't penalize these (exceptions to above patterns)
PROMOTIONAL_EXCEPTIONS = [
    r'\bbest\s+(year|quarter|season|earnings|performance)',  # "Best year on record"
    r'\btop\s+(executive|ceo|management|official)',          # "Top executive leaves"
    r'\brecord\s+(revenue|profit|earnings|visits)',          # "Record revenue"
]

# =============================================================================
# CONSUMER CONTENT TYPE PENALTIES (Blocks enthusiast/consumer content)
# =============================================================================

# These patterns identify consumer-oriented content that should be excluded
# even if it mentions ski resorts. Score impact is severe (-6 to -10).
CONSUMER_CONTENT_PATTERNS = [
    # Athlete/competition content (unless major business news)
    (r'\b(pov|gopro|helmet\s*cam)\s+(video|footage|view)', -8),  # POV footage articles
    (r'\bfirst[- ]ever\s+(ski\s+)?descent', -6),      # First descent achievements
    (r'\b(pro|professional)\s+skier\b(?!.*\b(dies|killed|lawsuit|charged))', -5),  # Pro skier profiles (unless incident)
    (r'\bski\s+(athlete|racer)\s+(profile|interview|story)', -6),
    (r'\b(podium|medal|bronze|silver|gold)\s+(finish|winner)', -4),  # Competition results
    (r'\bwinning\s+run\b', -5),                       # Competition footage
    (r'\bworld\s+record\s+(holder|attempt)', -4),    # Records (unless business context)
    (r'\bfreeride\s+(tour|world|competition|championship)', -4),  # Freeride events
    (r'\bx[\s-]?games\b(?!.*\b(economic|revenue|sponsor|business))', -5),  # X Games (unless business angle)

    # Consumer guides and reviews
    (r'\bresort\s+review\b', -7),                     # Resort reviews
    (r'\bwhere\s+to\s+ski\b', -6),                   # Destination guides
    (r'\bhow\s+to\s+(ski|snowboard|use)', -6),       # How-to guides
    (r'\b(beginner|intermediate|expert)\s+guide', -5),
    (r'\bski\s+(tips|technique|lesson)', -5),        # Instruction content
    (r'\blearning\s+to\s+ski\b', -6),
    (r'\bfamily[- ]friendly\s+(resort|ski)', -4),    # Family destination content

    # Weather/conditions consumer content
    (r'\bpowder\s+(day|report|alert|stash)', -4),    # Powder reports
    (r'\bsnow\s+report\b', -4),                      # Snow reports (consumer focus)
    (r'\bski\s+conditions\s+(report|update)', -4),   # Conditions updates

    # Promotional/event content
    (r'\b(taste\s+of|culinary\s+experience|wine\s+(dinner|tasting))\b', -6),  # Food/wine events
    (r'\bsommelier\s+on\s+(the\s+)?slopes', -7),     # Promotional events
    (r'\bgets\s+ready\s+for\b', -5),                 # Promotional language
    (r'\b(spring|summer|fall)\s+skiing\b(?!.*\b(revenue|business|extend))', -4),  # Seasonal content

    # Safety/avalanche consumer content
    (r'\bavalanche\s+(bulletin|forecast|report)\b', -5),  # Avalanche bulletins
    (r'\bhow\s+to\s+(read|use|interpret)\s+avalanche', -6),  # How-to avalanche
    (r'\bwinter\s+(mountain\s+)?safety\s+guide\b', -6),  # Safety guides
    (r'\bbackcountry\s+(safety|tips|guide)', -5),    # Backcountry guides

    # Minor incidents (individual accidents, not industry-relevant unless systemic)
    (r'\b(skier|snowboarder)\s+(dies|killed|dead|found\s+dead)\b(?!.*\b(lawsuit|negligence|investigation|class\s+action))', -4),
    (r'\b(skier|snowboarder)\s+(injured|hurt|airlifted|hospitalized)\b(?!.*\b(lawsuit|negligence|investigation))', -5),
    (r'\b(trail|run|lift|chair)\s+closed\s+(due|after|following)\b(?!.*\b(permanently|season|investment))', -4),

    # Action/lifestyle content
    (r'\b(epic|insane|wild|crazy|gnarly)\s+(run|descent|footage|video)', -6),
    (r'\bwatch\s+(this|the)\s+(video|footage)', -5),
    (r'\bcheck\s+out\s+(this|the)', -4),
    (r'\bmust[- ]see\s+(video|footage)', -5),
]

# Exceptions for consumer patterns (allow through if business context present)
CONSUMER_CONTENT_EXCEPTIONS = [
    r'\b(acquisition|merger|investment|earnings|revenue|lawsuit|death|fatal|killed|dies)\b',
    r'\b(ceo|executive|board|shareholders|quarterly|annual\s+report)\b',
    r'\b(layoff|bankruptcy|closure|shut\s*down|sold|buys|purchase)\b',
    r'\b(labor|workforce|employee|hiring|staffing)\b',
    r'\b(economic\s+impact|tourism\s+revenue|visitor\s+spending)\b',
    r'\b(negligence|class\s+action|investigation|regulatory|osha|safety\s+record)\b',
]

# =============================================================================
# ANALYTICAL CONTENT BOOST PATTERNS
# =============================================================================
# Patterns that indicate quality, in-depth analysis (boost display score)
ANALYTICAL_CONTENT_PATTERNS = [
    # Industry-wide analysis
    (r'\bindustry(-|\s)wide\b', 4),
    (r'\btrend(s)?\s+(in|across|for)\b', 3),
    (r'\banalysis\s+of\b', 3),
    (r'\bstate\s+of\s+(the\s+)?industry\b', 5),
    (r'\bmarket\s+(analysis|outlook|forecast)\b', 4),
    (r'\beconomic\s+(impact|analysis|outlook)\b', 4),
    # Data-driven indicators
    (r'\bskier\s+visits?\b.*\b(up|down|grew|declined|percent)\b', 4),
    (r'\bvisitation\s+(data|numbers|statistics)\b', 4),
    (r'\bquarterly\s+(results|earnings|report)\b', 5),
    (r'\bannual\s+report\b', 4),
    (r'\bfinancial\s+(results|performance)\b', 4),
    # Long-form indicators
    (r'\bin-depth\s+(look|analysis|report)\b', 3),
    (r'\bcomprehensive\s+(look|analysis|report)\b', 3),
    (r'\bexamines?\s+(the|how|why)\b', 2),
    (r'\binvestigates?\s+(the|how|why)\b', 3),
    # Future-looking analysis
    (r'\bwhat\s+(this|it)\s+means\s+for\b', 3),
    (r'\bimplications\s+for\b', 3),
    (r'\boutlook\s+for\b', 3),
    (r'\bfuture\s+of\s+(skiing|the\s+ski\s+industry)\b', 4),
    # Major business events
    (r'\b(acquisition|merger)\s+(announced|completed|closes)\b', 5),
    (r'\b(earnings|revenue)\s+(beat|miss|exceed)\b', 4),
]

# Premium source names (for display score boost)
PREMIUM_ANALYTICAL_SOURCES = {
    'New York Times - Travel', 'New York Times - Business',
    'New York Times - Climate', 'New York Times - U.S.',
    'Wall Street Journal', 'Financial Times', 'Bloomberg Markets',
    'The Economist', 'Reuters Business', 'Washington Post',
    'Skift', 'Globe and Mail',
}

# =============================================================================
# DISPLAY SCORE ADJUSTMENTS
# =============================================================================
# These affect the order articles appear in the feed, not whether they're included.
# Safety/incident stories are important but shouldn't lead the feed.

# Categories that should appear lower in the feed (display penalty)
DISPLAY_DEMOTED_CATEGORIES = {
    'safety-incidents': -8,   # Routine incidents shouldn't dominate feed
    'winter-sports': -2,      # Competition results less relevant to business audience
}

# Consumer-oriented sources get display penalty (still in feed, just not leading)
# These sources produce good content but tend toward consumer rather than business focus
CONSUMER_ORIENTED_SOURCES = {
    'Unofficial Networks', 'SnowBrains', 'PlanetSKI', 'The Ski Guru',
    'Powder Magazine', 'Freeskier', 'SKI Magazine', 'Skiing Magazine',
}
CONSUMER_SOURCE_DISPLAY_PENALTY = -4

# =============================================================================
# RSS SOURCES (Including new sources from improvement spec)
# =============================================================================

RSS_SOURCES = [
    # PREMIUM ANALYTICAL SOURCES (highest priority - quality long-form analysis)
    # These are major publications known for in-depth industry analysis
    {
        'name': 'New York Times - Travel',
        'url': 'https://rss.nytimes.com/services/xml/rss/nyt/Travel.xml',
        'category': 'premium_analytical',
        'boost': 6
    },
    {
        'name': 'New York Times - Business',
        'url': 'https://rss.nytimes.com/services/xml/rss/nyt/Business.xml',
        'category': 'premium_analytical',
        'boost': 6
    },
    {
        'name': 'New York Times - Climate',
        'url': 'https://rss.nytimes.com/services/xml/rss/nyt/Climate.xml',
        'category': 'premium_analytical',
        'boost': 6
    },
    {
        'name': 'New York Times - U.S.',
        'url': 'https://rss.nytimes.com/services/xml/rss/nyt/US.xml',
        'category': 'premium_analytical',
        'boost': 6
    },
    # WSJ doesn't have a free RSS feed - use Google News to find WSJ ski coverage
    {
        'name': 'Google News - WSJ Ski',
        'url': 'https://news.google.com/rss/search?q=site:wsj.com+ski+OR+skiing+OR+ski+resort&hl=en-US&gl=US&ceid=US:en',
        'category': 'premium_analytical',
        'boost': 6
    },
    {
        'name': 'Reuters Business',
        'url': 'https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best',
        'category': 'major_publication',
        'boost': 5
    },
    {
        'name': 'Washington Post',
        'url': 'https://feeds.washingtonpost.com/rss/business',
        'category': 'major_publication',
        'boost': 5
    },
    {
        'name': 'The Atlantic',
        'url': 'https://www.theatlantic.com/feed/all/',
        'category': 'major_publication',
        'boost': 5
    },
    {
        'name': 'Financial Times',
        'url': 'https://www.ft.com/rss/home',
        'category': 'premium_analytical',
        'boost': 6
    },
    {
        'name': 'Associated Press - Top News',
        'url': 'https://feedx.net/rss/ap.xml',
        'category': 'major_publication',
        'boost': 4
    },
    {
        'name': 'Bloomberg Markets',
        'url': 'https://feeds.bloomberg.com/markets/news.rss',
        'category': 'premium_analytical',
        'boost': 6
    },
    {
        'name': 'Christian Science Monitor',
        'url': 'https://rss.csmonitor.com/feeds/all',
        'category': 'major_publication',
        'boost': 4
    },
    # Google News Aggregators
    {
        'name': 'Google News - Ski Industry',
        'url': 'https://news.google.com/rss/search?q=ski+resort+business+OR+ski+industry&hl=en-US&gl=US&ceid=US:en',
        'category': 'aggregator',
        'boost': 1
    },
    {
        'name': 'Google News - Vail Alterra Ski',
        'url': 'https://news.google.com/rss/search?q=Vail+Resorts+OR+Alterra+Mountain+ski&hl=en-US&gl=US&ceid=US:en',
        'category': 'aggregator',
        'boost': 2
    },
    {
        'name': 'Google News - Ski Resort Business',
        'url': 'https://news.google.com/rss/search?q="ski+resort"+business+OR+investment+OR+acquisition&hl=en-US&gl=US&ceid=US:en',
        'category': 'aggregator',
        'boost': 2
    },
    {
        'name': 'Google News - Ski Pass Prices',
        'url': 'https://news.google.com/rss/search?q=ski+pass+price+OR+Epic+Pass+OR+Ikon+Pass&hl=en-US&gl=US&ceid=US:en',
        'category': 'aggregator',
        'boost': 1
    },
    {
        'name': 'Google News - 2026 Winter Olympics Ski',
        'url': 'https://news.google.com/rss/search?q=2026+Winter+Olympics+Milan+Cortina+skiing&hl=en-US&gl=US&ceid=US:en',
        'category': 'aggregator',
        'boost': 1
    },
    {
        'name': 'Google News - Ropeways & Lifts',
        'url': 'https://news.google.com/rss/search?q=site:ropeways.net+OR+chairlift+installation+OR+gondola+project+OR+ski+lift+construction&hl=en-US&gl=US&ceid=US:en',
        'category': 'industry',
        'boost': 2
    },
    # Canadian sources
    {
        'name': 'Globe and Mail - Business',
        'url': 'https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/business/',
        'category': 'canadian_publication',
        'boost': 3
    },
    {
        'name': 'CBC News - Business',
        'url': 'https://www.cbc.ca/webfeed/rss/rss-business',
        'category': 'canadian_publication',
        'boost': 2
    },
    {
        'name': 'Google News - Canada Ski Industry',
        'url': 'https://news.google.com/rss/search?q=canada+ski+resort+OR+whistler+OR+banff+skiing&hl=en-CA&gl=CA&ceid=CA:en',
        'category': 'canadian_industry',
        'boost': 2
    },
    # Industry publications
    {
        'name': 'Outside Business Journal',
        'url': 'https://www.outsidebusinessjournal.com/feed/',
        'category': 'business',
        'boost': 2
    },
    {
        'name': 'SIA - Snowsports Industries America',
        'url': 'https://snowsports.org/feed/',
        'category': 'industry',
        'boost': 2
    },
    {
        'name': 'Snow Industry News',
        'url': 'https://www.snowindustrynews.com/rss',
        'category': 'industry',
        'boost': 2
    },
    {
        'name': 'Ski Area Management',
        'url': 'https://www.saminfo.com/headline-news?format=feed&type=rss',
        'category': 'industry',
        'boost': 2
    },
    # Ski news sites (consumer-oriented - reduced boost, content penalties apply)
    {
        'name': 'Unofficial Networks',
        'url': 'https://unofficialnetworks.com/feed/',
        'category': 'consumer_news',
        'boost': 0  # Reduced: high volume of consumer/athlete content
    },
    {
        'name': 'SnowBrains',
        'url': 'https://snowbrains.com/feed/',
        'category': 'consumer_news',
        'boost': 0  # Reduced: mixes business with consumer content
    },
    # European/International (consumer-focused)
    {
        'name': 'PlanetSKI',
        'url': 'https://planetski.eu/feed/',
        'category': 'consumer_international',
        'boost': 0  # Reduced: mostly resort reviews and consumer content
    },
    {
        'name': 'The Ski Guru',
        'url': 'https://www.the-ski-guru.com/feed/',
        'category': 'consumer_international',
        'boost': 0  # Reduced: safety guides, resort reviews, consumer content
    },
    # Mountain community newspapers
    {
        'name': 'Summit Daily News',
        'url': 'https://www.summitdaily.com/feed/',
        'category': 'local',
        'boost': 1
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
        'boost': 1
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
        'boost': 0
    },
    # Environmental/Western news
    {
        'name': 'High Country News',
        'url': 'https://www.hcn.org/feed/',
        'category': 'environment',
        'boost': 1
    },
    # Ski history
    {
        'name': 'International Skiing History Association',
        'url': 'https://www.skiinghistory.org/feed',
        'category': 'history',
        'boost': 1
    },
    # Local TV
    {
        'name': 'Denver7',
        'url': 'https://www.denver7.com/news/local-news.rss',
        'category': 'local_news',
        'boost': 1
    },
    # Hospitality
    {
        'name': 'CoStar Hotels',
        'url': 'https://www.costar.com/rss/news/hotels',
        'category': 'hospitality',
        'boost': 2
    },
    # Government statistics
    {
        'name': 'U.S. Census Bureau',
        'url': 'https://www.census.gov/economic-indicators/indicator.xml',
        'category': 'government',
        'boost': 3
    },
    {
        'name': 'Statistics Canada - Travel & Tourism',
        'url': 'https://www150.statcan.gc.ca/n1/dai-quo/ssi/homepage-eng.xml',
        'category': 'government',
        'boost': 3
    },
    # NEW SOURCES FROM IMPROVEMENT SPEC
    # Financial news - Vail Resorts stock (MTN)
    {
        'name': 'Google Finance - Vail Resorts MTN',
        'url': 'https://news.google.com/rss/search?q=MTN+stock+Vail+Resorts+earnings&hl=en-US&gl=US&ceid=US:en',
        'category': 'financial',
        'boost': 2
    },
    # Canadian business
    {
        'name': 'BIV - Tourism',
        'url': 'https://biv.com/topic/tourism/feed',
        'category': 'canadian',
        'boost': 2
    },
    # DIRECT COMPANY INVESTOR RELATIONS FEEDS
    {
        'name': 'Vail Resorts Investor Relations',
        'url': 'https://investors.vailresorts.com/rss/news-releases.xml',
        'category': 'financial',
        'boost': 5  # High priority - official company news
    },
    {
        'name': 'Google News - Alterra Mountain Company',
        'url': 'https://news.google.com/rss/search?q=%22Alterra+Mountain+Company%22&hl=en-US&gl=US&ceid=US:en',
        'category': 'financial',
        'boost': 3
    },
    # Ski conditions and season coverage (mainstream news)
    {
        'name': 'Google News - Ski Season Conditions',
        'url': 'https://news.google.com/rss/search?q=ski+season+conditions+OR+ski+conditions+snow&hl=en-US&gl=US&ceid=US:en',
        'category': 'aggregator',
        'boost': 2
    },
    {
        'name': 'Google News - Ski Resort Snow Drought',
        'url': 'https://news.google.com/rss/search?q=ski+resort+snow+drought+OR+ski+resort+lack+snow+OR+ski+season+warm&hl=en-US&gl=US&ceid=US:en',
        'category': 'aggregator',
        'boost': 2
    },
    {
        'name': 'Google News - Ski Industry Climate',
        'url': 'https://news.google.com/rss/search?q=ski+industry+climate+OR+ski+resort+climate+change+OR+skiing+warming&hl=en-US&gl=US&ceid=US:en',
        'category': 'aggregator',
        'boost': 2
    },
    # ==========================================================================
    # BUSINESS-FOCUSED TRAVEL/HOSPITALITY SOURCES (high priority)
    # ==========================================================================
    {
        'name': 'Skift',
        'url': 'https://skift.com/feed/',
        'category': 'travel_business',
        'boost': 4  # High boost - premier travel industry analysis
    },
    {
        'name': 'PhocusWire',
        'url': 'https://www.phocuswire.com/rss.xml',
        'category': 'travel_business',
        'boost': 3  # Travel technology and business news
    },
    {
        'name': 'Hospitality Net',
        'url': 'https://www.hospitalitynet.org/rss/news.html',
        'category': 'hospitality_business',
        'boost': 3
    },
    {
        'name': 'Hotel News Now',
        'url': 'https://www.hotelnewsnow.com/rss',
        'category': 'hospitality_business',
        'boost': 3
    },
    # Labor/workforce news (important for resort operators)
    {
        'name': 'Google News - Ski Resort Labor',
        'url': 'https://news.google.com/rss/search?q=ski+resort+worker+OR+ski+resort+employee+OR+ski+resort+staffing+OR+seasonal+worker+visa&hl=en-US&gl=US&ceid=US:en',
        'category': 'labor',
        'boost': 3
    },
    {
        'name': 'Google News - H-2B Visa Seasonal',
        'url': 'https://news.google.com/rss/search?q=H-2B+visa+seasonal+worker+OR+J-1+visa+ski&hl=en-US&gl=US&ceid=US:en',
        'category': 'labor',
        'boost': 3
    },
    # Real estate in resort markets
    {
        'name': 'Google News - Ski Town Real Estate',
        'url': 'https://news.google.com/rss/search?q="ski+town"+OR+"mountain+town"+real+estate+OR+housing+market&hl=en-US&gl=US&ceid=US:en',
        'category': 'real_estate',
        'boost': 2
    },
    # Airport/air service (critical for destination resorts)
    {
        'name': 'Google News - Mountain Airport Service',
        'url': 'https://news.google.com/rss/search?q=Vail+Eagle+airport+OR+Jackson+Hole+airport+OR+Aspen+airport+OR+Bozeman+airport+air+service&hl=en-US&gl=US&ceid=US:en',
        'category': 'transportation',
        'boost': 3
    },
    # Ski industry lawsuits and legal
    {
        'name': 'Google News - Ski Resort Lawsuit',
        'url': 'https://news.google.com/rss/search?q=ski+resort+lawsuit+OR+ski+area+lawsuit+OR+ski+resort+liability&hl=en-US&gl=US&ceid=US:en',
        'category': 'legal',
        'boost': 3
    },
    # Climate/sustainability business angle
    {
        'name': 'Google News - Ski Industry Sustainability',
        'url': 'https://news.google.com/rss/search?q=ski+resort+sustainability+OR+ski+industry+carbon+OR+ski+resort+renewable+energy&hl=en-US&gl=US&ceid=US:en',
        'category': 'sustainability',
        'boost': 2
    },
    # Major business news with ski focus
    {
        'name': 'Google News - Ski Business Deals',
        'url': 'https://news.google.com/rss/search?q="ski+resort"+acquisition+OR+"ski+area"+merger+OR+"ski+resort"+sold+OR+"ski+resort"+bankruptcy&hl=en-US&gl=US&ceid=US:en',
        'category': 'business',
        'boost': 4  # High priority - M&A news
    },
]

# Source health tracking (populated during run)
SOURCE_HEALTH = {}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def print_safe(msg):
    """Print with safe encoding for Windows"""
    try:
        print(msg)
    except:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def parse_date(date_str):
    """Parse various date formats to ISO format for consistent sorting."""
    if not date_str:
        return ''

    # Already ISO format
    if re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
        return date_str[:10]

    # RFC 2822 format: "Thu, 15 Jan 2026 08:00:00 -0500"
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.strftime('%Y-%m-%d')
    except:
        pass

    # Try common formats
    for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S', '%B %d, %Y', '%d %b %Y']:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime('%Y-%m-%d')
        except:
            continue

    return date_str  # Return original if parsing fails


def fetch_url(url, timeout=30):
    """Fetch content from URL"""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode('utf-8', errors='replace')
    except Exception as e:
        # Track failed sources
        SOURCE_HEALTH[url] = {'status': 'failed', 'error': str(e)[:100]}
        return None


def clean_html(text):
    """Remove HTML tags and clean text"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def fetch_ropeways_net():
    """
    Scrape ropeways.net media clipping page for ski lift/ropeway industry news.
    Returns list of articles in same format as RSS parser.
    """
    url = 'https://ropeways.net/rn/medienclipping/medienclipping.php?nav=2'
    articles = []

    try:
        content = fetch_url(url)
        if not content:
            return articles

        # Extract articles using regex patterns
        # Pattern: date (YYYY-MM-DD) followed by title and source in anchor tags
        # The page has format: <a href="...">TITLE</a> (SOURCE) DATE
        # or variations thereof

        # Find all anchor tags with their surrounding context
        # Pattern looks for: <a href="URL">TITLE</a> with nearby date and source
        link_pattern = re.compile(
            r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>\s*(?:\(([^)]+)\))?\s*(\d{4}-\d{2}-\d{2})?',
            re.IGNORECASE
        )

        # Also try alternate pattern where date comes first
        date_first_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2})\s*<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>\s*(?:\(([^)]+)\))?',
            re.IGNORECASE
        )

        # Categories of interest (filter to ski-relevant)
        ski_relevant_categories = ['ropeways', 'snowmaking', 'slopes', 'economy', 'tourism']

        found_links = set()

        # Try date-first pattern
        for match in date_first_pattern.finditer(content):
            date, link, title, source = match.groups()
            if link in found_links:
                continue
            found_links.add(link)

            # Skip non-ski categories
            link_lower = link.lower()
            if not any(cat in link_lower or cat in title.lower() for cat in ski_relevant_categories):
                # Check if link contains ski-related terms
                combined = f"{title} {source or ''}".lower()
                if not any(term in combined for term in ['ski', 'lift', 'gondola', 'cable', 'resort', 'mountain', 'snow']):
                    continue

            article = {
                'source': 'Ropeways.net',
                'title': clean_html(title).strip(),
                'url': link if link.startswith('http') else f'https://ropeways.net{link}',
                'pub_date': date,
                'description': f"From {source.strip()}" if source else "Industry news from Ropeways.net",
                'id': hashlib.md5(link.encode()).hexdigest()[:12]
            }
            articles.append(article)

        # Try link-first pattern for remaining
        for match in link_pattern.finditer(content):
            link, title, source, date = match.groups()
            if link in found_links:
                continue
            found_links.add(link)

            # Skip navigation links and non-article links
            if 'medienclipping1.php' in link or 'nav=' in link:
                continue

            # Filter to ski-relevant
            combined = f"{title} {source or ''}".lower()
            if not any(term in combined for term in ['ski', 'lift', 'gondola', 'cable', 'resort', 'mountain', 'snow', 'ropeway']):
                continue

            article = {
                'source': 'Ropeways.net',
                'title': clean_html(title).strip(),
                'url': link if link.startswith('http') else f'https://ropeways.net{link}',
                'pub_date': date or datetime.now().strftime('%Y-%m-%d'),
                'description': f"From {source.strip()}" if source else "Industry news from Ropeways.net",
                'id': hashlib.md5(link.encode()).hexdigest()[:12]
            }
            articles.append(article)

        print_safe(f"  Scraped {len(articles)} articles from Ropeways.net")
        SOURCE_HEALTH['Ropeways.net (HTML)'] = {'status': 'ok', 'articles': len(articles)}

    except Exception as e:
        print_safe(f"  ! Error scraping Ropeways.net: {e}")
        SOURCE_HEALTH['Ropeways.net (HTML)'] = {'status': 'failed', 'error': str(e)[:100]}

    return articles


def parse_rss_feed(xml_content, source_name):
    """Parse RSS feed and extract articles"""
    articles = []
    try:
        root = ET.fromstring(xml_content)
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
                article['pub_date'] = parse_date(pub_date.text)

            # Generate unique ID
            if article.get('url'):
                article['id'] = hashlib.md5(article['url'].encode()).hexdigest()[:12]
                articles.append(article)

    except ET.ParseError as e:
        print_safe(f"  ! XML parse error for {source_name}: {e}")
    except Exception as e:
        print_safe(f"  ! Error parsing {source_name}: {e}")

    return articles


# =============================================================================
# STRICT PRE-FILTER (Improvement: Two-tier system)
# =============================================================================

def strict_prefilter(article):
    """
    Three-tier pre-filter with macro relevance pathway and major source whitelist.
    Returns (passed, business_score, is_macro) tuple.

    Primary pathway: Must have explicit ski industry reference (PRIMARY_SKI_TERMS)
    Resort pathway: Resort name + business context (not just consumer content)
    Macro pathway: Macro relevance term + mountain region geography
    Whitelist pathway: Trusted sources get relaxed filtering
    """
    text = f"{article.get('title', '')} {article.get('description', '')}".lower()
    source = article.get('source', '')
    is_whitelisted = source in WHITELIST_SOURCES

    # Gate 1: Check for explicit ski industry reference (primary pathway)
    has_ski_term = any(term in text for term in PRIMARY_SKI_TERMS)

    if has_ski_term:
        # Primary pathway passed - count business context terms
        business_count = sum(1 for term in SECONDARY_BUSINESS_TERMS if term in text)
        return True, business_count, False

    # Gate 1.5: Resort name + business context pathway
    # Allows resort-specific articles only if they have business relevance
    has_resort_name = any(resort in text for resort in RESORT_NAME_CONTEXT_REQUIRED)
    has_business_context = any(term in text for term in SECONDARY_BUSINESS_TERMS)

    if has_resort_name and has_business_context:
        business_count = sum(1 for term in SECONDARY_BUSINESS_TERMS if term in text)
        return True, business_count, False

    # Gate 2: Check macro relevance pathway (secondary)
    # Requires BOTH a macro term AND a mountain region term
    has_macro_term = any(term in text for term in MACRO_RELEVANCE_TERMS)
    has_region_term = any(term in text for term in MOUNTAIN_REGION_TERMS)

    if has_macro_term and has_region_term:
        # Macro pathway passed - these get lower priority during sorting
        business_count = sum(1 for term in SECONDARY_BUSINESS_TERMS if term in text)
        return True, business_count, True  # True = is_macro (lower priority)

    # Gate 3: Whitelisted sources get relaxed filtering
    # They only need a macro term OR a region term (not both)
    if is_whitelisted and (has_macro_term or has_region_term):
        business_count = sum(1 for term in SECONDARY_BUSINESS_TERMS if term in text)
        return True, business_count, True  # Treated as macro (lower priority but included)

    return False, 0, False


# =============================================================================
# STORY DEDUPLICATION (Improvement: Prevents duplicate stories across sources)
# =============================================================================

def normalize_title(title):
    """Extract key terms for fuzzy matching."""
    stop_words = {'the', 'a', 'an', 'to', 'for', 'of', 'in', 'on', 'at', 'by', 'is', 'are', 'was', 'were'}
    words = re.findall(r'\b[a-z]+\b', title.lower())
    key_words = [w for w in words if w not in stop_words and len(w) > 2]
    return ' '.join(sorted(key_words[:8]))  # First 8 significant words, sorted


def get_lead_paragraph(article):
    """Extract first ~100 chars of description for lead paragraph comparison."""
    desc = article.get('description', '') or article.get('content', '')
    # Normalize whitespace and truncate
    lead = ' '.join(desc.split())[:100].lower()
    return lead


def _strip_source_suffix(title):
    """Strip ' - Source Name' suffix commonly added by aggregators like Google News."""
    # Match ' - Source' at end of title (where Source is 1-5 words)
    return re.sub(r'\s*-\s+[\w\s&\']{2,40}$', '', title)


def deduplicate_articles(articles, similarity_threshold=0.85):
    """
    Group articles by title similarity, keep highest-scored from each group.
    Uses normalized title matching, fuzzy matching, and lead paragraph comparison.
    """
    if not articles:
        return []

    # First pass: group by normalized title
    groups = defaultdict(list)
    for article in articles:
        key = normalize_title(article.get('title', ''))
        groups[key].append(article)

    unique_articles = []
    processed_keys = set()

    # Sort groups by best score in group
    sorted_groups = sorted(
        groups.items(),
        key=lambda x: max(a.get('score', 0) for a in x[1]),
        reverse=True
    )

    for key, group in sorted_groups:
        if key in processed_keys:
            continue

        # Get best article from this group
        best = max(group, key=lambda x: (x.get('score', 0), x.get('source_boost', 0)))

        # Record other sources if duplicates exist
        if len(group) > 1:
            best['other_sources'] = [
                {'source': a['source'], 'url': a['url']}
                for a in group if a['url'] != best['url']
            ]

        # Check for fuzzy matches against already-selected articles
        is_duplicate = False
        best_title = best.get('title', '').lower()
        best_title_stripped = _strip_source_suffix(best_title)
        best_lead = get_lead_paragraph(best)

        for existing in unique_articles:
            existing_title = existing.get('title', '').lower()
            existing_title_stripped = _strip_source_suffix(existing_title)
            existing_lead = get_lead_paragraph(existing)

            # Check title similarity (both raw and with source suffix stripped)
            title_similarity = difflib.SequenceMatcher(None, best_title, existing_title).ratio()
            stripped_similarity = difflib.SequenceMatcher(None, best_title_stripped, existing_title_stripped).ratio()
            effective_title_sim = max(title_similarity, stripped_similarity)

            # Check lead paragraph similarity (catches same story with different headlines)
            lead_similarity = difflib.SequenceMatcher(None, best_lead, existing_lead).ratio() if best_lead and existing_lead else 0

            # Consider duplicate if either title or lead paragraph is very similar
            if effective_title_sim >= similarity_threshold or (lead_similarity >= 0.80 and len(best_lead) > 50):
                is_duplicate = True
                # Add to existing article's other sources
                if 'other_sources' not in existing:
                    existing['other_sources'] = []
                existing['other_sources'].append({
                    'source': best['source'],
                    'url': best['url']
                })
                break

        if not is_duplicate:
            unique_articles.append(best)

        processed_keys.add(key)

    return unique_articles


def deduplicate_against_existing(new_articles, existing_articles, similarity_threshold=0.85):
    """
    Filter out new articles that are duplicates of recently published articles.
    This prevents old topics from reappearing when a new source covers the same story.

    Args:
        new_articles: List of newly fetched articles
        existing_articles: Dict of existing articles (id -> article)
        similarity_threshold: Minimum similarity to consider duplicate

    Returns:
        List of articles that are NOT duplicates of existing content
    """
    if not new_articles or not existing_articles:
        return new_articles

    # Only compare against recent articles (within expiration window)
    cutoff_date = (datetime.now() - timedelta(days=MAX_ARTICLE_AGE_DAYS)).strftime('%Y-%m-%d')
    recent_existing = [
        a for a in existing_articles.values()
        if a.get('pub_date', a.get('approved_date', '')) >= cutoff_date
    ]

    if not recent_existing:
        return new_articles

    filtered = []
    duplicates_found = 0

    for article in new_articles:
        article_title = article.get('title', '').lower()
        article_lead = get_lead_paragraph(article)
        is_duplicate = False

        article_title_stripped = _strip_source_suffix(article_title)

        for existing in recent_existing:
            existing_title = existing.get('title', '').lower()
            existing_title_stripped = _strip_source_suffix(existing_title)
            existing_lead = get_lead_paragraph(existing)

            # Check title similarity (both raw and with source suffix stripped)
            title_similarity = difflib.SequenceMatcher(None, article_title, existing_title).ratio()
            stripped_similarity = difflib.SequenceMatcher(None, article_title_stripped, existing_title_stripped).ratio()
            effective_title_sim = max(title_similarity, stripped_similarity)

            # Check lead paragraph similarity
            lead_similarity = 0
            if article_lead and existing_lead and len(article_lead) > 50:
                lead_similarity = difflib.SequenceMatcher(None, article_lead, existing_lead).ratio()

            # Consider duplicate if title or lead is very similar
            if effective_title_sim >= similarity_threshold or lead_similarity >= 0.80:
                is_duplicate = True
                duplicates_found += 1
                break

        if not is_duplicate:
            filtered.append(article)

    if duplicates_found > 0:
        print_safe(f"  Historical dedup: filtered {duplicates_found} articles matching recent feed")

    return filtered


def filter_expired_articles(articles, max_age_days=MAX_ARTICLE_AGE_DAYS):
    """
    Remove articles older than the maximum age.

    Args:
        articles: List of articles
        max_age_days: Maximum age in days

    Returns:
        List of articles within the age limit
    """
    cutoff_date = (datetime.now() - timedelta(days=max_age_days)).strftime('%Y-%m-%d')

    filtered = []
    expired_count = 0

    for article in articles:
        pub_date = article.get('pub_date', article.get('approved_date', ''))
        if pub_date >= cutoff_date:
            filtered.append(article)
        else:
            expired_count += 1

    if expired_count > 0:
        print_safe(f"  Expired {expired_count} articles older than {max_age_days} days")

    return filtered


# =============================================================================
# CONTEXTUAL PENALTY SCORING (Improvement: Regex-based precision)
# =============================================================================

def apply_contextual_penalties(text, title):
    """Apply penalties for promotional and consumer content."""
    penalty = 0
    text_lower = text.lower()
    title_lower = title.lower()
    combined_text = f"{title_lower} {text_lower}"

    # Apply promotional content penalties
    for pattern, points in PROMOTIONAL_PATTERNS:
        # Check in title first (stronger penalty could be applied)
        if re.search(pattern, title_lower, re.IGNORECASE):
            # Check exceptions
            is_exception = any(
                re.search(exc, text_lower, re.IGNORECASE)
                for exc in PROMOTIONAL_EXCEPTIONS
            )
            if not is_exception:
                penalty += points
                continue

        # Check in full text
        if re.search(pattern, text_lower, re.IGNORECASE):
            is_exception = any(
                re.search(exc, text_lower, re.IGNORECASE)
                for exc in PROMOTIONAL_EXCEPTIONS
            )
            if not is_exception:
                penalty += points // 2  # Lower penalty for body matches

    # Apply consumer content penalties (more severe)
    for pattern, points in CONSUMER_CONTENT_PATTERNS:
        if re.search(pattern, combined_text, re.IGNORECASE):
            # Check if business context exception applies
            has_business_context = any(
                re.search(exc, combined_text, re.IGNORECASE)
                for exc in CONSUMER_CONTENT_EXCEPTIONS
            )
            if not has_business_context:
                # Title matches get full penalty, body gets reduced
                if re.search(pattern, title_lower, re.IGNORECASE):
                    penalty += points
                else:
                    penalty += points // 2

    return penalty


# =============================================================================
# CATEGORY ASSIGNMENT V2 (Improvement: Priority system with phrase matching)
# =============================================================================

def assign_categories_v2(article, llm_suggested_category=None):
    """
    Improved category assignment with phrase matching and priority.
    If LLM provides category, validate it; otherwise use rules.
    """
    text = f"{article.get('title', '')} {article.get('description', '')} {article.get('content', '')}".lower()
    title = article.get('title', '').lower()

    scores = {cat: 0 for cat in CATEGORY_PRIORITY}

    # Phase 1: Phrase matching (high confidence)
    for cat, phrases in CATEGORY_PHRASES.items():
        for phrase in phrases:
            if phrase in title:
                scores[cat] += 8  # Very high weight for title phrase match
            elif phrase in text:
                scores[cat] += 5  # High weight for body phrase match

    # Phase 2: Single keyword matching (lower weight)
    for cat, info in ARTICLE_CATEGORIES.items():
        for keyword in info['keywords']:
            kw_lower = keyword.lower()
            if kw_lower in title:
                scores[cat] += 3
            elif kw_lower in text:
                scores[cat] += 1

    # Apply priority tiebreaker
    def score_with_priority(cat):
        return (scores[cat], CATEGORY_PRIORITY.get(cat, 0))

    ranked = sorted(scores.keys(), key=score_with_priority, reverse=True)

    primary = ranked[0] if scores[ranked[0]] > 0 else 'resort-operations'
    secondary = [c for c in ranked[1:4] if scores[c] > 0 and c != primary]

    # If LLM suggested a category and it scored non-zero, consider it
    if llm_suggested_category and llm_suggested_category in scores:
        if scores.get(llm_suggested_category, 0) > 0:
            if llm_suggested_category != primary:
                # Move LLM suggestion to primary if it has decent score
                if scores[llm_suggested_category] >= scores[primary] * 0.5:
                    secondary = [primary] + [s for s in secondary if s != llm_suggested_category][:2]
                    primary = llm_suggested_category

    return primary, secondary


# =============================================================================
# SCORING FUNCTIONS
# =============================================================================

def basic_keyword_score(article):
    """Score article using improved keyword analysis with contextual penalties."""
    text = f"{article.get('title', '')} {article.get('description', '')} {article.get('content', '')}".lower()
    title = article.get('title', '').lower()

    # Use strict pre-filter check
    passed_prefilter, business_boost, is_macro = strict_prefilter(article)

    if not passed_prefilter:
        return 2, {"reason": "No ski industry relevance detected", "method": "keyword"}

    # Base score: lower for macro relevance pathway articles
    score = 4 if is_macro else 5

    # Add business term boost from pre-filter
    score += min(business_boost, 3)  # Cap at +3

    # HIGH PRIORITY: Phrase-based boosts (stronger signals)
    for cat, phrases in CATEGORY_PHRASES.items():
        for phrase in phrases:
            if phrase in title:
                score += 3
            elif phrase in text:
                score += 2

    # MEDIUM PRIORITY: Single keyword boosts
    business_keywords = ['acquisition', 'merger', 'investment', 'earnings', 'revenue',
                        'profit', 'bankruptcy', 'layoff', 'ceo', 'executive', 'quarterly']
    for kw in business_keywords:
        if kw in title:
            score += 2
        elif kw in text:
            score += 1

    # Weather/climate boost
    weather_keywords = ['snowfall', 'snow forecast', 'snowpack', 'la nina', 'el nino',
                       'climate change', 'record snow', 'winter storm']
    for kw in weather_keywords:
        if kw in text:
            score += 2
            break

    # Canadian/International boost
    if any(kw in text for kw in ['canada', 'canadian', 'whistler', 'banff', 'british columbia']):
        score += 2
    if any(kw in text for kw in ['europe', 'european', 'alps', 'japan', 'australia']):
        score += 1

    # Apply contextual penalties (regex-based)
    penalty = apply_contextual_penalties(text, title)
    score += penalty  # penalties are negative

    # Additional simple penalties for obvious fluff
    fluff_indicators = [
        'trip report', 'gear review', 'gift guide', 'bucket list',
        'must-visit', 'hidden gem', 'ultimate guide', 'complete guide',
        'best places to', 'where to ski', 'resort guide', 'destination guide',
        'ski vacation', 'family vacation', 'weekend getaway',
        'things to do', 'what to pack', 'packing list', 'travel tips',
    ]
    for indicator in fluff_indicators:
        if indicator in text:
            score -= 3
            break

    # Consumer-focused content penalties
    consumer_patterns = [
        'first descent', 'pov footage', 'gopro video', 'helmet cam',
        'pro skier', 'professional skier', 'ski athlete',
        'watch this', 'check out', 'epic run', 'insane footage',
        'spring skiing', 'powder day', 'bluebird day',
        'apres ski', 'après-ski', 'ski fashion', 'ski style',
    ]
    for pattern in consumer_patterns:
        if pattern in text:
            score -= 4
            break

    # Off-topic penalties
    offtopic = [
        'tick', 'mosquito', 'lyme disease', 'hiking trail', 'mountain bike',
        'summer hike', 'camping', 'kayak', 'rafting', 'rock climbing',
        'golf course', 'tennis', 'fishing', 'hunting',
    ]
    for kw in offtopic:
        if kw in text:
            score -= 4
            break

    # Minor incident penalty - routine accidents and closures aren't business news
    # unless they involve a lawsuit, major investigation, or systemic safety issue
    minor_incident_terms = [
        'injured skier', 'injured snowboarder', 'ski accident', 'snowboard accident',
        'tree well', 'out of bounds', 'off-piste', 'lost skier',
        'trail closed', 'run closed', 'lift closed', 'chairlift evacuation',
        'chair evacuation', 'stuck on lift', 'stranded on lift',
        'caught in avalanche', 'buried in avalanche', 'avalanche victim',
        'skier dies', 'snowboarder dies', 'skier killed', 'snowboarder killed',
        'skier death', 'snowboarder death', 'fatal ski', 'fatal snowboard',
        'collision on', 'crash on slope', 'helmet cam crash',
    ]
    # Only penalize if no systemic/business angle
    systemic_safety_terms = [
        'lawsuit', 'litigation', 'negligence', 'investigation', 'osha',
        'safety record', 'safety review', 'pattern of', 'systemic',
        'policy change', 'insurance', 'liability', 'class action',
        'regulatory', 'fine', 'penalty', 'settlement',
    ]
    has_minor_incident = any(term in text for term in minor_incident_terms)
    has_systemic_angle = any(term in text for term in systemic_safety_terms)
    if has_minor_incident and not has_systemic_angle:
        score -= 3

    # Dashboard indicator boost - articles about metrics we track get a relevance bump
    dashboard_indicators = {
        # Economic indicators tracked on dashboard
        'consumer confidence': 2, 'consumer sentiment': 2, 'consumer spending': 2,
        'personal savings rate': 2, 'discretionary spending': 2,
        'inflation rate': 2, 'cpi': 2, 'consumer price index': 2,
        'unemployment rate': 2, 'jobs report': 2, 'nonfarm payrolls': 2,
        'wage growth': 2, 'interest rate': 2, 'federal reserve': 2,
        'rate cut': 2, 'rate hike': 2, 'gdp growth': 2, 'recession': 2,
        # Energy/commodity indicators
        'oil price': 2, 'crude oil': 2, 'gasoline price': 2, 'gas prices': 2,
        'natural gas price': 2, 'energy prices': 2,
        # Market indicators
        'stock market': 1, 's&p 500': 1, 'sp 500': 1,
        # Currency indicators
        'exchange rate': 2, 'strong dollar': 2, 'weak dollar': 2, 'canadian dollar': 2,
    }
    dashboard_boost = 0
    for indicator, boost_val in dashboard_indicators.items():
        if indicator in title:
            dashboard_boost = max(dashboard_boost, boost_val + 1)  # Title match gets extra
        elif indicator in text:
            dashboard_boost = max(dashboard_boost, boost_val)
    if dashboard_boost > 0:
        score += dashboard_boost
        article['dashboard_indicator_boost'] = dashboard_boost

    # Source boost
    source_boost = 0
    for src in RSS_SOURCES:
        if src['name'] == article.get('source'):
            source_boost = src.get('boost', 0)
            article['source_boost'] = source_boost
            break
    score += source_boost

    # Focus topic boost - from config file
    focus_boost = 0
    if FOCUS_TOPICS:
        for topic, boost_value in FOCUS_TOPICS.items():
            topic_lower = topic.lower()
            if topic_lower in title:
                focus_boost = max(focus_boost, boost_value + 1)  # Title match gets +1
            elif topic_lower in text:
                focus_boost = max(focus_boost, boost_value)
        if focus_boost > 0:
            score += focus_boost
            article['focus_topic_boost'] = focus_boost

    reason = f"Keyword scoring (source: +{source_boost}"
    if focus_boost > 0:
        reason += f", focus: +{focus_boost}"
    reason += ")"

    return max(1, min(10, score)), {"reason": reason, "method": "keyword"}


def score_with_llm(article):
    """Score article using Claude API with optimized prompt."""
    if not ANTHROPIC_API_KEY:
        return None, {"reason": "No API key", "method": "llm_failed"}

    # Optimized prompt from improvement spec
    prompt = f"""Rate this ski industry article for a resort executive audience.

ARTICLE:
Title: {article.get('title', 'No title')}
Source: {article.get('source', 'Unknown')}
Content: {article.get('content', article.get('description', 'No content'))[:600]}

SCORING CRITERIA (1-10):
- 9-10: Major business news (M&A, earnings, executive changes, large investments)
- 7-8: Significant operational/industry news (expansion, policy changes, market trends)
- 5-6: Relevant but routine (weather, openings, minor updates)
- 3-4: Marginally relevant (local events, competitions)
- 1-2: Not relevant (promotional, gear reviews, trip reports, lifestyle)

REJECT SIGNALS (score 1-2):
- Headlines with "deals", "save", "discount", "best", "top 10", "guide"
- Product reviews or gear recommendations
- Trip reports or powder alerts
- Promotional content from resorts

Output JSON only:
{{"score": N, "category": "...", "reason": "15 words max"}}

Categories: resort-operations, business-investment, weather-snow, transportation,
winter-sports, safety-incidents, canada, international, ski-history, hospitality"""

    try:
        data = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 150,
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
                return scores.get('score', 5), {
                    "reason": scores.get('reason', 'LLM scored'),
                    "category": scores.get('category'),
                    "method": "llm"
                }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='replace')
        print_safe(f"    ! Claude API error: {e}")
        print_safe(f"    ! Error details: {error_body[:200]}")
    except Exception as e:
        print_safe(f"    ! Claude API error: {e}")

    return None, {"reason": "API error", "method": "llm_failed"}


def score_article(article):
    """Score article using configured method (LLM or keyword)."""
    if ENABLE_LLM_SCORING and ANTHROPIC_API_KEY:
        score, details = score_with_llm(article)
        if score is not None:
            return score, details
        # Fall back to keyword scoring if LLM fails
        print_safe("    ! LLM failed, falling back to keyword scoring")

    return basic_keyword_score(article)


# =============================================================================
# DATA PERSISTENCE
# =============================================================================

def rescore_article(article):
    """Re-score an existing article with current penalty patterns.
    Returns new score.
    """
    text = f"{article.get('title', '')} {article.get('description', '')} {article.get('content', '')}".lower()
    title = article.get('title', '').lower()

    # Apply new consumer content penalties
    penalty = apply_contextual_penalties(text, title)

    # If penalty is severe enough, demote the article
    old_score = article.get('score', 5)
    new_score = max(1, old_score + penalty)

    return new_score


def compute_display_score(article):
    """Compute a display score for sorting articles in the feed.

    This determines the order articles appear, separate from their approval score.
    Higher display scores appear first. Factors:
    - Base score (quality)
    - Premium source boost (NYT, WSJ, etc.)
    - Analytical content boost (in-depth analysis)
    - Category adjustments (safety incidents demoted from top)
    """
    base_score = article.get('score', 5)
    source = article.get('source', '')
    text = f"{article.get('title', '')} {article.get('description', '')} {article.get('content', '')}".lower()
    title = article.get('title', '').lower()
    category = article.get('category', '')

    display_score = base_score * 2  # Scale up base score for more differentiation

    # Premium source boost (quality journalism)
    if source in PREMIUM_ANALYTICAL_SOURCES:
        display_score += 8

    # Analytical content boost
    for pattern, boost in ANALYTICAL_CONTENT_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            display_score += boost * 1.5  # Title matches weighted more
        elif re.search(pattern, text, re.IGNORECASE):
            display_score += boost

    # Category-based display adjustments
    if category in DISPLAY_DEMOTED_CATEGORIES:
        display_score += DISPLAY_DEMOTED_CATEGORIES[category]

    # Boost business-investment category for top placement
    if category == 'business-investment':
        display_score += 5

    # Consumer-oriented source penalty (good content, just not business-focused)
    if source in CONSUMER_ORIENTED_SOURCES:
        display_score += CONSUMER_SOURCE_DISPLAY_PENALTY

    # Content length bonus (longer = more analytical, usually)
    content_length = len(article.get('content', ''))
    if content_length > 800:
        display_score += 2
    if content_length > 1500:
        display_score += 2

    article['display_score'] = display_score
    return display_score


def load_existing_articles():
    """Load existing articles, re-score them with current patterns, and purge low-quality ones."""
    path = 'static/data/ski-news.json'
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                articles = {}
                rescored_count = 0
                purged_count = 0

                for a in data.get('articles', []):
                    # Normalize dates for consistent sorting
                    if 'pub_date' in a:
                        a['pub_date'] = parse_date(a['pub_date'])

                    # Re-score with current penalty patterns
                    new_score = rescore_article(a)
                    if new_score <= AUTO_REJECT_THRESHOLD:
                        # Article no longer meets quality threshold - purge it
                        purged_count += 1
                        continue

                    if new_score != a.get('score'):
                        a['score'] = new_score
                        a['rescored'] = True
                        rescored_count += 1

                    articles[a['id']] = a

                if rescored_count > 0 or purged_count > 0:
                    print_safe(f"Re-scored {rescored_count} existing articles, purged {purged_count}")

                return articles
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


def save_source_health():
    """Save source health report"""
    path = 'static/data/ski-news-source-health.json'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    health_data = {
        'updated': datetime.now().isoformat(),
        'sources': SOURCE_HEALTH
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(health_data, f, indent=2)


def save_run_log(run_stats):
    """
    Save detailed run log for debugging and monitoring.
    Keeps history of the last N runs (configured in config file).
    """
    if not CONFIG.get('logging', {}).get('enable_run_log', True):
        return

    path = 'static/data/ski-news-run-log.json'
    max_entries = CONFIG.get('logging', {}).get('max_log_entries', 30)

    # Load existing log
    existing_runs = []
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                existing_runs = data.get('runs', [])
        except:
            pass

    # Add current run
    run_entry = {
        'timestamp': datetime.now().isoformat(),
        'scoring_method': 'llm' if ENABLE_LLM_SCORING else 'keyword',
        **run_stats
    }
    existing_runs.insert(0, run_entry)

    # Trim to max entries
    existing_runs = existing_runs[:max_entries]

    # Save
    os.makedirs(os.path.dirname(path), exist_ok=True)
    log_data = {
        'last_updated': datetime.now().isoformat(),
        'total_runs': len(existing_runs),
        'runs': existing_runs
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2)

    print_safe(f"Run log saved: {path}")


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def update_ski_news():
    """Main function to fetch and score ski news"""
    print_safe("=" * 60)
    print_safe("Ski Business News Aggregator (Improved)")
    print_safe(f"Timestamp: {datetime.now().isoformat()}")
    print_safe(f"Scoring Mode: {'LLM (Claude Haiku)' if ENABLE_LLM_SCORING else 'Keyword-based'}")
    print_safe(f"Thresholds: Approve >= {AUTO_APPROVE_THRESHOLD}, Reject <= {AUTO_REJECT_THRESHOLD}")
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
    sources_ok = 0
    sources_failed = 0

    # Fetch from all sources
    print_safe("\n--- Fetching RSS Feeds ---")
    for source in RSS_SOURCES:
        print_safe(f"\n{source['name']}...")
        content = fetch_url(source['url'])
        if content:
            articles = parse_rss_feed(content, source['name'])
            new_articles = [a for a in articles if a.get('id') not in existing_ids]
            print_safe(f"  Found {len(articles)} articles, {len(new_articles)} new")
            all_articles.extend(new_articles)
            SOURCE_HEALTH[source['name']] = {'status': 'ok', 'articles': len(articles)}
            sources_ok += 1
        else:
            print_safe(f"  ! Failed to fetch")
            SOURCE_HEALTH[source['name']] = {'status': 'failed'}
            sources_failed += 1

    # Fetch from HTML sources (non-RSS)
    print_safe("\n--- Fetching HTML Sources ---")
    print_safe("\nRopeways.net (HTML scraper)...")
    ropeways_articles = fetch_ropeways_net()
    new_ropeways = [a for a in ropeways_articles if a.get('id') not in existing_ids]
    if new_ropeways:
        # Give ropeways.net articles a source boost for being industry-specific
        for a in new_ropeways:
            a['source_boost'] = 2
        all_articles.extend(new_ropeways)
        print_safe(f"  Found {len(ropeways_articles)} articles, {len(new_ropeways)} new")
        sources_ok += 1
    elif ropeways_articles:
        print_safe(f"  Found {len(ropeways_articles)} articles, 0 new")
        sources_ok += 1

    print_safe(f"\n--- Source Health: {sources_ok} OK, {sources_failed} Failed ---")

    # Stage 1: Strict Pre-filter
    print_safe(f"\n--- Stage 1: Pre-filtering {len(all_articles)} Articles ---")
    prefiltered = []
    macro_count = 0
    for article in all_articles:
        passed, business_score, is_macro = strict_prefilter(article)
        if passed:
            article['prefilter_business_score'] = business_score
            article['is_macro_relevance'] = is_macro
            if is_macro:
                macro_count += 1
            prefiltered.append(article)

    reduction_pct = (1 - len(prefiltered) / max(len(all_articles), 1)) * 100
    print_safe(f"After strict pre-filter: {len(prefiltered)} articles ({reduction_pct:.0f}% reduction)")
    if macro_count > 0:
        print_safe(f"  (includes {macro_count} via macro relevance pathway)")

    # Stage 1.5: Historical deduplication against existing feed
    # This prevents old topics from reappearing when new sources cover the same story
    print_safe(f"\n--- Stage 1.5: Historical Deduplication ---")
    prefiltered = deduplicate_against_existing(prefiltered, existing_articles)
    print_safe(f"After historical dedup: {len(prefiltered)} articles")

    # Prioritize by business score and source
    # Tier 0: Highest priority - official company IR and industry publications
    top_priority_sources = ['Vail Resorts Investor Relations', 'Ski Area Management',
                           'Snow Industry News', 'SIA - Snowsports Industries America',
                           'Outside Business Journal']
    # Tier 1: Ski-dedicated news sources
    ski_dedicated_sources = ['Unofficial Networks', 'SnowBrains', 'PlanetSKI', 'The Ski Guru']

    def source_priority(article):
        source = article.get('source', '')
        business_score = article.get('prefilter_business_score', 0)
        is_macro = article.get('is_macro_relevance', False)
        # Macro relevance articles get lower priority (sorted last within tier)
        macro_penalty = 10 if is_macro else 0
        if source in top_priority_sources:
            return (-1 + macro_penalty, -business_score)  # Highest priority
        elif source in ski_dedicated_sources:
            return (0 + macro_penalty, -business_score)
        elif 'ski' in source.lower() or 'snow' in source.lower():
            return (1 + macro_penalty, -business_score)
        else:
            return (2 + macro_penalty, -business_score)

    prefiltered.sort(key=source_priority)

    # Stage 1.5: Apply source diversity cap
    source_counts = defaultdict(int)
    diversity_filtered = []
    skipped_by_cap = 0
    for article in prefiltered:
        source = article.get('source', 'Unknown')
        if source_counts[source] < MAX_ARTICLES_PER_SOURCE:
            source_counts[source] += 1
            diversity_filtered.append(article)
        else:
            skipped_by_cap += 1

    if skipped_by_cap > 0:
        print_safe(f"Source diversity cap ({MAX_ARTICLES_PER_SOURCE}/source): skipped {skipped_by_cap} articles")

    # Stage 2: Score and categorize
    print_safe(f"\n--- Stage 2: Scoring Top {min(len(diversity_filtered), MAX_PER_RUN)} Articles ---")

    scored_articles = []
    for i, article in enumerate(diversity_filtered[:MAX_PER_RUN]):  # Process up to MAX_PER_RUN per run
        print_safe(f"\n[{i+1}/{min(len(diversity_filtered), MAX_PER_RUN)}] {article.get('title', 'No title')[:55]}...")

        score, details = score_article(article)

        article['score'] = score if score else 5
        article['score_details'] = details
        article['score_method'] = details.get('method', 'unknown')

        # Get LLM-suggested category if available
        llm_category = details.get('category') if details.get('method') == 'llm' else None

        # Assign categories using v2 system
        primary, secondary = assign_categories_v2(article, llm_category)
        article['category'] = primary
        article['secondary_categories'] = secondary

        print_safe(f"    Score: {article['score']} | Category: {primary} | Method: {article['score_method']}")

        scored_articles.append(article)

    # Stage 3: Deduplicate
    print_safe(f"\n--- Stage 3: Deduplicating {len(scored_articles)} Articles ---")
    deduplicated = deduplicate_articles(scored_articles)
    print_safe(f"After deduplication: {len(deduplicated)} unique articles")

    # Classify by threshold
    approved = []
    pending = review_queue.get('pending', [])
    rejected = review_queue.get('rejected', [])

    for article in deduplicated:
        score = article['score']

        if score >= AUTO_APPROVE_THRESHOLD:
            article['approved_date'] = datetime.now().strftime('%Y-%m-%d')
            approved.append(article)
            print_safe(f"    + APPROVED: {article.get('title', '')[:50]}...")
        elif score <= AUTO_REJECT_THRESHOLD:
            rejected.append(article)
        else:
            pending.append(article)

    # Merge approved with existing
    for article in approved:
        existing_articles[article['id']] = article

    # Compute display scores for all articles
    print_safe(f"\n--- Computing Display Scores ---")
    for article in existing_articles.values():
        compute_display_score(article)

    # Sort by display_score (primary), then by pub_date (secondary)
    # This ensures high-quality analytical content appears at the top
    all_sorted = sorted(
        existing_articles.values(),
        key=lambda x: (x.get('display_score', 0), x.get('pub_date', x.get('approved_date', ''))),
        reverse=True
    )

    # Filter out expired articles (older than MAX_ARTICLE_AGE_DAYS)
    print_safe(f"\n--- Filtering Expired Articles (>{MAX_ARTICLE_AGE_DAYS} days) ---")
    all_sorted = filter_expired_articles(all_sorted)
    print_safe(f"Articles within age limit: {len(all_sorted)}")

    # Apply source diversity: sort by display_score first, then cap per source
    # This ensures the best articles appear first while still limiting any one source
    MAX_PER_SOURCE_OUTPUT = 4
    source_counts = defaultdict(int)
    sorted_articles = []

    # all_sorted is already sorted by display_score (primary) and pub_date (secondary)
    # Now apply source cap while maintaining the quality order
    for article in all_sorted:
        source = article.get('source', 'Unknown')
        if source_counts[source] < MAX_PER_SOURCE_OUTPUT:
            sorted_articles.append(article)
            source_counts[source] += 1
            if len(sorted_articles) >= MAX_ARTICLES_OUTPUT:
                break

    # Keep only last MAX_REJECTED_KEEP rejected
    rejected = rejected[-MAX_REJECTED_KEEP:]

    # Save results
    output_data = {
        'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_articles': len(sorted_articles),
        'scoring_method': 'llm' if ENABLE_LLM_SCORING else 'keyword',
        'articles': sorted_articles
    }

    output_path = 'static/data/ski-news.json'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)

    # Save review queue
    save_review_queue({'pending': pending, 'rejected': rejected})

    # Save source health
    save_source_health()

    # Collect run statistics for logging
    run_stats = {
        'sources': {
            'total': len(RSS_SOURCES) + 1,  # +1 for ropeways.net
            'ok': sources_ok,
            'failed': sources_failed
        },
        'articles': {
            'fetched': len(all_articles),
            'after_prefilter': len(prefiltered),
            'macro_relevance': macro_count,
            'after_diversity_cap': len(diversity_filtered),
            'scored': len(scored_articles),
            'after_dedup': len(deduplicated)
        },
        'decisions': {
            'approved': len(approved),
            'pending': len(pending) - len(review_queue.get('pending', [])),  # New pending
            'rejected': len([a for a in deduplicated if a['score'] <= AUTO_REJECT_THRESHOLD])
        },
        'output': {
            'total_articles': len(sorted_articles),
            'pending_queue': len(pending),
            'rejected_queue': len(rejected)
        },
        'approved_articles': [
            {'title': a.get('title', '')[:60], 'score': a.get('score'), 'source': a.get('source')}
            for a in approved
        ]
    }

    # Save run log
    save_run_log(run_stats)

    print_safe("\n" + "=" * 60)
    print_safe("SUMMARY")
    print_safe("=" * 60)
    print_safe(f"Scoring Method: {'LLM' if ENABLE_LLM_SCORING else 'Keyword'}")
    print_safe(f"New articles approved: {len(approved)}")
    print_safe(f"Total approved articles: {len(sorted_articles)}")
    print_safe(f"Pending review: {len(pending)}")
    print_safe(f"Rejected: {len(rejected)}")
    print_safe(f"Sources OK: {sources_ok}, Failed: {sources_failed}")
    print_safe(f"\nOutput: {output_path}")
    print_safe("=" * 60)

    return output_data


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    if ENABLE_LLM_SCORING:
        print_safe("LLM Scoring ENABLED (Claude Haiku)")
        if not ANTHROPIC_API_KEY:
            print_safe("WARNING: ANTHROPIC_API_KEY not set, will fall back to keyword scoring")
    else:
        print_safe("LLM Scoring DISABLED (using keyword-based scoring)")
    print_safe("")

    try:
        update_ski_news()
    except Exception as e:
        print_safe(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
