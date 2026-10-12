#!/usr/bin/env python3
"""
Session Briefing — a compact (~6-9 KB) snapshot of what the coach must know at the
start of a session, instead of dumping every memory file (~90 KB).

Sections, in priority order:
  1. Who (stable profile essentials)
  2. Freshness warnings (stale memory files)
  3. Open commitments (overdue first)
  4. Decisions awaiting outcome review
  5. Recent sessions + their follow-ups
  6. Current state (focus, challenges, goals, deals) — dated, truncated
  7. Recently learned facts

Everything else stays in Tier 2: `memory_db.py search "<query>"`.

Usage:
    python briefing.py              # print the briefing
    python briefing.py --max-chars 6000
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent.parent.parent.parent
MEMORY_DIR = REPO_ROOT / "outputs" / "_memory"
sys.path.insert(0, str(SCRIPT_DIR))

STALE_DAYS = 14
RECENT_SESSIONS = 3


def _load(name):
    f = MEMORY_DIR / name
    if not f.exists() or not f.read_text(encoding="utf-8").strip():
        return {}
    return json.loads(f.read_text(encoding="utf-8"))


def _parse(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "")).date()
    except (ValueError, TypeError):
        return None


def _age(s, today):
    d = _parse(s)
    return (today - d).days if d else None


def _clip(v, n):
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _flatten(v, prefix=""):
    """Yield (label, text) pairs from nested str/list/dict values."""
    if isinstance(v, dict):
        for k, x in v.items():
            yield from _flatten(x, f"{prefix}{k}: " if not prefix else f"{prefix}{k}: ")
    elif isinstance(v, list):
        for x in v:
            yield from _flatten(x, prefix)
    elif v not in (None, ""):
        yield prefix, str(v)


def section_who(profile):
    b = profile.get("birth", {})
    co = profile.get("company", {})
    lines = [
        f"- **{profile.get('name', '?')}** — {_clip(profile.get('fracktal_title') or co.get('name', ''), 160)}",
        f"- Birth: {b.get('date', '?')} {b.get('time', '')} {b.get('city', '')} (Vedic; chart in birth_chart.json)",
        f"- Education: {profile.get('education', '?')}",
        f"- Mentors: {_clip('; '.join(profile.get('mentors', [])), 200)}",
    ]
    return "## Who\n" + "\n".join(lines)


def section_freshness(today):
    files = {
        "startup_context": _load("startup_context.json"),
        "founder_profile": _load("founder_profile.json"),
        "interaction_log": _load("interaction_log.json"),
    }
    notes, out = [], []
    for name, data in files.items():
        age = _age(data.get("_last_updated"), today)
        out.append(f"{name}: {age}d ago" if age is not None else f"{name}: unknown")
        # A quiet interaction log is a gap in sessions, not outdated facts.
        if name != "interaction_log" and (age is None or age > STALE_DAYS):
            notes.append(name)
    head = "## Memory freshness\n- Last updated — " + "; ".join(out)
    if notes:
        head += ("\n- ⚠ **Stale: " + ", ".join(notes) + ".** Facts there (relationships, deals, personal status) "
                 "may be outdated or contradicted by newer interactions. Verify with Vijay before relying on them, "
                 "and correct them when he confirms.")
    return head


def section_commitments(conn, today):
    from memory_db import list_commitments
    rows = list_commitments(conn)
    if not rows:
        return "## Open commitments\n- None recorded. (Add with `memory_bank.py --add-commitment \"...\" --due YYYY-MM-DD`)"
    lines = []
    for c in rows:
        due = c["due"]
        flag = ""
        if due:
            d = _parse(due)
            if d and d < today:
                flag = f" **OVERDUE {(today - d).days}d**"
        lines.append(f"- #{c['id']} {_clip(c['text'], 200)} (due {due or 'no date'}){flag}")
    return "## Open commitments\n" + "\n".join(lines)


def section_decisions(today):
    decisions = _load("decision_journal.json").get("decisions", [])
    pending = [d for d in decisions if not d.get("outcome_recorded")]
    if not pending:
        return "## Decisions awaiting review\n- None."
    lines = []
    for d in pending:
        age = _age(d.get("date"), today)
        rb = _parse(d.get("review_by"))
        due = (rb and rb <= today) or (rb is None and age is not None and age > 30)
        tag = "**REVIEW DUE**" if due else "pending"
        lines.append(f"- #{d.get('id')} [{tag}, {age}d old] {_clip(d.get('decision', ''), 220)}"
                     + (f" (expected: {_clip(d['expected_outcome'], 100)})" if d.get("expected_outcome") else ""))
    return ("## Decisions awaiting review\n" + "\n".join(lines) +
            "\n- Close with `memory_bank.py --update-outcome ID --outcome \"...\"`. "
            "Ask Vijay how due ones turned out.")


def section_sessions(today):
    items = sorted(_load("interaction_log.json").get("interactions", []), key=lambda e: e.get("date", ""))
    recent = items[-RECENT_SESSIONS:]
    if not recent:
        return "## Recent sessions\n- None."
    lines = []
    for e in recent:
        lines.append(f"- **{str(e.get('date', ''))[:10]}** — {_clip(e.get('summary', ''), 450)}")
        fu = e.get("follow_ups") or []
        if fu:
            lines.append(f"  - Follow-ups: {_clip('; '.join(fu), 250)}")
    return "## Recent sessions (newest last)\n" + "\n".join(lines)


def section_state(ctx):
    lines = []
    for key, n in (("current_focus", 420), ("strategy", 200), ("personal", 200), ("financial_status", 160)):
        if ctx.get(key):
            lines.append(f"- **{key}**: {_clip(ctx[key], n)}")
    ch = [f"{lab}{txt}" for lab, txt in _flatten(ctx.get("challenges", {}))]
    if ch:
        lines.append("- **challenges**: " + " | ".join(_clip(c, 140) for c in ch[:5]))
    goals = ctx.get("goals", {})
    if isinstance(goals, dict):
        for k, v in list(goals.items())[:3]:
            lines.append(f"- **goal/{k}**: {_clip(v, 180)}")
    for key in ("active_deals", "pending_deals"):
        d = ctx.get(key, {})
        if isinstance(d, dict) and d:
            lines.append(f"- **{key}**: " + " | ".join(
                f"{k}: {_clip(v.get('status', v) if isinstance(v, dict) else v, 90)}" for k, v in list(d.items())[:5]))
    return "## Current state (from startup_context.json — check freshness above)\n" + "\n".join(lines)


def section_facts(conn):
    rows = conn.execute("""SELECT id, created_at, entity, content FROM facts
                           WHERE COALESCE(status,'active')='active'
                           ORDER BY created_at DESC, id DESC LIMIT 5""").fetchall()
    if not rows:
        return ""
    lines = [f"- #{r['id']} ({str(r['created_at'])[:10]}){' [' + r['entity'] + ']' if r['entity'] else ''} "
             f"{_clip(r['content'], 180)}" for r in rows]
    return "## Recently learned facts\n" + "\n".join(lines)


FOOTER = """## Digging deeper
- Past events / people / patterns: `python .github/skills/memory-management/scripts/memory_db.py search "<terms>"`
- Full files: `memory_bank.py --read startup_context|decision_journal|interaction_log|insights`
- Write: `--log-interaction` (use --advice/--follow-ups), `--log-decision` (--expected/--review-by), `--remember`, `--add-commitment`"""


def build(max_chars):
    today = date.today()
    out = [f"# Session Briefing — {today.isoformat()}"]
    profile = _load("founder_profile.json")
    ctx = _load("startup_context.json")

    conn = None
    try:
        import memory_db
        conn = memory_db.get_db()
        memory_db.init_db(conn)
    except Exception as e:  # noqa: BLE001
        out.append(f"⚠ SQLite unavailable ({e}); commitments and facts omitted.")

    out.append(section_who(profile))
    out.append(section_freshness(today))
    if conn:
        out.append(section_commitments(conn, today))
    out.append(section_decisions(today))
    out.append(section_sessions(today))
    out.append(section_state(ctx))
    if conn:
        out.append(section_facts(conn))
        conn.close()
    out.append(FOOTER)

    text = "\n\n".join(s for s in out if s)
    if len(text) > max_chars:
        # Drop lowest-priority sections (state, facts) before the high-value ones.
        for drop in ("## Recently learned facts", "## Current state"):
            out = [s for s in out if not s.startswith(drop)]
            text = "\n\n".join(s for s in out if s)
            if len(text) <= max_chars:
                break
        text += "\n\n(Briefing trimmed to fit; use the commands above for more.)"
    return text


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description="Compact session briefing for the Startup Guru coach")
    ap.add_argument("--max-chars", type=int, default=10000)
    args = ap.parse_args()
    print(build(args.max_chars))


if __name__ == "__main__":
    main()
