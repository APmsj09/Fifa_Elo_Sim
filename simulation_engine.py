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
    ('Defensive Wall', 'Strong Attack'): 1.10,    # Wall absorbs pure attack
    ('High Risk / Reward', 'Defensive Wall'): 1.10, # Chaos breaks the wall
    ('Disciplined', 'High Risk / Reward'): 1.10,  # Discipline punishes chaos
    ('Aggressive Starter', 'Late Drama'): 1.05,   # Early lead kills late momentum
    ('Late Drama', 'Disciplined'): 1.08,          # Late surge breaks discipline
    ('Set-Piece Reliant', 'Solid Defense'): 1.08, # Set pieces bypass solid defense
    ('Dominant', 'Balanced'): 1.05,               # Dominant crushes balanced
    ('Dominant', 'High Risk / Reward'): 1.10      # Dominant exploits risky teams
}

# This includes the 40 fixed teams + all potential qualifier teams
# Updated to match YOUR results.csv exactly
WC_TEAMS = [
    # Fixed Group Teams
    'mexico', 'south africa', 'south korea', # Matches CSV
    'canada', 'switzerland', 'qatar', 
    'brazil', 'morocco', 'haiti', 'scotland', 
    'united states',
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

def get_k_factor(tourney, goal_diff, home_team, away_team):
    """
    Determines match weight based on tournament importance,
    margin of victory, and regional strength.
    Adapted for the specific dataset provided.
    """
    t_str = str(tourney)
    
    # --- CONFEDERATION LOOKUP (Unchanged) ---
    tier_map = {
        'UEFA': 1.0, 'CONMEBOL': 1.0, 
        'CAF': 0.9, 
        'AFC': 0.8, 'CONCACAF': 0.8, 
        'OFC': 0.7
    }
    
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
    if any(x in t_str for x in [
        'CONIFA', 'VIVA', 'Island Games', 'Wild Cup', 'ELF Cup', 
        'FIFI', 'Inter Games', 'Coupe de l\'Outre-Mer', 'Unity Cup'
    ]):
        return 5 # Negligible impact

    # =========================================================
    # TIER 0: FRIENDLIES & MINOR INVITATIONALS
    # =========================================================
    # Catch specific friendly tournament names from your list
    if any(x in t_str for x in [
        'Friendly', 'FIFA Series', 'Kirin', 'King\'s Cup', 'Merdeka', 
        'Nehru', 'China Cup', 'Bangabandhu', 'Four Nations', 'Mundialito',
        'Lunar New Year', 'Tournoi de France'
    ]):
        k = 15

    # =========================================================
    # TIER 1: WORLD CUP FINALS
    # =========================================================
    elif 'World Cup' in t_str and 'qualification' not in t_str:
        k = 65
        
    # =========================================================
    # TIER 2: CONTINENTAL MAJORS (FINALS)
    # =========================================================
    elif any(x in t_str for x in [
        'Copa América', 'UEFA Euro', 'African Cup of Nations', 
        'Asian Cup', 'Gold Cup', 'CONCACAF Championship', 
        'Oceania Nations Cup', 'CONMEBOL–UEFA Cup of Champions'
    ]) and 'qualification' not in t_str:
        k = 50
        
    # =========================================================
    # TIER 3: QUALIFIERS & MAJOR OFFICIAL (Weighted by Region)
    # =========================================================
    elif any(x in t_str for x in [
        'qualification', 'Nations League', 'Confederations Cup', 
        'Arab Cup', 'Gulf Cup'
    ]):
        # "qualification" catches: World Cup, Euro, Asian Cup, Gold Cup, etc.
        # "Nations League" catches: UEFA NL, CONCACAF NL
        base_k = 40
        k = base_k * region_weight
        
    # =========================================================
    # TIER 4: SUB-REGIONAL & OLYMPICS (Weighted by Region)
    # =========================================================
    # This tier is massive in your dataset. These are official but smaller than Continental Cups.
    elif any(x in t_str for x in [
        'AFF', 'ASEAN', 'EAFF', 'CAFA', 'WAFF', 'SAFF', # Asian Sub-regions
        'CECAFA', 'COSAFA', 'WAFU', 'CEMAC',            # African Sub-regions
        'UNCAF', 'CFU', 'Caribbean Cup',                # CONCACAF Sub-regions
        'Baltic Cup', 'Nordic', 'British Home',         # European Sub-regions
        'Pacific Games', 'Melanesian', 'Polynesian',    # Oceania
        'Olympic Games', 'Asian Games', 'Pan American'  # Multi-sport Events
    ]):
        base_k = 25
        k = base_k * region_weight

    # =========================================================
    # DEFAULT CATCH-ALL
    # =========================================================
    else:
        # If we missed it (e.g. "Copa Paz del Chaco"), treat as slightly more than friendly
        k = 20

    # --- MARGIN OF VICTORY BOOSTER ---
    if goal_diff == 2: k *= 1.25
    elif goal_diff == 3: k *= 1.5
    elif goal_diff >= 4: k *= (1.5 + (goal_diff-3)/8)
    
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
    # PHASE 1: CHRONOLOGICAL ELO & LIVE TRACKING
    # ----------------------------------------------------
    team_elo = {}
    INITIAL_RATING = 1200
    RELEVANCE_CUTOFF = pd.to_datetime('2021-01-01') # "Recent History" Filter for Profile Stats
    
    global TEAM_HISTORY
    TEAM_HISTORY = {} 
    global TEAM_STATS
    TEAM_STATS = {}
    
    # 1. INITIALIZE ALL TEAMS FIRST
    # We create the master dictionary here so every team has empty counters ready.
    all_teams_set = set(elo_df['home_team']).union(set(elo_df['away_team']))
    for t in all_teams_set:
        TEAM_STATS[t] = {
            'elo': INITIAL_RATING, 'notable_results': [],
            'vs_elite': [0, 0, 0], # NEW: Tracks games against Top 20 caliber teams
            'vs_stronger': [0, 0, 0], 'vs_similar':  [0, 0, 0], 'vs_weaker':   [0, 0, 0],
            
            # --- Upset Tracking (Live Elo) ---
            'upsets_major_won': 0,  'upsets_minor_won': 0,
            'upsets_major_lost': 0, 'upsets_minor_lost': 0,
            
            # --- Stats to be filled in Phase 2 ---
            'matches': 0, 'clean_sheets': 0, 'btts': 0, 
            'gf_avg': 0, 'ga_avg': 0, 'off': 1.0, 'def': 1.0,
            'penalties': 0, 'first_half': 0, 'late_goals': 0, 'total_goals_recorded': 0,
            'form': []
        }

    # 2. THE MAIN LOOP (Chronological)
    matches_data = zip(elo_df['home_team'], elo_df['away_team'], 
                       elo_df['home_score'], elo_df['away_score'], 
                       elo_df['tournament'], elo_df['neutral'], elo_df['date'])
    
    for h, a, hs, as_, tourney, neutral, date in matches_data:
        # A. GET "LIVE" RATINGS (At the time of match)
        rh = team_elo.get(h, INITIAL_RATING)
        ra = team_elo.get(a, INITIAL_RATING)
        
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
                    'opp': opp,
                    'score': score_str,
                    'diff': abs(int(elo_diff)),
                    'date': match_date,
                    'type': type_code
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
                    # Optional: Don't record minor losses to keep list clean
                    # record_upset(h, a, score_h, diff_h, "LOST_MINOR", date)

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
        
        # Calculate Expectancy
        dr = rh - ra + (100 if not neutral else 0)
        we = 1 / (10**(-dr/600) + 1)
        W = 1 if hs > as_ else (0 if as_ > hs else 0.5)
        
        # Apply Update
        k = get_k_factor(tourney, abs(hs - as_), h, a)
        change = k * (W - we)
        
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
    
    # 1. Setup Global Context
    if len(recent_df) > 0:
        LATEST_DATE = recent_df['date'].max()
        avg_goals_global = (recent_df['home_score'].mean() + recent_df['away_score'].mean()) / 2
    else:
        LATEST_DATE = pd.to_datetime('today')
        avg_goals_global = 1.25
    
    # 2. Init Aggregators (Temp storage for the math)
    team_recent_aggregates = {t: {'gf':0, 'ga':0, 'eff_games':0, 'opp_elo_sum':0} for t in all_teams_set}
    
    # 3. SINGLE PASS LOOP (Form & Weighted Stats)
    for _, row in recent_df.iterrows():
        h, a = row['home_team'], row['away_team']
        hs, as_ = row['home_score'], row['away_score']
        match_date = row['date']
        
        # Get Final Elos (Used for SOS weighting, not Upset calculation)
        h_elo = TEAM_STATS.get(h, {}).get('elo', 1200)
        a_elo = TEAM_STATS.get(a, {}).get('elo', 1200)

        # A. CALCULATE TIME DECAY WEIGHT
        days_old = (LATEST_DATE - match_date).days
        years_old = int(max(0, days_old) / 365)
        
        if years_old == 0:   weight = 1.0  # Last 12 months
        elif years_old == 1: weight = 0.9  # 1-2 years ago
        elif years_old == 2: weight = 0.8  # 2-3 years ago
        elif years_old == 3: weight = 0.7  # 3-4 years ago
        else:                weight = 0.5  # Older

        # B. UPDATE HOME STATS
        if h in TEAM_STATS:
            TEAM_STATS[h]['matches'] += 1
            
            # Form String (W/D/L)
            res = 'W' if hs > as_ else ('L' if hs < as_ else 'D')
            TEAM_STATS[h]['form'].append(res)
            
            # Weighted Math
            agg = team_recent_aggregates[h]
            agg['gf'] += (hs * weight)
            agg['ga'] += (as_ * weight)
            agg['eff_games'] += weight       
            agg['opp_elo_sum'] += (a_elo * weight)
            
            # Count Clean Sheets / BTTS
            if as_ == 0: TEAM_STATS[h]['clean_sheets'] += 1
            if hs > 0 and as_ > 0: TEAM_STATS[h]['btts'] += 1

        # C. UPDATE AWAY STATS
        if a in TEAM_STATS: 
            TEAM_STATS[a]['matches'] += 1
            
            # Form String (W/D/L)
            res = 'W' if as_ > hs else ('L' if as_ < hs else 'D')
            TEAM_STATS[a]['form'].append(res)

            # Weighted Math
            agg = team_recent_aggregates[a]
            agg['gf'] += (as_ * weight)
            agg['ga'] += (hs * weight)
            agg['eff_games'] += weight
            agg['opp_elo_sum'] += (h_elo * weight)
            
            # Count Clean Sheets / BTTS
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
        
        # 2. SOS Calculation (Unchanged)
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
        # C. ELO BLENDING (THE "TRUST THE SIM" UPDATE)
        # -----------------------------------------------------------
        
        # 1. Calculate Base Ratio (Centered on 1500)
        # 1500 -> 1.0
        # 2100 -> 1.4
        elo_ratio = s['elo'] / 1500.0
        
        # 2. Apply Power Curve (Widen the gap)
        # A 10% Elo advantage translates to a ~20% Scoring advantage
        elo_off = elo_ratio ** 2.0 
        
        # 3. Defense is the Inverse (Reciprocal)
        # If Offense is 2.0 (Double Strength), Defense is 0.5 (Half Conceded)
        elo_def = 1.0 / elo_off
        
        # 4. Wide Guardrails (Trust the Sim!)
        # Allow multipliers to go from 0.3 (Tiny Nation) to 3.0 (Godlike)
        elo_off = np.clip(elo_off, 0.3, 3.0)
        elo_def = np.clip(elo_def, 0.3, 3.0)

        # -----------------------------------------------------------

        elo_off_log = np.log(elo_off)
        elo_def_log = np.log(elo_def)

        # 3. Blend stats + Elo prior
        STAT_WEIGHT = 0.65
        ELO_WEIGHT  = 0.35

        # Offense Blend
        final_off_log = STAT_WEIGHT * np.log(adjusted_off) + ELO_WEIGHT * elo_off_log
        s['off'] = np.exp(final_off_log)

        # Defense Blend
        final_def_log = STAT_WEIGHT * np.log(adjusted_def) + ELO_WEIGHT * elo_def_log
        s['def'] = np.exp(final_def_log)
        
        # Final Clamps (Also Widened)
        # We allow teams to be rated up to 3.0x Average
        s['off'] = np.clip(s['off'], 0.4, 3.0)
        s['def'] = np.clip(s['def'], 0.4, 3.0)

        # Display Values
        s['adj_gf'] = s['off'] * avg_goals_global
        s['adj_ga'] = s['def'] * avg_goals_global

        # Finalize Stats Strings
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
        # E. ADVANCED STYLE LABEL (Updated for SOS-Adjusted Stats)
        # -----------------------------------------------------------
        # We now use 'adj_gf' and 'adj_ga' so the label matches the rating.

        has_history = m >= 10 
        
        # Calculate relative strength (1.0 = exactly average)
        rel_gf = s['adj_gf'] / avg_goals_global
        rel_ga = s['adj_ga'] / avg_goals_global
    
        if has_history:
            # 1. ELITE: Adjusted to comfortably catch Spain, Argentina, France
            if rel_gf > 1.28 and rel_ga < 0.85: style = "Elite / Dominant"
            elif rel_gf > 1.20 and rel_ga > 1.15: style = "High Risk / Chaos"
            elif rel_gf < 0.90 and rel_ga < 0.80: style = "Defensive Wall"
            elif s['btts_pct'] < 50 and rel_ga < 0.95: style = "Control / Disciplined"
            elif s['late_pct'] > 35: style = "Late Surge"
            elif s['fh_pct'] > 55 and rel_gf > 1.05: style = "Fast Starters"
            elif s['pen_pct'] > 20 and rel_gf < 1.1: style = "Set-Piece Reliant"
            elif rel_gf > 1.10: style = "Strong Attack"
            elif rel_ga < 0.90: style = "Solid Defense"
            else: style = "Balanced"
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
        confed = TEAM_CONFEDS.get(team.lower(), 'OFC') 
        buckets[confed].append(stats['elo'])
        
    confed_scores = {}
    
    # Calculate a Global Baseline (Average of the Top 10 teams in the world)
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

    # 2. Normalize against the highest score (usually UEFA or CONMEBOL)
    baseline = max(confed_scores.values())
    
    for confed, score in confed_scores.items():
        # Linear normalization
        ratio = score / baseline
        
        # Safety Valve: Don't let the multiplier drop below 0.60
        # Even the weakest region shouldn't be "half as good" in a 90-minute sim
        CONFED_MULTIPLIERS[confed] = round(max(0.60, ratio), 3)
        js.console.error(f"{confed}: {CONFED_MULTIPLIERS[confed]} (Based on score {int(score)})")

def sim_match(t1, t2, knockout=False):
    
    # 1. GET BASE STATS
    # These inputs can now be as high as 3.0 due to your SOS changes
    s1 = TEAM_STATS.get(t1, {'elo':1200, 'off':1.0, 'def':1.0})
    s2 = TEAM_STATS.get(t2, {'elo':1200, 'off':1.0, 'def':1.0})

    # --- REGIONAL STRENGTH LOOKUP --------------
    # Get the confederation for both teams
    confed1 = TEAM_CONFEDS.get(t1, 'OFC')
    confed2 = TEAM_CONFEDS.get(t2, 'OFC')
    
    # Get the multipliers (default to 1.0 if not found)
    reg_mult1 = CONFED_MULTIPLIERS.get(confed1, 1.0)
    reg_mult2 = CONFED_MULTIPLIERS.get(confed2, 1.0)
    # ------------------------------------------
    
    # 2. ELO WIN EXPECTANCY
    dr = s1['elo'] - s2['elo']
    we = 1 / (10**(-dr/600) + 1)
    
    # 3. STYLES
    style1 = TEAM_PROFILES.get(t1, 'Balanced')
    style2 = TEAM_PROFILES.get(t2, 'Balanced')
    mod1 = STYLE_MATRIX.get((style1, style2), 1.0)
    mod2 = STYLE_MATRIX.get((style2, style1), 1.0)
    
    # Home Advantage (Hosts)
    home_boost = 1.15 if t1 in ['united states', 'mexico', 'canada'] else 1.0
    away_boost = 1.15 if t2 in ['united states', 'mexico', 'canada'] else 1.0

    # 4. FORM BIAS
    FORM_WEIGHT = 0.6 
    
    off1_adj = 1.0 + (s1['off'] - 1.0) * FORM_WEIGHT
    def1_adj = 1.0 + (s1['def'] - 1.0) * FORM_WEIGHT
    
    off2_adj = 1.0 + (s2['off'] - 1.0) * FORM_WEIGHT
    def2_adj = 1.0 + (s2['def'] - 1.0) * FORM_WEIGHT
    
    # Elo Scaling (Class difference)
    elo_scale = 1 + (we - 0.5)

    # 5. LOGARITHMIC COMPRESSION (The "Safety Valve")
    # RELAXED: Allows elite teams to score 2 or 3 goals realistically before throttling
    m1_raw = off1_adj * def2_adj
    m2_raw = off2_adj * def1_adj
    
    # RELAXED: Allows elite teams to score 2 or 3 goals realistically before throttling
    def compress(val):
        if val <= 1.5: return val
        return 1.5 + np.log(val - 0.5) * 0.85 

    m1 = compress(m1_raw)
    m2 = compress(m2_raw)

    # 6. TOURNAMENT INTENSITY 
    # ADJUSTED: 0.82 was too harsh. 0.95 simulates tighter knockout play 
    # without suffocating the goal generation.
    TOURNAMENT_INTENSITY = 0.95
    
    # 7. CALCULATE EXPECTED GOALS (Poisson Lambda)
    # REMOVED: reg_mult1 and reg_mult2 to prevent double-nerfing.
    lam1 = AVG_GOALS * m1 * mod1 * home_boost * TOURNAMENT_INTENSITY
    lam2 = AVG_GOALS * m2 * mod2 * away_boost * TOURNAMENT_INTENSITY
    
    # 8. RUN SIMULATION
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
        # DRAW
        if not knockout:
            return 'draw', g1, g2
            
        # EXTRA TIME (Knockout Only)
        et_scale = 0.33
        lam1_et = lam1 * et_scale * 0.80 # Tighter in ET
        lam2_et = lam2 * et_scale * 0.80
        
        g1_et = np.random.poisson(lam1_et)
        g2_et = np.random.poisson(lam2_et)
        
        g1 += g1_et
        g2 += g2_et
        
        if g1 > g2: return t1, g1, g2, 'aet'
        elif g2 > g1: return t2, g1, g2, 'aet'
            
        # PENALTIES
        p1_bonus = 0.1 if style1 == 'Set-Piece Reliant' else 0
        p2_bonus = 0.1 if style2 == 'Set-Piece Reliant' else 0
        
        pk_prob = np.clip(
            0.5 + dr / 4000 + (p1_bonus - p2_bonus),
            0.35, 0.65
        )
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
        # Shuffle for random tie-breakers
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

        # Notice gf is added here for proper FIFA tie-breakers!
        sorted_teams = sorted(teams_shuffled, key=lambda t: (table_stats[t]['p'], table_stats[t]['gd'], table_stats[t]['gf']), reverse=True)
        group_results_lists[grp] = sorted_teams
        
        # Make sure to pass the 'team_group' so the dynamic knockout bracket doesn't crash!
        third_place.append({'team': sorted_teams[2], 'team_group': grp, 'stats': table_stats[sorted_teams[2]]})

        if not fast_mode:
            structured_groups[grp] =[]
            for t in sorted_teams:
                structured_groups[grp].append({'team': t, **table_stats[t]})

    # --- 2. KNOCKOUT PREP (OFFICIAL FIFA 2026 FORMAT) ---
    def get_t(grp, pos):
        return group_results_lists[grp][pos]

    # 1. Get the 8 Best 3rd Place Teams (Include their Group Name)
    best_3rds = sorted(third_place, key=lambda x: (x['stats']['p'], x['stats']['gd'], x['stats']['gf']), reverse=True)[:8]
    # Format:[{'team': 'wales', 'group': 'A'}, {'team': 'poland', 'group': 'C'}, ...]
    
    
    # 2. Dynamic FIFA 3rd-Place Allocation Algorithm (Replaces the 495-line matrix)
    # The designated 8 Group Winners that play 3rd-place teams per FIFA rules
    target_winners =['A', 'B', 'D', 'E', 'G', 'I', 'K', 'L']
    t3_mapping = {}

    def assign_t3(index, available_t3):
        if index == len(target_winners): return True
        host_group = target_winners[index]
        
        for t3 in available_t3:
            # FIFA RULE: A group winner cannot play a 3rd place team from its own group
            if t3['team_group'] != host_group:          
                t3_mapping[host_group] = t3['team']
                new_available =[t for t in available_t3 if t != t3]
                if assign_t3(index + 1, new_available): 
                    return True
        return False
        
    # Run the allocator
    assign_t3(0, best_3rds)

    # 3. Official 2026 Bracket Structure
    bracket_matchups =[
        # --- LEFT SIDE OF BRACKET ---
        (get_t('A', 0), t3_mapping['A']),    # 1A vs 3rd
        (get_t('C', 1), get_t('F', 1)),      # 2C vs 2F
        
        (get_t('E', 0), t3_mapping['E']),    # 1E vs 3rd
        (get_t('G', 1), get_t('J', 1)),      # 2G vs 2J
        
        (get_t('I', 0), t3_mapping['I']),    # 1I vs 3rd
        (get_t('A', 1), get_t('D', 1)),      # 2A vs 2D
        
        (get_t('L', 0), t3_mapping['L']),    # 1L vs 3rd
        (get_t('H', 0), get_t('K', 1)),      # 1H vs 2K (1st vs 2nd)
        
        # --- RIGHT SIDE OF BRACKET ---
        (get_t('B', 0), t3_mapping['B']),    # 1B vs 3rd
        (get_t('E', 1), get_t('H', 1)),      # 2E vs 2H
        
        (get_t('G', 0), t3_mapping['G']),    # 1G vs 3rd
        (get_t('B', 1), get_t('I', 1)),      # 2B vs 2I
        
        (get_t('K', 0), t3_mapping['K']),    # 1K vs 3rd
        (get_t('C', 0), get_t('F', 0)),      # 1C vs 1F (Wait: Fixed to 1st vs 2nd below)
        
        (get_t('D', 0), t3_mapping['D']),    # 1D vs 3rd
        (get_t('J', 0), get_t('L', 1)),      # 1J vs 2L (1st vs 2nd)
    ]
    
    # *Correction for Right Side 1sts vs 2nds*: 
    # Remaining 1sts: C, F, H, J. 
    # Bracket adjustments to ensure 1sts only play 2nds:
    bracket_matchups[13] = (get_t('C', 0), get_t('L', 1)) # 1C vs 2L
    bracket_matchups[15] = (get_t('F', 0), get_t('J', 1)) # 1F vs 2J
    bracket_matchups[7]  = (get_t('H', 0), get_t('K', 1)) # 1H vs 2K
    bracket_matchups[3]  = (get_t('J', 0), get_t('G', 1)) # 1J vs 2G
        
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
        k = get_k_factor(row['tournament'], gd, h, a)
        
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
