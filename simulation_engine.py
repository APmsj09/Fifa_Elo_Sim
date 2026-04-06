### `simulation_engine.py`
import pandas as pd
import numpy as np
import random
import math
import js

def calculate_recency_weight(match_date, latest_date):
    """
    Adjusted for International Football (Lower frequency of games).
    Matches from 4 years ago (full WC cycle) now retain ~60% importance.
    """
    days_old = (latest_date - match_date).days
    return math.exp(-0.00035 * max(0, days_old))

# =============================================================================
# --- PART 1: SETUP & DATA LOADING ---
# =============================================================================

DATA_DIR = "." 

TEAM_STATS = {}
TEAM_PROFILES = {}
TEAM_HISTORY = {}
ADVANCED_TEAM_DATA = {} 
AVG_GOALS = 2.5
calculated_hfa = 0.0

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

FINALIZED_SLOTS = {
    'Path A': 'bosnia and herzegovina',
    'Path B': 'sweden',                  
    'Path C': 'turkey',                  
    'Path D': 'czech republic',          
    'ICP1': 'dr congo',                  
    'ICP2': 'iraq'                       
}

TEAM_TALENT = {}
TEAM_FORMATIONS = {}

def load_data():
    def load_csv(filename):
        try:
            df = pd.read_csv(filename)
            df.columns = df.columns.str.strip().str.lower()
            return df
        except Exception as e:
            js.console.warn(f"Warning: Could not load {filename}: {e}")
            return None

    results_df = load_csv("results.csv") 
    goalscorers_df = load_csv("goalscorers.csv")
    former_names_df = load_csv("former_names.csv")
    player_df = load_csv("FM 26 Player Data.csv")
    formation_df = load_csv("FM 26 Player Data - Formations.csv")
    
    return results_df, goalscorers_df, former_names_df, player_df, formation_df

def calculate_squad_ratings(player_df):
    """Calculates team overall based on top 2 players per position category (1-100 scale)."""
    if player_df is None: return {}
    
    def categorize(pos):
        pos = str(pos).upper()
        # Prioritize strikers/forwards over wingers/midfielders
        if 'GK' in pos: return 'GK'
        if 'ST' in pos or 'FW' in pos: return 'FWD' 
        if 'M' in pos: return 'MID' # Catches AM, M, DM
        if 'D' in pos: return 'DEF'
        return 'MID'

    player_df['category'] = player_df['position(s)'].apply(categorize)
    team_ratings = {}
    
    for nation, group in player_df.groupby('nation'):
        nation_key = str(nation).lower().strip()
        # Get top 2 highest rated players per positional category
        cat_scores = group.sort_values('rat', ascending=False).groupby('category').head(2)
        
        if not cat_scores.empty:
            avg_rat = cat_scores['rat'].mean()
            
            # MATH FIX: Ratings are 1-100. 
            # We assume ~70 is an average WC team. 85+ is elite.
            talent_weight = np.clip(avg_rat / 70.0, 0.84, 1.20)
            
            team_ratings[nation_key] = {
                'talent_score': avg_rat,
                'talent_weight': talent_weight,
                'top_players': group.sort_values('rat', ascending=False).head(4).to_dict('records')
            }
    return team_ratings

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

def initialize_engine():
    results_df, scorers_df, df_names = load_data()
    
    try:
        if df_names is not None and 'old_name' in df_names.columns and 'new_name' in df_names.columns:
            NAME_MAP = dict(zip(df_names['old_name'], df_names['new_name']))
        else:
            NAME_MAP = {}
    except:
        NAME_MAP = {}

    if results_df is None: return {}, {}, 2.5, None

    # CRASH PROTECTION
    if 'date' not in results_df.columns:
        raise ValueError(f"CRITICAL: 'date' column missing in results.csv. Check if your URL returns a 404 HTML page instead of CSV. Columns found: {list(results_df.columns)}")

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
        global calculated_hfa
        calculated_hfa = round(-400 * math.log10(1/h_win_prob - 1))
    else:
        calculated_hfa = 100 
    
    js.console.log(f"Data-Driven HFA: {calculated_hfa}")
    elo_df = results_df.sort_values('date')

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

    matches_data = zip(elo_df['home_team'], elo_df['away_team'], elo_df['home_score'], elo_df['away_score'], elo_df['tournament'], elo_df['neutral'], elo_df['date'])

    for h, a, hs, as_, tourney, neutral, date in matches_data:
        rh = team_elo.get(h, INITIAL_RATING)
        ra = team_elo.get(a, INITIAL_RATING)

        if hs > as_:   res_h, res_a = 0, 2
        elif hs == as_: res_h, res_a = 1, 1
        else:          res_h, res_a = 2, 0
        
        t_str = str(tourney).lower()
        is_wc_finals = 'world cup' in t_str and 'qualification' not in t_str
        is_continental_finals = any(x in t_str for x in ['copa américa', 'euro', 'african cup', 'asian cup', 'gold cup']) and 'qualification' not in t_str

        if is_wc_finals or is_continental_finals:
            ped_val = 1.0 if is_wc_finals else 0.35
            TEAM_STATS[h]['pedigree_pts'] = TEAM_STATS[h].get('pedigree_pts', 0) + ped_val
            TEAM_STATS[a]['pedigree_pts'] = TEAM_STATS[a].get('pedigree_pts', 0) + ped_val

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

        if date > RELEVANCE_CUTOFF:
            if is_wc_finals or is_continental_finals:
                w = calculate_recency_weight(date, LATEST_DATE) 
                TEAM_STATS[h]['ko_exp_weighted'] = TEAM_STATS[h].get('ko_exp_weighted', 0) + w
                TEAM_STATS[a]['ko_exp_weighted'] = TEAM_STATS[a].get('ko_exp_weighted', 0) + w

            def record_upset(team, opp, score_str, elo_diff, type_code, match_date):
                TEAM_STATS[team]['notable_results'].append({
                    'opp': opp, 'score': score_str, 'diff': abs(int(elo_diff)), 'date': match_date, 'type': type_code
                })
            
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

    if scorers_df is not None and 'team' in scorers_df.columns and 'date' in scorers_df.columns:
        scorers_df['team'] = scorers_df['team'].str.lower().str.strip().replace(NAME_MAP)
        scorers_df['date'] = pd.to_datetime(scorers_df['date'], errors='coerce')
        modern_scorers = scorers_df[scorers_df['date'] > RELEVANCE_CUTOFF]
        
        for _, row in modern_scorers.iterrows():
            t = row['team']
            if t in TEAM_STATS:
                weight = calculate_recency_weight(row['date'], LATEST_DATE)
                TEAM_STATS[t]['total_goals_recorded'] += weight
                if 'penalty' in row and row['penalty']: TEAM_STATS[t]['penalties'] += weight
                try:
                    if 'minute' in row and pd.notnull(row['minute']):
                        minute = float(str(row['minute']).split('+')[0])
                        if minute <= 45: TEAM_STATS[t]['first_half'] += weight
                        if minute >= 75: TEAM_STATS[t]['late_goals'] += weight
                except: pass

    active_elos = [s['elo'] for s in TEAM_STATS.values()]
    GLOBAL_ELO_MEAN = sum(active_elos) / len(active_elos) if active_elos else 1500

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

        elo_ratio = s['elo'] / GLOBAL_ELO_MEAN
        elo_off = elo_ratio ** 0.95 
        elo_def = 1.0 / (elo_ratio ** 0.95) 
        
        elo_off = np.clip(elo_off, 0.6, 2.0)
        elo_def = np.clip(elo_def, 0.6, 2.0)

        elo_off_log = np.log(elo_off)
        elo_def_log = np.log(elo_def)

        STAT_WEIGHT = 0.35  
        ELO_WEIGHT  = 0.65  

        final_off_log = STAT_WEIGHT * np.log(adjusted_off) + ELO_WEIGHT * elo_off_log
        s['off'] = np.exp(final_off_log)

        final_def_log = STAT_WEIGHT * np.log(adjusted_def) + ELO_WEIGHT * elo_def_log
        s['def'] = np.exp(final_def_log)
        
        s['off'] = np.clip(s['off'], 0.5, 2.2) 
        s['def'] = np.clip(s['def'], 0.5, 2.2) 

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
def calculate_confed_strength(results_df=None):
    global CONFED_MULTIPLIERS
    
    if results_df is None:
        results_df, _, _ = load_data()
        if results_df is not None and 'date' in results_df.columns:
            results_df['date'] = pd.to_datetime(results_df['date'], errors='coerce')
            
    if results_df is None or 'date' not in results_df.columns:
        for confed in set(TEAM_CONFEDS.values()):
            CONFED_MULTIPLIERS[confed] = 0.85
        return

    recent_cutoff = pd.to_datetime('2014-01-01')
    modern_df = results_df[results_df['date'] > recent_cutoff]
    
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

    for confed, data in confed_performance.items():
        if data['matches'] > 0:
            win_rate = data['pts'] / data['matches']
            CONFED_MULTIPLIERS[confed] = round(0.8 + (win_rate * 0.4), 3)
        else:
            CONFED_MULTIPLIERS[confed] = 0.85 

def engineer_team_signatures(results_df):
    global TEAM_PROFILES, ADVANCED_TEAM_DATA
    TEAM_PROFILES = {}
    ADVANCED_TEAM_DATA = {} 
    
    if results_df is None or 'date' not in results_df.columns:
        for team in TEAM_STATS.keys():
            true_vol = TEAM_STATS[team].get('volatility', 0.15)
            TEAM_PROFILES[team] = "Balanced"
            ADVANCED_TEAM_DATA[team] = {'type': 'Balanced', 'poss': 0.5, 'press': 0.5, 'dir': 0.5, 'vol': true_vol}
            TEAM_STATS[team]['engineered_xg'] = 1.25
            TEAM_STATS[team]['pace_factor'] = 1.0
        return

    modern_df = results_df[results_df['date'] > pd.to_datetime('2012-01-01')].copy()
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

        avg_off = np.mean(off_res)
        avg_def = np.mean(def_res)
        avg_pace = np.mean(pace_res)

        if avg_pace > 1.15 and true_vol > 0.18: style = "Chaos & Intensity"
        elif avg_pace < 0.90 and avg_def < 0.95: style = "Compact Block"
        elif avg_off > 1.15 and avg_pace > 1.1: style = "Vertical Control"
        elif avg_off > 1.1 and avg_def > 1.1: style = "Direct-Physical"
        else: style = "Balanced"

        TEAM_PROFILES[team] = style
        
        control_index = np.clip((stats.get('elo', 1500) - 1000) / 1000.0, 0.2, 0.95)
        openness_index = np.clip(avg_pace * 0.45, 0.2, 0.95)
        efficiency_index = np.clip((avg_off / (avg_def + 0.1)) * 0.35, 0.2, 0.95)

        ADVANCED_TEAM_DATA[team] = {
            'type': style,
            'poss': control_index,   
            'press': openness_index, 
            'dir': efficiency_index, 
            'vol': true_vol          
        }
        
        stats['engineered_xg'] = avg_off
        stats['pace_factor'] = avg_pace

TEAM_PRECOMPUTE = {}

def precompute_match_data(talent_data=None):
    global TEAM_PRECOMPUTE
    TEAM_PRECOMPUTE = {}
    for t, s in TEAM_STATS.items():
        clean_name = str(t).lower().strip()
        talent = talent_data.get(clean_name, {'talent_weight': 1.0}) if talent_data else {'talent_weight': 1.0}
        
        # BLENDING: 70% Elo Performance / 30% Squad Talent
        base_elo = s.get('elo', 1200)
        # Convert talent weight back to an Elo-delta (e.g., 1.1 weight = +100 Elo)
        talent_bonus = (talent['talent_weight'] - 1.0) * 800 
        blended_elo = base_elo + talent_bonus

        pen_skill = s.get('pen_pct', 5) / 100.0 
        experience = np.clip(s.get('ko_exp_weighted', 0) / 20.0, 0, 0.1)

        TEAM_PRECOMPUTE[clean_name] = {
            'elo': blended_elo,
            'xg_coeff': s.get('off', 1.0) * talent['talent_weight'], # Talent boosts finishing
            'xga_coeff': s.get('def', 1.0) / talent['talent_weight'], # Talent boosts defending
            'pace': s.get('pace_factor', 1.0),
            'vol': s.get('volatility', 0.15),
            'composure': np.clip(s.get('ko_exp_weighted', 0) / 10.0, 0, 1.0),
            'p_b': pen_skill + experience
        }

def sim_match(t1, t2, knockout=False):
    t1 = t1.lower().strip() 
    t2 = t2.lower().strip()
    p1 = TEAM_PRECOMPUTE.get(t1)
    p2 = TEAM_PRECOMPUTE.get(t2)

    if not p1 or not p2: return t1, 1, 0, 'reg'

    # 1. Match Environment 
    pace = (p1['pace'] + p2['pace']) / 2
    # Knockout matches are tighter -> fewer goals = more draws = better underdog odds
    intensity = 0.82 if knockout else 1.0 
    total_match_goals = 2.70 * pace * intensity 
    
    dr = p1['elo'] - p2['elo']
    
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

def get_historical_elo(cutoff_date='2022-11-20'):
    results_df, _, _ = load_data()
    if results_df is None or 'date' not in results_df.columns: return {}

    results_df['date'] = pd.to_datetime(results_df['date'], errors='coerce')
    results_df = results_df.dropna(subset=['date'])
    results_df = results_df.sort_values('date')
    historic_df = results_df[results_df['date'] < pd.to_datetime(cutoff_date)]

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