#!/usr/bin/env python3
"""
Memory Database — SQLite + FTS5 persistent memory for Startup Guru agent.

Replaces the JSON-file memory bank with a proper searchable database.
Every piece of information is an independently searchable atom.

Usage:
    # Universal search (the main thing agents should use)
    python memory_db.py search "funding RapidTool"
    python memory_db.py search "Ragupathi board dynamics"
    python memory_db.py search "satellite Punarjay"

    # Search with filters
    python memory_db.py search "funding" --type interactions
    python memory_db.py search "Honda" --type facts
    python memory_db.py search "board" --after 2026-03-01

    # Profile operations
    python memory_db.py profile show
    python memory_db.py profile set "goals.short_term" "Land first paid RapidTool license"
    python memory_db.py profile get "company.name"

    # Log an interaction
    python memory_db.py log-interaction --summary "Discussed Series A timing" \\
        --topics "funding,timing,jupiter transit" \\
        --advice "Wait for Mercury sub-period" \\
        --follow-ups "Prepare pitch deck,Research comparable valuations"

    # Log a decision
    python memory_db.py log-decision --decision "Delay fundraise to Q2" \\
        --context "Market conditions uncertain" \\
        --timing "Saturn transit 10th house"

    # Update decision outcome
    python memory_db.py update-outcome 1 "Good call - raised at better terms"

    # Store a fact (atomic piece of knowledge)
    python memory_db.py add-fact "Honda is interested in RapidTool for fixture automation" \\
        --category "business" --entity "Honda" --tags "enterprise,customer,manufacturing"

    # Store an entity (person, company, concept)
    python memory_db.py add-entity "Shailesh Lakhani" --type person \\
        --details "Ex-MD Peak XV Partners. Left Feb 2025. Raising deep-tech fund."

    # Add an insight
    python memory_db.py add-insight "Hardware startups need 2x runway vs software" --category startup

    # Store/retrieve context (current state)
    python memory_db.py context show
    python memory_db.py context set "fracktal.stage" "pivoting to tooling bundle"
    python memory_db.py context get "rapidtool.status"

    # Database health
    python memory_db.py status
    python memory_db.py rebuild-fts

    # Migration from old JSON
    python memory_db.py migrate
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from textwrap import dedent

SCRIPT_DIR = Path(__file__).parent.resolve()
# .github/skills/memory-management/scripts/ → memory-management/ → skills/ → .github/ → repo root
REPO_ROOT = SCRIPT_DIR.parent.parent.parent.parent
MEMORY_DIR = REPO_ROOT / "outputs" / "_memory"
DB_PATH = MEMORY_DIR / "guru_memory.db"


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

def get_db(db_path=None):
    """Get a connection to the memory database."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn):
    """Create all tables and FTS indexes if they don't exist."""
    conn.executescript(dedent("""\
        -- =============================================
        -- PROFILE: Key-value store for founder profile
        -- =============================================
        CREATE TABLE IF NOT EXISTS profile (
            key         TEXT PRIMARY KEY,
            value       TEXT NOT NULL,
            category    TEXT DEFAULT 'general',
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        -- =============================================
        -- INTERACTIONS: Conversation log
        -- =============================================
        CREATE TABLE IF NOT EXISTS interactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL DEFAULT (datetime('now')),
            summary     TEXT NOT NULL,
            topics      TEXT DEFAULT '',          -- comma-separated
            advice      TEXT DEFAULT '',
            follow_ups  TEXT DEFAULT '',
            raw_data    TEXT DEFAULT ''            -- full JSON if needed
        );

        -- =============================================
        -- DECISIONS: Decision journal with outcomes
        -- =============================================
        CREATE TABLE IF NOT EXISTS decisions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            date                TEXT NOT NULL DEFAULT (datetime('now')),
            decision            TEXT NOT NULL,
            context             TEXT DEFAULT '',
            astrological_timing TEXT DEFAULT '',
            expected_outcome    TEXT DEFAULT '',
            actual_outcome      TEXT DEFAULT '',
            status              TEXT DEFAULT 'pending',
            outcome_date        TEXT DEFAULT NULL
        );

        -- =============================================
        -- FACTS: Atomic searchable knowledge units
        -- This is the KEY table for agent searchability.
        -- Every discrete piece of information = one row.
        -- =============================================
        CREATE TABLE IF NOT EXISTS facts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            content     TEXT NOT NULL,
            category    TEXT DEFAULT 'general',   -- business, personal, astrology, market, team, investor, product
            entity      TEXT DEFAULT '',           -- primary entity this fact is about
            tags        TEXT DEFAULT '',            -- comma-separated tags
            source      TEXT DEFAULT '',            -- where this fact came from
            confidence  TEXT DEFAULT 'confirmed',  -- confirmed, inferred, outdated
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        -- =============================================
        -- ENTITIES: People, companies, concepts
        -- =============================================
        CREATE TABLE IF NOT EXISTS entities (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            type        TEXT DEFAULT 'person',     -- person, company, product, concept, institution
            details     TEXT DEFAULT '',
            tags        TEXT DEFAULT '',
            first_mentioned TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        -- =============================================
        -- INSIGHTS: Accumulated wisdom (append-only)
        -- =============================================
        CREATE TABLE IF NOT EXISTS insights (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            content     TEXT NOT NULL,
            category    TEXT DEFAULT 'general',
            date        TEXT DEFAULT (datetime('now'))
        );

        -- =============================================
        -- CONTEXT: Current state (like startup_context.json)
        -- Key-value store for mutable current state
        -- =============================================
        CREATE TABLE IF NOT EXISTS context (
            key         TEXT PRIMARY KEY,
            value       TEXT NOT NULL,
            category    TEXT DEFAULT 'general',
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        -- =============================================
        -- FTS5 VIRTUAL TABLES — The search engine
        -- One FTS table per content table for ranked search
        -- =============================================

        CREATE VIRTUAL TABLE IF NOT EXISTS fts_interactions USING fts5(
            summary, topics, advice, follow_ups,
            content='interactions',
            content_rowid='id',
            tokenize='porter unicode61'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS fts_facts USING fts5(
            content, category, entity, tags,
            content='facts',
            content_rowid='id',
            tokenize='porter unicode61'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS fts_entities USING fts5(
            name, type, details, tags,
            content='entities',
            content_rowid='id',
            tokenize='porter unicode61'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS fts_decisions USING fts5(
            decision, context, astrological_timing, expected_outcome, actual_outcome,
            content='decisions',
            content_rowid='id',
            tokenize='porter unicode61'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS fts_insights USING fts5(
            content, category,
            content='insights',
            content_rowid='id',
            tokenize='porter unicode61'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS fts_profile USING fts5(
            key, value, category,
            content='profile',
            tokenize='porter unicode61'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS fts_context USING fts5(
            key, value, category,
            content='context',
            tokenize='porter unicode61'
        );

        -- =============================================
        -- TRIGGERS to keep FTS indexes in sync
        -- =============================================

        -- interactions triggers
        CREATE TRIGGER IF NOT EXISTS trg_interactions_ai AFTER INSERT ON interactions BEGIN
            INSERT INTO fts_interactions(rowid, summary, topics, advice, follow_ups)
            VALUES (new.id, new.summary, new.topics, new.advice, new.follow_ups);
        END;
        CREATE TRIGGER IF NOT EXISTS trg_interactions_ad AFTER DELETE ON interactions BEGIN
            INSERT INTO fts_interactions(fts_interactions, rowid, summary, topics, advice, follow_ups)
            VALUES ('delete', old.id, old.summary, old.topics, old.advice, old.follow_ups);
        END;
        CREATE TRIGGER IF NOT EXISTS trg_interactions_au AFTER UPDATE ON interactions BEGIN
            INSERT INTO fts_interactions(fts_interactions, rowid, summary, topics, advice, follow_ups)
            VALUES ('delete', old.id, old.summary, old.topics, old.advice, old.follow_ups);
            INSERT INTO fts_interactions(rowid, summary, topics, advice, follow_ups)
            VALUES (new.id, new.summary, new.topics, new.advice, new.follow_ups);
        END;

        -- facts triggers
        CREATE TRIGGER IF NOT EXISTS trg_facts_ai AFTER INSERT ON facts BEGIN
            INSERT INTO fts_facts(rowid, content, category, entity, tags)
            VALUES (new.id, new.content, new.category, new.entity, new.tags);
        END;
        CREATE TRIGGER IF NOT EXISTS trg_facts_ad AFTER DELETE ON facts BEGIN
            INSERT INTO fts_facts(fts_facts, rowid, content, category, entity, tags)
            VALUES ('delete', old.id, old.content, old.category, old.entity, old.tags);
        END;
        CREATE TRIGGER IF NOT EXISTS trg_facts_au AFTER UPDATE ON facts BEGIN
            INSERT INTO fts_facts(fts_facts, rowid, content, category, entity, tags)
            VALUES ('delete', old.id, old.content, old.category, old.entity, old.tags);
            INSERT INTO fts_facts(rowid, content, category, entity, tags)
            VALUES (new.id, new.content, new.category, new.entity, new.tags);
        END;

        -- entities triggers
        CREATE TRIGGER IF NOT EXISTS trg_entities_ai AFTER INSERT ON entities BEGIN
            INSERT INTO fts_entities(rowid, name, type, details, tags)
            VALUES (new.id, new.name, new.type, new.details, new.tags);
        END;
        CREATE TRIGGER IF NOT EXISTS trg_entities_ad AFTER DELETE ON entities BEGIN
            INSERT INTO fts_entities(fts_entities, rowid, name, type, details, tags)
            VALUES ('delete', old.id, old.name, old.type, old.details, old.tags);
        END;
        CREATE TRIGGER IF NOT EXISTS trg_entities_au AFTER UPDATE ON entities BEGIN
            INSERT INTO fts_entities(fts_entities, rowid, name, type, details, tags)
            VALUES ('delete', old.id, old.name, old.type, old.details, old.tags);
            INSERT INTO fts_entities(rowid, name, type, details, tags)
            VALUES (new.id, new.name, new.type, new.details, new.tags);
        END;

        -- decisions triggers
        CREATE TRIGGER IF NOT EXISTS trg_decisions_ai AFTER INSERT ON decisions BEGIN
            INSERT INTO fts_decisions(rowid, decision, context, astrological_timing, expected_outcome, actual_outcome)
            VALUES (new.id, new.decision, new.context, new.astrological_timing, new.expected_outcome, new.actual_outcome);
        END;
        CREATE TRIGGER IF NOT EXISTS trg_decisions_ad AFTER DELETE ON decisions BEGIN
            INSERT INTO fts_decisions(fts_decisions, rowid, decision, context, astrological_timing, expected_outcome, actual_outcome)
            VALUES ('delete', old.id, old.decision, old.context, old.astrological_timing, old.expected_outcome, old.actual_outcome);
        END;
        CREATE TRIGGER IF NOT EXISTS trg_decisions_au AFTER UPDATE ON decisions BEGIN
            INSERT INTO fts_decisions(fts_decisions, rowid, decision, context, astrological_timing, expected_outcome, actual_outcome)
            VALUES ('delete', old.id, old.decision, old.context, old.astrological_timing, old.expected_outcome, old.actual_outcome);
            INSERT INTO fts_decisions(rowid, decision, context, astrological_timing, expected_outcome, actual_outcome)
            VALUES (new.id, new.decision, new.context, new.astrological_timing, new.expected_outcome, new.actual_outcome);
        END;

        -- insights triggers
        CREATE TRIGGER IF NOT EXISTS trg_insights_ai AFTER INSERT ON insights BEGIN
            INSERT INTO fts_insights(rowid, content, category)
            VALUES (new.id, new.content, new.category);
        END;
        CREATE TRIGGER IF NOT EXISTS trg_insights_ad AFTER DELETE ON insights BEGIN
            INSERT INTO fts_insights(fts_insights, rowid, content, category)
            VALUES ('delete', old.id, old.content, old.category);
        END;
        CREATE TRIGGER IF NOT EXISTS trg_insights_au AFTER UPDATE ON insights BEGIN
            INSERT INTO fts_insights(fts_insights, rowid, content, category)
            VALUES ('delete', old.id, old.content, old.category);
            INSERT INTO fts_insights(rowid, content, category)
            VALUES (new.id, new.content, new.category);
        END;
    """))
    conn.commit()


# ---------------------------------------------------------------------------
# Rebuild FTS indexes (for migration or repair)
# ---------------------------------------------------------------------------

def rebuild_fts(conn):
    """Rebuild all FTS indexes from source tables."""
    tables = [
        ("fts_interactions", "interactions", "id", "summary, topics, advice, follow_ups"),
        ("fts_facts", "facts", "id", "content, category, entity, tags"),
        ("fts_entities", "entities", "id", "name, type, details, tags"),
        ("fts_decisions", "decisions", "id", "decision, context, astrological_timing, expected_outcome, actual_outcome"),
        ("fts_insights", "insights", "id", "content, category"),
    ]
    for fts_table, src_table, rowid_col, cols in tables:
        conn.execute(f"INSERT INTO {fts_table}({fts_table}) VALUES('rebuild')")
    conn.commit()
    print("FTS indexes rebuilt.")


# ---------------------------------------------------------------------------
# UNIVERSAL SEARCH — The main agent interface
# ---------------------------------------------------------------------------

def search(conn, query, type_filter=None, after=None, before=None, limit=20):
    """
    Search across ALL memory tables using FTS5 ranked search.
    Returns results sorted by relevance (BM25 score).

    Args:
        query: Natural language search terms. Supports:
               - Simple: "funding"
               - Multi-word: "RapidTool Honda"
               - Phrases: '"board chairman"'
               - Boolean: "funding OR satellite"
               - Prefix: "fund*"
        type_filter: Limit to one type: interactions, facts, entities, decisions, insights, profile, context
        after: Only results after this date (ISO format)
        before: Only results before this date (ISO format)
        limit: Max results per type (default 20)

    Returns:
        List of dicts with: type, id, score, snippet, date, full_data
    """
    results = []

    # Sanitize query for FTS5 — convert natural language to valid FTS query
    fts_query = _sanitize_fts_query(query)

    search_configs = {
        "interactions": {
            "fts": "fts_interactions",
            "src": "interactions",
            "cols": "summary, topics, advice, follow_ups",
            "date_col": "date",
            "display": lambda r: f"[Interaction #{r['id']} - {r['date'][:10]}] {r['summary'][:200]}"
        },
        "facts": {
            "fts": "fts_facts",
            "src": "facts",
            "cols": "content, category, entity, tags",
            "date_col": "created_at",
            "display": lambda r: f"[Fact - {r['category']}] {r['content'][:200]}"
        },
        "entities": {
            "fts": "fts_entities",
            "src": "entities",
            "cols": "name, type, details, tags",
            "date_col": "first_mentioned",
            "display": lambda r: f"[Entity - {r['type']}] {r['name']}: {r['details'][:150]}"
        },
        "decisions": {
            "fts": "fts_decisions",
            "src": "decisions",
            "cols": "decision, context, astrological_timing, expected_outcome, actual_outcome",
            "date_col": "date",
            "display": lambda r: f"[Decision #{r['id']} - {r['status']}] {r['decision'][:200]}"
        },
        "insights": {
            "fts": "fts_insights",
            "src": "insights",
            "cols": "content, category",
            "date_col": "date",
            "display": lambda r: f"[Insight - {r['category']}] {r['content'][:200]}"
        },
        "profile": {
            "fts": "fts_profile",
            "src": "profile",
            "cols": "key, value, category",
            "date_col": "updated_at",
            "display": lambda r: f"[Profile - {r['key']}] {r['value'][:200]}",
            "rowid_is_key": True
        },
        "context": {
            "fts": "fts_context",
            "src": "context",
            "cols": "key, value, category",
            "date_col": "updated_at",
            "display": lambda r: f"[Context - {r['key']}] {r['value'][:200]}",
            "rowid_is_key": True
        },
    }

    types_to_search = [type_filter] if type_filter and type_filter in search_configs else list(search_configs.keys())

    for stype in types_to_search:
        cfg = search_configs[stype]
        is_kv = cfg.get("rowid_is_key", False)

        try:
            if is_kv:
                # For key-value tables (profile, context), search FTS and join
                sql = f"""
                    SELECT s.*, fts.rank
                    FROM {cfg['fts']} fts
                    JOIN {cfg['src']} s ON s.key = fts.key
                    WHERE {cfg['fts']} MATCH ?
                    ORDER BY fts.rank
                    LIMIT ?
                """
            else:
                sql = f"""
                    SELECT s.*, fts.rank
                    FROM {cfg['fts']} fts
                    JOIN {cfg['src']} s ON s.id = fts.rowid
                    WHERE {cfg['fts']} MATCH ?
                    ORDER BY fts.rank
                    LIMIT ?
                """

            rows = conn.execute(sql, (fts_query, limit)).fetchall()

            for row in rows:
                r = dict(row)
                date_val = r.get(cfg["date_col"], "")

                # Apply date filters
                if after and date_val and date_val < after:
                    continue
                if before and date_val and date_val > before:
                    continue

                results.append({
                    "type": stype,
                    "id": r.get("id") or r.get("key"),
                    "score": abs(r.get("rank", 0)),
                    "display": cfg["display"](r),
                    "date": date_val,
                    "data": {k: v for k, v in r.items() if k != "rank"}
                })
        except sqlite3.OperationalError:
            # Table might not have matching content — skip silently
            continue

    # Sort all results by score (lower BM25 rank = better match)
    results.sort(key=lambda x: x["score"])

    return results


def _sanitize_fts_query(query):
    """
    Convert a natural language query into a valid FTS5 query.
    Handles common agent query patterns gracefully.
    """
    # If it already looks like an FTS query (has operators), pass through
    if any(op in query for op in [' OR ', ' AND ', ' NOT ', '"', '*']):
        return query

    # Remove special chars that break FTS5 except quotes and asterisks
    cleaned = re.sub(r'[^\w\s"*]', ' ', query)

    # Split into tokens, remove empties
    tokens = [t.strip() for t in cleaned.split() if t.strip()]

    if not tokens:
        return query

    # Join with implicit AND (FTS5 default) — each word must appear somewhere
    return " ".join(tokens)


# ---------------------------------------------------------------------------
# PROFILE operations
# ---------------------------------------------------------------------------

def profile_set(conn, key, value, category="general"):
    """Set a profile key-value pair. Upserts."""
    # Delete from FTS first if exists
    existing = conn.execute("SELECT key, value, category FROM profile WHERE key = ?", (key,)).fetchone()
    if existing:
        conn.execute(
            "INSERT INTO fts_profile(fts_profile, key, value, category) VALUES('delete', ?, ?, ?)",
            (existing["key"], existing["value"], existing["category"])
        )

    conn.execute("""
        INSERT INTO profile (key, value, category, updated_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, category=excluded.category, updated_at=datetime('now')
    """, (key, value, category))

    # Insert into FTS
    conn.execute(
        "INSERT INTO fts_profile(key, value, category) VALUES(?, ?, ?)",
        (key, value, category)
    )
    conn.commit()


def profile_get(conn, key):
    """Get a profile value by key."""
    row = conn.execute("SELECT * FROM profile WHERE key = ?", (key,)).fetchone()
    return dict(row) if row else None


def profile_show(conn):
    """Show all profile data grouped by category."""
    rows = conn.execute("SELECT * FROM profile ORDER BY category, key").fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# CONTEXT operations (current mutable state)
# ---------------------------------------------------------------------------

def context_set(conn, key, value, category="general"):
    """Set a context key-value pair. Upserts."""
    existing = conn.execute("SELECT key, value, category FROM context WHERE key = ?", (key,)).fetchone()
    if existing:
        conn.execute(
            "INSERT INTO fts_context(fts_context, key, value, category) VALUES('delete', ?, ?, ?)",
            (existing["key"], existing["value"], existing["category"])
        )

    conn.execute("""
        INSERT INTO context (key, value, category, updated_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, category=excluded.category, updated_at=datetime('now')
    """, (key, value, category))

    conn.execute(
        "INSERT INTO fts_context(key, value, category) VALUES(?, ?, ?)",
        (key, value, category)
    )
    conn.commit()


def context_get(conn, key):
    """Get a context value by key."""
    row = conn.execute("SELECT * FROM context WHERE key = ?", (key,)).fetchone()
    return dict(row) if row else None


def context_show(conn):
    """Show all context data."""
    rows = conn.execute("SELECT * FROM context ORDER BY category, key").fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# INTERACTION logging
# ---------------------------------------------------------------------------

def log_interaction(conn, summary, topics="", advice="", follow_ups="", raw_data=""):
    """Log a conversation interaction."""
    cur = conn.execute("""
        INSERT INTO interactions (summary, topics, advice, follow_ups, raw_data)
        VALUES (?, ?, ?, ?, ?)
    """, (summary, topics, advice, follow_ups, raw_data))
    conn.commit()
    print(f"Logged interaction #{cur.lastrowid}")
    return cur.lastrowid


# ---------------------------------------------------------------------------
# DECISION logging
# ---------------------------------------------------------------------------

def log_decision(conn, decision, context="", timing="", expected=""):
    """Log a decision."""
    cur = conn.execute("""
        INSERT INTO decisions (decision, context, astrological_timing, expected_outcome)
        VALUES (?, ?, ?, ?)
    """, (decision, context, timing, expected))
    conn.commit()
    print(f"Logged decision #{cur.lastrowid}")
    return cur.lastrowid


def update_outcome(conn, decision_id, outcome, status="completed"):
    """Update a decision's outcome."""
    conn.execute("""
        UPDATE decisions
        SET actual_outcome = ?, status = ?, outcome_date = datetime('now')
        WHERE id = ?
    """, (outcome, status, decision_id))
    conn.commit()
    print(f"Updated decision #{decision_id}")


# ---------------------------------------------------------------------------
# FACT storage
# ---------------------------------------------------------------------------

def add_fact(conn, content, category="general", entity="", tags="", source="", confidence="confirmed"):
    """Store an atomic fact."""
    cur = conn.execute("""
        INSERT INTO facts (content, category, entity, tags, source, confidence)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (content, category, entity, tags, source, confidence))
    conn.commit()
    print(f"Stored fact #{cur.lastrowid}")
    return cur.lastrowid


# ---------------------------------------------------------------------------
# ENTITY storage
# ---------------------------------------------------------------------------

def add_entity(conn, name, type_="person", details="", tags=""):
    """Store or update an entity."""
    existing = conn.execute("SELECT id FROM entities WHERE name = ?", (name,)).fetchone()
    if existing:
        conn.execute("""
            UPDATE entities SET details = ?, type = ?, tags = ?, updated_at = datetime('now')
            WHERE name = ?
        """, (details, type_, tags, name))
        conn.commit()
        print(f"Updated entity: {name}")
        return existing["id"]
    else:
        cur = conn.execute("""
            INSERT INTO entities (name, type, details, tags)
            VALUES (?, ?, ?, ?)
        """, (name, type_, details, tags))
        conn.commit()
        print(f"Stored entity: {name} (#{cur.lastrowid})")
        return cur.lastrowid


# ---------------------------------------------------------------------------
# INSIGHT storage
# ---------------------------------------------------------------------------

def add_insight(conn, content, category="general"):
    """Store an insight (append-only)."""
    cur = conn.execute("""
        INSERT INTO insights (content, category)
        VALUES (?, ?)
    """, (content, category))
    conn.commit()
    print(f"Stored insight #{cur.lastrowid}")
    return cur.lastrowid


# ---------------------------------------------------------------------------
# STATUS / health check
# ---------------------------------------------------------------------------

def get_status(conn):
    """Get a summary of all memory tables."""
    tables = ["profile", "interactions", "decisions", "facts", "entities", "insights", "context"]
    status = {}
    for table in tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()["c"]
            status[table] = count
        except sqlite3.OperationalError:
            status[table] = "missing"
    return status


# ---------------------------------------------------------------------------
# MIGRATION from old JSON files
# ---------------------------------------------------------------------------

def migrate_from_json(conn):
    """Migrate all existing JSON/MD memory files into the database."""
    print("=" * 60)
    print("MIGRATING FROM JSON FILES TO DATABASE")
    print("=" * 60)

    _migrate_founder_profile(conn)
    _migrate_interactions(conn)
    _migrate_decisions(conn)
    _migrate_insights(conn)
    _migrate_startup_context(conn)
    _migrate_birth_chart(conn)
    _extract_entities_from_context(conn)

    # Rebuild FTS after bulk insert
    rebuild_fts(conn)

    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    status = get_status(conn)
    for table, count in status.items():
        print(f"  {table}: {count} rows")
    print("=" * 60)


def _migrate_founder_profile(conn):
    """Migrate founder_profile.json into profile table as atomic key-value pairs."""
    filepath = MEMORY_DIR / "founder_profile.json"
    if not filepath.exists():
        print("  Skip: founder_profile.json not found")
        return

    print("\n>> Migrating founder_profile.json...")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    for key, value, category in _flatten_json(data, category_map={
        "birth": "personal",
        "company": "company",
        "achievements": "achievements",
        "skills": "skills",
        "personality_traits": "personal",
        "goals": "goals",
        "key_people": "relationships",
        "board": "governance",
        "applied_additive": "ventures",
        "new_ventures": "ventures",
        "fracktal_status": "company",
    }):
        if key.startswith("_"):
            continue
        profile_set(conn, key, str(value), category)
        count += 1

    print(f"  Migrated {count} profile entries")


def _migrate_interactions(conn):
    """Migrate interaction_log.json into interactions table."""
    filepath = MEMORY_DIR / "interaction_log.json"
    if not filepath.exists():
        print("  Skip: interaction_log.json not found")
        return

    print("\n>> Migrating interaction_log.json...")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    interactions = data.get("interactions", [])
    # Deduplicate by summary (old system had duplicates)
    seen_summaries = set()
    count = 0
    for entry in interactions:
        summary = entry.get("summary", "")
        # Skip near-duplicate summaries (first 100 chars)
        sig = summary[:100]
        if sig in seen_summaries:
            continue
        seen_summaries.add(sig)

        topics = ",".join(entry.get("topics", []))
        advice = ",".join(entry.get("advice_given", []))
        follow_ups = ",".join(entry.get("follow_ups", []))
        raw_data = json.dumps(entry)

        conn.execute("""
            INSERT INTO interactions (date, summary, topics, advice, follow_ups, raw_data)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (entry.get("date", ""), summary, topics, advice, follow_ups, raw_data))
        count += 1

    conn.commit()
    print(f"  Migrated {count} interactions (deduped from {len(interactions)})")


def _migrate_decisions(conn):
    """Migrate decision_journal.json into decisions table."""
    filepath = MEMORY_DIR / "decision_journal.json"
    if not filepath.exists():
        print("  Skip: decision_journal.json not found")
        return

    print("\n>> Migrating decision_journal.json...")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    decisions = data.get("decisions", [])
    for entry in decisions:
        conn.execute("""
            INSERT INTO decisions (date, decision, context, astrological_timing,
                                   expected_outcome, actual_outcome, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.get("date", ""),
            entry.get("decision", ""),
            entry.get("context", ""),
            entry.get("astrological_timing", ""),
            entry.get("expected_outcome", ""),
            entry.get("actual_outcome", ""),
            entry.get("status", "pending")
        ))
    conn.commit()
    print(f"  Migrated {len(decisions)} decisions")


def _migrate_insights(conn):
    """Migrate insights.md into insights table as individual entries."""
    filepath = MEMORY_DIR / "insights.md"
    if not filepath.exists():
        print("  Skip: insights.md not found")
        return

    print("\n>> Migrating insights.md...")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse markdown insights — each ### header starts a new entry
    entries = re.split(r'\n### ', content)
    seen_content = set()
    count = 0

    for entry in entries[1:]:  # Skip header
        lines = entry.strip().split("\n")
        if not lines:
            continue

        # Parse date and category from header
        header = lines[0]
        date_match = re.match(r'(\d{4}-\d{2}-\d{2})\s*(?:\[(\w+)\])?', header)
        date = date_match.group(1) if date_match else ""
        category = date_match.group(2) if date_match and date_match.group(2) else "general"

        # Get content (everything after header, strip bullet points)
        content_lines = []
        for line in lines[1:]:
            stripped = line.strip()
            if stripped.startswith("- "):
                stripped = stripped[2:]
            if stripped:
                content_lines.append(stripped)

        insight_content = " ".join(content_lines)
        if not insight_content:
            continue

        # Deduplicate
        sig = insight_content[:120]
        if sig in seen_content:
            continue
        seen_content.add(sig)

        conn.execute("""
            INSERT INTO insights (content, category, date)
            VALUES (?, ?, ?)
        """, (insight_content, category, date))
        count += 1

    conn.commit()
    print(f"  Migrated {count} insights (deduped)")


def _migrate_startup_context(conn):
    """Migrate startup_context.json into context table as atomic key-value pairs."""
    filepath = MEMORY_DIR / "startup_context.json"
    if not filepath.exists():
        print("  Skip: startup_context.json not found")
        return

    print("\n>> Migrating startup_context.json...")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    for key, value, category in _flatten_json(data, category_map={
        "goals": "goals",
        "new_ventures": "ventures",
        "fracktal_status": "fracktal",
        "challenges": "challenges",
        "key_people": "relationships",
        "applied_additive": "ventures",
    }):
        if key.startswith("_"):
            continue
        context_set(conn, key, str(value), category)
        count += 1

    print(f"  Migrated {count} context entries")


def _migrate_birth_chart(conn):
    """Migrate birth_chart.json into profile table under astrology category."""
    filepath = MEMORY_DIR / "birth_chart.json"
    if not filepath.exists():
        print("  Skip: birth_chart.json not found")
        return

    print("\n>> Migrating birth_chart.json...")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    for key, value, _ in _flatten_json(data):
        if key.startswith("_"):
            continue
        profile_set(conn, f"astro.{key}", str(value), "astrology")
        count += 1

    print(f"  Migrated {count} birth chart entries")


def _extract_entities_from_context(conn):
    """Extract named entities from startup_context key_people."""
    filepath = MEMORY_DIR / "startup_context.json"
    if not filepath.exists():
        return

    print("\n>> Extracting entities...")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    key_people = data.get("key_people", {})
    count = 0
    for name_key, info in key_people.items():
        if isinstance(info, str):
            details = info
            tags = ""
        elif isinstance(info, dict):
            details = info.get("existing_info", "") or json.dumps(info)
            tags = ",".join(info.keys())
        else:
            continue

        # Convert key to display name
        display_name = name_key.replace("_", " ").title()
        add_entity(conn, display_name, "person", details, tags)
        count += 1

    # Also extract companies
    companies = {
        "Fracktal Works": ("company", "Vijay's primary company. 3D Printing / Additive Manufacturing. Founded 2011. Team of 20.", "3d-printing,manufacturing,hardware"),
        "Applied Additive": ("company", "Formerly RapidTool. AI-driven manufacturing tooling design automation.", "ai,manufacturing,saas"),
        "Constellation Aerospace": ("company", "Satellite venture with Punarjay Chakravarty. Funded by BlueHill.vc.", "satellite,spacetech,deeptech"),
        "Aarin Capital": ("company", "Mohandas Pai's VC firm. Fracktal investor.", "vc,investor"),
        "Claypond Capital": ("company", "Ranjan Pai/MEMG Family Office. Fracktal investor.", "vc,investor,manipal"),
        "BlueHill.vc": ("company", "Chennai deep-tech VC. Rs 350cr fund. Funded Constellation Aerospace.", "vc,deeptech,chennai"),
    }
    for name, (type_, details, tags) in companies.items():
        add_entity(conn, name, type_, details, tags)
        count += 1

    print(f"  Extracted {count} entities")


def _flatten_json(data, prefix="", category_map=None, default_category="general"):
    """
    Flatten a nested JSON dict into (key, value, category) tuples.
    Lists become separate entries with index suffixes.
    """
    results = []
    category_map = category_map or {}

    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        top_level_key = key if not prefix else prefix.split(".")[0]
        category = category_map.get(top_level_key, default_category)

        if isinstance(value, dict):
            results.extend(_flatten_json(value, full_key, category_map, category))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    results.extend(_flatten_json(item, f"{full_key}[{i}]", category_map, category))
                else:
                    results.append((f"{full_key}[{i}]", str(item), category))
        else:
            results.append((full_key, str(value) if value is not None else "", category))

    return results


# ---------------------------------------------------------------------------
# CLI interface
# ---------------------------------------------------------------------------

def print_search_results(results):
    """Pretty-print search results for terminal output."""
    if not results:
        print("No results found.")
        return

    print(f"\n{'='*60}")
    print(f"Found {len(results)} results")
    print(f"{'='*60}\n")

    for i, r in enumerate(results, 1):
        print(f"{i}. {r['display']}")
        if r.get('date'):
            print(f"   Date: {r['date'][:10]}  |  Type: {r['type']}  |  Score: {r['score']:.2f}")
        else:
            print(f"   Type: {r['type']}  |  Score: {r['score']:.2f}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Memory Database — Searchable persistent memory for Startup Guru",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent("""\
            Examples:
              python memory_db.py search "funding RapidTool"
              python memory_db.py search "board dynamics" --type facts
              python memory_db.py profile show
              python memory_db.py log-interaction --summary "Discussed timing" --topics "funding,astrology"
              python memory_db.py add-fact "Honda interested in RapidTool" --category business --entity Honda
              python memory_db.py migrate
        """)
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # --- search ---
    p_search = subparsers.add_parser("search", help="Search all memory")
    p_search.add_argument("query", help="Search terms")
    p_search.add_argument("--type", dest="type_filter", help="Filter by type: interactions, facts, entities, decisions, insights, profile, context")
    p_search.add_argument("--after", help="Only results after this date (YYYY-MM-DD)")
    p_search.add_argument("--before", help="Only results before this date (YYYY-MM-DD)")
    p_search.add_argument("--limit", type=int, default=20, help="Max results per type")
    p_search.add_argument("--json", action="store_true", help="Output as JSON")

    # --- profile ---
    p_profile = subparsers.add_parser("profile", help="Profile operations")
    p_profile_sub = p_profile.add_subparsers(dest="profile_cmd")
    p_profile_show = p_profile_sub.add_parser("show", help="Show all profile data")
    p_profile_show.add_argument("--json", action="store_true")
    p_profile_get = p_profile_sub.add_parser("get", help="Get a profile key")
    p_profile_get.add_argument("key")
    p_profile_set = p_profile_sub.add_parser("set", help="Set a profile key")
    p_profile_set.add_argument("key")
    p_profile_set.add_argument("value")
    p_profile_set.add_argument("--category", default="general")

    # --- context ---
    p_context = subparsers.add_parser("context", help="Context operations")
    p_ctx_sub = p_context.add_subparsers(dest="context_cmd")
    p_ctx_show = p_ctx_sub.add_parser("show", help="Show all context")
    p_ctx_show.add_argument("--json", action="store_true")
    p_ctx_get = p_ctx_sub.add_parser("get", help="Get a context key")
    p_ctx_get.add_argument("key")
    p_ctx_set = p_ctx_sub.add_parser("set", help="Set a context key")
    p_ctx_set.add_argument("key")
    p_ctx_set.add_argument("value")
    p_ctx_set.add_argument("--category", default="general")

    # --- log-interaction ---
    p_log = subparsers.add_parser("log-interaction", help="Log a conversation")
    p_log.add_argument("--summary", required=True)
    p_log.add_argument("--topics", default="")
    p_log.add_argument("--advice", default="")
    p_log.add_argument("--follow-ups", default="")

    # --- log-decision ---
    p_dec = subparsers.add_parser("log-decision", help="Log a decision")
    p_dec.add_argument("--decision", required=True)
    p_dec.add_argument("--context", default="")
    p_dec.add_argument("--timing", default="")
    p_dec.add_argument("--expected", default="")

    # --- update-outcome ---
    p_out = subparsers.add_parser("update-outcome", help="Update decision outcome")
    p_out.add_argument("decision_id", type=int)
    p_out.add_argument("outcome")

    # --- add-fact ---
    p_fact = subparsers.add_parser("add-fact", help="Store an atomic fact")
    p_fact.add_argument("content")
    p_fact.add_argument("--category", default="general")
    p_fact.add_argument("--entity", default="")
    p_fact.add_argument("--tags", default="")
    p_fact.add_argument("--source", default="")
    p_fact.add_argument("--confidence", default="confirmed")

    # --- add-entity ---
    p_ent = subparsers.add_parser("add-entity", help="Store an entity")
    p_ent.add_argument("name")
    p_ent.add_argument("--type", default="person")
    p_ent.add_argument("--details", default="")
    p_ent.add_argument("--tags", default="")

    # --- add-insight ---
    p_ins = subparsers.add_parser("add-insight", help="Store an insight")
    p_ins.add_argument("content")
    p_ins.add_argument("--category", default="general")

    # --- status ---
    subparsers.add_parser("status", help="Show database status")

    # --- rebuild-fts ---
    subparsers.add_parser("rebuild-fts", help="Rebuild FTS indexes")

    # --- migrate ---
    subparsers.add_parser("migrate", help="Migrate from old JSON files")

    # --- init ---
    subparsers.add_parser("init", help="Initialize database (create tables)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    conn = get_db()
    init_db(conn)

    try:
        if args.command == "search":
            results = search(conn, args.query, args.type_filter, args.after, args.before, args.limit)
            if getattr(args, "json", False):
                print(json.dumps(results, indent=2, default=str))
            else:
                print_search_results(results)

        elif args.command == "profile":
            if args.profile_cmd == "show":
                data = profile_show(conn)
                if getattr(args, "json", False):
                    print(json.dumps(data, indent=2))
                else:
                    current_cat = None
                    for row in data:
                        if row["category"] != current_cat:
                            current_cat = row["category"]
                            print(f"\n[{current_cat}]")
                        print(f"  {row['key']} = {row['value'][:120]}")
            elif args.profile_cmd == "get":
                result = profile_get(conn, args.key)
                if result:
                    print(json.dumps(result, indent=2))
                else:
                    print(f"Key not found: {args.key}")
            elif args.profile_cmd == "set":
                profile_set(conn, args.key, args.value, args.category)
                print(f"Set profile: {args.key}")

        elif args.command == "context":
            if args.context_cmd == "show":
                data = context_show(conn)
                if getattr(args, "json", False):
                    print(json.dumps(data, indent=2))
                else:
                    current_cat = None
                    for row in data:
                        if row["category"] != current_cat:
                            current_cat = row["category"]
                            print(f"\n[{current_cat}]")
                        print(f"  {row['key']} = {row['value'][:120]}")
            elif args.context_cmd == "get":
                result = context_get(conn, args.key)
                if result:
                    print(json.dumps(result, indent=2))
                else:
                    print(f"Key not found: {args.key}")
            elif args.context_cmd == "set":
                context_set(conn, args.key, args.value, args.category)
                print(f"Set context: {args.key}")

        elif args.command == "log-interaction":
            log_interaction(conn, args.summary, args.topics, args.advice, getattr(args, "follow_ups", ""))

        elif args.command == "log-decision":
            log_decision(conn, args.decision, args.context, args.timing, args.expected)

        elif args.command == "update-outcome":
            update_outcome(conn, args.decision_id, args.outcome)

        elif args.command == "add-fact":
            add_fact(conn, args.content, args.category, args.entity, args.tags, args.source, args.confidence)

        elif args.command == "add-entity":
            add_entity(conn, args.name, args.type, args.details, args.tags)

        elif args.command == "add-insight":
            add_insight(conn, args.content, args.category)

        elif args.command == "status":
            status = get_status(conn)
            print("\nMemory Database Status:")
            print(f"  Location: {DB_PATH}")
            print(f"  Size: {DB_PATH.stat().st_size / 1024:.1f} KB" if DB_PATH.exists() else "  Not created yet")
            for table, count in status.items():
                print(f"  {table}: {count} rows")

        elif args.command == "rebuild-fts":
            rebuild_fts(conn)

        elif args.command == "migrate":
            migrate_from_json(conn)

        elif args.command == "init":
            print(f"Database initialized at {DB_PATH}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
