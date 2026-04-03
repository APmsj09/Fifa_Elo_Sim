import pandas as pd
import numpy as np
import random
import math
import js
from pyodide.http import open_url

def calculate_recency_weight(match_date, latest_date):
    """
    Halves importance every ~3 years (1,066 days).
    A match from 4 years ago (1,460 days) is now worth ~39% (approx 2.5x less).
    """
    days_old = (latest_date - match_date).days
    return math.exp(-0.00065 * max(0, days_old))

# =============================================================================
# --- PART 1: SETUP & DATA LOADING ---
# =============================================================================

DATA_DIR = "." 

# Global Vars
TEAM_STATS = {}
TEAM_PROFILES = {}
TEAM_HISTORY = {}
AVG_GOALS = 2.5

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
ADVANCED_TEAM_DATA = {
    'france': {'type': 'Vertical Control', 'poss': 0.72, 'press': 0.58, 'dir': 0.52, 'vol': 0.04},
    'spain': {'type': 'Vertical Control', 'poss': 0.92, 'press': 0.68, 'dir': 0.35, 'vol': 0.03},
    'argentina': {'type': 'Vertical Control', 'poss': 0.78, 'press': 0.64, 'dir': 0.48, 'vol': 0.05},
    'england': {'type': 'Vertical Control', 'poss': 0.88, 'press': 0.62, 'dir': 0.38, 'vol': 0.04},
    'portugal': {'type': 'Vertical Control', 'poss': 0.84, 'press': 0.65, 'dir': 0.44, 'vol': 0.06},
    'brazil': {'type': 'Vertical Control', 'poss': 0.74, 'press': 0.62, 'dir': 0.55, 'vol': 0.07},
    'netherlands': {'type': 'Vertical Control', 'poss': 0.71, 'press': 0.64, 'dir': 0.52, 'vol': 0.07},
    'morocco': {'type': 'Compact Block', 'poss': 0.41, 'press': 0.52, 'dir': 0.84, 'vol': 0.06},
    'belgium': {'type': 'Vertical Control', 'poss': 0.68, 'press': 0.58, 'dir': 0.58, 'vol': 0.08},
    'germany': {'type': 'Vertical Control', 'poss': 0.82, 'press': 0.75, 'dir': 0.60, 'vol': 0.11},
    'croatia': {'type': 'Vertical Control', 'poss': 0.71, 'press': 0.52, 'dir': 0.42, 'vol': 0.05},
    'italy': {'type': 'Vertical Control', 'poss': 0.70, 'press': 0.65, 'dir': 0.45, 'vol': 0.09},
    'colombia': {'type': 'Vertical Control', 'poss': 0.64, 'press': 0.71, 'dir': 0.62, 'vol': 0.10},
    'senegal': {'type': 'Chaos & Intensity', 'poss': 0.52, 'press': 0.78, 'dir': 0.79, 'vol': 0.13},
    'mexico': {'type': 'Vertical Control', 'poss': 0.62, 'press': 0.65, 'dir': 0.58, 'vol': 0.12},
    'united states': {'type': 'Chaos & Intensity', 'poss': 0.59, 'press': 0.82, 'dir': 0.68, 'vol': 0.14},
    'uruguay': {'type': 'Chaos & Intensity', 'poss': 0.55, 'press': 0.94, 'dir': 0.84, 'vol': 0.12},
    'japan': {'type': 'Vertical Control', 'poss': 0.63, 'press': 0.75, 'dir': 0.68, 'vol': 0.06},
    'switzerland': {'type': 'Vertical Control', 'poss': 0.64, 'press': 0.55, 'dir': 0.48, 'vol': 0.05},
    'denmark': {'type': 'Vertical Control', 'poss': 0.65, 'press': 0.70, 'dir': 0.55, 'vol': 0.08},
    'iran': {'type': 'Compact Block', 'poss': 0.36, 'press': 0.35, 'dir': 0.88, 'vol': 0.04},
    'turkey': {'type': 'Vertical Control', 'poss': 0.61, 'press': 0.68, 'dir': 0.64, 'vol': 0.11},
    'ecuador': {'type': 'Direct-Physical', 'poss': 0.46, 'press': 0.68, 'dir': 0.78, 'vol': 0.09},
    'austria': {'type': 'Chaos & Intensity', 'poss': 0.51, 'press': 0.88, 'dir': 0.76, 'vol': 0.12},
    'south korea': {'type': 'Chaos & Intensity', 'poss': 0.51, 'press': 0.78, 'dir': 0.82, 'vol': 0.09},
    'nigeria': {'type': 'Chaos & Intensity', 'poss': 0.50, 'press': 0.80, 'dir': 0.75, 'vol': 0.15},
    'australia': {'type': 'Direct-Physical', 'poss': 0.48, 'press': 0.62, 'dir': 0.72, 'vol': 0.07},
    'algeria': {'type': 'Vertical Control', 'poss': 0.58, 'press': 0.62, 'dir': 0.62, 'vol': 0.12},
    'egypt': {'type': 'Compact Block', 'poss': 0.43, 'press': 0.42, 'dir': 0.82, 'vol': 0.08},
    'canada': {'type': 'Vertical Control', 'poss': 0.58, 'press': 0.72, 'dir': 0.64, 'vol': 0.13},
    'norway': {'type': 'Chaos & Intensity', 'poss': 0.58, 'press': 0.72, 'dir': 0.91, 'vol': 0.11},
    'ukraine': {'type': 'Vertical Control', 'poss': 0.62, 'press': 0.60, 'dir': 0.50, 'vol': 0.09},
    'panama': {'type': 'Compact Block', 'poss': 0.37, 'press': 0.42, 'dir': 0.75, 'vol': 0.10},
    'ivory coast': {'type': 'Chaos & Intensity', 'poss': 0.54, 'press': 0.71, 'dir': 0.74, 'vol': 0.14},
    'poland': {'type': 'Direct-Physical', 'poss': 0.44, 'press': 0.55, 'dir': 0.80, 'vol': 0.11},
    'russia': {'type': 'Vertical Control', 'poss': 0.55, 'press': 0.58, 'dir': 0.62, 'vol': 0.16},
    'wales': {'type': 'Direct-Physical', 'poss': 0.42, 'press': 0.65, 'dir': 0.78, 'vol': 0.09},
    'sweden': {'type': 'Chaos & Intensity', 'poss': 0.52, 'press': 0.72, 'dir': 0.86, 'vol': 0.12},
    'serbia': {'type': 'Direct-Physical', 'poss': 0.45, 'press': 0.55, 'dir': 0.78, 'vol': 0.14},
    'paraguay': {'type': 'Compact Block', 'poss': 0.37, 'press': 0.55, 'dir': 0.79, 'vol': 0.09},
    'czech republic': {'type': 'Chaos & Intensity', 'poss': 0.48, 'press': 0.85, 'dir': 0.75, 'vol': 0.11},
    'hungary': {'type': 'Compact Block', 'poss': 0.40, 'press': 0.45, 'dir': 0.70, 'vol': 0.07},
    'scotland': {'type': 'Direct-Physical', 'poss': 0.45, 'press': 0.58, 'dir': 0.76, 'vol': 0.08},
    'tunisia': {'type': 'Compact Block', 'poss': 0.39, 'press': 0.48, 'dir': 0.71, 'vol': 0.09},
    'cameroon': {'type': 'Direct-Physical', 'poss': 0.45, 'press': 0.60, 'dir': 0.75, 'vol': 0.17},
    'dr congo': {'type': 'Direct-Physical', 'poss': 0.42, 'press': 0.52, 'dir': 0.74, 'vol': 0.16},
    'greece': {'type': 'Compact Block', 'poss': 0.38, 'press': 0.40, 'dir': 0.72, 'vol': 0.06},
    'slovakia': {'type': 'Compact Block', 'poss': 0.42, 'press': 0.50, 'dir': 0.70, 'vol': 0.08},
    'venezuela': {'type': 'Compact Block', 'poss': 0.39, 'press': 0.55, 'dir': 0.78, 'vol': 0.12},
    'uzbekistan': {'type': 'Compact Block', 'poss': 0.38, 'press': 0.44, 'dir': 0.78, 'vol': 0.15},
    'costa rica': {'type': 'Compact Block', 'poss': 0.35, 'press': 0.48, 'dir': 0.76, 'vol': 0.11},
    'mali': {'type': 'Direct-Physical', 'poss': 0.46, 'press': 0.62, 'dir': 0.70, 'vol': 0.16},
    'peru': {'type': 'Vertical Control', 'poss': 0.55, 'press': 0.60, 'dir': 0.60, 'vol': 0.14},
    'chile': {'type': 'Chaos & Intensity', 'poss': 0.52, 'press': 0.85, 'dir': 0.72, 'vol': 0.15},
    'qatar': {'type': 'Compact Block', 'poss': 0.42, 'press': 0.31, 'dir': 0.68, 'vol': 0.14},
    'romania': {'type': 'Compact Block', 'poss': 0.41, 'press': 0.48, 'dir': 0.74, 'vol': 0.10},
    'iraq': {'type': 'Compact Block', 'poss': 0.31, 'press': 0.38, 'dir': 0.82, 'vol': 0.17},
    'slovenia': {'type': 'Compact Block', 'poss': 0.39, 'press': 0.45, 'dir': 0.78, 'vol': 0.08},
    'ireland': {'type': 'Direct-Physical', 'poss': 0.43, 'press': 0.52, 'dir': 0.76, 'vol': 0.09},
    'south africa': {'type': 'Direct-Physical', 'poss': 0.44, 'press': 0.48, 'dir': 0.72, 'vol': 0.15},
    'saudi arabia': {'type': 'Vertical Control', 'poss': 0.58, 'press': 0.52, 'dir': 0.54, 'vol': 0.14},
    'burkina faso': {'type': 'Chaos & Intensity', 'poss': 0.48, 'press': 0.70, 'dir': 0.75, 'vol': 0.18},
    'jordan': {'type': 'Compact Block', 'poss': 0.33, 'press': 0.31, 'dir': 0.84, 'vol': 0.19},
    'albania': {'type': 'Compact Block', 'poss': 0.36, 'press': 0.42, 'dir': 0.80, 'vol': 0.10},
    'bosnia and herzegovina': {'type': 'Compact Block', 'poss': 0.38, 'press': 0.35, 'dir': 0.80, 'vol': 0.14},
    'honduras': {'type': 'Direct-Physical', 'poss': 0.40, 'press': 0.55, 'dir': 0.74, 'vol': 0.13},
    'north macedonia': {'type': 'Compact Block', 'poss': 0.37, 'press': 0.44, 'dir': 0.79, 'vol': 0.12},
    'uae': {'type': 'Vertical Control', 'poss': 0.54, 'press': 0.48, 'dir': 0.58, 'vol': 0.14},
    'cape verde': {'type': 'Compact Block', 'poss': 0.34, 'press': 0.41, 'dir': 0.76, 'vol': 0.18},
    'northern ireland': {'type': 'Compact Block', 'poss': 0.32, 'press': 0.50, 'dir': 0.82, 'vol': 0.07},
    'jamaica': {'type': 'Direct-Physical', 'poss': 0.41, 'press': 0.64, 'dir': 0.78, 'vol': 0.17},
    'georgia': {'type': 'Compact Block', 'poss': 0.35, 'press': 0.40, 'dir': 0.86, 'vol': 0.15},
    'finland': {'type': 'Vertical Control', 'poss': 0.51, 'press': 0.45, 'dir': 0.64, 'vol': 0.09},
    'ghana': {'type': 'Chaos & Intensity', 'poss': 0.48, 'press': 0.68, 'dir': 0.78, 'vol': 0.19},
    'iceland': {'type': 'Compact Block', 'poss': 0.33, 'press': 0.45, 'dir': 0.85, 'vol': 0.08},
    'bolivia': {'type': 'Compact Block', 'poss': 0.34, 'press': 0.38, 'dir': 0.79, 'vol': 0.12},
    'israel': {'type': 'Vertical Control', 'poss': 0.53, 'press': 0.52, 'dir': 0.58, 'vol': 0.13},
    'kosovo': {'type': 'Chaos & Intensity', 'poss': 0.47, 'press': 0.65, 'dir': 0.74, 'vol': 0.16},
    'oman': {'type': 'Compact Block', 'poss': 0.41, 'press': 0.35, 'dir': 0.72, 'vol': 0.12},
    'guinea': {'type': 'Direct-Physical', 'poss': 0.43, 'press': 0.55, 'dir': 0.74, 'vol': 0.15},
    'montenegro': {'type': 'Compact Block', 'poss': 0.38, 'press': 0.42, 'dir': 0.78, 'vol': 0.10},
    'curaçao': {'type': 'Compact Block', 'poss': 0.32, 'press': 0.28, 'dir': 0.85, 'vol': 0.19},
    'haiti': {'type': 'Direct-Physical', 'poss': 0.35, 'press': 0.45, 'dir': 0.78, 'vol': 0.20},
    'syria': {'type': 'Compact Block', 'poss': 0.34, 'press': 0.32, 'dir': 0.80, 'vol': 0.13},
    'new zealand': {'type': 'Direct-Physical', 'poss': 0.40, 'press': 0.55, 'dir': 0.81, 'vol': 0.11},
    'bulgaria': {'type': 'Compact Block', 'poss': 0.41, 'press': 0.38, 'dir': 0.70, 'vol': 0.14},
    'gabon': {'type': 'Chaos & Intensity', 'poss': 0.46, 'press': 0.62, 'dir': 0.79, 'vol': 0.18},
    'uganda': {'type': 'Compact Block', 'poss': 0.35, 'press': 0.40, 'dir': 0.76, 'vol': 0.15},
    'angola': {'type': 'Compact Block', 'poss': 0.39, 'press': 0.42, 'dir': 0.74, 'vol': 0.14},
    'benin': {'type': 'Compact Block', 'poss': 0.37, 'press': 0.35, 'dir': 0.78, 'vol': 0.14},
    'bahrain': {'type': 'Compact Block', 'poss': 0.42, 'press': 0.32, 'dir': 0.70, 'vol': 0.13},
    'zambia': {'type': 'Chaos & Intensity', 'poss': 0.45, 'press': 0.65, 'dir': 0.76, 'vol': 0.19},
    'thailand': {'type': 'Vertical Control', 'poss': 0.52, 'press': 0.55, 'dir': 0.68, 'vol': 0.13},
    'el salvador': {'type': 'Compact Block', 'poss': 0.38, 'press': 0.45, 'dir': 0.74, 'vol': 0.14},
    'luxembourg': {'type': 'Compact Block', 'poss': 0.42, 'press': 0.40, 'dir': 0.68, 'vol': 0.09},
    'armenia': {'type': 'Compact Block', 'poss': 0.36, 'press': 0.38, 'dir': 0.79, 'vol': 0.14},
    'palestine': {'type': 'Compact Block', 'poss': 0.31, 'press': 0.35, 'dir': 0.82, 'vol': 0.18},
    'equatorial guinea': {'type': 'Compact Block', 'poss': 0.38, 'press': 0.48, 'dir': 0.72, 'vol': 0.16},
    'vietnam': {'type': 'Compact Block', 'poss': 0.38, 'press': 0.45, 'dir': 0.79, 'vol': 0.15},
    'kazakhstan': {'type': 'Compact Block', 'poss': 0.33, 'press': 0.42, 'dir': 0.84, 'vol': 0.16}
}

# =============================================================================
# --- TACTICAL MATCHUP MATRIX (The Rock-Paper-Scissors of Football) ---
# =============================================================================
# Format: ('Team 1 Style', 'Team 2 Style'): Attacking Multiplier for Team 1
# > 1.0 means Team 1 has a tactical advantage and generates more expected goals.
# < 1.0 means Team 1 is tactically countered and generates fewer expected goals.

STYLE_MATCHUPS = {
    # High Press disrupts teams that try to build from the back
    ('High Press', 'Ball Control'): 1.08,
    ('Ball Control', 'High Press'): 0.95,
    
    # Direct Play bypasses the High Press completely
    ('Direct Play', 'High Press'): 1.08,
    ('High Press', 'Direct Play'): 0.92,
    
    # Fast Build-up beats the press by moving the ball before the trap closes
    ('Fast Build-up', 'High Press'): 1.06,
    ('High Press', 'Fast Build-up'): 0.94,

    # Counter-Attack exploits high lines and possession teams
    ('Counter-Attack', 'Ball Control'): 1.08,
    ('Ball Control', 'Counter-Attack'): 0.96,
    ('Counter-Attack', 'High Risk'): 1.10,
    ('High Risk', 'Counter-Attack'): 0.90,
    
    # Deep Block starves Counter-Attack and Fast Build-up of running space
    ('Deep Block', 'Counter-Attack'): 1.05,
    ('Counter-Attack', 'Deep Block'): 0.85,
    ('Deep Block', 'Fast Build-up'): 1.05,
    ('Fast Build-up', 'Deep Block'): 0.90,

    # Technical Play (Individual Brilliance) unlocks the Deep Block
    ('Technical Play', 'Deep Block'): 1.10,
    ('Deep Block', 'Technical Play'): 0.90,
    
    # Disciplined structure neutralizes Technical flair and High Risk chaos
    ('Disciplined', 'Technical Play'): 1.08,
    ('Technical Play', 'Disciplined'): 0.92,
    ('Disciplined', 'High Risk'): 1.08,
    ('High Risk', 'Disciplined'): 0.92,

    # Ball Control starves Direct Play and grinds down Deep Blocks over 90 mins
    ('Ball Control', 'Direct Play'): 1.08,
    ('Direct Play', 'Ball Control'): 0.94,
    ('Ball Control', 'Deep Block'): 1.05,
    ('Deep Block', 'Ball Control'): 0.95
}

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

def load_data():
    try:
        former_names_df = pd.read_csv("former_names.csv")
        results_df = pd.read_csv("results.csv") 
        goalscorers_df = pd.read_csv("goalscorers.csv")
        return results_df, goalscorers_df, former_names_df
    except Exception as e:
        js.console.error(f"CRITICAL ERROR LOADING DATA: {e}")
        return None, None, None

# =============================================================================
# --- PART 2: INITIALIZATION (OPTIMIZED) ---
# =============================================================================
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

    if goal_diff == 2: k *= 1.15
    elif goal_diff == 3: k *= 1.30
    elif goal_diff >= 4: k *= 1.35
    
    return k

def initialize_engine():
    try:
        df_names = pd.read_csv(open_url("former_names.csv"))
        NAME_MAP = dict(zip(df_names['old_name'], df_names['new_name']))
    except:
        NAME_MAP = {}

    results_df, scorers_df, _ = load_data()
    
    if results_df is None:
        return {}, {}, 2.5

    # --- 1. CLEAN DATA ---
    results_df['date'] = pd.to_datetime(results_df['date'], errors='coerce')
    results_df = results_df.dropna(subset=['date', 'home_score', 'away_score'])
    results_df = results_df.astype({'home_score': int, 'away_score': int})
    
    # Standardize Names
    results_df['home_team'] = results_df['home_team'].str.lower().str.strip().replace(NAME_MAP)
    results_df['away_team'] = results_df['away_team'].str.lower().str.strip().replace(NAME_MAP)
    
    # Sort for Elo (Critical)
    elo_df = results_df.sort_values('date')

    # ----------------------------------------------------
    # PHASE 1: CHRONOLOGICAL ELO & LIVE TRACKING
    # ----------------------------------------------------
    team_elo = {}
    INITIAL_RATING = 1200
    RELEVANCE_CUTOFF = pd.to_datetime('2021-01-01') # "Recent History" Filter for Profile Stats
    
    global TEAM_HISTORY
    TEAM_HISTORY = {} 
    global TEAM_STATS
    TEAM_STATS = {}
    
    LATEST_DATE = elo_df['date'].max()
    
    # 1. INITIALIZE ALL TEAMS FIRST
    all_teams_set = set(elo_df['home_team']).union(set(elo_df['away_team']))
    recent_residuals = {t: [] for t in all_teams_set}
    
    for t in all_teams_set:
        TEAM_STATS[t] = {
            'elo': INITIAL_RATING, 'notable_results': [],
            'vs_elite': [0, 0, 0], 'vs_stronger': [0, 0, 0], 'vs_similar':  [0, 0, 0], 'vs_weaker':   [0, 0, 0],

            # --- Upset Tracking (Live Elo) ---
            'upsets_major_won': 0,  'upsets_minor_won': 0, 'upsets_major_lost': 0, 'upsets_minor_lost': 0,

            # --- Stats to be filled in Phase 2 ---
            'matches': 0, 'clean_sheets': 0, 'btts': 0, 'gf_avg': 0, 'ga_avg': 0, 'off': 1.0, 'def': 1.0,
            'penalties': 0, 'first_half': 0, 'late_goals': 0, 'total_goals_recorded': 0, 'form': []
        }

    # 2. THE MAIN LOOP (Chronological)
    matches_data = zip(elo_df['home_team'], elo_df['away_team'], 
                       elo_df['home_score'], elo_df['away_score'], 
                       elo_df['tournament'], elo_df['neutral'], elo_df['date'])

    for h, a, hs, as_, tourney, neutral, date in matches_data:
        rh = team_elo.get(h, INITIAL_RATING)
        ra = team_elo.get(a, INITIAL_RATING)

        ko_stages = ['Quarter-finals', 'Semi-finals', 'Final']
        if any(stage in tourney for stage in ko_stages):
            w = calculate_recency_weight(date, LATEST_DATE) 
            TEAM_STATS[h]['ko_exp_weighted'] = TEAM_STATS[h].get('ko_exp_weighted', 0) + w
            TEAM_STATS[a]['ko_exp_weighted'] = TEAM_STATS[a].get('ko_exp_weighted', 0) + w
        
        # B. DETERMINE RESULT (0=Win, 1=Draw, 2=Loss)
        if hs > as_:   res_h, res_a = 0, 2
        elif hs == as_: res_h, res_a = 1, 1
        else:          res_h, res_a = 2, 0
        
        # =========================================================
        # C. TRACK TIERS & UPSETS (LIVE EVALUATION)
        # =========================================================
        if date > RELEVANCE_CUTOFF:
            # Helper to record upset
            # type_code: "WON_MAJOR", "WON_MINOR", "LOST_MAJOR", "LOST_MINOR"
            def record_upset(team, opp, score_str, elo_diff, type_code, match_date):
                TEAM_STATS[team]['notable_results'].append({
                    'opp': opp, 'score': score_str, 'diff': abs(int(elo_diff)), 'date': match_date, 'type': type_code
                })

            # --- HOME PERSPECTIVE ---
            diff_h = ra - rh 
            if ra > 1750 or diff_h > 150: TEAM_STATS[h]['vs_elite'][res_h] += 1
            if diff_h > 100: cat = 'vs_stronger'
            elif diff_h < -100: cat = 'vs_weaker'
            else: cat = 'vs_similar'
            TEAM_STATS[h][cat][res_h] += 1
            
            # Upset Logic + RECORDING
            score_h = f"{hs}-{as_}"
            if res_h == 0: # Home Win
                if diff_h > 300:   
                    TEAM_STATS[h]['upsets_major_won'] += 1
                    record_upset(h, a, score_h, diff_h, "WON_MAJOR", date)
                elif diff_h > 150: 
                    TEAM_STATS[h]['upsets_minor_won'] += 1
                    record_upset(h, a, score_h, diff_h, "WON_MINOR", date)
            
            if res_h == 2: # Home Loss
                if diff_h < -300:   
                    TEAM_STATS[h]['upsets_major_lost'] += 1
                    record_upset(h, a, score_h, diff_h, "LOST_MAJOR", date)
                elif diff_h < -150: 
                    TEAM_STATS[h]['upsets_minor_lost'] += 1

            # --- AWAY PERSPECTIVE ---
            diff_a = rh - ra 
            if rh > 1750 or diff_a > 150: TEAM_STATS[a]['vs_elite'][res_a] += 1
            if diff_a > 100: cat = 'vs_stronger'
            elif diff_a < -100: cat = 'vs_weaker'
            else: cat = 'vs_similar'
            TEAM_STATS[a][cat][res_a] += 1
            
            score_a = f"{as_}-{hs}"
            if res_a == 0: # Away Win
                if diff_a > 300:   
                    TEAM_STATS[a]['upsets_major_won'] += 1
                    record_upset(a, h, score_a, diff_a, "WON_MAJOR", date)
                elif diff_a > 150: 
                    TEAM_STATS[a]['upsets_minor_won'] += 1
                    record_upset(a, h, score_a, diff_a, "WON_MINOR", date)
            
            if res_a == 2: # Away Loss
                if diff_a < -300:   
                    TEAM_STATS[a]['upsets_major_lost'] += 1
                    record_upset(a, h, score_a, diff_a, "LOST_MAJOR", date)
                elif diff_a < -150: 
                    TEAM_STATS[a]['upsets_minor_lost'] += 1
        
         # =========================================================
        
        # D. ELO CALCULATION (Standard)
        if h not in TEAM_HISTORY: TEAM_HISTORY[h] = {'dates': [], 'elo': []}
        if a not in TEAM_HISTORY: TEAM_HISTORY[a] = {'dates': [], 'elo': []}
        
        # Calculate Expectancy (Divisor changed to 400 for better elite separation)
        dr = rh - ra + (100 if not neutral else 0)
        we_h = 1 / (10**(-dr/400) + 1)
        W_h = 1.0 if hs > as_ else (0.5 if hs == as_ else 0.0)
        
        # Apply Update
        k = get_k_factor(tourney, abs(hs - as_), h, a)
        change = k * (W_h - we_h)

        # If the match is recent, track the surprisal (volatility)
        if date > RELEVANCE_CUTOFF:
            weight = calculate_recency_weight(date, LATEST_DATE)
            
            # 2. Home Team Volatility: (Actual - Expected)^2
            res_h_vol = (W_h - we_h)**2
            recent_residuals[h].append((weight, res_h_vol))
            
            # 3. Away Team Volatility: Surprisal is mirrored
            res_a_vol = ((1.0 - W_h) - (1.0 - we_h))**2
            recent_residuals[a].append((weight, res_a_vol))
        
        team_elo[h] = rh + change
        team_elo[a] = ra - change
        
        TEAM_HISTORY[h]['dates'].append(date); TEAM_HISTORY[h]['elo'].append(team_elo[h])
        TEAM_HISTORY[a]['dates'].append(date); TEAM_HISTORY[a]['elo'].append(team_elo[a])

    # Update Final Elos in Stats Dictionary
    for t in all_teams_set:
        TEAM_STATS[t]['elo'] = team_elo.get(t, INITIAL_RATING)

    # ----------------------------------------------------
    # PHASE 2: RECENT FORM & OPPONENT STRENGTH (Weighted)
    # ----------------------------------------------------
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

        weight = calculate_recency_weight(match_date, LATEST_DATE)

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

    # ----------------------------------------------------
    # PHASE 3: TIMING & PENALTIES
    # ----------------------------------------------------
    if scorers_df is not None:
        scorers_df['team'] = scorers_df['team'].str.lower().str.strip().replace(NAME_MAP)
        scorers_df['date'] = pd.to_datetime(scorers_df['date'])
        modern_scorers = scorers_df[scorers_df['date'] > RELEVANCE_CUTOFF]
        
        for _, row in modern_scorers.iterrows():
            t = row['team']
            if t in TEAM_STATS:
                TEAM_STATS[t]['total_goals_recorded'] += 1
                if row['penalty']: TEAM_STATS[t]['penalties'] += 1
                try:
                    minute = float(str(row['minute']).split('+')[0])
                    if minute <= 45: TEAM_STATS[t]['first_half'] += 1
                    if minute >= 75: TEAM_STATS[t]['late_goals'] += 1
                except: pass

    # --- CALCULATE GLOBAL ELO MEAN (Required for SOS) ---
    active_elos = [s['elo'] for s in TEAM_STATS.values()]
    GLOBAL_ELO_MEAN = sum(active_elos) / len(active_elos) if active_elos else 1500

    # ----------------------------------------------------
    # PHASE 4: FINALIZE (Weighted Math & Uncapped Elo)
    # ----------------------------------------------------
    TEAM_PROFILES = {}
    REGRESSION_DUMMY_GAMES = 10
    
    for t, s in TEAM_STATS.items():
        agg = team_recent_aggregates[t]
        
        # 1. Weighted Averages (Unchanged)
        denom = agg['eff_games'] + REGRESSION_DUMMY_GAMES
        numerator_gf = agg['gf'] + (REGRESSION_DUMMY_GAMES * avg_goals_global)
        numerator_ga = agg['ga'] + (REGRESSION_DUMMY_GAMES * avg_goals_global)
        
        raw_gf_avg = numerator_gf / denom
        raw_ga_avg = numerator_ga / denom
        s['gf_avg'] = raw_gf_avg
        s['ga_avg'] = raw_ga_avg 
        
        # 2. SOS Calculation
        if agg['eff_games'] > 0:
            avg_opp_elo = agg['opp_elo_sum'] / agg['eff_games']
        else:
            avg_opp_elo = GLOBAL_ELO_MEAN
            
        weighted_opp_elo = (avg_opp_elo * agg['eff_games'] + GLOBAL_ELO_MEAN * REGRESSION_DUMMY_GAMES) / denom
        difficulty_ratio = weighted_opp_elo / GLOBAL_ELO_MEAN
        
       # 3. Apply SOS to Stats
        # Offense: Power Boost (Higher is Better)
        off_log = np.log(raw_gf_avg / avg_goals_global)
        sos_weight_off = np.clip(difficulty_ratio, 0.85, 1.15)
        adjusted_off = np.exp(off_log * sos_weight_off)

        # Defense: Division Forgiveness (Lower is Better)
        sos_weight_def = difficulty_ratio ** 1.1 
        adjusted_def = (raw_ga_avg / avg_goals_global) / sos_weight_def

        # -----------------------------------------------------------
        # C. ELO BLENDING
        # -----------------------------------------------------------
        elo_ratio = s['elo'] / GLOBAL_ELO_MEAN
        # Power curve reduced to rein in dominant teams
        elo_off = elo_ratio ** 1.4 
        elo_def = 1.0 / (elo_ratio ** 1.2)
        
        elo_off = np.clip(elo_off, 0.4, 2.5)
        elo_def = np.clip(elo_def, 0.4, 2.5)

        elo_off_log = np.log(elo_off)
        elo_def_log = np.log(elo_def)

        STAT_WEIGHT = 0.60
        ELO_WEIGHT  = 0.40

        final_off_log = STAT_WEIGHT * np.log(adjusted_off) + ELO_WEIGHT * elo_off_log
        s['off'] = np.exp(final_off_log)

        final_def_log = STAT_WEIGHT * np.log(adjusted_def) + ELO_WEIGHT * elo_def_log
        s['def'] = np.exp(final_def_log)
        
        s['off'] = np.clip(s['off'], 0.4, 2.8)
        s['def'] = np.clip(s['def'], 0.4, 2.8)

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
        
        # -----------------------------------------------------------
        # E. ADVANCED STYLE LABEL (Data-Driven Logic)
        # -----------------------------------------------------------
        if t in ADVANCED_TEAM_DATA:
            d = ADVANCED_TEAM_DATA[t]
            t_type, poss, press, direct = d['type'], d['poss'], d['press'], d['dir']
            
            if t_type == 'Vertical Control':
                if poss >= 0.70: style = 'Ball Control'
                elif press >= 0.68: style = 'Fast Build-up'
                elif direct >= 0.58: style = 'Technical Play'
                else: style = 'Disciplined'
                
            elif t_type == 'Chaos & Intensity':
                if press >= 0.75: style = 'High Press'
                else: style = 'High Risk'
                
            elif t_type == 'Compact Block':
                if poss <= 0.38 and direct >= 0.75: style = 'Deep Block'
                else: style = 'Counter-Attack'
                
            elif t_type == 'Direct-Physical':
                style = 'Direct Play'
            else:
                style = 'Balanced'
                
        else:
            has_history = m >= 10 
            rel_gf = s['adj_gf'] / avg_goals_global
            rel_ga = s['adj_ga'] / avg_goals_global
            clean_sheets = s.get('cs_pct', 0)
            
            if has_history:
                if s['elo'] > 1850 and rel_ga < 0.85: style = "Ball Control"
                elif rel_gf > 1.30 and s['elo'] > 1750: style = "Technical Play"
                elif clean_sheets > 45: style = "Deep Block"
                elif rel_ga < 0.90 and rel_gf < 1.00: style = "Counter-Attack"
                elif rel_gf > 1.25 and rel_ga > 1.20: style = "High Risk"
                elif s.get('fh_pct', 0) > 55: style = "High Press"
                elif rel_ga > 1.10: style = "Direct Play"
                else: style = "Disciplined"
            else:
                style = "Balanced"

        if t in recent_residuals and recent_residuals[t]:
            num = sum(w * r for w, r in recent_residuals[t])
            den = sum(w for w, r in recent_residuals[t])
            s['volatility'] = np.clip(num / den, 0.05, 0.35)
        else:
            s['volatility'] = 0.15
        
        if t in TEAM_HISTORY and len(TEAM_HISTORY[t]['elo']) > 10:
            s['momentum'] = (TEAM_HISTORY[t]['elo'][-1] - TEAM_HISTORY[t]['elo'][-10]) / 100
        else:
            s['momentum'] = 0.0        

        TEAM_PROFILES[t] = style

    return TEAM_STATS, TEAM_PROFILES, avg_goals_global

# =============================================================================
# --- PART 3: SIMULATION ---
# =============================================================================
def calculate_confed_strength():
    """
    Calculates a 'Nerf' multiplier based on a Composite Score:
    50% Weight = Elite Strength (Top 3 Teams)
    50% Weight = Depth Strength (Average of the Top 50% of teams)
    
    This penalizes 'Top Heavy' regions where a few giants farm points 
    against weak depth.
    """
    global CONFED_MULTIPLIERS
    
    buckets = {c: [] for c in set(TEAM_CONFEDS.values())}
    for team, stats in TEAM_STATS.items():
        confed = TEAM_CONFEDS.get(team.lower(), 'OFC') 
        buckets[confed].append(stats['elo'])
        
    confed_scores = {}
    
    all_elos = sorted([s['elo'] for s in TEAM_STATS.values()], reverse=True)
    global_elite_avg = sum(all_elos[:10]) / 10

    for confed, elos in buckets.items():
        if not elos:
            confed_scores[confed] = 1000
            continue
            
        elos.sort(reverse=True)
        num_teams = len(elos)
        # --- DYNAMIC ELITE POOL ---
        # We take the square root of the number of teams to find the "Representative Elite"
        # UEFA (55) -> ~7 teams | CONMEBOL (10) -> ~3 teams | AFC (47) -> ~6 teams
        elite_count = max(2, int(math.sqrt(num_teams)))
        elite_avg = sum(elos[:elite_count]) / elite_count
        
        # --- DEPTH SCORE ---
        # How strong is the "Average" team you have to play in qualifying?
        # We take the top 50% to avoid being dragged down by tiny unranked nations
        depth_count = max(1, int(num_teams * 0.5))
        depth_avg = sum(elos[:depth_count]) / depth_count
        
        # --- DYNAMIC COMPOSITE ---
        # We weight the score: 60% Elite Strength, 40% Depth Strength
        composite = (elite_avg * 0.6) + (depth_avg * 0.4)
        
        # Bonus: The "Concentration Factor"
        # Small regions like CONMEBOL are "High Density" (fewer weak teams to farm)
        # Large regions like AFC are "Low Density" (many weak teams to farm)
        density_bonus = 1.0 + (1 / num_teams) # Small regions get a slight boost
        
        confed_scores[confed] = composite * density_bonus

    baseline = max(confed_scores.values())
    
    for confed, score in confed_scores.items():
        ratio = score / baseline
        # ratio**1.5 instead of 2.2 makes the nerf less aggressive
        CONFED_MULTIPLIERS[confed] = round(max(0.80, ratio**1.5), 3)

def sim_match(t1, t2, knockout=False):
    s1 = TEAM_STATS.get(t1, {'elo':1200, 'off':1.0, 'def':1.0})
    s2 = TEAM_STATS.get(t2, {'elo':1200, 'off':1.0, 'def':1.0})
    style1 = TEAM_PROFILES.get(t1, 'Balanced')
    style2 = TEAM_PROFILES.get(t2, 'Balanced')

    confed1 = TEAM_CONFEDS.get(t1, 'OFC')
    confed2 = TEAM_CONFEDS.get(t2, 'OFC')
    reg_mult1 = CONFED_MULTIPLIERS.get(confed1, 1.0)
    reg_mult2 = CONFED_MULTIPLIERS.get(confed2, 1.0)
    pedigree_gap = reg_mult1 - reg_mult2 
    
    dr = s1['elo'] - s2['elo']
    # Denominator tightened from 650 to 500 so odds don't explode for elites
    we1 = 1 / (10**(-dr/500) + 1)
    we2 = 1 - we1
    
    def get_archetype(style):
        if style in ['High-Intensity Chaos', 'Heavy Metal / Pressing', 'High Risk / Chaos', 'Fast Starters']: return 'chaos'
        if style in ['Organized Low-Block', 'Tactical Pragmatism', 'Defensive Wall', 'Control / Disciplined']: return 'pragmatic'
        if style in ['Positional Dominance', 'Vertical Tiki-Taka', 'Elite / Dominant']: return 'possession'
        if style in ['Fluid Creativity', 'Strong Attack']: return 'fluid'
        if style in ['Physical Direct', 'Set-Piece Reliant', 'Late Surge']: return 'direct'
        return 'balanced'

    arc1, arc2 = get_archetype(style1), get_archetype(style2)

    # 4. INITIALIZE MODIFIERS
    t1_atk_mod, t1_def_mod = 1.0, 1.0
    t2_atk_mod, t2_def_mod = 1.0, 1.0
    pace_mod = 1.0

    # 5. DYNAMIC COMPLEXITY & ELO SCALING (Continuous Interpolation)
    def apply_complexity(elo, style):
        # We scale between the absolute floor (Curaçao at ~1250) and ceiling (Spain at ~2000)
        # np.interp(elo, [1200, 1900],[multiplier_at_1200, multiplier_at_2000])
        if style == 'Ball Control':
            # Buffed: Elites now reach 1.20x atk instead of 1.10x
            atk = np.interp(elo, [1200, 2000], [0.90, 1.20])
            dfe = np.interp(elo, [1200, 2000], [0.85, 1.15])
        elif style == 'Technical Play':
            # Buffed: Ceiling raised for individual brilliance
            atk = np.interp(elo, [1200, 2000], [0.95, 1.25])
            dfe = np.interp(elo, [1200, 2000], [0.90, 1.10])
        elif style == 'High Press':
            atk = np.interp(elo, [1200, 1900], [0.85, 1.10])
            dfe = np.interp(elo, [1200, 1900], [0.80, 1.05])
        elif style == 'Fast Build-up':
            atk = np.interp(elo, [1200, 1900], [0.85, 1.08])
            dfe = np.interp(elo, [1200, 1900], [0.85, 1.02])
        elif style == 'Disciplined':
            atk = np.interp(elo, [1200, 1900], [0.95, 1.05])
            dfe = np.interp(elo, [1200, 1900], [1.02, 1.12])
        elif style == 'Counter-Attack':
            atk = np.interp(elo, [1200, 1900], [0.95, 0.88])
            dfe = np.interp(elo, [1200, 1900], [1.15, 1.02])
        elif style == 'Deep Block':
            # Def lowered from 1.20 to 1.10. It's an advantage, but not a cheat code.
            atk = np.interp(elo, [1200, 1900], [0.90, 0.80])
            dfe = np.interp(elo, [1200, 1900], [1.10, 1.05])
        elif style == 'Direct Play':
            atk = np.interp(elo, [1200, 1900], [1.08, 0.92])
            dfe = np.interp(elo, [1200, 1900], [1.05, 0.96])
        elif style == 'High Risk':
            atk = np.interp(elo, [1200, 1900], [1.05, 1.15])
            dfe = np.interp(elo, [1200, 1900], [0.75, 0.88])
        else: 
            atk, dfe = 1.0, 1.0

        return float(atk), float(dfe)

    c1_a, c1_d = apply_complexity(s1['elo'], style1)
    c2_a, c2_d = apply_complexity(s2['elo'], style2)
    t1_atk_mod *= c1_a; t1_def_mod *= c1_d
    t2_atk_mod *= c2_a; t2_def_mod *= c2_d

    # 6. HISTORICAL TACTICAL MATCHUPS (The Matrix)
    # Automatically looks up if either team has a structural advantage.
    # Defaults to 1.0 (neutral) if there is no specific historical counter.

    t1_tactical_edge = STYLE_MATCHUPS.get((style1, style2), 1.0)
    t2_tactical_edge = STYLE_MATCHUPS.get((style2, style1), 1.0)
    
    t1_atk_mod *= t1_tactical_edge
    t2_atk_mod *= t2_tactical_edge

    # 7. GAME PACE & DAVID-VS-GOLIATH
    # Open games speed up the pace (more chances for both)
    open_styles =['High Risk', 'High Press', 'Technical Play', 'Fast Build-up']
    slow_styles =['Deep Block', 'Counter-Attack', 'Disciplined']
    
    if style1 in open_styles and style2 in open_styles: 
        pace_mod = 1.15 
    elif style1 in slow_styles and style2 in slow_styles: 
        pace_mod = 0.85 

    # Underdog "Park the Bus" desperation 
    # If a defensive team is playing a massive favorite, they bunker even harder.    
    if style1 in slow_styles and dr < -150: t1_def_mod *= 1.10 
    if style2 in slow_styles and dr > 150: t2_def_mod *= 1.10


    # 8. MOMENTUM (Replaces old Form Hack)
    # Scale momentum safely so it doesn't break multipliers
    mom1_adj = np.clip(1.0 + (s1.get('momentum', 0) * 0.10), 0.90, 1.10)
    mom2_adj = np.clip(1.0 + (s2.get('momentum', 0) * 0.10), 0.90, 1.10)

    bus1, bus2 = 1.0, 1.0
    if dr > 300: 
        bus2, bus1 = 0.65, 0.90
    elif dr < -300:
        bus1, bus2 = 0.65, 0.90
        
    # 10. BRINGING IT ALL TOGETHER
    class1 = 1.0 + (we1 - 0.5) * 0.12 
    class2 = 1.0 + (we2 - 0.5) * 0.12
    ped1 = 1.0 + (pedigree_gap * 0.15)
    ped2 = 1.0 - (pedigree_gap * 0.15)
    
    # Normalized host advantages
    h1 = 1.15 if t1 in ['united states', 'mexico', 'canada'] else (1.05 if confed1 == 'CONCACAF' else 1.0)
    h2 = 1.15 if t2 in ['united states', 'mexico', 'canada'] else (1.05 if confed2 == 'CONCACAF' else 1.0)

    if t1 in ['united states', 'mexico', 'canada']: t1_def_mod *= 1.08
    if t2 in ['united states', 'mexico', 'canada']: t2_def_mod *= 1.08

    m1_base = (s1['off'] * s2['def']) * class1 * ped1 * bus1 * mom1_adj
    m2_base = (s2['off'] * s1['def']) * class2 * ped2 * bus2 * mom2_adj
    
    # 11. ELASTIC LIMITER (Replaces hard 'compress')
    vol1, vol2 = s1.get('volatility', 0.15), s2.get('volatility', 0.15)
    total_chaos = (vol1 + vol2)

    def elastic_limit(val, chaos):
        # Raised ceiling to 2.1x: Favorites are allowed to be dominant again.
        ceiling = 2.1 + (chaos * 1.5) 
        return val if val <= ceiling else ceiling + np.log(val - (ceiling - 1)) * (1.0 + chaos)

    intensity = 1.15 if knockout else 1.0

    lam1 = AVG_GOALS * elastic_limit(m1_base, total_chaos) * h1 * intensity * pace_mod * t1_atk_mod * (2.0 - t2_def_mod)
    lam2 = AVG_GOALS * elastic_limit(m2_base, total_chaos) * h2 * intensity * pace_mod * t2_atk_mod * (2.0 - t1_def_mod)

    # 12. GOAL ROLLING (Variance Injection via Volatility)
    def roll_goals(lam, v, ko_exp_weighted):
        # Reduced variance: Multiplying volatility (v) by 0.4 
        # This prevents the "Lambda" from swinging wildly into upset territory.
        composure = np.clip(1.0 - (ko_exp_weighted * 0.05), 0.85, 1.0)
        realized_lam = np.random.normal(lam, lam * (v * 0.4 * composure))
        return np.random.poisson(max(0.1, realized_lam))

    # Apply it (Removed undefined fatigue variables)
    ko1 = s1.get('ko_exp_weighted', 0)
    ko2 = s2.get('ko_exp_weighted', 0)
    g1 = roll_goals(lam1, vol1, ko1)
    g2 = roll_goals(lam2, vol2, ko2)
    
    if g1 > g2: return (t1, g1, g2, 'reg') if knockout else (t1, g1, g2)
    if g2 > g1: return (t2, g1, g2, 'reg') if knockout else (t2, g1, g2)
    if not knockout: return 'draw', g1, g2

    g1 += np.random.poisson(lam1 * 0.4)
    g2 += np.random.poisson(lam2 * 0.4)
    if g1 > g2: return t1, g1, g2, 'aet'
    if g2 > g1: return t2, g1, g2, 'aet'
    
    p1_b = 0.08 if style1 in ['Set-Piece Reliant', 'Control / Disciplined', 'Tactical Pragmatism'] else 0
    p2_b = 0.08 if style2 in ['Set-Piece Reliant', 'Control / Disciplined', 'Tactical Pragmatism'] else 0
    win_chance = np.clip(0.5 + (dr/2000) + (p1_b - p2_b), 0.30, 0.70)
    winner = t1 if random.random() < win_chance else t2
    return winner, g1, g2, 'pks'

def run_simulation(verbose=False, quiet=False, fast_mode=False, finalized_slots=None):
    structured_groups = {} if not fast_mode else None
    structured_bracket = [] if not fast_mode else None
    group_matches_log = {} if not fast_mode else None

    # --- 0. PRE-TOURNAMENT QUALIFIERS ---
    # Use finalized playoff results (actual 2026 qualifiers)
    # If custom slots provided, use those; otherwise use FINALIZED_SLOTS
    if finalized_slots is None:
        slots = FINALIZED_SLOTS.copy()
    else:
        slots = finalized_slots

    groups = {
        'A': ['mexico', 'south africa', 'south korea', slots['Path D']],
        'B': ['canada', 'switzerland', 'qatar', slots['Path A']],
        'C': ['brazil', 'morocco', 'haiti', 'scotland'],
        'D':['united states', 'paraguay', 'australia', slots['Path C']],
        'E':['germany', 'curaçao', 'ivory coast', 'ecuador'],
        'F':['netherlands', 'japan', 'tunisia', slots['Path B']],
        'G':['belgium', 'egypt', 'iran', 'new zealand'],
        'H':['spain', 'cape verde', 'saudi arabia', 'uruguay'],
        'I': ['france', 'senegal', 'norway', slots['ICP2']],
        'J':['argentina', 'algeria', 'austria', 'jordan'],
        'K': ['portugal', 'uzbekistan', 'colombia', slots['ICP1']],
        'L': ['england', 'croatia', 'ghana', 'panama']
    }
    
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
        (get_t('G', 1), get_t('J', 1)),      
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
    
    # --- 3. KNOCKOUT SIMULATION ---
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
            
            # Simulate 3rd Place Match
            t3_1, t3_2 = semi_losers[0], semi_losers[1]
            w_3rd, g3_1, g3_2, method_3rd = sim_match(t3_1, t3_2, knockout=True)
            third_place_winner = w_3rd 
            
            if not fast_mode:
                structured_bracket.append({'round': 'Third Place Play-off', 'matches': [{
                    't1': t3_1, 't2': t3_2, 'g1': g3_1, 'g2': g3_2, 'winner': w_3rd, 'method': method_3rd
                }]})

        if not fast_mode:
            structured_bracket.append({'round': r_name, 'matches': round_matches_log})
        
         # Prepare next round pairings (Winner Match 1 vs Winner Match 2)
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
    results_df, _, _ = load_data()
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