# Startup Guru

> Your personal startup mentor blending Vedic astrology, ecosystem intelligence, and persistent memory.

**Built for:** Vijay Raghav Varada, Founder of Fracktal Works

## What This Agent Does

**Startup Guru** is your AI mentor that combines:

- **Vedic Astrology** — Birth chart analysis, Dasha periods, transit timing for decisions
- **Startup Intelligence** — Indian & global ecosystem, hardware/deep-tech expertise
- **Web Research** — Real-time search for market data, news, founder profiles
- **Persistent Memory** — Remembers every conversation and gets smarter over time
- **Decision Journal** — Tracks decisions with astrological timing + actual outcomes

## Quick Start

**Double-click:** `startup-guru.code-workspace`

VS Code will automatically:

1. Open the workspace
2. Prompt to trust the folder (click **Yes**)
3. Run setup (creates venv, installs dependencies)
4. Prompt to install recommended extensions

Then select **"Startup Guru"** from the Copilot Chat agent dropdown.

## First Run

After setup, calculate your birth chart:

```bash
python .tmp/scripts/birth_chart.py --from-profile --save
```

This populates `outputs/_memory/birth_chart.json` with your Vedic natal chart.

## Manual Setup

```powershell
.\setup.ps1        # Windows
./setup.sh         # macOS/Linux
```

Then add your SERPAPI_API_KEY to `.env`.

## Structure

```
startup-guru/
├── startup-guru.code-workspace  # ← Double-click to open!
├── setup.ps1 / setup.sh         # One-command setup
├── AGENTS.md                    # Full system prompt
├── .env                         # API keys (SERPAPI_API_KEY)
├── .github/agents/              # VS Code custom agent config
├── directives/                  # Operating directives (SOPs)
│   ├── startup_mentor.md        # Main playbook
│   ├── vedic_astrology.md       # Astrology interpretation guide
│   ├── memory_management.md     # Memory bank operations
│   └── web_research.md          # Search protocols
├── execution/                   # Python scripts
│   ├── birth_chart.py           # Vedic birth chart calculator
│   ├── transit_calculator.py    # Current planetary transits
│   ├── web_search.py            # Google/News/Trends via SerpAPI
│   ├── personality_research.py  # Person/company/market research
│   └── memory_bank.py           # Persistent memory CRUD
├── memory/                      # Persistent memory bank
│   ├── founder_profile.json     # Your profile
│   ├── birth_chart.json         # Calculated natal chart
│   ├── startup_context.json     # Current projects & goals
│   ├── interaction_log.json     # Conversation history
│   ├── decision_journal.json    # Decisions + outcomes
│   └── insights.md              # Accumulated wisdom
└── .tmp/                        # Temporary search results
```

## Required API Keys

| Key               | Required | Source                                              |
| ----------------- | -------- | --------------------------------------------------- |
| `SERPAPI_API_KEY` | Yes      | [serpapi.com](https://serpapi.com) — for web search |
| `OPENAI_API_KEY`  | No       | Only for standalone mode (Copilot handles AI)       |

## How It Works

1. **You ask a question** — about strategy, timing, a person, a market
2. **Agent reads memory** — loads your profile, chart, past conversations
3. **Agent checks transits** — what planetary weather is affecting you now
4. **Agent researches** — searches web for current market data if needed
5. **Agent advises** — blends business strategy + astrological timing
6. **Agent remembers** — logs the conversation, updates memory for next time

---

_Built on the [DOE Framework](https://github.com/vjvarada/DOE-Framework-Agentic-AI)_
