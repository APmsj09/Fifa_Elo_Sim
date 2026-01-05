import js
import asyncio
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import simulation_engine as sim
from pyodide.ffi import create_proxy
from pyscript import display
from sklearn.ensemble import RandomForestClassifier

# ==========================================================
# --- 1. SIMULATION ENGINE BACKTEST (Monte Carlo) ---
# ==========================================================

def sim_2022_tournament(elo_snapshot):
    # (Same tournament logic as before)
    # 1. GROUP STAGE
    group_winners = {}
    group_runners = {}
    
    for grp, teams in sim.WC_2022_GROUPS.items():
        points = {t: 0 for t in teams}
        gd = {t: 0 for t in teams} 
        
        for i in range(len(teams)):
            for j in range(i+1, len(teams)):
                t1, t2 = teams[i], teams[j]
                s1 = {'elo': elo_snapshot.get(t1, 1600), 'off': 1.0, 'def': 1.0}
                s2 = {'elo': elo_snapshot.get(t2, 1600), 'off': 1.0, 'def': 1.0}
                dr = s1['elo'] - s2['elo']
                we = 1 / (10**(-dr/600) + 1)
                
                lam1, lam2 = 1.3 * we, 1.3 * (1-we)
                g1, g2 = np.random.poisson(lam1), np.random.poisson(lam2)
                
                gd[t1] += (g1-g2); gd[t2] += (g2-g1)
                if g1 > g2: points[t1] += 3
                elif g2 > g1: points[t2] += 3
                else: points[t1] += 1; points[t2] += 1

        sorted_teams = sorted(teams, key=lambda t: (points[t], gd[t]), reverse=True)
        group_winners[grp] = sorted_teams[0]
        group_runners[grp] = sorted_teams[1]

    # 2. KNOCKOUT STAGE
    ro16_matches = [
        (group_winners['A'], group_runners['B']), (group_winners['C'], group_runners['D']),
        (group_winners['E'], group_runners['F']), (group_winners['G'], group_runners['H']),
        (group_winners['B'], group_runners['A']), (group_winners['D'], group_runners['C']),
        (group_winners['F'], group_runners['E']), (group_winners['H'], group_runners['G'])
    ]
    
    def play_ko(t1, t2):
        s1 = elo_snapshot.get(t1, 1600)
        s2 = elo_snapshot.get(t2, 1600)
        prob = 1 / (10**(-(s1-s2)/600) + 1)
        return t1 if np.random.random() < prob else t2

    quarters = []
    for t1, t2 in ro16_matches: quarters.append(play_ko(t1, t2))
    semis = []
    for i in range(0, len(quarters), 2): semis.append(play_ko(quarters[i], quarters[i+1]))
    finalists = []
    for i in range(0, len(semis), 2): finalists.append(play_ko(semis[i], semis[i+1]))
    champion = play_ko(finalists[0], finalists[1])
    
    return champion, set(finalists), set(semis)

async def run_sim_backtest(event):
    await run_backtest_generic('sim')

# ==========================================================
# --- 2. ML MODEL BACKTEST (Random Forest) ---
# ==========================================================

async def run_ml_backtest(event):
    await run_backtest_generic('ml')

async def train_ml_historical(cutoff_date='2022-11-20'):
    """Trains a model ONLY on data before the cutoff."""
    results_df, _, _ = sim.load_data()
    results_df['date'] = pd.to_datetime(results_df['date'])
    
    # Filter Data
    train_df = results_df[(results_df['date'] < cutoff_date) & (results_df['date'] > '2014-01-01')]
    
    # We need historical Elo to train accurately. 
    # For speed, we will approximate using the 'get_historical_elo' result for both teams
    # Note: This is a simplification. A perfect ML model would calculating rolling Elo for every row.
    # To keep it fast in browser, we assume Elo Difference is the main feature.
    
    # Get Elo at time of cutoff (Best approximation we have in memory)
    elo_snapshot = sim.get_historical_elo(cutoff_date)
    
    X, y = [], []
    for _, row in train_df.iterrows():
        h, a = row['home_team'].lower().strip(), row['away_team'].lower().strip()
        if h in elo_snapshot and a in elo_snapshot:
            diff = elo_snapshot[h] - elo_snapshot[a]
            X.append([diff])
            y.append(1 if row['home_score'] > row['away_score'] else 0)
            
    clf = RandomForestClassifier(n_estimators=100, max_depth=3, random_state=42)
    clf.fit(X, y)
    return clf, elo_snapshot

def sim_ml_tournament(clf, elo_snapshot):
    """Simulates 2022 using ML probabilities instead of Poisson."""
    # Logic is identical to Sim Engine, but the 'play_match' function changes
    
    # HELPER: Predict Winner using ML
    def predict_winner(t1, t2):
        diff = elo_snapshot.get(t1, 1200) - elo_snapshot.get(t2, 1200)
        prob_t1 = clf.predict_proba([[diff]])[0][1] # Probability of Class 1 (Home Win)
        return t1 if np.random.random() < prob_t1 else t2

    # 1. GROUP STAGE (Simplified: ML predicts raw wins)
    group_winners = {}
    group_runners = {}
    
    for grp, teams in sim.WC_2022_GROUPS.items():
        points = {t: 0 for t in teams}
        # Randomized shuffle to prevent alphabetical bias in tie-breakers
        np.random.shuffle(teams) 
        
        for i in range(len(teams)):
            for j in range(i+1, len(teams)):
                t1, t2 = teams[i], teams[j]
                winner = predict_winner(t1, t2)
                points[winner] += 3
        
        sorted_teams = sorted(teams, key=lambda t: points[t], reverse=True)
        group_winners[grp] = sorted_teams[0]
        group_runners[grp] = sorted_teams[1]

    # 2. KNOCKOUT
    ro16 = [
        (group_winners['A'], group_runners['B']), (group_winners['C'], group_runners['D']),
        (group_winners['E'], group_runners['F']), (group_winners['G'], group_runners['H']),
        (group_winners['B'], group_runners['A']), (group_winners['D'], group_runners['C']),
        (group_winners['F'], group_runners['E']), (group_winners['H'], group_runners['G'])
    ]
    
    quarters = [predict_winner(t1, t2) for t1, t2 in ro16]
    semis = [predict_winner(quarters[i], quarters[i+1]) for i in range(0, len(quarters), 2)]
    finalists = [predict_winner(semis[i], semis[i+1]) for i in range(0, len(semis), 2)]
    champion = predict_winner(finalists[0], finalists[1])
    
    return champion, set(finalists), set(semis)

# ==========================================================
# --- 3. SHARED UI & RUNNER ---
# ==========================================================

async def run_backtest_generic(mode):
    out_div = js.document.getElementById("validation-text")
    chart_div = js.document.getElementById("validation-charts")
    
    title = "🎲 SIM ENGINE" if mode == 'sim' else "🤖 ML MODEL"
    out_div.innerHTML = f"Initializing {title} Backtest..."
    chart_div.innerHTML = ""
    await asyncio.sleep(0.1)

    try:
        # 1. Prepare Data
        if mode == 'sim':
            elo_2022 = sim.get_historical_elo('2022-11-20')
            runner_func = lambda: sim_2022_tournament(elo_2022)
        else:
            out_div.innerHTML = "Training Random Forest on 2014-2022 data..."
            await asyncio.sleep(0.1)
            clf, elo_2022 = await train_ml_historical()
            runner_func = lambda: sim_ml_tournament(clf, elo_2022)

        # 2. Run Simulations
        out_div.innerHTML = f"Running 500 {title} Simulations..."
        await asyncio.sleep(0.1)
        
        sim_count = 500
        stats = {} 
        
        for i in range(sim_count):
            champ, finalists, semifinalists = runner_func()
            
            def track(t, key):
                if t not in stats: stats[t] = {'win':0, 'final':0, 'semi':0}
                stats[t][key] += 1
                
            track(champ, 'win')
            for t in finalists: track(t, 'final')
            for t in semifinalists: track(t, 'semi')
            
            if i % 100 == 0: await asyncio.sleep(0.001) # UI Breath

        # 3. Visualization
        sorted_by_win = sorted(stats.items(), key=lambda x: x[1]['win'], reverse=True)
        top_5 = sorted_by_win[:5]
        
        fig, ax = plt.subplots(figsize=(6, 4))
        teams = [x[0].title() for x in top_5]
        probs = [(x[1]['win']/sim_count)*100 for x in top_5]
        colors = ['#f1c40f' if 'argentina' in t.lower() else '#2c3e50' for t in teams]
        
        ax.bar(teams, probs, color=colors)
        ax.set_ylabel("Win %")
        ax.set_title(f"{title} Prediction (2022)", fontweight='bold')
        display(fig, target="validation-charts")
        plt.close(fig)
        
        # 4. Report Card
        actual_results = [
            ('argentina', '🥇 Winner'), ('france', '🥈 Runner-up'),
            ('croatia', '🥉 3rd'), ('morocco', '4th')
        ]
        
        html = f"""
        <h3 style="margin-top:10px; border-bottom:1px solid #ddd;">{title} Report Card</h3>
        <table style="width:100%; border-collapse:collapse; font-size:0.85em;">
            <tr style="background:#2c3e50; color:white; text-align:left;">
                <th style="padding:8px;">Team</th>
                <th style="padding:8px;">Real Result</th>
                <th style="padding:8px;">Win %</th>
            </tr>
        """
        for team, result in actual_results:
            s = stats.get(team, {'win':0})
            p_win = (s['win'] / sim_count) * 100
            html += f"<tr><td style='padding:8px;'>{team.title()}</td><td>{result}</td><td style='font-weight:bold;'>{p_win:.1f}%</td></tr>"
        html += "</table>"
        
        out_div.innerHTML = html

    except Exception as e:
        out_div.innerHTML = f"Error: {e}"
        js.console.error(e)

# ==========================================================
# --- 3. INIT ---
# ==========================================================
def init_analysis():
    # Bind Sim Button
    btn_sim = js.document.getElementById("btn-backtest-sim")
    if btn_sim: btn_sim.onclick = create_proxy(run_sim_backtest)
        
    # Bind ML Button
    btn_ml = js.document.getElementById("btn-backtest-ml")
    if btn_ml: btn_ml.onclick = create_proxy(run_ml_backtest)

init_analysis()