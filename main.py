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

# GLOBAL VARIABLES
LAST_SIM_RESULTS = {}
# This list prevents the browser-to-python bridges from being deleted
EVENT_HANDLERS = []

# =============================================================================
# --- STARTUP & INITIALIZATION ---
# =============================================================================
async def initialize_app():
    try:
        js.console.log("Initializing Engine...")
        
        # 1. Initialize Backend
        sim.DATA_DIR = "."
        
        # Run calculations
        sim.TEAM_STATS, sim.TEAM_PROFILES, sim.AVG_GOALS = sim.initialize_engine()
        sim.calculate_confed_strength() 

        # 2. Setup UI Tabs & Buttons (This is where we bind clicks)
        setup_interactions()
        
        # 3. Populate Initial Dropdowns
        populate_team_dropdown(wc_only=False)

        # 4. Hide Loading Screen
        js.document.getElementById("loading-screen").style.display = "none"
        js.document.getElementById("main-dashboard").style.display = "grid" # Changed to grid to match CSS
        
        js.console.log("Engine Ready.")

    except Exception as e:
        # Show error on screen
        js.document.getElementById("loading-screen").innerHTML = f"""
        <div style='color:#e74c3c; text-align:center; padding:20px;'>
            <h1>Startup Error</h1>
            <p>The Python script crashed:</p>
            <pre style='background:black; padding:15px; border-radius:5px; text-align:left;'>{str(e)}</pre>
            <p>Check your console (F12) for more details.</p>
        </div>
        """
        js.console.error(f"CRITICAL ERROR: {e}")

# =============================================================================
# --- 1. TAB NAVIGATION & INTERACTION SETUP ---
# =============================================================================
def switch_tab(tab_id):
    # Hide all tabs
    for t in ["tab-single", "tab-bulk", "tab-data", "tab-history", "tab-analysis"]:
        el = js.document.getElementById(t)
        if el: el.style.display = "none"
        
    # Show selected
    target = js.document.getElementById(tab_id)
    if target: target.style.display = "block"

def setup_interactions():
    """
    Consolidates all event binding into one safe place.
    Includes Event Delegation for the Groups Grid.
    """
    global EVENT_HANDLERS 

    # Helper to create persistent listeners
    def bind_click(btn_id, func):
        el = js.document.getElementById(btn_id)
        if el:
            # Create the proxy
            proxy = create_proxy(func)
            # IMPORTANT: Store it so it doesn't get Garbage Collected
            EVENT_HANDLERS.append(proxy) 
            # Attach it
            el.addEventListener("click", proxy)
        else:
            js.console.warn(f"Warning: Element {btn_id} not found in HTML")

    # --- Navigation Tabs ---
    bind_click("btn-tab-single", lambda e: switch_tab("tab-single"))
    bind_click("btn-tab-bulk", lambda e: switch_tab("tab-bulk"))
    bind_click("btn-tab-data", lambda e: switch_tab("tab-data"))
    bind_click("btn-tab-history", lambda e: switch_tab("tab-history"))
    bind_click("btn-tab-analysis", lambda e: switch_tab("tab-analysis"))

    build_dashboard_shell()
    populate_team_dropdown(target_id="team-select-dashboard")

    # --- Simulation Buttons ---
    bind_click("btn-run-single", run_single_sim)
    bind_click("btn-run-bulk", run_bulk_sim)

    # --- Analysis Buttons ---
    bind_click("btn-view-history", view_team_history)
    bind_click("btn-view-style-map", plot_style_map) 

    # --- Filters ---
    bind_click("hist-filter-wc", handle_history_filter_change)
    bind_click("data-filter-wc", load_data_view)
    
    # --- Expose Global Functions ---
    proxy_view_group = create_proxy(open_group_modal)
    EVENT_HANDLERS.append(proxy_view_group)
    js.window.view_group_matches = proxy_view_group

    proxy_view_history = create_proxy(view_team_history)
    EVENT_HANDLERS.append(proxy_view_history)
    js.window.trigger_view_history = proxy_view_history

    proxy_refresh = create_proxy(refresh_team_analysis)
    EVENT_HANDLERS.append(proxy_refresh)
    js.window.refresh_team_analysis = proxy_refresh

    # ============================================================
    # --- NEW: EVENT DELEGATION FOR GROUPS ---
    # ============================================================
    def handle_group_grid_click(event):
        # We start at the element clicked (event.target)
        el = event.target
        
        # Traverse up the DOM until we find the container or a group card
        # This handles clicks on the text, table, or empty space inside the card
        while el and el.id != "groups-container":
            if el.id and el.id.startswith("group-card-"):
                # We found the card! Extract the group name (e.g., "A")
                group_name = el.id.replace("group-card-", "")
                open_group_modal(group_name)
                return
            el = el.parentElement

    # Bind this ONE listener to the parent container
    bind_click("groups-container", handle_group_grid_click)
    
# =============================================================================
# --- 2. SINGLE SIMULATION ---
# =============================================================================
async def run_single_sim(event):
    global LAST_SIM_RESULTS
    
    # UI Prep
    js.document.getElementById("visual-loading").style.display = "block"
    js.document.getElementById("visual-results-container").style.display = "none"
    
    # Yield control to allow UI update
    await asyncio.sleep(0.02)
    
    try:
        result = sim.run_simulation(fast_mode=False)
        LAST_SIM_RESULTS = result 
        
        champion = result["champion"]
        groups_data = result["groups_data"]
        bracket_data = result["bracket_data"]
        
        # Render Champion
        js.document.getElementById("visual-champion-name").innerText = champion.upper()

        # Render Groups
        groups_html = ""
        group_names = [] # List to track groups for binding clicks later

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

        # Render Bracket
        bracket_html = ""
        
        for round_data in bracket_data:
            bracket_html += f'<div class="bracket-round"><div class="round-title">{round_data["round"]}</div>'
            
            for m in round_data['matches']:
                
                c1 = "winner-text" if m['winner'] == m['t1'] else ""
                c2 = "winner-text" if m['winner'] == m['t2'] else ""
                
                # Logic to handle Penalty text display
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

        # Reveal UI
        js.document.getElementById("visual-loading").style.display = "none"
        js.document.getElementById("visual-results-container").style.display = "block"

    except Exception as e:
        js.document.getElementById("visual-loading").innerHTML = f"Error: {e}"
        js.console.error(f"SIM ERROR: {e}")

# Match Modal Logic
def open_group_modal(grp_name):
    try:
        # Retrieve matches from the last results
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
    num_el = js.document.getElementById("bulk-count")
    out_div = js.document.getElementById("bulk-results")
    if not num_el or not out_div: return
    num = int(num_el.value)
    
    # Initialize structures
    team_stats = {}   
    group_mapping = {} 
    
    def init_team(t):
        if t not in team_stats:
            # We add 'apps' to track how many times a playoff team actually made the WC
            team_stats[t] = {'apps': 0, 'grp_1st': 0, 'r32': 0, 'r16':0, 'qf':0, 'sf': 0, 'final': 0, 'win': 0}

    out_div.innerHTML = f"""
    <div style='text-align:center; padding:40px;'>
        <h2 style='color:var(--text-main); margin-bottom:15px;'>🎲 Simulating {num} Tournaments...</h2>
        <div style='width:100%; max-width:400px; background:#e2e8f0; border-radius:10px; height:12px; margin: 0 auto; overflow:hidden; box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);'>
            <div id='bulk-progress-bar' style='width:0%; height:100%; background:linear-gradient(90deg, #3b82f6, #2563eb); transition:width 0.1s ease-out; border-radius:10px;'></div>
        </div>
        <div id='bulk-progress-text' style='margin-top:12px; font-size:1em; font-weight:700; color:#3b82f6;'>0% Complete</div>
    </div>
    """
    await asyncio.sleep(0.05)

    try:
        for i in range(num):
            res = sim.run_simulation(fast_mode=False, quiet=True)
            
            # --- A. GROUP & APPEARANCE ANALYSIS ---
            for grp, table in res['groups_data'].items():
                if grp not in group_mapping: group_mapping[grp] = {}
                
                # Track Group Winner
                first_team = table[0]['team']
                init_team(first_team)
                team_stats[first_team]['grp_1st'] += 1
                
                # Track Appearance (Crucial for Playoff teams)
                for row in table:
                    t = row['team']
                    init_team(t)
                    team_stats[t]['apps'] += 1
                    group_mapping[grp][t] = True 
                    # REMOVED: r32 increment here to prevent double counting

            # --- B. KNOCKOUT ANALYSIS ---
            # Using the helper to ensure each team is counted once per round reached
            bracket = res['bracket_data']
            if bracket:
                def process_round_by_name(round_name, stat_key):
                    for r in bracket:
                        if r['round'] == round_name:
                            for m in r['matches']:
                                init_team(m['t1']); team_stats[m['t1']][stat_key] += 1
                                init_team(m['t2']); team_stats[m['t2']][stat_key] += 1

                process_round_by_name('Round of 32', 'r32')
                process_round_by_name('Round of 16', 'r16')
                process_round_by_name('Quarter-finals', 'qf')
                process_round_by_name('Semi-finals', 'sf')
                process_round_by_name('Final', 'final')

            # Track Winner
            champ = res['champion']
            init_team(champ)
            team_stats[champ]['win'] += 1
            
            # CRITICAL FIX: Properly yield to Pyodide event loop to draw progress
            if i % max(1, num // 20) == 0:
                pct = int((i / num) * 100)
                pbar = js.document.getElementById("bulk-progress-bar")
                ptext = js.document.getElementById("bulk-progress-text")
                if pbar: pbar.style.width = f"{pct}%"
                if ptext: ptext.innerHTML = f"{pct}% Complete"
                await asyncio.sleep(0.01)
            
        # --- 7. GENERATE OUTPUT ---
        html = "<h2 style='color:#2c3e50;'>📋 PROJECTED GROUP STANDINGS</h2>"
        html += "<div style='display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:20px;'>"
        
        for grp in sorted(group_mapping.keys()):
            html += f"""<div class='dashboard-card'>
                <h3 style='color:var(--accent-blue);'>🔹 Group {grp}</h3>
                <table style='width:100%; font-size:0.85em;'>
                    <tr style='text-align:left; color:var(--text-light);'>
                        <th>Team</th>
                        <th style='text-align:right;'>Win Group</th>
                        <th style='text-align:right;'>Advance</th>
                    </tr>"""
            
            # Sort teams in this group by their overall advancement probability
            group_teams = list(group_mapping[grp].keys())
            group_teams.sort(key=lambda t: team_stats[t]['r32'], reverse=True)

            for t in group_teams:
                s = team_stats[t]
                # Probability of reaching R32 relative to the WHOLE tournament
                adv_pct = (s['r32'] / num) * 100
                win_grp_pct = (s['grp_1st'] / num) * 100
                
                # If a team only appears in 10% of sims (playoffs), we fade their name
                opacity = "1.0" if (s['apps']/num) > 0.5 else "0.5"
                
                html += f"""<tr style='opacity:{opacity};'>
                    <td style='font-weight:600;'>{t.title()}</td>
                    <td style='text-align:right;'>{win_grp_pct:.1f}%</td>
                    <td style='text-align:right; font-weight:bold;'>{adv_pct:.1f}%</td>
                </tr>"""
            html += "</table></div>"
        
        html += "</div>"

        # SECTION 2: TOURNAMENT FAVORITES
        html += "<br><h2 style='color:#2c3e50; border-bottom:2px solid #ddd; padding-bottom:10px; margin-top:30px;'>🏆 TOURNAMENT FAVORITES</h2>"
        html += """
        <table style="width:100%; border-collapse:collapse; background:white; border-radius:8px; overflow:hidden; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
            <tr style="background:#2c3e50; color:white; text-align:left;">
                <th style="padding:12px;">Team</th>
                <th style="padding:12px; text-align:right; background:#34495e;">R16 %</th>
                <th style="padding:12px; text-align:right; background:#34495e;">QF %</th>
                <th style="padding:12px; text-align:right;">Semis %</th>
                <th style="padding:12px; text-align:right;">Finals %</th>
                <th style="padding:12px; text-align:right; background:#f1c40f; color:#2c3e50;">Win %</th>
            </tr>
        """
        
        all_teams_sorted = sorted(team_stats.items(), key=lambda x: x[1]['win'], reverse=True)
        
        for team, s in all_teams_sorted:
            win_pct = (s['win'] / num) * 100
            final_pct = (s['final'] / num) * 100
            semi_pct = (s['sf'] / num) * 100
            qf_pct = (s['qf'] / num) * 100
            r16_pct = (s['r16'] / num) * 100
            
            # Threshold to hide unlikely teams (Adjusted slightly to show more depth)
            if r16_pct < 1.0 and win_pct < 0.1: continue
            
            html += f"""
            <tr style="border-bottom:1px solid #eee;">
                <td style="padding:10px; font-weight:bold;">{team.title()}</td>
                <td style="padding:10px; text-align:right; color:#7f8c8d; background:#f8f9fa;">{r16_pct:.1f}%</td>
                <td style="padding:10px; text-align:right; color:#7f8c8d; background:#f8f9fa;">{qf_pct:.1f}%</td>
                <td style="padding:10px; text-align:right; color:#34495e;">{semi_pct:.1f}%</td>
                <td style="padding:10px; text-align:right;">{final_pct:.1f}%</td>
                <td style="padding:10px; text-align:right; font-weight:bold; background:#fffcf5;">{win_pct:.1f}%</td>
            </tr>
            """
            
        html += "</table>"
        out_div.innerHTML = html

    except Exception as e:
        out_div.innerHTML = f"<div style='color:red; padding:20px; font-weight:bold;'>Error: {e}</div>"
        js.console.error(f"BULK SIM ERROR: {e}")

# =============================================================================
# --- 4. DATA VIEW ---
# =============================================================================

def build_dashboard_shell():
    """
    Injects the dashboard layout using the modern CSS variables from index.html
    """
    container = js.document.getElementById("tab-history")
    
    container.innerHTML = """
    <div style="background:var(--card-bg); padding:15px; border-radius:12px; display:flex; gap:15px; align-items:center; margin-bottom:20px; box-shadow:var(--shadow-sm); border:1px solid #e2e8f0;">
        <label style="font-weight:600; color:var(--text-main); font-size:0.9em;">Select Team:</label>
        <select id="team-select-dashboard" onchange="window.refresh_team_analysis()" style="padding:10px; border-radius:8px; border:1px solid #cbd5e1; flex-grow:1; background:#f8fafc; color:var(--text-main); font-weight:500;"></select>
        
        <div style="width:1px; height:30px; background:#e2e8f0; margin:0 5px;"></div>
        
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


def load_data_view(event):
    container = js.document.getElementById("data-table-container")
    if not container: return
    
    container.innerHTML = "<div style='padding:20px; text-align:center;'>Loading raw data...</div>" 
    sidebar_checkbox = js.document.getElementById("hist-filter-wc")
    wc_only = sidebar_checkbox.checked if sidebar_checkbox else False
    
    html = """
    <div style="margin-bottom:10px; font-size:0.8em; color:#7f8c8d; text-align:right;">
        *Tactical stats (1H, Late, Pens) based on available scorer data
    </div>
    <table class="rankings-table">
        <thead>
            <tr>
                <th>Rank</th>
                <th>Team</th>
                <th>Elo</th>
                <th>Form</th>
                <th>Matches</th>
                <th>Gls For</th>
                <th>Gls Against</th>
                <th>Clean Sheets</th>
                <th>Both Teams Score</th>
                <th title="% of 1st Half Gls">1st Half Gls%</th>
                <th title="% of Gls After 75'">Late Gls%</th>
                <th title="% of Pen Gls">Pen%</th>
            </tr>
        </thead>
        <tbody>
    """
    
    sorted_teams = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)
    
    DUMMY_GAMES = 10 
    GLOBAL_AVG = sim.AVG_GOALS if sim.AVG_GOALS > 0 else 1.25

    rank_counter = 0
    for team, stats in sorted_teams:
        if wc_only and team not in sim.WC_TEAMS: continue
        
        matches = stats.get('matches', 0)
        if matches < 7: continue 

        rank_counter += 1

        # 1. Reverse-Engineer True Totals
        reg_gf_avg = stats.get('gf_avg', 0)
        reg_ga_avg = stats.get('ga_avg', 0)
        
        true_gf = (reg_gf_avg * (matches + DUMMY_GAMES)) - (DUMMY_GAMES * GLOBAL_AVG)
        true_ga = (reg_ga_avg * (matches + DUMMY_GAMES)) - (DUMMY_GAMES * GLOBAL_AVG)
        
        total_gf = max(0, int(round(true_gf)))
        total_ga = max(0, int(round(true_ga)))

        # 2. Form Formatting
        raw_form = stats.get('form', '-----')
        formatted_form = ""
        for char in raw_form:
            if char == 'W': color = "#27ae60"
            elif char == 'L': color = "#e74c3c"
            else: color = "#bdc3c7"
            formatted_form += f"<span style='color:{color}; font-weight:bold;'>{char}</span>"

        # 3. Get Counts & Percentages
        cs = stats.get('clean_sheets', 0)
        btts = stats.get('btts', 0)
        
        # We use the PERCENTAGES calculated in initialize_engine
        # These are accurate even if the raw count is low
        fh_pct = int(stats.get('fh_pct', 0))
        late_pct = int(stats.get('late_pct', 0))
        pen_pct = int(stats.get('pen_pct', 0))
        
        html += f"""
        <tr>
            <td style="font-weight:bold;">#{rank_counter}</td>
            <td style="font-weight:600">{team.title()}</td>
            <td style="font-weight:bold; color:#2c3e50;">{int(stats['elo'])}</td>
            <td style="font-family:monospace; letter-spacing:2px;">{formatted_form}</td>
            <td style="text-align:center;">{matches}</td>
            <td style="color:#2980b9; font-weight:bold;">{total_gf}</td>
            <td style="color:#c0392b;">{total_ga}</td>
            <td>{cs}</td>
            <td>{btts}</td>
            <td style="color:#7f8c8d;">{fh_pct}%</td>
            <td style="color:#e67e22;">{late_pct}%</td>
            <td style="color:#7f8c8d;">{pen_pct}%</td>
        </tr>
        """
    
    html += "</tbody></table>"
    container.innerHTML = html

def generate_scout_report(stats):
    """
    Generates a smart, multi-line report.
    Uses 'covered_concepts' to ensure subsequent lines do not repeat 
    information already implied by the main headline.
    """
    bullets = []
    covered_concepts = set() # Tracks what we have already said
    
    # Extract values
    gf = stats.get('gf_avg', 0)
    ga = stats.get('ga_avg', 0)
    cs = stats.get('cs_pct', 0)
    btts = stats.get('btts_pct', 0)
    late = stats.get('late_pct', 0)
    fh = stats.get('fh_pct', 0)
    pen = stats.get('pen_pct', 0)

    # --- 1. THE HEADLINE (The Core Identity) ---
    
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
        # Fallbacks
        if gf > 1.8: 
            bullets.append("⚔️ <b>Attacking Threat:</b> Consistently poses a danger to opponents.")
            covered_concepts.add("good_attack")
        elif cs > 40: 
            bullets.append("🛡️ <b>Defensive Unit:</b> Prioritizes organization over risk.")
            covered_concepts.add("good_defense")
        else: 
            bullets.append("⚖️ <b>Balanced Setup:</b> No glaring weaknesses, but lacks a 'superpower'.")

    # --- 2. TACTICAL QUIRKS (Add only if not redundant) ---

    # Timing: Fast Starters
    if fh > 55:
        bullets.append("⚡ <b>Fast Starters:</b> They tend to blitz opponents in the first half.")

    # Timing: Late Surge (Skip if we already called them 'Chaos Agents' who win late)
    if late > 30 and "late_goals" not in covered_concepts:
        bullets.append("⏱️ <b>Late Surge:</b> Fitness is a strength; they score heavily in the final 15 mins.")

    # Set Pieces
    if pen > 18:
        bullets.append("🎯 <b>Set-Piece Specialists:</b> A suspiciously high % of goals come from penalties.")

    # Volatility (BTTS) - Skip if we already said they have bad defense or are chaos agents
    if btts > 65 and "bad_defense" not in covered_concepts and "chaos" not in covered_concepts:
        bullets.append("👐 <b>Open Games:</b> They rarely keep clean sheets, but rarely get shut out.")

    # Defense Strength - Skip if we already said they are World Class or The Rock
    if cs > 50 and "good_defense" not in covered_concepts:
        bullets.append("🔒 <b>Clean Sheet Machine:</b> They shut out opponents in over half their games.")

    # --- 3. RED FLAGS (Only if extreme) ---
    
    if ga > 1.8 and "bad_defense" not in covered_concepts:
         bullets.append("⚠️ <b>Leaky Defense:</b> Conceding nearly 2 goals per game on average.")
         
    if gf < 0.8 and "bad_attack" not in covered_concepts:
        bullets.append("⚠️ <b>Goal Shy:</b> Major struggles creating chances in open play.")

    return "<br><br>".join(bullets)

# =============================================================================
# --- 5. HISTORY & ANALYSIS  ---
# =============================================================================

# Global flag to track if we have injected the dashboard HTML yet
DASHBOARD_BUILT = False

def populate_team_dropdown(target_id="team-select-dashboard", wc_only=False):
    """
    Robustly populates the team dropdown. 
    Can target either the dashboard select or a specific ID.
    """
    select = js.document.getElementById(target_id)
    
    # If the specific target doesn't exist, try the sidebar fallback
    if not select:
        select = js.document.getElementById("team-select")
        
    if not select:
        return # Exit if neither exists

    current_val = select.value
    select.innerHTML = "" # Clear existing options

    # Sort teams by ELO
    sorted_teams = sorted(
        sim.TEAM_STATS.items(),
        key=lambda x: x[1]['elo'],
        reverse=True
    )

    # Create Options
    for team, stats in sorted_teams:
        if wc_only and team not in sim.WC_TEAMS:
            continue

        opt = js.document.createElement("option")
        opt.value = team
        opt.text = team.title()
        select.appendChild(opt)

    # Restore selection or default to first option
    if current_val:
        select.value = current_val
    
    if not select.value and select.options.length > 0:
        select.selectedIndex = 0
        select.value = select.options[0].value

def handle_history_filter_change(event):
    is_checked = js.document.getElementById("hist-filter-wc").checked
    # Refresh the active view
    populate_team_dropdown(wc_only=is_checked)
    load_data_view(None)

def build_dashboard_shell():
    """
    Injects the dashboard layout safely, preserving the containers 
    needed for both History and Style Map modes.
    """
    container = js.document.getElementById("tab-history")
    
    container.innerHTML = """
    <div style="background:white; padding:15px; border-radius:8px; display:flex; gap:10px; align-items:center; margin-bottom:20px; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
        <label style="font-weight:bold; color:#2c3e50;">Select Team:</label>
        <select id="team-select-dashboard" onchange="window.refresh_team_analysis()" style="padding:8px; border-radius:4px; border:1px solid #bdc3c7; flex-grow:1;"></select>
        
        <div style="width:1px; height:30px; background:#eee; margin:0 10px;"></div>
        
        <button id="btn-show-dashboard" class="nav-btn" style="width:auto; background:#34495e; padding:8px 15px;">📊 Profile</button>
        <button id="btn-show-style" class="nav-btn" style="width:auto; background:#8e44ad; padding:8px 15px;">🗺️ Style Map</button>
    </div>

    <div id="view-profile">
        <div id="dashboard-header"></div>
        <div id="dashboard-metrics"></div>

        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap:20px;">
            <div style="background:white; padding:20px; border-radius:10px; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                <h4 style="margin-top:0; color:#7f8c8d;">Performance History</h4>
                <div id="dashboard_chart_elo"></div>
            </div>
            <div style="background:white; padding:20px; border-radius:10px; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                <h4 style="margin-top:0; color:#7f8c8d;">Strategic DNA</h4>
                <div id="dashboard_chart_radar"></div>
            </div>
        </div>
    </div>

    <div id="view-style-map" style="display:none;">
        <div style="background:white; padding:20px; border-radius:10px; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
             <div id="main-chart-container" style="min-height:500px;"></div>
        </div>
    </div>
    """

    # Re-bind the internal buttons since we just created them
    # We use a helper function here or manual binding
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
            # Trigger the style map plot logic
            asyncio.ensure_future(plot_style_map(None))

    # Bind the toggle buttons
    js.document.getElementById("btn-show-dashboard").onclick = create_proxy(lambda e: toggle_view('profile'))
    js.document.getElementById("btn-show-style").onclick = create_proxy(lambda e: toggle_view('style'))

async def view_team_history(event=None):
    global DASHBOARD_BUILT

    # 1. Build the HTML shell if it doesn't exist
    if not DASHBOARD_BUILT:
        build_dashboard_shell()
        populate_team_dropdown(target_id="team-select-dashboard")
        DASHBOARD_BUILT = True
    
    # 2. Ensure Profile View is visible
    js.document.getElementById("view-profile").style.display = "block"
    js.document.getElementById("view-style-map").style.display = "none"

    # 3. Update the Data
    await asyncio.sleep(0.01) # Yield to let DOM update
    update_dashboard_data()


def update_dashboard_data():
    select = js.document.getElementById("team-select-dashboard")
    if not select or not select.value:
        populate_team_dropdown(target_id="team-select-dashboard") 
        select = js.document.getElementById("team-select-dashboard")
    
    if not select or not select.value: return 

    team = select.value
    stats = sim.TEAM_STATS.get(team)
    history = sim.TEAM_HISTORY.get(team)
    confed = sim.TEAM_CONFEDS.get(team.lower(), 'OFC')
    
    # --- 1. CALCULATE WORLD RANK & PERCENTILES ---
    sorted_teams = sorted(sim.TEAM_STATS.keys(), key=lambda t: sim.TEAM_STATS[t]['elo'], reverse=True)
    global_rank = sorted_teams.index(team) + 1
    
    # Confederation Multiplier Impact
    reg_mult = sim.CONFED_MULTIPLIERS.get(confed, 1.0)
    
    # SOS Adjusted Power
    atk_index = stats.get('off', 1.0)
    def_index = stats.get('def', 1.0)
    
    # Final adjusted power for display
    atk_power = atk_index * reg_mult
    def_power = def_index # Defense is already relative to opponent in your engine
    
    # Percentile Logic (Casual Friendly)
    if atk_power > 1.4: atk_desc = "Elite 🔥"; atk_color = "var(--accent-green)"
    elif atk_power > 1.1: atk_desc = "Strong ⚔️"; atk_color = "var(--accent-blue)"
    else: atk_desc = "Average ⚖️"; atk_color = "var(--text-light)"

    if def_power < 0.8: def_desc = "Iron Wall 🧱"; def_color = "var(--accent-green)"
    elif def_power < 1.05: def_desc = "Solid 🛡️"; def_color = "var(--accent-blue)"
    else: def_desc = "Leaky ⚠️"; def_color = "var(--accent-red)"

    # --- 2. FORM DOTS ---
    raw_form = stats.get('form', '-----')[-5:]
    form_html = ""
    for char in raw_form:
        dot_class = f"form-{char}" if char in ['W', 'L', 'D'] else ""
        form_html += f"<span class='form-dot {dot_class}'>{char if char != '-' else ''}</span>"

    # --- 3. CLUTCH FACTOR (Die-Hard Stat) ---
    s_w, s_d, s_l = stats.get('vs_stronger', [0,0,0])
    strong_total = s_w + s_d + s_l
    upset_pct = (s_w / strong_total * 100) if strong_total > 0 else 0
    
    if upset_pct > 30: clutch_label = "Giant Killer ⚔️"; clutch_color = "var(--accent-gold)"
    elif stats.get('upsets_major_won', 0) > 0: clutch_label = "Upset Threat 🃏"; clutch_color = "#8b5cf6"
    else: clutch_label = "Standard ⚖️"; clutch_color = "var(--text-light)"

    # --- 4. RENDER HEADER ---
    header = js.document.getElementById("dashboard-header")
    header.innerHTML = f"""
    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                <h1 style="margin:0; font-size:2.4em; font-weight:800; color:var(--text-main); letter-spacing:-1px;">{team.title()}</h1>
                <span class="rank-badge">RANK #{global_rank}</span>
            </div>
            <div style="display:flex; gap:15px; font-size:0.9em; color:var(--text-light); font-weight:500;">
                <span>ELO: <b style="color:var(--text-main);">{int(stats['elo'])}</b></span>
                <span>REGION: <b style="color:var(--text-main);">{confed}</b></span>
                <span>IDENTITY: <b style="color:{clutch_color};">{clutch_label}</b></span>
            </div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:0.7em; font-weight:700; color:var(--text-light); text-transform:uppercase; margin-bottom:8px; letter-spacing:1px;">Recent Form</div>
            <div style="display:flex; gap:4px;">{form_html}</div>
        </div>
    </div>
    """

    # --- 5. RENDER METRICS ---
    js.document.getElementById("dashboard-metrics").innerHTML = f"""
    <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:20px; margin-bottom:25px;">
        <div class="stat-pill">
            <div class="stat-pill-title">Offensive Power</div>
            <div class="stat-pill-value" style="color:var(--accent-blue);">{round(atk_power, 2)}x</div>
            <div style="font-size:0.75em; font-weight:600; color:{atk_color}; margin-top:4px;">{atk_desc}</div>
        </div>
        <div class="stat-pill">
            <div class="stat-pill-title">Defensive Solidity</div>
            <div class="stat-pill-value" style="color:var(--accent-green);">{round(2.0 - def_power, 2)}x</div>
            <div style="font-size:0.75em; font-weight:600; color:{def_color}; margin-top:4px;">{def_desc}</div>
        </div>
        <div class="stat-pill">
            <div class="stat-pill-title">Big Game Record</div>
            <div class="stat-pill-value">{s_w}W - {s_d}D - {s_l}L</div>
            <div style="font-size:0.7em; color:var(--text-light); margin-top:4px;">Record vs. Top Tier Opponents</div>
        </div>
    </div>

    <div class="dashboard-card" style="background:#f8fafc; border-left:4px solid var(--accent-blue); padding:20px; margin-bottom:0;">
        <h4 style="margin:0 0 10px 0; color:var(--sidebar-bg); font-size:0.85em; text-transform:uppercase; letter-spacing:1px;">🔭 AI Scout Report</h4>
        <div style="font-size:1em; line-height:1.6; color:var(--text-main); font-weight:500;">
            {generate_dynamic_report(team, atk_power, def_power, upset_pct, stats)}
        </div>
    </div>

    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:15px; margin-top:20px;">
        <div class="stat-pill" style="padding:10px;">
            <div class="stat-pill-title" style="font-size:0.6em;">Clean Sheets</div>
            <div style="font-weight:800; font-size:1.1em;">{int(stats.get('cs_pct',0))}%</div>
        </div>
        <div class="stat-pill" style="padding:10px;">
            <div class="stat-pill-title" style="font-size:0.6em;">Both Teams Score</div>
            <div style="font-weight:800; font-size:1.1em;">{int(stats.get('btts_pct',0))}%</div>
        </div>
        <div class="stat-pill" style="padding:10px;">
            <div class="stat-pill-title" style="font-size:0.6em;">Late Gls (75'+)</div>
            <div style="font-weight:800; font-size:1.1em; color:var(--accent-gold);">{int(stats.get('late_pct',0))}%</div>
        </div>
        <div class="stat-pill" style="padding:10px;">
            <div class="stat-pill-title" style="font-size:0.6em;">Penalty Rely</div>
            <div style="font-weight:800; font-size:1.1em;">{int(stats.get('pen_pct',0))}%</div>
        </div>
    </div>
    """

    # --- 6. RE-RENDER CHARTS ---
    # Update Charts with clean styling
    render_elo_chart(history, team)
    render_power_chart(atk_index, def_index, team)

def render_elo_chart(history, team):
    js.document.getElementById("dashboard_chart_elo").innerHTML = ""
    fig, ax = plt.subplots(figsize=(6, 3.5))
    fig.patch.set_alpha(0.0) 
    ax.patch.set_alpha(0.0)
    ax.plot(history['dates'], history['elo'], color='#3b82f6', linewidth=3)
    ax.grid(True, linestyle='--', alpha=0.2, color="#cbd5e1")
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(colors='#64748b', labelsize=8)
    fig.tight_layout()
    display(fig, target="dashboard_chart_elo")
    plt.close(fig)

def render_power_chart(atk, dfe, team):
    js.document.getElementById("dashboard_chart_radar").innerHTML = ""
    fig, ax = plt.subplots(figsize=(6, 3.5))
    fig.patch.set_alpha(0.0) 
    ax.patch.set_alpha(0.0)
    
    labels = ['Attack', 'Defense']
    # Defense is inverted so "Higher Bar" always = "Better"
    vals = [atk, 2.0 - dfe]
    
    colors = ['#3b82f6', '#10b981']
    bars = ax.bar(labels, vals, color=colors, width=0.5, alpha=0.9)
    ax.axhline(y=1.0, color='#94a3b8', linestyle='--', linewidth=1, label="Global Avg")
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_ylim(0, max(vals) * 1.3)
    ax.tick_params(colors='#64748b', labelsize=9)
    
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                f'{height:.2f}x', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    fig.tight_layout()
    display(fig, target="dashboard_chart_radar")
    plt.close(fig)

def generate_dynamic_report(team, atk, dfe, upset, stats):
    """Generates a rich, dynamic text-based scouting report based on true analytics."""
    report_paragraphs = []
    
    confed = sim.TEAM_CONFEDS.get(team, 'Unknown')
    style = sim.TEAM_PROFILES.get(team, 'Balanced')
    
    sorted_teams = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)
    rank = next((i+1 for i, t in enumerate(sorted_teams) if t[0] == team), 0)
    
    if rank <= 10: tier_text = "a global powerhouse"
    elif rank <= 30: tier_text = "a formidable contender"
    elif rank <= 60: tier_text = "a competitive dark horse"
    else: tier_text = "an emerging underdog"
    
    # Overview
    report_paragraphs.append(f"<b>Overview:</b> Ranked #{rank} globally, {team.title()} is {tier_text} out of {confed}. They play a <b>{style}</b> style of football.")
    
    # Attack & Defense
    tactical = []
    if atk > 1.5: tactical.append("Offensively, they are elite, generating high-quality chances with ease.")
    elif atk > 1.1: tactical.append("They possess a reliable attack that can break down standard defenses.")
    else: tactical.append("Goal-scoring can be a struggle, often relying on opportunism.")
        
    if dfe < 0.8: tactical.append("At the back, they boast an 'iron wall', excelling at suffocating opponent attacks.")
    elif dfe < 1.05: tactical.append("Their defensive unit is solid, though occasionally vulnerable to world-class forwards.")
    else: tactical.append("Defensively, they are leaky, forcing them to frequently outscore their opponents.")
    report_paragraphs.append("<b>Tactical DNA:</b> " + " ".join(tactical))
    
    # Statistical Quirks
    quirks = []
    if stats.get('fh_pct', 0) > 55: quirks.append("They are notoriously fast starters, looking to blitz opponents early in the first half.")
    if stats.get('late_pct', 0) > 30: quirks.append("Fitness is a key strength; they frequently score decisive goals after the 75th minute.")
    if stats.get('pen_pct', 0) > 20: quirks.append("A significant portion of their goals come from the penalty spot.")
    
    btts = stats.get('btts_pct', 0)
    if btts > 60: quirks.append("Their matches are highly entertaining, with both teams finding the net in over 60% of their fixtures.")
    elif btts < 35: quirks.append("They prefer tight, low-event football, locking games down securely once they take the lead.")

    if quirks: report_paragraphs.append("<b>Statistical Quirks:</b> " + " ".join(quirks))
        
    # Big Game Factor
    s_w, s_d, s_l = stats.get('vs_stronger', [0,0,0])
    strong_games = s_w + s_d + s_l
    win_pct_strong = (s_w / strong_games * 100) if strong_games > 0 else 0
    
    if rank > 20 and win_pct_strong > 25: report_paragraphs.append(f"<b>X-Factor:</b> {team.title()} is a certified 'giant killer' with an impressive track record of upsetting heavyweights.")
    elif rank <= 20 and win_pct_strong > 40: report_paragraphs.append(f"<b>X-Factor:</b> They elevate their game against elite competition, boasting an excellent record against other top nations.")
    elif strong_games > 5 and win_pct_strong < 10: report_paragraphs.append(f"<b>X-Factor:</b> They consistently fall short when stepping up in class against top-tier opposition.")
    else: report_paragraphs.append(f"<b>X-Factor:</b> They are highly consistent, beating the teams they should beat and grinding out predictable results.")

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
    
    fig, ax = plt.subplots(figsize=(11, 8), dpi=100)
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

    # Add quadrant dividing lines
    ax.axhline(mean_ga, color='#cbd5e1', linestyle='--', zorder=1)
    ax.axvline(mean_gf, color='#cbd5e1', linestyle='--', zorder=1)

    # Plot points
    ax.scatter(x_vals, y_vals, s=sizes, c=colors, alpha=0.7, edgecolors='white', linewidth=1, zorder=3)

    # Place text directly onto graph (No hover required)
    for i, label in enumerate(labels):
        ax.text(x_vals[i], y_vals[i] + 0.04, label, fontsize=8, ha='center', va='bottom', color='#334155', fontweight='600', zorder=4, bbox=dict(facecolor='white', alpha=0.5, edgecolor='none', pad=0.5))

    # Background Labels
    ax.text(0.98, 0.98, "Elite Offense / Elite Defense", transform=ax.transAxes, fontsize=14, color='#10b981', alpha=0.4, ha='right', va='top', fontweight='bold', zorder=2)
    ax.text(0.02, 0.02, "Struggling / Leaky", transform=ax.transAxes, fontsize=14, color='#ef4444', alpha=0.4, ha='left', va='bottom', fontweight='bold', zorder=2)
    ax.text(0.98, 0.02, "Entertainers (All Attack, No Def)", transform=ax.transAxes, fontsize=12, color='#f59e0b', alpha=0.4, ha='right', va='bottom', fontweight='bold', zorder=2)
    ax.text(0.02, 0.98, "Defensive / Low Scoring", transform=ax.transAxes, fontsize=12, color='#3b82f6', alpha=0.4, ha='left', va='top', fontweight='bold', zorder=2)

    ax.set_title("Tactical DNA Landscape (Expected Goals For vs. Against)", fontsize=16, fontweight='800', color='#0f172a', pad=20)
    ax.set_xlabel("Attacking Power (Expected Goals For)", fontsize=12, fontweight='bold', color='#64748b')
    ax.set_ylabel("Defensive Solidity (Expected Goals Against)", fontsize=12, fontweight='bold', color='#64748b')
    ax.invert_yaxis() # Defense is inverted so top-right is the best place to be
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#cbd5e1')
    ax.spines['bottom'].set_color('#cbd5e1')
    ax.grid(True, linestyle=':', alpha=0.4, color='#cbd5e1', zorder=0)

    # Custom Legend
    import matplotlib.patches as mpatches
    ax.legend(handles=[mpatches.Patch(color=c, label=conf) for conf, c in confed_colors.items()], loc='upper left', bbox_to_anchor=(1.02, 1), frameon=False, title='Confederation', title_fontproperties={'weight':'bold'})

    plt.tight_layout()
    target_div.innerHTML = ""
    display(fig, target="main-chart-container")
    plt.close(fig)



# =============================================================================
# --- 6. BOOTSTRAP APP ---
# =============================================================================
# Start the engine
asyncio.ensure_future(initialize_app())
