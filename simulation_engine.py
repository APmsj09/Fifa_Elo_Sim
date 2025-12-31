import pandas as pd
import numpy as np
import random
import math

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
    ('Hero Ball', 'Balanced'): 1.05,
    ('Balanced', 'Hero Ball'): 1.0,
    ('Diesel Engine', 'Blitzkrieg'): 1.1,
    ('Dark Arts', 'Hero Ball'): 1.05,
    ('Blitzkrieg', 'Dark Arts'): 1.1
}

def load_data():
    """
    Loads data assuming all files are now standard CSVs.
    """
    try:
        former_names_df = pd.read_csv("former_names.csv")
        results_df = pd.read_csv("results.csv") 
        goalscorers_df = pd.read_csv("goalscorers.csv")
        return results_df, goalscorers_df, former_names_df
    except Exception as e:
        print(f"CRITICAL ERROR LOADING DATA: {e}")
        return None, None, None

# =============================================================================
# --- PART 2: INITIALIZATION (OPTIMIZED) ---
# =============================================================================

def initialize_engine():
    results_df, goalscorers_df, former_names_df = load_data()
    
    if results_df is None:
        return {}, {}, {}, 2.5 # Added extra return for history

    # --- 1. CLEAN DATA ---
    results_df['date'] = pd.to_datetime(results_df['date'], errors='coerce')
    results_df = results_df.dropna(subset=['date', 'home_score', 'away_score'])
    results_df = results_df.astype({'home_score': int, 'away_score': int})
    
    results_df['home_team'] = results_df['home_team'].str.lower().str.strip()
    results_df['away_team'] = results_df['away_team'].str.lower().str.strip()
    
    former_map = dict(zip(former_names_df['former'].str.lower(), former_names_df['current'].str.lower()))
    results_df['home_team'] = results_df['home_team'].replace(former_map)
    results_df['away_team'] = results_df['away_team'].replace(former_map)
    
    elo_df = results_df.sort_values('date')

    # --- 2. CALCULATE ELO & HISTORY ---
    team_elo = {}
    INITIAL_RATING = 1200
    
    # Initialize history dict
    global TEAM_HISTORY
    TEAM_HISTORY = {} 

    # We add 'date' to the zip loop to track when changes happen
    matches_data = zip(
        elo_df['home_team'].tolist(),
        elo_df['away_team'].tolist(),
        elo_df['home_score'].tolist(),
        elo_df['away_score'].tolist(),
        elo_df['tournament'].tolist(),
        elo_df['neutral'].tolist(),
        elo_df['date'].tolist() 
    )

    for h, a, hs, as_, tourney, neutral, date in matches_data:
        rh = team_elo.get(h, INITIAL_RATING)
        ra = team_elo.get(a, INITIAL_RATING)
        
        # Initialize history list if new team
        if h not in TEAM_HISTORY: TEAM_HISTORY[h] = {'dates': [], 'elo': []}
        if a not in TEAM_HISTORY: TEAM_HISTORY[a] = {'dates': [], 'elo': []}

        dr = rh - ra + (100 if not neutral else 0)
        we = 1 / (10**(-dr/600) + 1)
        
        if hs > as_: W = 1
        elif as_ > hs: W = 0
        else: W = 0.5
        
        gd = abs(hs - as_)
        k = 20
        if 'World Cup' in str(tourney): k = 60
        elif 'Continental' in str(tourney) or 'Euro' in str(tourney): k = 50
        elif 'Qualification' in str(tourney): k = 40
        
        if gd == 2: k *= 1.5
        elif gd == 3: k *= 1.75
        elif gd >= 4: k *= (1.75 + (gd-3)/8)
        
        change = k * (W - we)
        
        # Update Ratings
        team_elo[h] = rh + change
        team_elo[a] = ra - change
        
        # SAVE HISTORY (For Charts)
        # We only save the new rating and date
        TEAM_HISTORY[h]['dates'].append(date)
        TEAM_HISTORY[h]['elo'].append(team_elo[h])
        TEAM_HISTORY[a]['dates'].append(date)
        TEAM_HISTORY[a]['elo'].append(team_elo[a])

    # --- 3. CALCULATE OFF/DEF RATINGS ---
    # Filter for recent games only
    recent_date = pd.Timestamp('2022-01-01')
    recent_df = elo_df[elo_df['date'] > recent_date]
    
    if len(recent_df) > 0:
        avg_goals_global = (recent_df['home_score'].mean() + recent_df['away_score'].mean()) / 2
    else:
        avg_goals_global = 2.5

    # Calculate Off/Def stats using groupby (Much faster than per-team filtering)
    home_stats = recent_df.groupby('home_team').agg({'home_score': 'sum', 'away_score': 'sum', 'date': 'count'}).rename(columns={'date': 'matches'})
    away_stats = recent_df.groupby('away_team').agg({'away_score': 'sum', 'home_score': 'sum', 'date': 'count'}).rename(columns={'date': 'matches'})
    
    all_teams = set(team_elo.keys())
    team_stats = {}

    for team in all_teams:
        elo = team_elo[team]
        
        # Combine home and away stats safely
        h_s = home_stats.loc[team] if team in home_stats.index else pd.Series({'home_score':0, 'away_score':0, 'matches':0})
        a_s = away_stats.loc[team] if team in away_stats.index else pd.Series({'away_score':0, 'home_score':0, 'matches':0})
        
        total_matches = h_s['matches'] + a_s['matches']
        
        if total_matches < 5:
            off, def_ = 1.0, 1.0
        else:
            gs = h_s['home_score'] + a_s['away_score'] # Goals Scored
            gc = h_s['away_score'] + a_s['home_score'] # Goals Conceded
            
            off = (gs / total_matches) / avg_goals_global
            def_ = (gc / total_matches) / avg_goals_global
            
        team_stats[team] = {'elo': elo, 'off': off, 'def': def_}

    # --- 4. PROFILES (Optimized Groupby) ---
    team_profiles = {}
    
    # Prep Goalscorers
    goalscorers_df['team'] = goalscorers_df['team'].str.lower().str.strip()
    goalscorers_df['scorer'] = goalscorers_df['scorer'].str.strip()
    goalscorers_df['date'] = pd.to_datetime(goalscorers_df['date'], errors='coerce')
    
    # Helpers for profile logic
    def get_clean_min(m):
        try: return int(str(m).split('+')[0])
        except: return 0
    goalscorers_df['clean_min'] = goalscorers_df['minute'].apply(get_clean_min)
    
    recent_goals = goalscorers_df[goalscorers_df['date'] > '2018-01-01']
    
    # Group by team
    grouped_goals = recent_goals.groupby('team')
    
    for team, t_goals in grouped_goals:
        total = len(t_goals)
        if total < 10:
            team_profiles[team] = 'Balanced'
            continue
            
        late = len(t_goals[t_goals['clean_min'] >= 75])
        pens = len(t_goals[t_goals['penalty'].astype(str) == 'TRUE'])
        early = len(t_goals[t_goals['clean_min'] <= 20])
        
        hero_counts = t_goals['scorer'].value_counts()
        hero_reliance = (hero_counts.iloc[0] / total) if not hero_counts.empty else 0
        
        if hero_reliance > 0.30: style = "Hero Ball"
        elif (pens / total) > 0.15: style = "Dark Arts"
        elif (late / total) > 0.30: style = "Diesel Engine"
        elif (early / total) > 0.25: style = "Blitzkrieg"
        else: style = "Balanced"
        
        team_profiles[team] = style

    return team_stats, team_profiles, avg_goals_global

# =============================================================================
# --- PART 3: SIMULATION ---
# =============================================================================

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
    
    # Home Advantage
    hosts = ['usa', 'mexico', 'canada']
    home_boost = 1.15 if t1 in hosts else 1.0
    away_boost = 1.15 if t2 in hosts else 1.0

    # 1. REGULAR TIME (90 Mins)
    lam1 = AVG_GOALS * s1['off'] * s2['def'] * elo_scale * mod1 * home_boost
    lam2 = AVG_GOALS * s2['off'] * s1['def'] * (2 - elo_scale) * mod2 * away_boost
    
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

def run_simulation(verbose=False, quiet=False):
    # Data containers for visualization
    structured_groups = {}
    structured_bracket = []

    # --- PLAYOFFS (Simplified) ---
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

    # Inter-confederation playoffs
    # Assuming bracket logic: (Jamaica vs (DR Congo vs New Caledonia))
    w_ofc, _, _, _ = sim_match('dr congo', 'new caledonia', knockout=True)
    w_icp1, _, _, _ = sim_match('jamaica', w_ofc, knockout=True)
    slots['ICP1'] = w_icp1
    
    w_conmebol, _, _, _ = sim_match('bolivia', 'suriname', knockout=True)
    w_icp2, _, _, _ = sim_match('iraq', w_conmebol, knockout=True)
    slots['ICP2'] = w_icp2

    # --- GROUPS ---
    groups = {
        'A': ['mexico', 'south africa', 'south korea', slots['Path D']],
        'B': ['canada', 'switzerland', 'qatar', slots['Path A']],
        'C': ['brazil', 'morocco', 'haiti', 'scotland'],
        'D': ['usa', 'paraguay', 'australia', slots['Path C']],
        'E': ['germany', 'curacao', 'ivory coast', 'ecuador'],
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
        
        # Round Robin
        for i in range(len(teams)):
            for j in range(i+1, len(teams)):
                t1, t2 = teams[i], teams[j]
                w, g1, g2 = sim_match(t1, t2)
                
                table_stats[t1]['gf'] += g1; table_stats[t1]['gd'] += (g1-g2)
                table_stats[t2]['gf'] += g2; table_stats[t2]['gd'] += (g2-g1)
                
                if g1 > g2:
                    table_stats[t1]['p'] += 3; table_stats[t1]['w'] += 1; table_stats[t2]['l'] += 1
                elif g2 > g1:
                    table_stats[t2]['p'] += 3; table_stats[t2]['w'] += 1; table_stats[t1]['l'] += 1
                else:
                    table_stats[t1]['p'] += 1; table_stats[t2]['p'] += 1
                    table_stats[t1]['d'] += 1; table_stats[t2]['d'] += 1

        # Sort: Points -> GD -> GF
        sorted_teams = sorted(teams, key=lambda t: (table_stats[t]['p'], table_stats[t]['gd'], table_stats[t]['gf']), reverse=True)
        group_results_lists[grp] = sorted_teams
        third_place.append({'team': sorted_teams[2], 'stats': table_stats[sorted_teams[2]]})

        # Save structured data
        structured_groups[grp] = []
        for t in sorted_teams:
             structured_groups[grp].append({'team': t, **table_stats[t]})

    # --- KNOCKOUT PREP ---
    advancing = []
    # Top 2 from each group
    for g in groups: advancing.extend(group_results_lists[g][:2])
    
    # Best 8 third-place teams
    best_3rds = sorted(third_place, key=lambda x: (x['stats']['p'], x['stats']['gd'], x['stats']['gf']), reverse=True)[:8]
    advancing.extend([x['team'] for x in best_3rds])
    
    # Bracket Seeding (Simplified: Seed by Elo)
    seeded = sorted(advancing, key=lambda t: TEAM_STATS.get(t, {}).get('elo', 0), reverse=True)
    
    # Create Matchups (Top vs Bottom)
    bracket_matchups = []
    n = len(seeded)
    for i in range(n//2):
        bracket_matchups.append((seeded[i], seeded[n-1-i]))
        
    rounds = ['Round of 32', 'Round of 16', 'Quarter-finals', 'Semi-finals', 'Final']
    champion = None
    
    # --- KNOCKOUT SIMULATION ---
    for r_name in rounds:
        round_results = []
        next_round_teams = []
        
        for t1, t2 in bracket_matchups:
            w, g1, g2, method = sim_match(t1, t2, knockout=True)
            next_round_teams.append(w)
            round_results.append({
                't1': t1, 't2': t2, 'g1': g1, 'g2': g2, 
                'winner': w, 'method': method
            })
        
        structured_bracket.append({'round': r_name, 'matches': round_results})
        
        if len(next_round_teams) == 1:
             champion = next_round_teams[0]
        else:
            # Re-pair for next round (Winners play Winners)
            bracket_matchups = []
            for i in range(0, len(next_round_teams), 2):
                if i+1 < len(next_round_teams):
                     bracket_matchups.append((next_round_teams[i], next_round_teams[i+1]))

    return {
        "champion": champion,
        "groups_data": structured_groups,
        "bracket_data": structured_bracket
    }