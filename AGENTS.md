# Web Crawler & Search Engine — Agent Build Plan

## Overview
A local HTTP search API (Google/Brave/Perplexity-style) for the user's local LLM to call.
Input is a single keyword/topic, searches DuckDuckGo, crawls results, scores pages, returns JSON.

## Dependencies
```
requests
beautifulsoup4
fastapi
uvicorn[standard]
```

## Project Structure
```
scraper/
  requirements.txt
  crawler.py          # fetch_page(), crawl_from_seed() — shallow web crawler with CLI
  search.py           # score_page(), get_snippet() — relevance scoring with CLI
  ddg_search.py       # search_ddg() — DuckDuckGo HTML scraper for seed URLs
  server.py           # FastAPI app — GET /search endpoint
  results.json        # generated output (from crawler CLI)
  AGENTS.md           # this file
```

---

## File 1: `requirements.txt`
```
requests
beautifulsoup4
fastapi
uvicorn[standard]
```

---

## File 2: `crawler.py`

### Exports
- `fetch_page(url)` → dict with url, title, headings, body_text, links
- `crawl_from_seed(seed_url, depth=1, max_pages=3)` → list of page dicts

### CLI Interface (preserved)
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
   - Sleep 0.1 seconds (throttle, reduced from 0.5s)
   - GET request with timeout=10, User-Agent header set
   - Parse HTML with BeautifulSoup
   - Extract page data (see below)
   - Append to results
   - Discover new links (see below), append to queue with `depth + 1`

3. Write `results` to output JSON file (CLI only)

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
- `links`: absolute URLs extracted from all `<a href>` tags

### Link Discovery & Filtering
- Parse all `<a href>` tags
- Convert to absolute URLs using `urllib.parse.urljoin(base_url, href)`
- Only keep URLs that match the seed domain (same scheme + domain)
- Only keep `/wiki/` paths for Wikipedia
- Strip URL fragments (`#...`)
- Filter out Wikipedia namespace prefixes (case-sensitive):
  - `Special:`, `File:`, `Category:`, `Talk:`, `Help:`, `Template:`, `User:`
- Filter out URLs already in `visited`

### Error Handling
- Catch `requests.exceptions.RequestException` — skip page, log warning to stderr
- Catch `json` errors on write — print error to stderr, exit 1
- Set `session.headers['User-Agent'] = 'WebCrawlerCLI/1.0'`

---

## File 3: `search.py`

### Exports
- `score_page(page, query)` → int score
- `get_snippet(body_text, query, context=100)` → str snippet

### CLI Interface (preserved)
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

## File 4: `ddg_search.py`

### Export
- `search_ddg(query)` → list of dicts with url, title, snippet

### Logic
1. Initialize `requests.Session()` with Chrome User-Agent
2. Fetch `https://html.duckduckgo.com/` to obtain cookies
3. Search `https://html.duckduckgo.com/html/?q=<query>`
4. Sleep 100ms (throttle)
5. Parse HTML with BeautifulSoup:
   - Find `div.result` elements (skip ads with `result--ad` class)
   - Title from `a.result__a` or `a.result__title`
   - URL extracted from `uddg=` parameter in href
   - Snippet from `div.result__body` or `a.result__snippet`
6. Return up to 10 results

---

## File 5: `server.py`

### CLI Arguments
- `--include-body-text`: include body_text in responses
- `--host`: bind address (default 0.0.0.0)
- `--port`: listen port (default 8000)

### Endpoint: `GET /search`
- Query params:
  - `q` (required): search query string
  - `top_k` (int, default=8): max results to return

### Response JSON
```json
{
  "query": "search term",
  "results": [
    {
      "url": "https://...",
      "title": "Page title",
      "score": 12,
      "snippet": "Context around query match...",
      "body_text": "..."
    }
  ],
  "total_results": 5,
  "crawled_pages": 28
}
```

- `body_text` included only if server started with `--include-body-text`
- Returns 400 if `q` is missing or empty

### Pipeline
1. Get URLs from DuckDuckGo via `search_ddg(q)`
2. For each URL, shallow-crawl via `crawl_from_seed(url, depth=1, max_pages=3)`
3. Score all crawled pages via `score_page(page, q)`
4. Sort by score descending, slice to `top_k`
5. Return JSON response

---

## Run Commands

### Install
```bash
pip install -r requirements.txt
```

### Start Search API Server
```bash
python server.py --port 8000
# With body text:
python server.py --port 8000 --include-body-text
```

### Query API
```bash
curl "http://localhost:8000/search?q=artificial+intelligence&top_k=5"
```

### Legacy CLI Usage (preserved)
```bash
python crawler.py --url https://en.wikipedia.org/wiki/Computer
python search.py --query "artificial intelligence"
```

---

## Constraints
- No robots.txt checking
- No authentication
- Terminal output only (no web UI)
- JSON for all data storage
- 100ms throttle between requests
- Depth 1 default per seed (via API)
- 3 pages max per seed domain
- DuckDuckGo HTML scraping (not API) — Google/Bing/Brave block automated scraping without API keys
