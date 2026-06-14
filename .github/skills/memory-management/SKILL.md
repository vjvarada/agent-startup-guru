---
name: memory-management
description: >
  Dual-tier persistent memory system for the Startup Guru agent.
  Tier 1 (JSON/Markdown working memory) loaded at session start.
  Tier 2 (SQLite FTS5 long-term memory) queried on demand.
  Memory retrieval routing rules, update protocols, and search best practices.
when_to_use: "At session start, when searching for historical context, logging interactions/decisions, or updating profile/context."
authority: read
cost_tier: 1
version: 0.1.0
---

# Memory Management Directive

## Purpose
Manage persistent memory across sessions so the agent gets smarter over time. Memory is the agent's competitive advantage over generic AI chat.

## Memory Architecture

### Dual Storage Systems

**Primary (JSON + Markdown)** — Agent reads these at session start:

| File | Purpose | Format |
|------|---------|--------|
| `founder_profile.json` | Vijay's personal & professional details | JSON |
| `birth_chart.json` | Calculated Vedic birth chart data | JSON |
| `startup_context.json` | Current projects, stage, challenges, goals, relationships, ventures | JSON |
| `interaction_log.json` | Log of past conversations & advice | JSON |
| `decision_journal.json` | Decisions made with timing & outcomes | JSON |
| `insights.md` | Accumulated wisdom & pattern observations | Markdown |
| `namala_meeting_notes.md` | Full Srinivasan Namala mentorship transcript (March 2026) | Markdown |

**Secondary (SQLite)** — `guru_memory.db` for full-text search across all knowledge:

| Table | Purpose |
|-------|---------|
| `profile` | Key-value founder attributes |
| `interactions` | Detailed conversation logs (22 entries, Mar 2-17) |
| `facts` | Atomic searchable knowledge units |
| `entities` | People, companies, concepts |
| `insights` | Accumulated wisdom |
| `context` | Current state key-value store |

**Relationship:** JSON files are the primary read/write surface. SQLite (`memory_db.py`) is the search engine for when you need to find something specific. When updating memory, update JSON files. Use `memory_db.py search "<query>"` when you need to find historical context across all data.

---

## Memory Retrieval Routing

The agent has two memory tiers. The routing system decides which tier to query for any given need. **Getting this wrong** means either: (a) wasting time searching when the answer is already loaded, or (b) giving incomplete/wrong answers because relevant history wasn't retrieved.

### Tier 1: Working Memory (JSON + Markdown files)
- **Loaded at session start** via `memory_bank.py --read all`
- **Contents:** Current state, recent interactions (last ~10), active challenges, key relationships, goals, birth chart, insights
- **Size:** ~60KB total — fits comfortably in context
- **Latency:** Zero (already in context)
- **Freshness:** Updated in real-time during conversations

### Tier 2: Long-Term Memory (SQLite FTS via `memory_db.py`)
- **Queried on demand** via `memory_db.py search "<query>"`
- **Contents:** 500+ rows — 22 detailed interaction transcripts, 19 entity profiles, 8 facts, 20 insights, 102 context key-values, 325 profile attributes
- **Size:** 400KB indexed with full-text search (FTS5, porter stemming)
- **Latency:** ~1 second per query
- **Freshness:** Captures granular detail from Mar 2-17 sessions that JSON files only summarize

### Routing Decision Tree

When Vijay asks a question or the agent needs context, follow this tree:

```
Is the topic about CURRENT STATE?
  (active deals, current challenges, who's involved now, goals, what should I do)
  → YES: Use Tier 1 (Working Memory). It has the latest.
  → NO: Continue ↓

Is the answer clearly in the loaded JSON files?
  (agent can see the relevant data already in context)
  → YES: Use Tier 1. Don't waste a search.
  → NO: Continue ↓

Does the question reference a SPECIFIC PAST EVENT?
  ("what did we discuss about X?", "when did Y happen?", "what was the exact advice on Z?")
  → YES: Use Tier 2. Search with the key entity/topic as query.
  → NO: Continue ↓

Does the question mention a NAME or ENTITY not in current JSON?
  (someone from an older session, a company researched weeks ago)
  → YES: Use Tier 2. Search by entity name.
  → NO: Continue ↓

Is the question about PATTERNS OVER TIME?
  ("have I dealt with this before?", "what's my track record on X decisions?")
  → YES: Use BOTH. Tier 1 for recent pattern, Tier 2 for historical pattern.
  → NO: Continue ↓

Is the agent about to give STRATEGIC ADVICE on a major decision?
  (pivot, fundraise, partnership, hire/fire, product direction)
  → YES: Use BOTH. Major decisions deserve full context retrieval.
  → NO: Use Tier 1 (default).
```

### Specific Routing Rules

| Situation | Tier | Why |
|-----------|------|-----|
| "What's happening with the Army deal?" | T1 | Current state — in `startup_context.json` |
| "What did Namala say about company structure?" | T2 | Specific past advice — need granular detail |
| "Who is Shailesh Lakhani?" | T1 first, T2 if thin | Profile exists in JSON but SQLite has more detail |
| "Should I take this deal?" | T1 + T2 | Strategic decision — pull full history for similar patterns |
| "What's my Dasha period?" | T1 | In `birth_chart.json` |
| "What happened with Krishna?" | T1 first | In `startup_context.json` team section. T2 only if more detail needed |
| "Have I been in a cash crisis before?" | T2 | Pattern across time — need historical interactions |
| "What's the Toyota spare parts opportunity?" | T2 | Older session (Mar 7) — only in SQLite |
| "Tell me about Applied Additive medical roadmap" | T1 | Migrated to `startup_context.json` in reorganization |
| Vijay mentions a new person → agent checks if already known | T1 scan, T2 search | Check JSON keys first, then search SQLite entities |
| Agent is about to ask Vijay a question | T1 + T2 | Search first to avoid asking something already discussed |

### Pre-Response Memory Check

**Before every substantive response, the agent should internally ask:**

1. **Do I have enough context from working memory to answer this well?**
   - If YES → respond using Tier 1.
   - If NO or UNCERTAIN → search Tier 2 with 1-2 targeted queries before responding.

2. **Am I about to ask Vijay something he already told me?**
   - If the topic rings a bell but you can't find it in loaded JSON → search Tier 2 BEFORE asking.
   - Asking a repeat question is a trust-eroding failure for a "mentor who remembers everything."

3. **Is this topic one we've discussed before but I only see a summary?**
   - JSON `interaction_log.json` has compressed summaries for older sessions.
   - If you need the DETAIL behind a summary → search Tier 2.

### Search Query Best Practices

When searching Tier 2 (`memory_db.py search`):
- **Use the most distinctive keyword**, not generic ones. "Namala daughter company" beats "company structure."
- **Use entity names** for people/company lookups. "Shailesh Lakhani" not "VC who recommended medical."
- **Use `--type` filter** when you know the table: `--type interactions`, `--type entities`, `--type facts`.
- **Use `--after` filter** when you know the approximate time: `--after 2026-03-06`.
- **If first search returns nothing**, try synonyms or related terms. RapidTool = Applied Additive. Ragupathi = Raghupathi = Cavale.

---

### Tool: `.github/skills/memory-management/scripts/memory_bank.py`

#### Read
```bash
python .github/skills/memory-management/scripts/memory_bank.py --read founder_profile      # Read one
python .github/skills/memory-management/scripts/memory_bank.py --read all                   # Read everything
python .github/skills/memory-management/scripts/memory_bank.py --status                     # Check what's populated
```

#### Update Profile
```bash
# Update a specific field (dot notation)
python .github/skills/memory-management/scripts/memory_bank.py --update founder_profile --key "goals.six_month" --value "Launch new product line"

# Merge a JSON object
python .github/skills/memory-management/scripts/memory_bank.py --update startup_context --data '{"stage": "growth", "revenue": "growing"}'
```

#### Log Interactions
```bash
python .github/skills/memory-management/scripts/memory_bank.py --log-interaction --summary "Discussed Series A timing" --topics "funding,timing,jupiter transit"
```

#### Log Decisions
```bash
python .github/skills/memory-management/scripts/memory_bank.py --log-decision --decision "Delay fundraise to Q2" --context "Market conditions uncertain" --timing "Saturn transit 10th house"
```

#### Update Decision Outcomes
```bash
python .github/skills/memory-management/scripts/memory_bank.py --update-outcome 1 --outcome "Good call - market improved by Q2, raised at better terms"
```

#### Add Insights
```bash
python .github/skills/memory-management/scripts/memory_bank.py --add-insight "Hardware startups need 2x runway vs software" --category "startup"
```

#### Search Memory
```bash
python .github/skills/memory-management/scripts/memory_bank.py --search "funding"
```

## Memory Hygiene Protocol

### REAL-TIME UPDATE RULE (CRITICAL)
**Do not wait until the end of a conversation to update memory.** Update memory files immediately when new information is received, in the same response turn. This prevents context loss if a session is interrupted and ensures the agent is always working from the latest state.

**Pattern:**
1. Vijay shares new info → 2. Agent responds with analysis → 3. Agent updates memory files — all in the same turn.

**Triggers for immediate update:**
- New person, company, or relationship mentioned
- Financial data (payments, collections, deal values, debts)
- Deal/project status changes
- Personal life developments
- Strategic decisions or options under consideration
- New insights or patterns
- Changes to goals, priorities, or mood

**Rule of thumb:** If in doubt, write it. Retrieval is cheap. Lost context is expensive.

### After EVERY substantive conversation (final sweep):
1. **Log the interaction** — summary, topics, advice given
2. **Update profile** if any new personal/professional info was shared
3. **Update startup_context** if project status changed
4. **Add insights** if any new pattern or learning emerged
5. **Log decisions** if any decision was made or recommended

### Weekly Review (when prompted or proactively):
1. Read the decision journal — any outcomes to record?
2. Read insights — any patterns emerging?
3. Check interaction log — what topics keep coming up? (indicates persistent concerns)
4. Cross-reference with transit data — any predictions validated?

### Data Quality Rules:
- Never overwrite data without reading existing state first
- Use deep_merge for updates — add, don't replace
- Timestamps on everything
- Keep raw search data in `.tmp/`, synthesized data in `outputs/_memory/`
- The `insights.md` file is append-only (never delete insights)

---

## Self-Organizing Memory Protocol

Memory grows with every session. Without periodic maintenance, files become bloated, duplicated, and hard to parse. This protocol ensures the agent's memory stays clean and useful.

### When to Self-Organize

**Automatic triggers** — run maintenance when ANY of these are true:
1. **Session start, if >5 sessions since last reorganization** — check `_reorganized` timestamp in `startup_context.json`
2. **Any JSON file exceeds 25KB** — the file is too large for efficient context loading
3. **`insights.md` exceeds 20KB** — needs summarization of older entries
4. **Agent detects conflicting data** — two files say different things about the same fact
5. **Vijay explicitly asks** — "organize your memory" or similar

### What Self-Organization Looks Like

#### 1. File Size Audit
```bash
# Check sizes of all memory files
Get-ChildItem outputs/_memory/ -File | Select-Object Name, @{N='SizeKB';E={[math]::Round($_.Length/1KB,1)}}
```

If any file exceeds its threshold, proceed to the relevant restructuring step.

#### 2. startup_context.json — Restructuring Rules
- **Target:** Keep under 25KB
- **Structure:** Must have these top-level sections: `primary_company`, `industry`, `stage`, `current_focus`, `challenges` (categorized), `active_deals`, `debtors_receivables`, `team`, `key_relationships`, `personal`, `strategic_pivot_discussion`, `sls_project`, `applied_additive`, `satellite_opportunity`, `funding_history`, `goals`
- **When too large:** Extract completed/resolved deals into an `_archive` section or separate `outputs/_memory/archive/` file. Remove details of fully collected debtors. Compress old relationship entries that haven't been referenced in 3+ sessions.
- **Never delete:** Active relationships, ongoing deals, current challenges, strategic context

#### 3. insights.md — Summarization Rules
- **Target:** Keep under 20KB
- **Structure:** Chronological, newest at top, each entry dated with `[category]` tags
- **When too large:** Summarize entries older than 60 days into a "Historical Insights Summary" section at the bottom. Keep the original insight's key takeaway as a one-liner. Move verbose analysis to `outputs/_memory/archive/insights_archive.md`.
- **Never delete:** Lessons that are still relevant (even if old), validated predictions, recurring patterns

#### 4. interaction_log.json — Compression Rules
- **Target:** Keep under 15KB
- **When too large:** Compress interactions older than 90 days to summary-only format (remove action_items, reduce summary to 2 sentences). Keep full detail for the last 10 interactions.
- **Never delete:** The interaction entry itself — always keep date + summary at minimum

#### 5. Cross-Reference Audit
At each self-organization cycle, check:
- Are all people mentioned in `startup_context.json` relationships also present in `guru_memory.db` entities? If not, add them.
- Does `interaction_log.json` cover all sessions? No gaps?
- Are `insights.md` entries reflected in the structured JSON where relevant?
- Are any facts in `guru_memory.db` more recent than what's in JSON files? If so, migrate forward.

#### 6. Deduplication
- Check for duplicate entries in `insights.md` (same insight captured twice in different words)
- Check for duplicate entities in `guru_memory.db`
- Check for relationships described in both `startup_context.json` and `founder_profile.json` — keep the detailed version in `startup_context.json`, keep only the name list in `founder_profile.json`

### Self-Organization Log
After every reorganization, update `startup_context.json` with:
```json
"_reorganized": "YYYY-MM-DD — Brief description of what was done"
```

And append to `insights.md`:
```markdown
### YYYY-MM-DD [memory maintenance]
- What was reorganized and why
- Any data quality issues found and fixed
```

## Bootstrapping Memory

For first run, populate these:

### 1. Founder Profile (run once):
```bash
python .github/skills/memory-management/scripts/memory_bank.py --update founder_profile --data '{
  "name": "Vijay Raghav Varada",
  "birth": {
    "date": "1992-06-18",
    "time": "03:30",
    "city": "Secunderabad",
    "state": "Telangana",
    "country": "India",
    "latitude": 17.4399,
    "longitude": 78.4983
  },
  "astrology_preference": "vedic",
  "current_city": "India",
  "education": "Mechatronics Engineering",
  "skills": ["hardware design", "3D printing", "product development", "entrepreneurship", "public speaking", "writing", "open-source hardware"],
  "company": {
    "name": "Fracktal Works",
    "founded": 2011,
    "industry": "3D Printing / Additive Manufacturing",
    "sectors": ["Medicine", "Automotive", "Aerospace", "Architecture", "Education"]
  },
  "achievements": [
    "Founded Fracktal Works at age 19",
    "Hackaday Prize Winner 2017",
    "Hackaday Prize Winner 2018",
    "Antarctica expedition with Robert Swan",
    "3D Printable Wind Turbine (open-source)",
    "Assistive tech for visually impaired (open-source)",
    "TEDx speaker",
    "Published author (multiple languages)"
  ],
  "personality_traits": ["visionary", "inventor", "storyteller", "adventurous", "sustainability-minded"],
  "linkedin_bio": "Meet Vijay Varada, the visionary inventor, storyteller, and entrepreneur at the intersection of art, design, and technology..."
}'
```

### 2. Birth Chart (run once):
```bash
python .github/skills/vedic-astrology/scripts/birth_chart.py --date "1992-06-18" --time "03:30" --lat 17.4399 --lon 78.4983 --city "Secunderabad" --save
```

### 3. Startup Context (update as needed):
```bash
python .github/skills/memory-management/scripts/memory_bank.py --update startup_context --data '{
  "primary_company": "Fracktal Works",
  "stage": "established",
  "current_focus": "Exploring new opportunities and products",
  "challenges": [],
  "goals": {
    "short_term": "Clarity on new product direction",
    "long_term": "To be discussed"
  }
}'
```

## Edge Cases
- If memory files are corrupted: Delete and re-bootstrap
- If memory gets too large (>1MB per file): Archive old interactions
- If conflicting data: Latest update wins, but note the conflict in insights
