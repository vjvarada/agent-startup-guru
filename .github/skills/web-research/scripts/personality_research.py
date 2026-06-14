#!/usr/bin/env python3
"""
Personality & Founder Research

Deep research on founders, investors, mentors, and other personalities
relevant to the startup journey. Compiles a dossier from multiple sources.

Usage:
    python personality_research.py --name "Kunal Shah" --role "founder"
    python personality_research.py --name "Balaji Srinivasan" --role "investor"
    python personality_research.py --company "Fracktal Works" --research-type "company"
    python personality_research.py --industry "3D printing India" --research-type "market"
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = Path(__file__).parent.resolve()
# .github/skills/web-research/scripts/ → web-research/ → skills/ → .github/ → repo root
REPO_ROOT = SCRIPT_DIR.parent.parent.parent.parent
TMP_DIR = REPO_ROOT / ".tmp"
TMP_SCRIPTS = TMP_DIR / "scripts"

# web_search.py is a shared utility in .tmp/scripts/
sys.path.insert(0, str(TMP_SCRIPTS))
from web_search import get_api_key, search_google, search_news


def research_founder(name, company=None, num_results=15):
    """
    Compile a comprehensive dossier on a founder/personality.

    Returns structured profile data.
    """
    queries = [
        name,
        f"{name} founder startup",
        f"{name} interview",
        f"{name} site:linkedin.com",
    ]

    if company:
        queries.append(f"{name} {company}")
        queries.append(f"{company} founder CEO")

    all_results = {}
    for query in queries[:4]:  # Limit API calls
        try:
            results = search_google(query, num_results=5)
            all_results[query] = results.get("results", [])
        except Exception as e:
            print(f"Warning: Search failed for '{query}': {e}")

    # News
    try:
        news = search_news(name, num_results=5)
        all_results["news"] = news.get("news_results", [])
    except Exception as e:
        print(f"Warning: News search failed: {e}")
        all_results["news"] = []

    # Compile dossier
    dossier = {
        "name": name,
        "company": company,
        "researched_at": datetime.now().isoformat(),
        "search_results": {},
        "news": all_results.get("news", []),
        "linkedin_results": all_results.get(f"{name} site:linkedin.com", []),
        "summary_prompt": _generate_summary_prompt(name, all_results)
    }

    # Flatten unique results
    seen_urls = set()
    unique_results = []
    for query, results in all_results.items():
        if query == "news":
            continue
        for r in results:
            url = r.get("link", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)
    dossier["search_results"] = unique_results

    return dossier


def research_company(company_name, industry=None, num_results=15):
    """
    Research a company — competitors, market position, news.
    """
    queries = [
        f"{company_name}",
        f"{company_name} products services",
        f"{company_name} competitors",
        f"{company_name} funding revenue",
    ]

    if industry:
        queries.append(f"{industry} market India 2026")

    all_results = {}
    for query in queries[:4]:
        try:
            results = search_google(query, num_results=5)
            all_results[query] = results.get("results", [])
        except Exception as e:
            print(f"Warning: Search failed for '{query}': {e}")

    # News
    try:
        news = search_news(company_name, num_results=5)
        news_results = news.get("news_results", [])
    except:
        news_results = []

    dossier = {
        "company": company_name,
        "industry": industry,
        "researched_at": datetime.now().isoformat(),
        "search_results": {},
        "news": news_results,
        "summary_prompt": _generate_company_prompt(company_name, all_results, news_results)
    }

    # Flatten
    seen = set()
    unique = []
    for q, results in all_results.items():
        for r in results:
            url = r.get("link", "")
            if url and url not in seen:
                seen.add(url)
                unique.append(r)
    dossier["search_results"] = unique

    return dossier


def research_market(industry_query, num_results=10):
    """
    Research a market/industry — trends, players, opportunities.
    """
    queries = [
        f"{industry_query} market size 2026",
        f"{industry_query} India startups",
        f"{industry_query} trends opportunities",
        f"{industry_query} challenges problems",
    ]

    all_results = {}
    for query in queries:
        try:
            results = search_google(query, num_results=5)
            all_results[query] = results.get("results", [])
        except Exception as e:
            print(f"Warning: Search failed for '{query}': {e}")

    news = []
    try:
        n = search_news(industry_query, num_results=5)
        news = n.get("news_results", [])
    except:
        pass

    # Flatten
    seen = set()
    unique = []
    for q, results in all_results.items():
        for r in results:
            url = r.get("link", "")
            if url and url not in seen:
                seen.add(url)
                unique.append(r)

    return {
        "query": industry_query,
        "researched_at": datetime.now().isoformat(),
        "results": unique,
        "news": news,
        "summary_prompt": _generate_market_prompt(industry_query, all_results, news)
    }


def _generate_summary_prompt(name, all_results):
    """Generate a prompt for Copilot to synthesize the research."""
    snippets = []
    for query, results in all_results.items():
        if isinstance(results, list):
            for r in results[:3]:
                if isinstance(r, dict) and r.get("snippet"):
                    snippets.append(r["snippet"])

    snippet_text = "\n".join(f"- {s}" for s in snippets[:15])
    return f"""Based on the following search results about {name}, create a concise profile:

{snippet_text}

Please synthesize into:
1. **Background**: Who they are, education, career path
2. **Key Achievements**: Notable accomplishments
3. **Philosophy/Approach**: Their thinking style and values
4. **Relevance**: How they might be relevant as a mentor/connection for a hardware startup founder
5. **Key Quotes/Ideas**: Any notable quotes or frameworks they've shared"""


def _generate_company_prompt(company, all_results, news):
    """Generate prompt for company analysis."""
    snippets = []
    for query, results in all_results.items():
        if isinstance(results, list):
            for r in results[:3]:
                if isinstance(r, dict) and r.get("snippet"):
                    snippets.append(r["snippet"])

    snippet_text = "\n".join(f"- {s}" for s in snippets[:15])
    return f"""Based on the following search results about {company}, create a company analysis:

{snippet_text}

Please synthesize into:
1. **Overview**: What they do, products/services
2. **Market Position**: Where they stand in the market
3. **Competitors**: Key competitors
4. **Recent News**: Any recent developments
5. **Strategic Assessment**: Strengths, weaknesses, opportunities"""


def _generate_market_prompt(query, all_results, news):
    """Generate prompt for market analysis."""
    snippets = []
    for q, results in all_results.items():
        if isinstance(results, list):
            for r in results[:3]:
                if isinstance(r, dict) and r.get("snippet"):
                    snippets.append(r["snippet"])

    snippet_text = "\n".join(f"- {s}" for s in snippets[:15])
    return f"""Based on the following search results about "{query}", create a market analysis:

{snippet_text}

Please synthesize into:
1. **Market Size & Growth**: Current size and projections
2. **Key Players**: Major companies and startups
3. **Trends**: Important trends shaping the market
4. **Opportunities**: Gaps and opportunities
5. **Challenges**: Key challenges and barriers
6. **India-Specific**: Unique aspects of the Indian market"""


def save_dossier(data, label):
    """Save research dossier to .tmp/"""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = label.lower().replace(" ", "_")[:30]
    filepath = TMP_DIR / f"research_{slug}_{timestamp}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Dossier saved to {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Personality & Founder Research")
    parser.add_argument("--name", type=str, help="Person name to research")
    parser.add_argument("--company", type=str, help="Company name")
    parser.add_argument("--industry", type=str, help="Industry/market to research")
    parser.add_argument("--role", type=str, default="founder",
                       choices=["founder", "investor", "mentor", "competitor"],
                       help="Role of the person")
    parser.add_argument("--research-type", type=str, default="person",
                       choices=["person", "company", "market"],
                       help="Type of research")
    parser.add_argument("--save", action="store_true", help="Save dossier to .tmp/")
    parser.add_argument("--json-only", action="store_true", help="JSON output only")

    args = parser.parse_args()

    if args.research_type == "person" and args.name:
        result = research_founder(args.name, company=args.company)
        label = args.name
    elif args.research_type == "company" and args.company:
        result = research_company(args.company, industry=args.industry)
        label = args.company
    elif args.research_type == "market" and args.industry:
        result = research_market(args.industry)
        label = args.industry
    else:
        print("Error: Provide --name (for person), --company (for company), or --industry (for market)")
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.save:
        save_dossier(result, label)


if __name__ == "__main__":
    main()
