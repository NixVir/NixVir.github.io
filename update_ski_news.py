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

# Scoring thresholds
# Without LLM: lower thresholds to let more through
AUTO_APPROVE_THRESHOLD = 6  # Was 8 for LLM scoring
AUTO_REJECT_THRESHOLD = 3   # Was 4 for LLM scoring

# Curated RSS sources for ski industry news
RSS_SOURCES = [
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
        'name': 'The Ski Diva',
        'url': 'https://www.theskidiva.com/feed/',
        'category': 'community',
        'boost': 0
    },
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
    }
]

# Keywords for basic pre-filtering (must contain at least one)
BUSINESS_KEYWORDS = [
    'resort', 'ski area', 'mountain', 'lift', 'investment', 'acquisition',
    'merger', 'expansion', 'revenue', 'profit', 'loss', 'earnings', 'quarterly',
    'annual', 'season pass', 'ikon', 'epic', 'vail', 'alterra', 'boyne',
    'aspen', 'powder', 'employee', 'workforce', 'labor', 'snowmaking',
    'climate', 'sustainability', 'real estate', 'development', 'hotel',
    'lodging', 'retail', 'rental', 'lessons', 'ski school', 'terrain park',
    'gondola', 'chairlift', 'industry', 'market', 'growth', 'decline',
    'visitor', 'skier visits', 'snowfall', 'opening', 'closing', 'bankruptcy',
    'ceo', 'executive', 'management', 'partnership', 'sponsor'
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

def score_with_claude(article):
    """Score article using Claude API"""
    if not ANTHROPIC_API_KEY:
        return None, "No API key"

    prompt = f"""Score this ski industry news article on a scale of 1-10 for inclusion in a ski business news feed.

Title: {article.get('title', 'No title')}
Source: {article.get('source', 'Unknown')}
Content: {article.get('content', article.get('description', 'No content'))[:800]}

Scoring criteria:
- Relevance to ski resort operations, management, or industry business (1-10)
- News value and timeliness (1-10)
- Quality of reporting vs clickbait/fluff (1-10)

Respond with ONLY a JSON object in this exact format:
{{"relevance": X, "news_value": X, "quality": X, "overall": X, "reason": "brief explanation"}}

The overall score should be your recommendation for inclusion (1-10)."""

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

Scoring criteria:
- Relevance to ski resort operations, management, or industry business (1-10)
- News value and timeliness (1-10)
- Quality of reporting vs clickbait/fluff (1-10)

Respond with ONLY a JSON object in this exact format:
{{"relevance": X, "news_value": X, "quality": X, "overall": X, "reason": "brief explanation"}}"""

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

    score = 5  # Base score (slightly higher to be less restrictive)

    # High-value business keywords (in title = +2, in body = +1)
    high_value = ['acquisition', 'merger', 'investment', 'earnings', 'expansion',
                  'revenue', 'profit', 'growth', 'ipo', 'bankruptcy', 'layoff',
                  'ceo', 'executive', 'quarterly', 'annual report', 'partnership',
                  'financial', 'closes', 'sold', 'buys', 'purchase']
    for kw in high_value:
        if kw in title:
            score += 2
        elif kw in text:
            score += 1

    # Industry-specific keywords (+1 each)
    industry_kw = ['vail resorts', 'alterra', 'ikon', 'epic pass', 'boyne',
                   'aspen skiing', 'skier visits', 'snowmaking', 'season pass',
                   'lift ticket', 'ski industry', 'resort operator', 'new lift',
                   'new chairlift', 'gondola', 'terrain expansion', 'real estate',
                   'hotel', 'lodging', 'tariff', 'workforce', 'employees']
    for kw in industry_kw:
        if kw in text:
            score += 1

    # Resort/business news indicators (+1)
    news_kw = ['announces', 'announces', 'unveils', 'launches', 'opening',
               'closing', 'to open', 'will open', 'set to', 'plans to',
               'introduces', 'reveals', 'reports']
    for kw in news_kw:
        if kw in title:
            score += 1
            break

    # Penalty for likely non-business content
    fluff_kw = ['powder day', 'best runs', 'trip report', 'gear review',
                'how to ski', 'beginner tips', 'what to wear', 'packing list',
                'gift guide', 'top 10', 'best of']
    for kw in fluff_kw:
        if kw in text:
            score -= 2

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
