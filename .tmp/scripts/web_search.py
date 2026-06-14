#!/usr/bin/env python3
"""
Web Search via SerpAPI

Searches Google for current affairs, startup ecosystem news, market trends,
personality profiles, and astrological transits.

Modes:
    search    - General web search
    news      - Google News search
    person    - Research a specific person/founder
    startup   - Search startup ecosystem news (India + global)
    trends    - Google Trends data

Usage:
    python web_search.py --mode search --query "3D printing industry India 2026"
    python web_search.py --mode news --query "Indian startup funding latest"
    python web_search.py --mode person --query "Vijay Varada Fracktal Works"
    python web_search.py --mode startup --query "hardware startups India"
    python web_search.py --mode trends --query "3D printing,additive manufacturing"
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

try:
    from serpapi import GoogleSearch
except ImportError:
    print("Installing google-search-results (SerpAPI)...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-search-results"])
    from serpapi import GoogleSearch

SCRIPT_DIR = Path(__file__).parent.resolve()
# .tmp/scripts/ → .tmp/ → repo root
REPO_ROOT = SCRIPT_DIR.parent.parent
TMP_DIR = REPO_ROOT / ".tmp"


def get_api_key():
    """Get SerpAPI key from environment."""
    key = os.getenv("SERPAPI_API_KEY")
    if not key:
        print("Error: SERPAPI_API_KEY not set in .env")
        sys.exit(1)
    return key


def search_google(query, num_results=10, location="India", language="en"):
    """
    General Google search.

    Returns structured results with titles, snippets, and links.
    """
    params = {
        "engine": "google",
        "q": query,
        "api_key": get_api_key(),
        "num": num_results,
        "location": location,
        "hl": language,
        "gl": "in"  # India
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    organic = []
    for r in results.get("organic_results", []):
        organic.append({
            "title": r.get("title"),
            "link": r.get("link"),
            "snippet": r.get("snippet"),
            "position": r.get("position"),
            "date": r.get("date")
        })

    related_questions = []
    for q in results.get("related_questions", []):
        related_questions.append({
            "question": q.get("question"),
            "snippet": q.get("snippet"),
            "link": q.get("link")
        })

    knowledge_graph = None
    if "knowledge_graph" in results:
        kg = results["knowledge_graph"]
        knowledge_graph = {
            "title": kg.get("title"),
            "type": kg.get("type"),
            "description": kg.get("description"),
            "source": kg.get("source", {}).get("link")
        }

    return {
        "query": query,
        "results": organic,
        "related_questions": related_questions,
        "knowledge_graph": knowledge_graph,
        "total_results": results.get("search_information", {}).get("total_results"),
        "timestamp": datetime.now().isoformat()
    }


def search_news(query, num_results=10):
    """
    Google News search for latest updates.
    """
    params = {
        "engine": "google_news",
        "q": query,
        "api_key": get_api_key(),
        "gl": "in",
        "hl": "en"
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    news_results = []
    for item in results.get("news_results", []):
        news_results.append({
            "title": item.get("title"),
            "link": item.get("link"),
            "source": item.get("source", {}).get("name") if isinstance(item.get("source"), dict) else item.get("source"),
            "date": item.get("date"),
            "snippet": item.get("snippet")
        })

    return {
        "query": query,
        "news_results": news_results[:num_results],
        "timestamp": datetime.now().isoformat()
    }


def research_person(name, num_results=15):
    """
    Research a person — founder, investor, mentor, etc.
    Combines multiple searches for comprehensive profile.
    """
    results = {}

    # Main search
    main_search = search_google(f"{name}", num_results=num_results)
    results["main"] = main_search

    # LinkedIn search
    linkedin_search = search_google(f"{name} site:linkedin.com", num_results=3)
    results["linkedin"] = linkedin_search.get("results", [])

    # News mentions
    news = search_news(name, num_results=5)
    results["news"] = news.get("news_results", [])

    # Knowledge graph (from main search)
    results["knowledge_graph"] = main_search.get("knowledge_graph")

    return {
        "person": name,
        "main_results": results["main"]["results"],
        "linkedin_profiles": results["linkedin"],
        "news_mentions": results["news"],
        "knowledge_graph": results["knowledge_graph"],
        "timestamp": datetime.now().isoformat()
    }


def search_startup_ecosystem(query, num_results=10):
    """
    Search startup ecosystem news — India and global.
    Combines curated queries for better context.
    """
    results = {}

    # Main query
    results["main"] = search_google(query, num_results=num_results)

    # India-specific
    india_query = f"{query} India startup ecosystem"
    results["india"] = search_google(india_query, num_results=5)

    # Funding and investor news
    funding_query = f"{query} funding investment 2026"
    results["funding"] = search_google(funding_query, num_results=5)

    # Latest news
    results["news"] = search_news(query, num_results=5)

    return {
        "query": query,
        "main_results": results["main"]["results"],
        "india_specific": results["india"]["results"],
        "funding_news": results["funding"]["results"],
        "latest_news": results["news"]["news_results"],
        "timestamp": datetime.now().isoformat()
    }


def search_trends(keywords, timeframe="today 12-m", geo="IN"):
    """
    Google Trends data for keywords.

    Args:
        keywords: Comma-separated keywords (max 5)
        timeframe: "today 12-m", "today 3-m", "today 5-y", etc.
        geo: Country code ("IN" for India, "US", etc.)
    """
    params = {
        "engine": "google_trends",
        "q": keywords,
        "api_key": get_api_key(),
        "date": timeframe,
        "geo": geo
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    interest_over_time = results.get("interest_over_time", {})
    related_queries = results.get("related_queries", {})

    return {
        "keywords": keywords,
        "geo": geo,
        "timeframe": timeframe,
        "interest_over_time": interest_over_time,
        "related_queries": related_queries,
        "timestamp": datetime.now().isoformat()
    }


def save_results(data, filename):
    """Save search results to .tmp/"""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    filepath = TMP_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Results saved to {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Web Search via SerpAPI")
    parser.add_argument("--mode", type=str, required=True,
                       choices=["search", "news", "person", "startup", "trends"],
                       help="Search mode")
    parser.add_argument("--query", "-q", type=str, required=True, help="Search query")
    parser.add_argument("--num", type=int, default=10, help="Number of results")
    parser.add_argument("--save", action="store_true", help="Save results to .tmp/")
    parser.add_argument("--json-only", action="store_true", help="Output JSON only")

    args = parser.parse_args()

    if args.mode == "search":
        results = search_google(args.query, args.num)
    elif args.mode == "news":
        results = search_news(args.query, args.num)
    elif args.mode == "person":
        results = research_person(args.query, args.num)
    elif args.mode == "startup":
        results = search_startup_ecosystem(args.query, args.num)
    elif args.mode == "trends":
        results = search_trends(args.query)

    if args.json_only:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(results, indent=2, ensure_ascii=False))

    if args.save:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_results(results, f"search_{args.mode}_{timestamp}.json")


if __name__ == "__main__":
    main()
