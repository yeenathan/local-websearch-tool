# Web Crawler & Search Engine — Agent Build Plan

## Overview
Build a generic HTML-based web crawler with CLI search. Target: Wikipedia. Design for portability to other sites later.

## Dependencies
```
requests
beautifulsoup4
```

## Project Structure
```
scraper/
  requirements.txt
  crawler.py
  search.py
  results.json          # generated output
  AGENTS.md              # this file
```

---

## File 1: `requirements.txt`
Create with exact contents:
```
requests
beautifulsoup4
```

---

## File 2: `crawler.py`

### CLI Interface
- Use `argparse`
- Args:
  - `--url` (required): seed URL to start crawling
  - `--depth` (int, default=2): max recursion depth from seed
  - `--max-pages` (int, default=20): max pages per domain
  - `--output` (str, default="results.json"): output file path

### Crawl Logic
1. Initialize:
   - `visited = set()` — track visited URLs
   - `results = []` — list of page dicts
   - `queue = deque([(seed_url, 0)])` — BFS queue of (url, depth)
   - `session = requests.Session()` — reuse connections

2. While queue is not empty and `len(visited) < max_pages`:
   - Pop `(url, depth)` from queue
   - Skip if `url` in visited or `depth > max_depth`
   - Add to visited
   - Sleep 0.5 seconds (throttle)
   - GET request with timeout=10, User-Agent header set
   - Parse HTML with BeautifulSoup
   - Extract page data (see below)
   - Append to results
   - Discover new links (see below), append to queue with `depth + 1`

3. Write `results` to output JSON file

### Per-Page Extraction
For each page, build a dict:
```python
{
  "url": str,
  "title": str,
  "headings": [{"tag": "h1", "text": "..."}, ...],
  "body_text": str,
  "links": ["https://...", ...],
}
```

- `url`: the fetched URL
- `title`: `<title>` tag text, or `<h1>` if no title tag
- `headings`: list of all h1-h6 tags in order, with their tag name and stripped text
- `body_text`: concatenation of all text from `<p>`, `<li>`, `<td>`, `<dd>` tags, collapsed to single string (strip whitespace)
- `links`: absolute URLs extracted from all `<a href>` tags (see link filtering below)

### Link Discovery & Filtering
- Parse all `<a href>` tags
- Convert to absolute URLs using `urllib.parse.urljoin(base_url, href)`
- Only keep URLs that match the seed domain (same scheme + domain)
- Only keep `/wiki/` paths for Wikipedia
- Strip URL fragments (`#...`)
- Filter out these Wikipedia namespace prefixes (case-sensitive):
  - `Special:`, `File:`, `Category:`, `Talk:`, `Help:`, `Template:`, `User:`
- Filter out URLs already in `visited`
- Append to queue with `depth + 1`

### Error Handling
- Catch `requests.exceptions.RequestException` — skip page, log warning to stderr
- Catch `json` errors on write — print error to stderr, exit 1
- Set `session.headers['User-Agent'] = 'WebCrawlerCLI/1.0'`

### Output Format
`results.json` is a JSON array of page objects, one per crawled page.

---

## File 3: `search.py`

### CLI Interface
- Use `argparse`
- Args:
  - `--query` (required): search query string
  - `--data` (str, default="results.json"): path to results file

### Search Logic
1. Load `results.json`
2. For each page, compute relevance score:
   - `+10` points if query (case-insensitive) is in `title`
   - `+1` point per occurrence of query (case-insensitive) in `body_text`
   - `+2` points if query is in any heading text
3. Filter pages with score > 0
4. Sort by score descending
5. Print top 20 results to stdout

### Output Format
For each result, print:
```
Title: <title>
URL: <url>
Score: <score>
Snippet: <200 chars of body_text around the query match>
---
```

- Snippet: find the query match in `body_text`, extract 100 chars before and after, strip whitespace
- Separator between results: three dashes on their own line

---

## Run Commands
```bash
pip install -r requirements.txt
python crawler.py --url https://en.wikipedia.org/wiki/Computer
python search.py --query "artificial intelligence"
```

---

## Constraints
- No robots.txt checking
- No authentication
- Terminal output only (no web UI)
- JSON for all data storage
- 500ms throttle between requests
- 20 pages max per domain
- Depth 2 default (configurable via flag)
