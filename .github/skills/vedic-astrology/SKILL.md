---
name: vedic-astrology
description: >
  Vedic (Jyotish) astrology interpretation framework for startup decisions.
  Dasha periods, transits, muhurta timing, house activation, yogas,
  and chart-specific insights. Use when analyzing birth charts or
  giving astrological guidance for business timing.
when_to_use: "When the agent needs to interpret astrological data for timing, decisions, or chart analysis."
authority: read
cost_tier: 1
version: 0.1.0
---

# Vedic Astrology Reference Directive

## Purpose
Reference guide for interpreting Vijay's Vedic birth chart in the context of startup decisions. This is NOT a general astrology guide — it's tailored to entrepreneurial decision-making.

## Birth Data
- **Name**: Vijay Raghav Varada
- **Date**: June 18, 1992
- **Time**: 3:30 AM IST
- **Place**: Secunderabad, India (17.4399°N, 78.4983°E)
- **Ayanamsa**: Lahiri
- **System**: Whole-sign houses

## Scripts

| Script | Purpose |
|--------|--------|
| `scripts/birth_chart.py` | Calculate full Vedic natal chart (Rashi, Navamsha, Dashas, Yogas, Nakshatras) |
| `scripts/transit_calculator.py` | Current planetary transits vs natal chart, upcoming transit windows |

## How to Calculate Charts

### Initial Setup (run once):
```bash
python .github/skills/vedic-astrology/scripts/birth_chart.py --date "1992-06-18" --time "03:30" --lat 17.4399 --lon 78.4983 --city "Secunderabad" --save
```
This saves the chart to `outputs/_memory/birth_chart.json`.

### Check Current Transits:
```bash
python .github/skills/vedic-astrology/scripts/transit_calculator.py
```

### Look Ahead:
```bash
python .github/skills/vedic-astrology/scripts/transit_calculator.py --range 90  # Next 90 days
python .github/skills/vedic-astrology/scripts/transit_calculator.py --range 365  # Next year
```

## Interpretation Framework for Startups

### Dasha Periods — What Phase of Life
The Vimshottari Dasha system divides life into planetary periods. Each planet colors the entire period's themes:

| Dasha Lord | Duration | Startup Implications |
|-----------|----------|---------------------|
| **Ketu** | 7 years | Research mode, spiritual ventures, deep tech, letting go of old things |
| **Venus** | 20 years | Design, luxury, creative products, partnerships, fundraising, aesthetics |
| **Sun** | 6 years | Leadership, authority, government, personal brand, solar industries |
| **Moon** | 10 years | Public-facing, emotions, marketing, consumer products, nurturing teams |
| **Mars** | 7 years | Manufacturing, competition, physical products, rapid action, R&D, defense |
| **Rahu** | 18 years | Disruption, unconventional paths, foreign markets, tech, rapid scaling |
| **Jupiter** | 16 years | Wisdom, expansion, mentors, education, international, ethics |
| **Saturn** | 19 years | Discipline, restructuring, systems, government, long-term building |
| **Mercury** | 17 years | Communication, technology, B2B, partnerships, trading, data |

### Transits — Current Weather
Key transits to track for startup timing:

**Jupiter** (in a sign ~1 year):
- Through 1st house: Personal growth, new beginnings, confidence
- Through 5th house: Creativity, product ideas, innovation
- Through 9th house: Vision, mentors, international opportunities
- Through 10th house: Career peak, recognition, achievements
- Through 11th house: Network growth, revenue increase, goals manifest

**Saturn** (in a sign ~2.5 years):
- Through 1st house: Self-discipline, restructuring identity
- Through 7th house: Partnership lessons, serious collaborations
- Through 10th house: Career consolidation, authority tested
- Sade Sati (7.5 yrs around Moon): Deep transformation, maturity

**Rahu-Ketu** (in a sign ~1.5 years):
- Rahu in 10th: Ambitious career moves, unconventional rise
- Ketu in 4th: Detaching from comfort zone, office changes
- Rahu in 1st: Identity transformation, trying new things
- Rahu in 11th: Expanding network, social media, community

### Favorable Timing Indicators (Muhurta)
For important launches, partnerships, or decisions, prefer:
- Jupiter aspecting the relevant house
- Moon in benefic nakshatra (Rohini, Pushya, Shravana, Hasta, Chitra)
- Avoid eclipses, combustions, and retrograde Mercury for launches
- Mars hour for competitive moves, Jupiter hour for expansion, Venus hour for partnerships

### Chart-Specific Insights
After calculating the birth chart, note:
1. **Lagna Lord strength** — indicates overall life direction and health
2. **10th house & lord** — career direction and public life
3. **2nd & 11th house** — wealth accumulation patterns
4. **7th house** — partnership karma
5. **5th house** — creative intelligence, children, innovation
6. **9th house** — luck, mentors, dharma, international
7. **Yogas** — special planetary combinations that indicate specific strengths

## Important Caveats
1. This is **approximate calculation** using simplified ephemeris. For exact positions, cross-reference with Jagannatha Hora or Astro-Sage
2. Astrology is a **lens, not a verdict**. Use it to inform timing and awareness, not to prevent action
3. Always present both the astrological reading AND the business rationale
4. If astrology and business logic conflict, business logic should weight 60%
5. Sub-periods (Antardasha, Pratyantardasha) provide more granular timing — calculate when needed

## Updating This Directive
Record observations here as we learn what interpretations prove accurate:

### Validated Patterns
_To be filled as we track decisions and outcomes_

### Adjustments Needed
_To be filled as we learn from experience_
