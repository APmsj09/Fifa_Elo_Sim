import pandas as pd
import numpy as np
import random
import math
import js
from pyodide.http import open_url

def calculate_recency_weight(match_date, latest_date):
    """
    Adjusted for International Football (Lower frequency of games).
    Matches from 4 years ago (full WC cycle) now retain ~60% importance.
    """
    days_old = (latest_date - match_date).days
    # Changed from 0.00065 to 0.00035
    return math.exp(-0.00035 * max(0, days_old))

# =============================================================================
# --- PART 1: SETUP & DATA LOADING ---
# =============================================================================

DATA_DIR = "data"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/APmsj09/Fifa_Elo_Sim/main"

# Global Vars
TEAM_STATS = {}
TEAM_PROFILES = {}
TEAM_HISTORY = {}
ADVANCED_TEAM_DATA = {} 
AVG_GOALS = 2.5
calculated_hfa = 0.0
PLAYER_DF = None
FORMATION_DF = None
TEAM_ROSTERS = {}
TEAM_FORMATIONS = {}

# The 48 Teams of World Cup 2026 (Fully Qualified)
WC_TEAMS = [
    # Group A
    'mexico', 'south africa', 'south korea', 'czech republic',
    # Group B
    'canada', 'bosnia and herzegovina', 'qatar', 'switzerland',
    # Group C
    'brazil', 'morocco', 'haiti', 'scotland',
    # Group D
    'united states', 'paraguay', 'australia', 'turkey',
    # Group E
    'germany', 'curaçao', 'ivory coast', 'ecuador',
    # Group F
    'netherlands', 'japan', 'sweden', 'tunisia',
    # Group G
    'belgium', 'egypt', 'iran', 'new zealand',
    # Group H
    'spain', 'cape verde', 'saudi arabia', 'uruguay',
    # Group I
    'france', 'senegal', 'iraq', 'norway',
    # Group J
    'argentina', 'algeria', 'austria', 'jordan',
    # Group K
    'portugal', 'dr congo', 'uzbekistan', 'colombia',
    # Group L
    'england', 'croatia', 'ghana', 'panama'
]

# =============================================================================
# --- ADVANCED TACTICAL METRICS & VOLATILITY DATA ---
# =============================================================================
# ADVANCED_TEAM_DATA = {
#     'france': {'type': 'Vertical Control', 'poss': 0.72, 'press': 0.58, 'dir': 0.52, 'vol': 0.04},
#     'spain': {'type': 'Vertical Control', 'poss': 0.92, 'press': 0.68, 'dir': 0.35, 'vol': 0.03},
#     'argentina': {'type': 'Vertical Control', 'poss': 0.78, 'press': 0.64, 'dir': 0.48, 'vol': 0.05},
#     'england': {'type': 'Vertical Control', 'poss': 0.88, 'press': 0.62, 'dir': 0.38, 'vol': 0.04},
#     'portugal': {'type': 'Vertical Control', 'poss': 0.84, 'press': 0.65, 'dir': 0.44, 'vol': 0.06},
#     'brazil': {'type': 'Vertical Control', 'poss': 0.74, 'press': 0.62, 'dir': 0.55, 'vol': 0.07},
#     'netherlands': {'type': 'Vertical Control', 'poss': 0.71, 'press': 0.64, 'dir': 0.52, 'vol': 0.07},
#     'morocco': {'type': 'Compact Block', 'poss': 0.41, 'press': 0.52, 'dir': 0.84, 'vol': 0.06},
#     'belgium': {'type': 'Vertical Control', 'poss': 0.68, 'press': 0.58, 'dir': 0.58, 'vol': 0.08},
#     'germany': {'type': 'Vertical Control', 'poss': 0.82, 'press': 0.75, 'dir': 0.60, 'vol': 0.11},
#     'croatia': {'type': 'Vertical Control', 'poss': 0.71, 'press': 0.52, 'dir': 0.42, 'vol': 0.05},
#     'italy': {'type': 'Vertical Control', 'poss': 0.70, 'press': 0.65, 'dir': 0.45, 'vol': 0.09},
#     'colombia': {'type': 'Vertical Control', 'poss': 0.64, 'press': 0.71, 'dir': 0.62, 'vol': 0.10},
#     'senegal': {'type': 'Chaos & Intensity', 'poss': 0.52, 'press': 0.78, 'dir': 0.79, 'vol': 0.13},
#     'mexico': {'type': 'Vertical Control', 'poss': 0.62, 'press': 0.65, 'dir': 0.58, 'vol': 0.12},
#     'united states': {'type': 'Chaos & Intensity', 'poss': 0.59, 'press': 0.82, 'dir': 0.68, 'vol': 0.14},
#     'uruguay': {'type': 'Chaos & Intensity', 'poss': 0.55, 'press': 0.94, 'dir': 0.84, 'vol': 0.12},
#     'japan': {'type': 'Vertical Control', 'poss': 0.63, 'press': 0.75, 'dir': 0.68, 'vol': 0.06},
#     'switzerland': {'type': 'Vertical Control', 'poss': 0.64, 'press': 0.55, 'dir': 0.48, 'vol': 0.05},
#     'denmark': {'type': 'Vertical Control', 'poss': 0.65, 'press': 0.70, 'dir': 0.55, 'vol': 0.08},
#     'iran': {'type': 'Compact Block', 'poss': 0.36, 'press': 0.35, 'dir': 0.88, 'vol': 0.04},
#     'turkey': {'type': 'Vertical Control', 'poss': 0.61, 'press': 0.68, 'dir': 0.64, 'vol': 0.11},
#     'ecuador': {'type': 'Direct-Physical', 'poss': 0.46, 'press': 0.68, 'dir': 0.78, 'vol': 0.09},
#     'austria': {'type': 'Chaos & Intensity', 'poss': 0.51, 'press': 0.88, 'dir': 0.76, 'vol': 0.12},
#     'south korea': {'type': 'Chaos & Intensity', 'poss': 0.51, 'press': 0.78, 'dir': 0.82, 'vol': 0.09},
#     'nigeria': {'type': 'Chaos & Intensity', 'poss': 0.50, 'press': 0.80, 'dir': 0.75, 'vol': 0.15},
#     'australia': {'type': 'Direct-Physical', 'poss': 0.48, 'press': 0.62, 'dir': 0.72, 'vol': 0.07},
#     'algeria': {'type': 'Vertical Control', 'poss': 0.58, 'press': 0.62, 'dir': 0.62, 'vol': 0.12},
#     'egypt': {'type': 'Compact Block', 'poss': 0.43, 'press': 0.42, 'dir': 0.82, 'vol': 0.08},
#     'canada': {'type': 'Vertical Control', 'poss': 0.58, 'press': 0.72, 'dir': 0.64, 'vol': 0.13},
#     'norway': {'type': 'Chaos & Intensity', 'poss': 0.58, 'press': 0.72, 'dir': 0.91, 'vol': 0.11},
#     'ukraine': {'type': 'Vertical Control', 'poss': 0.62, 'press': 0.60, 'dir': 0.50, 'vol': 0.09},
#     'panama': {'type': 'Compact Block', 'poss': 0.37, 'press': 0.42, 'dir': 0.75, 'vol': 0.10},
#     'ivory coast': {'type': 'Chaos & Intensity', 'poss': 0.54, 'press': 0.71, 'dir': 0.74, 'vol': 0.14},
#     'poland': {'type': 'Direct-Physical', 'poss': 0.44, 'press': 0.55, 'dir': 0.80, 'vol': 0.11},
#     'russia': {'type': 'Vertical Control', 'poss': 0.55, 'press': 0.58, 'dir': 0.62, 'vol': 0.16},
#     'wales': {'type': 'Direct-Physical', 'poss': 0.42, 'press': 0.65, 'dir': 0.78, 'vol': 0.09},
#     'sweden': {'type': 'Chaos & Intensity', 'poss': 0.52, 'press': 0.72, 'dir': 0.86, 'vol': 0.12},
#     'serbia': {'type': 'Direct-Physical', 'poss': 0.45, 'press': 0.55, 'dir': 0.78, 'vol': 0.14},
#     'paraguay': {'type': 'Compact Block', 'poss': 0.37, 'press': 0.55, 'dir': 0.79, 'vol': 0.09},
#     'czech republic': {'type': 'Chaos & Intensity', 'poss': 0.48, 'press': 0.85, 'dir': 0.75, 'vol': 0.11},
#     'hungary': {'type': 'Compact Block', 'poss': 0.40, 'press': 0.45, 'dir': 0.70, 'vol': 0.07},
#     'scotland': {'type': 'Direct-Physical', 'poss': 0.45, 'press': 0.58, 'dir': 0.76, 'vol': 0.08},
#     'tunisia': {'type': 'Compact Block', 'poss': 0.39, 'press': 0.48, 'dir': 0.71, 'vol': 0.09},
#     'cameroon': {'type': 'Direct-Physical', 'poss': 0.45, 'press': 0.60, 'dir': 0.75, 'vol': 0.17},
#     'dr congo': {'type': 'Direct-Physical', 'poss': 0.42, 'press': 0.52, 'dir': 0.74, 'vol': 0.16},
#     'greece': {'type': 'Compact Block', 'poss': 0.38, 'press': 0.40, 'dir': 0.72, 'vol': 0.06},
#     'slovakia': {'type': 'Compact Block', 'poss': 0.42, 'press': 0.50, 'dir': 0.70, 'vol': 0.08},
#     'venezuela': {'type': 'Compact Block', 'poss': 0.39, 'press': 0.55, 'dir': 0.78, 'vol': 0.12},
#     'uzbekistan': {'type': 'Compact Block', 'poss': 0.38, 'press': 0.44, 'dir': 0.78, 'vol': 0.15},
#     'costa rica': {'type': 'Compact Block', 'poss': 0.35, 'press': 0.48, 'dir': 0.76, 'vol': 0.11},
#     'mali': {'type': 'Direct-Physical', 'poss': 0.46, 'press': 0.62, 'dir': 0.70, 'vol': 0.16},
#     'peru': {'type': 'Vertical Control', 'poss': 0.55, 'press': 0.60, 'dir': 0.60, 'vol': 0.14},
#     'chile': {'type': 'Chaos & Intensity', 'poss': 0.52, 'press': 0.85, 'dir': 0.72, 'vol': 0.15},
#     'qatar': {'type': 'Compact Block', 'poss': 0.42, 'press': 0.31, 'dir': 0.68, 'vol': 0.14},
#     'romania': {'type': 'Compact Block', 'poss': 0.41, 'press': 0.48, 'dir': 0.74, 'vol': 0.10},
#     'iraq': {'type': 'Compact Block', 'poss': 0.31, 'press': 0.38, 'dir': 0.82, 'vol': 0.17},
#     'slovenia': {'type': 'Compact Block', 'poss': 0.39, 'press': 0.45, 'dir': 0.78, 'vol': 0.08},
#     'ireland': {'type': 'Direct-Physical', 'poss': 0.43, 'press': 0.52, 'dir': 0.76, 'vol': 0.09},
#     'south africa': {'type': 'Direct-Physical', 'poss': 0.44, 'press': 0.48, 'dir': 0.72, 'vol': 0.15},
#     'saudi arabia': {'type': 'Vertical Control', 'poss': 0.58, 'press': 0.52, 'dir': 0.54, 'vol': 0.14},
#     'burkina faso': {'type': 'Chaos & Intensity', 'poss': 0.48, 'press': 0.70, 'dir': 0.75, 'vol': 0.18},
#     'jordan': {'type': 'Compact Block', 'poss': 0.33, 'press': 0.31, 'dir': 0.84, 'vol': 0.19},
#     'albania': {'type': 'Compact Block', 'poss': 0.36, 'press': 0.42, 'dir': 0.80, 'vol': 0.10},
#     'bosnia and herzegovina': {'type': 'Compact Block', 'poss': 0.38, 'press': 0.35, 'dir': 0.80, 'vol': 0.14},
#     'honduras': {'type': 'Direct-Physical', 'poss': 0.40, 'press': 0.55, 'dir': 0.74, 'vol': 0.13},
#     'north macedonia': {'type': 'Compact Block', 'poss': 0.37, 'press': 0.44, 'dir': 0.79, 'vol': 0.12},
#     'uae': {'type': 'Vertical Control', 'poss': 0.54, 'press': 0.48, 'dir': 0.58, 'vol': 0.14},
#     'cape verde': {'type': 'Compact Block', 'poss': 0.34, 'press': 0.41, 'dir': 0.76, 'vol': 0.18},
#     'northern ireland': {'type': 'Compact Block', 'poss': 0.32, 'press': 0.50, 'dir': 0.82, 'vol': 0.07},
#     'jamaica': {'type': 'Direct-Physical', 'poss': 0.41, 'press': 0.64, 'dir': 0.78, 'vol': 0.17},
#     'georgia': {'type': 'Compact Block', 'poss': 0.35, 'press': 0.40, 'dir': 0.86, 'vol': 0.15},
#     'finland': {'type': 'Vertical Control', 'poss': 0.51, 'press': 0.45, 'dir': 0.64, 'vol': 0.09},
#     'ghana': {'type': 'Chaos & Intensity', 'poss': 0.48, 'press': 0.68, 'dir': 0.78, 'vol': 0.19},
#     'iceland': {'type': 'Compact Block', 'poss': 0.33, 'press': 0.45, 'dir': 0.85, 'vol': 0.08},
#     'bolivia': {'type': 'Compact Block', 'poss': 0.34, 'press': 0.38, 'dir': 0.79, 'vol': 0.12},
#     'israel': {'type': 'Vertical Control', 'poss': 0.53, 'press': 0.52, 'dir': 0.58, 'vol': 0.13},
#     'kosovo': {'type': 'Chaos & Intensity', 'poss': 0.47, 'press': 0.65, 'dir': 0.74, 'vol': 0.16},
#     'oman': {'type': 'Compact Block', 'poss': 0.41, 'press': 0.35, 'dir': 0.72, 'vol': 0.12},
#     'guinea': {'type': 'Direct-Physical', 'poss': 0.43, 'press': 0.55, 'dir': 0.74, 'vol': 0.15},
#     'montenegro': {'type': 'Compact Block', 'poss': 0.38, 'press': 0.42, 'dir': 0.78, 'vol': 0.10},
#     'curaçao': {'type': 'Compact Block', 'poss': 0.32, 'press': 0.28, 'dir': 0.85, 'vol': 0.19},
#     'haiti': {'type': 'Direct-Physical', 'poss': 0.35, 'press': 0.45, 'dir': 0.78, 'vol': 0.20},
#     'syria': {'type': 'Compact Block', 'poss': 0.34, 'press': 0.32, 'dir': 0.80, 'vol': 0.13},
#     'new zealand': {'type': 'Direct-Physical', 'poss': 0.40, 'press': 0.55, 'dir': 0.81, 'vol': 0.11},
#     'bulgaria': {'type': 'Compact Block', 'poss': 0.41, 'press': 0.38, 'dir': 0.70, 'vol': 0.14},
#     'gabon': {'type': 'Chaos & Intensity', 'poss': 0.46, 'press': 0.62, 'dir': 0.79, 'vol': 0.18},
#     'uganda': {'type': 'Compact Block', 'poss': 0.35, 'press': 0.40, 'dir': 0.76, 'vol': 0.15},
#     'angola': {'type': 'Compact Block', 'poss': 0.39, 'press': 0.42, 'dir': 0.74, 'vol': 0.14},
#     'benin': {'type': 'Compact Block', 'poss': 0.37, 'press': 0.35, 'dir': 0.78, 'vol': 0.14},
#     'bahrain': {'type': 'Compact Block', 'poss': 0.42, 'press': 0.32, 'dir': 0.70, 'vol': 0.13},
#     'zambia': {'type': 'Chaos & Intensity', 'poss': 0.45, 'press': 0.65, 'dir': 0.76, 'vol': 0.19},
#     'thailand': {'type': 'Vertical Control', 'poss': 0.52, 'press': 0.55, 'dir': 0.68, 'vol': 0.13},
#     'el salvador': {'type': 'Compact Block', 'poss': 0.38, 'press': 0.45, 'dir': 0.74, 'vol': 0.14},
#     'luxembourg': {'type': 'Compact Block', 'poss': 0.42, 'press': 0.40, 'dir': 0.68, 'vol': 0.09},
#     'armenia': {'type': 'Compact Block', 'poss': 0.36, 'press': 0.38, 'dir': 0.79, 'vol': 0.14},
#     'palestine': {'type': 'Compact Block', 'poss': 0.31, 'press': 0.35, 'dir': 0.82, 'vol': 0.18},
#     'equatorial guinea': {'type': 'Compact Block', 'poss': 0.38, 'press': 0.48, 'dir': 0.72, 'vol': 0.16},
#     'vietnam': {'type': 'Compact Block', 'poss': 0.38, 'press': 0.45, 'dir': 0.79, 'vol': 0.15},
#     'kazakhstan': {'type': 'Compact Block', 'poss': 0.33, 'press': 0.42, 'dir': 0.84, 'vol': 0.16}
# }

# =============================================================================
# --- TACTICAL MATCHUP MATRIX (The Rock-Paper-Scissors of Football) ---
# =============================================================================
# Format: ('Team 1 Style', 'Team 2 Style'): Attacking Multiplier for Team 1
# > 1.0 means Team 1 has a tactical advantage and generates more expected goals.
# < 1.0 means Team 1 is tactically countered and generates fewer expected goals.

# STYLE_MATCHUPS = {
#     # High Press disrupts teams that try to build from the back
#     ('High Press', 'Ball Control'): 1.08,
#     ('Ball Control', 'High Press'): 0.95,
    
#     # Direct Play bypasses the High Press completely
#     ('Direct Play', 'High Press'): 1.08,
#     ('High Press', 'Direct Play'): 0.92,
    
#     # Fast Build-up beats the press by moving the ball before the trap closes
#     ('Fast Build-up', 'High Press'): 1.06,
#     ('High Press', 'Fast Build-up'): 0.94,

#     # Counter-Attack exploits high lines and possession teams
#     ('Counter-Attack', 'Ball Control'): 1.08,
#     ('Ball Control', 'Counter-Attack'): 0.96,
#     ('Counter-Attack', 'High Risk'): 1.10,
#     ('High Risk', 'Counter-Attack'): 0.90,
    
#     # Deep Block starves Counter-Attack and Fast Build-up of running space
#     ('Deep Block', 'Counter-Attack'): 1.05,
#     ('Counter-Attack', 'Deep Block'): 0.85,
#     ('Deep Block', 'Fast Build-up'): 1.05,
#     ('Fast Build-up', 'Deep Block'): 0.90,

#     # Technical Play (Individual Brilliance) unlocks the Deep Block
#     ('Technical Play', 'Deep Block'): 1.10,
#     ('Deep Block', 'Technical Play'): 0.90,
    
#     # Disciplined structure neutralizes Technical flair and High Risk chaos
#     ('Disciplined', 'Technical Play'): 1.08,
#     ('Technical Play', 'Disciplined'): 0.92,
#     ('Disciplined', 'High Risk'): 1.08,
#     ('High Risk', 'Disciplined'): 0.92,

#     # Ball Control starves Direct Play and grinds down Deep Blocks over 90 mins
#     ('Ball Control', 'Direct Play'): 1.08,
#     ('Direct Play', 'Ball Control'): 0.94,
#     ('Ball Control', 'Deep Block'): 1.05,
#     ('Deep Block', 'Ball Control'): 0.95
# }

# Map teams to Confederations
# UEFA (Europe), CONMEBOL (S. America), CONCACAF (N. America), CAF (Africa), AFC (Asia), OFC (Oceania)
TEAM_CONFEDS = {
    # UEFA
    'france': 'UEFA', 'germany': 'UEFA', 'england': 'UEFA', 'spain': 'UEFA', 
    'belgium': 'UEFA', 'netherlands': 'UEFA', 'portugal': 'UEFA', 'croatia': 'UEFA',
    'italy': 'UEFA', 'denmark': 'UEFA', 'switzerland': 'UEFA', 'serbia': 'UEFA',
    'poland': 'UEFA', 'sweden': 'UEFA', 'wales': 'UEFA', 'ukraine': 'UEFA',
    'scotland': 'UEFA', 'austria': 'UEFA', 'turkey': 'UEFA', 'norway': 'UEFA',
    'romania': 'UEFA', 'czech republic': 'UEFA', 'hungary': 'UEFA', 'greece': 'UEFA',
    'slovakia': 'UEFA', 'republic of ireland': 'UEFA', 'northern ireland': 'UEFA',
    'bosnia and herzegovina': 'UEFA', 'iceland': 'UEFA', 'north macedonia': 'UEFA',
    'albania': 'UEFA', 'slovenia': 'UEFA', 'montenegro': 'UEFA', 'kosovo': 'UEFA',
    'georgia': 'UEFA', 'bulgaria': 'UEFA', 'finland': 'UEFA', 'luxembourg': 'UEFA',
    'russia': 'UEFA', 'belarus': 'UEFA', 'israel': 'UEFA',

    # CONMEBOL
    'brazil': 'CONMEBOL', 'argentina': 'CONMEBOL', 'uruguay': 'CONMEBOL', 
    'colombia': 'CONMEBOL', 'ecuador': 'CONMEBOL', 'chile': 'CONMEBOL', 
    'peru': 'CONMEBOL', 'paraguay': 'CONMEBOL', 'venezuela': 'CONMEBOL', 'bolivia': 'CONMEBOL',

    # CONCACAF
    'united states': 'CONCACAF', 'mexico': 'CONCACAF', 'canada': 'CONCACAF', 
    'costa rica': 'CONCACAF', 'panama': 'CONCACAF', 'jamaica': 'CONCACAF',
    'honduras': 'CONCACAF', 'el salvador': 'CONCACAF', 'haiti': 'CONCACAF',
    'curaçao': 'CONCACAF', 'trinidad & tobago': 'CONCACAF', 'guatemala': 'CONCACAF',

    # CAF
    'morocco': 'CAF', 'senegal': 'CAF', 'tunisia': 'CAF', 'nigeria': 'CAF', 
    'algeria': 'CAF', 'egypt': 'CAF', 'cameroon': 'CAF', 'ghana': 'CAF', 
    'mali': 'CAF', 'ivory coast': 'CAF', 'burkina faso': 'CAF', 'south africa': 'CAF',
    'dr congo': 'CAF', 'cabo verde': 'CAF', 'guinea': 'CAF', 'zambia': 'CAF',

    # AFC
    'japan': 'AFC', 'iran': 'AFC', 'south korea': 'AFC', 'australia': 'AFC', 
    'saudi arabia': 'AFC', 'qatar': 'AFC', 'iraq': 'AFC', 'uae': 'AFC', 
    'oman': 'AFC', 'uzbekistan': 'AFC', 'china': 'AFC', 'jordan': 'AFC', 
    'bahrain': 'AFC', 'syria': 'AFC', 'vietnam': 'AFC', 'thailand': 'AFC',

    # OFC
    'new zealand': 'OFC', 'new caledonia': 'OFC', 'fiji': 'OFC', 'solomon islands': 'OFC'
}

# Where we will store the calculated multipliers
CONFED_MULTIPLIERS = {}

# Finalized 2026 World Cup Playoff Results (As of April 1, 2026)
FINALIZED_SLOTS = {
    'Path A': 'bosnia and herzegovina',  # Winner of Italy/Northern Ireland vs Wales
    'Path B': 'sweden',                  # Winner of Ukraine vs Poland/Albania
    'Path C': 'turkey',                  # Winner of Turkey vs Slovakia/Kosovo
    'Path D': 'czech republic',          # Winner of Czech Republic/Republic of Ireland vs Denmark/North Macedonia
    'ICP1': 'dr congo',                  # Winner of Jamaica vs OFC winner
    'ICP2': 'iraq'                       # Winner of Iraq vs CONMEBOL playoffs
}

def _read_csv_safe(path):
    normalized = str(path).lstrip('./')
    basename = normalized.split('/')[-1]

    local_paths = [path, normalized, f"./{normalized}", f"/{normalized}"]
    if basename != normalized:
        local_paths += [basename, f"./{basename}", f"/{basename}"]

    if normalized.startswith('http://') or normalized.startswith('https://'):
        local_paths = [normalized]

    for candidate in local_paths:
        try:
            return pd.read_csv(open_url(candidate))
        except Exception:
            continue

    fallback_urls = []
    if normalized.startswith('http://') or normalized.startswith('https://'):
        fallback_urls.append(normalized)
    else:
        fallback_urls.append(f"{GITHUB_RAW_BASE}/{normalized}")
        if not normalized.startswith('data/'):
            fallback_urls.append(f"{GITHUB_RAW_BASE}/data/{normalized}")
        if basename != normalized:
            fallback_urls.append(f"{GITHUB_RAW_BASE}/{basename}")

    for fallback in fallback_urls:
        try:
            return pd.read_csv(open_url(fallback))
        except Exception:
            continue

    try:
        return pd.read_csv(path)
    except Exception as e:
        js.console.error(f"Failed to read {path}: {e}")
        return None


def load_data():
    try:
        former_names_df = _read_csv_safe(f"{DATA_DIR}/former_names.csv")
        results_df = _read_csv_safe(f"{DATA_DIR}/results.csv")
        goalscorers_df = _read_csv_safe(f"{DATA_DIR}/goalscorers.csv")
        player_df = _read_csv_safe(f"{DATA_DIR}/FM 26 Player Data.csv")
        formation_df = _read_csv_safe(f"{DATA_DIR}/FM 26 Player Data - Formations.csv")
        return results_df, goalscorers_df, former_names_df, player_df, formation_df
    except Exception as e:
        js.console.error(f"CRITICAL ERROR LOADING DATA: {e}")
        return None, None, None, None, None

# =============================================================================
# --- PART 2: INITIALIZATION (OPTIMIZED) ---
# =============================================================================
def get_match_importance(tourney, match_date):
    t_str = str(tourney).lower()
    
    # 1. World Cup Finals (The absolute gold standard of data)
    if 'world cup' in t_str and 'qualification' not in t_str:
        return 1.2
    # 2. Continental Majors (Euros, Copa America)
    elif any(x in t_str for x in ['copa américa', 'euro', 'african cup', 'asian cup', 'gold cup']) and 'qualification' not in t_str:
        return 1.1
    # 3. Qualifiers & Nations League (Highly competitive)
    elif 'qualification' in t_str or 'nations league' in t_str:
        return 1.0
    # 4. Friendlies
    elif 'friendly' in t_str:
        # Pre-Tournament Friendlies (Usually played in May/June, or Nov for Qatar 2022)
        if match_date.month in [5, 6] or (match_date.year == 2022 and match_date.month == 11):
            return 0.7  # Teams play their starters, good data
        else:
            return 0.3  # Standard friendly, heavy rotation, mostly noise
    # 5. Minor Tournaments
    else:
        return 0.6

def get_k_factor(tourney, goal_diff, home_team, away_team):
    t_str = str(tourney)

    # --- CONFEDERATION LOOKUP
    tier_map = { 'UEFA': 1.0, 'CONMEBOL': 1.0, 'CAF': 0.9, 'AFC': 0.8, 'CONCACAF': 0.8, 'OFC': 0.7 }
    
    h_conf = TEAM_CONFEDS.get(home_team, 'OFC') 
    a_conf = TEAM_CONFEDS.get(away_team, 'OFC')
    
    if h_conf == a_conf:
        region_weight = tier_map.get(h_conf, 0.75)
    else:
        region_weight = (tier_map.get(h_conf, 0.75) + tier_map.get(a_conf, 0.75)) / 2.0

    # =========================================================
    # TIER -1: NON-FIFA / INDEPENDENT (The "Noise" Filter)
    # =========================================================
    # These tournaments are for non-FIFA members (e.g. Tibet, Kurdistan).
    # We set K extremely low to prevent them from affecting global FIFA rankings.
    if any(x in t_str for x in ['CONIFA', 'VIVA', 'Island Games', 'Wild Cup', 'ELF Cup', 'FIFI', 'Inter Games', 'Coupe de l\'Outre-Mer', 'Unity Cup']):
        return 5 

    # =========================================================
    # TIER 0: FRIENDLIES & MINOR INVITATIONALS
    # =========================================================
    # Catch specific friendly tournament names from your list
    if any(x in t_str for x in ['Friendly', 'FIFA Series', 'Kirin', 'King\'s Cup', 'Merdeka', 'Nehru', 'China Cup', 'Bangabandhu', 'Four Nations', 'Mundialito', 'Lunar New Year', 'Tournoi de France']):
        k = 15

    # =========================================================
    # TIER 1: WORLD CUP FINALS
    # =========================================================
    elif 'World Cup' in t_str and 'qualification' not in t_str:
        k = 65
    
    # =========================================================
    # TIER 2: CONTINENTAL MAJORS (FINALS)
    # =========================================================
    elif any(x in t_str for x in ['Copa América', 'UEFA Euro', 'African Cup of Nations', 'Asian Cup', 'Gold Cup', 'CONCACAF Championship', 'Oceania Nations Cup', 'CONMEBOL–UEFA Cup of Champions']) and 'qualification' not in t_str:
        k = 50
    # =========================================================
    # TIER 3: QUALIFIERS & MAJOR OFFICIAL (Weighted by Region)
    # =========================================================
    elif any(x in t_str for x in ['qualification', 'Nations League', 'Confederations Cup', 'Arab Cup', 'Gulf Cup']):
        # "qualification" catches: World Cup, Euro, Asian Cup, Gold Cup, etc.
        # "Nations League" catches: UEFA NL, CONCACAF NL
        k = 40 * region_weight
    # =========================================================
    # TIER 4: SUB-REGIONAL & OLYMPICS (Weighted by Region)
    # =========================================================
    # This tier is massive in your dataset. These are official but smaller than Continental Cups.
    elif any(x in t_str for x in ['AFF', 'ASEAN', 'EAFF', 'CAFA', 'WAFF', 'SAFF', 'CECAFA', 'COSAFA', 'WAFU', 'CEMAC', 'UNCAF', 'CFU', 'Caribbean Cup', 'Baltic Cup', 'Nordic', 'British Home', 'Pacific Games', 'Melanesian', 'Polynesian', 'Olympic Games', 'Asian Games', 'Pan American']):
        k = 25 * region_weight
    # =========================================================
    # DEFAULT CATCH-ALL
    # =========================================================
    else:
        k = 20

    if goal_diff <= 1:
        gd_factor = 1.0
    elif goal_diff == 2:
        gd_factor = 1.5
    else:
        gd_factor = (11.0 + goal_diff) / 8.0
        
    return k * gd_factor

def _parse_value(value):
    if pd.isna(value):
        return 0.0
    text = str(value).replace('€', '').replace(',', '').strip()
    if text == '-' or text == '':
        return 0.0
    try:
        if '-' in text:
            parts = [p.strip() for p in text.split('-') if p.strip()]
            nums = []
            for part in parts:
                multiplier = 1.0
                if part.endswith('M'):
                    multiplier = 1_000_000
                    part = part[:-1]
                elif part.endswith('K'):
                    multiplier = 1_000
                    part = part[:-1]
                part = part.strip()
                nums.append(float(part) * multiplier)
            return sum(nums) / len(nums) / 1_000_000.0
        multiplier = 1.0
        if text.endswith('M'):
            multiplier = 1_000_000
            text = text[:-1]
        elif text.endswith('K'):
            multiplier = 1_000
            text = text[:-1]
        return float(text) * multiplier / 1_000_000.0
    except Exception:
        return 0.0


def _safe_int(value, fallback=np.nan):
    try:
        return int(float(value))
    except Exception:
        return fallback


def _normalize_status(value):
    if pd.isna(value):
        return 'Unknown'
    text = str(value).strip().lower()
    if 'yes' in text:
        return 'Yes'
    if 'likely' in text:
        return 'Likely'
    if 'tbd' in text or 'unknown' in text:
        return 'TBD'
    if 'no' in text:
        return 'No'
    return value.title()


def _player_groups(position):
    pos = str(position).upper()
    groups = set()
    if 'GK' in pos:
        groups.add('GK')
    if any(token in pos for token in ['DL', 'DR', 'DC', 'LB', 'RB', 'WB', 'WBL', 'WBR', 'SW']):
        groups.add('D')
    if any(token in pos for token in ['DM', 'MC', 'CM', 'AMC', 'LM', 'RM', 'ML', 'MR']):
        groups.add('M')
    if any(token in pos for token in ['ST', 'CF', 'LW', 'RW', 'SS', 'FW', 'AMR', 'AML']):
        groups.add('F')
    if not groups:
        groups.add('M')
    return groups


def _estimate_club_influence(club_name):
    if not isinstance(club_name, str):
        return 0.0
    club = club_name.lower()
    elite = ['real madrid', 'barcelona', 'manchester city', 'man city', 'manchester united', 'bayern', 'psg', 'liverpool', 'juventus', 'atletico', 'inter', 'ac milan', 'chelsea', 'arsenal', 'ajax', 'porto', 'benfica']
    strong = ['roma', 'napoli', 'leipzig', 'sevilla', 'marseille', 'lyon', 'celtic', 'rangers', 'lazio', 'fiorentina', 'monaco', 'dortmund']

    if any(name in club for name in elite):
        return 1.6
    if any(name in club for name in strong):
        return 1.1
    if club.strip() == '':
        return 0.0
    return 0.5


def _estimate_potential(row):
    current = row.get('Rat', 0)
    pot = row.get('Pot', np.nan)
    age = row.get('Age', 22)
    sell_m = row.get('Sell_Millions', 0.0)
    status = row.get('WC_Status', 'Unknown')
    club = row.get('Club', '')
    if not np.isnan(pot) and pot > 0:
        return max(current, pot)
    if age >= 27 or current <= 0:
        return current

    if age <= 19:
        age_bonus = 6 + (19 - age) * 1.4
    elif age <= 22:
        age_bonus = 2 + (22 - age) * 0.9
    else:
        age_bonus = max(0.0, 1.5 - (age - 22) * 0.6)

    value_bonus = np.log10(max(sell_m, 1.0)) * 2.3
    club_bonus = _estimate_club_influence(club) * 1.8
    status_bonus = 0.0
    if status in ['Yes', 'Likely'] and age <= 23:
        status_bonus = 4.0
    elif status == 'Likely':
        status_bonus = 1.5

    estimate = current + age_bonus + value_bonus + club_bonus + status_bonus
    estimate = max(current + 3, min(current + 18, estimate))
    return max(current, round(estimate))


def _select_team_players(squad_df, explicit_keys=None, explicit_watchlist=None):
    explicit_keys = [p for p in (explicit_keys or []) if p]
    explicit_watchlist = [p for p in (explicit_watchlist or []) if p]
    if squad_df is None or squad_df.empty:
        return explicit_keys, explicit_watchlist

    selected_keys = []
    if explicit_keys:
        selected_keys.extend(explicit_keys)

    group_targets = [('GK', 1), ('D', 2), ('M', 2), ('F', 2)]
    for group_name, count in group_targets:
        if len(selected_keys) >= 6:
            break
        group_players = squad_df[squad_df['Position_Groups'].apply(lambda g: group_name in g)]
        for _, row in group_players.sort_values(['Rat', 'Pot', 'Emerging_Score'], ascending=[False, False, False]).iterrows():
            name = row['Name']
            if name not in selected_keys:
                selected_keys.append(name)
                if len(selected_keys) >= 6:
                    break

    if len(selected_keys) < 6:
        for _, row in squad_df.sort_values(['Rat', 'Pot', 'Emerging_Score'], ascending=[False, False, False]).iterrows():
            name = row['Name']
            if name not in selected_keys:
                selected_keys.append(name)
                if len(selected_keys) >= 6:
                    break

    # Watchlist: emerging young talent, prioritizing those who are not already key players.
    watchlist = []
    if explicit_watchlist:
        watchlist.extend(explicit_watchlist)

    if len(watchlist) < 4:
        young_prospects = squad_df[(squad_df['Age'] <= 23) & (squad_df['Emerging_Score'] > 0)].copy()
        young_prospects = young_prospects.sort_values(['Emerging_Score', 'Pot', 'Rat'], ascending=[False, False, False])
        for _, row in young_prospects.iterrows():
            name = row['Name']
            if name not in watchlist and name not in selected_keys:
                watchlist.append(name)
                if len(watchlist) >= 4:
                    break

    if len(watchlist) < 2:
        fallback_young = squad_df[squad_df['Age'] <= 22].sort_values(['Pot', 'Rat'], ascending=[False, False])
        for _, row in fallback_young.iterrows():
            name = row['Name']
            if name not in watchlist and name not in selected_keys:
                watchlist.append(name)
                if len(watchlist) >= 2:
                    break

    return selected_keys[:6], watchlist[:4]


def _clean_player_dataframe(player_df, formation_df):
    global PLAYER_DF, FORMATION_DF, TEAM_ROSTERS, TEAM_FORMATIONS
    PLAYER_DF = None
    FORMATION_DF = None
    TEAM_ROSTERS = {}
    TEAM_FORMATIONS = {}

    if player_df is None:
        return

    player_df = player_df.copy()
    player_df.columns = [c.strip() for c in player_df.columns]
    player_df['Nation'] = player_df['Nation'].astype(str).str.lower().str.strip()
    player_df['Name'] = player_df['Name'].astype(str).str.strip()
    player_df['Rat'] = player_df['Rat'].apply(_safe_int)
    player_df['Pot'] = player_df['Pot'].apply(_safe_int)
    player_df['Age'] = player_df['Age'].apply(_safe_int)
    player_df['Sell_Millions'] = player_df['Sell Value'].apply(_parse_value)
    player_df['Wage_K'] = player_df['Wage (p/w)'].astype(str).str.replace('€','').str.replace('K','').str.replace(',','').replace('k','')
    player_df['Wage_K'] = player_df['Wage_K'].apply(lambda x: float(x) if str(x).strip().replace('.','',1).isdigit() else 0.0)
    player_df['WC_Status'] = player_df['WC 2026?'].apply(_normalize_status)
    player_df['Position_Groups'] = player_df['Position(s)'].apply(_player_groups)
    player_df['Pot'] = player_df.apply(_estimate_potential, axis=1)
    player_df['Rating_Score'] = player_df['Pot'] * 0.7 + player_df['Rat'] * 0.3
    player_df['Emerging_Score'] = player_df.apply(lambda r: ((r['Pot'] - r['Rat']) * max(0, 28 - r['Age']) * 0.15) if r['Age'] <= 23 else 0, axis=1)

    PLAYER_DF = player_df

    if formation_df is not None:
        formation_df = formation_df.copy()
        formation_df.columns = [c.strip() for c in formation_df.columns]
        formation_df['Nation'] = formation_df['Nation'].astype(str).str.lower().str.strip()
        formation_df['Formation 1'] = formation_df['Formation 1'].astype(str).str.strip()
        formation_df['Formation 2'] = formation_df['Formation 2'].astype(str).str.strip()
        formation_df['Key Guaranteed Players'] = formation_df['Key Guaranteed Players'].astype(str)
        formation_df['Key Likely Players'] = formation_df['Key Likely Players'].astype(str)
        formation_df['Notable Absences / Retirements'] = formation_df['Notable Absences / Retirements'].astype(str)
        FORMATION_DF = formation_df

    for nation in player_df['Nation'].unique():
        nation_players = player_df[player_df['Nation'] == nation].copy()
        form_row = None
        if FORMATION_DF is not None and nation in FORMATION_DF['Nation'].values:
            form_row = FORMATION_DF[FORMATION_DF['Nation'] == nation].iloc[0]
        preferred_formation = form_row['Formation 1'] if form_row is not None and form_row['Formation 1'] not in ['', 'nan'] else '4-3-3'
        squad = _build_squad(nation_players, preferred_formation)

        explicit_keys = []
        explicit_watchlist = []
        notable = ''
        if form_row is not None:
            explicit_keys = [p.strip() for p in str(form_row.get('Key Guaranteed Players', '')).split(',') if p.strip()]
            explicit_watchlist = [p.strip() for p in str(form_row.get('Key Likely Players', '')).split(',') if p.strip()]
            notable = str(form_row.get('Notable Absences / Retirements', '')).strip()

        key_players, watchlist = _select_team_players(squad, explicit_keys, explicit_watchlist)

        squad_rating = float(squad['Rat'].mean()) if not squad.empty else 0.0
        squad_potential = float(squad['Pot'].mean()) if not squad.empty else squad_rating
        depth_score = float(squad['Emerging_Score'].sum()) if not squad.empty else 0.0
        team_rating = round(squad_rating + 0.20 * max(0, squad_potential - squad_rating), 2)
        if team_rating < 60:
            team_rating = float(squad_rating)

        TEAM_FORMATIONS[nation] = {
            'preferred_formation': preferred_formation,
            'secondary_formation': form_row['Formation 2'] if form_row is not None and form_row['Formation 2'] not in ['', 'nan'] else None,
            'key_players': key_players,
            'watchlist': watchlist,
            'notable_absences': notable,
            'squad': squad[['Name','Rat','Pot','Age','Position(s)','Club','WC_Status']].to_dict('records'),
            'team_rating': team_rating,
            'squad_rating': round(squad_rating,2),
            'squad_potential': round(squad_potential,2),
            'depth_score': round(depth_score,2)
        }
        TEAM_ROSTERS[nation] = TEAM_FORMATIONS[nation]


def _build_squad(players, preferred_formation):
    if players.empty:
        return players

    formation_counts = {
        '4-3-3': {'GK': 3, 'D': 8, 'M': 8, 'F': 7},
        '4-2-3-1': {'GK': 3, 'D': 8, 'M': 9, 'F': 6},
        '4-4-2': {'GK': 3, 'D': 8, 'M': 8, 'F': 7},
        '4-1-4-1': {'GK': 3, 'D': 8, 'M': 9, 'F': 6},
        '3-4-2-1': {'GK': 3, 'D': 7, 'M': 9, 'F': 7},
        '3-5-2': {'GK': 3, 'D': 7, 'M': 10, 'F': 6},
        '5-3-2': {'GK': 3, 'D': 9, 'M': 8, 'F': 6}
    }
    counts = formation_counts.get(preferred_formation.lower(), formation_counts.get(preferred_formation, {'GK': 3, 'D': 8, 'M': 9, 'F': 6}))
    players = players.copy()
    players['selection_score'] = players['Rating_Score'] + players['Emerging_Score'] * 0.1
    players = players.sort_values(['selection_score', 'Pot', 'Rat'], ascending=[False, False, False])

    selected = []
    used = set()

    def pick_group(group_name, count):
        rows = players[players['Position_Groups'].apply(lambda g: group_name in g) & ~players.index.isin(used)]
        chosen = rows.head(count)
        for idx in chosen.index:
            used.add(idx)
        return chosen

    gk = pick_group('GK', counts['GK'])
    d = pick_group('D', counts['D'])
    m = pick_group('M', counts['M'])
    f = pick_group('F', counts['F'])
    selected_df = pd.concat([gk, d, m, f])

    if len(selected_df) < 26:
        remaining = players[~players.index.isin(used)].head(26 - len(selected_df))
        selected_df = pd.concat([selected_df, remaining])

    if len(selected_df) > 26:
        selected_df = selected_df.head(26)

    return selected_df


def initialize_engine():
    try:
        former_names_df = _read_csv_safe(f"{DATA_DIR}/former_names.csv")
        if former_names_df is not None:
            NAME_MAP = dict(zip(former_names_df['old_name'], former_names_df['new_name']))
        else:
            NAME_MAP = {}
    except Exception:
        NAME_MAP = {}

    results_df, scorers_df, _, player_df, formation_df = load_data()
    
    _clean_player_dataframe(player_df, formation_df)
    
    if results_df is None:
        return {}, {}, 2.5

    if 'date' not in results_df.columns:
        js.console.warn("Results data missing 'date' column; retrying alternate load paths.")
        results_df = _read_csv_safe('data/results.csv') or _read_csv_safe('results.csv')
        if results_df is None or 'date' not in results_df.columns:
            js.console.error("Failed to load results.csv with expected 'date' column.")
            return {}, {}, 2.5

    results_df['date'] = pd.to_datetime(results_df['date'], errors='coerce')
    results_df = results_df.dropna(subset=['date', 'home_score', 'away_score', 'neutral'])
    
    results_df['home_team'] = results_df['home_team'].str.lower().str.strip().replace(NAME_MAP)
    results_df['away_team'] = results_df['away_team'].str.lower().str.strip().replace(NAME_MAP)
    results_df = results_df.astype({'home_score': int, 'away_score': int})

    # HFA CALC
    non_neutral = results_df[results_df['neutral'] == False]
    h_wins = len(non_neutral[non_neutral['home_score'] > non_neutral['away_score']])
    total_non_neutral = len(non_neutral)
    
    if total_non_neutral > 0:
        h_win_prob = h_wins / total_non_neutral
        h_win_prob = max(0.01, min(0.99, h_win_prob))
        calculated_hfa = round(-400 * math.log10(1/h_win_prob - 1))
    else:
        calculated_hfa = 100 
    
    js.console.log(f"Data-Driven HFA: {calculated_hfa}")
    elo_df = results_df.sort_values('date')

    # PHASE 1
    team_elo = {}
    INITIAL_RATING = 1200
    RELEVANCE_CUTOFF = pd.to_datetime('2021-01-01') 
    
    global TEAM_HISTORY, TEAM_STATS
    TEAM_HISTORY = {} 
    TEAM_STATS = {}
    
    LATEST_DATE = elo_df['date'].max()
    all_teams_set = set(elo_df['home_team']).union(set(elo_df['away_team']))
    recent_residuals = {t: [] for t in all_teams_set}
    
    for t in all_teams_set:
        TEAM_STATS[t] = {
            'elo': INITIAL_RATING, 'notable_results': [],
            'rec_weaker': [0, 0, 0], 'rec_similar': [0, 0, 0], 'rec_stronger': [0, 0, 0], 'rec_elite': [0, 0, 0],
            'pedigree_pts': 0,
            'upsets_major_won': 0,  'upsets_minor_won': 0, 'upsets_major_lost': 0, 'upsets_minor_lost': 0,
            'matches': 0, 'clean_sheets': 0, 'btts': 0, 'gf_avg': 0, 'ga_avg': 0, 'off': 1.0, 'def': 1.0,
            'penalties': 0, 'first_half': 0, 'late_goals': 0, 'total_goals_recorded': 0, 'form': []
        }
        if t in TEAM_ROSTERS:
            TEAM_STATS[t].update({
                'preferred_formation': TEAM_ROSTERS[t].get('preferred_formation'),
                'secondary_formation': TEAM_ROSTERS[t].get('secondary_formation'),
                'key_players': TEAM_ROSTERS[t].get('key_players', []),
                'watchlist': TEAM_ROSTERS[t].get('watchlist', []),
                'notable_absences': TEAM_ROSTERS[t].get('notable_absences', ''),
                'team_rating': TEAM_ROSTERS[t].get('team_rating', 85.0),
                'squad_rating': TEAM_ROSTERS[t].get('squad_rating', 0.0),
                'squad_potential': TEAM_ROSTERS[t].get('squad_potential', 0.0),
                'depth_score': TEAM_ROSTERS[t].get('depth_score', 0.0),
                'squad': TEAM_ROSTERS[t].get('squad', [])
            })

    matches_data = zip(elo_df['home_team'], elo_df['away_team'], elo_df['home_score'], elo_df['away_score'], elo_df['tournament'], elo_df['neutral'], elo_df['date'])

    for h, a, hs, as_, tourney, neutral, date in matches_data:
        rh = team_elo.get(h, INITIAL_RATING)
        ra = team_elo.get(a, INITIAL_RATING)

        if hs > as_:   res_h, res_a = 0, 2
        elif hs == as_: res_h, res_a = 1, 1
        else:          res_h, res_a = 2, 0
        
        # --- 1. ALL-TIME PEDIGREE TRACKING ---
        t_str = str(tourney).lower()
        is_wc_finals = 'world cup' in t_str and 'qualification' not in t_str
        is_continental_finals = any(x in t_str for x in ['copa américa', 'euro', 'african cup', 'asian cup', 'gold cup']) and 'qualification' not in t_str

        if is_wc_finals or is_continental_finals:
            ped_val = 1.0 if is_wc_finals else 0.35
            TEAM_STATS[h]['pedigree_pts'] = TEAM_STATS[h].get('pedigree_pts', 0) + ped_val
            TEAM_STATS[a]['pedigree_pts'] = TEAM_STATS[a].get('pedigree_pts', 0) + ped_val

        # --- 2. ALL-TIME ELO RECORD TRACKING ---
        # "Elite" means opponent is 1800+ Elo. "Stronger" means opponent is +75 Elo higher.
        diff_h = ra - rh 
        if ra >= 1800: TEAM_STATS[h]['rec_elite'][res_h] += 1
        elif diff_h > 75: TEAM_STATS[h]['rec_stronger'][res_h] += 1
        elif diff_h < -75: TEAM_STATS[h]['rec_weaker'][res_h] += 1
        else: TEAM_STATS[h]['rec_similar'][res_h] += 1

        diff_a = rh - ra 
        if rh >= 1800: TEAM_STATS[a]['rec_elite'][res_a] += 1
        elif diff_a > 75: TEAM_STATS[a]['rec_stronger'][res_a] += 1
        elif diff_a < -75: TEAM_STATS[a]['rec_weaker'][res_a] += 1
        else: TEAM_STATS[a]['rec_similar'][res_a] += 1

        # --- 3. RECENT TRACKING (Last 4 Years) ---
        if date > RELEVANCE_CUTOFF:
            # Recent Knockout Experience Decay
            if is_wc_finals or is_continental_finals:
                w = calculate_recency_weight(date, LATEST_DATE) 
                TEAM_STATS[h]['ko_exp_weighted'] = TEAM_STATS[h].get('ko_exp_weighted', 0) + w
                TEAM_STATS[a]['ko_exp_weighted'] = TEAM_STATS[a].get('ko_exp_weighted', 0) + w

            def record_upset(team, opp, score_str, elo_diff, type_code, match_date):
                TEAM_STATS[team]['notable_results'].append({
                    'opp': opp, 'score': score_str, 'diff': abs(int(elo_diff)), 'date': match_date, 'type': type_code
                })
            
            # Record Giant Killings
            score_h = f"{hs}-{as_}"
            if res_h == 0: 
                if diff_h > 300:   
                    TEAM_STATS[h]['upsets_major_won'] += 1
                    record_upset(h, a, score_h, diff_h, "WON_MAJOR", date)
                elif diff_h > 150: 
                    TEAM_STATS[h]['upsets_minor_won'] += 1
                    record_upset(h, a, score_h, diff_h, "WON_MINOR", date)
            if res_h == 2: 
                if diff_h < -300:   
                    TEAM_STATS[h]['upsets_major_lost'] += 1
                    record_upset(h, a, score_h, diff_h, "LOST_MAJOR", date)
                elif diff_h < -150: TEAM_STATS[h]['upsets_minor_lost'] += 1
            
            score_a = f"{as_}-{hs}"
            if res_a == 0: 
                if diff_a > 300:   
                    TEAM_STATS[a]['upsets_major_won'] += 1
                    record_upset(a, h, score_a, diff_a, "WON_MAJOR", date)
                elif diff_a > 150: 
                    TEAM_STATS[a]['upsets_minor_won'] += 1
                    record_upset(a, h, score_a, diff_a, "WON_MINOR", date)
            if res_a == 2: 
                if diff_a < -300:   
                    TEAM_STATS[a]['upsets_major_lost'] += 1
                    record_upset(a, h, score_a, diff_a, "LOST_MAJOR", date)
                elif diff_a < -150: TEAM_STATS[a]['upsets_minor_lost'] += 1
        
        if h not in TEAM_HISTORY: TEAM_HISTORY[h] = {'dates': [], 'elo': []}
        if a not in TEAM_HISTORY: TEAM_HISTORY[a] = {'dates': [], 'elo': []}
        
        dr = rh - ra + (calculated_hfa if not neutral else 0)
        we_h = 1 / (10**(-dr/400) + 1)
        W_h = 1.0 if hs > as_ else (0.5 if hs == as_ else 0.0)
        
        k = get_k_factor(tourney, abs(hs - as_), h, a)
        change = k * (W_h - we_h)

        if date > RELEVANCE_CUTOFF:
            weight = calculate_recency_weight(date, LATEST_DATE) * get_match_importance(tourney, date)
            res_h_vol = (W_h - we_h)**2
            recent_residuals[h].append((weight, res_h_vol))
            res_a_vol = ((1.0 - W_h) - (1.0 - we_h))**2
            recent_residuals[a].append((weight, res_a_vol))
        
        team_elo[h] = rh + change
        team_elo[a] = ra - change
        
        TEAM_HISTORY[h]['dates'].append(date); TEAM_HISTORY[h]['elo'].append(team_elo[h])
        TEAM_HISTORY[a]['dates'].append(date); TEAM_HISTORY[a]['elo'].append(team_elo[a])

    for t in all_teams_set:
        TEAM_STATS[t]['elo'] = team_elo.get(t, INITIAL_RATING)

    # PHASE 2
    recent_df = elo_df[elo_df['date'] > RELEVANCE_CUTOFF]
    if len(recent_df) > 0:
        LATEST_DATE = recent_df['date'].max()
        avg_goals_global = (recent_df['home_score'].mean() + recent_df['away_score'].mean()) / 2
    else:
        LATEST_DATE = pd.to_datetime('today')
        avg_goals_global = 1.25
    
    team_recent_aggregates = {t: {'gf':0, 'ga':0, 'eff_games':0, 'opp_elo_sum':0} for t in all_teams_set}
    
    for _, row in recent_df.iterrows():
        h, a = row['home_team'], row['away_team']
        hs, as_ = row['home_score'], row['away_score']
        match_date = row['date']
        
        h_elo = TEAM_STATS.get(h, {}).get('elo', 1200)
        a_elo = TEAM_STATS.get(a, {}).get('elo', 1200)

        weight = calculate_recency_weight(match_date, LATEST_DATE) * get_match_importance(row['tournament'], match_date)

        if h in TEAM_STATS:
            TEAM_STATS[h]['matches'] += 1
            res = 'W' if hs > as_ else ('L' if hs < as_ else 'D')
            TEAM_STATS[h]['form'].append(res)
            
            agg = team_recent_aggregates[h]
            agg['gf'] += (hs * weight)
            agg['ga'] += (as_ * weight)
            agg['eff_games'] += weight       
            agg['opp_elo_sum'] += (a_elo * weight)
            
            if as_ == 0: TEAM_STATS[h]['clean_sheets'] += 1
            if hs > 0 and as_ > 0: TEAM_STATS[h]['btts'] += 1

        if a in TEAM_STATS: 
            TEAM_STATS[a]['matches'] += 1
            res = 'W' if as_ > hs else ('L' if as_ < hs else 'D')
            TEAM_STATS[a]['form'].append(res)

            agg = team_recent_aggregates[a]
            agg['gf'] += (as_ * weight)
            agg['ga'] += (hs * weight)
            agg['eff_games'] += weight
            agg['opp_elo_sum'] += (h_elo * weight)
            
            if hs == 0: TEAM_STATS[a]['clean_sheets'] += 1
            if hs > 0 and as_ > 0: TEAM_STATS[a]['btts'] += 1

    # PHASE 3
    if scorers_df is not None:
        scorers_df['team'] = scorers_df['team'].str.lower().str.strip().replace(NAME_MAP)
        scorers_df['date'] = pd.to_datetime(scorers_df['date'])
        modern_scorers = scorers_df[scorers_df['date'] > RELEVANCE_CUTOFF]
        
        for _, row in modern_scorers.iterrows():
            t = row['team']
            if t in TEAM_STATS:
                weight = calculate_recency_weight(row['date'], LATEST_DATE)
                TEAM_STATS[t]['total_goals_recorded'] += weight
                if row['penalty']: TEAM_STATS[t]['penalties'] += weight
                try:
                    minute = float(str(row['minute']).split('+')[0])
                    if minute <= 45: TEAM_STATS[t]['first_half'] += weight
                    if minute >= 75: TEAM_STATS[t]['late_goals'] += weight
                except: pass

    active_elos = [s['elo'] for s in TEAM_STATS.values()]
    GLOBAL_ELO_MEAN = sum(active_elos) / len(active_elos) if active_elos else 1500

    # PHASE 4
    global TEAM_PROFILES
    TEAM_PROFILES = {}
    REGRESSION_DUMMY_GAMES = 6
    
    for t, s in TEAM_STATS.items():
        agg = team_recent_aggregates[t]
        
        denom = agg['eff_games'] + REGRESSION_DUMMY_GAMES
        numerator_gf = agg['gf'] + (REGRESSION_DUMMY_GAMES * avg_goals_global)
        numerator_ga = agg['ga'] + (REGRESSION_DUMMY_GAMES * avg_goals_global)
        
        raw_gf_avg = numerator_gf / denom
        raw_ga_avg = numerator_ga / denom
        s['gf_avg'] = raw_gf_avg
        s['ga_avg'] = raw_ga_avg 
        
        if agg['eff_games'] > 0: avg_opp_elo = agg['opp_elo_sum'] / agg['eff_games']
        else: avg_opp_elo = GLOBAL_ELO_MEAN
            
        weighted_opp_elo = (avg_opp_elo * agg['eff_games'] + GLOBAL_ELO_MEAN * REGRESSION_DUMMY_GAMES) / denom
        difficulty_ratio = weighted_opp_elo / GLOBAL_ELO_MEAN
        
        off_log = np.log(raw_gf_avg / avg_goals_global)
        sos_weight_off = np.clip(difficulty_ratio, 0.85, 1.15)
        adjusted_off = np.exp(off_log * sos_weight_off)

        sos_weight_def = difficulty_ratio ** 1.1 
        adjusted_def = (raw_ga_avg / avg_goals_global) / sos_weight_def

        # --- ELO BLENDING (NERFED ELITE BOOST) ---
        elo_ratio = s['elo'] / GLOBAL_ELO_MEAN
        elo_off = elo_ratio ** 0.95  # Flattens the offensive gap for mid-tier
        elo_def = 1.0 / (elo_ratio ** 0.95) # Flattens the defensive gap
        
        elo_off = np.clip(elo_off, 0.6, 2.0)
        elo_def = np.clip(elo_def, 0.6, 2.0)

        elo_off_log = np.log(elo_off)
        elo_def_log = np.log(elo_def)

        STAT_WEIGHT = 0.35  # Shifted to respect actual output more
        ELO_WEIGHT  = 0.65  

        final_off_log = STAT_WEIGHT * np.log(adjusted_off) + ELO_WEIGHT * elo_off_log
        s['off'] = np.exp(final_off_log)

        final_def_log = STAT_WEIGHT * np.log(adjusted_def) + ELO_WEIGHT * elo_def_log
        s['def'] = np.exp(final_def_log)
        
        s['off'] = np.clip(s['off'], 0.5, 2.2) # Tightened
        s['def'] = np.clip(s['def'], 0.5, 2.2) # Tightened

        s['adj_gf'] = s['off'] * avg_goals_global
        s['adj_ga'] = s['def'] * avg_goals_global

        recent_form = s['form'][-5:] 
        s['form'] = "".join(recent_form) if recent_form else "-----"
        m = s['matches']
        g = s['total_goals_recorded']
        
        s['cs_pct'] = (s['clean_sheets'] / m * 100) if m > 0 else 0
        s['btts_pct'] = (s['btts'] / m * 100) if m > 0 else 0            
        s['pen_pct'] = (s['penalties'] / g * 100) if g > 0 else 0
        s['fh_pct'] = (s['first_half'] / g * 100) if g > 0 else 0
        s['late_pct'] = (s['late_goals'] / g * 100) if g > 0 else 0
        
        if t in recent_residuals and recent_residuals[t]:
            num = sum(w * r for w, r in recent_residuals[t])
            den = sum(w for w, r in recent_residuals[t])
            # Raised floor from 0.05 to 0.10. Prevents top teams from having mathematically 0 variance.
            s['volatility'] = np.clip(num / den, 0.10, 0.40) 
        else:
            s['volatility'] = 0.15
        
        if t in TEAM_HISTORY and len(TEAM_HISTORY[t]['elo']) > 10:
            s['momentum'] = (TEAM_HISTORY[t]['elo'][-1] - TEAM_HISTORY[t]['elo'][-10]) / 100
        else:
            s['momentum'] = 0.0        

    return TEAM_STATS, TEAM_PROFILES, AVG_GOALS, results_df

# =============================================================================
# --- PART 3: SIMULATION ---
# =============================================================================
def calculate_confed_strength():
    global CONFED_MULTIPLIERS
    results_df, _, _, _, _ = load_data()
    
    # Filter for modern era (last 10 years) to get current confederation parity
    recent_cutoff = pd.to_datetime('2014-01-01')
    results_df['date'] = pd.to_datetime(results_df['date'])
    modern_df = results_df[results_df['date'] > recent_cutoff]
    
    # Track cross-confederation performance
    # We look at how often teams from Confed A beat teams from Confed B
    confed_performance = {c: {'pts': 0, 'matches': 0} for c in set(TEAM_CONFEDS.values())}
    
    for _, row in modern_df.iterrows():
        h_conf = TEAM_CONFEDS.get(row['home_team'].lower(), 'OFC')
        a_conf = TEAM_CONFEDS.get(row['away_team'].lower(), 'OFC')
        
        if h_conf != a_conf:
            confed_performance[h_conf]['matches'] += 1
            confed_performance[a_conf]['matches'] += 1
            if row['home_score'] > row['away_score']:
                confed_performance[h_conf]['pts'] += 1
            elif row['away_score'] > row['home_score']:
                confed_performance[a_conf]['pts'] += 1
            else:
                confed_performance[h_conf]['pts'] += 0.5
                confed_performance[a_conf]['pts'] += 0.5

    # Calculate multiplier based on win percentage against other regions
    for confed, data in confed_performance.items():
        if data['matches'] > 0:
            win_rate = data['pts'] / data['matches']
            # Baseline is 0.5 (equal). We scale around that.
            # This reflects actual historical dominance (UEFA/CONMEBOL usually ~0.65)
            CONFED_MULTIPLIERS[confed] = round(0.8 + (win_rate * 0.4), 3)
        else:
            CONFED_MULTIPLIERS[confed] = 0.85 # Default for isolated regions
def engineer_team_signatures(results_df):
    global TEAM_PROFILES, ADVANCED_TEAM_DATA
    TEAM_PROFILES = {}
    ADVANCED_TEAM_DATA = {} 
    
    modern_df = results_df[results_df['date'] > '2012-01-01'].copy()
    global_avg = (modern_df['home_score'].mean() + modern_df['away_score'].mean()) / 2

    for team in TEAM_STATS.keys():
        t_games = modern_df[(modern_df['home_team'] == team) | (modern_df['away_team'] == team)]
        stats = TEAM_STATS[team]
        
        true_vol = stats.get('volatility', 0.15)
        
        if len(t_games) < 5:
            TEAM_PROFILES[team] = "Balanced"
            ADVANCED_TEAM_DATA[team] = {'type': 'Balanced', 'poss': 0.5, 'press': 0.5, 'dir': 0.5, 'vol': true_vol}
            continue

        off_res = []
        def_res = []
        pace_res = [] 
        
        for _, row in t_games.iterrows():
            is_home = row['home_team'] == team
            opp = row['away_team'] if is_home else row['home_team']
            scored = row['home_score'] if is_home else row['away_score']
            conceded = row['away_score'] if is_home else row['home_score']
            
            opp_ga = TEAM_STATS.get(opp, {}).get('ga_avg', global_avg)
            opp_gf = TEAM_STATS.get(opp, {}).get('gf_avg', global_avg)
            
            off_res.append(scored / (opp_ga + 0.5))
            def_res.append(conceded / (opp_gf + 0.5))
            pace_res.append((scored + conceded) / (global_avg * 2))

        # --- B. MAP MATH TO UI NAMES ---
        avg_off = np.mean(off_res)
        avg_def = np.mean(def_res)
        avg_pace = np.mean(pace_res)

        if avg_pace > 1.15 and true_vol > 0.18: style = "Chaos & Intensity"
        elif avg_pace < 0.90 and avg_def < 0.95: style = "Compact Block"
        elif avg_off > 1.15 and avg_pace > 1.1: style = "Vertical Control"
        elif avg_off > 1.1 and avg_def > 1.1: style = "Direct-Physical"
        else: style = "Balanced"

        TEAM_PROFILES[team] = style
        
        # We don't have possession data, so we map real statistical concepts 
        # to a 0.0 - 1.0 scale for the UI to use safely.
        
        # 'poss' -> Match Control (Higher Elo teams dictate the game state)
        control_index = np.clip((stats.get('elo', 1500) - 1000) / 1000.0, 0.2, 0.95)
        
        # 'press' -> Match Openness/Pace (How many total goals happen in their games)
        openness_index = np.clip(avg_pace * 0.45, 0.2, 0.95)
        
        # 'dir' -> Efficiency (How well they score relative to how much they concede)
        efficiency_index = np.clip((avg_off / (avg_def + 0.1)) * 0.35, 0.2, 0.95)

        ADVANCED_TEAM_DATA[team] = {
            'type': style,
            'poss': control_index,   # Acts as "Dominance"
            'press': openness_index, # Acts as "Pace"
            'dir': efficiency_index, # Acts as "Efficiency"
            'vol': true_vol          # Actual calculated variance
        }
        
        # Store the "Signature" for the Match Engine
        stats['engineered_xg'] = avg_off
        stats['pace_factor'] = avg_pace

TEAM_PRECOMPUTE = {}

def precompute_match_data():
    global TEAM_PRECOMPUTE
    TEAM_PRECOMPUTE = {}
    for t, s in TEAM_STATS.items():
        clean_name = str(t).lower().strip()
        pen_skill = s.get('pen_pct', 5) / 100.0 
        experience = np.clip(s.get('ko_exp_weighted', 0) / 20.0, 0, 0.1)
        p_bonus = pen_skill + experience
        team_rating = s.get('team_rating', 85.0)
        rating_delta = team_rating - 85.0
        rating_adj = 1.0 + np.clip(rating_delta / 110.0, -0.12, 0.12)
        TEAM_PRECOMPUTE[clean_name] = {
            'elo': s.get('elo', 1200) + (team_rating - 85.0) * 1.15,
            'xg_coeff': s.get('off', 1.0) * rating_adj,
            'xga_coeff': s.get('def', 1.0) / rating_adj,
            'pace': s.get('pace_factor', 1.0),
            'vol': s.get('volatility', 0.15),
            'composure': np.clip(s.get('ko_exp_weighted', 0) / 10.0, 0, 1.0),
            'p_b': p_bonus
        }


def sim_match(t1, t2, knockout=False):
    t1 = t1.lower().strip()
    t2 = t2.lower().strip()
    p1 = TEAM_PRECOMPUTE.get(t1)
    p2 = TEAM_PRECOMPUTE.get(t2)

    if not p1 or not p2:
        return t1, 1, 0, 'reg'

    # 1. Match Environment
    pace = (p1['pace'] + p2['pace']) / 2
    intensity = 0.82 if knockout else 1.0
    total_match_goals = 2.70 * pace * intensity

    dr = p1['elo'] - p2['elo']
    active_divisor = 580 if knockout else 500
    win_prob = 1 / (10**(-dr/active_divisor) + 1)

    elo_lam1 = total_match_goals * win_prob
    elo_lam2 = total_match_goals * (1.0 - win_prob)

    stat_lam1 = (total_match_goals / 2) * p1['xg_coeff'] * p2['xga_coeff']
    stat_lam2 = (total_match_goals / 2) * p2['xg_coeff'] * p1['xga_coeff']

    lam1 = max(0.1, (elo_lam1 * 0.65) + (stat_lam1 * 0.35))
    lam2 = max(0.1, (elo_lam2 * 0.65) + (stat_lam2 * 0.35))

    lam1 *= (1.0 + max(0, 0.15 - p1['vol']) * 0.25)
    lam2 *= (1.0 + max(0, 0.15 - p2['vol']) * 0.25)

    def roll(l, v, c, is_ko):
        if is_ko:
            active_vol = v * (1.25 - (c * 0.35))
        else:
            active_vol = v
        if active_vol > 0:
            l = np.random.gamma(1/active_vol, l * active_vol)
        return np.random.poisson(max(0.05, l))

    g1 = roll(lam1, p1['vol'], p1['composure'], knockout)
    g2 = roll(lam2, p2['vol'], p2['composure'], knockout)

    if g1 > g2:
        return (t1, g1, g2, 'reg') if knockout else (t1, g1, g2)
    if g2 > g1:
        return (t2, g1, g2, 'reg') if knockout else (t2, g1, g2)
    if not knockout:
        return 'draw', g1, g2

    g1 += roll(lam1 * 0.38, p1['vol'], p1['composure'], True)
    g2 += roll(lam2 * 0.38, p2['vol'], p2['composure'], True)
    if g1 > g2:
        return t1, g1, g2, 'aet'
    if g2 > g1:
        return t2, g1, g2, 'aet'

    win_chance = 0.5 + (dr / 6000.0) + ((p1['p_b'] - p2['p_b']) * 0.5)
    winner = t1 if random.random() < np.clip(win_chance, 0.40, 0.60) else t2
    return winner, g1, g2, 'pks'


def run_simulation(verbose=False, quiet=False, fast_mode=False, finalized_slots=None):
    p1 = TEAM_PRECOMPUTE.get(t1)
    p2 = TEAM_PRECOMPUTE.get(t2)

    if not p1 or not p2: return t1, 1, 0, 'reg'

    # 1. Match Environment 
    pace = (p1['pace'] + p2['pace']) / 2
    # Knockout matches are tighter -> fewer goals = more draws = better underdog odds
    intensity = 0.82 if knockout else 1.0 
    total_match_goals = 2.70 * pace * intensity 
    
    dr = p1.get('rating_elo', p1.get('elo', 1200)) - p2.get('rating_elo', p2.get('elo', 1200))
    
    # 3. Elo Probability Distribution
    # Increase the divisor strictly for knockouts to simulate tournament parity
    active_divisor = 580 if knockout else 500
    win_prob = 1 / (10**(-dr/active_divisor) + 1)
    
    elo_lam1 = total_match_goals * win_prob
    elo_lam2 = total_match_goals * (1.0 - win_prob)

    # 4. Tactical Stat Flavor
    stat_lam1 = (total_match_goals / 2) * p1['xg_coeff'] * p2['xga_coeff']
    stat_lam2 = (total_match_goals / 2) * p2['xg_coeff'] * p1['xga_coeff']

    # 5. The Master Blend
    lam1 = max(0.1, (elo_lam1 * 0.65) + (stat_lam1 * 0.35))
    lam2 = max(0.1, (elo_lam2 * 0.65) + (stat_lam2 * 0.35))
    
    # 6. Consistency/Clinical Bonus (Buff reduced to prevent elite over-performance)
    lam1 *= (1.0 + max(0, 0.15 - p1['vol']) * 0.25)
    lam2 *= (1.0 + max(0, 0.15 - p2['vol']) * 0.25)

    # 7. THE ROLL (Gamma-Poisson Distribution)
    def roll(l, v, c, is_ko):
        if is_ko:
            # Underdogs keep high variance, top teams get a slightly smaller composure buff
            active_vol = v * (1.25 - (c * 0.35))
        else:
            active_vol = v
        if active_vol > 0:
            l = np.random.gamma(1/active_vol, l * active_vol)
        return np.random.poisson(max(0.05, l))

    g1 = roll(lam1, p1['vol'], p1['composure'], knockout)
    g2 = roll(lam2, p2['vol'], p2['composure'], knockout)

    # 8. RESOLUTION
    if g1 > g2: return (t1, g1, g2, 'reg') if knockout else (t1, g1, g2)
    if g2 > g1: return (t2, g1, g2, 'reg') if knockout else (t2, g1, g2)
    if not knockout: return 'draw', g1, g2

    # Extra Time (Approx 1/3 of match time)
    g1 += roll(lam1 * 0.38, p1['vol'], p1['composure'], True)
    g2 += roll(lam2 * 0.38, p2['vol'], p2['composure'], True)
    if g1 > g2: return t1, g1, g2, 'aet'
    if g2 > g1: return t2, g1, g2, 'aet'
    
    # Penalties (Pressure + Skill + Luck)
    # Reduced the Elo advantage to make shootouts more of a 50/50 lottery
    win_chance = 0.5 + (dr / 6000.0) + ((p1['p_b'] - p2['p_b']) * 0.5)
    winner = t1 if random.random() < np.clip(win_chance, 0.40, 0.60) else t2
    return winner, g1, g2, 'pks'

def run_simulation(verbose=False, quiet=False, fast_mode=False, finalized_slots=None):
    structured_groups = {} if not fast_mode else None
    structured_bracket = [] if not fast_mode else None
    group_matches_log = {} if not fast_mode else None

    if finalized_slots is None:
        slots = FINALIZED_SLOTS.copy()
    else:
        slots = finalized_slots

    groups = {
        'A': ['mexico', 'south africa', 'south korea', slots['Path D']],
        'B': ['canada', 'switzerland', 'qatar', slots['Path A']],
        'C': ['brazil', 'morocco', 'haiti', 'scotland'],
        'D': ['united states', 'paraguay', 'australia', slots['Path C']],
        'E': ['germany', 'curaçao', 'ivory coast', 'ecuador'],
        'F': ['netherlands', 'japan', 'tunisia', slots['Path B']],
        'G': ['belgium', 'egypt', 'iran', 'new zealand'],
        'H': ['spain', 'cape verde', 'saudi arabia', 'uruguay'],
        'I': ['france', 'senegal', 'norway', slots['ICP2']],
        'J': ['argentina', 'algeria', 'austria', 'jordan'],
        'K': ['portugal', 'uzbekistan', 'colombia', slots['ICP1']],
        'L': ['england', 'croatia', 'ghana', 'panama']
    }

    clean_groups = {}
    for grp, teams in groups.items():
        clean_groups[grp] = [str(team).lower().strip() for team in teams]
    groups = clean_groups

    group_results_lists = {}
    third_place =[]
    
    for grp, teams in groups.items():
        teams_shuffled = teams.copy()
        np.random.shuffle(teams_shuffled)
        
        table_stats = {t: {'p':0, 'gd':0, 'gf':0, 'w':0, 'd':0, 'l':0} for t in teams_shuffled}
        if not fast_mode: group_matches_log[grp] =[]

        for i in range(len(teams_shuffled)):
            for j in range(i+1, len(teams_shuffled)):
                t1, t2 = teams_shuffled[i], teams_shuffled[j]
                w, g1, g2 = sim_match(t1, t2)
                
                if not fast_mode:
                    group_matches_log[grp].append({'t1': t1, 't2': t2, 'g1': g1, 'g2': g2})
                
                table_stats[t1]['gf'] += g1; table_stats[t1]['gd'] += (g1-g2)
                table_stats[t2]['gf'] += g2; table_stats[t2]['gd'] += (g2-g1)
                
                if g1 > g2: 
                    table_stats[t1]['p'] += 3
                    table_stats[t1]['w'] += 1
                    table_stats[t2]['l'] += 1
                elif g2 > g1: 
                    table_stats[t2]['p'] += 3
                    table_stats[t2]['w'] += 1
                    table_stats[t1]['l'] += 1
                else: 
                    table_stats[t1]['p'] += 1; table_stats[t2]['p'] += 1
                    table_stats[t1]['d'] += 1; table_stats[t2]['d'] += 1

        sorted_teams = sorted(teams_shuffled, key=lambda t: (table_stats[t]['p'], table_stats[t]['gd'], table_stats[t]['gf']), reverse=True)
        group_results_lists[grp] = sorted_teams
        third_place.append({'team': sorted_teams[2], 'team_group': grp, 'stats': table_stats[sorted_teams[2]]})

        if not fast_mode:
            structured_groups[grp] =[]
            for t in sorted_teams:
                structured_groups[grp].append({'team': t, **table_stats[t]})

    def get_t(grp, pos):
        return group_results_lists[grp][pos]

    best_3rds = sorted(third_place, key=lambda x: (x['stats']['p'], x['stats']['gd'], x['stats']['gf']), reverse=True)[:8]
    target_winners =['A', 'B', 'D', 'E', 'G', 'I', 'K', 'L']
    t3_mapping = {}

    def assign_t3(index, available_t3):
        if index == len(target_winners): return True
        host_group = target_winners[index]
        for t3 in available_t3:
            if t3['team_group'] != host_group:          
                t3_mapping[host_group] = t3['team']
                new_available =[t for t in available_t3 if t != t3]
                if assign_t3(index + 1, new_available): 
                    return True
        return False
        
    assign_t3(0, best_3rds)

    bracket_matchups =[
        (get_t('A', 0), t3_mapping['A']),    
        (get_t('C', 1), get_t('F', 1)),      
        (get_t('E', 0), t3_mapping['E']),    
        (get_t('J', 0), get_t('G', 1)),     
        (get_t('I', 0), t3_mapping['I']),    
        (get_t('A', 1), get_t('D', 1)),      
        (get_t('L', 0), t3_mapping['L']),    
        (get_t('H', 0), get_t('K', 1)),      
        (get_t('B', 0), t3_mapping['B']),    
        (get_t('E', 1), get_t('H', 1)),      
        (get_t('G', 0), t3_mapping['G']),    
        (get_t('B', 1), get_t('I', 1)),      
        (get_t('K', 0), t3_mapping['K']),    
        (get_t('C', 0), get_t('L', 1)),      
        (get_t('D', 0), t3_mapping['D']),    
        (get_t('F', 0), get_t('J', 1)),      
    ]
        
    rounds = ['Round of 32', 'Round of 16', 'Quarter-finals', 'Semi-finals', 'Final']
    champion = None
    runner_up = None 
    third_place_winner = None
    semi_losers = []
    
    for r_name in rounds:
        next_round_teams = []
        current_round_losers = []
        round_matches_log = [] if not fast_mode else None
        
        for t1, t2 in bracket_matchups:
            w, g1, g2, method = sim_match(t1, t2, knockout=True)
            next_round_teams.append(w)
            
            l = t2 if w == t1 else t1
            current_round_losers.append(l)
            
            if not fast_mode:
                round_matches_log.append({'t1': t1, 't2': t2, 'g1': g1, 'g2': g2, 'winner': w, 'method': method})
        
        if r_name == 'Semi-finals':
            semi_losers = current_round_losers

        if r_name == 'Final':
            champion = next_round_teams[0]
            runner_up = current_round_losers[0]
            
            t3_1, t3_2 = semi_losers[0], semi_losers[1]
            w_3rd, g3_1, g3_2, method_3rd = sim_match(t3_1, t3_2, knockout=True)
            third_place_winner = w_3rd 
            
            if not fast_mode:
                structured_bracket.append({'round': 'Third Place Play-off', 'matches': [{
                    't1': t3_1, 't2': t3_2, 'g1': g3_1, 'g2': g3_2, 'winner': w_3rd, 'method': method_3rd
                }]})

        if not fast_mode:
            structured_bracket.append({'round': r_name, 'matches': round_matches_log})
        
        bracket_matchups = []
        for i in range(0, len(next_round_teams), 2):
            if i+1 < len(next_round_teams):
                    bracket_matchups.append((next_round_teams[i], next_round_teams[i+1]))

    return {
        "champion": champion,
        "runner_up": runner_up, 
        "third_place": third_place_winner, 
        "groups_data": structured_groups,
        "bracket_data": structured_bracket,
        "group_matches": group_matches_log
    }

# =============================================================================
# --- 6. HISTORICAL BACKTESTING UTILS ---
# =============================================================================
def get_historical_elo(cutoff_date='2022-11-20'):
    results_df, _, _, _, _ = load_data()
    if results_df is None: return {}

    results_df['date'] = pd.to_datetime(results_df['date'])
    results_df = results_df.sort_values('date')
    historic_df = results_df[results_df['date'] < cutoff_date]

    team_elo = {}
    INITIAL_RATING = 1200
    
    for _, row in historic_df.iterrows():
        h = row['home_team'].lower().strip()
        a = row['away_team'].lower().strip()
        hs, as_ = row['home_score'], row['away_score']
        
        rh = team_elo.get(h, INITIAL_RATING)
        ra = team_elo.get(a, INITIAL_RATING)
        
        gd = abs(hs - as_)
        k = get_k_factor(row['tournament'], gd, h, a)
        
        dr = rh - ra + (100 if not row['neutral'] else 0)
        we = 1 / (10**(-dr/500) + 1)
        W = 1 if hs > as_ else (0 if as_ > hs else 0.5)
        
        change = k * (W - we)
        team_elo[h] = rh + change
        team_elo[a] = ra - change

    return team_elo

# The 32 Teams of Qatar 2022 (Correct Groups)
WC_2022_GROUPS = {
    'A': ['qatar', 'ecuador', 'senegal', 'netherlands'],
    'B': ['england', 'iran', 'united states', 'wales'],
    'C': ['argentina', 'saudi arabia', 'mexico', 'poland'],
    'D': ['france', 'australia', 'denmark', 'tunisia'],
    'E': ['spain', 'costa rica', 'germany', 'japan'],
    'F': ['belgium', 'canada', 'morocco', 'croatia'],
    'G': ['brazil', 'serbia', 'switzerland', 'cameroon'],
    'H': ['portugal', 'ghana', 'uruguay', 'south korea']
}