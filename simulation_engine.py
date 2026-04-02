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
#STYLE_MATRIX = {
#    ('Defensive Wall', 'Strong Attack'): 1.10,    # Wall absorbs pure attack
#    ('High Risk / Reward', 'Defensive Wall'): 1.10, # Chaos breaks the wall
#    ('Disciplined', 'High Risk / Reward'): 1.10,  # Discipline punishes chaos
#    ('Aggressive Starter', 'Late Drama'): 1.05,   # Early lead kills late momentum
#    ('Late Drama', 'Disciplined'): 1.08,          # Late surge breaks discipline
#    ('Set-Piece Reliant', 'Solid Defense'): 1.08, # Set pieces bypass solid defense
#    ('Dominant', 'Balanced'): 1.05,               # Dominant crushes balanced
#    ('Dominant', 'High Risk / Reward'): 1.10      # Dominant exploits risky teams
#}

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

# SOURCE-VERIFIED TACTICAL PROFILES (Based on 2024/25 Managerial Trends)
TACTICAL_PROFILES = {
    # --- GROUP A ---
    'mexico': 'Tactical Pragmatism',       # Under Javier Aguirre: Shifted from flair to defensive discipline/grinding results.
    'south africa': 'Fluid Creativity',    # Hugo Broos: Uses technical, short-passing domestic core (Mamelodi Sundowns style).
    'south korea': 'Heavy Metal / Pressing', # Hong Myung-bo: Transition-heavy, high-intensity running.
    'czech republic': 'Physical Direct',   # Ivan Hašek: Traditional focus on crosses, set-pieces, and height.

    # --- GROUP B ---
    'canada': 'High-Intensity Chaos',      # Jesse Marsch: "Red Bull" style—ultra-aggressive, vertical, and high-risk.
    'switzerland': 'Tactical Pragmatism',  # Murat Yakin: Elite mid-block, adaptive to opponent weaknesses.
    'qatar': 'Organized Low-Block',        # Tintín Márquez: Pragmatic, counter-attacking focus.
    'bosnia and herzegovina': 'Physical Direct', # Direct play targeting physical strikers.

    # --- GROUP C ---
    'brazil': 'Fluid Creativity',          # Dorival Júnior: Seeking to restore 'Ginga' with roaming attackers like Vinicius/Rodrygo.
    'morocco': 'Organized Low-Block',      # Walid Regragui: World-renowned for the 4-1-4-1 deep defensive shell.
    'haiti': 'High-Intensity Chaos',       # Focus on raw pace and individual transitions.
    'scotland': 'Physical Direct',         # Steve Clarke: Low block + set-piece reliance + Robertson/McGinn crosses.

    # --- GROUP D ---
    'united states': 'Heavy Metal / Pressing', # Mauricio Pochettino: Known for high-line, aggressive ball-recovery.
    'paraguay': 'Organized Low-Block',     # Gustavo Alfaro: Master of the 'anti-football' defensive masterclass.
    'australia': 'Tactical Pragmatism',    # Tony Popovic: Structurally rigid, focused on organization.
    'turkey': 'Fluid Creativity',          # Vincenzo Montella: Heavy focus on technical #10s (Arda Güler) and roaming wings.

    # --- GROUP E ---
    'germany': 'Heavy Metal / Pressing',   # Julian Nagelsmann: Complex counter-pressing and narrow 'Zocker' combinations.
    'curaçao': 'Vertical Tiki-Taka',       # Dutch-influenced school of technical, quick passing.
    'ivory coast': 'Vertical Tiki-Taka',   # Emerse Faé: High-speed wing play combined with midfield control.
    'ecuador': 'Heavy Metal / Pressing',   # Sebastián Beccacece: Intense physical pressure and high athletic output.

    # --- GROUP F ---
    'netherlands': 'Positional Dominance', # Ronald Koeman: Total Football roots—focus on wing-backs and ball circulation.
    'japan': 'Vertical Tiki-Taka',         # Hajime Moriyasu: Famous for ultra-fast technical transitions (The "Blue Samurai" blitz).
    'tunisia': 'Organized Low-Block',      # Traditionally one of Africa's most disciplined defensive units.
    'sweden': 'Vertical Tiki-Taka',        # Jon Dahl Tomasson: Moving away from 4-4-2 to a technical, attacking 4-3-3.

    # --- GROUP G ---
    'belgium': 'Positional Dominance',     # Domenico Tedesco: High possession, high technical ceiling.
    'egypt': 'Tactical Pragmatism',        # Focus on Salah’s transition, but structurally conservative.
    'iran': 'Organized Low-Block',         # Amir Ghalenoei: Maintaining the Queiroz-era defensive discipline.
    'new zealand': 'Physical Direct',      # Direct approach using height in the box (Chris Wood).

    # --- GROUP H ---
    'spain': 'Positional Dominance',       # De la Fuente: High possession but with new "Vertical" wingers (Lamine Yamal).
    'cape verde': 'Vertical Tiki-Taka',    # Technical, short-passing style that surprised in AFCON.
    'saudi arabia': 'Tactical Pragmatism', # Herve Renard: Known for high defensive lines and disciplined traps.
    'uruguay': 'Heavy Metal / Pressing',   # Marcelo Bielsa: The purest "Heavy Metal" team in international football.

    # --- GROUP I ---
    'france': 'Tactical Pragmatism',       # Deschamps: Does not care about possession; waits for the killer counter-attack.
    'senegal': 'Physical Direct',          # Aliou Cissé: Extreme physical power, pace, and aerial dominance.
    'norway': 'Physical Direct',           # Ståle Solbakken: Built to feed Haaland via direct verticality and crosses.
    'iraq': 'Organized Low-Block',         # Jesús Casas: Spanish-organized defensive shape with quick breaks.

    # --- GROUP J ---
    'argentina': 'Fluid Creativity',       # Scaloni: 'La Nuestra'—midfielders interchange positions constantly to confuse the block.
    'algeria': 'Vertical Tiki-Taka',       # Vladimir Petković: Technical build-up with aggressive wing play.
    'austria': 'Heavy Metal / Pressing',   # Ralf Rangnick: The architect of the modern high-press.
    'jordan': 'Organized Low-Block',       # Jamal Sellami: Rigid defensive lines as seen in Asian Cup.

    # --- GROUP K ---
    'portugal': 'Positional Dominance',    # Roberto Martínez: Obsessive focus on 3-box-3 possession structures.
    'uzbekistan': 'Organized Low-Block',   # Srečko Katanec: Highly disciplined, hard-to-beat Asian powerhouse.
    'colombia': 'Fluid Creativity',        # Néstor Lorenzo: High-tempo technical football led by James Rodríguez.
    'dr congo': 'High-Intensity Chaos',    # Sébastien Desabre: Direct, physical, and extremely fast on the break.

    # --- GROUP L ---
    'england': 'Positional Dominance',     # Post-Southgate: Reverting to a more technical, possession-first philosophy.
    'croatia': 'Positional Dominance',     # Zlatko Dalić: Midfield-led (Modrić/Kovačić) game control.
    'ghana': 'High-Intensity Chaos',       # Focus on athletic transitions and individual 1v1s.
    'panama': 'Tactical Pragmatism'        # Thomas Christiansen: Organized, balanced, and patient.
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
    # REDUCED per audit: prevents excessive Elo gains in high K-factor tournaments
    if goal_diff == 2: k *= 1.15  # Reduced from 1.25
    elif goal_diff == 3: k *= 1.30  # Reduced from 1.5
    elif goal_diff >= 4: k *= 1.35  # Capped instead of unbounded
    
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
        
        # FIXED per audit: Use actual global mean instead of hardcoded 1500
        elo_ratio = s['elo'] / GLOBAL_ELO_MEAN
        
        # Power curve reduced from 2.0 to 1.5. 
        elo_off = elo_ratio ** 1.5 
        elo_def = 1.0 / elo_off
        
        # Widen guardrails for stats
        elo_off = np.clip(elo_off, 0.4, 2.5)
        elo_def = np.clip(elo_def, 0.4, 2.5)

        elo_off_log = np.log(elo_off)
        elo_def_log = np.log(elo_def)

        # Trust Elo slightly more (International football stats are noisy)
        STAT_WEIGHT = 0.60
        ELO_WEIGHT  = 0.40

        # Offense Blend
        final_off_log = STAT_WEIGHT * np.log(adjusted_off) + ELO_WEIGHT * elo_off_log
        s['off'] = np.exp(final_off_log)

        # Defense Blend
        final_def_log = STAT_WEIGHT * np.log(adjusted_def) + ELO_WEIGHT * elo_def_log
        s['def'] = np.exp(final_def_log)
        
        s['off'] = np.clip(s['off'], 0.4, 2.8)
        s['def'] = np.clip(s['def'], 0.4, 2.8)

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
        # E. ADVANCED STYLE LABEL (Identity Bridge Logic)
        # -----------------------------------------------------------
        # Priority 1: Check the hardcoded TACTICAL_PROFILES dictionary
        if t in TACTICAL_PROFILES:
            style = TACTICAL_PROFILES[t]
        
        # Priority 2: Use your existing complex Data-Driven logic for all other teams
        else:
            has_history = m >= 10 
            rel_gf = s['adj_gf'] / avg_goals_global
            rel_ga = s['adj_ga'] / avg_goals_global
            
            # Using your provided data columns
            btts = s.get('btts_pct', 0)
            late = s.get('late_pct', 0)
            clean_sheets = s.get('cs_pct', 0)

            if has_history:
                # 1. THE ELITE (Spain/Argentina context)
                if s['elo'] > 1900 and rel_gf > 1.25 and rel_ga < 0.85:
                    style = "Elite / Dominant"
                
                # 2. THE SPECIALISTS (Based on your table data)
                elif rel_ga < 0.75 or (clean_sheets > 45 and rel_gf < 0.95):
                    style = "Defensive Wall"      # E.g., Paraguay/Morocco style
                
                elif rel_gf > 1.35 and rel_ga > 1.20:
                    style = "High Risk / Chaos"   # E.g., Netherlands style
                
                elif btts > 60:
                    style = "High-Intensity Chaos" 
                
                elif btts < 35:
                    style = "Control / Disciplined" 
                
                elif late > 30:
                    style = "Late Surge"          # E.g., Mexico (32%)
                
                # 3. STATISTICAL TRENDS
                elif rel_gf > 1.15:
                    style = "Strong Attack"
                elif rel_ga < 0.90:
                    style = "Solid Defense"
                else:
                    style = "Balanced"
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
    s1 = TEAM_STATS.get(t1, {'elo':1200, 'off':1.0, 'def':1.0})
    s2 = TEAM_STATS.get(t2, {'elo':1200, 'off':1.0, 'def':1.0})
    style1 = TEAM_PROFILES.get(t1, 'Balanced')
    style2 = TEAM_PROFILES.get(t2, 'Balanced')

    # --- REGIONAL STRENGTH & PEDIGREE (FROM YOUR SNIPPET) ---
    confed1 = TEAM_CONFEDS.get(t1, 'OFC')
    confed2 = TEAM_CONFEDS.get(t2, 'OFC')
    reg_mult1 = CONFED_MULTIPLIERS.get(confed1, 1.0)
    reg_mult2 = CONFED_MULTIPLIERS.get(confed2, 1.0)
    pedigree_gap = reg_mult1 - reg_mult2 
    
    # 2. MATCH-DAY WIN EXPECTANCY
    dr = s1['elo'] - s2['elo']
    we1 = 1 / (10**(-dr/400) + 1)
    we2 = 1 - we1
    
    # 3. ARCHETYPE BRIDGE
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

    # 5. DYNAMIC COMPLEXITY CHECK (New Layer)
    def apply_complexity(elo, style):
        atk, dfe = 1.0, 1.0
        
        # Tier 1: High Floor / High Ceiling (The "Barcelona/Liverpool" problem)
        # Needs high technical talent and stamina.
        elite_styles = ['Positional Dominance', 'Heavy Metal / Pressing', 'Vertical Tiki-Taka', 'Fluid Creativity']
        
        # Tier 2: Low Floor / Low Ceiling (The "Great Equalizers")
        # Easy to coach, hard to break down.
        robust_styles = ['Organized Low-Block', 'Physical Direct', 'High-Intensity Chaos', 'Defensive Wall']
        
        # Tier 3: Adaptive
        adaptive_styles = ['Tactical Pragmatism', 'Control / Disciplined', 'Strong Attack', 'Solid Defense']

        if style in elite_styles:
            if elo > 1950: # The "Spain/Argentina" Tier
                atk, dfe = 1.12, 1.08  # System Mastery: Complete dominance
            elif elo > 1800: # The "Contender" Tier (England, Brazil)
                atk, dfe = 1.06, 1.04  # High Competency
            elif elo < 1600: # The "Trap" Tier (USA, Canada)
                # These teams have the ambition but often lack the depth/talent to execute
                # Result: Caught on the counter or mistakes in build-up.
                atk, dfe = 0.88, 0.85  # -12% Atk / -15% Def penalty
            elif elo < 1750: # Mid-Tier
                atk, dfe = 0.94, 0.94  # Execution errors

        elif style in robust_styles:
            if elo < 1650: # Underdog Sweet Spot (Morocco, Iran, Paraguay)
                # These styles make weaker teams much harder to kill.
                dfe = 1.18  # +18% Defensive Solidity
                atk = 0.92  # Sacrifice offense for the bus
            elif elo > 1850: 
                # Elite teams playing too simply lose their creative edge.
                atk = 0.90  # "Glass Ceiling" penalty
                dfe = 1.05  

        elif style in adaptive_styles:
            if elo > 1800:
                atk, dfe = 1.05, 1.05 # Professional efficiency (France model)
            elif elo < 1550:
                dfe = 0.92            # Lack of discipline/structure

        return round(atk, 2), round(dfe, 2)

    c1_a, c1_d = apply_complexity(s1['elo'], style1)
    c2_a, c2_d = apply_complexity(s2['elo'], style2)
    t1_atk_mod *= c1_a; t1_def_mod *= c1_d
    t2_atk_mod *= c2_a; t2_def_mod *= c2_d

    # 6. ARCHETYPE MATCHUPS (Rock-Paper-Scissors)
    matchup = (arc1, arc2)
    if matchup == ('chaos', 'possession'): t1_atk_mod *= 1.10; t2_atk_mod *= 0.90
    elif matchup == ('possession', 'chaos'): t1_atk_mod *= 0.90; t2_atk_mod *= 1.10
    elif matchup == ('possession', 'pragmatic'): t1_atk_mod *= 1.10
    elif matchup == ('pragmatic', 'possession'): t2_atk_mod *= 1.10
    elif matchup == ('pragmatic', 'chaos'): t1_atk_mod *= 1.10; t2_atk_mod *= 0.90
    elif matchup == ('chaos', 'pragmatic'): t1_atk_mod *= 0.90; t2_atk_mod *= 1.10

    # 7. GAME PACE & DAVID-VS-GOLIATH
    if arc1 in ['chaos', 'fluid'] and arc2 in ['chaos', 'fluid']: pace_mod = 1.15
    elif arc1 in ['pragmatic', 'possession'] and arc2 == 'pragmatic': pace_mod = 0.85

    if arc1 == 'pragmatic' and dr < -150: t1_def_mod *= 1.15 
    if arc2 == 'pragmatic' and dr > 150: t2_def_mod *= 1.15

    # 8. FORM BIAS (FROM YOUR SNIPPET)
    FORM_WEIGHT = 0.5 
    off1_adj = 1.0 + (s1['off'] - 1.0) * FORM_WEIGHT
    def1_adj = 1.0 + (s1['def'] - 1.0) * FORM_WEIGHT
    off2_adj = 1.0 + (s2['off'] - 1.0) * FORM_WEIGHT
    def2_adj = 1.0 + (s2['def'] - 1.0) * FORM_WEIGHT

    # 9. PARK THE BUS / GAME STATE (FROM YOUR SNIPPET)
    bus1, bus2 = 1.0, 1.0
    if dr > 300: 
        bus2, bus1 = 0.65, 0.90
    elif dr < -300:
        bus1, bus2 = 0.65, 0.90
        
    # 10. BRINGING IT ALL TOGETHER (ELO & PEDIGREE FROM YOUR SNIPPET)
    class1 = 1.0 + (we1 - 0.5) * 0.4  
    class2 = 1.0 + (we2 - 0.5) * 0.4
    ped1 = 1.0 + (pedigree_gap * 0.15)
    ped2 = 1.0 - (pedigree_gap * 0.15)
    
    # 2026 Home Advantage
    h1 = 1.15 if t1 in ['united states', 'mexico', 'canada'] else (1.05 if confed1 == 'CONCACAF' else 1.0)
    h2 = 1.15 if t2 in ['united states', 'mexico', 'canada'] else (1.05 if confed2 == 'CONCACAF' else 1.0)

    m1_base = (off1_adj * def2_adj) * class1 * ped1 * bus1
    m2_base = (off2_adj * def1_adj) * class2 * ped2 * bus2
    
    def compress(val): return val if val <= 1.8 else 1.8 + np.log(val - 0.8) * 0.8 
    intensity = 0.88 if knockout else 1.0

    # 11. FINAL LAMBDA (XG) GENERATION
    lam1 = AVG_GOALS * compress(m1_base) * h1 * intensity * pace_mod * t1_atk_mod * (2.0 - t2_def_mod)
    lam2 = AVG_GOALS * compress(m2_base) * h2 * intensity * pace_mod * t2_atk_mod * (2.0 - t1_def_mod)

    # 12. GOAL ROLLING (Variance Injection)
    def roll_goals(lam, arc):
        if lam <= 0: return 0
        if arc in ['chaos', 'fluid']:
            return np.random.poisson(np.random.gamma(10, lam / 10))
        return np.random.poisson(lam)

    g1, g2 = roll_goals(lam1, arc1), roll_goals(lam2, arc2)
    
    # --- RESULT LOGIC ---
    if g1 > g2: return (t1, g1, g2, 'reg') if knockout else (t1, g1, g2)
    if g2 > g1: return (t2, g1, g2, 'reg') if knockout else (t2, g1, g2)
    if not knockout: return 'draw', g1, g2

    # EXTRA TIME
    g1 += np.random.poisson(lam1 * 0.4)
    g2 += np.random.poisson(lam2 * 0.4)
    if g1 > g2: return t1, g1, g2, 'aet'
    if g2 > g1: return t2, g1, g2, 'aet'
    
    # PENALTIES
    p1_b = 0.08 if style1 in ['Set-Piece Reliant', 'Control / Disciplined', 'Tactical Pragmatism'] else 0
    p2_b = 0.08 if style2 in ['Set-Piece Reliant', 'Control / Disciplined', 'Tactical Pragmatism'] else 0
    winner = t1 if random.random() < np.clip(0.5 + (dr/3000) + (p1_b - p2_b), 0.35, 0.65) else t2
    return winner, g1, g2, 'pks'

def run_simulation(verbose=False, quiet=False, fast_mode=False, finalized_slots=None):
    # Data containers
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
