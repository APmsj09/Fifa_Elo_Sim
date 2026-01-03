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
            js.console.warn(f"Warning: Button {btn_id} not found in HTML")

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
    # Note: Checkboxes usually use "change", but "click" works too
    bind_click("hist-filter-wc", handle_history_filter_change)
    bind_click("data-filter-wc", load_data_view)
    
    # 1. Existing Group Popup Logic
    proxy_view_group = create_proxy(open_group_modal)
    EVENT_HANDLERS.append(proxy_view_group)
    js.window.view_group_matches = proxy_view_group

    # 2. NEW: Expose History View for the Dashboard Dropdown
    proxy_view_history = create_proxy(view_team_history)
    EVENT_HANDLERS.append(proxy_view_history)
    js.window.trigger_view_history = proxy_view_history
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
            
            # NOTE: Removed 'onclick' attribute, added 'id'
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

        # --- NEW: Bind Click Listeners via Python ---
        # This is much more reliable than HTML onclick
        for g in group_names:
            # We use a default arg (grp=g) to capture the current value of the loop
            def make_handler(grp):
                return lambda e: open_group_modal(grp)
            
            el = js.document.getElementById(f"group-card-{g}")
            if el:
                # Create proxy and save it to EVENT_HANDLERS to prevent garbage collection
                proxy = create_proxy(make_handler(g))
                EVENT_HANDLERS.append(proxy)
                el.addEventListener("click", proxy)

        # Render Bracket (with Mobile Hint)
        bracket_html = "<div style='font-size:0.8em; color:#7f8c8d; margin-bottom:5px; display:block; text-align:right;'>👉 Swipe to see Final</div>"
        
        for round_data in bracket_data:
            bracket_html += f'<div class="bracket-round"><div class="round-title">{round_data["round"]}</div>'
            for m in round_data['matches']:
                c1 = "winner-text" if m['winner'] == m['t1'] else ""
                c2 = "winner-text" if m['winner'] == m['t2'] else ""
                method_text = m['method'].upper() if m['method'] != 'reg' else ""
                note = f"<div class='match-note' style='font-size:0.7em; color:#7f8c8d; text-align:right;'>{method_text}</div>" if method_text else ""
                
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
# --- 5. HISTORY & ANALYSIS ---
# =============================================================================
def populate_team_dropdown(wc_only=False):
    # Try sidebar first
    select = js.document.getElementById("team-select")
    
    # Fallback to dashboard select
    if select is None:
        select = js.document.getElementById("team-select-dashboard")
    
    if select is None:
        js.console.warn("populate_team_dropdown: no team select found")
        return

    current_val = getattr(select, "value", None)
    select.innerHTML = ""

    sorted_teams = sorted(
        sim.TEAM_STATS.items(),
        key=lambda x: x[1]['elo'],
        reverse=True
    )

    for team, stats in sorted_teams:
        if wc_only and team not in sim.WC_TEAMS:
            continue

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
    # Also refresh data view if that tab is open
    load_data_view(None)

import math 

async def view_team_history(event):
    container = js.document.getElementById("tab-history")
    
    # --- 1. ROBUST INPUT RETRIEVAL ---
    # We must assume ANY element might be missing depending on the current view.
    
    # A. Get Team Name
    val_team = None
    
    # Try Sidebar Dropdown
    el_sidebar = js.document.getElementById("team-select")
    if el_sidebar: 
        val_team = el_sidebar.value
        
    # Try Dashboard Dropdown (if sidebar is hidden/gone)
    if not val_team:
        el_dash = js.document.getElementById("team-select-dashboard")
        if el_dash: 
            val_team = el_dash.value
            
    # Fallback if both fail
    if not val_team:
        if len(sim.TEAM_STATS) > 0:
            val_team = list(sim.TEAM_STATS.keys())[0]
        else:
            container.innerHTML = "Error: No data loaded."
            return

    # B. Get Timeframe (Safety Check Added)
    timeframe = "all"
    el_time = js.document.getElementById("chart-timeframe")
    if el_time:
        timeframe = el_time.value

    # --- 2. RENDER LOADING STATE ---
    container.innerHTML = """
    <div style="text-align:center; padding:50px; color:#7f8c8d;">
        <div style="font-size:2em; margin-bottom:10px;">🔄</div>
        <div>Generating Scout Report for <b>""" + val_team.title() + """</b>...</div>
    </div>
    """
    await asyncio.sleep(0.05)
    
    try:
        team = val_team
        stats = sim.TEAM_STATS.get(team)
        history = sim.TEAM_HISTORY.get(team)
        
        if not stats or not history:
            container.innerHTML = f"Error: No data found for {team}."
            return

        # --- 3. CALCULATE METRICS ---
        sorted_teams = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)
        # Handle case where team might not be in sorted list (rare bug safety)
        try:
            rank = next((i+1 for i, (t, _) in enumerate(sorted_teams) if t == team), "-")
        except StopIteration:
            rank = "-"
        
        form_str = stats.get('form', '-----')
        form_badges = ""
        for char in form_str:
            c = "#2ecc71" if char == 'W' else "#e74c3c" if char == 'L' else "#95a5a6"
            form_badges += f"<span style='background:{c}; color:white; padding:2px 8px; border-radius:4px; margin-right:4px; font-size:0.8em; font-weight:bold;'>{char}</span>"
            
        m_score = stats.get('avg_minute_scored', 48)
        m_concede = stats.get('avg_minute_conceded', 48)
        net_timing = m_score - m_concede
        
        timing_color = "#e74c3c" if net_timing > 5 else "#2980b9" if net_timing < -5 else "#7f8c8d"
        timing_text = "Late Bloomer" if net_timing > 5 else "Fast Starter" if net_timing < -5 else "Balanced"
        
        # --- 4. BUILD OPTIONS FOR DASHBOARD DROPDOWN ---
        options_html = ""
        # Check if the "WC Only" checkbox exists, otherwise default to False
        wc_only = False
        el_cb = js.document.getElementById("hist-filter-wc")
        if el_cb: wc_only = el_cb.checked

        for t, _ in sorted_teams:
            if wc_only and t not in sim.WC_TEAMS: continue
            
            sel = "selected" if t == team else ""
            options_html += f'<option value="{t}" {sel}>{t.title()}</option>'

        # --- 5. DASHBOARD HTML ---
        html = f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; background:white; padding:20px; border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,0.05);">
            <div style="flex:1;">
                <div style="font-size:0.9em; color:#7f8c8d; letter-spacing:1px;">WORLD RANK #{rank}</div>
                <h1 style="margin:5px 0 0 0; font-size:2.5em; text-transform:uppercase;">{team}</h1>
                <div style="margin-top:10px;">{form_badges}</div>
            </div>
            
            <div style="flex:1; text-align:right; display:flex; flex-direction:column; align-items:flex-end; gap:5px;">
                <div style="font-size:3em; font-weight:800; color:#2c3e50; line-height:1;">{int(stats['elo'])}</div>
                <div style="font-size:0.9em; color:#7f8c8d; margin-bottom:10px;">ELO RATING</div>
                
                <select id="team-select-dashboard" onchange="window.trigger_view_history()" style="padding:8px; border-radius:4px; border:1px solid #bdc3c7; background:#f9f9f9; font-size:1em;">
                    {options_html}
                </select>
            </div>
        </div>

        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:15px; margin-bottom:20px;">
            <div style="background:white; padding:15px; border-radius:8px; border-left:4px solid #2ecc71; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                <div style="font-size:0.75em; color:#95a5a6; font-weight:bold;">ATTACK (Goals/Gm)</div>
                <div style="font-size:1.5em; font-weight:bold; color:#2c3e50;">{round(stats['gf_avg'], 2)}</div>
            </div>
            <div style="background:white; padding:15px; border-radius:8px; border-left:4px solid #e74c3c; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                <div style="font-size:0.75em; color:#95a5a6; font-weight:bold;">DEFENSE (Conceded/Gm)</div>
                <div style="font-size:1.5em; font-weight:bold; color:#2c3e50;">{round(stats['ga_avg'], 2)}</div>
            </div>
            <div style="background:white; padding:15px; border-radius:8px; border-left:4px solid {timing_color}; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                <div style="font-size:0.75em; color:#95a5a6; font-weight:bold;">GAME PHASE</div>
                <div style="font-size:1.2em; font-weight:bold; color:{timing_color};">{timing_text}</div>
                <div style="font-size:0.7em; opacity:0.6;">Score {int(m_score)}' / Conc {int(m_concede)}'</div>
            </div>
            <div style="background:white; padding:15px; border-radius:8px; border-left:4px solid #f1c40f; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                <div style="font-size:0.75em; color:#95a5a6; font-weight:bold;">PENALTY RELIANCE</div>
                <div style="font-size:1.5em; font-weight:bold; color:#f39c12;">{int(stats.get('pen_pct',0)*100)}%</div>
            </div>
        </div>

        <div style="display:grid; grid-template-columns: 2fr 1fr; gap:20px;">
            <div style="background:white; padding:20px; border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,0.05);">
                <h4 style="margin:0 0 15px 0; color:#2c3e50; border-bottom:1px solid #eee; padding-bottom:10px;">Performance History</h4>
                <div id="dashboard_chart_elo"></div>
            </div>
            <div style="background:white; padding:20px; border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,0.05);">
                <h4 style="margin:0 0 15px 0; color:#2c3e50; border-bottom:1px solid #eee; padding-bottom:10px;">Strategic DNA</h4>
                <div id="dashboard_chart_radar"></div>
            </div>
        </div>
        """
        
        container.innerHTML = html
        
        # --- 6. RENDER PLOTS ---
        
        # ELO CHART
        dates = history['dates']
        elos = history['elo']
        limit = -100 if timeframe == "10y" else 0
        
        fig1, ax1 = plt.subplots(figsize=(8, 4))
        ax1.plot(dates[limit:], elos[limit:], color='#34495e', linewidth=2)
        ax1.fill_between(dates[limit:], elos[limit:], min(elos[limit:])-20, color='#34495e', alpha=0.1)
        ax1.grid(True, linestyle='--', alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("'%y"))
        display(fig1, target="dashboard_chart_elo")
        plt.close(fig1)

        # RADAR CHART
        avg_gf = sim.AVG_GOALS / 2
        avg_ga = sim.AVG_GOALS / 2
        val_att = min(2.0, max(0.2, stats['gf_avg'] / avg_gf))
        val_def = min(2.0, max(0.2, avg_ga / stats['ga_avg'] if stats['ga_avg'] > 0 else 2.0))
        wins = form_str.count('W')
        val_form = 0.5 + (wins * 0.3)
        val_int = min(2.0, (stats['gf_avg'] + stats['ga_avg']) / (avg_gf + avg_ga))
        val_clutch = 1.0 + (net_timing / 40.0)
        
        categories = ['Attack', 'Defense', 'Form', 'Intensity', 'Clutch']
        values = [val_att, val_def, val_form, val_int, val_clutch]
        values += values[:1]
        
        angles = [n / float(len(categories)) * 2 * math.pi for n in range(len(categories))]
        angles += angles[:1]
        
        fig2, ax2 = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
        ax2.set_theta_offset(math.pi / 2)
        ax2.set_theta_direction(-1)
        ax2.set_rlabel_position(0)
        ax2.plot(angles, values, linewidth=2, linestyle='solid', color='#e67e22')
        ax2.fill(angles, values, '#e67e22', alpha=0.4)
        ax2.set_xticks(angles[:-1])
        ax2.set_xticklabels(categories, size=9, weight='bold')
        ax2.set_yticks([]) # Hide radial numbers
        ax2.set_ylim(0, 2.2)
        
        display(fig2, target="dashboard_chart_radar")
        plt.close(fig2)

    except Exception as e:
        container.innerHTML = f"<div style='color:red; padding:20px;'>Dashboard Error: {e}</div>"
        js.console.error(f"DASHBOARD ERROR: {e}")

async def plot_style_map(event):
    js.document.getElementById("main-chart-container").innerHTML = "Generating 5D Map..."
    await asyncio.sleep(0.01)
    
    fig, ax = plt.subplots(figsize=(9, 6))
    
    wc_only = js.document.getElementById("hist-filter-wc").checked
    sorted_teams = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)
    teams_to_plot = [t for t in sorted_teams if t[0] in sim.WC_TEAMS] if wc_only else sorted_teams[:80]

    x_vals, y_vals, colors, sizes = [], [], [], []
    
    for team, stats in teams_to_plot:
        # X/Y: Offense vs Defense
        gf = stats.get('gf_avg', 0)
        ga = stats.get('ga_avg', 0)
        x_vals.append(gf)
        y_vals.append(ga) 
        
        # Color: Net Timing (Clutch Factor)
        # Formula: Scored Minute - Conceded Minute
        # Positive = Scores Late, Concedes Early (Comeback Kings / 2nd Half)
        # Negative = Scores Early, Concedes Late (Front Runners / 1st Half)
        m_scored = stats.get('avg_minute_scored', 48)
        m_conceded = stats.get('avg_minute_conceded', 48)
        net_timing = m_scored - m_conceded
        colors.append(net_timing)
        
        # Size: Penalty Reliance
        pen = stats.get('pen_pct', 0.05)
        sizes.append(50 + (pen * 1200)) # Scale up for visibility

        # Labels for Elite teams
        should_label = False
        if wc_only:
            if team in ['argentina', 'france', 'brazil', 'usa', 'england', 'germany', 'japan', 'morocco', 'mexico']: should_label = True
        elif stats['elo'] > 1950:
            should_label = True
            
        if should_label:
            ax.annotate(team.title(), (gf, ga), xytext=(5, 5), textcoords='offset points', fontsize=9, fontweight='bold')

    # Scatter Plot with Diverging Color Map (Red vs Blue)
    # vmin/vmax set the range. +/- 15 minutes is a massive difference in football averages.
    scatter = ax.scatter(x_vals, y_vals, c=colors, s=sizes, cmap='coolwarm', alpha=0.8, edgecolors='black', linewidth=0.5, vmin=-15, vmax=15)

    # Colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Net Timing (Blue = 1st Half / Red = 2nd Half)')

    # Quadrant Analysis
    ax.axvline(x=1.5, color='gray', linestyle='--', alpha=0.3)
    ax.axhline(y=1.2, color='gray', linestyle='--', alpha=0.3)
    
    ax.text(2.6, 0.2, "ELITE\n(Dominant)", color='green', fontsize=9, ha='center', weight='bold')
    ax.text(0.5, 2.5, "STRUGGLING\n(Leaky)", color='red', fontsize=9, ha='center', weight='bold')
    
    # Legend for Size
    # Manually adding a text box to explain bubble size
    ax.text(0.02, 0.95, "Size = % Goals from Pens", transform=ax.transAxes, fontsize=8, 
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax.set_title(f"Strategic Profile Map (5D Analysis)", fontsize=14, fontweight='bold')
    ax.set_xlabel("Goals Scored per Game", fontsize=10)
    ax.set_ylabel("Goals Conceded per Game", fontsize=10)
    ax.invert_yaxis() # Defense: Lower is Higher
    ax.grid(True, linestyle='--', alpha=0.2)

    js.document.getElementById("main-chart-container").innerHTML = ""
    display(fig, target="main-chart-container")
    plt.close(fig)

# =============================================================================
# --- 6. BOOTSTRAP APP ---
# =============================================================================
# Start the engine
asyncio.ensure_future(initialize_app())