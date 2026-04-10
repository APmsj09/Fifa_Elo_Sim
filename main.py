### `main.py`
import js
import asyncio
import gc
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import simulation_engine as sim
from pyodide.ffi import create_proxy
from pyscript import display
import mplcursors
import random
import numpy as np

LAST_SIM_RESULTS = {}
EVENT_HANDLERS = []
BULK_STATE = {} 
TABLE_SORT_COL = "hybrid"
TABLE_SORT_DESC = True 
BULK_SORT_COL = "win"
BULK_SORT_DESC = True

def calculate_ci(count, total):
    p = count / total if total > 0 else 0
    margin = 1.96 * np.sqrt(p * (1 - p) / total) * 100 if total > 0 else 0
    return margin

def toggle_dark_mode(event):
    html = js.document.documentElement
    btn = js.document.getElementById("dark-mode-btn")
    
    if html.classList.contains("dark-mode"):
        html.classList.remove("dark-mode")
        js.localStorage.setItem("theme", "light")
        if btn: btn.innerText = "🌙"
    else:
        html.classList.add("dark-mode")
        js.localStorage.setItem("theme", "dark")
        if btn: btn.innerText = "☀️"
        
    try:
        if js.document.getElementById("tab-history").style.display == "block":
            update_dashboard_data()
    except: pass

def apply_saved_theme():
    saved_theme = js.localStorage.getItem("theme")
    html = js.document.documentElement
    btn = js.document.getElementById("dark-mode-btn")
    
    if saved_theme == "dark":
        html.classList.add("dark-mode")
        if btn: btn.innerText = "☀️"
    else:
        html.classList.remove("dark-mode")
        if btn: btn.innerText = "🌙"

# =============================================================================
# --- STARTUP & INITIALIZATION ---
# =============================================================================
async def initialize_app():
    loading_screen = js.document.getElementById("loading-screen")
    status_el = js.document.querySelector("#loading-screen div:last-child")
    
    try:
        apply_saved_theme()
        sim.DATA_DIR = "."
        
        status_el.innerHTML = "Step 1/5: Loading CSV Files (Check filenames if stuck here)..."
        await asyncio.sleep(0.1)
        stats, profiles, avg_goals, results_df = sim.initialize_engine()
        sim.TEAM_STATS = stats
        sim.TEAM_PROFILES = profiles
        sim.AVG_GOALS = avg_goals
        
        status_el.innerHTML = "Step 2/5: Analyzing Team Signatures..."
        await asyncio.sleep(0.1)
        sim.engineer_team_signatures(results_df) 
        
        status_el.innerHTML = "Step 3/5: Calculating Confederation Strength..."
        await asyncio.sleep(0.1)
        sim.calculate_confed_strength(results_df) 
        
        status_el.innerHTML = "Step 4/5: Precomputing Match Data..."
        await asyncio.sleep(0.1)
        sim.precompute_match_data()
        
        status_el.innerHTML = "Step 5/5: Setting Up Interface..."
        await asyncio.sleep(0.1)
        setup_interactions()
        
        cb = js.document.getElementById("hist-filter-wc")
        is_wc = cb.checked if cb else True
        populate_team_dropdown(wc_only=is_wc)

    except Exception as e:
        import traceback
        error_msg = str(e)
        trace = traceback.format_exc()
        js.console.error(trace)
        
        # PRINT ERROR DIRECTLY TO SCREEN
        loading_screen.innerHTML = f"""
        <div style='padding:40px; color:white; text-align:center; max-width: 800px;'>
            <h3 style='color:#ef4444; font-size: 2em;'>Engine Crashed</h3>
            <p style='font-size: 1.2em; font-weight: bold;'>Error: {error_msg}</p>
            <pre style='background: #1e293b; color: #a7f3d0; padding: 15px; text-align: left; overflow-x: auto; font-size: 0.8em;'>{trace}</pre>
            <p style='margin-top:20px;'>Check your Developer Console (F12) for more details.</p>
        </div>
        """
        # Stop the code here so the error stays on screen
        return 
    
    # If successful, hide the loading screen
    await asyncio.sleep(0.1)
    if loading_screen:
        loading_screen.style.display = "none"
    js.document.getElementById("main-dashboard").style.display = "grid"

def switch_tab(tab_id):
    for t in ["tab-single", "tab-bulk", "tab-data", "tab-history", "tab-analysis", "tab-matchup"]:
        el = js.document.getElementById(t)
        if el: el.style.display = "none"
        
    target = js.document.getElementById(tab_id)
    if target: target.style.display = "block"

def setup_interactions():
    global EVENT_HANDLERS 

    def bind_click(btn_id, func):
        el = js.document.getElementById(btn_id)
        if el:
            proxy = create_proxy(func)
            EVENT_HANDLERS.append(proxy) 
            el.addEventListener("click", proxy)
        else:
            js.console.warn(f"Warning: Element {btn_id} not found in HTML")

    bind_click("btn-tab-single", lambda e: switch_tab("tab-single"))
    bind_click("btn-tab-bulk", lambda e: switch_tab("tab-bulk"))
    bind_click("btn-tab-data", lambda e: switch_tab("tab-data"))
    bind_click("btn-tab-history", lambda e: switch_tab("tab-history"))
    bind_click("btn-tab-analysis", lambda e: switch_tab("tab-analysis"))
    bind_click("btn-tab-matchup", lambda e: switch_tab("tab-matchup"))
    bind_click("btn-run-matchup", run_matchup_analysis)
    
    bind_click("dark-mode-btn", toggle_dark_mode)
    
    cb = js.document.getElementById("hist-filter-wc")
    is_wc = cb.checked if cb else True

    populate_team_dropdown(target_id="matchup-team-a", wc_only=is_wc)
    populate_team_dropdown(target_id="matchup-team-b", wc_only=is_wc)

    build_dashboard_shell()
    populate_team_dropdown(target_id="team-select-dashboard", wc_only=is_wc)

    # --- Simulation Buttons ---
    bind_click("btn-run-single", run_single_sim)
    bind_click("btn-run-single-top", run_single_sim)
    bind_click("btn-run-bulk", run_bulk_sim)

    # --- Analysis Buttons ---
    bind_click("btn-view-history", view_team_history)
    bind_click("btn-view-style-map", plot_style_map) 

    # --- Filters ---
    bind_click("hist-filter-wc", handle_history_filter_change)
    bind_click("data-filter-wc", load_data_view)
    
    # --- Expose Global Functions ---
    
    proxy_sort = create_proxy(sort_table)
    EVENT_HANDLERS.append(proxy_sort)
    js.window.sort_table = proxy_sort

    proxy_bulk_sort = create_proxy(sort_bulk_table)
    EVENT_HANDLERS.append(proxy_bulk_sort)
    js.window.sort_bulk_table = proxy_bulk_sort

    js.window.switch_bulk_tab = create_proxy(switch_bulk_tab)
    js.window.show_top_bracket = create_proxy(show_top_bracket)

    proxy_view_group = create_proxy(open_group_modal)
    EVENT_HANDLERS.append(proxy_view_group)
    js.window.view_group_matches = proxy_view_group

    proxy_view_history = create_proxy(view_team_history)
    EVENT_HANDLERS.append(proxy_view_history)
    js.window.trigger_view_history = proxy_view_history

    proxy_refresh = create_proxy(refresh_team_analysis)
    EVENT_HANDLERS.append(proxy_refresh)
    js.window.refresh_team_analysis = proxy_refresh

    js.window.change_odds_format = create_proxy(render_favorites_table)
    js.window.show_team_path = create_proxy(open_team_path_modal)

    def handle_group_grid_click(event):
        el = event.target
        while el and el.id != "groups-container":
            if el.id and el.id.startswith("group-card-"):
                group_name = el.id.replace("group-card-", "")
                open_group_modal(group_name)
                return
            el = el.parentElement

    bind_click("groups-container", handle_group_grid_click)
    
# =============================================================================
# --- 2. SINGLE SIMULATION ---
# =============================================================================
def switch_bulk_tab(tab_id):
    views = ['agg', 'brackets', 'table']
    
    for v in views:
        el = js.document.getElementById(f'bulk-{v}-view')
        btn = js.document.getElementById(f'btn-bulk-{v}')
        if el and btn:
            if v == tab_id:
                el.style.display = 'block'
                btn.classList.add('active')
            else:
                el.style.display = 'none'
                btn.classList.remove('active')
                
    if tab_id == 'brackets':
        container = js.document.getElementById('top-bracket-render-area')
        if container and container.innerHTML.strip() == "":
            show_top_bracket(0)
    elif tab_id == 'table':
        render_bulk_spreadsheet()

def show_top_bracket(index):
    state = BULK_STATE
    if not state or 'top_brackets' not in state: return
    brackets = state['top_brackets']
    if index >= len(brackets): return
    
    # Update active button states
    for i in range(5):
        btn = js.document.getElementById(f"btn-scenario-{i}")
        if btn:
            if i == index: btn.classList.add("active")
            else: btn.classList.remove("active")
            
    bracket_data = brackets[index]
    
    # Generate Bracket HTML
    bracket_html = '<div id="bracket-container">'
    for round_data in bracket_data:
        if round_data["round"] == "Third Place Play-off": continue # Hide 3rd place from bracket view to save space
        
        bracket_html += f'<div class="bracket-round"><div class="round-title">{round_data["round"]}</div>'
        for m in round_data['matches']:
            c1 = "winner-text" if m['winner'] == m['t1'] else ""
            c2 = "winner-text" if m['winner'] == m['t2'] else ""
            
            g1_txt = str(m['g1'])
            g2_txt = str(m['g2'])
            if m['method'] == 'pks':
                g1_txt = f"{m['g1']} (P)" if m['winner'] == m['t1'] else str(m['g1'])
                g2_txt = f"{m['g2']} (P)" if m['winner'] == m['t2'] else str(m['g2'])
            elif m['method'] == 'aet':
                g1_txt = f"{m['g1']} (ET)"
                g2_txt = f"{m['g2']} (ET)"

            name1 = sim.PRETTY_NAMES.get(m['t1'], m['t1'].title())
            name2 = sim.PRETTY_NAMES.get(m['t2'], m['t2'].title())

            bracket_html += f'''
            <div class="matchup">
                <div class="matchup-team {c1}">
                    <span>{name1}</span> <span>{g1_txt}</span>
                </div>
                <div class="matchup-team {c2}">
                    <span>{name2}</span> <span>{g2_txt}</span>
                </div>
            </div>
            '''
        bracket_html += "</div>"
    bracket_html += "</div>"
    
    js.document.getElementById("top-bracket-render-area").innerHTML = bracket_html

async def run_single_sim(event):
    global LAST_SIM_RESULTS
    
    js.document.getElementById("single-start-card").style.display = "none"
    js.document.getElementById("visual-loading").style.display = "block"
    js.document.getElementById("visual-results-container").style.display = "none"
    
    await asyncio.sleep(0.02)
    
    try:
        result = sim.run_simulation(fast_mode=False)
        LAST_SIM_RESULTS = result 
        
        champion = result["champion"]
        groups_data = result["groups_data"]
        bracket_data = result["bracket_data"]
        
        js.document.getElementById("visual-champion-name").innerText = champion.upper()

        groups_html = ""
        group_names = [] 

        for grp_name, team_list in groups_data.items():
            group_names.append(grp_name)
            
            groups_html += f"""
            <div id="group-card-{grp_name}" class="group-box" style="cursor:pointer;" title="Click to view matches">
                <div style="display:flex; justify-content:space-between;">
                    <h3>Group {grp_name}</h3>
                    <span style="font-size:0.8em; color:#3498db;">ℹ️ Matches</span>
                </div>
                <table class="group-table">
                    <thead><tr><th>Team</th><th>P</th><th>W</th><th>D</th><th>L</th><th>GD</th></tr></thead>
                    <tbody>
            """
            for i, row in enumerate(team_list):
                q_class = "qualified" if i < 2 else ""
                groups_html += f"""
                    <tr class="{q_class}">
                        <td>{row['team'].title()}</td>
                        <td><strong>{row['p']}</strong></td>
                        <td>{row['w']}</td>
                        <td>{row['d']}</td>
                        <td>{row['l']}</td>
                        <td>{row['gd']}</td>
                    </tr>
                """
            groups_html += "</tbody></table></div>"
        
        js.document.getElementById("groups-container").innerHTML = groups_html

        bracket_html = ""
        for round_data in bracket_data:
            bracket_html += f'<div class="bracket-round"><div class="round-title">{round_data["round"]}</div>'
            
            for m in round_data['matches']:
                c1 = "winner-text" if m['winner'] == m['t1'] else ""
                c2 = "winner-text" if m['winner'] == m['t2'] else ""
                
                score_display = ""
                g1_txt = str(m['g1'])
                g2_txt = str(m['g2'])
                
                if m['method'] == 'pks':
                    g1_txt = f"{m['g1']} (P)" if m['winner'] == m['t1'] else str(m['g1'])
                    g2_txt = f"{m['g2']} (P)" if m['winner'] == m['t2'] else str(m['g2'])
                elif m['method'] == 'aet':
                    g1_txt = f"{m['g1']} (ET)"
                    g2_txt = f"{m['g2']} (ET)"

                bracket_html += f"""
                <div class="matchup">
                    <div class="matchup-team {c1}">
                        <span>{m['t1'].title()}</span> <span>{g1_txt}</span>
                    </div>
                    <div class="matchup-team {c2}">
                        <span>{m['t2'].title()}</span> <span>{g2_txt}</span>
                    </div>
                </div>
                """
            bracket_html += "</div>"
            
        js.document.getElementById("bracket-container").innerHTML = bracket_html
        js.document.getElementById("visual-loading").style.display = "none"
        js.document.getElementById("visual-results-container").style.display = "block"

    except Exception as e:
        js.document.getElementById("visual-loading").innerHTML = f"Error: {e}"
        js.console.error(f"SIM ERROR: {e}")

def open_group_modal(grp_name):
    try:
        matches = LAST_SIM_RESULTS.get("group_matches", {}).get(grp_name, [])
        js.document.getElementById("modal-title").innerText = f"Group {grp_name} Results"
        
        html = ""
        if not matches:
            html = "<div style='padding:20px; text-align:center;'>No match data available.</div>"
        else:
            for m in matches:
                s1 = "font-weight:bold" if m['g1'] > m['g2'] else ""
                s2 = "font-weight:bold" if m['g2'] > m['g1'] else ""
                html += f"""
                <div class="result-row" style="display:flex; align-items:center; padding:10px; border-bottom:1px solid #eee;">
                    <span style="flex:1; text-align:right; {s1}">{m['t1'].title()}</span>
                    <span class="result-score" style="margin:0 15px; background:#f1f2f6; padding:4px 10px; border-radius:4px; font-weight:bold;">{m['g1']} - {m['g2']}</span>
                    <span style="flex:1; text-align:left; {s2}">{m['t2'].title()}</span>
                </div>
                """
        
        js.document.getElementById("modal-matches").innerHTML = html
        js.document.getElementById("group-modal").style.display = "block"
    except Exception as e:
        js.console.error(f"MODAL ERROR: {e}")

# =============================================================================
# --- 3. BULK SIMULATION ---
# =============================================================================

async def run_bulk_sim(event):
    global BULK_STATE
    num_el = js.document.getElementById("bulk-count")
    out_div = js.document.getElementById("bulk-results")
    if not num_el or not out_div: return
    num = int(num_el.value)
    
    team_stats = {}   
    group_mapping = {} 
    goals_tracker = {}
    matchups = {}
    h2h_tracker = {} 
    chaos_events = 0 
    
    sorted_elos = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)
    top_5_teams = [t[0] for t in sorted_elos[:5]]
    
     def init_team(t):
        if t not in team_stats:
            team_stats[t] = {'apps': 0, 'grp_1st': 0, 'r32': 0, 'r16':0, 'qf':0, 'sf': 0, 'final': 0, 'win': 0, 'grp_pts': 0} # Added grp_pts
            goals_tracker[t] = 0
            ga_tracker[t] = 0
            matchups[t] = {
                'Round of 32': {}, 
                'Round of 16': {}, 
                'Quarter-finals': {}, 
                'Semi-finals': {}, 
                'Third Place Play-off': {}, 
                'Final': {}
            }
            h2h_tracker[t] = {}
            
    def update_h2h(t1, t2, winner):
        if t2 not in h2h_tracker[t1]: h2h_tracker[t1][t2] = {'m': 0, 'w': 0, 'l': 0, 'd': 0}
        if t1 not in h2h_tracker[t2]: h2h_tracker[t2][t1] = {'m': 0, 'w': 0, 'l': 0, 'd': 0}
        
        h2h_tracker[t1][t2]['m'] += 1
        h2h_tracker[t2][t1]['m'] += 1
        
        if winner == t1:
            h2h_tracker[t1][t2]['w'] += 1; h2h_tracker[t2][t1]['l'] += 1
        elif winner == t2:
            h2h_tracker[t2][t1]['w'] += 1; h2h_tracker[t1][t2]['l'] += 1
        else:
            h2h_tracker[t1][t2]['d'] += 1; h2h_tracker[t2][t1]['d'] += 1

    out_div.innerHTML = f"""
    <div style='text-align:center; padding:40px;'>
        <h2 style='color:var(--text-main); margin-bottom:15px;'>🎲 Simulating {num:,} Tournaments...</h2>
        <div style='width:100%; max-width:400px; background:var(--sidebar-border); border-radius:10px; height:12px; margin: 0 auto; overflow:hidden;'>
            <div id='bulk-progress-bar' style='width:0%; height:100%; background:var(--accent-blue); transition:width 0.1s ease-out; border-radius:10px;'></div>
        </div>
        <div id='bulk-progress-text' style='margin-top:12px; font-size:1em; font-weight:700; color:var(--accent-blue);'>0% Complete</div>
    </div>
    """
    await asyncio.sleep(0.05)

    all_brackets = [] # NEW

    try:
        for i in range(num):
            res = sim.run_simulation(fast_mode=False, quiet=True)
            
            all_brackets.append(res['bracket_data']) # NEW
            
            for grp, table in res['groups_data'].items():
                if grp not in group_mapping: group_mapping[grp] = {'teams': {}, 'total_elo': 0}
                
                first_team = table[0]['team']
                init_team(first_team)
                team_stats[first_team]['grp_1st'] += 1
                
                for row in table:
                    t = row['team']
                    init_team(t)
                    team_stats[t]['apps'] += 1
                    team_stats[t]['grp_pts'] += row['p'] # NEW
                    group_mapping[grp]['teams'][t] = True
                    goals_tracker[t] += row['gf']
                    ga_tracker[t] += (row['gf'] - row['gd']) # NEW (Goals against = GF - GD)
                    if i == 0: group_mapping[grp]['total_elo'] += sim.TEAM_STATS.get(t, {}).get('elo', 1200)
            
            for grp, matches in res['group_matches'].items():
                for m in matches:
                    w = m['t1'] if m['g1'] > m['g2'] else (m['t2'] if m['g2'] > m['g1'] else 'draw')
                    update_h2h(m['t1'], m['t2'], w)

            bracket = res['bracket_data']
            if bracket:
                for r in bracket:
                    r_name = r['round']
                    for m in r['matches']:
                        t1, t2 = m['t1'], m['t2']
                        init_team(t1); init_team(t2)
                        
                        if r_name == 'Round of 32': team_stats[t1]['r32'] += 1; team_stats[t2]['r32'] += 1
                        elif r_name == 'Round of 16': team_stats[t1]['r16'] += 1; team_stats[t2]['r16'] += 1
                        elif r_name == 'Quarter-finals': team_stats[t1]['qf'] += 1; team_stats[t2]['qf'] += 1
                        elif r_name == 'Semi-finals': team_stats[t1]['sf'] += 1; team_stats[t2]['sf'] += 1
                        elif r_name == 'Final': team_stats[t1]['final'] += 1; team_stats[t2]['final'] += 1
                            
                        goals_tracker[t1] += m['g1']
                        goals_tracker[t2] += m['g2']
                        ga_tracker[t1] += m['g2'] # NEW
                        ga_tracker[t2] += m['g1'] # NEW

                        matchups[t1][r_name][t2] = matchups[t1][r_name].get(t2, 0) + 1
                        matchups[t2][r_name][t1] = matchups[t2][r_name].get(t1, 0) + 1
                        
                        update_h2h(t1, t2, m['winner'])

            champ = res['champion']
            init_team(champ)
            team_stats[champ]['win'] += 1
            if champ not in top_5_teams:
                chaos_events += 1
            
            if i % 10 == 0: 
                pct = int((i / num) * 100)
                pbar = js.document.getElementById("bulk-progress-bar")
                ptext = js.document.getElementById("bulk-progress-text")
                if pbar: pbar.style.width = f"{pct}%"
                if ptext: ptext.innerHTML = f"{pct}% Complete"
                await asyncio.sleep(0)

        # NEW: SCORE AND RANK THE BRACKETS
        unique_brackets = {}
        for b in all_brackets:
            if not b: continue
            score = 0
            sig_parts = []
            for r in b:
                r_name = r['round']
                if r_name == 'Round of 32': metric = 'r16'
                elif r_name == 'Round of 16': metric = 'qf'
                elif r_name == 'Quarter-finals': metric = 'sf'
                elif r_name == 'Semi-finals': metric = 'final'
                elif r_name == 'Final': metric = 'win'
                else: continue
                
                for m in r['matches']:
                    w = m['winner']
                    # Add the probability of this team reaching this far
                    score += (team_stats[w][metric] / num)
                    sig_parts.append(w)
            
            sig = "|".join(sig_parts)
            if sig not in unique_brackets or unique_brackets[sig]['score'] < score:
                unique_brackets[sig] = {'score': score, 'bracket': b}
                
        sorted_unique = sorted(unique_brackets.values(), key=lambda x: x['score'], reverse=True)
        top_brackets = [x['bracket'] for x in sorted_unique[:5]]

        BULK_STATE = {
            'num': num, 'stats': team_stats, 'matchups': matchups, 
            'goals': goals_tracker, 'ga': ga_tracker, 'groups': group_mapping, 'chaos': chaos_events, # Added 'ga': ga_tracker
            'h2h': h2h_tracker, 'top_brackets': top_brackets
        }

        build_bulk_dashboard()

    except Exception as e:
        out_div.innerHTML = f"<div style='color:red; padding:20px; font-weight:bold;'>Error: {e}</div>"
        js.console.error(f"BULK SIM ERROR: {e}")

def build_bulk_dashboard():
    state = BULK_STATE
    num = state['num']
    out_div = js.document.getElementById("bulk-results")

    def sort_bulk_table(col):
    global BULK_SORT_COL, BULK_SORT_DESC
    if BULK_SORT_COL == col:
        BULK_SORT_DESC = not BULK_SORT_DESC
    else:
        BULK_SORT_COL = col
        BULK_SORT_DESC = False if col == 'team' else True
    render_bulk_spreadsheet()

    def render_bulk_spreadsheet(event=None):
    state = BULK_STATE
    if not state: return
    num = state['num']
    
    table_data = []
    for t, s in state['stats'].items():
        t_name = sim.PRETTY_NAMES.get(t, t.title())
        
        # Expected matches: 3 Group stage + probabilities of reaching each KO round
        # Making SF guarantees an extra match (Final or 3rd Place)
        exp_matches = 3.0 + (s['r32']/num) + (s['r16']/num) + (s['qf']/num) + (s['sf']/num) * 2
        
        exp_pts = s['grp_pts'] / num
        exp_gf = state['goals'][t] / num
        exp_ga = state['ga'][t] / num
        
        table_data.append({
            'team': t_name,
            'grp_1st': (s['grp_1st'] / num) * 100,
            'r32': (s['r32'] / num) * 100,
            'r16': (s['r16'] / num) * 100,
            'qf': (s['qf'] / num) * 100,
            'sf': (s['sf'] / num) * 100,
            'final': (s['final'] / num) * 100,
            'win': (s['win'] / num) * 100,
            'exp_pts': exp_pts,
            'exp_gf': exp_gf,
            'exp_ga': exp_ga,
            'exp_matches': exp_matches
        })
        
    # Apply Sort
    table_data.sort(key=lambda x: x[BULK_SORT_COL], reverse=BULK_SORT_DESC)
    
    def get_th(col_id, label):
        arrow = ""
        if BULK_SORT_COL == col_id:
            arrow = " ▼" if BULK_SORT_DESC else " ▲"
        else:
            arrow = " ↕"
        return f'<th class="sortable-th" onclick="window.sort_bulk_table(\'{col_id}\')" style="white-space:nowrap; padding:12px 10px;">{label}<span style="font-size:0.8em; opacity:0.6;">{arrow}</span></th>'

    html = f'''
    <div class="dashboard-card" style="padding:0; overflow:hidden;">
        <div style="overflow-x:auto;">
            <table class="rankings-table" style="margin:0; border:none; box-shadow:none;">
                <thead>
                    <tr>
                        {get_th("team", "Team")}
                        {get_th("exp_pts", "Exp. Grp Pts")}
                        {get_th("grp_1st", "1st in Grp")}
                        {get_th("r32", "R32")}
                        {get_th("r16", "R16")}
                        {get_th("qf", "QF")}
                        {get_th("sf", "SF")}
                        {get_th("final", "Final")}
                        {get_th("win", "Win")}
                        {get_th("exp_matches", "Exp. Matches")}
                        {get_th("exp_gf", "Exp. GF")}
                        {get_th("exp_ga", "Exp. GA")}
                    </tr>
                </thead>
                <tbody>
    '''
    
    for row in table_data:
        html += f'''
        <tr>
            <td style="font-weight:600; white-space:nowrap;">{row['team']}</td>
            <td style="color:var(--accent-blue); font-weight:bold; text-align:center;">{row['exp_pts']:.2f}</td>
            <td style="text-align:right;">{row['grp_1st']:.1f}%</td>
            <td style="text-align:right;">{row['r32']:.1f}%</td>
            <td style="text-align:right;">{row['r16']:.1f}%</td>
            <td style="text-align:right;">{row['qf']:.1f}%</td>
            <td style="text-align:right;">{row['sf']:.1f}%</td>
            <td style="text-align:right;">{row['final']:.1f}%</td>
            <td style="color:var(--accent-gold); font-weight:bold; text-align:right;">{row['win']:.1f}%</td>
            <td style="text-align:center;">{row['exp_matches']:.2f}</td>
            <td style="color:var(--accent-green); text-align:center;">{row['exp_gf']:.2f}</td>
            <td style="color:var(--accent-red); text-align:center;">{row['exp_ga']:.2f}</td>
        </tr>
        '''
    html += "</tbody></table></div></div>"
    
    js.document.getElementById("bulk-spreadsheet-container").innerHTML = html
    
    # 1. CALCULATE TOP-LEVEL TEAM STATS
    chaos_pct = (state['chaos'] / num) * 100
    if chaos_pct > 40: chaos_desc, chaos_col = "High 🌋", "var(--accent-red)"
    elif chaos_pct > 20: chaos_desc, chaos_col = "Medium 🌪️", "var(--accent-gold)"
    else: chaos_desc, chaos_col = "Low (Chalk) 🧊", "var(--accent-blue)"
    
    sorted_teams_elo = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)
    eligible_underdogs = [t[0] for i, t in enumerate(sorted_teams_elo) if i > 14 and t[0] in state['stats']]
    cinderella = max(eligible_underdogs, key=lambda t: state['stats'][t]['qf']) if eligible_underdogs else "None"
    cind_name = sim.PRETTY_NAMES.get(cinderella, cinderella.title())
    cind_pct = (state['stats'][cinderella]['qf'] / num * 100) if cinderella != "None" else 0
    
    group_elos = {g: data['total_elo'] for g, data in state['groups'].items()}
    group_of_death = max(group_elos, key=group_elos.get) if group_elos else "A"

    # 2. CALCULATE PLAYER AWARDS (BOOT & BALL) WITH POSITION WEIGHTING
    # --- PROJECTIONS: GOLDEN BOOT & GOLDEN BALL ---
    boot_candidates = []
    ball_candidates =[]
    
    for t, s in state['stats'].items():
        if t not in sim.TEAM_TALENT or not sim.TEAM_TALENT[t].get('top_players'):
            continue
            
        top_players = sim.TEAM_TALENT[t]['top_players']
        
        # 1. Golden Ball Candidate (Best overall player on the team)
        ball_player = top_players[0]
        try: ball_rat = float(ball_player.get('rat', 70))
        except: ball_rat = 70.0
        
        win_pct = s['win'] / num
        final_pct = s['final'] / num
        sf_pct = s['sf'] / num
        
        # Golden Ball heavily favors players who make the semi-finals or further
        team_success = (win_pct * 1.5) + (final_pct * 1.0) + (sf_pct * 0.5)
        ball_score = team_success * (ball_rat ** 1.5)
        
        ball_candidates.append({
            'player': ball_player['name'], 'team': t, 'score': ball_score, 'win_pct': win_pct * 100
        })
        
        # 2. Golden Boot Candidate (Player with highest 'Threat Score')
        best_threat_score = -1
        boot_player = None
        boot_mult = 0.5
        boot_rat = 70.0
        
        for p in top_players:
            try: rat = float(p.get('rat', 70))
            except: rat = 70.0
            
            # Identify position to determine goalscoring likelihood
            pos_str = str(p.get('position', p.get('pos', ''))).upper()
            unit_str = str(p.get('unit', '')).upper()
            
            if any(x in pos_str for x in ['ST', 'CF', 'FW', 'STRIKER']):
                mult = 1.0
            elif any(x in pos_str for x in['LW', 'RW', 'AML', 'AMR', 'WF', 'WING']):
                mult = 0.85
            elif any(x in pos_str for x in ['AMC', 'CAM', 'AM']):
                mult = 0.75
            elif any(x in pos_str for x in['MC', 'CM', 'LM', 'RM']):
                mult = 0.40
            elif any(x in pos_str for x in['CB', 'LB', 'RB', 'LWB', 'RWB', 'DC', 'DL', 'DR']):
                mult = 0.15
            elif 'GK' in pos_str:
                mult = 0.02
            else:
                # Fallback if position string is missing
                if 'ATT' in unit_str: mult = 0.90
                elif 'MID' in unit_str: mult = 0.50
                elif 'DEF' in unit_str: mult = 0.15
                else: mult = 0.50
                
            threat = rat * mult
            if threat > best_threat_score:
                best_threat_score = threat
                boot_player = p
                boot_mult = mult
                boot_rat = rat
                
        if boot_player:
            team_avg_goals = state['goals'][t] / num
            
            # Strikers take ~35-40% of team goals. Midfielders take ~15-20%.
            # Plus a small bonus for being a highly-rated player.
            share = (boot_mult * 0.35) + ((boot_rat - 70) / 100) * 0.15
            share = max(0.05, min(0.60, share)) # Keep realistic bounds (5% to 60%)
            
            exp_player_goals = team_avg_goals * share
            boot_candidates.append({
                'player': boot_player['name'], 'team': t, 'xG': exp_player_goals, 'rat': boot_rat
            })
            
    boot_candidates.sort(key=lambda x: x['xG'], reverse=True)
    ball_candidates.sort(key=lambda x: x['score'], reverse=True)

    # 3. MATCHUP INSIGHTS
    ko_counts = {}
    giant_killer = ("None", "None", 0, 0) 
    for t1, opps in state['h2h'].items():
        elo1 = sim.TEAM_STATS.get(t1, {}).get('elo', 1200)
        for t2, data in opps.items():
            if t1 < t2:
                ko_counts[tuple(sorted((t1, t2)))] = data['m']
            elo2 = sim.TEAM_STATS.get(t2, {}).get('elo', 1200)
            if elo2 - elo1 > 100 and data['m'] > max(5, num * 0.02):
                win_rate = data['w'] / data['m']
                if win_rate > giant_killer[2]:
                    giant_killer = (t1, t2, win_rate, data['m'])

    top_rivalry = max(ko_counts, key=ko_counts.get) if ko_counts else ("None", "None")
    riv1_name = sim.PRETTY_NAMES.get(top_rivalry[0], top_rivalry[0].title())
    riv2_name = sim.PRETTY_NAMES.get(top_rivalry[1], top_rivalry[1].title())
    
    if giant_killer[0] != "None":
        gk0_name = sim.PRETTY_NAMES.get(giant_killer[0], giant_killer[0].title())
        gk1_name = sim.PRETTY_NAMES.get(giant_killer[1], giant_killer[1].title())
        gk_text = f"{gk0_name} vs {gk1_name} ({giant_killer[2]*100:.1f}%)"
    else:
        gk_text = "None"

    # 4. BUILD THE DASHBOARD HTML
    html = f"""
    <!-- ROW 1: CORE TOURNAMENT METRICS -->
    <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:15px; margin-bottom:15px;">
        <div class="dashboard-card" style="margin:0; border-left:4px solid {chaos_col};">
            <div style="font-size:0.75em; text-transform:uppercase; color:var(--text-light); font-weight:700;">Chaos Index</div>
            <div style="font-size:1.5em; font-weight:900; color:var(--text-main); margin:5px 0;">{chaos_desc}</div>
            <div style="font-size:0.8em; color:var(--text-light);">Upset Probability: {chaos_pct:.1f}%</div>
        </div>
        <div class="dashboard-card" style="margin:0; border-left:4px solid var(--accent-gold);">
            <div style="font-size:0.75em; text-transform:uppercase; color:var(--text-light); font-weight:700;">Top Dark Horse</div>
            <div style="font-size:1.5em; font-weight:900; color:var(--accent-gold); margin:5px 0;">{cind_name}</div>
            <div style="font-size:0.8em; color:var(--text-light);">{cind_pct:.1f}% to reach QF</div>
        </div>
        <div class="dashboard-card" style="margin:0; border-left:4px solid var(--accent-red);">
            <div style="font-size:0.75em; text-transform:uppercase; color:var(--text-light); font-weight:700;">Group of Death</div>
            <div style="font-size:1.5em; font-weight:900; color:var(--accent-red); margin:5px 0;">Group {group_of_death}</div>
            <div style="font-size:0.8em; color:var(--text-light);">Highest Average Elo</div>
        </div>
    </div>

    <!-- ROW 2: AWARDS PROJECTIONS -->
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px; margin-bottom:15px;">
        <div class="dashboard-card" style="margin:0; padding:15px; border-top:3px solid #f59e0b;">
            <h4 style="margin:0 0 10px 0; color:#f59e0b; font-size:0.85em; text-transform:uppercase; letter-spacing:1px;">👟 Golden Boot Projection</h4>
            <table style="width:100%; font-size:0.85em; border-collapse:collapse;">
    """
    for i, c in enumerate(boot_candidates[:5]):
        t_name = sim.PRETTY_NAMES.get(c['team'], c['team'].title())
        html += f"""<tr style="border-bottom:1px solid var(--sidebar-border);">
            <td style="padding:6px 0; color:var(--text-main);"><b>#{i+1}</b> {c['player']} ({t_name})</td>
            <td style="text-align:right; font-weight:bold; color:var(--accent-green);">{c['xG']:.1f} xG</td>
        </tr>"""
    
    html += f"""
            </table>
        </div>
        <div class="dashboard-card" style="margin:0; padding:15px; border-top:3px solid #8b5cf6;">
            <h4 style="margin:0 0 10px 0; color:#8b5cf6; font-size:0.85em; text-transform:uppercase; letter-spacing:1px;">🏆 Golden Ball Projection</h4>
            <table style="width:100%; font-size:0.85em; border-collapse:collapse;">
    """
    for i, c in enumerate(ball_candidates[:5]):
        t_name = sim.PRETTY_NAMES.get(c['team'], c['team'].title())
        html += f"""<tr style="border-bottom:1px solid var(--sidebar-border);">
            <td style="padding:6px 0; color:var(--text-main);"><b>#{i+1}</b> {c['player']} ({t_name})</td>
            <td style="text-align:right; font-weight:bold; color:var(--accent-blue);">{c['win_pct']:.1f}% Win</td>
        </tr>"""
    
    html += f"""
            </table>
        </div>
    </div>

    <!-- ROW 3: MATCHUP INSIGHTS -->
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px; margin-bottom:30px;">
        <div class="dashboard-card" style="margin:0; background:rgba(139, 92, 246, 0.05); border:1px solid rgba(139, 92, 246, 0.2);">
            <div style="font-size:0.7em; text-transform:uppercase; color:#8b5cf6; font-weight:700;">⚔️ Most Likely KO Matchup</div>
            <div style="font-size:1.1em; font-weight:700; color:var(--text-main); margin-top:3px;">{riv1_name} vs {riv2_name}</div>
        </div>
        <div class="dashboard-card" style="margin:0; background:rgba(239, 68, 68, 0.05); border:1px solid rgba(239, 68, 68, 0.2);">
            <div style="font-size:0.7em; text-transform:uppercase; color:#ef4444; font-weight:700;">💀 Biggest Bogey Matchup</div>
            <div style="font-size:1.1em; font-weight:700; color:var(--text-main); margin-top:3px;">{gk_text}</div>
        </div>
    </div>

    <h3 style='color:var(--text-main); border-bottom:2px solid var(--sidebar-border); padding-bottom:10px;'>📋 Projected Group Standings</h3>
    <div style='display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap:15px; margin-bottom:40px;'>
    """
    
    for grp in sorted(state['groups'].keys()):
        is_god = "💀" if grp == group_of_death else ""
        html += f"""<div class='dashboard-card' style='margin:0; padding:15px;'>
            <h4 style='margin:0 0 10px 0; color:var(--accent-blue);'>Group {grp} <span style="float:right;" title="Group of Death">{is_god}</span></h4>
            <table style='width:100%; font-size:0.85em; border-collapse:collapse;'>"""
        group_teams = list(state['groups'][grp]['teams'].keys())
        group_teams.sort(key=lambda t: state['stats'][t]['r32'], reverse=True)
        for t in group_teams:
            s = state['stats'][t]
            adv_pct = (s['r32'] / num) * 100
            opacity = "1.0" if (s['apps']/num) > 0.5 else "0.5"
            t_name = sim.PRETTY_NAMES.get(t, t.title())  # ADDED THIS LINE
            html += f"""<tr style='opacity:{opacity}; border-bottom:1px solid var(--sidebar-border);'>
                <td style='padding:6px 0; font-weight:600;'>{t_name}</td>
                <td style='padding:6px 0; text-align:right; font-weight:bold; color:var(--accent-green);'>{adv_pct:.1f}%</td>
            </tr>"""
        html += "</table></div>"
    
    html += """</div>
    <div style='display:flex; justify-content:space-between; align-items:flex-end; border-bottom:2px solid var(--sidebar-border); padding-bottom:10px; margin-bottom:15px;'>
        <div>
            <h3 style='color:var(--text-main); margin:0;'>🏆 Tournament Favorites</h3>
            <p style='color:var(--text-light); font-size:0.8em; margin:5px 0 0 0;'>Click a team name to view their likely path.</p>
        </div>
        <select id="odds-format-selector" onchange="window.change_odds_format()" style="padding:6px 12px; border-radius:6px; border:1px solid var(--sidebar-border); background:var(--card-bg); color:var(--text-main); font-size:0.85em; cursor:pointer;">
            <option value="pct">Probabilities (%)</option>
            <option value="dec">Decimal Odds (2.50)</option>
            <option value="amer">American Odds (+150)</option>
        </select>
    </div>
    <div id="favorites-table-container"></div>
    <div id="path-modal-container"></div>
    """
    
    tabs_html = """
    <div class="sub-tab-container">
        <button id="btn-bulk-agg" class="sub-tab-btn active" onclick="window.switch_bulk_tab('agg')">📊 Aggregates</button>
        <button id="btn-bulk-brackets" class="sub-tab-btn" onclick="window.switch_bulk_tab('brackets')">🔮 Most Likely Scenarios</button>
        <button id="btn-bulk-table" class="sub-tab-btn" onclick="window.switch_bulk_tab('table')">📑 Spreadsheet</button>
    </div>
    """
    
    # Wrap original aggregates in a div
    html = f"<div id='bulk-agg-view'>{html}</div>"
    
    # Build the Brackets shell
    brackets_shell = """
    <div id="bulk-brackets-view" style="display:none;">
        <div class="dashboard-card" style="margin-bottom:20px;">
            <h3 style="margin-top:0;">Top 5 Most Likely Outcomes</h3>
            <p style="color:var(--text-light); font-size:0.9em; margin-bottom:15px;">Based on the mathematical probability of each matchup, these are the 5 exact brackets that were most likely to occur in this simulation block.</p>
            <div style="display:flex; gap:10px; overflow-x:auto; padding-bottom:10px;">
    """
    
    for i in range(len(state.get('top_brackets', []))):
        act_class = "active" if i == 0 else ""
        brackets_shell += f'<button id="btn-scenario-{i}" class="scenario-btn {act_class}" onclick="window.show_top_bracket({i})">Scenario {i+1}</button>'
        
    brackets_shell += """
            </div>
        </div>
        <div id="top-bracket-render-area" style="overflow-x:auto; padding-bottom: 20px;"></div>
    </div>
    """

    # Build the Spreadsheet shell
    table_shell = """
    <div id="bulk-table-view" style="display:none;">
        <h3 style="margin-top:0;">Raw Data Spreadsheet</h3>
        <p style="color:var(--text-light); font-size:0.9em; margin-bottom:15px;">Sortable metrics averaged across all simulated tournaments.</p>
        <div id="bulk-spreadsheet-container"></div>
    </div>
    """
    
    out_div.innerHTML = tabs_html + html + brackets_shell + table_shell
    render_favorites_table()

def render_favorites_table(event=None):
    state = BULK_STATE
    if not state: return
    
    num = state['num']
    team_stats = state['stats']
    
    format_el = js.document.getElementById("odds-format-selector")
    fmt = format_el.value if format_el else "pct"
    
    def format_odds(count, total):
        if count == 0: return "-"
        p = count / total
        if fmt == "pct": return f"{p*100:.1f}%"
        if fmt == "dec": return f"{1/p:.2f}"
        if fmt == "amer":
            if p > 0.5: 
                return f"{int((p / (1 - p)) * -100)}"
            else: 
                return f"+{int(((1 - p) / p) * 100)}"
    
    html = f"""<table class="favorites-table">
        <tr style="text-align:left;">
            <th style="text-align:left; width: 25%;">Team</th>
            <th style="text-align:right; width: 12%;">R32</th>
            <th style="text-align:right; width: 12%;">R16</th>
            <th style="text-align:right; width: 12%;">QF</th>
            <th style="text-align:right; width: 12%;">SF</th>
            <th style="text-align:right; width: 12%;">Final</th>
            <th style="text-align:right; width: 15%; color:var(--accent-gold);">Win</th>
        </tr>"""
    
    all_teams_sorted = sorted(team_stats.items(), key=lambda x: x[1]['win'], reverse=True)
    
    for team, s in all_teams_sorted:
        if (s['r32'] / num) < 0.01: continue
        
        html += f"""
        <tr>
            <td style="text-align:left;">
                <button onclick="window.show_team_path('{team}')" style="background:transparent; border:none; color:var(--accent-blue); font-weight:bold; cursor:pointer; font-size:1em; padding:0; text-align:left;">
                    {sim.PRETTY_NAMES.get(team, team.title())} 🔍
                </button>
            </td>
            <td style="text-align:right;">{format_odds(s['r32'], num)}</td>
            <td style="text-align:right;">{format_odds(s['r16'], num)}</td>
            <td style="text-align:right;">{format_odds(s['qf'], num)}</td>
            <td style="text-align:right;">{format_odds(s['sf'], num)}</td>
            <td style="text-align:right;">{format_odds(s['final'], num)}</td>
            <td style="text-align:right; font-weight:bold;">{format_odds(s['win'], num)}</td>
        </tr>
        """
    html += "</table>"
    js.document.getElementById("favorites-table-container").innerHTML = html

def open_team_path_modal(team):
    state = BULK_STATE
    matchups = state['matchups'].get(team)
    h2h = state['h2h'].get(team, {})
    if not matchups: return
    
    def get_top_opponents(round_name, limit=3):
        opps = matchups.get(round_name, {})
        total_games = sum(opps.values())
        if total_games == 0: return "<div style='color:var(--text-light); font-size:0.85em;'>Probability too low.</div>"
        
        sorted_opps = sorted(opps.items(), key=lambda x: x[1], reverse=True)[:limit]
        out = ""
        for opp, count in sorted_opps:
            pct = (count / total_games) * 100
            opp_name = sim.PRETTY_NAMES.get(opp, opp.title()) # ADD THIS LINE
            out += f"""
            <div style="display:flex; justify-content:space-between; margin-bottom:5px; font-size:0.9em; border-bottom:1px solid var(--sidebar-border); padding-bottom:3px;">
                <span style="color:var(--text-main); font-weight:500;">{opp_name}</span>
                <span style="color:var(--accent-blue); font-weight:bold;">{pct:.1f}%</span>
            </div>"""
        return out

    min_matches = max(5, state['num'] * 0.01)
    
    valid_opps = []
    for opp, data in h2h.items():
        if data['m'] >= min_matches:
            win_pct = (data['w'] / data['m']) * 100
            valid_opps.append((opp, win_pct, data['m']))
            
    valid_opps.sort(key=lambda x: x[1], reverse=True)
    
    def render_h2h(data_list):
        if not data_list: return "<div style='font-size:0.85em; color:var(--text-light);'>Not enough data.</div>"
        return "".join([f"<div style='display:flex; justify-content:space-between; font-size:0.85em; margin-bottom:4px;'><span style='font-weight:600;'>{sim.PRETTY_NAMES.get(x[0], x[0].title())}</span> <b>{x[1]:.1f}%</b></div>" for x in data_list])
    best_opps_html = render_h2h(valid_opps[:3])
    worst_opps_html = render_h2h(valid_opps[-3:][::-1]) 

    html = f"""
    <div id="path-modal-overlay" style="position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.6); z-index:9999; display:flex; justify-content:center; align-items:center; backdrop-filter:blur(3px);" onclick="document.getElementById('path-modal-overlay').remove()">
        <div style="background:var(--card-bg); width:95%; max-width:500px; border-radius:12px; padding:25px; box-shadow:var(--shadow-lg); max-height: 90vh; overflow-y: auto;" onclick="event.stopPropagation()">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; border-bottom:1px solid var(--sidebar-border); padding-bottom:10px;">
                <h2 style="margin:0; color:var(--text-main); font-size:1.3em;">🔮 The Path: {sim.PRETTY_NAMES.get(team, team.title())}</h2>
                <button onclick="document.getElementById('path-modal-overlay').remove()" style="background:transparent; border:none; font-size:1.5em; cursor:pointer; color:var(--text-light);">&times;</button>
            </div>
            
            <div style="margin-bottom:15px;">
                <h4 style="margin:0 0 8px 0; color:var(--accent-green); font-size:0.75em; text-transform:uppercase; letter-spacing:1px;">Round of 32 (First Knockout)</h4>
                {get_top_opponents('Round of 32')}
            </div>
            <div style="margin-bottom:15px;">
                <h4 style="margin:0 0 8px 0; color:var(--text-main); font-size:0.75em; text-transform:uppercase; letter-spacing:1px;">Round of 16</h4>
                {get_top_opponents('Round of 16')}
            </div>
            <div style="margin-bottom:15px;">
                <h4 style="margin:0 0 8px 0; color:var(--text-main); font-size:0.75em; text-transform:uppercase; letter-spacing:1px;">Quarter-Finals</h4>
                {get_top_opponents('Quarter-finals')}
            </div>
            <div style="margin-bottom:15px;">
                <h4 style="margin:0 0 8px 0; color:var(--text-main); font-size:0.75em; text-transform:uppercase; letter-spacing:1px;">Semi-Finals</h4>
                {get_top_opponents('Semi-finals')}
            </div>
            <div style="margin-bottom:15px;">
                <h4 style="margin:0 0 8px 0; color:#94a3b8; font-size:0.75em; text-transform:uppercase; letter-spacing:1px;">Third Place Play-off</h4>
                {get_top_opponents('Third Place Play-off')}
            </div>
            
            <div style="display:flex; gap:15px; margin-top:20px; border-top:2px solid var(--sidebar-border); padding-top:15px; background:rgba(0,0,0,0.02); border-radius:8px; padding:15px;">
                <div style="flex:1;">
                    <h4 style="margin:0 0 8px 0; color:#10b981; font-size:0.8em; text-transform:uppercase;">🟢 High Win Rate Vs.</h4>
                    {best_opps_html}
                </div>
                <div style="flex:1; border-left:1px solid var(--sidebar-border); padding-left:15px;">
                    <h4 style="margin:0 0 8px 0; color:#ef4444; font-size:0.8em; text-transform:uppercase;">🔴 Bogey Teams</h4>
                    {worst_opps_html}
                </div>
            </div>
        </div>
    </div>
    """
    js.document.getElementById("path-modal-container").innerHTML = html

async def run_matchup_analysis(event):
    team_a = js.document.getElementById("matchup-team-a").value
    team_b = js.document.getElementById("matchup-team-b").value
    out_div = js.document.getElementById("matchup-results-container")
    
    try:
        sim_count = int(js.document.getElementById("matchup-sim-count").value)
        sim_count = max(1, min(100000, sim_count)) 
    except:
        sim_count = 10000
    
    if team_a == team_b:
        out_div.innerHTML = "<div style='color:red; text-align:center; padding:20px; font-weight:bold;'>Please select two different teams.</div>"
        return

    out_div.innerHTML = f"<div style='text-align:center; padding:50px;'><div class='loader-circle' style='border-top-color:var(--accent-blue); margin: 0 auto 20px;'></div>Simulating {sim_count:,} Matches...</div>"
    await asyncio.sleep(0.05) 

    try:
        a_wins, b_wins, draws = 0, 0, 0
        a_goals, b_goals = 0, 0
        scorelines = {}

        for _ in range(sim_count):
            res, g1, g2 = sim.sim_match(team_a, team_b, knockout=False)
            if res == team_a: a_wins += 1
            elif res == team_b: b_wins += 1
            else: draws += 1
            a_goals += g1
            b_goals += g2
            score_str = f"{g1}-{g2}"
            scorelines[score_str] = scorelines.get(score_str, 0) + 1

        p_a = (a_wins / sim_count) * 100
        p_d = (draws / sim_count) * 100
        p_b = (b_wins / sim_count) * 100
        ci_a = calculate_ci(a_wins, sim_count)
        ci_d = calculate_ci(draws, sim_count)
        ci_b = calculate_ci(b_wins, sim_count)
        avg_ga = a_goals / sim_count
        avg_gb = b_goals / sim_count
        sorted_scores = sorted(scorelines.items(), key=lambda x: x[1], reverse=True)[:3]

        sa = sim.TEAM_STATS.get(team_a, {})
        sb = sim.TEAM_STATS.get(team_b, {})
        ta = sim.TEAM_TALENT.get(team_a, {})
        tb = sim.TEAM_TALENT.get(team_b, {})
        name_a = sim.PRETTY_NAMES.get(team_a, team_a.title())
        name_b = sim.PRETTY_NAMES.get(team_b, team_b.title())

        def get_rat(talent_dict, key):
            val = talent_dict.get(key, 0)
            return int(round(val)) if val > 0 else "--"

        talent_att_a, talent_att_b = get_rat(ta, 'rating_att'), get_rat(tb, 'rating_att')
        talent_mid_a, talent_mid_b = get_rat(ta, 'rating_mid'), get_rat(tb, 'rating_mid')
        talent_def_a, talent_def_b = get_rat(ta, 'rating_def'), get_rat(tb, 'rating_def')
        talent_gk_a,  talent_gk_b  = get_rat(ta, 'rating_gk'),  get_rat(tb, 'rating_gk')

        import math
        def calc_tactical_score(attacking, defending):
            ratio = attacking / defending if defending > 0 else 1.0
            score = 5 + 2.5 * math.log(ratio)
            return max(0.5, min(9.5, score)) 
        
        # Consistent tac_ prefix for all 0-10 bar calculations
        tac_atk_a = calc_tactical_score(sa.get('off', 1.0), sb.get('def', 1.0))
        tac_atk_b = calc_tactical_score(sb.get('off', 1.0), sa.get('def', 1.0))
        tac_def_a = calc_tactical_score(sa.get('def', 1.0), sb.get('off', 1.0))
        tac_def_b = calc_tactical_score(sb.get('def', 1.0), sa.get('off', 1.0))
        consistency_a = min(10, (7.5 - (sa.get('btts_pct', 50) - 50) / 10))
        consistency_b = min(10, (7.5 - (sb.get('btts_pct', 50) - 50) / 10))

        style_a = sim.TEAM_PROFILES.get(team_a, 'Balanced')
        style_b = sim.TEAM_PROFILES.get(team_b, 'Balanced')
        tactical_clash = f"Clash between {name_a}'s {style_a} and {name_b}'s {style_b}."
        elo_diff = abs(int(sa.get('elo', 1200)) - int(sb.get('elo', 1200)))
        
        html = f"""
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-bottom:20px;">
            <div class="dashboard-card" style="margin-bottom:0;">
                <h3 style="margin-top:0; color:var(--text-light); text-transform:uppercase; font-size:0.85em;">Match Simulation ({sim_count:,} runs)</h3>
                <div style="display:flex; justify-content:space-between; margin-bottom:10px; font-weight:800; font-size:1.2em;">
                    <div style="color:#3b82f6;">{name_a}<br><span style="font-size:0.6em; font-weight:400;"><span class='ci-value' data-ci='95% CI: ±{ci_a:.1f}%'>{p_a:.1f}%</span></span></div>
                    <div style="color:#64748b; font-size:0.8em; align-self:center;">DRAW<br><span style="font-size:0.7em;"><span class='ci-value' data-ci='95% CI: ±{ci_d:.1f}%'>{p_d:.1f}%</span></span></div>
                    <div style="color:#ef4444;">{name_b}<br><span style="font-size:0.6em; font-weight:400;"><span class='ci-value' data-ci='95% CI: ±{ci_b:.1f}%'>{p_b:.1f}%</span></span></div>
                </div>
                <div style="width:100%; height:30px; display:flex; border-radius:8px; overflow:hidden;">
                    <div style="width:{p_a}%; background:#3b82f6;"></div>
                    <div style="width:{p_d}%; background:#cbd5e1;"></div>
                    <div style="width:{p_b}%; background:#ef4444;"></div>
                </div>
                <div style="display:flex; justify-content:space-between; margin-top:20px;">
                    <div class="stat-pill" style="flex:1; margin-right:10px;">
                        <div class="stat-pill-title">Exp. Goals</div>
                        <div class="stat-pill-value" style="color:#3b82f6;">{avg_ga:.2f}</div>
                    </div>
                    <div class="stat-pill" style="flex:1; margin-left:10px;">
                        <div class="stat-pill-title">Exp. Goals</div>
                        <div class="stat-pill-value" style="color:#ef4444;">{avg_gb:.2f}</div>
                    </div>
                </div>
            </div>
            <div class="dashboard-card" style="margin-bottom:0;">
                <h3 style="margin-top:0; color:var(--text-light); text-transform:uppercase; font-size:0.85em;">Likely Scorelines</h3>
                <div style="display:flex; flex-direction:column; gap:10px; margin-top:15px;">
        """
        for i, (score, count) in enumerate(sorted_scores):
            pct = (count/sim_count)*100
            html += f"""
            <div class="scoreline-row">
                <div class="scoreline-label">{score}</div>
                <div style="flex-grow:1;"><div style="height:8px; background:#e2e8f0; border-radius:4px;"><div style="height:100%; width:{pct * 3}%; background:#f59e0b; border-radius:4px;"></div></div></div>
                <div class="scoreline-pct">{pct:.1f}%</div>
            </div>"""
        html += f"""
                </div>
            </div>
        </div>
        <div class="dashboard-card" style="border-top:4px solid #8b5cf6;">
            <h3 style="margin-top:0; color:#8b5cf6; font-size:1.2em;">🔭 Matchup Analysis</h3>
            <p>{tactical_clash}</p>
            <table class="rankings-table" style="margin-top:20px;">
                <thead>
                    <tr><th style="width:33%; text-align:right;">{name_a}</th><th style="width:33%; text-align:center;">Squad DNA</th><th style="width:33%; text-align:left;">{name_b}</th></tr>
                </thead>
                <tbody>
                    <tr><td style="text-align:right; font-weight:bold;">{int(sa.get('elo', 0))}</td><td style="text-align:center;">Elo Rating</td><td style="text-align:left; font-weight:bold;">{int(sb.get('elo', 0))}</td></tr>
                    <tr style="background: rgba(59, 130, 246, 0.03);"><td style="text-align:right;">{talent_att_a}</td><td style="text-align:center;">ATTACK</td><td style="text-align:left;">{talent_att_b}</td></tr>
                    <tr style="background: rgba(59, 130, 246, 0.03);"><td style="text-align:right;">{talent_mid_a}</td><td style="text-align:center;">MIDFIELD</td><td style="text-align:left;">{talent_mid_b}</td></tr>
                    <tr style="background: rgba(59, 130, 246, 0.03);"><td style="text-align:right;">{talent_def_a}</td><td style="text-align:center;">DEFENSE</td><td style="text-align:left;">{talent_def_b}</td></tr>
                    <tr style="background: rgba(59, 130, 246, 0.03);"><td style="text-align:right;">{talent_gk_a}</td><td style="text-align:center;">GOALKEEPER</td><td style="text-align:left;">{talent_gk_b}</td></tr>
                    <tr><td style="text-align:right; font-weight:bold;">{sa.get('adj_gf', 0):.2f}</td><td style="text-align:center;">Attacking Power</td><td style="text-align:left; font-weight:bold;">{sb.get('adj_gf', 0):.2f}</td></tr>
                </tbody>
            </table>
        </div>
        <div class="dashboard-card" style="border-left:4px solid #f59e0b; margin-top:20px;">
            <h3 style="margin-top:0; color:#f59e0b;">⚔️ Tactical Comparison</h3>
            <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:15px;">
                <div style="background:var(--card-bg); padding:12px; border-radius:8px; border-left:3px solid #ef4444;">
                    <div style="font-weight:bold; font-size:0.85em;">Attacking Power ⚽</div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <div style="flex:1; background:#f0f0f0; height:16px; border-radius:3px; overflow:hidden;">
                            <div style="background:#3b82f6; height:100%; width:{(tac_atk_a/10)*100:.0f}%;"></div>
                        </div>
                        <div style="font-weight:bold;">{tac_atk_a:.1f}</div>
                    </div>
                    <div style="display:flex; align-items:center; gap:8px; margin-top:5px;">
                        <div style="flex:1; background:#f0f0f0; height:16px; border-radius:3px; overflow:hidden;">
                            <div style="background:#ef4444; height:100%; width:{(tac_atk_b/10)*100:.0f}%;"></div>
                        </div>
                        <div style="font-weight:bold;">{tac_atk_b:.1f}</div>
                    </div>
                </div>
                <div style="background:var(--card-bg); padding:12px; border-radius:8px; border-left:3px solid #10b981;">
                    <div style="font-weight:bold; font-size:0.85em;">Defensive Solidity 🛡️</div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <div style="flex:1; background:#f0f0f0; height:16px; border-radius:3px; overflow:hidden;">
                            <div style="background:#3b82f6; height:100%; width:{(tac_def_a/10)*100:.0f}%;"></div>
                        </div>
                        <div style="font-weight:bold;">{tac_def_a:.1f}</div>
                    </div>
                    <div style="display:flex; align-items:center; gap:8px; margin-top:5px;">
                        <div style="flex:1; background:#f0f0f0; height:16px; border-radius:3px; overflow:hidden;">
                            <div style="background:#ef4444; height:100%; width:{(tac_def_b/10)*100:.0f}%;"></div>
                        </div>
                        <div style="font-weight:bold;">{tac_def_b:.1f}</div>
                    </div>
                </div>
                <div style="background:var(--card-bg); padding:12px; border-radius:8px; border-left:3px solid #8b5cf6;">
                    <div style="font-weight:bold; font-size:0.85em;">Consistency 📊</div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <div style="flex:1; background:#f0f0f0; height:16px; border-radius:3px; overflow:hidden;">
                            <div style="background:#3b82f6; height:100%; width:{(consistency_a/10)*100:.0f}%;"></div>
                        </div>
                        <div style="font-weight:bold;">{consistency_a:.1f}</div>
                    </div>
                    <div style="display:flex; align-items:center; gap:8px; margin-top:5px;">
                        <div style="flex:1; background:#f0f0f0; height:16px; border-radius:3px; overflow:hidden;">
                            <div style="background:#ef4444; height:100%; width:{(consistency_b/10)*100:.0f}%;"></div>
                        </div>
                        <div style="font-weight:bold;">{consistency_b:.1f}</div>
                    </div>
                </div>
            </div>
        </div>
        <div class="dashboard-card" style="background:linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, rgba(16, 185, 129, 0.05) 100%); border-left:4px solid #3b82f6; margin-top:20px;">
            <h3 style="margin-top:0; color:#0f172a;">💡 Strategic Insights</h3>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px;">
                <div>
                    <div style="font-weight:bold; margin-bottom:8px; color: #3b82f6;">{name_a}'s Strengths</div>
                    <ul style="margin:0; padding-left:18px; font-size:0.9em; line-height:1.6;">
                        <li>{('💪 Dominant Attack' if tac_atk_a > tac_atk_b + 1.5 else '⚔️ Balanced Offense') if abs(tac_atk_a - tac_atk_b) > 0.5 else '⚖️ Average Attack'}</li>
                        <li>{('🧱 Fortress Defense' if tac_def_a > tac_def_b + 1.5 else '🛡️ Solid Backline') if abs(tac_def_a - tac_def_b) > 0.5 else '⚖️ Average Defense'}</li>
                        <li>{('✓ Game Control' if consistency_a > consistency_b else '⚠️ Unpredictable') if abs(consistency_a - consistency_b) > 1.5 else '↔️ Similar Control'}</li>
                    </ul>
                </div>
                <div>
                    <div style="font-weight:bold; margin-bottom:8px; color: #ef4444;">{name_b}'s Strengths</div>
                    <ul style="margin:0; padding-left:18px; font-size:0.9em; line-height:1.6;">
                        <li>{('💪 Dominant Attack' if tac_atk_b > tac_atk_a + 1.5 else '⚔️ Balanced Offense') if abs(tac_atk_b - tac_atk_a) > 0.5 else '⚖️ Average Attack'}</li>
                        <li>{('🧱 Fortress Defense' if tac_def_b > tac_def_a + 1.5 else '🛡️ Solid Backline') if abs(tac_def_b - tac_def_a) > 0.5 else '⚖️ Average Defense'}</li>
                        <li>{('✓ Game Control' if consistency_b > consistency_a else '⚠️ Unpredictable') if abs(consistency_b - consistency_a) > 1.5 else '↔️ Similar Control'}</li>
                    </ul>
                </div>
            </div>
            <div style="margin-top:15px; padding-top:15px; border-top:1px solid #e2e8f0;">
                <div style="font-size:0.9em; color:var(--text-light);"><b>Prediction Confidence:</b> {('Very High' if elo_diff > 200 else ('High' if elo_diff > 100 else 'Moderate'))} based on {elo_diff} Elo point difference</div>
            </div>
        </div>
        """
        out_div.innerHTML = html

    except Exception as e:
        out_div.innerHTML = f"<div style='color:red; padding:20px;'>Error running matchup: {e}</div>"
        js.console.error(f"MATCHUP ERROR: {e}")

def build_dashboard_shell():
    container = js.document.getElementById("tab-history")
    
    container.innerHTML = """
    <div style="background:var(--card-bg); padding:15px; border-radius:12px; display:flex; gap:15px; align-items:center; margin-bottom:20px; box-shadow:var(--shadow-sm); border:1px solid var(--sidebar-border);">
        <label style="font-weight:600; color:var(--text-main); font-size:0.9em;">Select Team:</label>
        <select id="team-select-dashboard" onchange="window.refresh_team_analysis()" style="padding:10px; border-radius:8px; border:1px solid var(--sidebar-border); flex-grow:1; background:transparent; color:var(--text-main); font-weight:500;"></select>
        
        <div style="width:1px; height:30px; background:var(--sidebar-border); margin:0 5px;"></div>
        
        <button id="btn-show-dashboard" class="action-btn" style="width:auto; margin:0; background:var(--sidebar-bg); padding:10px 20px;">📊 Profile</button>
        <button id="btn-show-style" class="action-btn" style="width:auto; margin:0; background:#8b5cf6; padding:10px 20px;">🗺️ 5D Style Map</button>
    </div>

    <div id="view-profile">
        <div id="dashboard-header" class="dashboard-card" style="margin-bottom:20px; padding:30px;"></div>
        <div id="dashboard-metrics"></div>

        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap:25px; margin-top:25px;">
            <div class="dashboard-card" style="margin-bottom:0;">
                <h4 style="margin-top:0; color:var(--text-light); font-size:0.85em; text-transform:uppercase; letter-spacing:1px;">Historical Performance (Elo)</h4>
                <div id="dashboard_chart_elo" style="margin-top:15px;"></div>
            </div>
            <div class="dashboard-card" style="margin-bottom:0;">
                <h4 style="margin-top:0; color:var(--text-light); font-size:0.85em; text-transform:uppercase; letter-spacing:1px;">Strategic DNA</h4>
                <div id="dashboard_chart_radar" style="margin-top:15px;"></div>
            </div>
        </div>
    </div>

    <div id="view-style-map" style="display:none;">
        <div class="dashboard-card">
             <div id="main-chart-container" style="min-height:500px;"></div>
        </div>
    </div>
    """

    def toggle_view(mode):
        p = js.document.getElementById("view-profile")
        s = js.document.getElementById("view-style-map")
        if mode == 'profile':
            p.style.display = "block"
            s.style.display = "none"
            update_dashboard_data()
        else:
            p.style.display = "none"
            s.style.display = "block"
            asyncio.ensure_future(plot_style_map(None))

    js.document.getElementById("btn-show-dashboard").onclick = create_proxy(lambda e: toggle_view('profile'))
    js.document.getElementById("btn-show-style").onclick = create_proxy(lambda e: toggle_view('style'))


def sort_table(col):
    global TABLE_SORT_COL, TABLE_SORT_DESC
    if TABLE_SORT_COL == col:
        TABLE_SORT_DESC = not TABLE_SORT_DESC
    else:
        TABLE_SORT_COL = col
        if col == 'name':
            TABLE_SORT_DESC = False # Default to A-Z for text
        else:
            TABLE_SORT_DESC = True  # Default to highest-first for stats
    load_data_view(None)

def load_data_view(event=None):
    global TABLE_SORT_COL, TABLE_SORT_DESC
    container = js.document.getElementById("data-table-container")
    if not container: return
    
    container.innerHTML = "<div style='padding:20px; text-align:center;'>Loading raw data...</div>" 
    
    sidebar_checkbox = js.document.getElementById("hist-filter-wc")
    wc_only = sidebar_checkbox.checked if sidebar_checkbox else False
    
    wc_team_slugs = [sim.get_slug(t) for t in sim.WC_TEAMS]
    
    table_data = []
    DUMMY_GAMES = 10 
    GLOBAL_AVG = sim.AVG_GOALS if sim.AVG_GOALS > 0 else 1.25

    for team, stats in sim.TEAM_STATS.items():
        if wc_only and team not in wc_team_slugs:
            continue
            
        matches = stats.get('matches', 0)
        if matches < 7 and team not in wc_team_slugs:
            continue

        talent = sim.TEAM_TALENT.get(team, {})
        def fmt(key):
            v = talent.get(key, 0)
            return int(round(v)) if v > 0 else 0

        elo = stats.get('elo', 1200)
        ovr = fmt('talent_score')

        if ovr > 0:
            overall_rating_z_score = (ovr - 70.0) / 8.0
            talent_elo_rating = 1500.0 + (overall_rating_z_score * 200.0)
            hybrid = (elo * 0.60) + (talent_elo_rating * 0.40)
        else:
            hybrid = elo

        reg_gf_avg = stats.get('gf_avg', 0)
        reg_ga_avg = stats.get('ga_avg', 0)
        
        true_gf = (reg_gf_avg * (matches + DUMMY_GAMES)) - (DUMMY_GAMES * GLOBAL_AVG)
        true_ga = (reg_ga_avg * (matches + DUMMY_GAMES)) - (DUMMY_GAMES * GLOBAL_AVG)
        
        total_gf = max(0, int(round(true_gf)))
        total_ga = max(0, int(round(true_ga)))

        raw_form = stats.get('form', '-----')
        formatted_form = ""
        for char in raw_form:
            if char == 'W': color = "#27ae60"
            elif char == 'L': color = "#e74c3c"
            else: color = "#bdc3c7"
            formatted_form += f"<span style='color:{color}; font-weight:bold;'>{char}</span>"

        table_data.append({
            'team_slug': team,
            'name': sim.PRETTY_NAMES.get(team, team.title()),
            'elo': elo,
            'ovr': ovr,
            'hybrid': hybrid, # Fixed variable name
            'att': fmt('rating_att'),
            'mid': fmt('rating_mid'),
            'def': fmt('rating_def'),
            'gk': fmt('rating_gk'),
            'form_html': formatted_form,
            'matches': matches,
            'gf': total_gf,
            'ga': total_ga,
            'cs': int(stats.get('cs_pct', 0)),
            'btts': int(stats.get('btts_pct', 0)),
            'late': int(stats.get('late_pct', 0))
        })

    # Apply Active Sort
    if TABLE_SORT_COL == 'name':
        table_data.sort(key=lambda x: x['name'], reverse=TABLE_SORT_DESC)
    else:
        table_data.sort(key=lambda x: x.get(TABLE_SORT_COL, 0), reverse=TABLE_SORT_DESC)

    # Helper function for sortable headers
    def get_th(col_id, label, color="", title=""):
        arrow = ""
        if TABLE_SORT_COL == col_id:
            arrow = " ▼" if TABLE_SORT_DESC else " ▲"
        else:
            arrow = " ↕"
        style = ""
        if color: style += f" color:{color};"
        title_attr = f" title='{title}'" if title else ""
        return f'<th class="sortable-th" onclick="window.sort_table(\'{col_id}\')" style="{style}"{title_attr}>{label}<span style="font-size:0.8em; opacity:0.6;">{arrow}</span></th>'

    html = f'''
    <div style="margin-bottom:10px; font-size:0.8em; color:#7f8c8d; text-align:right;">
        *Tactical stats (1H, Late, Pens) based on available scorer data
    </div>
    <div style="overflow-x:auto;">
    <table class="rankings-table">
        <thead>
            <tr>
                <th>Rank</th>
                {get_th("name", "Team")}
                {get_th("elo", "Elo")}
                {get_th("hybrid", "Power Rating", "var(--accent-gold)", "60% Elo / 40% Squad OVR")}
                {get_th("ovr", "OVR", "var(--accent-blue)", "Overall Squad Rating")}
                {get_th("att", "ATT", "var(--accent-green)")}
                {get_th("mid", "MID", "var(--accent-green)")}
                {get_th("def", "DEF", "var(--accent-green)")}
                {get_th("gk", "GK", "var(--accent-green)")}
                <th>Form</th>
                {get_th("matches", "Matches")}
                {get_th("gf", "Gls For")}
                {get_th("ga", "Gls Agst")}
                {get_th("cs", "CS%")}
                {get_th("btts", "BTTS%")}
                {get_th("late", "Late%")}
            </tr>
        </thead>
        <tbody>
    '''

    rank_counter = 0
    for row in table_data:
        rank_counter += 1
        
        ovr_display = row['ovr'] if row['ovr'] > 0 else '--'
        att_display = row['att'] if row['att'] > 0 else '--'
        mid_display = row['mid'] if row['mid'] > 0 else '--'
        def_display = row['def'] if row['def'] > 0 else '--'
        gk_display = row['gk'] if row['gk'] > 0 else '--'
        
        html += f'''
        <tr>
            <td style="font-weight:bold;">#{rank_counter}</td>
            <td style="font-weight:600">{row['name']}</td>
            <td style="font-weight:bold; color:var(--text-main); font-size:1.1em;">{int(row['elo'])}</td>
            <td style="font-weight:900; color:var(--accent-gold); font-size:1.15em; text-align:center;">{int(row['hybrid'])}</td>
            <td style="font-weight:bold; color:var(--accent-blue); background:rgba(59, 130, 246, 0.05); text-align:center;">{ovr_display}</td>
            <td style="text-align:center;">{att_display}</td>
            <td style="text-align:center;">{mid_display}</td>
            <td style="text-align:center;">{def_display}</td>
            <td style="text-align:center;">{gk_display}</td>
            <td style="font-family:monospace; letter-spacing:2px;">{row['form_html']}</td>
            <td style="text-align:center;">{row['matches']}</td>
            <td style="color:#2980b9; font-weight:bold;">{row['gf']}</td>
            <td style="color:#c0392b;">{row['ga']}</td>
            <td>{row['cs']}%</td>
            <td>{row['btts']}%</td>
            <td style="color:#e67e22;">{row['late']}%</td>
        </tr>
        '''
    
    html += "</tbody></table></div>"
    container.innerHTML = html

def generate_scout_report(stats):
    bullets = []
    covered_concepts = set() 
    
    gf = stats.get('gf_avg', 0)
    ga = stats.get('ga_avg', 0)
    cs = stats.get('cs_pct', 0)
    btts = stats.get('btts_pct', 0)
    late = stats.get('late_pct', 0)
    fh = stats.get('fh_pct', 0)
    pen = stats.get('pen_pct', 0)

    if gf > 2.2 and cs > 50:
        bullets.append("🌟 <b>World Class:</b> Elite at both scoring and defending. A title contender.")
        covered_concepts.add("good_attack")
        covered_concepts.add("good_defense")
    elif gf > 2.0 and ga > 1.4:
        bullets.append("🍿 <b>Entertainers:</b> High-octane offense that leaves gaps at the back.")
        covered_concepts.add("good_attack")
        covered_concepts.add("bad_defense")
    elif gf < 1.0 and cs > 45:
        bullets.append("🧱 <b>The Rock:</b> Extremely difficult to break down, but struggles to score.")
        covered_concepts.add("good_defense")
        covered_concepts.add("bad_attack")
    elif btts > 60 and late > 25:
        bullets.append("🎢 <b>Chaos Agents:</b> Their games are unpredictable and often decided late.")
        covered_concepts.add("chaos")
        covered_concepts.add("late_goals")
    elif btts < 30 and ga < 1.0:
        bullets.append("📏 <b>Disciplined:</b> Organized, low-event football. They rarely make mistakes.")
        covered_concepts.add("boring")
        covered_concepts.add("good_defense")
    else:
        if gf > 1.8: 
            bullets.append("⚔️ <b>Attacking Threat:</b> Consistently poses a danger to opponents.")
            covered_concepts.add("good_attack")
        elif cs > 40: 
            bullets.append("🛡️ <b>Defensive Unit:</b> Prioritizes organization over risk.")
            covered_concepts.add("good_defense")
        else: 
            bullets.append("⚖️ <b>Balanced Setup:</b> No glaring weaknesses, but lacks a 'superpower'.")

    if fh > 55:
        bullets.append("⚡ <b>Fast Starters:</b> They tend to blitz opponents in the first half.")
    if late > 30 and "late_goals" not in covered_concepts:
        bullets.append("⏱️ <b>Late Surge:</b> Fitness is a strength; they score heavily in the final 15 mins.")
    if pen > 18:
        bullets.append("🎯 <b>Set-Piece Specialists:</b> A suspiciously high % of goals come from penalties.")
    if btts > 65 and "bad_defense" not in covered_concepts and "chaos" not in covered_concepts:
        bullets.append("👐 <b>Open Games:</b> They rarely keep clean sheets, but rarely get shut out.")
    if cs > 50 and "good_defense" not in covered_concepts:
        bullets.append("🔒 <b>Clean Sheet Machine:</b> They shut out opponents in over half their games.")
    
    if ga > 1.8 and "bad_defense" not in covered_concepts:
         bullets.append("⚠️ <b>Leaky Defense:</b> Conceding nearly 2 goals per game on average.")
    if gf < 0.8 and "bad_attack" not in covered_concepts:
        bullets.append("⚠️ <b>Goal Shy:</b> Major struggles creating chances in open play.")

    return "<br><br>".join(bullets)

DASHBOARD_BUILT = False

def populate_team_dropdown(target_id="team-select-dashboard", wc_only=False):
    current_val = None 
    
    select = js.document.getElementById(target_id)
    if not select:
        select = js.document.getElementById("team-select")
        
    if not select: 
        return 

    try:
        current_val = select.value
    except Exception:
        current_val = None

    select.innerHTML = "" 

    # 1. Prepare the WC slug list ONCE (not inside the loop)
    wc_team_slugs = [sim.get_slug(t) for t in sim.WC_TEAMS]
    
    sorted_teams = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)

    for slug, stats in sorted_teams:
        # 2. FIX: Changed 'team' to 'slug' to match the loop variable
        if wc_only and slug not in wc_team_slugs:
            continue
            
        opt = js.document.createElement("option")
        opt.value = slug
        opt.text = sim.PRETTY_NAMES.get(slug, slug.title())
        select.appendChild(opt)

    if current_val:
        select.value = current_val
        
    if not select.value and select.options.length > 0:
        select.selectedIndex = 0
        select.value = select.options[0].value

def handle_history_filter_change(event):
    is_checked = js.document.getElementById("hist-filter-wc").checked
    populate_team_dropdown(wc_only=is_checked)
    load_data_view(None)

async def view_team_history(event=None):
    global DASHBOARD_BUILT

    if not DASHBOARD_BUILT:
        build_dashboard_shell()
        populate_team_dropdown(target_id="team-select-dashboard")
        DASHBOARD_BUILT = True
    
    js.document.getElementById("view-profile").style.display = "block"
    js.document.getElementById("view-style-map").style.display = "none"

    await asyncio.sleep(0.01) 
    update_dashboard_data()

def update_dashboard_data(event=None):
    select = js.document.getElementById("team-select-dashboard")
    if not select or not select.value:
        populate_team_dropdown(target_id="team-select-dashboard")
        select = js.document.getElementById("team-select-dashboard")

    if not select or not select.value: return

    # 'team' is now the SLUG (e.g., 'curacao') because of our dropdown change
    team = select.value
    stats = sim.TEAM_STATS.get(team)
    if not stats: return

    # Get the "Nice" name for the UI (e.g., 'Curaçao')
    display_name = sim.PRETTY_NAMES.get(team, team.title())

    history = sim.TEAM_HISTORY.get(team)
    # Use the slug to look up the confederation
    confed = sim.TEAM_CONFEDS.get(team, 'OFC')

    sorted_teams = sorted(sim.TEAM_STATS.keys(), key=lambda t: sim.TEAM_STATS[t]['elo'], reverse=True)
    global_rank = sorted_teams.index(team) + 1

    reg_mult = sim.CONFED_MULTIPLIERS.get(confed, 1.0)

    atk_index = stats.get('off', 1.0)
    def_index = stats.get('def', 1.0)

    atk_power = atk_index * reg_mult
    def_power = def_index

    if atk_power > 1.45: atk_desc, atk_color = "Elite 🔥", "var(--accent-green)"
    elif atk_power > 1.10: atk_desc, atk_color = "Strong ⚔️", "var(--accent-blue)"
    else: atk_desc, atk_color = "Average ⚖️", "var(--text-light)"

    if def_power < 0.65: def_desc, def_color = "Iron Wall 🧱", "var(--accent-green)"
    elif def_power < 0.95: def_desc, def_color = "Solid 🛡️", "var(--accent-blue)"
    else: def_desc, def_color = "Leaky ⚠️", "var(--accent-red)"

    form_html = "".join([f"<span class='form-dot {'form-'+c if c in ['W','L','D'] else ''}'>{c if c != '-' else ''}</span>" for c in stats.get('form', '-----')[-5:]]) # Indentation fixed

    def format_rec(rec):
        w, d, l = rec
        total = w + d + l
        pct = (w / total * 100) if total > 0 else 0
        color = "#10b981" if pct >= 45 else ("#f59e0b" if pct >= 25 else "#ef4444")
        if total == 0: return "<span style='color:var(--text-light);'>No Data</span>"
        return f"<span style='color:{color}; font-weight:bold;'>{pct:.1f}% Win</span> <span style='font-size:0.75em; color:var(--text-light);'>({w}W - {d}D - {l}L)</span>"

    # Recency records
    rec_elite = stats.get('rec_elite', [0,0,0])
    rec_stronger = stats.get('rec_stronger', [0,0,0])
    rec_similar = stats.get('rec_similar', [0,0,0])

    best_win = stats.get('best_win', 'None Recorded')

    header = js.document.getElementById("dashboard-header")
    header.innerHTML = f"""
    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                <h1 style="margin:0; font-size:2.4em; font-weight:800; color:var(--text-main); letter-spacing:-1px;">{display_name}</h1>
                <span class="rank-badge">RANK #{global_rank}</span>
            </div>
            <div style="display:flex; gap:15px; font-size:0.9em; color:var(--text-light); font-weight:500;">
                <span>ELO: <b style="color:var(--text-main);">{int(stats['elo'])}</b></span>
                <span>CONFED: <b style="color:var(--accent-blue);">{confed}</b></span>
            </div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:0.7em; font-weight:700; color:var(--text-light); text-transform:uppercase; margin-bottom:8px; letter-spacing:1px;">Recent Form</div>
            <div style="display:flex; gap:4px;">{form_html}</div>
        </div>
    </div>
    """

    sim_h2h_html = ""

    if BULK_STATE and 'h2h' in BULK_STATE and team in BULK_STATE['h2h']:
        h2h_data = BULK_STATE['h2h'][team]
        min_matches = max(5, BULK_STATE['num'] * 0.01)

        valid_opps =[]
        for opp, data in h2h_data.items():
            if data['m'] >= min_matches:
                win_pct = (data['w'] / data['m']) * 100
                valid_opps.append((opp, win_pct, data['m']))

        valid_opps.sort(key=lambda x: x[1], reverse=True)

        def render_h2h_row(x):
            return f"""
            <div style='display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid var(--sidebar-border);'>
                <span style='font-weight:600; color:var(--text-main);'>{x[0].title()} <span style='font-weight:normal; font-size:0.8em; color:var(--text-light);'>({x[2]} matches)</span></span>
                <b style='font-size:1.1em; color:var(--text-main);'>{x[1]:.1f}%</b>
            </div>"""

        if valid_opps:
            best_opps = valid_opps[:3]
            worst_opps = valid_opps[-3:][::-1]

            best_html = "".join([render_h2h_row(x) for x in best_opps])
            worst_html = "".join([render_h2h_row(x) for x in worst_opps])

            sim_h2h_html = f"""
            <div class="dashboard-card" style="margin-top:20px; border-top:4px solid #8b5cf6;">
                <h3 style="margin-top:0; color:#8b5cf6; font-size:1.1em;">🎲 Simulated Head-to-Head (Based on {BULK_STATE['num']:,} Tournaments)</h3>
                <div style="display:flex; gap:20px; margin-top:15px;">
                    <div style="flex:1; background:var(--card-bg); padding:15px; border-radius:8px; border-left:3px solid #10b981;">
                        <h4 style="margin:0 0 10px 0; color:#10b981; font-size:0.85em; text-transform:uppercase; letter-spacing:1px;">🟢 Highest Win Rate</h4>
                        {best_html}
                    </div>
                    <div style="flex:1; background:var(--card-bg); padding:15px; border-radius:8px; border-left:3px solid #ef4444;">
                        <h4 style="margin:0 0 10px 0; color:#ef4444; font-size:0.85em; text-transform:uppercase; letter-spacing:1px;">🔴 Bogey Teams</h4>
                        {worst_html}
                    </div>
                </div>
            </div>
            """
        else:
            sim_h2h_html = f"""
            <div class="dashboard-card" style="margin-top:20px; text-align:center; padding:20px; color:var(--text-light);">
                <span style="font-size:1.5em;">🎲</span><br>
                Simulated data available, but {team.title()} didn't play enough knockout matches to establish statistical rivalries.
            </div>
            """
    else:
        sim_h2h_html = """
        <div class="dashboard-card" style="margin-top:20px; text-align:center; padding:25px; background:rgba(139, 92, 246, 0.05); border:1px dashed rgba(139, 92, 246, 0.3);">
            <span style="font-size:2em; margin-bottom:10px; display:inline-block;">🎲</span><br>
            <b style="color:var(--text-main); font-size:1.1em;">Unlock Simulated Rivalries</b><br>
            <span style="font-size:0.9em; color:var(--text-light); display:inline-block; margin-top:5px;">Run a Bulk Simulation (10,000+ matches) to automatically uncover this team's best matchups and worst "Bogey" teams.</span>
        </div>
        """

    slug_team = sim.get_slug(team)

    talent_info = sim.TEAM_TALENT.get(slug_team, {})
    formation_info = sim.TEAM_FORMATIONS.get(slug_team, {})

    # 1. Build Playmakers List
    # 1. Build Playmakers List
    playmakers_html = ""
    if 'top_players' in talent_info:
        for p in talent_info['top_players'][:4]:
            club = p.get('club', 'Unknown')
            
            # --- FIXED RATING PARSER ---
            rating = '--'
            raw_rat = p.get('rat')
            if raw_rat is not None:
                try:
                    rat_float = float(raw_rat)
                    if rat_float > 0:
                        rating = int(rat_float)
                except (ValueError, TypeError):
                    pass
            # ---------------------------

            playmakers_html += f"""
            <div style="display:flex; justify-content:space-between; font-size:0.85em; padding:6px 0; border-bottom:1px solid var(--sidebar-border);">
                <span style="color:var(--text-main); font-weight:600;">{p['name']} <span style="font-size:0.8em; color:var(--text-light); font-weight:normal;">({club})</span></span>
                <span style="color:var(--accent-blue); font-weight:bold;">{rating}</span>
            </div>"""

    # 2. Build Positional Unit Strengths
    r_att = int(talent_info.get('rating_att', 0))
    r_mid = int(talent_info.get('rating_mid', 0))
    r_def = int(talent_info.get('rating_def', 0))
    r_gk  = int(talent_info.get('rating_gk', 0))

    def make_unit_bar(label, val):
        if val == 0: return ""
        # Dynamic color mapping based on how strong the unit is
        color = "#10b981" if val >= 83 else ("#3b82f6" if val >= 77 else ("#f59e0b" if val >= 72 else "#ef4444"))
        return f"""
        <div style="margin-bottom:8px;">
            <div style="display:flex; justify-content:space-between; font-size:0.75em; font-weight:700; color:var(--text-light); text-transform:uppercase; margin-bottom:4px;">
                <span>{label}</span>
                <span style="color:{color};">{val}</span>
            </div>
            <div style="height:6px; background:var(--sidebar-border); border-radius:3px; overflow:hidden;">
                <div style="height:100%; width:{val}%; background:{color};"></div>
            </div>
        </div>
        """

    # --- NEW DYNAMIC SQUAD OVERVIEW GENERATOR ---
    csv_overview = formation_info.get('wc 2026 squad overview', '')
    if not isinstance(csv_overview, str) or csv_overview.lower() == 'nan':
        csv_overview = ''

    # 1. Smart Player Phrasing based on FIFA Ratings
    top_players = talent_info.get('top_players',[])
    star_text = ""
    if len(top_players) >= 2:
        p1 = top_players[0]
        p2 = top_players[1]
        
        def safe_rat(p):
            try: return float(p.get('rat', 0))
            except: return 0
            
        r1 = safe_rat(p1)
        
        if r1 >= 84:
            star_phrases = [
                f", headlined by world-class talents like {p1['name']} and {p2['name']},",
                f", boasting global superstars like {p1['name']} and {p2['name']},",
                f", driven by the elite quality of {p1['name']} and {p2['name']},"
            ]
        elif r1 >= 76:
            star_phrases = [
                f", led by standout figures like {p1['name']} and {p2['name']},",
                f", featuring key difference-makers like {p1['name']} and {p2['name']},",
                f", relying on the proven quality of {p1['name']} and {p2['name']},"
            ]
        else:
            star_phrases =[
                f", anchored by key contributors like {p1['name']} and {p2['name']},",
                f", characterized by the hard work of {p1['name']} and {p2['name']},",
                f", depending on the chemistry of players like {p1['name']} and {p2['name']},"
            ]
        star_text = random.choice(star_phrases)

    # 2. Smart Unit Phrasing
    unit_dict = {'Attack': r_att, 'Midfield': r_mid, 'Defense': r_def, 'Goalkeeping': r_gk}
    best_unit = max(unit_dict, key=unit_dict.get) if sum(unit_dict.values()) > 0 else "balanced core"
    max_unit_val = unit_dict.get(best_unit, 0)
    
    if max_unit_val >= 83:
        unit_adj = random.choice(["dominant", "fearsome", "world-class", "formidable"])
    elif max_unit_val >= 75:
        unit_adj = random.choice(["capable", "reliable", "solid", "well-rounded"])
    else:
        unit_adj = random.choice(["hard-working", "gritty", "scrappy", "determined"])

    # 3. Smart Elo/Threat Phrasing
    elo_val = int(stats.get('elo', 1200))
    if elo_val >= 1800:
        elo_desc = random.choice(["an imposing", "an elite", "a terrifying"])
        challenge_desc = random.choice([
            "a massive tactical challenge for any opponent",
            "a nightmare matchup for almost anyone in the draw",
            "a dominant force on the global stage"
        ])
    elif elo_val >= 1600:
        elo_desc = random.choice(["a strong", "a highly respectable", "a dangerous"])
        challenge_desc = random.choice([
            "a stiff test for most teams on the global stage",
            "a tricky opponent capable of deep tournament runs",
            "a proven competitive setup"
        ])
    else:
        elo_desc = random.choice(["a developing", "a modest", "an emerging"])
        challenge_desc = random.choice([
            "a scrappy and determined setup",
            "an underdog unit looking to shock the world",
            "a team relying on chemistry and effort over raw talent"
        ])

    form_string = formation_info.get('formation 1', 'fluid')
    sys_phrases =[
        f"Operating primarily out of a <b>{form_string}</b> system",
        f"Deploying a <b>{form_string}</b> base formation",
        f"Set up tactically in a <b>{form_string}</b> shape"
    ]
    
    # 4. Generate the final adaptive text
    dynamic_overview = f"{random.choice(sys_phrases)}, the #{global_rank} globally ranked {display_name} squad is built around a {unit_adj} <b>{best_unit}</b> unit. With {elo_desc} Elo rating of {elo_val}{star_text} they present {challenge_desc}."
    
    if csv_overview:
        dynamic_overview += f"<div style='margin-top:12px; padding-top:12px; border-top:1px dashed #cbd5e1;'><b style='color:var(--accent-blue);'>Scout's Notebook:</b> {csv_overview}</div>"
    # ---------------------------------------------

    unit_bars_html = ""
    if r_att > 0:
        unit_bars_html = f"""
        <div style="margin-top:15px; padding-top:15px; border-top:1px dashed #cbd5e1;">
            <h5 style="margin:0 0 10px 0; color:var(--text-main); font-size:0.85em; text-transform:uppercase;">📊 Unit Strengths</h5>
            {make_unit_bar('Attack', r_att)}
            {make_unit_bar('Midfield', r_mid)}
            {make_unit_bar('Defense', r_def)}
            {make_unit_bar('Goalkeeper', r_gk)}
        </div>
        """

    # 3. Inject Everything
    js.document.getElementById("dashboard-metrics").innerHTML = f"""
    <div style="display:grid; grid-template-columns: 1fr 1fr 1.3fr; gap:20px; margin-bottom:20px;">
        <div class="stat-pill" title="Expected goals scored per match vs. average team">
            <div class="stat-pill-title">Offensive Power 💪</div>
            <div class="stat-pill-value" style="color:var(--accent-blue);">{round(atk_power, 2)}x</div>
            <div style="font-size:0.75em; font-weight:600; color:{atk_color}; margin-top:4px;">{atk_desc}</div>
        </div>
        <div class="stat-pill" title="How well they defend - lower is better">
            <div class="stat-pill-title">Defensive Solidity 🛡️</div>
            <div class="stat-pill-value" style="color:var(--accent-green);">{round(def_index, 2)}x</div>
            <div style="font-size:0.75em; font-weight:600; color:{def_color}; margin-top:4px;">{def_desc}</div>
        </div>

        <div class="dashboard-card" style="margin:0; padding:15px; border-left:4px solid var(--accent-gold);">
            <div style="font-size:0.7em; font-weight:700; color:var(--text-light); margin-bottom:8px; text-transform:uppercase;">All-Time Record by Matchup</div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:0.9em;">
                <span style="color:var(--text-main);">Vs. Global Elite (1800+ Elo):</span>
                <span>{format_rec(rec_elite)}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:0.9em;">
                <span style="color:var(--text-main);">Vs. Better Teams (+75 Elo):</span>
                <span>{format_rec(rec_stronger)}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:0.9em;">
                <span style="color:var(--text-main);">Vs. Peers (Even):</span>
                <span>{format_rec(rec_similar)}</span>
            </div>
            <div style="font-size:0.8em; color:var(--text-light); margin-top:8px; border-top:1px solid var(--sidebar-border); padding-top:6px;">
                <b>Biggest Recent Scalp:</b> <span style="color:var(--text-main); font-weight:bold;">{best_win}</span>
            </div>
        </div>
    </div>

    <!-- PLAYER TALENT AND SQUAD OVERVIEW BLOCK -->
    <div style="display:grid; grid-template-columns: 1fr 1.5fr; gap:20px; margin-bottom:20px;">
        <div class="dashboard-card" style="margin:0; padding:20px;">
            <h4 style="margin:0 0 12px 0; color:var(--text-main); font-size:0.85em; text-transform:uppercase;">🌟 Key Playmakers</h4>
            {playmakers_html if playmakers_html else "<div style='color:var(--text-light); font-size:0.9em;'>No player data available.</div>"}
            <div style="margin-top:15px; font-size:0.8em; color:var(--text-light);">
                <b style="color:var(--text-main);">Primary Formation:</b> {formation_info.get('formation 1', 'Unknown')}
            </div>
        </div>

        <div class="dashboard-card" style="margin:0; padding:20px; background:rgba(59, 130, 246, 0.05); border-left:4px solid var(--accent-blue);">
            <h4 style="margin:0 0 10px 0; color:var(--text-main); font-size:0.85em; text-transform:uppercase;">🔭 Squad Overview</h4>
            <div style="font-size:0.95em; line-height:1.6; color:var(--text-main);">
                {dynamic_overview}
            </div>
            {unit_bars_html}
        </div>
    </div>

    <!-- STANDARD STATS ROW -->
    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:15px;">
        <div class="stat-pill" style="padding:10px;">
            <div class="stat-pill-title" style="font-size:0.65em;">Clean Sheets</div>
            <div style="font-weight:800; font-size:1.1em; color:var(--text-main);">{int(stats.get('cs_pct',0))}%</div>
        </div>
        <div class="stat-pill" style="padding:10px;">
            <div class="stat-pill-title" style="font-size:0.65em;">Both Teams Score</div>
            <div style="font-weight:800; font-size:1.1em; color:var(--text-main);">{int(stats.get('btts_pct',0))}%</div>
        </div>
        <div class="stat-pill" style="padding:10px;">
            <div class="stat-pill-title" style="font-size:0.65em;">Late Gls (75'+)</div>
            <div style="font-weight:800; font-size:1.1em; color:var(--accent-gold);">{int(stats.get('late_pct',0))}%</div>
        </div>
        <div class="stat-pill" style="padding:10px;">
            <div class="stat-pill-title" style="font-size:0.65em;">Penalty Rely</div>
            <div style="font-weight:800; font-size:1.1em; color:var(--text-main);">{int(stats.get('pen_pct',0))}%</div>
        </div>
    </div>

    {sim_h2h_html}
    """

    render_elo_chart(history, display_name)
    render_power_chart(atk_index, def_index, display_name)

def render_elo_chart(history, team):
    js.document.getElementById("dashboard_chart_elo").innerHTML = ""
    
    is_dark = js.document.documentElement.classList.contains("dark-mode")
    text_color = "#e2e8f0" if is_dark else "#64748b"
    grid_color = "#334155" if is_dark else "#cbd5e1"
    
    fig, ax = plt.subplots(figsize=(6, 3.5))
    fig.patch.set_alpha(0.0) 
    ax.patch.set_alpha(0.0)
    ax.plot(history['dates'], history['elo'], color='#3b82f6', linewidth=3)
    ax.grid(True, linestyle='--', alpha=0.4, color=grid_color)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color(grid_color)
    ax.spines['left'].set_color(grid_color)
    ax.tick_params(colors=text_color, labelsize=8)
    fig.tight_layout()
    display(fig, target="dashboard_chart_elo")
    plt.close(fig)

def render_power_chart(atk, dfe, team):
    js.document.getElementById("dashboard_chart_radar").innerHTML = ""
    
    is_dark = js.document.documentElement.classList.contains("dark-mode")
    text_color = "#e2e8f0" if is_dark else "#64748b"
    line_color = "#475569" if is_dark else "#94a3b8"
    
    fig, ax = plt.subplots(figsize=(6, 3.5))
    fig.patch.set_alpha(0.0) 
    ax.patch.set_alpha(0.0)
    
    labels = ['Attack', 'Defense']
    vals = [atk, 2.0 - dfe]
    
    colors = ['#3b82f6', '#10b981']
    bars = ax.bar(labels, vals, color=colors, width=0.5, alpha=0.9)
    ax.axhline(y=1.0, color=line_color, linestyle='--', linewidth=1, label="Global Avg")
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color(line_color)
    ax.spines['left'].set_color(line_color)
    ax.set_ylim(0, max(vals) * 1.3)
    ax.tick_params(colors=text_color, labelsize=9)
    
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                f'{height:.2f}x', ha='center', va='bottom', fontsize=9, fontweight='bold', color=text_color)
    
    fig.tight_layout()
    display(fig, target="dashboard_chart_radar")
    plt.close(fig)

def generate_dynamic_report(team, atk, dfe, upset, stats):
    report_paragraphs =[]
    
    confed = getattr(sim, 'TEAM_CONFEDS', {}).get(team, 'Unknown')
    style = getattr(sim, 'TEAM_PROFILES', {}).get(team, 'Balanced')
    
    sorted_teams = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)
    rank = next((i+1 for i, t in enumerate(sorted_teams) if t[0] == team), 0)
    
    tier_phrases = {
        10: ["a global powerhouse", "an undisputed heavyweight", "a premier title contender"],
        30: ["a formidable contender", "a dangerous knockout threat", "a high-level competitor"],
        60: ["a highly competitive dark horse", "a tricky opponent", "a resilient challenger"],
        999:["an emerging underdog", "a gritty outsider", "a passionate wildcard"]
    }
    
    if rank <= 10: tier_text = random.choice(tier_phrases[10])
    elif rank <= 30: tier_text = random.choice(tier_phrases[30])
    elif rank <= 60: tier_text = random.choice(tier_phrases[60])
    else: tier_text = random.choice(tier_phrases[999])
    
    ov_phrases =[
        f"Ranked #{rank} globally, {team.title()} stands as {tier_text} out of {confed}.",
        f"Hailing from {confed}, the #{rank} ranked {team.title()} is widely regarded as {tier_text}.",
        f"Currently sitting at #{rank} in the world rankings, {team.title()} is {tier_text} representing {confed}."
    ]
    report_paragraphs.append(f"<b>Overview:</b> {random.choice(ov_phrases)} Their overall system is classified as <b>{style}</b>.")
    
    tactical =[]
    pace = stats.get('pace_factor', 1.0)
    ko_exp = stats.get('ko_exp_weighted', 0)
    momentum = stats.get('momentum', 0.0)
    
    if pace > 1.15: 
        tactical.append(random.choice([
            "Their games are typically open and played at a frantic pace, frequently resulting in end-to-end action.",
            "They thrive in chaotic, fast-paced matches that stretch opponents and create high-scoring affairs.",
            "Expect a track meet; they push the tempo aggressively and force games to break open."
        ]))
    elif pace < 0.90: 
        tactical.append(random.choice([
            "They prefer to control the tempo, systematically dragging opponents into tight, low-scoring tactical battles.",
            "They excel at slowing the game down, frustrating opponents with methodical and risk-averse play.",
            "Matches involving them are usually chess matches—slow, tight, and decided by fine margins."
        ]))
    
    if atk > 1.10: 
        tactical.append(random.choice([
            "Offensively, they consistently create high-quality chances and punish mistakes.",
            "They boast a lethal attack that can dissect defenses from multiple angles.",
            "Their forward line is a constant threat, generating expected goals at an elite rate."
        ]))
    elif atk < 0.90: 
        tactical.append(random.choice([
            "Goal-scoring can be a severe struggle for them in open play.",
            "They frequently lack a cutting edge in the final third, relying heavily on set pieces or luck.",
            "Creating high-value offensive chances is a well-documented weakness for this squad."
        ]))
    
    if dfe < 0.85: 
        tactical.append(random.choice([
            "Defensively, they are incredibly disciplined and notoriously difficult to break down.",
            "Their backline operates like a fortress, rarely conceding high-quality looks.",
            "They pride themselves on a watertight defensive structure that stifles opposing attackers."
        ]))
    elif dfe > 1.10: 
        tactical.append(random.choice([
            "Their backline is prone to leaks, heavily relying on outscoring their opponents to secure results.",
            "Defensive fragility is a major concern, often leaving gaps that top-tier teams easily exploit.",
            "They are statistically vulnerable at the back, meaning clean sheets are a rarity."
        ]))
    
    report_paragraphs.append("<b>Identity:</b> " + " ".join(tactical))
    
    quirks =[]
    vol = stats.get('volatility', 0.15)
    
    if vol >= 0.25: 
        quirks.append(random.choice([
            "⚠️ <b>High Volatility:</b> Their matches are wildly unpredictable. They can shock the world or collapse spectacularly.",
            "⚠️ <b>High Volatility:</b> A classic wildcard. They play up (and down) to their competition constantly.",
            "⚠️ <b>High Volatility:</b> Consistently inconsistent. They have the raw variance to pull off massive upsets."
        ]))
    elif vol <= 0.10:
        quirks.append(random.choice([
            "🔒 <b>Highly Consistent:</b> They perform exactly to expectations. They rarely drop points to underdogs.",
            "🔒 <b>Highly Consistent:</b> A machine-like setup. Minimal variance means they rarely beat themselves.",
            "🔒 <b>Highly Consistent:</b> Extremely clinical against weaker sides, though they lack the chaotic edge to upset giants."
        ]))
        
    if ko_exp > 15:
        quirks.append("They boast immense tournament pedigree and vast experience navigating high-pressure knockout scenarios.")
    if momentum > 0.5:
        quirks.append("They are currently riding a massive wave of positive form, surging up the global power rankings.")
    elif momentum < -0.5:
        quirks.append("They enter the current cycle struggling for form, bleeding Elo rating over their last 10 matches.")
    
    if quirks: 
        report_paragraphs.append("<b>Tournament Readiness:</b> " + " ".join(quirks))

    return "".join([f"<div style='margin-bottom:12px;'>{p}</div>" for p in report_paragraphs])

async def refresh_team_analysis(event=None):
    update_dashboard_data()

async def plot_style_map(event):
    global DASHBOARD_BUILT
    if not DASHBOARD_BUILT:
        build_dashboard_shell()
        DASHBOARD_BUILT = True
        
    js.document.getElementById("view-profile").style.display = "none"
    js.document.getElementById("view-style-map").style.display = "block"
    target_div = js.document.getElementById("main-chart-container")
    
    target_div.innerHTML = "<div style='text-align:center; padding:50px;'><div class='loader-circle' style='border-top-color:var(--accent-blue); margin: 0 auto 20px;'></div>Generating Tactical Landscape...</div>"
    await asyncio.sleep(0.1)
    
    fig, ax = plt.subplots(figsize=(14, 7), dpi=100)
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)

    wc_only = js.document.getElementById("hist-filter-wc").checked
    sorted_teams = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)
    teams_to_plot = [t for t in sorted_teams if t[0] in sim.WC_TEAMS] if wc_only else sorted_teams[:48]

    mean_gf = np.mean([s.get('adj_gf', 1.25) for t, s in teams_to_plot])
    mean_ga = np.mean([s.get('adj_ga', 1.25) for t, s in teams_to_plot])

    confed_colors = {'UEFA': '#3b82f6', 'CONMEBOL': '#10b981', 'CONCACAF': '#f59e0b', 'CAF': '#8b5cf6', 'AFC': '#ef4444', 'OFC': '#64748b'}

    x_vals, y_vals, sizes, colors, labels = [], [], [], [], []
    for team, stats in teams_to_plot:
        gf, ga, elo = stats.get('adj_gf', 1.25), stats.get('adj_ga', 1.25), stats.get('elo', 1200)
        x_vals.append(gf); y_vals.append(ga)
        sizes.append(max(50, (elo - 800) ** 1.2 / 5) if elo > 800 else 50)
        colors.append(confed_colors.get(sim.TEAM_CONFEDS.get(team, 'OFC'), '#cbd5e1'))
        labels.append(team.title())

    ax.axhline(mean_ga, color='#cbd5e1', linestyle='--', zorder=1)
    ax.axvline(mean_gf, color='#cbd5e1', linestyle='--', zorder=1)

    ax.scatter(x_vals, y_vals, s=sizes, c=colors, alpha=0.7, edgecolors='white', linewidth=1, zorder=3)

    for i, label in enumerate(labels):
        ax.text(x_vals[i], y_vals[i] + 0.04, label, fontsize=8, ha='center', va='bottom', color='#334155', fontweight='600', zorder=4, bbox=dict(facecolor='white', alpha=0.5, edgecolor='none', pad=0.5))

    ax.text(0.98, 0.98, "Elite Offense / Elite Defense", transform=ax.transAxes, fontsize=14, color='#10b981', alpha=0.4, ha='right', va='top', fontweight='bold', zorder=2)
    ax.text(0.02, 0.02, "Struggling / Leaky", transform=ax.transAxes, fontsize=14, color='#ef4444', alpha=0.4, ha='left', va='bottom', fontweight='bold', zorder=2)
    ax.text(0.98, 0.02, "Entertainers (All Attack, No Def)", transform=ax.transAxes, fontsize=12, color='#f59e0b', alpha=0.4, ha='right', va='bottom', fontweight='bold', zorder=2)
    ax.text(0.02, 0.98, "Defensive / Low Scoring", transform=ax.transAxes, fontsize=12, color='#3b82f6', alpha=0.4, ha='left', va='top', fontweight='bold', zorder=2)

    ax.set_title("Tactical DNA Landscape (Expected Goals For vs. Against)", fontsize=16, fontweight='800', color='#0f172a', pad=20)
    ax.set_xlabel("Attacking Power (Expected Goals For)", fontsize=12, fontweight='bold', color='#64748b')
    ax.set_ylabel("Defensive Solidity (Expected Goals Against)", fontsize=12, fontweight='bold', color='#64748b')
    ax.invert_yaxis() 
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#cbd5e1')
    ax.spines['bottom'].set_color('#cbd5e1')
    ax.grid(True, linestyle=':', alpha=0.4, color='#cbd5e1', zorder=0)

    import matplotlib.patches as mpatches
    ax.legend(
        handles=[mpatches.Patch(color=c, label=conf) for conf, c in confed_colors.items()], 
        loc='upper center', 
        bbox_to_anchor=(0.5, -0.1), 
        ncol=6, 
        frameon=False, 
        title='Confederation', 
        title_fontproperties={'weight':'bold'}
    )

    plt.tight_layout()
    target_div.innerHTML = ""
    display(fig, target="main-chart-container")
    plt.close(fig)

asyncio.ensure_future(initialize_app())