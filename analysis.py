import js
import asyncio
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import simulation_engine as sim
from pyodide.ffi import create_proxy
from pyscript import display

# ==========================================================
# --- 2022 BACKTEST SIMULATION (Standard Engine) ---
# ==========================================================

def sim_2022_tournament(elo_snapshot):
    # 1. GROUP STAGE
    group_winners = {}
    group_runners = {}
    
    for grp, teams in sim.WC_2022_GROUPS.items():
        points = {t: 0 for t in teams}
        gd = {t: 0 for t in teams} 
        
        # Shuffle for random tie-breakers
        teams_shuffled = teams.copy()
        np.random.shuffle(teams_shuffled)
        
        for i in range(len(teams_shuffled)):
            for j in range(i+1, len(teams_shuffled)):
                t1, t2 = teams_shuffled[i], teams_shuffled[j]
                
                # Manual Match Sim
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

        sorted_teams = sorted(teams_shuffled, key=lambda t: (points[t], gd[t]), reverse=True)
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
    out_div = js.document.getElementById("validation-text")
    chart_div = js.document.getElementById("validation-charts")
    btn = js.document.getElementById("btn-backtest-sim")
    
    # Progress Bar Elements
    prog_container = js.document.getElementById("sim-progress-container")
    prog_bar = js.document.getElementById("sim-progress-bar")
    
    if btn: 
        btn.disabled = True
        btn.innerText = "⏳ Running..."

    # Reset UI
    out_div.innerHTML = "Step 1: Calculating historical Elo (1872 - 2022)..."
    chart_div.innerHTML = ""
    if prog_container: 
        prog_container.style.display = "block"
        prog_bar.style.width = "0%"
    
    await asyncio.sleep(0.1)

    try:
        # 1. Prepare Data
        elo_2022 = sim.get_historical_elo('2022-11-20')
        
        # 2. Run Simulations
        sim_count = 1000
        out_div.innerHTML = f"Step 2: Simulating Qatar World Cup {sim_count} times..."
        
        stats = {} 
        for i in range(sim_count):
            champ, finalists, semifinalists = sim_2022_tournament(elo_2022)
            
            def track(t, key):
                if t not in stats: stats[t] = {'win':0, 'final':0, 'semi':0}
                stats[t][key] += 1
                
            track(champ, 'win')
            for t in finalists: track(t, 'final')
            for t in semifinalists: track(t, 'semi')
            
            # Update Progress Bar every 20 iterations (keeps UI smooth)
            if i % 20 == 0:
                pct = (i / sim_count) * 100
                if prog_bar: prog_bar.style.width = f"{pct}%"
                await asyncio.sleep(0.001)

        # Finalize Progress
        if prog_bar: prog_bar.style.width = "100%"
        await asyncio.sleep(0.2) # Small pause to let user see 100%

        # 3. Visualization
        sorted_by_win = sorted(stats.items(), key=lambda x: x[1]['win'], reverse=True)
        top_5 = sorted_by_win[:5]
        
        fig, ax = plt.subplots(figsize=(7, 4))
        teams = [x[0].title() for x in top_5]
        probs = [(x[1]['win']/sim_count)*100 for x in top_5]
        colors = ['#f1c40f' if 'argentina' in t.lower() else '#3498db' for t in teams]
        
        bars = ax.bar(teams, probs, color=colors)
        ax.set_ylabel("Win %")
        ax.set_title(f"Engine Prediction for 2022 (Based on {sim_count} Sims)", fontweight='bold')
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%', ha='center', va='bottom', fontsize=9)
                        
        display(fig, target="validation-charts")
        plt.close(fig)
        
        # 4. Report Card
        actual_results = [
            ('argentina', '🥇 Winner'), ('france', '🥈 Runner-up'),
            ('croatia', '🥉 3rd'), ('morocco', '4th'),
            ('england', 'Q-Finals'), ('brazil', 'Q-Finals'), 
            ('portugal', 'Q-Finals'), ('netherlands', 'Q-Finals')
        ]
        
        html = """
        <table style="width:100%; border-collapse:collapse; font-size:0.9em; margin-top:20px;">
            <tr style="background:#2c3e50; color:white; text-align:left;">
                <th style="padding:10px;">Team</th>
                <th style="padding:10px;">Real Result</th>
                <th style="padding:10px; background:#34495e;">Reach Semis</th>
                <th style="padding:10px; background:#2980b9;">Reach Final</th>
                <th style="padding:10px; background:#f1c40f; color:#2c3e50;">Win Cup</th>
            </tr>
        """
        for team, result in actual_results:
            s = stats.get(team, {'win':0, 'final':0, 'semi':0})
            
            p_semi = (s['semi'] / sim_count) * 100
            p_final = (s['final'] / sim_count) * 100
            p_win = (s['win'] / sim_count) * 100
            
            html += f"""
            <tr style="border-bottom:1px solid #ddd;">
                <td style="padding:10px; font-weight:bold;">{team.title()}</td>
                <td style="padding:10px;">{result}</td>
                <td style="padding:10px;">{p_semi:.1f}%</td>
                <td style="padding:10px;">{p_final:.1f}%</td>
                <td style="padding:10px; font-weight:bold;">{p_win:.1f}%</td>
            </tr>
            """
        html += "</table>"
        
        out_div.innerHTML = html
        
        # Hide progress bar after completion
        if prog_container: prog_container.style.display = "none"

    except Exception as e:
        out_div.innerHTML = f"Error: {e}"
        js.console.error(e)
        
    finally:
        if btn:
            btn.disabled = False
            btn.innerText = "▶ Run Simulation Check"

# ==========================================================
# --- INIT ---
# ==========================================================
def init_analysis():
    btn = js.document.getElementById("btn-backtest-sim")
    if btn: btn.onclick = create_proxy(run_sim_backtest)

init_analysis()