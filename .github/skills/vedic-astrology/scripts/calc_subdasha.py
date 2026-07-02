"""
Vedic Dasha Sub-Period Calculator

Calculates Antardasha (sub-periods) and Pratyantardasha (sub-sub-periods)
for the current Mahadasha from the natal birth chart.

Usage:
    python calc_subdasha.py                # Print all sub-periods
    python calc_subdasha.py --json-only    # JSON output for agent consumption
"""
import json
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
# .github/skills/vedic-astrology/scripts/ → vedic-astrology/ → skills/ → .github/ → repo root
REPO_ROOT = SCRIPT_DIR.parent.parent.parent.parent
MEMORY_DIR = REPO_ROOT / "outputs" / "_memory"

# Import Dasha constants from sibling birth_chart module
sys.path.insert(0, str(SCRIPT_DIR))
from birth_chart import DASHA_YEARS, DASHA_SEQUENCE as DASHA_SEQ, now_ist, IST

TOTAL = 120


def main(json_only=False):
    chart_path = MEMORY_DIR / "birth_chart.json"
    if not chart_path.exists():
        msg = f"Error: birth_chart.json not found at {chart_path}. Run birth_chart.py first."
        if json_only:
            print(json.dumps({"error": msg}))
        else:
            print(msg)
        return

    chart = json.loads(chart_path.read_text(encoding="utf-8"))
    now = now_ist()

    rahu_dasha = chart.get("current_dasha")
    if not rahu_dasha:
        msg = "Error: No current_dasha found in birth chart."
        if json_only:
            print(json.dumps({"error": msg}))
        else:
            print(msg)
        return

    rahu_start = datetime.strptime(rahu_dasha["start"], "%Y-%m-%d").replace(tzinfo=IST)
    rahu_end = datetime.strptime(rahu_dasha["end"], "%Y-%m-%d").replace(tzinfo=IST)

    output = {"maha_dasha": rahu_dasha, "antardashas": [], "pratyantardashas": []}

    if not json_only:
        print("=" * 70)
        print(f"  {rahu_dasha['planet'].upper()} MAHADASHA - ANTARDASHA (SUB-PERIODS)")
        print(f"  {rahu_dasha['start']} to {rahu_dasha['end']}")
        print("=" * 70)

    current = rahu_start
    maha_planet = rahu_dasha.get("planet", "Rahu")
    rahu_idx = DASHA_SEQ.index(maha_planet)

    for i in range(9):
        idx = (rahu_idx + i) % 9
        planet = DASHA_SEQ[idx]
        ad_years = (DASHA_YEARS[maha_planet] * DASHA_YEARS[planet]) / TOTAL
        ad_days = ad_years * 365.25
        end = current + timedelta(days=ad_days)
        is_current = current <= now <= end
        marker = " <-- CURRENT" if is_current else ""
        start_str = current.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        entry = {
            "maha": maha_planet, "antar": planet,
            "start": start_str, "end": end_str,
            "years": round(ad_years, 2), "is_current": is_current
        }
        output["antardashas"].append(entry)
        if not json_only:
            print(f"  {maha_planet}-{planet:<8s} {start_str} to {end_str}  ({ad_years:.2f} yrs){marker}")
        if is_current:
            current_ad = entry
            ad_planet = planet
            ad_start = current
            ad_end_date = end
        current = end

    # Pratyantardasha for current Antardasha
    if "current_ad" in dir():
        if not json_only:
            print()
            print("=" * 70)
            print(f"  CURRENT: {maha_planet}-{ad_planet} ANTARDASHA - PRATYANTARDASHA")
            print("=" * 70)

        ad_idx = DASHA_SEQ.index(ad_planet)
        current_p = ad_start
        for i in range(9):
            idx2 = (ad_idx + i) % 9
            p2 = DASHA_SEQ[idx2]
            pd_years = (DASHA_YEARS[maha_planet] * DASHA_YEARS[ad_planet] * DASHA_YEARS[p2]) / (TOTAL * TOTAL)
            pd_days = pd_years * 365.25
            end_p = current_p + timedelta(days=pd_days)
            is_cur = current_p <= now <= end_p
            marker = " <-- CURRENT" if is_cur else ""
            entry = {
                "maha": maha_planet, "antar": ad_planet, "pratyantar": p2,
                "start": current_p.strftime("%Y-%m-%d"),
                "end": end_p.strftime("%Y-%m-%d"),
                "years": round(pd_years, 3), "is_current": is_cur
            }
            output["pratyantardashas"].append(entry)
            if not json_only:
                print(f"  {maha_planet}-{ad_planet}-{p2:<8s} {current_p.strftime('%Y-%m-%d')} to {end_p.strftime('%Y-%m-%d')}  ({pd_years:.3f} yrs){marker}")
            current_p = end_p

    if json_only:
        output["calculated_at"] = now.isoformat()
        print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vedic Dasha Sub-Period Calculator")
    parser.add_argument("--json-only", action="store_true", help="JSON output only")
    args = parser.parse_args()
    main(json_only=args.json_only)

