import argparse
import json
import re
import sys


def get_snippet(body_text, query, context=100):
    lower_body = body_text.lower()
    query_words = query.lower().split()
    if not query_words:
        return ""

    # Find the first occurrence of any query word
    index = None
    matched_word_len = 0
    for w in query_words:
        pos = lower_body.find(w)
        if pos != -1 and (index is None or pos < index):
            index = pos
            matched_word_len = len(w)

    if index is None:
        return ""

    start = max(0, index - context)
    end = min(len(body_text), index + matched_word_len + context)
    snippet = body_text[start:end].strip()
    return snippet[:200] if len(snippet) > 200 else snippet


def score_page(page, query):
    score = 0
    query_words = query.lower().split()
    if not query_words:
        return 0

    # Title: +10 if ANY query word appears in title
    title = page.get("title", "").lower()
    if any(w in title for w in query_words):
        score += 10

    # Body: +1 per occurrence of each query word
    body_text = page.get("body_text", "")
    body_lower = body_text.lower()
    for w in query_words:
        score += len(re.findall(re.escape(w), body_lower))

    # Headings: +2 if ANY query word appears in heading
    for heading in page.get("headings", []):
        if any(w in heading.get("text", "").lower() for w in query_words):
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
