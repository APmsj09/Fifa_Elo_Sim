import js
import asyncio
import gc
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import simulation_engine as sim
from pyodide.ffi import create_proxy
from pyscript import display

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
    for t in ["tab-single", "tab-bulk", "tab-data", "tab-history"]:
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

        # Render Bracket (with Mobile Hint)
        bracket_html = "<div style='font-size:0.8em; color:#7f8c8d; margin-bottom:5px; display:block; text-align:right;'>👉 Swipe to see Final</div>"
        
        for round_data in bracket_data:
            bracket_html += f'<div class="bracket-round"><div class="round-title">{round_data["round"]}</div>'
            for m in round_data['matches']:
            c1 = "winner-text" if m['winner'] == m['t1'] else ""
            c2 = "winner-text" if m['winner'] == m['t2'] else ""
    
            # IMPROVED SCORE DISPLAY
            score_display = ""
            if m['method'] == 'pks':
                # If penalties, show score like "1 (4) - 1 (3)" or just "1 - 1 (P)"
                # Since we don't simulate specific PK scores, let's just mark the winner
                g1_txt = f"{m['g1']} (P)" if m['winner'] == m['t1'] else str(m['g1'])
                g2_txt = f"{m['g2']} (P)" if m['winner'] == m['t2'] else str(m['g2'])
            elif m['method'] == 'aet':
                 g1_txt = f"{m['g1']} (AET)"
                g2_txt = f"{m['g2']} (AET)"
            else:
                g1_txt = str(m['g1'])
                g2_txt = str(m['g2'])

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
    num = int(num_el.value)
    out_div = js.document.getElementById("bulk-results")
    out_div.innerHTML = f"Running {num} simulations... please wait."
    
    await asyncio.sleep(0.02)
    
    stats = {} 
    
    try:
        for i in range(num):
            res = sim.run_simulation(quiet=True, fast_mode=True)
            
            def add_stat(team, place):
                if not team: return
                if team not in stats: stats[team] = {'1st':0, '2nd':0, '3rd':0}
                stats[team][place] += 1
            
            add_stat(res["champion"], '1st')
            add_stat(res["runner_up"], '2nd')
            add_stat(res["third_place"], '3rd')
            
            if i % 20 == 0:
                out_div.innerHTML = f"Running... ({i}/{num})"
                await asyncio.sleep(0.001)
        
        gc.collect()

        def get_score(item):
            s = item[1]
            return (s['1st'] * 3) + (s['2nd'] * 2) + (s['3rd'] * 1)
            
        sorted_stats = sorted(stats.items(), key=get_score, reverse=True)
        
        html = """
        <h3>Medal Table</h3>
        <table style="text-align:center; width:100%; border-collapse:collapse;">
            <thead>
                <tr style="background:#34495e; color:white;">
                    <th style="text-align:left; padding:8px;">Team</th>
                    <th style="background:#f1c40f; color:#2c3e50;">🥇 1st</th>
                    <th style="background:#bdc3c7; color:#2c3e50;">🥈 2nd</th>
                    <th style="background:#d35400; color:white;">🥉 3rd</th>
                    <th>Win %</th>
                </tr>
            </thead>
            <tbody>
        """
        for team, s in sorted_stats:
            perc = round((s['1st'] / num) * 100, 1)
            row_style = "background:#eafaf1;" if perc > 10 else "border-bottom:1px solid #ddd;"
            html += f"""
            <tr style="{row_style}">
                <td style="text-align:left; font-weight:600; padding:8px;">{team.title()}</td>
                <td>{s['1st']}</td>
                <td>{s['2nd']}</td>
                <td>{s['3rd']}</td>
                <td>{perc}%</td>
            </tr>
            """
        html += "</tbody></table>"
        out_div.innerHTML = html
        
    except Exception as e:
        out_div.innerHTML = f"Error in Bulk Sim: {e}"

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
    
    container.innerHTML = "<div style='padding:20px; text-align:center;'>Loading data...</div>" 
    
    sidebar_checkbox = js.document.getElementById("hist-filter-wc")
    wc_only = sidebar_checkbox.checked if sidebar_checkbox else False
    
    html = """
    <table class="data-table">
        <thead>
            <tr>
                <th>Rank</th>
                <th>Team</th>
                <th>Rating</th>
                <th>Form</th>
                <th title="Goals Scored per Game (Last 2 Years)">GF / Gm</th>
                <th title="Goals Allowed per Game (Last 2 Years)">GA / Gm</th>
                <th>Style</th>
            </tr>
        </thead>
        <tbody>
    """
    
    sorted_teams = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)
    
    rank_counter = 0
    for team, stats in sorted_teams:
        if wc_only and team not in sim.WC_TEAMS: continue
        
        rank_counter += 1
        style = sim.TEAM_PROFILES.get(team, "Balanced")
        
        form_html = ""
        form_raw = stats.get('form', '-----')
        for char in form_raw:
            color = "#ccc"
            if char == "W": color = "#2ecc71"
            elif char == "L": color = "#e74c3c"
            elif char == "D": color = "#f1c40f"
            form_html += f"<span style='color:{color}; font-weight:bold; margin-right:2px;'>{char}</span>"

        gf = round(stats.get('gf_avg', 0), 2)
        ga = round(stats.get('ga_avg', 0), 2)
        
        gf_color = "green" if gf > 2.0 else "#555"
        ga_color = "red" if ga > 1.5 else "#555"

        html += f"""
        <tr>
            <td>#{rank_counter}</td>
            <td style='font-weight:600'>{team.title()}</td>
            <td>{int(stats['elo'])}</td>
            <td style='letter-spacing:1px; font-size:0.9em'>{form_html}</td>
            <td style='color:{gf_color}; font-weight:bold;'>{gf}</td>
            <td style='color:{ga_color};'>{ga}</td>
            <td>{style}</td>
        </tr>
        """
    
    html += "</tbody></table>"
    container.innerHTML = html

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
    # Get the select element
    select = js.document.getElementById("team-select-dashboard")
    
    # Safety Check: If select isn't ready, try populating it
    if not select or not select.value:
        populate_team_dropdown(target_id="team-select-dashboard")
        select = js.document.getElementById("team-select-dashboard")
    
    if not select or not select.value:
        return # Still nothing? Abort.

    team = select.value
    stats = sim.TEAM_STATS.get(team)
    history = sim.TEAM_HISTORY.get(team)

    if not stats or not history:
        return

    # --- HEADER ---
    header = js.document.getElementById("dashboard-header")
    header.innerHTML = f"""
    <div style="margin-bottom:20px;">
        <h1 style="margin:0; font-size:2.5em; color:#2c3e50;">{team.title()}</h1>
        <div style="color:#7f8c8d; font-weight:bold;">Current FIFA Elo: {int(stats['elo'])}</div>
    </div>
    """

    # --- METRICS ---
    # Using flexbox for better responsive behavior than grid
    js.document.getElementById("dashboard-metrics").innerHTML = f"""
    <div style="display:flex; gap:15px; margin-bottom:25px; flex-wrap:wrap;">
        <div style="background:#3498db; color:white; padding:15px; borderRadius:8px; flex:1; min-width:100px; text-align:center;">
            <div style="font-size:0.8em; opacity:0.8;">ATTACK</div>
            <div style="font-size:1.5em; font-weight:bold;">{round(stats['gf_avg'],2)}</div>
        </div>
        <div style="background:#e74c3c; color:white; padding:15px; borderRadius:8px; flex:1; min-width:100px; text-align:center;">
            <div style="font-size:0.8em; opacity:0.8;">DEFENSE</div>
            <div style="font-size:1.5em; font-weight:bold;">{round(stats['ga_avg'],2)}</div>
        </div>
        <div style="background:#f1c40f; color:#2c3e50; padding:15px; borderRadius:8px; flex:1; min-width:100px; text-align:center;">
            <div style="font-size:0.8em; opacity:0.8;">FORM</div>
            <div style="font-size:1.5em; font-weight:bold;">{stats.get('form','-----')}</div>
        </div>
        <div style="background:#9b59b6; color:white; padding:15px; borderRadius:8px; flex:1; min-width:100px; text-align:center;">
            <div style="font-size:0.8em; opacity:0.8;">STYLE</div>
            <div style="font-size:1.2em; font-weight:bold;">{sim.TEAM_PROFILES.get(team, 'Balanced')}</div>
        </div>
    </div>
    """

    # --- ELO CHART ---
    js.document.getElementById("dashboard_chart_elo").innerHTML = ""
    fig, ax = plt.subplots(figsize=(6,4))
    ax.plot(history['dates'], history['elo'], color='#2980b9', linewidth=2)
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.set_title("Rating History", fontsize=10)
    fig.tight_layout()
    display(fig, target="dashboard_chart_elo")
    plt.close(fig)

    # --- RADAR / STYLE CHART ---
    # Simplified visual representation of Offense vs Defense
    js.document.getElementById("dashboard_chart_radar").innerHTML = ""
    fig2, ax2 = plt.subplots(figsize=(4,4))
    
    # Simple Bar Comparison
    metrics = ['Attack', 'Defense']
    # Normalize roughly (2.5 is high for goals)
    vals = [min(stats['gf_avg'], 3.0), min(stats['ga_avg'], 3.0)]
    colors = ['#3498db', '#e74c3c']
    
    ax2.bar(metrics, vals, color=colors)
    ax2.set_ylim(0, 3.5)
    ax2.set_title("Team Balance", fontsize=10)
    
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

    x_vals, y_vals, colors, sizes = [], [], [], []
    for team, stats in teams_to_plot:
        gf = stats.get('gf_avg', 0)
        ga = stats.get('ga_avg', 0)
        x_vals.append(gf)
        y_vals.append(ga) 
        # Color: Net Timing
        m_scored = stats.get('avg_minute_scored', 48)
        m_conceded = stats.get('avg_minute_conceded', 48)
        colors.append(m_scored - m_conceded)
        # Size: Elo strength
        sizes.append(stats['elo'] / 10) 

        # Label elites
        if stats['elo'] > 1900 or (wc_only and stats['elo'] > 1700):
            ax.annotate(team.title(), (gf, ga), xytext=(5, 5), textcoords='offset points', fontsize=8)

    scatter = ax.scatter(x_vals, y_vals, c=colors, s=sizes, cmap='coolwarm', alpha=0.7, edgecolors='black', vmin=-15, vmax=15)
    
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