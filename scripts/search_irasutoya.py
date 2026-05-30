#!/usr/bin/env python3
"""IRASUTOYA illustration search and download tool.

Usage:
    python search_irasutoya.py <keyword> [--output <path>] [--limit <n>] [--list-only]

Examples:
    python search_irasutoya.py 猫
    python search_irasutoya.py "ビジネス会議" --output ./images/
    python search_irasutoya.py 犬 --limit 5 --list-only
"""

import argparse
import io
import json
import os
import re
import sys
import time
from urllib.parse import quote, urljoin

# Fix Windows terminal encoding for Japanese characters
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: requests and beautifulsoup4 are required.")
    print("Install: pip install requests beautifulsoup4")
    sys.exit(1)

BASE_URL = "https://www.irasutoya.com"
SEARCH_URL = f"{BASE_URL}/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}


def search_irasutoya(keyword: str, limit: int = 10) -> list[dict]:
    """Search IRASUTOYA for illustrations matching the keyword.

    Returns a list of dicts with keys: title, thumbnail_url, page_url

    IRASUTOYA's search results use div.boxim entries with JavaScript-rendered
    thumbnails. The JS calls bp_thumbnail_resize("url","title") to generate
    <img> tags dynamically.
    """
    params = {"q": keyword}
    results = []

    try:
        resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"ERROR: Failed to search IRASUTOYA: {e}", file=sys.stderr)
        return results

    soup = BeautifulSoup(resp.text, "html.parser")

    # Primary: div.boxim entries (IRASUTOYA's actual search result structure)
    entries = soup.select("div.boxim")

    for entry in entries[:limit]:
        result = {}

        # Get page URL from the <a> tag
        link = entry.find("a", href=True)
        if link:
            result["page_url"] = link.get("href", "")

        # Parse the JavaScript to extract thumbnail URL and title.
        # Format: bp_thumbnail_resize("IMAGE_URL","TITLE")
        script = entry.find("script")
        if script and script.string:
            js_text = script.string
            # Match the bp_thumbnail_resize call
            match = re.search(
                r'bp_thumbnail_resize\s*\(\s*"([^"]+)"\s*,\s*"([^"]*)"\s*\)',
                js_text
            )
            if match:
                raw_url = match.group(1)
                result["title"] = match.group(2)
                # Convert thumbnail URL to a usable size
                # The URL has /s72-c/ (tiny thumbnail); replace with /s320/ for medium
                result["thumbnail_url"] = re.sub(r"/s\d+-c/", "/s320/", raw_url)

        # Fallback: try to find an <img> tag directly (for non-JS entries)
        if not result.get("thumbnail_url"):
            img = entry.find("img")
            if img:
                result["thumbnail_url"] = img.get("src") or img.get("data-src") or ""
                result["title"] = result.get("title") or img.get("alt") or ""

        if result.get("page_url") or result.get("thumbnail_url"):
            results.append(result)

    # Fallback: if no boxim entries found, try other selectors
    if not results:
        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "")
            if "irasutoya.com" in href and "/20" in href:
                img = a_tag.find("img")
                results.append({
                    "page_url": href,
                    "thumbnail_url": img["src"] if img and img.get("src") else "",
                    "title": img.get("alt", "") if img else a_tag.get_text(strip=True)[:50],
                })
                if len(results) >= limit:
                    break

    return results


def get_full_image_url(page_url: str) -> dict:
    """Visit an illustration detail page and extract the full-size image URL.

    Returns dict with: title, full_image_url, tags

    Strategy (in priority order):
    1. og:image meta tag — most reliable, always points to the main illustration
    2. First large blogspot image in the post body
    """
    result = {"title": "", "full_image_url": "", "tags": []}

    try:
        resp = requests.get(page_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"ERROR: Failed to fetch page: {e}", file=sys.stderr)
        return result

    soup = BeautifulSoup(resp.text, "html.parser")

    # --- Get the main illustration image ---
    # Primary: og:image meta tag (always present on IRASUTOYA detail pages)
    og_img = soup.find("meta", property="og:image")
    if og_img and og_img.get("content"):
        og_url = og_img["content"]
        # Convert social-preview size to full original size
        # og:image has /w1200-h630-p-k-no-nu/ or similar; replace with /s0/
        full_url = re.sub(r"/w\d+-h\d+[^/]*/", "/s0/", og_url)
        full_url = re.sub(r"/s\d+/", "/s0/", full_url)
        result["full_image_url"] = full_url

    # Fallback: find the largest blogspot image in post body
    if not result["full_image_url"]:
        post_content = (
            soup.select_one("div.entry-content") or
            soup.select_one("div.post-body") or
            soup.select_one("article") or
            soup
        )
        best_width = 0
        for img in post_content.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if "bp.blogspot.com" in src or "blogger.googleusercontent.com" in src:
                full_src = re.sub(r"/s\d+/", "/s0/", src)
                size_match = re.search(r"/s(\d+)/", src)
                width = int(size_match.group(1)) if size_match else 0
                if width >= best_width:
                    best_width = width
                    result["full_image_url"] = full_src

    # --- Get the page title ---
    # Look for h2 that's NOT a generic sidebar/nav title
    # Sidebar titles are typically short navigation labels; real titles contain "イラスト"
    sidebar_keywords = {"検索", "カテゴリ", "人気", "プロフィール", "アーカイブ", "コメント"}
    for h2 in soup.find_all("h2"):
        text = h2.get_text(strip=True)
        if not text or len(text) <= 3:
            continue
        # Skip if it looks like a sidebar/nav element
        if any(kw in text for kw in sidebar_keywords):
            continue
        result["title"] = text
        break

    # Fallback: og:title
    if not result["title"]:
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            result["title"] = og_title["content"]

    # --- Extract tags/labels ---
    tag_elements = (
        soup.select("span.labels a") or
        soup.select("a[rel='tag']") or
        soup.select(".post-labels a")
    )
    result["tags"] = [t.get_text(strip=True) for t in tag_elements]

    return result


def download_image(url: str, output_path: str) -> bool:
    """Download an image from URL to output_path."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, stream=True)
        resp.raise_for_status()

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except requests.RequestException as e:
        print(f"ERROR: Failed to download image: {e}", file=sys.stderr)
        return False


def pick_best_match(keyword: str, results: list[dict]) -> dict | None:
    """Pick the most relevant result based on keyword matching in title."""
    if not results:
        return None

    scored = []
    for r in results:
        score = 0
        title = r.get("title", "")
        # Exact keyword match in title
        if keyword in title:
            score += 10
        # Partial match
        for char in keyword:
            if char in title:
                score += 1
        scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1] if scored else results[0]


def main():
    parser = argparse.ArgumentParser(
        description="Search and download illustrations from IRASUTOYA"
    )
    parser.add_argument("keyword", help="Search keyword (Japanese)")
    parser.add_argument("--output", "-o", default=".", help="Output directory (default: current)")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Max search results to fetch")
    parser.add_argument("--list-only", action="store_true", help="List results without downloading")
    parser.add_argument("--index", "-i", type=int, default=0, help="Download specific result by index (0-based)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    # Search
    print(f"Searching IRASUTOYA for: {args.keyword}", file=sys.stderr)
    results = search_irasutoya(args.keyword, limit=args.limit)

    if not results:
        print("No results found.", file=sys.stderr)
        sys.exit(1)

    # Get full image URLs for each result
    enriched = []
    for i, r in enumerate(results):
        print(f"  Fetching details [{i+1}/{len(results)}]...", file=sys.stderr)
        if r.get("page_url"):
            details = get_full_image_url(r["page_url"])
            r["full_image_url"] = details.get("full_image_url", "")
            r["tags"] = details.get("tags", [])
            if details.get("title") and not r.get("title"):
                r["title"] = details["title"]
        enriched.append(r)
        time.sleep(0.5)  # Be polite to the server

    if args.json:
        print(json.dumps(enriched, ensure_ascii=False, indent=2))
        return

    # List results
    print(f"\nFound {len(enriched)} results:\n", file=sys.stderr)
    for i, r in enumerate(enriched):
        title = r.get("title", "(no title)")
        print(f"  [{i}] {title}", file=sys.stderr)

    if args.list_only:
        return

    # Download
    idx = args.index
    if idx >= len(enriched):
        print(f"ERROR: Index {idx} out of range (max {len(enriched)-1})", file=sys.stderr)
        sys.exit(1)

    target = enriched[idx]
    img_url = target.get("full_image_url") or target.get("thumbnail_url", "")
    if not img_url:
        print("ERROR: No image URL found for this result.", file=sys.stderr)
        sys.exit(1)

    # Determine filename
    title = target.get("title", "irasutoya_image")
    safe_title = re.sub(r'[\\/:*?"<>|]', "_", title)[:80]
    ext = ".png"
    if ".jpg" in img_url.lower() or ".jpeg" in img_url.lower():
        ext = ".jpg"
    filename = f"{safe_title}{ext}"
    output_path = os.path.join(args.output, filename)

    print(f"\nDownloading: {title}", file=sys.stderr)
    print(f"  URL: {img_url}", file=sys.stderr)
    print(f"  -> {output_path}", file=sys.stderr)

    if download_image(img_url, output_path):
        print(f"OK: Saved to {output_path}", file=sys.stderr)
        # Print the path to stdout for easy piping
        print(os.path.abspath(output_path))
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
