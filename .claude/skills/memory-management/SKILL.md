---
name: memory-management
description: Dual-tier persistent memory system for the Startup Guru agent. Tier 1 (JSON/Markdown working memory) loaded at session start. Tier 2 (SQLite FTS5 long-term memory) queried on demand. Memory retrieval routing rules, update protocols, and search best practices.
---

# memory-management

The canonical instructions live in `.github/skills/memory-management/SKILL.md` (shared with Copilot Chat and CommandCenter). **Read that file in full now, then follow it.**

Script paths in that file are relative to the repo root. Run them with `PYTHONPATH=.tmp/scripts python <script>` (the Claude Code settings already set PYTHONPATH).
