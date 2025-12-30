# =============================================================================
# --- FIFA WORLD CUP 2026 PREDICTOR (WEB ENGINE VERSION) ---
# =============================================================================
import pandas as pd
import numpy as np
import random
import os

# =============================================================================
# --- PART 1: SETUP & DATA LOADING ---
# =============================================================================

# Default to a 'data' folder in the same directory as this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "." 

def load_data():
    """
    Loads data from the virtual file system.
    Handles TSV format for results/goals and CSV for names.
    """
    try:
        # 1. Construct Paths
        former_path = os.path.join(DATA_DIR, 'former_names.csv')
        results_path = os.path.join(DATA_DIR, 'results.tsv')      # <--- Changed to .tsv
        goals_path = os.path.join(DATA_DIR, 'goalscorers.tsv')    # <--- Changed to .tsv
        
        # 2. Read Files
        # former_names is standard CSV (comma separated)
        former_names_df = pd.read_csv(former_path)
        
        # results and goalscorers are TSV (Tab Separated)
        # We MUST specify sep='\t' or pandas won't split the columns correctly
        results_df = pd.read_csv(results_path, sep='\t')
        goalscorers_df = pd.read_csv(goals_path, sep='\t')
        
        return results_df, goalscorers_df, former_names_df

    except FileNotFoundError as e:
        return None, None, None


# =============================================================================
# --- PART 2: INITIALIZATION (Run once on startup) ---
# =============================================================================

def initialize_engine():
    """
    Calculates Elo and Profiles once when the app starts.
    Returns: (team_stats, team_profiles, avg_goals_global)
    """
    results_df, goalscorers_df, former_names_df = load_data()
    
    if results_df is None:
        return {}, {}, 2.5 # Fallback defaults

    # --- 1. CLEAN DATA ---
    results_df['date'] = pd.to_datetime(results_df['date'])
    results_df['home_team'] = results_df['home_team'].str.lower().str.strip()
    results_df['away_team'] = results_df['away_team'].str.lower().str.strip()
    
    former_map = dict(zip(former_names_df['former'].str.lower(), former_names_df['current'].str.lower()))
    results_df['home_team'] = results_df['home_team'].replace(former_map)
    results_df['away_team'] = results_df['away_team'].replace(former_map)
    
    elo_df = results_df.sort_values('date').copy()

    # --- 2. CALCULATE ELO ---
    team_elo = {}
    INITIAL_RATING = 1200
    
    def get_k(tournament, gd):
        k = 20
        if 'World Cup' in tournament: k = 60
        elif 'Continental' in tournament or 'Euro' in tournament: k = 50
        elif 'Qualification' in tournament: k = 40
        if gd == 2: k *= 1.5
        elif gd == 3: k *= 1.75
        elif gd >= 4: k *= (1.75 + (gd-3)/8)
        return k

    for _, row in elo_df.iterrows():
        h, a = row['home_team'], row['away_team']
        hs, as_ = row['home_score'], row['away_score']
        rh = team_elo.get(h, INITIAL_RATING)
        ra = team_elo.get(a, INITIAL_RATING)
        
        dr = rh - ra + 100 if not row['neutral'] else rh - ra
        we = 1 / (10**(-dr/600) + 1)
        
        if hs > as_: W = 1
        elif as_ > hs: W = 0
        else: W = 0.5
        
        k = get_k(str(row['tournament']), abs(hs-as_))
        change = k * (W - we)
        team_elo[h] = rh + change
        team_elo[a] = ra - change

    # --- 3. OFFENSE/DEFENSE STATS ---
    recent_df = elo_df[elo_df['date'] > '2022-01-01']
    avg_goals_global = (recent_df['home_score'].mean() + recent_df['away_score'].mean()) / 2
    
    team_stats = {}
    for team in team_elo.keys():
        games = recent_df[(recent_df['home_team'] == team) | (recent_df['away_team'] == team)]
        if len(games) < 5:
            off, def_ = 1.0, 1.0
        else:
            gs = games[games['home_team']==team]['home_score'].sum() + games[games['away_team']==team]['away_score'].sum()
            gc = games[games['home_team']==team]['away_score'].sum() + games[games['away_team']==team]['home_score'].sum()
            matches = len(games)
            off = (gs / matches) / avg_goals_global
            def_ = (gc / matches) / avg_goals_global
        team_stats[team] = {'elo': team_elo[team], 'off': off, 'def': def_}

    # --- 4. TACTICAL PROFILES ---
    goalscorers_df['team'] = goalscorers_df['team'].str.lower().str.strip()
    goalscorers_df['scorer'] = goalscorers_df['scorer'].str.strip()
    goalscorers_df['penalty'] = goalscorers_df['penalty'].astype(str).str.upper() == 'TRUE'
    
    def clean_min(m):
        try: return int(str(m).split('+')[0])
        except: return 0
    goalscorers_df['clean_min'] = goalscorers_df['minute'].apply(clean_min)
    
    team_profiles = {}
    recent_goals = goalscorers_df[goalscorers_df['date'] > '2018-01-01']
    
    for team in team_elo.keys():
        t_goals = recent_goals[recent_goals['team'] == team]
        if len(t_goals) < 10:
            team_profiles[team] = 'Balanced'
            continue
        total = len(t_goals)
        late = len(t_goals[t_goals['clean_min'] >= 75])
        pens = len(t_goals[t_goals['penalty'] == True])
        
        if not t_goals.empty:
            hero_reliance = t_goals['scorer'].value_counts().iloc[0] / total
        else: hero_reliance = 0

        if hero_reliance > 0.30: style = "Hero Ball"
        elif (pens / total) > 0.15: style = "Dark Arts"
        elif (late / total) > 0.30: style = "Diesel Engine"
        elif (len(t_goals[t_goals['clean_min']<=20]) / total) > 0.25: style = "Blitzkrieg"
        else: style = "Balanced"
        team_profiles[team] = style

    return team_stats, team_profiles, avg_goals_global

# Load stats globally so they are ready for the web function
TEAM_STATS, TEAM_PROFILES, AVG_GOALS = initialize_engine()

# =============================================================================
# --- PART 3: SIMULATION FUNCTIONS ---
# =============================================================================

STYLE_MATRIX = {
    ('Hero Ball', 'Balanced'): 1.05,
    ('Balanced', 'Hero Ball'): 1.0,
    ('Diesel Engine', 'Blitzkrieg'): 1.1,
    ('Dark Arts', 'Hero Ball'): 1.05,
    ('Blitzkrieg', 'Dark Arts'): 1.1
}

def sim_match(t1, t2, knockout=False):
    s1 = TEAM_STATS.get(t1, {'elo':1200, 'off':1.0, 'def':1.0})
    s2 = TEAM_STATS.get(t2, {'elo':1200, 'off':1.0, 'def':1.0})
    
    dr = s1['elo'] - s2['elo']
    we = 1 / (10**(-dr/600) + 1)
    
    style1 = TEAM_PROFILES.get(t1, 'Balanced')
    style2 = TEAM_PROFILES.get(t2, 'Balanced')
    mod1 = STYLE_MATRIX.get((style1, style2), 1.0)
    mod2 = STYLE_MATRIX.get((style2, style1), 1.0)
    
    elo_scale = 1 + (we - 0.5)
    home_boost = 1.15 if t1 in ['usa', 'mexico', 'canada'] else 1.0
    away_boost = 1.15 if t2 in ['usa', 'mexico', 'canada'] else 1.0

    lam1 = AVG_GOALS * s1['off'] * s2['def'] * elo_scale * mod1 * home_boost
    lam2 = AVG_GOALS * s2['off'] * s1['def'] * (2 - elo_scale) * mod2 * away_boost
    
    g1 = np.random.poisson(lam1)
    g2 = np.random.poisson(lam2)
    
    if g1 > g2: 
        if knockout: return t1, g1, g2, 'reg'
        return t1, g1, g2
    elif g2 > g1: 
        if knockout: return t2, g1, g2, 'reg'
        return t2, g1, g2
    else:
        if knockout:
            p1_bonus = 0.1 if style1 == 'Dark Arts' else 0
            p2_bonus = 0.1 if style2 == 'Dark Arts' else 0
            pk_prob = 0.5 + (dr/3000) + (p1_bonus - p2_bonus)
            winner = t1 if random.random() < pk_prob else t2
            return winner, g1, g2, 'pks'
        return 'draw', g1, g2

def run_simulation(verbose=False):
    """
    Main entry point for the web app.
    Returns a Dictionary containing the champion and a log of events.
    """
    game_log = [] # This list will hold the "commentary" for the web page
    
    def log(msg):
        if verbose: game_log.append(msg)

    # --- PLAYOFFS ---
    log("=== MARCH 2026 PLAYOFFS ===")
    slots = {}
    
    # Simulate UEFA Paths
    uefa_paths = {
        'Path A': [('italy', 'northern ireland'), ('wales', 'bosnia and herzegovina')],
        'Path B': [('ukraine', 'sweden'), ('poland', 'albania')],
        'Path C': [('turkey', 'romania'), ('slovakia', 'kosovo')],
        'Path D': [('czech republic', 'republic of ireland'), ('denmark', 'north macedonia')]
    }
    
    for path, semis in uefa_paths.items():
        finalists = []
        for t1, t2 in semis:
            w, g1, g2, _ = sim_match(t1, t2, knockout=True)
            finalists.append(w)
        w_final, g1, g2, type_ = sim_match(finalists[0], finalists[1], knockout=True)
        method = "(PKs)" if type_ == 'pks' else ""
        log(f"{path}: {finalists[0].title()} {g1}-{g2} {finalists[1].title()} {method} -> {w_final.title()}")
        slots[path] = w_final

    # Simulate Inter-confederation
    w_icp1, g1, g2, _ = sim_match('jamaica', sim_match('dr congo', 'new caledonia', knockout=True)[0], knockout=True)
    slots['ICP1'] = w_icp1
    
    w_icp2, g1, g2, _ = sim_match('iraq', sim_match('bolivia', 'suriname', knockout=True)[0], knockout=True)
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
    
    log("\n=== GROUP STAGE ===")
    group_results = {}
    third_place = []
    
    for grp, teams in groups.items():
        table = {t: {'p':0, 'gd':0, 'gf':0} for t in teams}
        for i in range(len(teams)):
            for j in range(i+1, len(teams)):
                t1, t2 = teams[i], teams[j]
                w, g1, g2 = sim_match(t1, t2)
                table[t1]['gf'] += g1; table[t1]['gd'] += (g1-g2)
                table[t2]['gf'] += g2; table[t2]['gd'] += (g2-g1)
                if w == t1: table[t1]['p'] += 3
                elif w == t2: table[t2]['p'] += 3
                else: table[t1]['p'] += 1; table[t2]['p'] += 1
                
        sorted_teams = sorted(teams, key=lambda t: (table[t]['p'], table[t]['gd']), reverse=True)
        group_results[grp] = sorted_teams
        third_place.append({'team': sorted_teams[2], 'stats': table[sorted_teams[2]]})
        log(f"Group {grp}: 1.{sorted_teams[0].title()} 2.{sorted_teams[1].title()}")

    # --- KNOCKOUTS ---
    advancing = []
    for g in groups: advancing.extend(group_results[g][:2])
    best_3rds = sorted(third_place, key=lambda x: (x['stats']['p'], x['stats']['gd']), reverse=True)[:8]
    advancing.extend([x['team'] for x in best_3rds])
    
    seeded = sorted(advancing, key=lambda t: TEAM_STATS.get(t, {}).get('elo', 0), reverse=True)
    bracket = []
    n = len(seeded)
    for i in range(n//2):
        bracket.append((seeded[i], seeded[n-1-i]))
        
    rounds = ['Round of 32', 'Round of 16', 'Quarter-finals', 'Semi-finals', 'Final']
    champion = None
    
    log("\n=== KNOCKOUT STAGE ===")
    for r in rounds:
        log(f"--- {r} ---")
        next_round = []
        for t1, t2 in bracket:
            w, g1, g2, method = sim_match(t1, t2, knockout=True)
            note = "(PKs)" if method == 'pks' else ""
            log(f"{t1.title()} {g1}-{g2} {t2.title()} {note} -> {w.title()}")
            next_round.append(w)
        
        if len(next_round) == 1: champion = next_round[0]
        else:
            bracket = []
            for i in range(0, len(next_round), 2):
                if i+1 < len(next_round): bracket.append((next_round[i], next_round[i+1]))

    # Return a structured dictionary for the Web Page to read
    return {
        "champion": champion,
        "logs": game_log
    }
