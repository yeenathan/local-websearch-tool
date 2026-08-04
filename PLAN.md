# Threaded Concurrent Crawling — Implementation Plan

## Goal
Replace sequential page fetching in `crawler.py` with threaded concurrency while preserving CLI interface and function signatures.

## Changes

### 1. Imports
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
```

### 2. New CLI Argument
- `--workers` (int, default=4): max concurrent fetch threads

### 3. crawl_from_seed — BFS with ThreadPoolExecutor

**Main loop (per depth level):**
1. Separate queue into current-depth items
2. Filter items: skip if URL in `visited`, if `visited` >= max_pages, or depth exceeded
3. Mark URLs as visited (in main thread — thread-safe)
4. Submit all valid fetch jobs to `ThreadPoolExecutor(max_workers)`
5. Collect results via `as_completed()`
6. For completed pages: append to results list, extract/validate links, enqueue next-depth items
7. Repeat for next depth level

### 4. fetch_page — Per-Request Throttle

**Change:**
- Move `time.sleep(0.1)` into `fetch_page()` as `time.sleep(0.025)`
- Each worker throttles itself before making request
- Keeps total request rate reasonable across threads

### 5. Thread Safety

- **visited set:** checked and modified only in main thread before submitting work
- **results list:** appended to only in main thread after futures complete
- **queue:** only main thread reads/writes (deque is not thread-safe)
- **session:** create one `requests.Session` per thread inside executor worker, or share a single session (requests.Session is thread-safe for concurrent GETs)

### 6. Error Handling

- Same as current: catch `RequestException`, log warning to stderr, skip page
- `as_completed()` handles failed futures — check `future.exception()` before processing

### 7. Preserve

- Function exports: `fetch_page()`, `crawl_from_seed()`
- Link filtering logic (Wikipedia namespace prefixes, `/wiki/` paths, same-domain)
- CLI behavior: `--url`, `--depth`, `--max-pages`, `--output`
- Output JSON format

## Testing
```bash
python crawler.py --url https://en.wikipedia.org/wiki/Computer --workers 4
python crawler.py --url https://en.wikipedia.org/wiki/Computer --workers 1  # verify unchanged
```
