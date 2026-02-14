# Ski News Configuration Guide

This document explains how to configure the ski news aggregation system using the YAML configuration file.

## Configuration File Location

```
config/ski-news-config.yaml
```

The system loads this file at startup. If the file doesn't exist or PyYAML is not installed, sensible defaults are used.

## Configuration Sections

### Scoring Settings

Control how articles are scored for relevance.

```yaml
scoring:
  # Enable LLM scoring (requires ANTHROPIC_API_KEY environment variable)
  enable_llm: false

  # Thresholds for automatic approval/rejection
  thresholds:
    llm:
      approve: 7  # Articles >= this score are auto-approved
      reject: 3   # Articles <= this score are auto-rejected
    keyword:
      approve: 6
      reject: 3
```

**Notes:**
- LLM scoring uses Claude Haiku and costs approximately $6-10/month
- Articles scoring between reject and approve thresholds go to a review queue
- Keyword scoring is free and uses pattern matching

### Source Diversity

Prevent any single source from dominating the feed.

```yaml
diversity:
  max_per_source: 5  # Maximum articles from any single source per run
```

**Why this matters:**
- Some sources (like Google News aggregators) may return dozens of ski-related articles
- This cap ensures variety in the feed
- High-priority sources are processed first, so their articles get priority

### Deduplication

Control how similar articles are detected and merged.

```yaml
deduplication:
  title_similarity: 0.85          # 0.0-1.0, higher = stricter
  lead_paragraph_similarity: 0.80  # For catching same story, different headline
  min_lead_length: 50              # Minimum chars to consider lead comparison
```

**How it works:**
1. Articles are first grouped by normalized title keywords
2. Then fuzzy matching compares titles at the configured threshold
3. Source suffixes (e.g. " - The Cool Down") are stripped before comparison to catch Google News aggregator variants of the same story
4. Lead paragraph comparison catches stories with different headlines but same content

### Focus Topics

Temporarily boost articles about trending or important topics.

```yaml
focus_topics:
  "2026 winter olympics": 3
  "vail resorts earnings": 2
  "climate change snow": 2
```

**Format:** `"topic phrase": boost_value`

**Boost values:**
- 1-2: Slight preference
- 3-4: Moderate boost
- 5: Strong preference (use sparingly)

Title matches get an additional +1 boost.

**Example use cases:**
- Earnings season: boost company names
- Olympics: boost event-related terms
- Breaking news: boost specific incidents

### Output Settings

Control the size of output files.

```yaml
output:
  max_articles: 50     # Maximum articles in main feed
  max_rejected: 100    # Maximum rejected articles to keep
  max_per_run: 30      # Maximum articles to process per run
```

### Logging

Configure run logging for debugging and monitoring.

```yaml
logging:
  enable_run_log: true   # Enable/disable run logging
  max_log_entries: 30    # Number of historical runs to keep
```

**Log file location:** `static/data/ski-news-run-log.json`

**Log contents:**
- Timestamp of each run
- Source health (OK/failed counts)
- Article counts at each pipeline stage
- Decision breakdown (approved/pending/rejected)
- List of approved articles with scores

## Environment Variables

These override config file settings:

| Variable | Purpose |
|----------|---------|
| `ENABLE_LLM_SCORING` | Set to `true` to enable LLM scoring |
| `ANTHROPIC_API_KEY` | Required for LLM scoring |

## Example: Boosting Olympics Coverage

```yaml
focus_topics:
  "2026 winter olympics": 4
  "milan cortina": 3
  "alpine skiing world cup": 2
  "fis": 2
```

## Example: Stricter Deduplication

```yaml
deduplication:
  title_similarity: 0.90
  lead_paragraph_similarity: 0.85
```

## Troubleshooting

### Config not loading
1. Check that PyYAML is installed: `pip install pyyaml`
2. Verify YAML syntax is valid
3. Check console output for config loading errors

### Too many duplicates
- Increase `title_similarity` threshold
- Enable lead paragraph comparison by ensuring `min_lead_length` is appropriate
- Note: Source suffix stripping (`_strip_source_suffix()`) automatically handles Google News aggregator variants

### Missing relevant articles
- Check if articles are being rejected by source diversity cap
- Review the run log to see where articles are filtered
- Consider lowering `approve` threshold slightly

### Focus topics not working
- Ensure topics are lowercase in the config
- Check that topic phrases match exactly how they appear in articles
- Review run log for `focus_topic_boost` values

## Pipeline Overview

```
RSS Feeds → Pre-filter → Source Diversity Cap → Scoring → Deduplication → Output
              ↓              ↓                    ↓            ↓
         Ski terms      Max per source      Focus boost   Title + Lead
         Macro terms                        Penalties     comparison
```

## Related Files

- `update_ski_news.py` - Main aggregation script
- `docs/SKI_NEWS_SCRAPING_DOCUMENTATION.md` - Technical documentation
- `static/data/ski-news.json` - Output feed (automated)
- `content/manual-news/*.md` - CMS-managed manual stories
- `layouts/manual-news/list.json` - Hugo template → `/manual-news/index.json`
- `static/admin/config.yml` - Sveltia CMS configuration
- `static/data/ski-news-run-log.json` - Run history
- `static/data/ski-news-source-health.json` - Source status
