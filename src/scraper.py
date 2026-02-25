"""
scraper.py — Page Fetcher & HTML Cleaner
------------------------------------------
For each search result URL:
  1. Fetches raw HTML with a browser-like User-Agent
  2. Strips all noise tags (nav, script, style, footer, header, aside)
  3. Extracts meaningful <p> tag text
  4. Falls back to the snippet description if the page fails
  5. Handles timeouts, connection errors, paywalls, and non-HTML pages

Target: ≥80% of pages yield usable text (>200 chars of clean content).
"""

import re
import time
import requests
from bs4 import BeautifulSoup

# ─── Constants ────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}

# File types that are never HTML — skip them
SKIP_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".mp4", ".mp3", ".zip", ".doc", ".docx", ".xlsx", ".pptx",
}

# Tags to remove entirely (they contain noise, not content)
NOISE_TAGS = [
    "nav", "script", "style", "footer", "header",
    "aside", "advertisement", "iframe", "noscript",
    "form", "button", "select", "option",
]

# CSS class/id patterns that indicate noise
NOISE_PATTERNS = [
    "nav", "menu", "sidebar", "advertisement", "cookie",
    "popup", "banner", "footer", "header", "social",
    "share", "related", "comment", "widget", "promo",
]

MAX_TEXT_LENGTH = 6000   # Characters to keep per page
MIN_TEXT_LENGTH = 150    # Minimum chars to consider a page "usable"


# ─── Public entry point ───────────────────────────────────────────────────────

def fetch_and_clean(search_results: list[dict], max_workers: int = 8) -> list[dict]:
    """
    Fetch and clean content for a list of search result dicts — CONCURRENTLY.
    Uses ThreadPoolExecutor so all pages are fetched in parallel instead of one-by-one.

    Args:
        search_results: List from search.py [{title, url, description, ...}]
        max_workers:    Number of parallel fetch threads (default 8)

    Returns:
        List of dicts: [{url, title, text, status}]
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def process_one(result: dict) -> dict:
        url = (result.get("url") or "").strip()
        title = result.get("title", "")
        description = result.get("description", "")

        if not url:
            return None

        url_lower = url.lower().split("?")[0]
        if any(url_lower.endswith(ext) for ext in SKIP_EXTENSIONS):
            return _make_result(url, title, description, "skipped_extension")

        html = _fetch_page(url)
        if html is None:
            return _make_result(url, title, description, "fallback_fetch_failed")

        text = _clean_html(html)
        if len(text) >= MIN_TEXT_LENGTH:
            return _make_result(url, title, text, "success")
        else:
            fallback = description if description else text
            return _make_result(url, title, fallback, "fallback_thin_content")

    cleaned_pages = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_one, r): r for r in search_results}
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                cleaned_pages.append(result)

    success_count = sum(1 for p in cleaned_pages if p["status"] == "success")
    print(f"[scraper.py] Done. {success_count}/{len(cleaned_pages)} pages fully extracted.")
    return cleaned_pages


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _fetch_page(url: str, timeout: int = 10) -> str | None:
    """Fetch raw HTML. Returns None on any failure."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            print(f"[scraper.py]   Skipping non-HTML content-type: {content_type[:40]}")
            return None

        return response.text

    except requests.exceptions.Timeout:
        print(f"[scraper.py]   Timeout: {url[:50]}")
    except requests.exceptions.ConnectionError:
        print(f"[scraper.py]   Connection error: {url[:50]}")
    except requests.exceptions.TooManyRedirects:
        print(f"[scraper.py]   Too many redirects: {url[:50]}")
    except requests.exceptions.HTTPError as e:
        print(f"[scraper.py]   HTTP {e.response.status_code}: {url[:50]}")
    except Exception as e:
        print(f"[scraper.py]   Unexpected: {str(e)[:60]}")

    return None


def _clean_html(html: str) -> str:
    """
    Strip noise from HTML and extract readable content.

    Strategy:
      1. Remove all noise tags entirely
      2. Remove elements with noise-indicating class/id names
      3. Extract all <p> tags with meaningful text
      4. Fall back to article/main/body if paragraphs are sparse
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise tags
    for tag_name in NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Remove noise by class/id patterns
    for tag in soup.find_all(True):
        # Guard: some BS4 tags have attrs=None instead of {}
        if not isinstance(getattr(tag, "attrs", None), dict):
            continue
        classes = " ".join(tag.get("class", []) or []).lower()
        tag_id = (tag.get("id") or "").lower()
        combined = classes + " " + tag_id
        if any(pattern in combined for pattern in NOISE_PATTERNS):
            tag.decompose()

    # Extract paragraphs with meaningful content
    paragraphs = soup.find_all("p")
    text = " ".join(
        p.get_text(separator=" ", strip=True)
        for p in paragraphs
        if len(p.get_text(strip=True)) > 40
    )

    # Fallback to article/main if paragraphs are thin
    if len(text) < MIN_TEXT_LENGTH:
        for selector in ["article", "main", "[role='main']", "body"]:
            try:
                element = soup.select_one(selector)
            except Exception:
                element = soup.find(selector)
            if element:
                candidate = element.get_text(separator=" ", strip=True)
                if len(candidate) > len(text):
                    text = candidate
                    break

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Truncate
    return text[:MAX_TEXT_LENGTH]


def _make_result(url: str, title: str, text: str, status: str) -> dict:
    return {"url": url, "title": title, "text": text, "status": status}