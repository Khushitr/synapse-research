"""
search.py — Web Search Module
-------------------------------
Calls SerpAPI (primary) or Brave Search API (alternative) for each
generated query. Deduplicates results by URL so we never fetch the
same page twice. Returns a clean list of {title, url, description} dicts.

Free tiers:
  - SerpAPI:      100 searches/month  → https://serpapi.com
  - Brave Search: 2000 queries/month  → https://brave.com/search/api/
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# ─── Public entry point ───────────────────────────────────────────────────────

def search_web(queries: list[str], results_per_query: int = 5) -> list[dict]:
    """
    Search the web for each query string.
    Returns a deduplicated list of result dicts.

    Args:
        queries:            List of search query strings (from agent.py)
        results_per_query:  How many results to request per query (default 5)

    Returns:
        List of dicts: [{title, url, description, query_source}]
    """
    all_results = []
    seen_urls: set[str] = set()

    for query in queries:
        results = _search_single_query(query, results_per_query)
        for result in results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                result["query_source"] = query   # track which query found this
                all_results.append(result)

    print(f"[search.py] Total unique results: {len(all_results)} across {len(queries)} queries")
    return all_results


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _search_single_query(query: str, num_results: int) -> list[dict]:
    """Route to the correct API based on which key is set in .env."""
    if os.getenv("SERPAPI_KEY"):
        return _serpapi_search(query, num_results)
    elif os.getenv("BRAVE_API_KEY"):
        return _brave_search(query, num_results)
    else:
        raise EnvironmentError(
            "No search API key found.\n"
            "Set SERPAPI_KEY or BRAVE_API_KEY in your .env file.\n"
            "  SerpAPI:      https://serpapi.com  (100 free/month)\n"
            "  Brave Search: https://brave.com/search/api  (2000 free/month)"
        )


def _serpapi_search(query: str, num_results: int) -> list[dict]:
    """Fetch results from SerpAPI (Google Search)."""
    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": os.getenv("SERPAPI_KEY"),
        "num": num_results,
        "engine": "google",
        "hl": "en",
        "gl": "us",
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("organic_results", [])[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "description": item.get("snippet", ""),
                "api": "serpapi",
            })
        print(f"[search.py] SerpAPI: {len(results)} results for '{query[:40]}'")
        return results

    except requests.exceptions.HTTPError as e:
        print(f"[search.py] SerpAPI HTTP error: {e}")
        return []
    except Exception as e:
        print(f"[search.py] SerpAPI error: {e}")
        return []


def _brave_search(query: str, num_results: int) -> list[dict]:
    """Fetch results from Brave Search API."""
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": os.getenv("BRAVE_API_KEY"),
    }
    params = {
        "q": query,
        "count": min(num_results, 20),  # Brave max is 20
        "result_filter": "web",
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("web", {}).get("results", [])[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
                "api": "brave",
            })
        print(f"[search.py] Brave: {len(results)} results for '{query[:40]}'")
        return results

    except requests.exceptions.HTTPError as e:
        print(f"[search.py] Brave HTTP error: {e}")
        return []
    except Exception as e:
        print(f"[search.py] Brave error: {e}")
        return []
