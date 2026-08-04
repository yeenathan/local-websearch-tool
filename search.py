import argparse
import json
import re
import sys


def get_snippet(body_text, query, context=100):
    lower_body = body_text.lower()
    lower_query = query.lower()
    index = lower_body.find(lower_query)
    if index == -1:
        return ""

    start = max(0, index - context)
    end = min(len(body_text), index + len(query) + context)
    snippet = body_text[start:end].strip()
    return snippet[:200] if len(snippet) > 200 else snippet


def score_page(page, query):
    score = 0
    lower_query = query.lower()

    title = page.get("title", "").lower()
    if lower_query in title:
        score += 10

    body_text = page.get("body_text", "")
    score += len(re.findall(re.escape(lower_query), body_text.lower()))

    for heading in page.get("headings", []):
        if lower_query in heading.get("text", "").lower():
            score += 2

    return score


def main():
    parser = argparse.ArgumentParser(description="Search crawled results")
    parser.add_argument("--query", required=True, help="Search query string")
    parser.add_argument("--data", default="results.json", help="Path to results file")
    args = parser.parse_args()

    try:
        with open(args.data, "r") as f:
            pages = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading {args.data}: {e}", file=sys.stderr)
        sys.exit(1)

    scored = []
    for page in pages:
        s = score_page(page, args.query)
        if s > 0:
            scored.append((s, page))

    scored.sort(key=lambda x: x[0], reverse=True)

    for i, (s, page) in enumerate(scored[:20]):
        snippet = get_snippet(page.get("body_text", ""), args.query)
        print(f"Title: {page.get('title', '')}")
        print(f"URL: {page.get('url', '')}")
        print(f"Score: {s}")
        print(f"Snippet: {snippet}")
        print("---")


if __name__ == "__main__":
    main()
