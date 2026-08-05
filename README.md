# Local Search API

A local HTTP search API that crawls the web and returns ranked results with a json response.

**DISCLAIMER:** Almost completely written with a Q4 quant of Qwen 3.6-27B. This is a personal experiment and exercise with AI agentic workflows. And I didn't want to enter my card for search api credits

## How It Works

1. Sends your query to DuckDuckGo (HTML endpoint, no API key needed)
2. For each search result URL, performs a shallow crawl (depth=2, max 10 pages per seed)
3. Scores all crawled pages against your query
4. Returns the top-k most relevant pages with snippets

## Setup

Install dependencies:

```bash
pip install fastapi uvicorn requests beautifulsoup4
```

## Usage

### As a Search API Server

Start the server:

```bash
python server.py
```

Options:
- `--host` — bind address (default: `127.0.0.1`)
- `--port` — listen port (default: `8000`)
- `--include-body-text` — include full `body_text` in responses

Query the API:

```bash
curl "http://localhost:8000/search?q=rust+ownership&top_k=5"
```

Parameters:
- `q` — search query (required)
- `top_k` — max results to return (1-50, default: 8)

Example response:

```json
{
  "query": "rust ownership",
  "results": [
    {
      "url": "https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html",
      "title": "Chapter 4: Understanding Ownership",
      "score": 42,
      "snippet": "..."
    }
  ],
  "total_results": 5,
  "crawled_pages": 37
}
```

### As a Standalone Crawler

```bash
python crawler.py --url https://example.com/article --depth 2 --max-pages 20 --output results.json
```

Options:
- `--url` — seed URL (required)
- `--depth` — max recursion depth (default: 2)
- `--max-pages` — max pages per domain (default: 20)
- `--output` — output JSON file (default: `results.json`)
- `--workers` — concurrent fetch threads (default: 4)

### As a Query Tool

Search previously crawled results:

```bash
python search.py --query "rust ownership" --data results.json
```

Options:
- `--query` — search query (required)
- `--data` — path to crawled results JSON (default: `results.json`)

## Scoring

Pages are ranked by a simple scoring function:
- +10 if any query word appears in the title
- +1 per query word occurrence in the body
- +2 per heading containing a query word

Results are sorted by score descending and sliced to `top_k`.
