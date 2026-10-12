---
name: web-research
description: >
  Web search, news, personality/company/market research via SerpAPI.
  When to search, API budget management, post-search workflow.
  Use when the agent needs current information beyond training cutoff.
when_to_use: "When the user asks about current events, market trends, startup news, founders, investors, competitors, or any topic needing real-time data."
authority: read
cost_tier: 2
version: 0.1.0
---

# Web Research Directive

## Purpose

Search the web for current affairs, startup news, personality/company research, and market intelligence to inform mentoring advice.

## Tools

### General Search

```bash
python .tmp/scripts/web_search.py --mode search --query "3D printing India market 2026"
```

### News

```bash
python .tmp/scripts/web_search.py --mode news --query "Indian startup funding"
```

### Person Research

```bash
python .tmp/scripts/web_search.py --mode person --query "Kunal Shah CRED"
```

### Startup Ecosystem

```bash
python .tmp/scripts/web_search.py --mode startup --query "hardware startups India"
```

### Google Trends

```bash
python .tmp/scripts/web_search.py --mode trends --query "3D printing,additive manufacturing"
```

### Deep Person/Company Research

```bash
python .github/skills/web-research/scripts/personality_research.py --name "Name" --company "Company" --save
python .github/skills/web-research/scripts/personality_research.py --company "Company" --research-type company --save
python .github/skills/web-research/scripts/personality_research.py --industry "3D printing India" --research-type market --save
```

## When to Search

### Always search in these situations:

1. **Person mentioned**: Any founder, investor, or personality Vijay mentions — research them
2. **Industry question**: Market size, trends, competitors
3. **Current events**: If timestamp matters (funding rounds, policy changes, etc.)
4. **Unfamiliar topic**: Anything you're not confident about
5. **Decision support**: When Vijay is deciding, get fresh market context

### Don't search for:

1. Astrological calculations (use local tools)
2. Vijay's own profile (use memory bank)
3. General business frameworks (use your training)
4. Previous conversation context (use memory bank)

## API Budget

- SerpAPI has rate limits. Use efficiently:
  - Combine related queries where possible
  - Use --save to cache results in .tmp/
  - Don't repeat searches within the same session
  - `personality_research.py` uses 4-5 API calls per person — use sparingly

## Post-Search Workflow

1. Run search tool
2. Read raw results (JSON output)
3. Synthesize into actionable insight (you do this, not a script)
4. Present to Vijay with relevance to his situation
5. If the insight is durable, add to `outputs/_memory/insights.md`
6. If about a recurring topic, update `outputs/_memory/startup_context.json`
