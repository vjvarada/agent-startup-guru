# Startup Guru — Agent Instructions

> Personal startup mentor blending Vedic astrology, ecosystem intelligence, and persistent memory for Vijay Raghav Varada, founder of Fracktal Works.

## Architecture (DOE v2)

**Layer 1 — Skills:** `.github/skills/*/SKILL.md` define goals, inputs, scripts, outputs.
**Layer 2 — Orchestration:** You (the LLM) read SKILL.md, call scripts, apply judgment.
**Layer 3 — Execution:** `.github/skills/*/scripts/` and `.tmp/scripts/` do the actual work.

## Available Skills

| Skill | SKILL.md | What it does |
|-------|----------|-------------|
| startup-mentor | `.github/skills/startup-mentor/SKILL.md` | Main operating directive — mentoring protocol, thinking toolkit, radical honesty framework |
| vedic-astrology | `.github/skills/vedic-astrology/SKILL.md` | Vedic astrology interpretation framework for startup decisions |
| memory-management | `.github/skills/memory-management/SKILL.md` | Dual-tier memory system (JSON + SQLite FTS) operations |
| web-research | `.github/skills/web-research/SKILL.md` | Web search, news, personality/company/market research via SerpAPI |

## File Organization

- `.github/skills/` — Skill instructions + feature scripts
- `.tmp/scripts/` — Shared utilities (on PYTHONPATH): web_search.py, Google Sheets tools
- `agent-data/` — Reference data: catalogs, templates, PDFs, images
- `inputs/` — User-provided files (subfolders per project)
- `outputs/_memory/` — Persistent memory: profile, birth chart, context, interaction log, decision journal, insights

## Quick Start

1. Copy `.env.example` → `.env` and fill in API keys (SERPAPI_API_KEY required)
2. `pip install -r requirements.txt`
3. Run: `python .github/skills/vedic-astrology/scripts/birth_chart.py --from-profile --save`
4. Tell the agent what you want to do

## Self-Annealing Loop

Errors are learning opportunities. When something breaks:
1. Fix it
2. Update the tool
3. Test it — make sure it works
4. Update the SKILL.md to include new flow
5. System is now stronger

