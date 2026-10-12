#!/usr/bin/env python3
"""
Memory Bank Manager

Persistent memory system for the Startup Guru agent. Stores and retrieves:
- Founder profile (personal details, skills, background)
- Birth chart data
- Startup context (current projects, stage, challenges)
- Interaction log (past conversations, advice given)
- Decision journal (decisions, timing, outcomes)
- Accumulated insights

All data is stored as JSON in the memory/ directory and Markdown for insights.

Usage:
    python memory_bank.py --read founder_profile
    python memory_bank.py --read all
    python memory_bank.py --update founder_profile --key "name" --value "Vijay Raghav Varada"
    python memory_bank.py --update startup_context --data '{"stage": "growth"}'
    python memory_bank.py --log-interaction --summary "Discussed funding strategy"
    python memory_bank.py --log-decision --decision "Pursue Series A" --context "Jupiter transit 9th house"
    python memory_bank.py --add-insight "Hardware startups in India need 2x runway"
    python memory_bank.py --search "funding"
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
# .github/skills/memory-management/scripts/ → memory-management/ → skills/ → .github/ → repo root
REPO_ROOT = SCRIPT_DIR.parent.parent.parent.parent
MEMORY_DIR = REPO_ROOT / "outputs" / "_memory"

MEMORY_FILES = {
    "founder_profile": "founder_profile.json",
    "birth_chart": "birth_chart.json",
    "startup_context": "startup_context.json",
    "interaction_log": "interaction_log.json",
    "decision_journal": "decision_journal.json",
    "insights": "insights.md",
    "interaction_archive": "interaction_archive.json",
}

# Not part of `--read all`: archived history is searched via memory_db.py, not preloaded.
ARCHIVE_ONLY = {"interaction_archive"}

DEFAULT_REVIEW_DAYS = 30


# ---------------------------------------------------------------------------
# SQLite mirror. JSON stays the source of truth; every JSON write is mirrored
# into guru_memory.db so Tier 2 search never goes stale. A mirror failure never
# loses the JSON write, but it is reported loudly (run `memory_db.py sync`).
# ---------------------------------------------------------------------------

def _db():
    sys.path.insert(0, str(SCRIPT_DIR))
    import memory_db
    conn = memory_db.get_db()
    memory_db.init_db(conn)
    return memory_db, conn


def _mirror(label, fn):
    try:
        mdb, conn = _db()
        try:
            fn(mdb, conn)
        finally:
            conn.close()
    except Exception as e:  # noqa: BLE001 - must never lose the JSON write
        print(f"WARNING: SQLite mirror failed for {label}: {e}. "
              f"JSON saved; run `python {Path(__file__).name.replace('memory_bank', 'memory_db')} sync` to repair.",
              file=sys.stderr)


def _csv(items):
    return ",".join(i.strip() for i in (items or []) if i and i.strip())


def ensure_memory_dir():
    """Ensure memory directory exists."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def read_memory(memory_type):
    """
    Read a memory file.

    Args:
        memory_type: One of founder_profile, birth_chart, startup_context,
                     interaction_log, decision_journal, insights

    Returns:
        Contents of the memory file (dict for JSON, string for MD)
    """
    if memory_type not in MEMORY_FILES:
        print(f"Error: Unknown memory type '{memory_type}'. Available: {', '.join(MEMORY_FILES.keys())}")
        return None

    filepath = MEMORY_DIR / MEMORY_FILES[memory_type]

    if not filepath.exists():
        if memory_type not in ARCHIVE_ONLY:
            print(f"Memory file not found: {filepath}")
        return {} if filepath.suffix == ".json" else ""

    if filepath.suffix == ".json":
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    else:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()


def read_all_memory():
    """Read all memory files and return combined state."""
    state = {}
    for memory_type in MEMORY_FILES:
        if memory_type in ARCHIVE_ONLY:
            continue
        state[memory_type] = read_memory(memory_type)
    return state


def write_memory(memory_type, data):
    """
    Write data to a memory file.

    Args:
        memory_type: Memory file key
        data: Dict (for JSON files) or string (for MD files)
    """
    ensure_memory_dir()
    filepath = MEMORY_DIR / MEMORY_FILES[memory_type]

    if filepath.suffix == ".json":
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    else:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(data)

    print(f"Updated memory: {memory_type}")


def update_memory(memory_type, key=None, value=None, data=None):
    """
    Update a specific field or merge data into a memory file.

    Args:
        memory_type: Memory file key
        key: Specific key to update (dot notation supported: "birth.date")
        value: Value for the key
        data: Full dict to merge (alternative to key/value)
    """
    current = read_memory(memory_type)
    if current is None:
        current = {}

    if isinstance(current, str):
        # For markdown files, append data
        if data:
            current += f"\n{data}"
        write_memory(memory_type, current)
        return

    if data:
        if isinstance(data, str):
            data = json.loads(data)
        current = deep_merge(current, data)
    elif key and value is not None:
        set_nested(current, key, value)

    # Add last_updated timestamp
    current["_last_updated"] = datetime.now().isoformat()

    write_memory(memory_type, current)


def deep_merge(base, override):
    """Deep merge two dicts. Override wins on conflicts."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def set_nested(d, key_path, value):
    """Set a value using dot notation path. E.g., 'birth.date' -> d['birth']['date']"""
    keys = key_path.split(".")
    current = d
    for k in keys[:-1]:
        if k not in current or not isinstance(current[k], dict):
            current[k] = {}
        current = current[k]

    # Try to parse value as JSON for complex values
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
        current[keys[-1]] = parsed
    except (json.JSONDecodeError, TypeError):
        current[keys[-1]] = value


def log_interaction(summary, topics=None, advice_given=None, follow_ups=None):
    """
    Log an interaction to the interaction log.

    Args:
        summary: Brief summary of the conversation
        topics: List of topics discussed
        advice_given: List of advice/recommendations given
        follow_ups: List of follow-up items
    """
    log = read_memory("interaction_log")
    if not isinstance(log, dict):
        log = {}
    if "interactions" not in log:
        log["interactions"] = []

    entry = {
        "date": datetime.now().isoformat(),
        "summary": summary,
        "topics": topics or [],
        "advice_given": advice_given or [],
        "follow_ups": follow_ups or [],
        # Monotonic across consolidation (archived entries still count).
        "interaction_number": max(log.get("total_interactions", 0), len(log["interactions"])) + 1
    }

    log["interactions"].append(entry)
    log["total_interactions"] = entry["interaction_number"]
    log["_last_updated"] = datetime.now().isoformat()

    write_memory("interaction_log", log)
    _mirror("interaction", lambda mdb, conn: mdb.log_interaction(
        conn, summary, _csv(topics), _csv(advice_given), _csv(follow_ups),
        json_key=entry["date"], date=entry["date"]))
    return entry


def log_decision(decision, context=None, astrological_timing=None, expected_outcome=None, actual_outcome=None,
                 review_by=None):
    """
    Log a decision to the decision journal.

    Args:
        decision: What was decided
        context: Business context
        astrological_timing: Relevant planetary positions/transits
        expected_outcome: What we expect to happen
        actual_outcome: What actually happened (updated later)
        review_by: YYYY-MM-DD to revisit the outcome (default: today + 30 days)
    """
    journal = read_memory("decision_journal")
    if not isinstance(journal, dict):
        journal = {}
    if "decisions" not in journal:
        journal["decisions"] = []

    entry = {
        "id": len(journal["decisions"]) + 1,
        "date": datetime.now().isoformat(),
        "decision": decision,
        "context": context or "",
        "astrological_timing": astrological_timing or "",
        "expected_outcome": expected_outcome or "",
        "actual_outcome": actual_outcome,
        "review_by": review_by or (datetime.now() + timedelta(days=DEFAULT_REVIEW_DAYS)).strftime("%Y-%m-%d"),
        "status": "pending",
        "outcome_recorded": False
    }

    journal["decisions"].append(entry)
    journal["total_decisions"] = len(journal["decisions"])
    journal["_last_updated"] = datetime.now().isoformat()

    write_memory("decision_journal", journal)
    _mirror("decision", lambda mdb, conn: mdb.log_decision(
        conn, decision, context or "", astrological_timing or "", expected_outcome or "",
        entry["review_by"], json_key=entry["date"], date=entry["date"]))
    return entry


def update_decision_outcome(decision_id, actual_outcome, status="completed"):
    """Update the outcome of a previously logged decision."""
    journal = read_memory("decision_journal")
    if not isinstance(journal, dict) or "decisions" not in journal:
        print("Error: No decision journal found")
        return

    for entry in journal["decisions"]:
        if entry["id"] == decision_id:
            entry["actual_outcome"] = actual_outcome
            entry["status"] = status
            entry["outcome_recorded"] = True
            entry["outcome_date"] = datetime.now().isoformat()
            write_memory("decision_journal", journal)
            print(f"Updated decision #{decision_id} outcome")

            def _sync_outcome(mdb, conn):
                conn.execute("""UPDATE decisions SET actual_outcome=?, status=?, outcome_date=datetime('now')
                                WHERE json_key=? OR (json_key IS NULL AND substr(date,1,10)=?)""",
                             (actual_outcome, status, entry["date"], entry["date"][:10]))
                conn.commit()
            _mirror("decision outcome", _sync_outcome)
            return

    print(f"Decision #{decision_id} not found")


def add_insight(insight_text, category=None):
    """
    Add an insight to the insights file.

    Args:
        insight_text: The insight to record
        category: Optional category (startup, astrology, personal, market, etc.)
    """
    filepath = MEMORY_DIR / "insights.md"

    # Read existing content
    content = ""
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

    # If empty, add header
    if not content.strip():
        content = "# Accumulated Insights\n\n_Lessons learned, patterns observed, and wisdom collected over time._\n\n"

    # Add the insight
    date_str = datetime.now().strftime("%Y-%m-%d")
    category_tag = f" [{category}]" if category else ""
    content += f"\n### {date_str}{category_tag}\n- {insight_text}\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Insight added to {filepath}")
    _mirror("insight", lambda mdb, conn: mdb.add_insight(conn, insight_text, category or "general"))


def consolidate(keep=15):
    """Move all but the newest `keep` interactions to interaction_archive.json so the
    working log stays small. Nothing is deleted: archived entries remain searchable in
    SQLite, and the DB is verified to contain them before anything is moved."""
    log = read_memory("interaction_log")
    items = sorted(log.get("interactions", []), key=lambda e: e.get("date", ""))
    if len(items) <= keep:
        print(f"Nothing to consolidate ({len(items)} interactions <= keep={keep})")
        return 0
    mdb, conn = _db()
    try:
        mdb.sync_from_json(conn)
        old, recent = items[:-keep], items[-keep:]
        for e in old:
            row = conn.execute(
                "SELECT 1 FROM interactions WHERE json_key=? OR (json_key IS NULL AND substr(date,1,10)=?)",
                (e["date"], e["date"][:10])).fetchone()
            if not row:
                raise RuntimeError(f"Aborting: interaction {e['date']} is not in the SQLite index")
    finally:
        conn.close()

    archive = read_memory("interaction_archive") or {}
    archive.setdefault("interactions", [])
    seen = {e["date"] for e in archive["interactions"]}
    archive["interactions"].extend(e for e in old if e["date"] not in seen)
    archive["_last_updated"] = datetime.now().isoformat()
    write_memory("interaction_archive", archive)

    log["interactions"] = recent
    log["total_interactions"] = max(log.get("total_interactions", 0), len(items))
    log["_last_updated"] = datetime.now().isoformat()
    write_memory("interaction_log", log)
    print(f"Archived {len(old)} interactions; {len(recent)} remain in the working log.")
    return len(old)


def search_memory(query):
    """
    Search across all memory files for relevant information.

    Args:
        query: Search term

    Returns:
        Dict of matches by memory type
    """
    query_lower = query.lower()
    results = {}

    for memory_type in MEMORY_FILES:
        data = read_memory(memory_type)
        matches = []

        if isinstance(data, dict):
            matches = _search_dict(data, query_lower)
        elif isinstance(data, str):
            for i, line in enumerate(data.split("\n")):
                if query_lower in line.lower():
                    matches.append({"line": i + 1, "text": line.strip()})

        if matches:
            results[memory_type] = matches

    return results


def _search_dict(d, query, path=""):
    """Recursively search a dict for query matches."""
    matches = []
    for key, value in d.items():
        current_path = f"{path}.{key}" if path else key
        if isinstance(value, dict):
            matches.extend(_search_dict(value, query, current_path))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    matches.extend(_search_dict(item, query, f"{current_path}[{i}]"))
                elif isinstance(item, str) and query in item.lower():
                    matches.append({"path": f"{current_path}[{i}]", "value": item})
        elif isinstance(value, str) and query in value.lower():
            matches.append({"path": current_path, "value": value})
    return matches


def get_memory_summary():
    """Get a brief summary of what's stored in memory."""
    summary = {}
    for memory_type, filename in MEMORY_FILES.items():
        filepath = MEMORY_DIR / filename
        if filepath.exists():
            if filepath.suffix == ".json":
                data = read_memory(memory_type)
                if isinstance(data, dict):
                    summary[memory_type] = {
                        "status": "populated" if len(data) > 1 else "empty",
                        "keys": list(data.keys())[:10],
                        "last_updated": data.get("_last_updated", "unknown")
                    }
                else:
                    summary[memory_type] = {"status": "empty"}
            else:
                content = read_memory(memory_type)
                summary[memory_type] = {
                    "status": "populated" if content.strip() else "empty",
                    "lines": len(content.split("\n")) if content else 0
                }
        else:
            summary[memory_type] = {"status": "not_created"}

    return summary


def main():
    parser = argparse.ArgumentParser(description="Memory Bank Manager")
    parser.add_argument("--read", type=str, help="Read a memory type (or 'all')")
    parser.add_argument("--update", type=str, help="Memory type to update")
    parser.add_argument("--key", type=str, help="Key to update (dot notation)")
    parser.add_argument("--value", type=str, help="Value to set")
    parser.add_argument("--data", type=str, help="JSON data to merge")
    parser.add_argument("--log-interaction", action="store_true", help="Log an interaction")
    parser.add_argument("--summary", type=str, help="Interaction summary")
    parser.add_argument("--topics", type=str, help="Comma-separated topics")
    parser.add_argument("--log-decision", action="store_true", help="Log a decision")
    parser.add_argument("--decision", type=str, help="Decision text")
    parser.add_argument("--context", type=str, help="Decision context")
    parser.add_argument("--timing", type=str, help="Astrological timing context")
    parser.add_argument("--add-insight", type=str, help="Add an insight")
    parser.add_argument("--category", type=str, help="Insight category")
    parser.add_argument("--search", type=str, help="Search all memory for a term")
    parser.add_argument("--status", action="store_true", help="Show memory bank status")
    parser.add_argument("--update-outcome", type=int, help="Decision ID to update outcome")
    parser.add_argument("--outcome", type=str, help="Actual outcome text")
    parser.add_argument("--advice", type=str, help="Advice given, ';'-separated (with --log-interaction)")
    parser.add_argument("--follow-ups", type=str, help="Follow-up items, ';'-separated (with --log-interaction)")
    parser.add_argument("--expected", type=str, help="Expected outcome (with --log-decision)")
    parser.add_argument("--review-by", type=str, help="YYYY-MM-DD to revisit a decision (default +30d)")
    parser.add_argument("--remember", type=str, help="Store a dated, searchable fact")
    parser.add_argument("--entity", type=str, help="Entity the fact is about (with --remember)")
    parser.add_argument("--supersedes", type=int, help="Fact ID this new fact replaces (with --remember)")
    parser.add_argument("--add-commitment", type=str, help="Record an open commitment / follow-up")
    parser.add_argument("--due", type=str, help="YYYY-MM-DD due date (with --add-commitment)")
    parser.add_argument("--close-commitment", type=int, help="Commitment ID to close")
    parser.add_argument("--dropped", action="store_true", help="Close as dropped instead of done")
    parser.add_argument("--note", type=str, default="", help="Note when closing a commitment")
    parser.add_argument("--consolidate", action="store_true", help="Archive old interactions (keeps newest N)")
    parser.add_argument("--keep", type=int, default=15, help="Interactions to keep with --consolidate")
    parser.add_argument("--sync", action="store_true", help="Backfill SQLite from the JSON files")

    args = parser.parse_args()

    if args.read:
        if args.read == "all":
            data = read_all_memory()
        else:
            data = read_memory(args.read)
        print(json.dumps(data, indent=2, ensure_ascii=False) if isinstance(data, dict) else data)

    elif args.update:
        update_memory(args.update, key=args.key, value=args.value, data=args.data)

    elif args.log_interaction:
        if not args.summary:
            print("Error: --summary required for logging interaction")
            sys.exit(1)
        split = lambda s: [x.strip() for x in s.split(";") if x.strip()] if s else []  # noqa: E731
        topics = [x.strip() for x in args.topics.split(",") if x.strip()] if args.topics else []
        entry = log_interaction(args.summary, topics=topics, advice_given=split(args.advice),
                                follow_ups=split(args.follow_ups))
        print(json.dumps(entry, indent=2))

    elif args.log_decision:
        if not args.decision:
            print("Error: --decision required")
            sys.exit(1)
        entry = log_decision(args.decision, context=args.context, astrological_timing=args.timing,
                             expected_outcome=args.expected, review_by=args.review_by)
        print(json.dumps(entry, indent=2))

    elif args.update_outcome and args.outcome:
        update_decision_outcome(args.update_outcome, args.outcome)

    elif args.remember:
        mdb, conn = _db()
        try:
            mdb.add_fact(conn, args.remember, args.category or "general", args.entity or "",
                         supersedes=args.supersedes)
        finally:
            conn.close()

    elif args.add_commitment:
        mdb, conn = _db()
        try:
            mdb.add_commitment(conn, args.add_commitment, args.due)
        finally:
            conn.close()

    elif args.close_commitment:
        mdb, conn = _db()
        try:
            mdb.close_commitment(conn, args.close_commitment, "dropped" if args.dropped else "done", args.note)
        finally:
            conn.close()

    elif args.consolidate:
        consolidate(args.keep)

    elif args.sync:
        mdb, conn = _db()
        try:
            mdb.sync_from_json(conn)
        finally:
            conn.close()

    elif args.add_insight:
        add_insight(args.add_insight, category=args.category)

    elif args.search:
        results = search_memory(args.search)
        print(json.dumps(results, indent=2, ensure_ascii=False))

    elif args.status:
        summary = get_memory_summary()
        print(json.dumps(summary, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
