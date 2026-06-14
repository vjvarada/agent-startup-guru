#!/usr/bin/env python3
"""
Vedic Transit Calculator

Calculates current planetary transits relative to the natal chart.
Identifies significant transits (Saturn return, Jupiter transit, Rahu-Ketu axis, etc.)
and provides timing context for decision-making.

Usage:
    python transit_calculator.py                           # Current transits vs natal chart
    python transit_calculator.py --date "2026-06-18"       # Transits for specific date
    python transit_calculator.py --range 90                # Upcoming significant transits in next 90 days
    python transit_calculator.py --json-only               # JSON output only
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
# .github/skills/vedic-astrology/scripts/ → vedic-astrology/ → skills/ → .github/ → repo root
REPO_ROOT = SCRIPT_DIR.parent.parent.parent.parent
MEMORY_DIR = REPO_ROOT / "outputs" / "_memory"

# birth_chart.py is a sibling in the same skill scripts folder
sys.path.insert(0, str(SCRIPT_DIR))
from birth_chart import (NAKSHATRA_LORDS, NAKSHATRAS, RASHI_LORDS, RASHIS,
                         approximate_planetary_positions, calculate_ayanamsa,
                         get_nakshatra, get_rashi, local_to_utc,
                         tropical_to_sidereal)


def load_natal_chart():
    """Load natal chart from memory."""
    chart_path = MEMORY_DIR / "birth_chart.json"
    if chart_path.exists():
        with open(chart_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def get_current_transits(target_date=None):
    """
    Calculate current sidereal planetary positions.

    Args:
        target_date: datetime object (defaults to now)

    Returns:
        Dict of planet -> {sidereal_longitude, rashi, nakshatra, etc.}
    """
    if target_date is None:
        target_date = datetime.now()

    # Convert local time to UTC for astronomical calculations
    target_utc = local_to_utc(target_date)

    ayanamsa = calculate_ayanamsa(target_utc)
    tropical = approximate_planetary_positions(target_utc)

    transits = {}
    for planet, deg in tropical.items():
        sid_deg = tropical_to_sidereal(deg, ayanamsa)
        rashi_idx, deg_in_sign = get_rashi(sid_deg)
        nak_idx, pada = get_nakshatra(sid_deg)

        transits[planet] = {
            "sidereal_longitude": round(sid_deg, 2),
            "rashi": RASHIS[rashi_idx],
            "rashi_index": rashi_idx,
            "degree_in_sign": round(deg_in_sign, 2),
            "nakshatra": NAKSHATRAS[nak_idx],
            "nakshatra_pada": pada
        }

    return transits


def analyze_transit_to_natal(transits, natal_chart):
    """
    Analyze current transits relative to natal chart positions.

    Returns list of significant transit aspects and their interpretations.
    """
    if not natal_chart:
        return []

    natal_lagna_idx = natal_chart["lagna"]["rashi_index"]
    natal_planets = natal_chart["planets"]

    aspects = []

    for t_planet, t_data in transits.items():
        t_rashi = t_data["rashi_index"]

        # Transit through natal houses (from Lagna)
        house_from_lagna = ((t_rashi - natal_lagna_idx) % 12) + 1

        # Check conjunctions with natal planets
        for n_planet, n_data in natal_planets.items():
            n_rashi = n_data["rashi_index"]
            diff = (t_rashi - n_rashi) % 12

            if diff == 0:  # Conjunction
                aspects.append({
                    "type": "conjunction",
                    "transit_planet": t_planet,
                    "natal_planet": n_planet,
                    "transit_rashi": t_data["rashi"],
                    "house_from_lagna": house_from_lagna,
                    "significance": _get_conjunction_significance(t_planet, n_planet),
                    "advice": _get_transit_advice(t_planet, n_planet, "conjunction", house_from_lagna)
                })
            elif diff == 6:  # Opposition (7th aspect)
                aspects.append({
                    "type": "opposition",
                    "transit_planet": t_planet,
                    "natal_planet": n_planet,
                    "transit_rashi": t_data["rashi"],
                    "house_from_lagna": house_from_lagna,
                    "significance": _get_opposition_significance(t_planet, n_planet),
                    "advice": _get_transit_advice(t_planet, n_planet, "opposition", house_from_lagna)
                })

        # Special transits
        # Saturn through important natal houses
        if t_planet == "Saturn":
            natal_moon_rashi = natal_planets["Moon"]["rashi_index"]
            moon_diff = (t_rashi - natal_moon_rashi) % 12
            if moon_diff in [11, 0, 1]:  # Sade Sati
                phase = {11: "Rising (approaching)", 0: "Peak (over Moon)", 1: "Setting (departing)"}
                aspects.append({
                    "type": "sade_sati",
                    "transit_planet": "Saturn",
                    "phase": phase.get(moon_diff, "Active"),
                    "transit_rashi": t_data["rashi"],
                    "house_from_lagna": house_from_lagna,
                    "significance": "HIGH — Sade Sati is a 7.5 year period of Saturn transiting around natal Moon. Brings transformation, maturity, and restructuring. Can be challenging but builds lasting foundations.",
                    "advice": "Focus on discipline, long-term planning, and building resilient systems. Avoid shortcuts. This is a period for consolidation, not rapid expansion."
                })

        # Jupiter transit through key houses
        if t_planet == "Jupiter":
            if house_from_lagna in [1, 5, 9]:  # Trikona transit
                aspects.append({
                    "type": "jupiter_trikona",
                    "transit_planet": "Jupiter",
                    "transit_rashi": t_data["rashi"],
                    "house_from_lagna": house_from_lagna,
                    "significance": f"POSITIVE — Jupiter transiting {house_from_lagna}th house (trikona). Expansion, new opportunities, wisdom, and growth.",
                    "advice": "Excellent time for launching new ventures, seeking funding, partnerships, and intellectual growth. Say yes to opportunities."
                })
            elif house_from_lagna in [2, 11]:  # Wealth houses
                aspects.append({
                    "type": "jupiter_wealth",
                    "transit_planet": "Jupiter",
                    "transit_rashi": t_data["rashi"],
                    "house_from_lagna": house_from_lagna,
                    "significance": f"POSITIVE — Jupiter in {house_from_lagna}th house. Financial gains, income growth, and valuable networks.",
                    "advice": "Good period for revenue focus, pricing changes, and building profitable relationships."
                })

        # Rahu-Ketu axis transits
        if t_planet in ["Rahu", "Ketu"]:
            if house_from_lagna in [1, 7]:
                aspects.append({
                    "type": "nodal_axis",
                    "transit_planet": t_planet,
                    "transit_rashi": t_data["rashi"],
                    "house_from_lagna": house_from_lagna,
                    "significance": f"TRANSFORMATIVE — {t_planet} on the 1-7 axis. Major identity and relationship shifts. Past karma manifesting.",
                    "advice": "Period of significant change in self-presentation and partnerships. Embrace unconventional approaches. Be mindful of illusions."
                })
            elif house_from_lagna in [10, 4]:
                aspects.append({
                    "type": "nodal_axis",
                    "transit_planet": t_planet,
                    "transit_rashi": t_data["rashi"],
                    "house_from_lagna": house_from_lagna,
                    "significance": f"CAREER — {t_planet} on the 4-10 axis. Career direction and home/foundation shifts.",
                    "advice": "Major career developments coming. Rahu in 10th drives ambition; Ketu in 10th demands letting go of status attachment."
                })

    return aspects


def _get_conjunction_significance(transit, natal):
    """Get significance of a transit planet conjuncting a natal planet."""
    key_combos = {
        ("Jupiter", "Sun"): "Expansion of authority, recognition, and leadership. Great for launching initiatives.",
        ("Jupiter", "Moon"): "Emotional expansion, optimism, public favor. Good for marketing and community building.",
        ("Jupiter", "Venus"): "Financial blessings, partnerships, creative inspiration. Excellent for fundraising.",
        ("Saturn", "Sun"): "Testing of leadership. Hard work brings lasting results but may feel heavy.",
        ("Saturn", "Moon"): "Emotional restructuring. Build mental resilience. Evaluate personal foundations.",
        ("Saturn", "Mars"): "Controlled action. Discipline in execution. May face delays but builds strength.",
        ("Rahu", "Jupiter"): "Unconventional expansion. International opportunities. Think big but verify.",
        ("Rahu", "Venus"): "Unusual financial or creative opportunities. Exciting but verify reality.",
    }
    return key_combos.get((transit, natal), f"Transit {transit} influencing natal {natal}.")


def _get_opposition_significance(transit, natal):
    """Get significance of transit planet opposing natal planet."""
    return f"Transit {transit} opposing natal {natal} — creates tension that demands balance and conscious choice."


def _get_transit_advice(transit, natal, aspect_type, house):
    """Generate startup-specific advice for a transit."""
    house_themes = {
        1: "personal brand, leadership style, health",
        2: "revenue, pricing, financial management",
        3: "communication, marketing, short trips, siblings",
        4: "office/workspace, foundational systems, emotional security",
        5: "creativity, product innovation, team morale",
        6: "operations, employees, daily routines, competition",
        7: "partnerships, investors, key clients, negotiations",
        8: "funding rounds, transformation, pivots, deep research",
        9: "vision, mentors, international expansion, higher learning",
        10: "public image, career milestones, reputation",
        11: "network, community, revenue streams, goals",
        12: "behind-the-scenes work, R&D, spiritual growth, exits"
    }
    theme = house_themes.get(house, "general matters")
    return f"Focus area: {theme} (House {house})"


def find_upcoming_transits(natal_chart, days_ahead=90):
    """
    Scan upcoming period for significant transit events.
    """
    events = []
    today = datetime.now()

    # Check each day
    for day_offset in range(0, days_ahead, 3):  # Check every 3 days for efficiency
        check_date = today + timedelta(days=day_offset)
        transits = get_current_transits(check_date)
        aspects = analyze_transit_to_natal(transits, natal_chart)

        for aspect in aspects:
            if aspect.get("significance", "").startswith(("HIGH", "POSITIVE", "TRANSFORMATIVE", "CAREER")):
                aspect["date"] = check_date.strftime("%Y-%m-%d")
                events.append(aspect)

    # Deduplicate by removing consecutive same-type events
    unique_events = []
    seen = set()
    for event in events:
        key = f"{event['type']}_{event.get('transit_planet')}_{event.get('natal_planet', '')}"
        if key not in seen:
            seen.add(key)
            unique_events.append(event)

    return unique_events


def print_transit_report(transits, aspects, natal_chart):
    """Print formatted transit report."""
    print("\n" + "=" * 70)
    print("  CURRENT PLANETARY TRANSITS (Vedic/Sidereal)")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    print(f"\n{'─' * 70}")
    print(f"  {'Planet':<10} {'Rashi':<25} {'Degree':<8} {'Nakshatra':<20}")
    print(f"{'─' * 70}")
    for planet, data in transits.items():
        print(f"  {planet:<10} {data['rashi']:<25} {data['degree_in_sign']:>5.1f}°  {data['nakshatra']}")

    if natal_chart and natal_chart.get("current_dasha"):
        dasha = natal_chart["current_dasha"]
        print(f"\n{'─' * 70}")
        print(f"  CURRENT MAHA DASHA: {dasha['planet']}")
        print(f"  Period: {dasha['start']} to {dasha['end']}")
        print(f"{'─' * 70}")

    if aspects:
        print(f"\n{'─' * 70}")
        print("  SIGNIFICANT ASPECTS TO NATAL CHART")
        print(f"{'─' * 70}")
        for aspect in aspects:
            print(f"\n  ✦ {aspect['type'].upper().replace('_', ' ')}")
            print(f"    Transit {aspect.get('transit_planet', '?')} in {aspect.get('transit_rashi', '?')} (House {aspect.get('house_from_lagna', '?')})")
            if 'natal_planet' in aspect:
                print(f"    Aspecting natal {aspect['natal_planet']}")
            print(f"    Significance: {aspect.get('significance', 'N/A')}")
            print(f"    Advice: {aspect.get('advice', 'N/A')}")

    print(f"\n{'=' * 70}\n")


def main():
    parser = argparse.ArgumentParser(description="Vedic Transit Calculator")
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD), default=today")
    parser.add_argument("--range", type=int, help="Look ahead N days for significant transits")
    parser.add_argument("--json-only", action="store_true", help="Output JSON only")

    args = parser.parse_args()

    # Load natal chart
    natal_chart = load_natal_chart()
    if not natal_chart:
        print("Warning: No natal chart found in memory/birth_chart.json")
        print("Run birth_chart.py --save first, or transit analysis will be limited.")

    # Parse target date
    target_date = None
    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d")

    if args.range:
        # Upcoming significant transits
        events = find_upcoming_transits(natal_chart, args.range)
        if args.json_only:
            print(json.dumps(events, indent=2))
        else:
            print(f"\n{'=' * 70}")
            print(f"  UPCOMING SIGNIFICANT TRANSITS (next {args.range} days)")
            print(f"{'=' * 70}")
            for event in events:
                print(f"\n  📅 {event.get('date', 'N/A')} — {event['type'].upper().replace('_', ' ')}")
                print(f"     {event.get('transit_planet', '?')} in {event.get('transit_rashi', '?')}")
                print(f"     {event.get('significance', '')[:100]}")
            if not events:
                print("  No major transit events found in the specified period.")
            print()
    else:
        # Current transits
        transits = get_current_transits(target_date)
        aspects = analyze_transit_to_natal(transits, natal_chart) if natal_chart else []

        if args.json_only:
            output = {
                "date": (target_date or datetime.now()).strftime("%Y-%m-%d"),
                "transits": transits,
                "aspects": aspects
            }
            print(json.dumps(output, indent=2))
        else:
            print_transit_report(transits, aspects, natal_chart)


if __name__ == "__main__":
    main()
