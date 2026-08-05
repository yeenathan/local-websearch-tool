import argparse
import json
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


def parse_args():
    parser = argparse.ArgumentParser(description="Web crawler CLI")
    parser.add_argument("--url", required=True, help="Seed URL to start crawling")
    parser.add_argument("--depth", type=int, default=2, help="Max recursion depth")
    parser.add_argument("--max-pages", type=int, default=20, help="Max pages per domain")
    parser.add_argument("--output", default="results.json", help="Output JSON file path")
    parser.add_argument("--workers", type=int, default=4, help="Max concurrent fetch threads")
    return parser.parse_args()


def extract_page(url, html):
    soup = BeautifulSoup(html, "html.parser")

    content = soup.find("div", id="mw-content-text") or soup.find("div", class_="mw-parser-output") or soup

    title_tag = soup.find("title")
    h1_tag = content.find("h1")
    title = (title_tag.get_text(strip=True) if title_tag else "") or (
        h1_tag.get_text(strip=True) if h1_tag else ""
    )

    headings = []
    for tag in content.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        headings.append({"tag": tag.name, "text": tag.get_text(strip=True)})

    body_parts = []
    for tag in content.find_all(["p", "li", "td", "dd"]):
        text = tag.get_text(strip=True)
        if text:
            body_parts.append(text)
    body_text = " ".join(body_parts)

    links = []
    for a in soup.find_all("a", href=True):
        links.append(urljoin(url, a["href"]))

    return {
        "url": url,
        "title": title,
        "headings": headings,
        "body_text": body_text,
        "links": links,
    }


def filter_links(links, seed_url, visited):
    seed_parsed = urlparse(seed_url)
    seed_scheme = seed_parsed.scheme
    seed_domain = seed_parsed.netloc
    seed_path = seed_parsed.path

    filtered = []
    exclude_prefixes = (
        "Special:",
        "File:",
        "Category:",
        "Talk:",
        "Help:",
        "Template:",
        "User:",
    )

    # Detect wiki-style path prefix
    wiki_prefix = None
    for prefix in ("/wiki/", "/title/"):
        if prefix in seed_path:
            wiki_prefix = prefix
            break

    for link in links:
        parsed = urlparse(link)

        if parsed.scheme != seed_scheme or parsed.netloc != seed_domain:
            continue

        path = parsed.path

        # If seed is on a wiki/title path, only follow same-type links
        if wiki_prefix is not None:
            if wiki_prefix not in path:
                continue

            # Apply namespace prefix exclusions for any wiki-style path
            page_name = path.split(wiki_prefix)[1].split("/")[0]
            if any(page_name.startswith(p) for p in exclude_prefixes):
                continue

        if "#" in link:
            link = link.split("#")[0]

        if link not in visited:
            filtered.append(link)

    return filtered

def fetch_page(url, session=None):
    """Fetch a single page and return page data dict, or None on failure."""
    if session is None:
        session = requests.Session()
        session.headers["User-Agent"] = "WebCrawlerCLI/1.0"
        close_session = True
    else:
        close_session = False

    try:
        time.sleep(0.025)
        response = session.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Warning: Failed to fetch {url}: {e}", file=sys.stderr)
        if close_session:
            session.close()
        return None

    page_data = extract_page(url, response.text)

    if close_session:
        session.close()

    return page_data


def crawl_from_seed(seed_url, depth=1, max_pages=3, workers=4):
    """BFS crawl from a seed URL using ThreadPoolExecutor. Returns list of page dicts."""
    visited = set()
    results = []
    queue = deque([(seed_url, 0)])
    session = requests.Session()
    session.headers["User-Agent"] = "WebCrawlerCLI/1.0"

    while queue and len(visited) < max_pages:
        current_level = []
        next_level = deque()

        while queue:
            url, d = queue.popleft()

            if d > depth:
                continue
            if url in visited:
                continue
            if len(visited) >= max_pages:
                queue.appendleft((url, d))
                break

            visited.add(url)
            current_level.append((url, d))

        if not current_level:
            break

        def fetch_task(url):
            return fetch_page(url, session)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_url = {executor.submit(fetch_task, url): url for url, _ in current_level}

            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    page_data = future.result()
                except Exception as e:
                    print(f"Warning: Failed to fetch {url}: {e}", file=sys.stderr)
                    continue

                if page_data is not None:
                    results.append(page_data)
                    new_links = filter_links(page_data["links"], seed_url, visited)
                    current_depth = next(d for u, d in current_level if u == url)
                    for link in new_links:
                        next_level.append((link, current_depth + 1))

        queue.extend(next_level)

    session.close()
    return results


def crawl(seed_url, max_depth, max_pages, output_path, workers=4):
    results = crawl_from_seed(seed_url, depth=max_depth, max_pages=max_pages, workers=workers)

    try:
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
    except (TypeError, IOError) as e:
        print(f"Error writing results: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    args = parse_args()
    crawl(args.url, args.depth, args.max_pages, args.output, args.workers)


if __name__ == "__main__":
    main()
