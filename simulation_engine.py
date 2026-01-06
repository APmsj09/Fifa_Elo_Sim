import pandas as pd
import numpy as np
import random
import math
import js
from pyodide.http import open_url

# =============================================================================
# --- PART 1: SETUP & DATA LOADING ---
# =============================================================================

DATA_DIR = "." 

# Global Vars
TEAM_STATS = {}
TEAM_PROFILES = {}
TEAM_HISTORY = {}
AVG_GOALS = 2.5
STYLE_MATRIX = {
    ('Star-Centric', 'Balanced'): 1.05,
    ('Balanced', 'Star-Centric'): 1.0,
    ('Endurance', 'Fast-Paced'): 1.1, 
    ('Aggressive', 'Star-Centric'): 1.05,
    ('Fast-Paced', 'Aggressive'): 1.1
}

# This includes the 40 fixed teams + all potential qualifier teams
# Updated to match YOUR results.csv exactly
WC_TEAMS = [
    # Fixed Group Teams
    'mexico', 'south africa', 'south korea', # Matches CSV
    'canada', 'switzerland', 'qatar', 
    'brazil', 'morocco', 'haiti', 'scotland', 
    'united states', # FIXED: CSV uses 'United States', not 'USA'
    'paraguay', 'australia', 
    'germany', 'curaçao', # FIXED: CSV uses special character 'ç'
    'ivory coast', 'ecuador', # Matches CSV
    'netherlands', 'japan', 'tunisia', 
    'belgium', 'egypt', 'iran', 'new zealand', 
    'spain', 'cape verde', 'saudi arabia', 'uruguay', 
    'france', 'senegal', 'norway', 
    'argentina', 'algeria', 'austria', 'jordan', 
    'portugal', 'uzbekistan', 'colombia', 
    'england', 'croatia', 'ghana', 'panama',
    
    # Potential Qualifiers (UEFA Paths)
    'italy', 'northern ireland', 'wales', 'bosnia and herzegovina',
    'ukraine', 'sweden', 'poland', 'albania',
    'turkey', 'romania', 'slovakia', 'kosovo',
    'czech republic', 'republic of ireland', 'denmark', 'north macedonia',
    
    # Potential Qualifiers (Inter-Confederation)
    'dr congo', 'new caledonia', 'jamaica',
    'bolivia', 'suriname', 'iraq'
]

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

def load_data():
    """
    Loads data assuming all files are now standard CSVs.
    """
    try:
        # Note: If using PyScript, ensure files are fetched to virtual FS first
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

def get_k_factor(tourney, goal_diff):
    """
    Determines the weight of the match based on tournament importance
    and margin of victory.
    """
    t_str = str(tourney)
    k = 25 # Default
    
    # --- TIER 0: FRIENDLIES ---
    if t_str == 'Friendly':
        k = 15

    # --- TIER 1: WORLD CUP ---
    elif 'World Cup' in t_str and 'qualification' not in t_str:
        k = 60
        
    # --- TIER 2: CONTINENTAL FINALS ---
    elif any(x in t_str for x in [
        'Copa América', 'UEFA Euro', 'African Cup of Nations', 
        'Asian Cup', 'Gold Cup', 'CONCACAF Championship', 
        'Oceania Nations Cup'
    ]) and 'qualification' not in t_str:
        k = 50
        
    # --- TIER 3: QUALIFIERS & OFFICIAL ---
    elif any(x in t_str for x in [
        'qualification', 'Nations League', 'Confederations Cup', 
        'Arab Cup', 'Gulf Cup'
    ]):
        k = 40
        
    # --- TIER 4: REGIONAL ---
    elif any(x in t_str for x in [
        'AFF Championship', 'ASEAN', 'EAFF', 'Caribbean Cup', 
        'UNCAF', 'COSAFA', 'SAFF', 'WAFF'
    ]):
        k = 30

    # --- MARGIN MULTIPLIER ---
    # Rewards dominant wins
    if goal_diff == 2: k *= 1.5
    elif goal_diff == 3: k *= 1.75
    elif goal_diff >= 4: k *= (1.75 + (goal_diff-3)/8)
    
    return k

def initialize_engine():
    # Load DataFrames
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
    # PHASE 1: CUSTOM ELO CALCULATION
    # ----------------------------------------------------
    team_elo = {}
    INITIAL_RATING = 1200
    global TEAM_HISTORY
    TEAM_HISTORY = {} 
    
    # Init master stats container
    global TEAM_STATS
    TEAM_STATS = {}

    matches_data = zip(elo_df['home_team'], elo_df['away_team'], 
                       elo_df['home_score'], elo_df['away_score'], 
                       elo_df['tournament'], elo_df['neutral'], elo_df['date'])
    
    for h, a, hs, as_, tourney, neutral, date in matches_data:
        rh = team_elo.get(h, INITIAL_RATING)
        ra = team_elo.get(a, INITIAL_RATING)
        
        # Init history
        if h not in TEAM_HISTORY: TEAM_HISTORY[h] = {'dates': [], 'elo': []}
        if a not in TEAM_HISTORY: TEAM_HISTORY[a] = {'dates': [], 'elo': []}
        
        # Elo Math
        dr = rh - ra + (100 if not neutral else 0)
        we = 1 / (10**(-dr/600) + 1)
        
        if hs > as_: W = 1
        elif as_ > hs: W = 0
        else: W = 0.5
        
        # K-Factor
        gd = abs(hs - as_)
        k = get_k_factor(tourney, gd) # Uses your custom helper
    
        # Apply Change
        change = k * (W - we)
        team_elo[h] = rh + change
        team_elo[a] = ra - change
        
        TEAM_HISTORY[h]['dates'].append(date); TEAM_HISTORY[h]['elo'].append(team_elo[h])
        TEAM_HISTORY[a]['dates'].append(date); TEAM_HISTORY[a]['elo'].append(team_elo[a])

    # Transfer Elo to TEAM_STATS
    all_teams = set(team_elo.keys())
    for t in all_teams:
        TEAM_STATS[t] = {
            'elo': team_elo[t],
            # Initialize other fields to avoid KeyErrors later
            'gf_avg': 0, 'ga_avg': 0, 'off': 1.0, 'def': 1.0,
            'matches': 0, 'clean_sheets': 0, 'btts': 0, 
            'penalties': 0, 'first_half': 0, 'late_goals': 0, 'total_goals_recorded': 0,
            'form': [] # List to hold recent results for string generation
        }

    # ----------------------------------------------------
    # PHASE 2: RECENT FORM & STATS (Post-2022)
    # ----------------------------------------------------
    RELEVANCE_CUTOFF = '2022-01-01'
    recent_df = elo_df[elo_df['date'] > RELEVANCE_CUTOFF]
    
    # Calculate Global Average for Normalization (Required for off/def)
    if len(recent_df) > 0:
        avg_goals_global = (recent_df['home_score'].mean() + recent_df['away_score'].mean()) / 2
    else:
        avg_goals_global = 1.25

    team_recent_aggregates = {t: {'gf':0, 'ga':0, 'games':0} for t in all_teams}
    
    for _, row in recent_df.iterrows():
        h, a = row['home_team'], row['away_team']
        hs, as_ = row['home_score'], row['away_score']
        
        # 1. Update Form (W/D/L)
        if h in TEAM_STATS:
            res = 'W' if hs > as_ else ('L' if hs < as_ else 'D')
            TEAM_STATS[h]['form'].append(res)
        
        if a in TEAM_STATS:
            res = 'W' if as_ > hs else ('L' if as_ < hs else 'D')
            TEAM_STATS[a]['form'].append(res)

        # 2. Track Stats
        if h in TEAM_STATS: 
            TEAM_STATS[h]['matches'] += 1
            team_recent_aggregates[h]['gf'] += hs; team_recent_aggregates[h]['ga'] += as_; team_recent_aggregates[h]['games'] += 1
            if as_ == 0: TEAM_STATS[h]['clean_sheets'] += 1
            if hs > 0 and as_ > 0: TEAM_STATS[h]['btts'] += 1
            
        if a in TEAM_STATS: 
            TEAM_STATS[a]['matches'] += 1
            team_recent_aggregates[a]['gf'] += as_; team_recent_aggregates[a]['ga'] += hs; team_recent_aggregates[a]['games'] += 1
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

    # ----------------------------------------------------
    # PHASE 4: FINALIZE (Calc Averages & Form String)
    # ----------------------------------------------------
    TEAM_PROFILES = {}
    
    for t, s in TEAM_STATS.items():
        # A. Calculate Averages (Recent)
        agg = team_recent_aggregates[t]
        if agg['games'] > 0:
            s['gf_avg'] = agg['gf'] / agg['games']
            s['ga_avg'] = agg['ga'] / agg['games']
        else:
            s['gf_avg'] = 1.0; s['ga_avg'] = 1.0
            
        # B. Normalize for Engine (Required for run_simulation)
        s['off'] = s['gf_avg'] / avg_goals_global
        s['def'] = s['ga_avg'] / avg_goals_global

        # C. Form String (Take last 5)
        recent_form = s['form'][-5:] 
        s['form'] = "".join(recent_form) if recent_form else "-----"

        # D. Percentages for Dashboard
        m = s['matches']
        g = s['total_goals_recorded']
        
        s['cs_pct'] = (s['clean_sheets'] / m * 100) if m > 0 else 0
        s['btts_pct'] = (s['btts'] / m * 100) if m > 0 else 0
        s['pen_pct'] = (s['penalties'] / g * 100) if g > 0 else 0
        s['fh_pct'] = (s['first_half'] / g * 100) if g > 0 else 0
        s['late_pct'] = (s['late_goals'] / g * 100) if g > 0 else 0
        
        # E. Advanced Style Label (Simplified for Clarity)
        
        # 1. "ELITE" COMBINATIONS (The best of the best)
        if s['gf_avg'] > 2.2 and s['cs_pct'] > 50:
            style = "Dominant"              # Elite Attack + Elite Defense (e.g. Prime Brazil)
        elif s['late_pct'] > 30 and s['cs_pct'] > 45:
            style = "Resilient"             # Good defense + Wins games late (e.g. Real Madrid)
            
        # 2. "CHAOS" COMBINATIONS (High Event)
        elif s['gf_avg'] > 2.0 and s['ga_avg'] > 1.5:
            style = "High Risk / Reward"    # Scores a lot, but defense leaks (e.g. Germany 2024)
        elif s['btts_pct'] > 65 and s['late_pct'] > 30:
            style = "Late Drama"            # Chaotic games usually decided in final minutes
            
        # 3. "CONTROL" COMBINATIONS (Low Event)
        elif s['gf_avg'] < 1.0 and s['cs_pct'] > 45:
            style = "Defensive Wall"        # Can't score much, but refuses to concede (e.g. Morocco)
        elif s['btts_pct'] < 30 and s['ga_avg'] < 1.0:
            style = "Disciplined"           # Very organized, boring low-scoring wins
            
        # 4. "TIMING" SPECIALISTS
        elif s['fh_pct'] > 60 and s['gf_avg'] > 1.5:
            style = "Aggressive Starter"    # Blitzes opponents early to take control
        elif s['pen_pct'] > 20 and s['gf_avg'] < 1.5:
            style = "Set-Piece Reliant"     # Struggles in open play, relies on fouls/corners
            
        # 5. FALLBACKS (Single Stat Dominance)
        elif s['gf_avg'] > 2.0: style = "Strong Attack"
        elif s['cs_pct'] > 45:  style = "Solid Defense"
        elif s['btts_pct'] > 60: style = "Open Games"
        elif s['gf_avg'] < 1.0: style = "Low Scoring"
        
        else:
            style = "Balanced"
        
        TEAM_PROFILES[t] = style

    return TEAM_STATS, TEAM_PROFILES, avg_goals_global

# =============================================================================
# --- PART 3: SIMULATION ---
# =============================================================================

import statistics

def calculate_confed_strength():
    """
    Calculates a 'Nerf' multiplier based on a Composite Score:
    50% Weight = Elite Strength (Top 3 Teams)
    50% Weight = Depth Strength (Average of the Top 50% of teams)
    
    This penalizes 'Top Heavy' regions where a few giants farm points 
    against weak depth.
    """
    global CONFED_MULTIPLIERS
    
    # 1. Bucket teams by Confed
    buckets = {c: [] for c in set(TEAM_CONFEDS.values())}
    
    for team, stats in TEAM_STATS.items():
        confed = TEAM_CONFEDS.get(team, 'OFC') 
        buckets[confed].append(stats['elo'])
        
    # 2. Calculate Composite Scores
    confed_scores = {}
    
    for confed, elos in buckets.items():
        if not elos:
            confed_scores[confed] = 1000
            continue
            
        # Sort Rating Descending (High to Low)
        elos.sort(reverse=True)
        count = len(elos)
        
        # A. Elite Score (Top 3)
        # We focus on the absolute best who represent the region in the World Cup
        elite_count = min(3, count)
        elite_avg = sum(elos[:elite_count]) / elite_count
        
        # B. Depth Score (Top 50%)
        # We look at the upper half of the table. 
        # If the mid-table is weak, this score drops.
        depth_count = max(1, int(count * 0.5))
        depth_avg = sum(elos[:depth_count]) / depth_count
        
        # C. Composite (50/50 Split)
        # You can tweak weights: 0.7/0.3 if you prefer favoring top teams.
        composite = (elite_avg * 0.6) + (depth_avg * 0.4)
        confed_scores[confed] = composite
        
        js.console.error(f"Region {confed}: Elite={int(elite_avg)}, Depth={int(depth_avg)} -> Score={int(composite)}")

    # 3. Normalize against the best region
    baseline = max(confed_scores.values()) if confed_scores else 1800
    
    js.console.error("\n--- DYNAMIC REGIONAL MULTIPLIERS ---")
    for confed, score in confed_scores.items():
        # Calculate ratio
        ratio = score / baseline
        
        # Apply a 'Curve' to prevent minimal differences from punishing too hard
        # e.g., if ratio is 0.95, we might treat it as 0.98
        # But if it's 0.70, it stays 0.70.
        # We'll use a simple root curve: ratio^(0.5) roughly pushes 0.8 -> 0.9
        # But for 'Top Heavy' accountability, a linear ratio is often fairer.
        
        CONFED_MULTIPLIERS[confed] = round(ratio, 3)
        js.console.error(f"{confed}: {CONFED_MULTIPLIERS[confed]} (Based on score {int(score)})")

def sim_match(t1, t2, knockout=False):
    
    s1 = TEAM_STATS.get(t1, {'elo':1200, 'off':1.0, 'def':1.0})
    s2 = TEAM_STATS.get(t2, {'elo':1200, 'off':1.0, 'def':1.0})
    
    dr = s1['elo'] - s2['elo']
    we = 1 / (10**(-dr/600) + 1)
    
    style1 = TEAM_PROFILES.get(t1, 'Balanced')
    style2 = TEAM_PROFILES.get(t2, 'Balanced')
    
    # Style modifiers
    mod1 = STYLE_MATRIX.get((style1, style2), 1.0)
    mod2 = STYLE_MATRIX.get((style2, style1), 1.0)
    
    elo_scale = 1 + (we - 0.5)

    # GET CONFEDERATIONS
    c1 = TEAM_CONFEDS.get(t1, 'OFC')
    c2 = TEAM_CONFEDS.get(t2, 'OFC')
    
    # GET DYNAMIC MULTIPLIERS
    # Default to 0.8 if something goes wrong, but usually it's calculated
    tier1 = CONFED_MULTIPLIERS.get(c1, 0.8)
    tier2 = CONFED_MULTIPLIERS.get(c2, 0.8)
    
    # Home Advantage
    hosts = ['united states', 'mexico', 'canada']
    home_boost = 1.15 if t1 in hosts else 1.0
    away_boost = 1.15 if t2 in hosts else 1.0

    # 1. REGULAR TIME (90 Mins)
    lam1 = AVG_GOALS * s1['off'] * s2['def'] * elo_scale * mod1 * home_boost * tier1
    lam2 = AVG_GOALS * s2['off'] * s1['def'] * (2 - elo_scale) * mod2 * away_boost * tier2
    
    g1 = np.random.poisson(lam1)
    g2 = np.random.poisson(lam2)
    
    # Check Result
    if g1 > g2: 
        if knockout: return t1, g1, g2, 'reg'
        return t1, g1, g2
    elif g2 > g1: 
        if knockout: return t2, g1, g2, 'reg'
        return t2, g1, g2
    else:
        # IT IS A DRAW
        if not knockout:
            return 'draw', g1, g2
            
        # 2. EXTRA TIME (30 Mins) if Knockout
        # ET is approx 1/3 the length of regular time, often tighter defensively
        et_scale = 0.33 
        
        # We re-roll goals for the extra period
        g1_et = np.random.poisson(lam1 * et_scale)
        g2_et = np.random.poisson(lam2 * et_scale)
        
        # Add ET goals to total score
        g1 += g1_et
        g2 += g2_et
        
        if g1 > g2:
            return t1, g1, g2, 'aet' # After Extra Time
        elif g2 > g1:
            return t2, g1, g2, 'aet'
            
        # 3. PENALTIES (Only if still tied)
        p1_bonus = 0.1 if style1 == 'Dark Arts' else 0
        p2_bonus = 0.1 if style2 == 'Dark Arts' else 0
        
        # Higher Elo has slight mental edge + style bonus
        pk_prob = 0.5 + (dr/4000) + (p1_bonus - p2_bonus)
        winner = t1 if random.random() < pk_prob else t2
        
        return winner, g1, g2, 'pks'

def run_simulation(verbose=False, quiet=False, fast_mode=False):
    # Data containers
    structured_groups = {} if not fast_mode else None
    structured_bracket = [] if not fast_mode else None
    group_matches_log = {} if not fast_mode else None

    # --- 0. PRE-TOURNAMENT QUALIFIERS ---
    slots = {}
    uefa_paths = {
        'Path A': [('italy', 'northern ireland'), ('wales', 'bosnia and herzegovina')],
        'Path B': [('ukraine', 'sweden'), ('poland', 'albania')],
        'Path C': [('turkey', 'romania'), ('slovakia', 'kosovo')],
        'Path D': [('czech republic', 'republic of ireland'), ('denmark', 'north macedonia')]
    }
    
    for path, semis in uefa_paths.items():
        finalists = []
        for t1, t2 in semis:
            w, _, _, _ = sim_match(t1, t2, knockout=True)
            finalists.append(w)
        w_final, _, _, _ = sim_match(finalists[0], finalists[1], knockout=True)
        slots[path] = w_final

    w_ofc, _, _, _ = sim_match('dr congo', 'new caledonia', knockout=True)
    w_icp1, _, _, _ = sim_match('jamaica', w_ofc, knockout=True)
    slots['ICP1'] = w_icp1
    
    w_conmebol, _, _, _ = sim_match('bolivia', 'suriname', knockout=True)
    w_icp2, _, _, _ = sim_match('iraq', w_conmebol, knockout=True)
    slots['ICP2'] = w_icp2

    # --- 1. GROUP STAGE ---
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
    
    group_results_lists = {}
    third_place = []
    
    for grp, teams in groups.items():
        table_stats = {t: {'p':0, 'gd':0, 'gf':0, 'w':0, 'd':0, 'l':0} for t in teams}
        
        if not fast_mode: group_matches_log[grp] = []

        for i in range(len(teams)):
            for j in range(i+1, len(teams)):
                t1, t2 = teams[i], teams[j]
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

        sorted_teams = sorted(teams, key=lambda t: (table_stats[t]['p'], table_stats[t]['gd'], table_stats[t]['gf']), reverse=True)
        group_results_lists[grp] = sorted_teams
        third_place.append({'team': sorted_teams[2], 'stats': table_stats[sorted_teams[2]]})

        if not fast_mode:
            structured_groups[grp] = []
            for t in sorted_teams:
                structured_groups[grp].append({'team': t, **table_stats[t]})

    # --- 2. KNOCKOUT PREP (FIXED BRACKET) ---
    # Helper to get team by group position (0=1st, 1=2nd)
    def get_t(grp, pos):
        return group_results_lists[grp][pos]

    # Get the 8 Best 3rd Place Teams
    best_3rds = sorted(third_place, key=lambda x: (x['stats']['p'], x['stats']['gd'], x['stats']['gf']), reverse=True)[:8]
    t3 = [x['team'] for x in best_3rds] # List of just the names

    # Hard-Coded Bracket: Round of 32 (16 Matches)
    # This structure ensures 1st place teams play 3rds or 2nds, and pathways don't overlap until deep in tourney.
    # The order is: Match 1 plays Match 2 in next round, Match 3 plays Match 4, etc.

    bracket_matchups = [
        # --- SECTION 1 ---
        (get_t('A', 0), t3[0]),       # 1. 1A vs Best 3rd
        (get_t('B', 1), get_t('C', 1)), # 2. 2B vs 2C
        
        (get_t('D', 0), t3[1]),       # 3. 1D vs 2nd Best 3rd
        (get_t('E', 1), get_t('F', 1)), # 4. 2E vs 2F
        
        # --- SECTION 2 ---
        (get_t('G', 0), t3[2]),       # 5. 1G vs 3rd
        (get_t('H', 1), get_t('I', 1)), # 6. 2H vs 2I
        
        (get_t('J', 0), t3[3]),       # 7. 1J vs 3rd
        (get_t('K', 1), get_t('L', 1)), # 8. 2K vs 2L
        
        # --- SECTION 3 (Other Side of Bracket) ---
        (get_t('B', 0), t3[4]),       # 9. 1B vs 3rd
        (get_t('A', 1), get_t('D', 1)), # 10. 2A vs 2D (Runners up clash)
        
        (get_t('E', 0), t3[5]),       # 11. 1E vs 3rd
        (get_t('C', 0), get_t('G', 1)), # 12. 1C vs 2G
        
        # --- SECTION 4 ---
        (get_t('H', 0), t3[6]),       # 13. 1H vs 3rd
        (get_t('F', 0), get_t('J', 1)), # 14. 1F vs 2J

        (get_t('K', 0), t3[7]),       # 15. 1K vs 3rd
        (get_t('L', 0), get_t('I', 0)), # 16. 1L vs 1I (Titans clash early)
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
        
        # USE THE EXACT SAME LOGIC HERE
        gd = abs(hs - as_)
        k = get_k_factor(row['tournament'], gd)
        
        dr = rh - ra + (100 if not row['neutral'] else 0)
        we = 1 / (10**(-dr/600) + 1)
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