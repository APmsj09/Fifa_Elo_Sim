import js
import asyncio
import pandas as pd
import numpy as np
import matplotlib.subplots as plt_subplots
import matplotlib.pyplot as plt
import simulation_engine as sim
from pyodide.ffi import create_proxy
from pyscript import display

# ==========================================================
# --- 2022 BACKTEST SIMULATION (Upgraded to use main engine) ---
# ==========================================================

def sim_2022_tournament():
    # 1. GROUP STAGE
    group_winners = {}
    group_runners = {}
    
    for grp, teams in sim.WC_2022_GROUPS.items():
        table = {t: {'p':0, 'gd':0, 'gf':0} for t in teams}
        
        # Shuffle for random tie-breakers (simulates drawing lots if all else is equal)
        teams_shuffled = teams.copy()
        np.random.shuffle(teams_shuffled)
        
        for i in range(len(teams_shuffled)):
            for j in range(i+1, len(teams_shuffled)):
                t1, t2 = teams_shuffled[i], teams_shuffled[j]
                
                # USE THE REAL ENGINE WE JUST TUNED!
                w, g1, g2 = sim.sim_match(t1, t2, knockout=False)
                
                # Update standings
                table[t1]['gf'] += g1
                table[t2]['gf'] += g2
                table[t1]['gd'] += (g1 - g2)
                table[t2]['gd'] += (g2 - g1)
                
                if g1 > g2: 
                    table[t1]['p'] += 3
                elif g2 > g1: 
                    table[t2]['p'] += 3
                else: 
                    table[t1]['p'] += 1
                    table[t2]['p'] += 1

        # Sort using proper FIFA tiebreakers
        sorted_teams = sorted(teams_shuffled, key=lambda t: (table[t]['p'], table[t]['gd'], table[t]['gf']), reverse=True)
        group_winners[grp] = sorted_teams[0]
        group_runners[grp] = sorted_teams[1]

    # 2. KNOCKOUT STAGE (Official 2022 Bracket Flow)
    ro16_matches = [
        (group_winners['A'], group_runners['B']), (group_winners['C'], group_runners['D']),
        (group_winners['E'], group_runners['F']), (group_winners['G'], group_runners['H']),
        (group_winners['B'], group_runners['A']), (group_winners['D'], group_runners['C']),
        (group_winners['F'], group_runners['E']), (group_winners['H'], group_runners['G'])
    ]
    
    def play_ko(t1, t2):
        # USE THE REAL ENGINE WE JUST TUNED!
        w, _, _, _ = sim.sim_match(t1, t2, knockout=True)
        return w

    quarters = []
    for t1, t2 in ro16_matches: 
        quarters.append(play_ko(t1, t2))
        
    semis = []
    for i in range(0, len(quarters), 2): 
        semis.append(play_ko(quarters[i], quarters[i+1]))
        
    finalists = []
    for i in range(0, len(semis), 2): 
        finalists.append(play_ko(semis[i], semis[i+1]))
        
    champion = play_ko(finalists[0], finalists[1])
    
    return champion, set(finalists), set(semis)


async def run_sim_backtest(event):
    out_div = js.document.getElementById("validation-text")
    chart_div = js.document.getElementById("validation-charts")
    btn = js.document.getElementById("btn-backtest-sim")
    
    prog_container = js.document.getElementById("sim-progress-container")
    prog_bar = js.document.getElementById("sim-progress-bar")
    
    # --- GET DYNAMIC SIM COUNT FROM HTML INPUT ---
    try:
        sim_count = int(js.document.getElementById("backtest-count").value)
        sim_count = max(10, min(10000, sim_count)) # Keep it between 10 and 10,000
    except:
        sim_count = 1000
        
    if btn: 
        btn.disabled = True
        btn.innerHTML = "<span class='loader-circle' style='width:12px; height:12px; border-width:2px; display:inline-block; margin:0 8px -2px 0;'></span> Running..."

    out_div.innerHTML = "Step 1: Calculating historical Elo (1872 - 2022)..."
    chart_div.innerHTML = ""
    if prog_container: 
        prog_container.style.display = "block"
        prog_bar.style.width = "0%"
    
    await asyncio.sleep(0.1)

    try:
        # 1. Fetch 2022 Elos
        elo_2022 = sim.get_historical_elo('2022-11-20')
        
        # BACKUP current 2026 Elos & TEMPORARILY override with 2022 Elos
        current_stats_backup = {t: sim.TEAM_STATS[t]['elo'] for t in sim.TEAM_STATS}
        for t in sim.WC_2022_GROUPS:
            for team in sim.WC_2022_GROUPS[t]:
                if team in elo_2022:
                    sim.TEAM_STATS[team]['elo'] = elo_2022[team]
        
        # 2. Run Simulations
        out_div.innerHTML = f"Step 2: Simulating Qatar World Cup {sim_count:,} times..."
        
        stats = {} 
        for i in range(sim_count):
            champ, finalists, semifinalists = sim_2022_tournament()
            
            def track(t, key):
                if t not in stats: stats[t] = {'win':0, 'final':0, 'semi':0}
                stats[t][key] += 1
                
            track(champ, 'win')
            for t in finalists: track(t, 'final')
            for t in semifinalists: track(t, 'semi')
            
            # Progress Bar Update
            if i % max(1, sim_count // 50) == 0:
                if prog_bar: prog_bar.style.width = f"{int((i / sim_count) * 100)}%"
                await asyncio.sleep(0.01)

        if prog_bar: prog_bar.style.width = "100%"
        await asyncio.sleep(0.2)
        
        # RESTORE the 2026 Elos so the rest of the app doesn't break
        for t, original_elo in current_stats_backup.items():
            sim.TEAM_STATS[t]['elo'] = original_elo

        # 3. Visualization: Bar Chart
        sorted_by_win = sorted(stats.items(), key=lambda x: x[1]['win'], reverse=True)
        top_5 = sorted_by_win[:5]
        
        fig, ax = plt.subplots(figsize=(8, 4))
        fig.patch.set_alpha(0.0) 
        ax.patch.set_alpha(0.0)

        teams = [x[0].title() for x in top_5]
        probs = [(x[1]['win']/sim_count)*100 for x in top_5]
        colors = ['#10b981' if 'argentina' in t.lower() else '#3b82f6' for t in teams]
        
        bars = ax.bar(teams, probs, color=colors, edgecolor='none', width=0.6, alpha=0.9)
        ax.set_ylabel("Win Probability %", color="#64748b", fontweight='bold')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#cbd5e1')
        ax.spines['bottom'].set_color('#cbd5e1')
        ax.tick_params(colors='#64748b')
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{height:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold', color='#334155')
                        
        display(fig, target="validation-charts")
        plt.close(fig)
        
        # 4. UPGRADED REPORT CARD (Data Bars UI)
        actual_results = [
            ('argentina', '🥇 Winner', '#f59e0b'), 
            ('france', '🥈 Runner-up', '#94a3b8'),
            ('croatia', '🥉 3rd', '#b45309'), 
            ('morocco', '4th', '#64748b'),
            ('england', 'Q-Finals', '#cbd5e1'), 
            ('brazil', 'Q-Finals', '#cbd5e1'), 
            ('portugal', 'Q-Finals', '#cbd5e1'), 
            ('netherlands', 'Q-Finals', '#cbd5e1')
        ]
        
        # Helper to draw data bars
        def make_bar(val, max_val, color):
            w = min(100, (val / max_val) * 100) if max_val > 0 else 0
            return f"""
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="width:45px; font-weight:600; font-size:0.9em;">{val:.1f}%</span>
                <div style="flex-grow:1; background:#f1f5f9; height:8px; border-radius:4px; overflow:hidden;">
                    <div style="width:{w}%; background:{color}; height:100%; border-radius:4px;"></div>
                </div>
            </div>
            """

        html = """
        <div style="overflow-x: auto;">
        <table class="rankings-table" style="margin-top:20px; min-width:600px;">
            <thead>
                <tr>
                    <th style="width:20%;">Team</th>
                    <th style="width:15%;">Real Result</th>
                    <th style="width:20%;">Engine: Reach Semis</th>
                    <th style="width:20%;">Engine: Reach Final</th>
                    <th style="width:25%;">Engine: Win Cup</th>
                </tr>
            </thead>
            <tbody>
        """
        for team, result, badge_color in actual_results:
            s = stats.get(team, {'win':0, 'final':0, 'semi':0})
            
            p_semi = (s['semi'] / sim_count) * 100
            p_final = (s['final'] / sim_count) * 100
            p_win = (s['win'] / sim_count) * 100
            
            html += f"""
            <tr>
                <td style="font-weight:700; color:#0f172a;">{team.title()}</td>
                <td><span style="background:{badge_color}20; color:{badge_color}; padding:4px 8px; border-radius:6px; font-weight:600; font-size:0.85em; border:1px solid {badge_color}40;">{result}</span></td>
                <td>{make_bar(p_semi, 60, '#94a3b8')}</td>
                <td>{make_bar(p_final, 40, '#3b82f6')}</td>
                <td>{make_bar(p_win, 25, '#10b981')}</td>
            </tr>
            """
        html += "</tbody></table></div>"
        
        out_div.innerHTML = html
        if prog_container: prog_container.style.display = "none"

    except Exception as e:
        out_div.innerHTML = f"<div style='color:#ef4444; padding:10px; background:#fef2f2; border:1px solid #fca5a5; border-radius:8px;'>Error: {e}</div>"
        js.console.error(f"ANALYSIS SCRIPT ERROR: {e}")
        
    finally:
        if btn:
            btn.disabled = False
            btn.innerHTML = "▶ Run Validation"

# Remove duplicate initializations
def init_analysis():
    btn = js.document.getElementById("btn-backtest-sim")
    if btn: btn.onclick = create_proxy(run_sim_backtest)

init_analysis()
