# Startup Guru — Copilot Instructions

This is the **Startup Guru** agent repo — a CommandCenter-compatible agent that blends Vedic astrology, deep startup ecosystem knowledge, and persistent memory to mentor Vijay Raghav Varada, founder of Fracktal Works.

## Architecture (DOE v2)

- **Skills**: `.github/skills/*/SKILL.md` — define goals, inputs, scripts, outputs
- **Orchestration**: `agents.py` (build_agents entry point for CommandCenter) + LLM decision-making
- **Execution**: `.github/skills/*/scripts/` (skill-specific) + `.tmp/scripts/` (shared utilities)

## Key Files

- `agents.py` — MAF build_agents() entry point
- `config.json` — CommandCenter contract
- `.github/prompts/system.md` — Primary system prompt
- `.github/agents/startup-guru.agent.md` — VS Code Copilot Chat definition

## Script Paths

Always use `sys.executable` when running scripts. Scripts resolve the repo root relative to their location.
