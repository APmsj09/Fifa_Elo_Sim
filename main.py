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
EVENT_HANDLERS = []

# =============================================================================
# --- STARTUP & INITIALIZATION ---
# =============================================================================
async def initialize_app():
    try:
        js.console.log("Initializing Engine...")
        
        # 1. Initialize Backend
        sim.DATA_DIR = "."
        
        # Make sure to run the confed calculation we discussed
        sim.TEAM_STATS, sim.TEAM_PROFILES, sim.AVG_GOALS = sim.initialize_engine()
        # Trigger the dynamic tier calculation immediately after stats are ready
        sim.calculate_confed_strength() 

        # 2. Setup UI Tabs
        setup_tabs()
        
        # 3. Populate Initial Dropdowns
        populate_team_dropdown(wc_only=False)

        # 4. Hide Loading Screen
        js.document.getElementById("loading-screen").style.display = "none"
        js.document.getElementById("main-dashboard").style.display = "block"
        
        js.console.log("Engine Ready.")

    except Exception as e:
        # If this fails, show error on screen
        js.document.getElementById("loading-screen").innerHTML = f"""
        <div style='color:#e74c3c; text-align:center; padding:20px;'>
            <h1>Startup Error</h1>
            <p>The Python script crashed:</p>
            <pre style='background:black; padding:15px; border-radius:5px;'>{str(e)}</pre>
            <p>Check your console (F12) for more details.</p>
        </div>
        """
        # Log error to console instead of screen
        js.console.error(f"CRITICAL ERROR: {e}")

# =============================================================================
# --- 1. TAB NAVIGATION ---
# =============================================================================
def switch_tab(tab_id):
    # Hide all tabs
    for t in ["tab-single", "tab-bulk", "tab-data", "tab-history"]:
        el = js.document.getElementById(t)
        if el: el.style.display = "none"
        
    # Show selected
    target = js.document.getElementById(tab_id)
    if target: target.style.display = "block"

def setup_tabs():
    global EVENT_HANDLERS # Important: Use the global list

    # Helper to keep references alive
    def bind_click(btn_id, func):
        el = js.document.getElementById(btn_id)
        if el:
            proxy = create_proxy(func)
            EVENT_HANDLERS.append(proxy) # 1. Save it so it doesn't get deleted
            el.addEventListener("click", proxy) # 2. Attach it

    # Navigation Tabs
    bind_click("btn-tab-single", lambda e: switch_tab("tab-single"))
    bind_click("btn-tab-bulk", lambda e: switch_tab("tab-bulk"))
    bind_click("btn-tab-data", lambda e: switch_tab("tab-data"))
    bind_click("btn-tab-history", lambda e: switch_tab("tab-history"))

    # Simulation Buttons
    bind_click("btn-run-single", run_single_sim)
    bind_click("btn-run-bulk", run_bulk_sim)

    # Analysis Buttons
    bind_click("btn-view-history", view_team_history)
    bind_click("btn-view-style-map", plot_style_map) 

    # Filters
    bind_click("hist-filter-wc", handle_history_filter_change)
    bind_click("data-filter-wc", load_data_view)

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
        for grp_name, team_list in groups_data.items():
            groups_html += f"""
            <div class="group-box" onclick="window.view_group_matches('{grp_name}')" title="Click to view matches">
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
                note = f"<div class='match-note'>{m['method'].upper()}</div>" if m['method'] != 'reg' else ""
                
                bracket_html += f"""
                <div class="matchup">
                    <div class="matchup-team {c1}">
                        <span>{m['t1'].title()}</span> <span>{m['g1']}</span>
                    </div>
                    <div class="matchup-team {c2}">
                        <span>{m['t2'].title()}</span> <span>{m['g2']}</span>
                    </div>
                    {note}
                </div>
                """
            bracket_html += "</div>"
            
        js.document.getElementById("bracket-container").innerHTML = bracket_html

        # Reveal UI
        js.document.getElementById("visual-loading").style.display = "none"
        js.document.getElementById("visual-results-container").style.display = "block"

    except Exception as e:
        js.document.getElementById("visual-loading").innerHTML = f"Error: {e}"
        js.console.error(e)

# Match Modal Logic
def open_group_modal(grp_name):
    matches = LAST_SIM_RESULTS.get("group_matches", {}).get(grp_name, [])
    js.document.getElementById("modal-title").innerText = f"Group {grp_name} Results"
    
    html = ""
    for m in matches:
        s1 = "font-weight:bold" if m['g1'] > m['g2'] else ""
        s2 = "font-weight:bold" if m['g2'] > m['g1'] else ""
        html += f"""
        <div class="result-row">
            <span style="flex:1; text-align:right; {s1}">{m['t1'].title()}</span>
            <span class="result-score" style="margin:0 15px;">{m['g1']} - {m['g2']}</span>
            <span style="flex:1; text-align:left; {s2}">{m['t2'].title()}</span>
        </div>
        """
    js.document.getElementById("modal-matches").innerHTML = html
    js.document.getElementById("group-modal").style.display = "block"

js.window.view_group_matches = create_proxy(open_group_modal)
js.document.getElementById("btn-run-single").addEventListener("click", create_proxy(run_single_sim))

# =============================================================================
# --- 3. BULK SIMULATION (MEDALS & OPTIMIZED) ---
# =============================================================================
async def run_bulk_sim(event):
    num_el = js.document.getElementById("bulk-count")
    num = int(num_el.value)
    out_div = js.document.getElementById("bulk-results")
    out_div.innerHTML = f"Running {num} simulations... please wait."
    
    await asyncio.sleep(0.02)
    
    stats = {} # Structure: {Team: {'1st':0, '2nd':0, '3rd':0}}
    
    try:
        for i in range(num):
            # Run Fast Mode
            res = sim.run_simulation(quiet=True, fast_mode=True)
            
            # Helper to increment stats
            def add_stat(team, place):
                if not team: return
                if team not in stats: stats[team] = {'1st':0, '2nd':0, '3rd':0}
                stats[team][place] += 1
            
            add_stat(res["champion"], '1st')
            add_stat(res["runner_up"], '2nd')
            add_stat(res["third_place"], '3rd')
            
            # Update UI every 20 sims
            if i % 20 == 0:
                out_div.innerHTML = f"Running... ({i}/{num})"
                await asyncio.sleep(0.01)
        
        # Cleanup
        gc.collect()

        # Weighted Sort (Gold=3, Silver=2, Bronze=1)
        def get_score(item):
            s = item[1]
            return (s['1st'] * 3) + (s['2nd'] * 2) + (s['3rd'] * 1)
            
        sorted_stats = sorted(stats.items(), key=get_score, reverse=True)
        
        # Build Medal Table
        html = """
        <h3>Medal Table</h3>
        <table style="text-align:center;">
            <thead>
                <tr>
                    <th style="text-align:left;">Team</th>
                    <th style="background:#f1c40f; color:#fff;">🥇 1st</th>
                    <th style="background:#bdc3c7; color:#fff;">🥈 2nd</th>
                    <th style="background:#cd7f32; color:#fff;">🥉 3rd</th>
                    <th>Win %</th>
                </tr>
            </thead>
            <tbody>
        """
        for team, s in sorted_stats:
            perc = round((s['1st'] / num) * 100, 1)
            row_style = "background:#fdfefe;" if perc > 10 else ""
            html += f"""
            <tr style="{row_style}">
                <td style="text-align:left; font-weight:600;">{team.title()}</td>
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

js.document.getElementById("btn-run-bulk").addEventListener("click", create_proxy(run_bulk_sim))

# =============================================================================
# --- 4. DATA VIEW ---
# =============================================================================
def load_data_view(event):
    container = js.document.getElementById("data-table-container")
    if not container: return
    
    # Clear and show loading state
    container.innerHTML = "<div style='padding:20px; text-align:center;'>Loading data...</div>" 
    
    # --- FIX: READ FROM SIDEBAR CHECKBOX ---
    # The element 'data-filter-wc' is now a Button, so we check 'hist-filter-wc' instead.
    sidebar_checkbox = js.document.getElementById("hist-filter-wc")
    wc_only = sidebar_checkbox.checked if sidebar_checkbox else False
    
    # 1. New Headers
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
        
        # 2. Render Form (Colors)
        form_html = ""
        form_raw = stats.get('form', '-----')
        for char in form_raw:
            color = "#ccc"
            if char == "W": color = "#2ecc71"
            elif char == "L": color = "#e74c3c"
            elif char == "D": color = "#f1c40f"
            form_html += f"<span style='color:{color}; font-weight:bold; margin-right:2px;'>{char}</span>"

        # 3. Get New Stats
        gf = round(stats.get('gf_avg', 0), 2)
        ga = round(stats.get('ga_avg', 0), 2)
        
        # Color code the stats for readability
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

# Ensure the button in the Data tab triggers this function
btn_refresh = js.document.getElementById("data-filter-wc")
if btn_refresh:
    # Remove old listeners to be safe (though PyScript handles this mostly)
    # Just add the new click listener
    btn_refresh.addEventListener("click", create_proxy(load_data_view))
    
# Ensure the TAB button triggers it too
js.document.getElementById("btn-tab-data").addEventListener("click", create_proxy(load_data_view))

# =============================================================================
# --- 5. HISTORY & ANALYSIS ---
# =============================================================================

# Dropdown Helper
def populate_team_dropdown(wc_only=False):
    select = js.document.getElementById("team-select")
    current_val = select.value 
    select.innerHTML = "" 
    
    sorted_teams = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)
    
    for team, stats in sorted_teams:
        if wc_only and team not in sim.WC_TEAMS: continue
            
        opt = js.document.createElement("option")
        opt.value = team
        opt.text = team.title()
        select.appendChild(opt)
    
    if current_val:
        for opt in select.options:
            if opt.value == current_val:
                select.value = current_val
                break
    if not select.value and select.options.length > 0:
        select.selectedIndex = 0

def handle_history_filter_change(event):
    is_checked = js.document.getElementById("hist-filter-wc").checked
    populate_team_dropdown(wc_only=is_checked)

# Chart 1: Team Analysis
async def view_team_history(event):
    js.document.getElementById("team-stats-card").innerHTML = "Loading Analysis..."
    await asyncio.sleep(0.01)
    
    try:
        team = js.document.getElementById("team-select").value
        timeframe = js.document.getElementById("chart-timeframe").value
        
        stats = sim.TEAM_STATS.get(team)
        history = sim.TEAM_HISTORY.get(team)
        
        if not stats or not history:
            js.document.getElementById("team-stats-card").innerHTML = "No data found."
            return

        # --- 1. STATS CARD UPDATE ---
        style = sim.TEAM_PROFILES.get(team, "Balanced")
        
        # Get the new stats (default to 0 if missing)
        gf = round(stats.get('gf_avg', 0), 2)
        ga = round(stats.get('ga_avg', 0), 2)
        
        # Color Logic
        gf_color = "#27ae60" if gf > 2.0 else "white"
        ga_color = "#e74c3c" if ga > 1.5 else "white"
        
        card_html = f"""
        <div style='background:#2c3e50; color:white; padding:20px; border-radius:8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h1 style='margin:0; font-size:2.5em;'>{team.title()}</h1>
                <div style="background:#f1c40f; color:#2c3e50; padding:5px 10px; border-radius:4px; font-weight:bold;">
                    {int(stats['elo'])} ELO
                </div>
            </div>
            
            <hr style='border-color:#ffffff30; margin: 15px 0;'>
            
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-bottom:15px;">
                <div style="background:#34495e; padding:10px; border-radius:4px; text-align:center;">
                    <div style="font-size:0.8em; color:#bdc3c7;">GOALS FOR / GM</div>
                    <div style="font-size:1.5em; font-weight:bold; color:{gf_color}">{gf}</div>
                </div>
                <div style="background:#34495e; padding:10px; border-radius:4px; text-align:center;">
                    <div style="font-size:0.8em; color:#bdc3c7;">GOALS AGAINST / GM</div>
                    <div style="font-size:1.5em; font-weight:bold; color:{ga_color}">{ga}</div>
                </div>
            </div>

            <p><strong>Play Style:</strong> {style}</p>
            <p style="font-size:0.9em; opacity:0.8;">Based on last 2 years of performance.</p>
        </div>
        """
        js.document.getElementById("team-stats-card").innerHTML = card_html

        # --- 2. ELO CHART (Unchanged) ---
        dates = history['dates']
        elos = history['elo']
        
        limit = 0
        if timeframe == "10y": limit = -150 
        elif timeframe == "4y": limit = -60 
        
        if limit != 0 and abs(limit) < len(dates):
            plot_dates, plot_elos = dates[limit:], elos[limit:]
        else:
            plot_dates, plot_elos = dates, elos

        fig1, ax1 = plt.subplots(figsize=(8, 4))
        ax1.plot(plot_dates, plot_elos, color='#2980b9', linewidth=2)
        ax1.set_title(f"{team.title()} - Elo Rating History", fontsize=12)
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.fill_between(plot_dates, plot_elos, min(plot_elos)-50, color='#3498db', alpha=0.1)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        js.document.getElementById("main-chart-container").innerHTML = ""
        display(fig1, target="main-chart-container")
        plt.close(fig1)

        # --- 3. PIE CHART (Win/Loss/Draw) ---
        # Since we removed the "Attack/Defense" bar chart, let's show their Form
        form_str = stats.get('form', '')
        w = form_str.count('W')
        d = form_str.count('D')
        l = form_str.count('L')
        
        if len(form_str) > 0:
            fig2, ax2 = plt.subplots(figsize=(4, 3))
            ax2.pie([w, d, l], labels=['W', 'D', 'L'], colors=['#2ecc71', '#f1c40f', '#e74c3c'], autopct='%1.0f%%')
            ax2.set_title("Recent Form (Last 5)")
            plt.tight_layout()
            js.document.getElementById("dist-chart-container").innerHTML = ""
            display(fig2, target="dist-chart-container")
            plt.close(fig2)
        else:
            js.document.getElementById("dist-chart-container").innerHTML = "<p style='text-align:center; padding:20px;'>No recent games.</p>"

    except Exception as e:
        js.document.getElementById("team-stats-card").innerHTML = f"Error: {e}"
        js.console.error(e)

# Chart 2: Global Map
async def plot_style_map(event):
    js.document.getElementById("main-chart-container").innerHTML = "Generating Global Map..."
    await asyncio.sleep(0.01)
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    wc_only = js.document.getElementById("hist-filter-wc").checked
    sorted_teams = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)
    
    teams_to_plot = []
    if wc_only:
        teams_to_plot = [t for t in sorted_teams if t[0] in sim.WC_TEAMS]
    else:
        teams_to_plot = sorted_teams[:100]

    # Collect Data
    x_vals = [] 
    y_vals = [] 
    colors = []
    sizes = []
    
    for team, stats in teams_to_plot:
        # X Axis: Goals Scored (GF), Y Axis: Goals Allowed (GA)
        gf = stats.get('gf_avg', 0)
        ga = stats.get('ga_avg', 0)
        
        x_vals.append(gf)
        y_vals.append(ga) 
        
        # Color based on Elo
        elo = stats['elo']
        if elo > 2000: c = '#f1c40f' # Gold
        elif elo > 1800: c = '#2ecc71' # Green
        elif elo > 1600: c = '#3498db' # Blue
        else: c = '#95a5a6' # Grey
        colors.append(c)
        sizes.append(elo / 15) # Size based on rating

        # Labels for top teams
        should_label = False
        if wc_only:
            if team in ['argentina', 'france', 'brazil', 'usa', 'england', 'germany', 'japan', 'morocco']:
                should_label = True
        elif elo > 1950:
            should_label = True
            
        if should_label:
            ax.annotate(team.title(), (gf, ga), xytext=(5, 5), textcoords='offset points', fontsize=9)

    ax.scatter(x_vals, y_vals, c=colors, s=sizes, alpha=0.7, edgecolors='black', linewidth=0.5)

    # Add quadrant lines (using approx averages)
    ax.axvline(x=1.5, color='gray', linestyle='--', alpha=0.3) # Avg Goals Scored
    ax.axhline(y=1.2, color='gray', linestyle='--', alpha=0.3) # Avg Goals Conceded

    # --- QUADRANT LABELS ---
    # ELITE: High Scoring (Right), Low Conceding (Top - due to inverted axis)
    ax.text(2.5, 0.2, "ELITE\n(High Score, Low Concede)", color='green', fontsize=10, ha='center')
    
    # STRUGGLING: Low Scoring (Left), High Conceding (Bottom)
    ax.text(0.5, 2.5, "STRUGGLING\n(Low Score, High Concede)", color='red', fontsize=10, ha='center')
    
    # CHAOTIC: High Scoring (Right), High Conceding (Bottom)
    ax.text(2.5, 2.5, "CHAOTIC\n(High Score, High Concede)", color='orange', fontsize=8, ha='center')
    
    # DEFENSIVE: Low Scoring (Left), Low Conceding (Top)
    ax.text(0.5, 0.2, "DEFENSIVE\n(Low Score, Low Concede)", color='blue', fontsize=8, ha='center')

    ax.set_title(f"Performance Map: Offense vs Defense", fontsize=14, fontweight='bold')
    ax.set_xlabel("Goals Scored per Game (Avg)", fontsize=10)
    ax.set_ylabel("Goals Conceded per Game (Avg)", fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.2)
    
    # We invert Y axis because for Defense, a LOWER number is better.
    # So the "Top" of the graph will be 0.0 goals allowed.
    ax.invert_yaxis()

    js.document.getElementById("main-chart-container").innerHTML = ""
    display(fig, target="main-chart-container")
    plt.close(fig)

    
# =============================================================================
# --- 6. BOOTSTRAP APP ---
# =============================================================================
# Run initialization
asyncio.ensure_future(initialize_app())