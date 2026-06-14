#!/usr/bin/env python3
"""
Vedic Birth Chart Calculator

Calculates a complete Vedic (Jyotish) birth chart including:
- Lagna (Ascendant) and planetary positions in sidereal zodiac
- Rashi chart (D1) and Navamsha chart (D9)
- Vimshottari Dasha periods
- Key Yogas (planetary combinations)
- Nakshatra (lunar mansion) positions

Uses the Swiss Ephemeris (pyswisseph) for precise astronomical calculations,
and applies Lahiri ayanamsa for sidereal conversion.

Usage:
    python birth_chart.py --date "1992-06-18" --time "03:30" --lat 17.4399 --lon 78.4983 --city "Secunderabad"
    python birth_chart.py --from-profile      # Reads from outputs/_memory/founder_profile.json
    python birth_chart.py --save              # Saves chart to outputs/_memory/birth_chart.json
"""

import os
import sys
import json
import math
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import swisseph as swe

SCRIPT_DIR = Path(__file__).parent.resolve()
# .tmp/scripts/ → .tmp/ → repo root
REPO_ROOT = SCRIPT_DIR.parent.parent
MEMORY_DIR = REPO_ROOT / "outputs" / "_memory"

# ─── Swiss Ephemeris Setup ────────────────────────────────────────────
swe.set_sid_mode(swe.SIDM_LAHIRI)

# IST (Indian Standard Time) offset from UTC in hours
IST_OFFSET_HOURS = 5.5

RASHIS = [
    "Mesha (Aries)", "Vrishabha (Taurus)", "Mithuna (Gemini)",
    "Karka (Cancer)", "Simha (Leo)", "Kanya (Virgo)",
    "Tula (Libra)", "Vrishchika (Scorpio)", "Dhanu (Sagittarius)",
    "Makara (Capricorn)", "Kumbha (Aquarius)", "Meena (Pisces)"
]

RASHI_LORDS = [
    "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
    "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

NAKSHATRA_LORDS = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury", "Ketu", "Venus", "Sun",
    "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury"
]

# Vimshottari Dasha periods (years)
DASHA_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17
}

DASHA_SEQUENCE = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
TOTAL_DASHA_YEARS = 120  # Full Vimshottari cycle


def local_to_utc(dt_local, tz_offset_hours=IST_OFFSET_HOURS):
    """Convert local time to UTC."""
    return dt_local - timedelta(hours=tz_offset_hours)


def _datetime_to_jd(dt_utc):
    """Convert UTC datetime to Julian Day number."""
    hour_decimal = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour_decimal)


def calculate_ayanamsa(dt_utc):
    """Calculate Lahiri ayanamsa for a given UTC datetime using Swiss Ephemeris."""
    jd = _datetime_to_jd(dt_utc)
    return swe.get_ayanamsa(jd)


def tropical_to_sidereal(tropical_deg, ayanamsa):
    """Convert tropical longitude to sidereal."""
    sidereal = tropical_deg - ayanamsa
    if sidereal < 0:
        sidereal += 360.0
    return sidereal % 360.0


def get_rashi(sidereal_deg):
    """Get Rashi (sign) index and degree within sign."""
    sign_index = int(sidereal_deg / 30) % 12
    degree_in_sign = sidereal_deg % 30
    return sign_index, degree_in_sign


def get_nakshatra(sidereal_deg):
    """Get Nakshatra index and pada."""
    nak_index = int(sidereal_deg / (360 / 27)) % 27
    degree_in_nak = sidereal_deg % (360 / 27)
    pada = int(degree_in_nak / (360 / 108)) + 1
    return nak_index, pada


def get_navamsha_sign(sidereal_deg):
    """Calculate Navamsha (D9) sign from sidereal degree."""
    # Each sign has 9 navamshas of 3°20' each
    navamsha_number = int(sidereal_deg / (10/3)) % 108
    # Navamsha sign: for fire signs starts from same sign, etc.
    rashi_index = int(sidereal_deg / 30) % 12
    element = rashi_index % 4  # 0=fire, 1=earth, 2=air, 3=water
    start_sign = element * 3  # fire->0(Aries), earth->3(Cancer), air->6(Libra), water->9(Capricorn)
    navamsha_in_sign = int((sidereal_deg % 30) / (10/3))
    navamsha_sign = (start_sign + navamsha_in_sign) % 12
    return navamsha_sign


def approximate_planetary_positions(dt_utc):
    """
    Calculate tropical planetary longitudes using Swiss Ephemeris.

    Args:
        dt_utc: datetime in UTC

    Returns:
        dict of planet -> tropical longitude in degrees.
    """
    jd = _datetime_to_jd(dt_utc)

    planet_ids = {
        "Sun": swe.SUN,
        "Moon": swe.MOON,
        "Mercury": swe.MERCURY,
        "Venus": swe.VENUS,
        "Mars": swe.MARS,
        "Jupiter": swe.JUPITER,
        "Saturn": swe.SATURN,
    }

    positions = {}
    for name, pid in planet_ids.items():
        result, _ = swe.calc_ut(jd, pid, swe.FLG_SWIEPH)
        positions[name] = result[0]

    # Rahu (Mean North Node) — standard in Vedic astrology
    result, _ = swe.calc_ut(jd, swe.MEAN_NODE, swe.FLG_SWIEPH)
    positions["Rahu"] = result[0]

    # Ketu (South Node — opposite Rahu)
    positions["Ketu"] = (positions["Rahu"] + 180) % 360

    return positions


def calculate_lagna(dt_utc, lat, lon):
    """
    Calculate Lagna (Ascendant) for given UTC time and location using Swiss Ephemeris.
    Returns tropical ascendant longitude in degrees.
    """
    jd = _datetime_to_jd(dt_utc)
    houses, ascmc = swe.houses(jd, lat, lon, b'P')  # Placidus house system
    return ascmc[0]  # Ascendant tropical longitude


def calculate_vimshottari_dasha(moon_sidereal_deg, birth_dt):
    """
    Calculate Vimshottari Dasha periods from Moon's nakshatra position.

    Returns list of Maha Dasha periods with start/end dates.
    """
    nak_index, pada = get_nakshatra(moon_sidereal_deg)
    nak_lord = NAKSHATRA_LORDS[nak_index]

    # Calculate elapsed portion of first dasha
    degree_in_nak = moon_sidereal_deg % (360 / 27)
    nak_span = 360 / 27
    fraction_elapsed = degree_in_nak / nak_span

    # Find starting dasha lord in sequence
    start_idx = DASHA_SEQUENCE.index(nak_lord)
    first_dasha_total_years = DASHA_YEARS[nak_lord]
    remaining_years = first_dasha_total_years * (1 - fraction_elapsed)

    dashas = []
    current_date = birth_dt

    # First (partial) dasha
    end_date = current_date + timedelta(days=remaining_years * 365.25)
    dashas.append({
        "planet": nak_lord,
        "start": current_date.strftime("%Y-%m-%d"),
        "end": end_date.strftime("%Y-%m-%d"),
        "years": round(remaining_years, 2),
        "is_partial": True
    })
    current_date = end_date

    # Subsequent full dashas
    for i in range(1, 9):
        idx = (start_idx + i) % 9
        planet = DASHA_SEQUENCE[idx]
        years = DASHA_YEARS[planet]
        end_date = current_date + timedelta(days=years * 365.25)
        dashas.append({
            "planet": planet,
            "start": current_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "years": years,
            "is_partial": False
        })
        current_date = end_date

    return dashas


def identify_yogas(planets_sidereal):
    """
    Identify key Vedic yogas (planetary combinations) in the chart.
    Returns list of identified yogas with descriptions.
    """
    yogas = []

    # Get rashi indices for all planets
    rashis = {}
    for planet, deg in planets_sidereal.items():
        rashis[planet] = get_rashi(deg)[0]

    # Gajakesari Yoga: Jupiter in kendra from Moon
    moon_rashi = rashis.get("Moon", -1)
    jup_rashi = rashis.get("Jupiter", -1)
    if moon_rashi >= 0 and jup_rashi >= 0:
        diff = (jup_rashi - moon_rashi) % 12
        if diff in [0, 3, 6, 9]:
            yogas.append({
                "name": "Gajakesari Yoga",
                "planets": ["Moon", "Jupiter"],
                "description": "Jupiter in kendra (1st/4th/7th/10th) from Moon. Bestows wisdom, wealth, fame, and leadership qualities. Excellent for public recognition and business success.",
                "strength": "Strong"
            })

    # Budhaditya Yoga: Sun and Mercury in same sign
    if rashis.get("Sun") == rashis.get("Mercury"):
        yogas.append({
            "name": "Budhaditya Yoga",
            "planets": ["Sun", "Mercury"],
            "description": "Sun-Mercury conjunction. Grants intelligence, communication skills, analytical mind, and success in intellectual pursuits. Excellent for entrepreneurship and tech.",
            "strength": "Strong"
        })

    # Chandra-Mangal Yoga: Moon and Mars in same sign or mutual aspect
    if rashis.get("Moon") == rashis.get("Mars"):
        yogas.append({
            "name": "Chandra-Mangal Yoga",
            "planets": ["Moon", "Mars"],
            "description": "Moon-Mars conjunction. Gives wealth through enterprise, courage, and determination. Good for manufacturing and hands-on businesses.",
            "strength": "Moderate"
        })

    # Hamsa Yoga: Jupiter in own sign or exalted in kendra
    jup_deg = planets_sidereal.get("Jupiter", 0)
    jup_rashi_idx = rashis.get("Jupiter", -1)
    lagna_rashi = rashis.get("Lagna", -1)
    if jup_rashi_idx in [8, 11, 3]:  # Sagittarius, Pisces, Cancer (own/exalted)
        if lagna_rashi >= 0:
            diff = (jup_rashi_idx - lagna_rashi) % 12
            if diff in [0, 3, 6, 9]:
                yogas.append({
                    "name": "Hamsa Yoga",
                    "planets": ["Jupiter"],
                    "description": "One of the Pancha Mahapurusha Yogas. Jupiter strong in kendra. Bestows righteousness, spiritual wisdom, respect, and good fortune.",
                    "strength": "Very Strong"
                })

    # Dhana Yoga indicators: Lords of 2nd and 11th in mutual aspect or conjunction
    # (Simplified: check if benefics are in 2nd or 11th from Lagna)
    if lagna_rashi >= 0:
        second_house = (lagna_rashi + 1) % 12
        eleventh_house = (lagna_rashi + 10) % 12
        benefics_in_money_houses = []
        for planet in ["Jupiter", "Venus", "Mercury"]:
            if rashis.get(planet) in [second_house, eleventh_house]:
                benefics_in_money_houses.append(planet)
        if benefics_in_money_houses:
            yogas.append({
                "name": "Dhana Yoga (Wealth Indicator)",
                "planets": benefics_in_money_houses,
                "description": f"Benefic planet(s) {', '.join(benefics_in_money_houses)} in wealth houses (2nd/11th). Indicates potential for wealth accumulation.",
                "strength": "Moderate"
            })

    # Raja Yoga indicators: Kendra-Trikona lord connections
    # (Simplified check)
    if lagna_rashi >= 0:
        kendra_houses = [lagna_rashi, (lagna_rashi + 3) % 12, (lagna_rashi + 6) % 12, (lagna_rashi + 9) % 12]
        trikona_houses = [lagna_rashi, (lagna_rashi + 4) % 12, (lagna_rashi + 8) % 12]
        kendra_planets = [p for p, r in rashis.items() if r in kendra_houses and p not in ["Rahu", "Ketu", "Lagna"]]
        trikona_planets = [p for p, r in rashis.items() if r in trikona_houses and p not in ["Rahu", "Ketu", "Lagna"]]
        raja_planets = set(kendra_planets) & set(trikona_planets)
        if raja_planets:
            yogas.append({
                "name": "Raja Yoga Potential",
                "planets": list(raja_planets),
                "description": f"Planet(s) {', '.join(raja_planets)} placed in both kendra and trikona influence. Indicates leadership ability and rise to prominence.",
                "strength": "Strong"
            })

    return yogas


def calculate_full_chart(date_str, time_str, lat, lon, city="Unknown"):
    """
    Calculate complete Vedic birth chart.

    Args:
        date_str: "YYYY-MM-DD"
        time_str: "HH:MM" (24-hour format)
        lat: Latitude
        lon: Longitude
        city: City name

    Returns:
        Complete chart data dictionary
    """
    # Parse birth datetime (local IST time)
    birth_dt_local = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

    # Convert to UTC for astronomical calculations
    birth_dt_utc = local_to_utc(birth_dt_local)

    # Calculate ayanamsa
    ayanamsa = calculate_ayanamsa(birth_dt_utc)

    # Get tropical planetary positions
    tropical_positions = approximate_planetary_positions(birth_dt_utc)

    # Calculate Lagna (Ascendant) - tropical first, then convert
    lagna_tropical = calculate_lagna(birth_dt_utc, lat, lon)

    # Convert all to sidereal
    sidereal_positions = {}
    for planet, deg in tropical_positions.items():
        sidereal_positions[planet] = tropical_to_sidereal(deg, ayanamsa)

    lagna_sidereal = tropical_to_sidereal(lagna_tropical, ayanamsa)
    sidereal_positions["Lagna"] = lagna_sidereal

    # Build chart data
    chart = {
        "meta": {
            "name": city,
            "date": date_str,
            "time": time_str,
            "latitude": lat,
            "longitude": lon,
            "city": city,
            "ayanamsa": round(ayanamsa, 4),
            "ayanamsa_type": "Lahiri",
            "calculation_note": "Calculated using Swiss Ephemeris (pyswisseph) with Lahiri ayanamsa.",
            "calculated_at": datetime.now().isoformat()
        },
        "lagna": {},
        "planets": {},
        "houses": {},
        "nakshatras": {},
        "navamsha": {},
        "dashas": [],
        "yogas": []
    }

    # Lagna details
    lagna_rashi, lagna_deg = get_rashi(lagna_sidereal)
    lagna_nak, lagna_pada = get_nakshatra(lagna_sidereal)
    chart["lagna"] = {
        "sidereal_longitude": round(lagna_sidereal, 2),
        "rashi": RASHIS[lagna_rashi],
        "rashi_index": lagna_rashi,
        "degree_in_sign": round(lagna_deg, 2),
        "rashi_lord": RASHI_LORDS[lagna_rashi],
        "nakshatra": NAKSHATRAS[lagna_nak],
        "nakshatra_pada": lagna_pada,
        "navamsha_sign": RASHIS[get_navamsha_sign(lagna_sidereal)]
    }

    # Planet details
    for planet in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
        deg = sidereal_positions[planet]
        rashi_idx, deg_in_sign = get_rashi(deg)
        nak_idx, pada = get_nakshatra(deg)
        nav_sign = get_navamsha_sign(deg)

        chart["planets"][planet] = {
            "sidereal_longitude": round(deg, 2),
            "rashi": RASHIS[rashi_idx],
            "rashi_index": rashi_idx,
            "degree_in_sign": round(deg_in_sign, 2),
            "rashi_lord": RASHI_LORDS[rashi_idx],
            "nakshatra": NAKSHATRAS[nak_idx],
            "nakshatra_pada": pada,
            "nakshatra_lord": NAKSHATRA_LORDS[nak_idx],
            "navamsha_sign": RASHIS[nav_sign],
            "navamsha_index": nav_sign
        }

    # House occupants (whole-sign houses from Lagna)
    for i in range(12):
        house_num = i + 1
        house_rashi = (lagna_rashi + i) % 12
        planets_in_house = []
        for planet, data in chart["planets"].items():
            if data["rashi_index"] == house_rashi:
                planets_in_house.append(planet)
        chart["houses"][str(house_num)] = {
            "rashi": RASHIS[house_rashi],
            "rashi_lord": RASHI_LORDS[house_rashi],
            "planets": planets_in_house
        }

    # Navamsha chart
    nav_chart = {}
    nav_chart["Lagna"] = RASHIS[get_navamsha_sign(lagna_sidereal)]
    for planet in chart["planets"]:
        nav_chart[planet] = chart["planets"][planet]["navamsha_sign"]
    chart["navamsha"] = nav_chart

    # Vimshottari Dasha
    moon_deg = sidereal_positions["Moon"]
    chart["dashas"] = calculate_vimshottari_dasha(moon_deg, birth_dt_local)

    # Current Dasha
    now = datetime.now()
    current_dasha = None
    for dasha in chart["dashas"]:
        start = datetime.strptime(dasha["start"], "%Y-%m-%d")
        end = datetime.strptime(dasha["end"], "%Y-%m-%d")
        if start <= now <= end:
            current_dasha = dasha
            break
    chart["current_dasha"] = current_dasha

    # Yogas
    chart["yogas"] = identify_yogas(sidereal_positions)

    return chart


def print_chart_summary(chart):
    """Print a readable summary of the chart."""
    print("\n" + "=" * 70)
    print("  VEDIC BIRTH CHART (KUNDLI)")
    print(f"  {chart['meta']['city']} | {chart['meta']['date']} | {chart['meta']['time']}")
    print(f"  Ayanamsa: {chart['meta']['ayanamsa']}° ({chart['meta']['ayanamsa_type']})")
    print("=" * 70)

    # Lagna
    l = chart["lagna"]
    print(f"\n🔱 LAGNA (Ascendant): {l['rashi']} at {l['degree_in_sign']}°")
    print(f"   Nakshatra: {l['nakshatra']} (Pada {l['nakshatra_pada']})")
    print(f"   Lord: {l['rashi_lord']}")
    print(f"   Navamsha: {l['navamsha_sign']}")

    # Planets
    print(f"\n{'─' * 70}")
    print(f"  {'Planet':<10} {'Rashi':<25} {'Degree':<8} {'Nakshatra':<20} {'Pada'}")
    print(f"{'─' * 70}")
    for planet, data in chart["planets"].items():
        print(f"  {planet:<10} {data['rashi']:<25} {data['degree_in_sign']:>5.1f}°  {data['nakshatra']:<20} {data['nakshatra_pada']}")

    # Houses
    print(f"\n{'─' * 70}")
    print("  BHAVA CHART (Whole-Sign Houses)")
    print(f"{'─' * 70}")
    for house_num, house_data in chart["houses"].items():
        planets_str = ", ".join(house_data["planets"]) if house_data["planets"] else "—"
        print(f"  House {house_num:>2}: {house_data['rashi']:<25} Lord: {house_data['rashi_lord']:<10} Planets: {planets_str}")

    # Navamsha
    print(f"\n{'─' * 70}")
    print("  NAVAMSHA (D9) CHART")
    print(f"{'─' * 70}")
    for planet, sign in chart["navamsha"].items():
        print(f"  {planet:<10} → {sign}")

    # Dashas
    print(f"\n{'─' * 70}")
    print("  VIMSHOTTARI DASHA PERIODS")
    print(f"{'─' * 70}")
    now = datetime.now()
    for dasha in chart["dashas"]:
        start = datetime.strptime(dasha["start"], "%Y-%m-%d")
        end = datetime.strptime(dasha["end"], "%Y-%m-%d")
        marker = " ← CURRENT" if start <= now <= end else ""
        partial = " (partial)" if dasha["is_partial"] else ""
        print(f"  {dasha['planet']:<10} {dasha['start']} to {dasha['end']}  ({dasha['years']} yrs{partial}){marker}")

    # Yogas
    if chart["yogas"]:
        print(f"\n{'─' * 70}")
        print("  YOGAS (Planetary Combinations)")
        print(f"{'─' * 70}")
        for yoga in chart["yogas"]:
            print(f"\n  ✦ {yoga['name']} [{yoga['strength']}]")
            print(f"    Planets: {', '.join(yoga['planets'])}")
            print(f"    {yoga['description']}")

    print(f"\n{'=' * 70}")
    print(f"  Note: {chart['meta']['calculation_note']}")
    print(f"{'=' * 70}\n")


def save_chart(chart, filepath=None):
    """Save chart to JSON file."""
    if filepath is None:
        filepath = MEMORY_DIR / "birth_chart.json"
    else:
        filepath = Path(filepath)

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(chart, f, indent=2, ensure_ascii=False)

    print(f"Chart saved to {filepath}")


def load_profile():
    """Load founder profile from memory."""
    profile_path = MEMORY_DIR / "founder_profile.json"
    if profile_path.exists():
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def main():
    parser = argparse.ArgumentParser(description="Vedic Birth Chart Calculator")
    parser.add_argument("--date", type=str, help="Birth date (YYYY-MM-DD)")
    parser.add_argument("--time", type=str, help="Birth time (HH:MM, 24-hour)")
    parser.add_argument("--lat", type=float, help="Latitude")
    parser.add_argument("--lon", type=float, help="Longitude")
    parser.add_argument("--city", type=str, default="Unknown", help="City name")
    parser.add_argument("--from-profile", action="store_true", help="Load birth data from memory/founder_profile.json")
    parser.add_argument("--save", action="store_true", help="Save chart to memory/birth_chart.json")
    parser.add_argument("--output", type=str, help="Custom output filepath for JSON")
    parser.add_argument("--json-only", action="store_true", help="Output JSON only (no formatted display)")

    args = parser.parse_args()

    if args.from_profile:
        profile = load_profile()
        if not profile or "birth" not in profile:
            print("Error: No birth data found in memory/founder_profile.json")
            sys.exit(1)
        birth = profile["birth"]
        date_str = birth["date"]
        time_str = birth["time"]
        lat = birth["latitude"]
        lon = birth["longitude"]
        city = birth.get("city", "Unknown")
    elif args.date and args.time and args.lat is not None and args.lon is not None:
        date_str = args.date
        time_str = args.time
        lat = args.lat
        lon = args.lon
        city = args.city
    else:
        print("Error: Provide --date, --time, --lat, --lon OR use --from-profile")
        sys.exit(1)

    chart = calculate_full_chart(date_str, time_str, lat, lon, city)

    if args.json_only:
        print(json.dumps(chart, indent=2, ensure_ascii=False))
    else:
        print_chart_summary(chart)

    if args.save or args.output:
        save_chart(chart, args.output)


if __name__ == "__main__":
    main()
