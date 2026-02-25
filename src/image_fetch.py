"""
image_fetch.py — Fetch relevant images for a research topic.
Uses Unsplash Source (free, no key) + Wikipedia API as fallback.
Returns list of {url, alt, source} dicts.
"""
import requests, re, json

HEADERS = {"User-Agent": "ResearchAssistant/1.0 (educational project)"}

def fetch_images(query: str, count: int = 3) -> list[dict]:
    images = []
    images += _wikipedia_images(query, count)
    if len(images) < count:
        images += _unsplash_images(query, count - len(images))
    return images[:count]

def _wikipedia_images(query: str, count: int) -> list[dict]:
    try:
        search_url = "https://en.wikipedia.org/w/api.php"
        params = {"action": "query", "list": "search", "srsearch": query,
                  "format": "json", "srlimit": 3}
        r = requests.get(search_url, params=params, headers=HEADERS, timeout=8)
        results = r.json().get("query", {}).get("search", [])
        if not results:
            return []
        
        page_title = results[0]["title"]
        img_params = {
            "action": "query", "titles": page_title, "prop": "pageimages",
            "piprop": "original|thumbnail", "pithumbsize": 800,
            "format": "json", "pilimit": count
        }
        r2 = requests.get(search_url, params=img_params, headers=HEADERS, timeout=8)
        pages = r2.json().get("query", {}).get("pages", {})
        images = []
        for page in pages.values():
            if "original" in page:
                src = page["original"].get("source", "")
                if src and not src.endswith(".svg") and not src.endswith(".ogg"):
                    images.append({"url": src, "alt": page_title, "source": "Wikipedia"})
        return images
    except Exception as e:
        print(f"[image_fetch] Wikipedia error: {e}")
        return []

def _unsplash_images(query: str, count: int) -> list[dict]:
    """Unsplash source API - free, no key needed, random relevant image."""
    slug = query.replace(" ", ",")[:60]
    images = []
    for i in range(count):
        try:
            url = f"https://source.unsplash.com/800x450/?{slug}&sig={i}"
            r = requests.head(url, timeout=6, allow_redirects=True)
            if r.status_code == 200 and "unsplash" in r.url:
                images.append({"url": r.url, "alt": query, "source": "Unsplash"})
        except:
            pass
    return images