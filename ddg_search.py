import re
import sys
import time

import requests
from bs4 import BeautifulSoup


def search_ddg(query):
    """Search DuckDuckGo HTML endpoint and return list of result dicts.

    Returns:
        List of dicts with keys: url, title, snippet
    """
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    # Step 1: Fetch main page to get cookies
    try:
        session.get("https://html.duckduckgo.com/", timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"Warning: Failed to initialize DDG session: {e}", file=sys.stderr)
        return []

    # Step 2: Perform search
    url = f"https://html.duckduckgo.com/html/?q={query}"
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Warning: Failed DuckDuckGo search: {e}", file=sys.stderr)
        return []

    time.sleep(0.1)

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for result_div in soup.find_all("div", class_="result"):
        # Skip ads
        if "result--ad" in result_div.get("class", []):
            continue

        # Try to find title (new structure: a.result__a or a.result__title)
        title_tag = result_div.find("a", class_="result__a")
        if not title_tag:
            title_tag = result_div.find("a", class_="result__title")

        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)

        # Extract URL from the redirect link
        href = title_tag.get("href", "")
        result_url = extract_url(href)

        # Find snippet (new structure: div.result__body or a.result__snippet)
        snippet = ""
        snippet_tag = result_div.find("a", class_="result__snippet")
        if not snippet_tag:
            body_tag = result_div.find("div", class_="result__body")
            if body_tag:
                snippet_tag = body_tag
        if snippet_tag:
            snippet = snippet_tag.get_text(strip=True)

        results.append({
            "url": result_url,
            "title": title,
            "snippet": snippet,
        })

    return results[:10]


def extract_url(href):
    """Extract actual URL from DuckDuckGo redirect link."""
    # DuckDuckGo uses //duckduckgo.com/l/?uddg=https%3A%2F%2F...
    match = re.search(r"uddg=([^&]+)", href)
    if match:
        import urllib.parse
        return urllib.parse.unquote(match.group(1))
    return href
