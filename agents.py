"""agent-startup-guru — MAF Agent definitions.

Exports:
    build_agents() -> list[GitHubCopilotAgent]   (Dynamic Agent Loader entry point)

Architecture (DOE v2):
  Layer 1 (Skills)        — .github/skills/*/SKILL.md + .github/skills/*/scripts/
  Layer 2 (Orchestration) — THIS FILE (GitHubCopilotAgent via MAF)
  Layer 3 (Execution)     — .tmp/scripts/ shared utilities + skill scripts
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# ── Paths ─────────────────────────────────────────────────────────────────────
AGENT_DIR   = Path(__file__).parent.resolve()
PROMPTS_DIR = AGENT_DIR / ".github" / "prompts"
SKILLS_DIR  = AGENT_DIR / ".github" / "skills"
SCRIPTS_DIR = AGENT_DIR / ".tmp" / "scripts"

# Make .tmp/scripts/ importable by skill scripts at runtime
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


# ── Subprocess helpers ────────────────────────────────────────────────────────

def _run_env() -> dict[str, str]:
    """Add .tmp/scripts/ to PYTHONPATH so skill scripts can import shared utilities."""
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    scripts = str(SCRIPTS_DIR)
    env["PYTHONPATH"] = f"{scripts}{os.pathsep}{existing}" if existing else scripts
    return env


async def _run(args: list[str]) -> str:
    """Run a script as a subprocess. Raises RuntimeError on non-zero exit."""
    result = await asyncio.to_thread(
        subprocess.run, args,
        capture_output=True, text=True,
        cwd=str(AGENT_DIR), env=_run_env(),
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or f"Script exited {result.returncode}")
    return result.stdout or "(no output)"


# ── System prompt ─────────────────────────────────────────────────────────────

def _build_system_prompt() -> str:
    """Load .github/prompts/system.md + append each .github/skills/*/SKILL.md as a tool block."""
    parts: list[str] = []
    system_md = PROMPTS_DIR / "system.md"
    if system_md.exists():
        parts.append(system_md.read_text(encoding="utf-8", errors="replace"))
        if SKILLS_DIR.exists():
            skill_sections: list[str] = []
            for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
                content = skill_md.read_text(encoding="utf-8", errors="replace")
                skill_sections.append(f"\n### Tool: {skill_md.parent.name}\n\n{content}")
            if skill_sections:
                parts.append("\n\n---\n\n## Registered Skill Tool Descriptions\n")
                parts.extend(skill_sections)
    else:
        agents_md = AGENT_DIR / "AGENTS.md"
        if agents_md.exists():
            parts.append(agents_md.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


SYSTEM_PROMPT = _build_system_prompt()


# ── Tool functions ────────────────────────────────────────────────────────────

async def read_memory(section: str = "all") -> str:
    """Read from the persistent memory bank. Use when the user asks about past
    conversations, decisions, their profile, startup context, or birth chart.
    section: one of all|founder_profile|birth_chart|startup_context|interaction_log|decision_journal|insights."""
    return await _run([sys.executable,
        str(SKILLS_DIR / "memory-management" / "scripts" / "memory_bank.py"),
        "--read", section])


async def search_memory(query: str, search_type: str = "") -> str:
    """Full-text search across all past interactions, facts, entities, and insights.
    Use when looking for specific past events, people, or detailed historical context.
    query: search terms. search_type: optional filter (interactions|facts|entities|insights)."""
    args = [sys.executable,
        str(SKILLS_DIR / "memory-management" / "scripts" / "memory_db.py"),
        "search", query]
    if search_type:
        args.extend(["--type", search_type])
    return await _run(args)


async def check_transits(range_days: int = 0) -> str:
    """Calculate current planetary transits relative to the natal chart.
    Use when the user asks about timing, astrological weather, or muhurta.
    range_days: optionally look ahead N days (e.g. 90 for 3-month outlook)."""
    args = [sys.executable,
        str(SKILLS_DIR / "vedic-astrology" / "scripts" / "transit_calculator.py")]
    if range_days:
        args.extend(["--range", str(range_days)])
    return await _run(args)


async def calculate_birth_chart(from_profile: bool = True) -> str:
    """Calculate or recalculate the Vedic birth chart. Use when the user asks
    about their natal chart, planetary positions, Dasha periods, or yogas.
    from_profile: read birth data from memory (default True)."""
    args = [sys.executable,
        str(SKILLS_DIR / "vedic-astrology" / "scripts" / "birth_chart.py")]
    if from_profile:
        args.append("--from-profile")
    return await _run(args)


async def web_search(mode: str, query: str) -> str:
    """Search the web via SerpAPI. Use when the user asks about current events,
    market trends, startup news, or any information beyond your training cutoff.
    mode: one of search|news|startup|person|trends.
    query: the search query string."""
    return await _run([sys.executable,
        str(SCRIPTS_DIR / "web_search.py"),
        "--mode", mode, "--query", query])


async def research_person(name: str, company: str = "") -> str:
    """Deep research on a person or company. Use when the user mentions a founder,
    investor, competitor, or potential partner and wants a dossier.
    name: person or company name. company: optional associated company."""
    args = [sys.executable,
        str(SKILLS_DIR / "web-research" / "scripts" / "personality_research.py"),
        "--name", name]
    if company:
        args.extend(["--company", company])
    args.append("--json-only")
    return await _run(args)


async def ocr_extract(image_path: str, output_format: str = "json") -> str:
    """Extract text and tables from images. Use when the user uploads an image
    with text (invoice, screenshot, document photo) and wants the data.
    image_path: path to the image file. output_format: json|csv|table."""
    return await _run([sys.executable,
        str(SKILLS_DIR / "startup-mentor" / "scripts" / "ocr_extract.py"),
        "--image", image_path, "--format", output_format])


async def log_interaction(summary: str, topics: str = "", advice: str = "") -> str:
    """Log a conversation interaction to persistent memory. Use after substantive
    exchanges to ensure continuity across sessions.
    summary: brief summary of the discussion.
    topics: comma-separated topics. advice: key advice given."""
    args = [sys.executable,
        str(SKILLS_DIR / "memory-management" / "scripts" / "memory_bank.py"),
        "--log-interaction", "--summary", summary]
    if topics:
        args.extend(["--topics", topics])
    return await _run(args)


async def log_decision(decision: str, context: str = "", timing: str = "") -> str:
    """Log a decision to the decision journal. Use when Vijay makes a significant
    business or personal decision to track outcomes over time.
    decision: the decision made. context: surrounding circumstances.
    timing: astrological timing context."""
    args = [sys.executable,
        str(SKILLS_DIR / "memory-management" / "scripts" / "memory_bank.py"),
        "--log-decision", "--decision", decision]
    if context:
        args.extend(["--context", context])
    if timing:
        args.extend(["--timing", timing])
    return await _run(args)


# ── LiteLLM provider (CommandCenter mode) ────────────────────────────────────

def _llm_provider() -> dict[str, Any]:
    base_url = os.environ.get("LITELLM_BASE_URL", "http://127.0.0.1:8080")
    api_key  = os.environ.get("LITELLM_MASTER_KEY", "sk-local")
    return {"type": "openai", "base_url": f"{base_url}/v1", "api_key": api_key}


# ── Agent factory ─────────────────────────────────────────────────────────────

def build_agent() -> "GitHubCopilotAgent":
    from agent_framework_github_copilot import GitHubCopilotAgent  # type: ignore[import]
    from copilot.types import PermissionHandler                     # type: ignore[import]

    return GitHubCopilotAgent(
        name="agent-startup-guru",
        description="Startup mentor blending Vedic astrology, ecosystem intelligence, and persistent memory.",
        instructions=SYSTEM_PROMPT,
        tools=[
            read_memory,
            search_memory,
            check_transits,
            calculate_birth_chart,
            web_search,
            research_person,
            ocr_extract,
            log_interaction,
            log_decision,
        ],
        default_options={
            "model": "tier-balanced",
            "provider": _llm_provider(),
            "mcp_servers": {},
            "on_permission_request": PermissionHandler.approve_all,
        },
    )


def build_agents() -> list:
    """Dynamic Agent Loader entry point. Synchronous, zero-argument, pure."""
    return [build_agent()]


__all__ = ["build_agents", "build_agent", "SYSTEM_PROMPT"]
