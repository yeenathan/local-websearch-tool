import argparse
import os

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

import crawler
import ddg_search
import search


def parse_args():
    parser = argparse.ArgumentParser(description="Search API server")
    parser.add_argument("--include-body-text", action="store_true", help="Include body_text in responses")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    return parser.parse_args()


app = FastAPI(title="Local Search API")


def get_include_body_text():
    """Check environment variable or default to False."""
    return os.environ.get("INCLUDE_BODY_TEXT", "0") == "1"


@app.get("/search")
def search_endpoint(
    q: str = Query(..., description="Search query string"),
    top_k: int = Query(8, ge=1, le=50, description="Max results to return"),
):
    """Search the web and return ranked results."""
    if not q:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing required parameter: q"},
        )

    include_body = get_include_body_text()

    # Step 1: Get URLs from DuckDuckGo
    ddg_results = ddg_search.search_ddg(q)
    if not ddg_results:
        return {
            "query": q,
            "results": [],
            "total_results": 0,
            "crawled_pages": 0,
        }

    # Step 2: Crawl each URL (shallow crawl, depth 1)
    all_pages = []
    for result in ddg_results:
        pages = crawler.crawl_from_seed(result["url"], depth=2, max_pages=10)
        all_pages.extend(pages)

    crawled_pages = len(all_pages)

    # Step 3: Score each page
    scored = []
    for page in all_pages:
        s = search.score_page(page, q)
        if s > 0:
            scored.append((s, page))

    # Step 4: Sort by score, slice to top_k
    scored.sort(key=lambda x: x[0], reverse=True)
    top_results = scored[:top_k]

    # Step 5: Build response
    results = []
    for s, page in top_results:
        entry = {
            "url": page["url"],
            "title": page["title"],
            "score": s,
            "snippet": search.get_snippet(page.get("body_text", ""), q),
        }
        if include_body:
            entry["body_text"] = page.get("body_text", "")
        results.append(entry)

    return {
        "query": q,
        "results": results,
        "total_results": len(results),
        "crawled_pages": crawled_pages,
    }


if __name__ == "__main__":
    import uvicorn

    args = parse_args()
    if args.include_body_text:
        os.environ["INCLUDE_BODY_TEXT"] = "1"
    uvicorn.run(app, host=args.host, port=args.port)
