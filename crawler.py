import argparse
import json
import sys
import time
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


def parse_args():
    parser = argparse.ArgumentParser(description="Web crawler CLI")
    parser.add_argument("--url", required=True, help="Seed URL to start crawling")
    parser.add_argument("--depth", type=int, default=2, help="Max recursion depth")
    parser.add_argument("--max-pages", type=int, default=20, help="Max pages per domain")
    parser.add_argument("--output", default="results.json", help="Output JSON file path")
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

    for link in links:
        parsed = urlparse(link)

        if parsed.scheme != seed_scheme or parsed.netloc != seed_domain:
            continue

        path = parsed.path

        if seed_domain.endswith("wikipedia.org"):
            if "/wiki/" not in path:
                continue

            path_prefix = path.split("/wiki/")[1].split("/")[0]
            if any(path_prefix.startswith(p) for p in exclude_prefixes):
                continue

        if "#" in link:
            link = link.split("#")[0]

        if link not in visited:
            filtered.append(link)

    return filtered


def crawl(seed_url, max_depth, max_pages, output_path):
    visited = set()
    results = []
    queue = deque([(seed_url, 0)])
    session = requests.Session()
    session.headers["User-Agent"] = "WebCrawlerCLI/1.0"

    while queue and len(visited) < max_pages:
        url, depth = queue.popleft()

        if url in visited:
            continue
        if depth > max_depth:
            continue

        visited.add(url)

        time.sleep(0.1)

        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Warning: Failed to fetch {url}: {e}", file=sys.stderr)
            continue

        page_data = extract_page(url, response.text)
        results.append(page_data)

        new_links = filter_links(page_data["links"], seed_url, visited)
        for link in new_links:
            queue.append((link, depth + 1))

    try:
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
    except (TypeError, IOError) as e:
        print(f"Error writing results: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    args = parse_args()
    crawl(args.url, args.depth, args.max_pages, args.output)


if __name__ == "__main__":
    main()
