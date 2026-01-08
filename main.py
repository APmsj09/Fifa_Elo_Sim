import js
import asyncio
import gc
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import simulation_engine as sim
from pyodide.ffi import create_proxy
from pyscript import display
import mplcursors

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
    # 1. Get Elements
    num_el = js.document.getElementById("bulk-count")
    out_div = js.document.getElementById("bulk-results")
    
    # 2. Safety Check & Init
    if not num_el or not out_div: return
    num = int(num_el.value)
    
    # 3. Initialize Data Structures
    team_stats = {}   
    group_mapping = {} 
    
    # 4. Helper Function to init team stats if missing
    def init_team(t):
        if t not in team_stats:
            team_stats[t] = {'grp_1st': 0, 'r32': 0, 'r16':0, 'qf':0, 'sf': 0, 'final': 0, 'win': 0}

    # 5. UI Loading State
    out_div.innerHTML = f"""
    <div style='text-align:center; padding:40px; color:#34495e;'>
        <h3 style='margin:0;'>🎲 Simulating {num} Tournaments...</h3>
        <p style='margin:10px 0 0 0; color:#7f8c8d;'>Compiling rigorous statistics for every team.</p>
        <div style='margin-top:20px; width:100%; height:4px; background:#eee; border-radius:2px; overflow:hidden;'>
            <div id='bulk-progress' style='width:0%; height:100%; background:#3498db; transition:width 0.1s;'></div>
        </div>
    </div>
    """
    await asyncio.sleep(0.05)

    try:
        # 6. Main Simulation Loop
        for i in range(num):
            res = sim.run_simulation(fast_mode=False, quiet=True)
            
            # --- A. GROUP ANALYSIS ---
            
            # Create a set of teams that made the Round of 32 (First Knockout Round)
            r32_roster = set()
            if len(res['bracket_data']) > 0:
                # The first round in bracket_data is always the first KO round
                for match in res['bracket_data'][0]['matches']:
                    r32_roster.add(match['t1'])
                    r32_roster.add(match['t2'])

            for grp, table in res['groups_data'].items():
                if grp not in group_mapping: group_mapping[grp] = {}
                
                # Track First Place
                first_team = table[0]['team']
                init_team(first_team)
                team_stats[first_team]['grp_1st'] += 1
                
                # Track Advancement
                for row in table:
                    t = row['team']
                    init_team(t)
                    group_mapping[grp][t] = True 
                    
                    if t in r32_roster:
                        team_stats[t]['r32'] += 1

            # --- B. KNOCKOUT ANALYSIS (UPDATED) ---
            
            champ = res['champion']
            init_team(champ)
            team_stats[champ]['win'] += 1
            
            bracket = res['bracket_data']
            if bracket:
                rounds_count = len(bracket)
                
                # Helper to process a specific round by index (from end)
                # index -1 = Final, -2 = Semis, -3 = QF, -4 = R16
                def process_round(idx, stat_key):
                    if rounds_count >= abs(idx):
                        for m in bracket[idx]['matches']:
                            init_team(m['t1']); team_stats[m['t1']][stat_key] += 1
                            init_team(m['t2']); team_stats[m['t2']][stat_key] += 1

                # 1. Finals (Last Round)
                process_round(-1, 'final')
                
                # 2. Semi-Finals (2nd to Last)
                process_round(-2, 'sf')
                
                # 3. Quarter-Finals (3rd to Last)
                process_round(-3, 'qf')

                # 4. Round of 16 (4th to Last)
                process_round(-4, 'r16')

            
            # Update Progress Bar
            if i % 20 == 0:
                pct = (i / num) * 100
                prog_bar = js.document.getElementById("bulk-progress")
                if prog_bar: prog_bar.style.width = f"{pct}%"
                await asyncio.sleep(0.001)

        # Finalize Progress
        prog_bar = js.document.getElementById("bulk-progress")
        if prog_bar: prog_bar.style.width = "100%"
        await asyncio.sleep(0.2)

        # --- 7. GENERATE OUTPUT HTML ---
        html = ""

        # SECTION 1: GROUP STANDINGS
        html += "<h2 style='color:#2c3e50; border-bottom:2px solid #ddd; padding-bottom:10px;'>📋 PROJECTED GROUP STANDINGS</h2>"
        html += "<div style='display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:20px;'>"
        
        # Sort groups (A, B, C...)
        sorted_groups = sorted(group_mapping.keys())

        for grp in sorted_groups:
            teams = list(group_mapping[grp].keys())
            html += f"""
            <div style="background:white; padding:15px; border-radius:8px; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                <h3 style="margin:0 0 10px 0; color:#2980b9;">🔹 Group {grp}</h3>
                <table style="width:100%; border-collapse:collapse; font-size:0.85em;">
                    <tr style="border-bottom:1px solid #eee; text-align:left; color:#7f8c8d;">
                        <th style="padding:5px;">Team</th>
                        <th style="padding:5px; text-align:right;">Grp Win %</th>
                        <th style="padding:5px; text-align:right;">Advance %</th>
                    </tr>
            """
            grp_data = []
            for t in teams:
                s = team_stats.get(t, {'grp_1st':0, 'r32':0})
                grp_data.append({
                    'name': t,
                    'win_pct': (s['grp_1st'] / num) * 100,
                    'adv_pct': (s['r32'] / num) * 100
                })
            # Sort by Advance %
            grp_data.sort(key=lambda x: x['adv_pct'], reverse=True)
            for row in grp_data:
                bg = ""
                if row['adv_pct'] > 85: bg = "background:#eafaf1;"
                elif row['adv_pct'] < 15: bg = "color:#aaa;"
                html += f"""
                <tr style="border-bottom:1px solid #f9f9f9; {bg}">
                    <td style="padding:6px; font-weight:600;">{row['name'].title()}</td>
                    <td style="padding:6px; text-align:right;">{row['win_pct']:.1f}%</td>
                    <td style="padding:6px; text-align:right; font-weight:bold;">{row['adv_pct']:.1f}%</td>
                </tr>
                """
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
    container = js.document.getElementById("tab-history")

    container.innerHTML = """
    <div id="dashboard-header"></div>

    <div id="dashboard-metrics"></div>

    <div style="display:grid; grid-template-columns: 2fr 1fr; gap:20px;">
        <div style="background:white; padding:20px; border-radius:10px;">
            <h4>Performance History</h4>
            <div id="dashboard_chart_elo"></div>
        </div>
        <div style="background:white; padding:20px; border-radius:10px;">
            <h4>Strategic DNA</h4>
            <div id="dashboard_chart_radar"></div>
        </div>
    </div>
    """

    populate_team_dropdown()

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
    # 1. GET TEAM SELECTION
    select = js.document.getElementById("team-select-dashboard")
    if not select or not select.value:
        populate_team_dropdown(target_id="team-select-dashboard")
        select = js.document.getElementById("team-select-dashboard")
    if not select or not select.value: return 

    team = select.value
    stats = sim.TEAM_STATS.get(team)
    history = sim.TEAM_HISTORY.get(team)
    if not stats or not history: return

    # --- 1. GET THE SOS-ADJUSTED METRICS ---
    atk_index = stats.get('off', 1.0)
    def_index = stats.get('def', 1.0)

    std_attack = stats.get('adj_gf', sim.AVG_GOALS)
    std_defense = stats.get('adj_ga', sim.AVG_GOALS)
    global_avg = sim.AVG_GOALS if sim.AVG_GOALS > 0 else 1.25

    rel_att_strength = atk_index * 100
    rel_def_strength = def_index * 100

    # --- 2. PREPARE SCOUT REPORT ---
    adjusted_stats = stats.copy()
    adjusted_stats['gf_avg'] = std_attack
    adjusted_stats['ga_avg'] = std_defense
    scout_report = generate_scout_report(adjusted_stats)

    # =========================================================
    # 2. RENDER HEADER
    # =========================================================
    
    header = js.document.getElementById("dashboard-header")
    header.innerHTML = f"""
    <div style="margin-bottom:20px; border-bottom:1px solid #eee; padding-bottom:10px;">
        <h1 style="margin:0; font-size:2.2em; color:#2c3e50;">{team.title()}</h1>
        <div style="color:#7f8c8d; font-weight:bold; display:flex; justify-content:space-between; align-items:center;">
            <span>FIFA Elo: <span style="color:#2c3e50;">{int(stats['elo'])}</span></span>
            <span style="font-size:0.8em; color:#2980b9; background:#eaf2f8; padding:4px 8px; border-radius:4px;">
                SOS Standardized Ratings
            </span>
        </div>
    </div>
    """

    js.document.getElementById("dashboard-metrics").innerHTML = f"""
    <div style="display:grid; grid-template-columns: 2fr 1fr; gap:20px; margin-bottom:20px;">
        <div>
            <div style="display:flex; gap:10px; margin-bottom:15px;">
                <div style="background:#3498db; color:white; padding:12px; border-radius:8px; flex:1; display:flex; flex-direction:column; justify-content:center; text-align:center;">
                    <div style="font-size:0.75em; opacity:0.9; margin-bottom:5px;">OFFENSIVE RATING</div>
                    
                    <div style="margin-bottom:5px;">
                        <span style="font-size:1.9em; font-weight:bold;">{round(std_attack, 2)}</span>
                        <span style="font-size:0.7em; opacity:0.8;">Goals/Gm</span>
                    </div>

                    <div style="background:rgba(0,0,0,0.2); padding:4px; border-radius:4px; font-size:0.8em;">
                        Index: <strong>{round(atk_index, 2)}</strong> <span style="opacity:0.8;">({int(rel_att_strength)}% Avg)</span>
                    </div>
                </div>

                <div style="background:#e74c3c; color:white; padding:12px; border-radius:8px; flex:1; display:flex; flex-direction:column; justify-content:center; text-align:center;">
                    <div style="font-size:0.75em; opacity:0.9; margin-bottom:5px;">DEFENSIVE RATING</div>
                    
                    <div style="margin-bottom:5px;">
                        <span style="font-size:1.9em; font-weight:bold;">{round(std_defense, 2)}</span>
                        <span style="font-size:0.7em; opacity:0.8;">Conc/Gm</span>
                    </div>

                    <div style="background:rgba(0,0,0,0.2); padding:4px; border-radius:4px; font-size:0.8em;">
                        Index: <strong>{round(def_index, 2)}</strong> <span style="opacity:0.8;">({int(rel_def_strength)}% Avg)</span>
                    </div>
                </div>

                <div style="background:#f1c40f; color:#2c3e50; padding:15px; borderRadius:8px; flex:1; text-align:center;">
                    <div style="font-size:0.75em; opacity:0.9;">CLEAN SHEETS</div>
                    <div style="font-size:1.8em; font-weight:bold;">{int(stats.get('cs_pct',0))}%</div>
                     <div style="font-size:0.7em; opacity:0.7; margin-top:8px;">Frequency</div>
                </div>
            </div>
            <h4 style="margin:0 0 10px 0; color:#7f8c8d; border-bottom:1px solid #eee; padding-bottom:5px;">🧬 Tactical DNA</h4>
            <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:10px;">
                <div style="background:#f8f9fa; border:1px solid #eee; padding:10px; border-radius:8px; text-align:center;">
                    <div style="font-size:1.1em; font-weight:bold; color:#2c3e50;">{int(stats.get('fh_pct',0))}%</div>
                    <div style="font-size:0.7em; color:#7f8c8d;">1st Half</div>
                </div>
                <div style="background:#f8f9fa; border:1px solid #eee; padding:10px; border-radius:8px; text-align:center;">
                    <div style="font-size:1.1em; font-weight:bold; color:#e67e22;">{int(stats.get('late_pct',0))}%</div>
                    <div style="font-size:0.7em; color:#7f8c8d;">Late (75'+)</div>
                </div>
                <div style="background:#f8f9fa; border:1px solid #eee; padding:10px; border-radius:8px; text-align:center;">
                    <div style="font-size:1.1em; font-weight:bold; color:#2c3e50;">{int(stats.get('pen_pct',0))}%</div>
                    <div style="font-size:0.7em; color:#7f8c8d;">Pens</div>
                </div>
                <div style="background:#f8f9fa; border:1px solid #eee; padding:10px; border-radius:8px; text-align:center;">
                    <div style="font-size:1.1em; font-weight:bold; color:#e74c3c;">{int(stats.get('btts_pct',0))}%</div>
                    <div style="font-size:0.7em; color:#7f8c8d;">BTTS</div>
                </div>
            </div>
        </div>
        <div style="background:#2c3e50; color:white; padding:20px; border-radius:10px; display:flex; flex-direction:column; justify-content:center;">
            <h4 style="margin-top:0; color:#f1c40f; border-bottom:1px solid #555; padding-bottom:10px;">📋 Scouting Report</h4>
            <div style="font-size:0.9em; line-height:1.6;">{scout_report}</div>
        </div>
    </div>
    """

    # --- 4. RENDER ELO HISTORY ---
    js.document.getElementById("dashboard_chart_elo").innerHTML = ""
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.plot(history['dates'], history['elo'], color='#2980b9', linewidth=2, label=team.title())
    ax.axhline(y=1800, color='gray', linestyle='--', linewidth=1, alpha=0.7, label='Elite Tier')
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.set_title("Rating History", fontsize=10, fontweight='bold')
    ax.legend(loc='upper left', fontsize='small')
    fig.tight_layout()
    display(fig, target="dashboard_chart_elo")
    plt.close(fig)

    # --- 5. RENDER RADAR-STYLE BAR CHART ---
    js.document.getElementById("dashboard_chart_radar").innerHTML = ""
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    metrics = ['Attack', 'Defense']
    team_vals = [atk_index, def_index]
    global_avgs = [1.0, 1.0]  # normalized SOS avg = 1.0

    bars_team = ax2.bar([0,1], team_vals, width=0.35, color=['#3498db','#e74c3c'], label=team.title())
    bars_avg  = ax2.bar([0,1], global_avgs, width=0.35, color='#95a5a6', alpha=0.6, label='Global Avg', align='edge')

    ax2.set_xticks([0,1])
    ax2.set_xticklabels(metrics)
    ax2.set_ylabel("SOS-Adjusted Strength")
    ax2.set_ylim(0, max(team_vals + global_avgs)*1.2)
    ax2.set_title(f"{team.title()} vs Global Avg", fontsize=12)
    ax2.bar_label(bars_team, fmt='%.2f', padding=3)
    ax2.bar_label(bars_avg, fmt='%.2f', padding=3)
    ax2.grid(axis='y', linestyle='--', alpha=0.3)
    ax2.legend(fontsize='small')
    fig2.tight_layout()
    display(fig2, target="dashboard_chart_radar")
    plt.close(fig2)

async def refresh_team_analysis(event=None):
    update_dashboard_data()

async def plot_style_map(event):
    global DASHBOARD_BUILT
    # Ensure shell exists (so the container exists)
    if not DASHBOARD_BUILT:
        build_dashboard_shell()
        DASHBOARD_BUILT = True
        
    # Switch Tabs manually if this was triggered from Sidebar
    js.document.getElementById("view-profile").style.display = "none"
    js.document.getElementById("view-style-map").style.display = "block"

    target_div = js.document.getElementById("main-chart-container")
    target_div.innerHTML = "<div style='text-align:center; padding:50px;'>Generating 5D Style Map...</div>"

    await asyncio.sleep(0.05)
    
    fig, ax = plt.subplots(figsize=(9, 6))
    wc_only = js.document.getElementById("hist-filter-wc").checked
    sorted_teams = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)
    teams_to_plot = [t for t in sorted_teams if t[0] in sim.WC_TEAMS] if wc_only else sorted_teams[:60]

    fig, ax = plt.subplots(figsize=(9,6))
    sorted_teams = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)[:60]

    x_vals, y_vals, colors, sizes, labels = [], [], [], [], []
    for team, stats in sorted_teams:
        gf = stats.get('gf_avg', 0)
        ga = stats.get('ga_avg', 0)
        x_vals.append(gf)
        y_vals.append(ga)
        m_scored = stats.get('avg_minute_scored', 48)
        m_conceded = stats.get('avg_minute_conceded', 48)
        colors.append(m_scored - m_conceded)
        sizes.append(stats['elo'] / 10)
        labels.append(f"{team.title()}\nAttack: {gf:.2f}\nDefense: {ga:.2f}\nElo: {int(stats['elo'])}")

    scatter = ax.scatter(x_vals, y_vals, c=colors, s=sizes, cmap='coolwarm', alpha=0.7, edgecolors='black', vmin=-15, vmax=15)

    # Shaded quadrants
    ax.axhspan(0, 1.0, xmin=0.5, xmax=1, facecolor='green', alpha=0.05)
    ax.axhspan(1.0, 3.0, xmin=0, xmax=0.5, facecolor='red', alpha=0.05)

    # Hover tooltips
    cursor = mplcursors.cursor(scatter, hover=True)
    @cursor.connect("add")
    def on_hover(sel):
        sel.annotation.set_text(labels[sel.index])
        sel.annotation.get_bbox_patch().set(fc="white", alpha=0.9)

    ax.set_title("Strategic Style Map", fontsize=14, fontweight='bold')
    ax.set_xlabel("Goals Scored per Game")
    ax.set_ylabel("Goals Conceded per Game")
    ax.invert_yaxis() # Defense: Lower is better (so high up)
    ax.grid(True, linestyle='--', alpha=0.2)
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Game Control (Blue=Early Lead, Red=Late Comeback)')

    target_div.innerHTML = ""
    display(fig, target="main-chart-container")
    plt.close(fig)



# =============================================================================
# --- 6. BOOTSTRAP APP ---
# =============================================================================
# Start the engine
asyncio.ensure_future(initialize_app())