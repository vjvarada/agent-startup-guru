"""
Vedic Yoga (Planetary Combination) Analysis

Performs detailed yoga checks on the natal chart: Gajakesari, Chandra-Mangal,
Budhaditya, Parivartana, Viparita Raja, and other key planetary combinations.

Usage:
    python yoga_analysis.py                # Print detailed analysis
    python yoga_analysis.py --json-only    # JSON output for agent consumption
"""
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
# .github/skills/vedic-astrology/scripts/ → vedic-astrology/ → skills/ → .github/ → repo root
REPO_ROOT = SCRIPT_DIR.parent.parent.parent.parent
MEMORY_DIR = REPO_ROOT / "outputs" / "_memory"

# Import Rashi constants from sibling birth_chart module
sys.path.insert(0, str(SCRIPT_DIR))
from birth_chart import RASHIS, RASHI_LORDS


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
    planets = chart["planets"]
    lagna = chart["lagna"]

    # Get all rashi indices
    rashis = {p: data["rashi_index"] for p, data in planets.items()}
    lagna_rashi = lagna["rashi_index"]

    if not json_only:
        print("=" * 70)
        print("  DETAILED YOGA ANALYSIS")
        print(f"  Birth: June 18, 1992, 3:30 AM, Secunderabad")
        print(f"  Lagna: {lagna['rashi']} ({lagna_rashi})")
        print("=" * 70)

    yogas = []
    checks = []

    # 1. Gajakesari Yoga: Jupiter in kendra from Moon
    moon_r = rashis["Moon"]
    jup_r = rashis["Jupiter"]
    diff = (jup_r - moon_r) % 12
    check = {"name": "Gajakesari Yoga", "condition": f"Jupiter in kendra from Moon (diff={diff})", "result": diff in [0, 3, 6, 9]}
    checks.append(check)
    if check["result"]:
        yogas.append("Gajakesari Yoga")

    # 2. Chandra-Mangal Yoga: Moon-Mars connection
    mars_r = rashis["Mars"]
    mars_aspects = [(mars_r + 3) % 12, (mars_r + 6) % 12, (mars_r + 7) % 12]
    cm_result = rashis["Moon"] == rashis["Mars"] or moon_r in mars_aspects
    check = {"name": "Chandra-Mangal Yoga", "condition": f"Moon-Mars conjunction or Mars aspect on Moon", "result": cm_result}
    checks.append(check)
    if cm_result:
        yogas.append("Chandra-Mangal Yoga" if rashis["Moon"] == rashis["Mars"] else "Chandra-Mangal (aspect)")

    # 3. Budhaditya Yoga: Sun-Mercury same sign
    b_result = rashis["Sun"] == rashis["Mercury"]
    check = {"name": "Budhaditya Yoga", "condition": "Sun-Mercury same sign", "result": b_result}
    checks.append(check)
    if b_result:
        yogas.append("Budhaditya Yoga")

    # 4. Parivartana Yoga (exchange of signs)
    for p1_name, p1_rashi in rashis.items():
        if p1_name in ["Rahu", "Ketu"]:
            continue
        p1_own_signs = [i for i, lord in enumerate(RASHI_LORDS) if lord == p1_name]
        for p2_name, p2_rashi in rashis.items():
            if p2_name in ["Rahu", "Ketu"] or p2_name == p1_name:
                continue
            p2_own_signs = [i for i, lord in enumerate(RASHI_LORDS) if lord == p2_name]
            if p1_rashi in p2_own_signs and p2_rashi in p1_own_signs:
                h1 = (p1_rashi - lagna_rashi) % 12 + 1
                h2 = (p2_rashi - lagna_rashi) % 12 + 1
                label = f"Parivartana: {p1_name}-{p2_name} (H{h1}-H{h2})"
                yogas.append(label)
                checks.append({"name": "Parivartana Yoga", "condition": f"{p1_name} in {p2_name}'s sign (H{h1}) and {p2_name} in {p1_name}'s sign (H{h2})", "result": True})

    # 5. Viparita Raja Yoga: Lords of 6,8,12 in 6,8,12
    h6_rashi = (lagna_rashi + 5) % 12
    h8_rashi = (lagna_rashi + 7) % 12
    h12_rashi = (lagna_rashi + 11) % 12
    dusthana_rashis = {h6_rashi, h8_rashi, h12_rashi}
    h6_lord = RASHI_LORDS[h6_rashi]
    h8_lord = RASHI_LORDS[h8_rashi]
    h12_lord = RASHI_LORDS[h12_rashi]
    dusthana_lords = {h6_lord, h8_lord, h12_lord}
    viparita_planets = []
    for p, r in rashis.items():
        if p in ["Rahu", "Ketu"]:
            continue
        if p in dusthana_lords and r in dusthana_rashis:
            viparita_planets.append(p)
    check = {"name": "Viparita Raja Yoga", "condition": f"Lords of 6/8/12 in dusthana houses", "result": len(viparita_planets) > 0, "planets": viparita_planets}
    checks.append(check)
    if viparita_planets:
        yogas.append(f"Viparita Raja ({', '.join(viparita_planets)})")

    # Build output
    result = {
        "lagna": lagna["rashi"],
        "lagna_index": lagna_rashi,
        "yogas_detected": yogas,
        "checks": checks,
        "total_yogas": len(yogas),
        "calculated_at": datetime.now().isoformat()
    }

    if json_only:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"\nYogas detected: {len(yogas)}")
        for y in yogas:
            print(f"  + {y}")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vedic Yoga Analysis")
    parser.add_argument("--json-only", action="store_true", help="JSON output only")
    args = parser.parse_args()
    main(json_only=args.json_only)

