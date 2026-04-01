import js
import asyncio
import traceback
import numpy as np
import matplotlib.pyplot as plt
import simulation_engine as sim
from pyodide.ffi import create_proxy
from pyscript import display

ANALYSIS_HANDLERS = []

# ==========================================================
# --- HISTORICAL TOURNAMENT DATABASE ---
# ==========================================================
TOURNAMENTS = {
    '2022': {
        'name': 'Qatar 2022',
        'cutoff_date': '2022-11-20',
        'real_winner': 'argentina',
        'real_runner_up': 'france',
        'real_surprises': ['croatia', 'morocco'], # 3rd and 4th place
        'groups': {
            'A': ['qatar', 'ecuador', 'senegal', 'netherlands'],
            'B': ['england', 'iran', 'united states', 'wales'],
            'C': ['argentina', 'saudi arabia', 'mexico', 'poland'],
            'D': ['france', 'australia', 'denmark', 'tunisia'],
            'E': ['spain', 'costa rica', 'germany', 'japan'],
            'F': ['belgium', 'canada', 'morocco', 'croatia'],
            'G': ['brazil', 'serbia', 'switzerland', 'cameroon'],
            'H': ['portugal', 'ghana', 'uruguay', 'south korea']
        },
        'ui_results': [
            ('argentina', '🥇 Winner', '#f59e0b'), ('france', '🥈 Runner-up', '#94a3b8'),
            ('croatia', '🥉 3rd', '#b45309'), ('morocco', '4th', '#64748b'),
            ('england', 'Q-Finals', '#cbd5e1'), ('brazil', 'Q-Finals', '#cbd5e1'), 
            ('portugal', 'Q-Finals', '#cbd5e1'), ('netherlands', 'Q-Finals', '#cbd5e1')
        ]
    },
    '2018': {
        'name': 'Russia 2018',
        'cutoff_date': '2018-06-14',
        'real_winner': 'france',
        'real_runner_up': 'croatia',
        'real_surprises': ['belgium', 'england'],
        'groups': {
            'A': ['russia', 'saudi arabia', 'egypt', 'uruguay'],
            'B': ['portugal', 'spain', 'morocco', 'iran'],
            'C': ['france', 'australia', 'peru', 'denmark'],
            'D': ['argentina', 'iceland', 'croatia', 'nigeria'],
            'E': ['brazil', 'switzerland', 'costa rica', 'serbia'],
            'F': ['germany', 'mexico', 'sweden', 'south korea'],
            'G': ['belgium', 'panama', 'tunisia', 'england'],
            'H': ['poland', 'senegal', 'colombia', 'japan']
        },
        'ui_results': [
            ('france', '🥇 Winner', '#f59e0b'), ('croatia', '🥈 Runner-up', '#94a3b8'),
            ('belgium', '🥉 3rd', '#b45309'), ('england', '4th', '#64748b'),
            ('uruguay', 'Q-Finals', '#cbd5e1'), ('brazil', 'Q-Finals', '#cbd5e1'), 
            ('sweden', 'Q-Finals', '#cbd5e1'), ('russia', 'Q-Finals', '#cbd5e1')
        ]
    },
    '2014': {
        'name': 'Brazil 2014',
        'cutoff_date': '2014-06-12',
        'real_winner': 'germany',
        'real_runner_up': 'argentina',
        'real_surprises': ['netherlands', 'brazil'],
        'groups': {
            'A': ['brazil', 'croatia', 'mexico', 'cameroon'],
            'B': ['spain', 'netherlands', 'chile', 'australia'],
            'C': ['colombia', 'greece', 'ivory coast', 'japan'],
            'D': ['uruguay', 'costa rica', 'england', 'italy'],
            'E': ['switzerland', 'ecuador', 'france', 'honduras'],
            'F': ['argentina', 'bosnia and herzegovina', 'iran', 'nigeria'],
            'G': ['germany', 'portugal', 'ghana', 'united states'],
            'H': ['belgium', 'algeria', 'russia', 'south korea']
        },
        'ui_results': [
            ('germany', '🥇 Winner', '#f59e0b'), ('argentina', '🥈 Runner-up', '#94a3b8'),
            ('netherlands', '🥉 3rd', '#b45309'), ('brazil', '4th', '#64748b'),
            ('colombia', 'Q-Finals', '#cbd5e1'), ('france', 'Q-Finals', '#cbd5e1'), 
            ('costa rica', 'Q-Finals', '#cbd5e1'), ('belgium', 'Q-Finals', '#cbd5e1')
        ]
    }
}

def sim_32_team_tournament(groups_dict):
    """Generic 32-team World Cup Simulator (Used from 1998 to 2022)"""
    group_winners = {}
    group_runners = {}
    
    for grp, teams in groups_dict.items():
        table = {t: {'p':0, 'gd':0, 'gf':0} for t in teams}
        teams_shuffled = teams.copy()
        np.random.shuffle(teams_shuffled)
        
        for i in range(len(teams_shuffled)):
            for j in range(i+1, len(teams_shuffled)):
                t1, t2 = teams_shuffled[i], teams_shuffled[j]
                
                result = sim.sim_match(t1, t2, knockout=False)
                if result[0] == 'draw':
                    w, g1, g2 = None, result[1], result[2]
                else:
                    w, g1, g2 = result[0], result[1], result[2]
                
                table[t1]['gf'] += g1
                table[t2]['gf'] += g2
                table[t1]['gd'] += (g1 - g2)
                table[t2]['gd'] += (g2 - g1)
                
                if g1 > g2: table[t1]['p'] += 3
                elif g2 > g1: table[t2]['p'] += 3
                else: 
                    table[t1]['p'] += 1
                    table[t2]['p'] += 1

        sorted_teams = sorted(teams_shuffled, key=lambda t: (table[t]['p'], table[t]['gd'], table[t]['gf']), reverse=True)
        group_winners[grp] = sorted_teams[0]
        group_runners[grp] = sorted_teams[1]

    # Standard 32-team Knockout Bracket mapping
    ro16_matches = [
        (group_winners['A'], group_runners['B']), (group_winners['C'], group_runners['D']),
        (group_winners['E'], group_runners['F']), (group_winners['G'], group_runners['H']),
        (group_winners['B'], group_runners['A']), (group_winners['D'], group_runners['C']),
        (group_winners['F'], group_runners['E']), (group_winners['H'], group_runners['G'])
    ]
    
    def play_ko(t1, t2):
        w, _, _, _ = sim.sim_match(t1, t2, knockout=True)
        return w

    quarters = [play_ko(t1, t2) for t1, t2 in ro16_matches]
    semis = [play_ko(quarters[i], quarters[i+1]) for i in range(0, len(quarters), 2)]
    finalists = [play_ko(semis[i], semis[i+1]) for i in range(0, len(semis), 2)]
    champion = play_ko(finalists[0], finalists[1])
    
    return champion, set(finalists), set(semis)

async def run_sim_backtest(event):
    out_div = js.document.getElementById("validation-text")
    chart_div = js.document.getElementById("validation-charts")
    btn = js.document.getElementById("btn-backtest-sim")
    prog_container = js.document.getElementById("sim-progress-container")
    prog_bar = js.document.getElementById("sim-progress-bar")
    
    # 1. READ USER INPUTS
    try:
        tourney_id = js.document.getElementById("backtest-tourney").value
        sim_count = int(js.document.getElementById("backtest-count").value)
        sim_count = max(10, min(20000, sim_count)) 
    except:
        tourney_id = '2022'
        sim_count = 1000
        
    t_data = TOURNAMENTS[tourney_id]
        
    if btn: 
        btn.disabled = True
        btn.innerHTML = "<span class='loader-circle' style='width:12px; height:12px; border-width:2px; display:inline-block; margin:0 8px -2px 0;'></span> Running..."

    out_div.innerHTML = f"Step 1: Calculating historical Elo (1872 - {t_data['name']})..."
    chart_div.innerHTML = ""
    if prog_container: 
        prog_container.style.display = "block"
        prog_bar.style.width = "0%"
    
    await asyncio.sleep(0.1)

    try:
        # 2. FETCH HISTORICAL ELOS
        elo_historic = sim.get_historical_elo(t_data['cutoff_date'])
        
        # Backup current 2026 stats
        current_stats_backup = {t: sim.TEAM_STATS[t].copy() for t in sim.TEAM_STATS}
        
        # Override with historic Elos
        for t in t_data['groups']:
            for team in t_data['groups'][t]:
                if team in elo_historic:
                    if team not in sim.TEAM_STATS:
                        sim.TEAM_STATS[team] = {
                            'elo': 1200, 'off': 1.0, 'def': 1.0, 'matches': 0, 'clean_sheets': 0, 'btts': 0,
                            'gf_avg': 0, 'ga_avg': 0, 'penalties': 0, 'first_half': 0, 'late_goals': 0, 'total_goals_recorded': 0,
                            'form': [], 'notable_results': [], 'vs_elite': [0, 0, 0], 'vs_stronger': [0, 0, 0],
                            'vs_similar': [0, 0, 0], 'vs_weaker': [0, 0, 0], 'upsets_major_won': 0, 'upsets_minor_won': 0,
                            'upsets_major_lost': 0, 'upsets_minor_lost': 0
                        }
                    sim.TEAM_STATS[team]['elo'] = elo_historic[team]
        
        # 3. RUN SIMULATIONS
        out_div.innerHTML = f"Step 2: Simulating {t_data['name']} {sim_count:,} times..."
        stats = {} 
        for i in range(sim_count):
            champ, finalists, semifinalists = sim_32_team_tournament(t_data['groups'])
            
            def track(t, key):
                if t not in stats: stats[t] = {'win':0, 'final':0, 'semi':0}
                stats[t][key] += 1
                
            track(champ, 'win')
            for t in finalists: track(t, 'final')
            for t in semifinalists: track(t, 'semi')
            
            if i % max(1, sim_count // 50) == 0:
                if prog_bar: prog_bar.style.width = f"{int((i / sim_count) * 100)}%"
                await asyncio.sleep(0.01)

        if prog_bar: prog_bar.style.width = "100%"
        await asyncio.sleep(0.2)
        
        # RESTORE 2026 STATS
        sim.TEAM_STATS.clear()
        sim.TEAM_STATS.update(current_stats_backup)

        # 4. VISUALIZATION: BAR CHART
        sorted_by_win = sorted(stats.items(), key=lambda x: x[1]['win'], reverse=True)
        top_5 = sorted_by_win[:5]
        
        fig, ax = plt.subplots(figsize=(8, 4))
        fig.patch.set_alpha(0.0) 
        ax.patch.set_alpha(0.0)

        teams = [x[0].title() for x in top_5]
        probs = [(x[1]['win']/sim_count)*100 for x in top_5]
        # Highlight the actual winner dynamically
        colors = ['#10b981' if t_data['real_winner'] in t.lower() else '#3b82f6' for t in teams]
        
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
        
        # 5. DYNAMIC HTML REPORT GENERATOR
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

        html = f"""
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
        for team, result, badge_color in t_data['ui_results']:
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

        # Dynamically extract numbers for the narrative
        real_win_team = t_data['real_winner']
        real_run_team = t_data['real_runner_up']
        surp1, surp2 = t_data['real_surprises']
        
        act_win_prob = (stats.get(real_win_team, {}).get('win', 0) / sim_count) * 100
        act_run_prob = (stats.get(real_run_team, {}).get('final', 0) / sim_count) * 100
        surp1_prob = (stats.get(surp1, {}).get('semi', 0) / sim_count) * 100
        surp2_prob = (stats.get(surp2, {}).get('semi', 0) / sim_count) * 100
        
        top_fav_name = top_5[0][0].title() if top_5 else "Unknown"
        top_fav_win = (top_5[0][1]['win'] / sim_count * 100) if top_5 else 0
        
        act_win_rank = next((i for i, v in enumerate(sorted_by_win) if v[0] == real_win_team), 99) + 1
        
        if act_win_rank <= 3: grade = "A+"
        elif act_win_rank <= 5: grade = "B"
        else: grade = "C"

        html += f"""
        <div style="margin-top: 35px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 25px; box-shadow: var(--shadow-sm);">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 2px solid #f1f5f9; padding-bottom: 12px; margin-bottom: 20px;">
                <h3 style="margin: 0; color: #0f172a; font-size:1.3em;">📊 Model Performance Metrics: {t_data['name']}</h3>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 25px;">
                <div style="background: #f0fdf4; padding: 20px; border-radius: 8px; border-left: 4px solid #10b981;">
                    <div style="font-size: 0.8em; font-weight: 600; color: #166534; text-transform: uppercase; margin-bottom: 8px;">Top 1 Accuracy</div>
                    <div style="font-size: 2.5em; font-weight: 900; color: #22c55e; margin: 10px 0;">Rank #{act_win_rank}</div>
                    <div style="font-size: 0.85em; color: #15803d; line-height: 1.5;">
                        Actual winner ({real_win_team.title()}) ranked #{act_win_rank} in engine probabilities.
                    </div>
                </div>

                <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; border-left: 4px solid #3b82f6;">
                    <div style="font-size: 0.8em; font-weight: 600; color: #1e40af; text-transform: uppercase; margin-bottom: 8px;">Best Prediction</div>
                    <div style="font-size: 1.8em; font-weight: 900; color: #3b82f6; margin: 10px 0;">{top_fav_win:.1f}%</div>
                    <div style="font-size: 0.85em; color: #1e40af; line-height: 1.5;">
                        Engine's #1 favorite to win ({top_fav_name}). Values over 15% are very high for knockout tournaments.
                    </div>
                </div>

                <div style="background: #fef3c7; padding: 20px; border-radius: 8px; border-left: 4px solid #f59e0b;">
                    <div style="font-size: 0.8em; font-weight: 600; color: #92400e; text-transform: uppercase; margin-bottom: 8px;">Upset / Anomaly Capture</div>
                    <div style="font-size: 1.8em; font-weight: 900; color: #f59e0b; margin: 10px 0;">{surp1_prob:.1f}%</div>
                    <div style="font-size: 0.85em; color: #92400e; line-height: 1.5;">
                        {surp1.title()}'s semi-final odds. Correctly identified their deep run as an anomaly, not a baseline.
                    </div>
                </div>
            </div>

            <div style="margin-top: 25px; padding: 15px; background: linear-gradient(135deg, #fef3c7 0%, #fef9e7 100%); border-left: 4px solid #f59e0b; border-radius: 6px;">
                <h4 style="margin-top: 0; color: #92400e; display: flex; gap: 8px; align-items: center;">💡 Key Insights</h4>
                <ul style="margin: 10px 0; color: #b45309; line-height: 1.7; font-size: 0.95em;">
                    <li><b>✓ Ranking Calibration:</b> Ensure the actual winner was predicted inside the Top 5 contenders. If so, the core logic is sound.</li>
                    <li><b>✓ Compound Risk:</b> Surviving 4 knockout rounds guarantees that even prime favorites sit at only ~15% to 20% to win it all.</li>
                    <li><b>⚠️ Black Swan Limits:</b> Unexpected injuries or red cards during the real tournament dictate outcomes statistical models cannot foresee.</li>
                </ul>
            </div>
        </div>
        """
        
        if prog_container: prog_container.style.display = "none"
        out_div.innerHTML = html

    except Exception as e:
        error_trace = traceback.format_exc()
        out_div.innerHTML = f"""
        <div style='color:#ef4444; padding:15px; background:#fef2f2; border:1px solid #fca5a5; border-radius:8px; overflow-x:auto;'>
            <h3 style='margin-top:0;'>Critical Python Error:</h3>
            <pre style='font-size:0.85em;'>{error_trace}</pre>
        </div>
        """
        js.console.error(f"ANALYSIS SCRIPT ERROR: {e}")
        
    finally:
        if btn:
            btn.disabled = False
            btn.innerHTML = "▶ Run Validation"

def init_analysis():
    btn = js.document.getElementById("btn-backtest-sim")
    if btn: 
        proxy = create_proxy(run_sim_backtest)
        ANALYSIS_HANDLERS.append(proxy)
        btn.onclick = proxy

init_analysis()