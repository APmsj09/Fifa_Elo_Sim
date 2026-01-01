import js
import asyncio
import gc
import simulation_engine as sim
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pyodide.ffi import create_proxy

# 1. INITIALIZE
print("Initializing Engine...")
sim.DATA_DIR = "."
sim.TEAM_STATS, sim.TEAM_PROFILES, sim.AVG_GOALS = sim.initialize_engine()

# Remove loading screen
js.document.getElementById("loading-screen").style.display = "none"
js.document.getElementById("main-dashboard").style.display = "block"
LAST_SIM_RESULTS = {}

# =============================================================================
# --- TAB NAVIGATION & DROPDOWN MANAGEMENT ---
# =============================================================================

# Function to populate the dropdown
def populate_team_dropdown(wc_only=False):
    select = js.document.getElementById("team-select")
    current_val = select.value 
    select.innerHTML = "" 
    
    sorted_teams = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)
    
    for team, stats in sorted_teams:
        # NEW FILTER LOGIC:
        if wc_only and team not in sim.WC_TEAMS:
            continue
            
        opt = js.document.createElement("option")
        opt.value = team
        opt.text = team.title()
        select.appendChild(opt)
    
    if current_val:
        # Verify the previous selection is still valid in the new list
        for opt in select.options:
            if opt.value == current_val:
                select.value = current_val
                break
    
    if not select.value and select.options.length > 0:
        select.selectedIndex = 0

# =============================================================================
# --- 1. SINGLE SIMULATION (ASYNC) ---
# =============================================================================
async def run_single_sim(event): # <--- CHANGED TO ASYNC
    global LAST_SIM_RESULTS
    
    # 1. UI Prep (Show Loading)
    js.document.getElementById("visual-loading").style.display = "block"
    js.document.getElementById("visual-results-container").style.display = "none"
    
    # 2. YIELD CONTROL (Critical!)
    # This pauses Python for 10ms, allowing the Browser to actually PAINT the loading screen.
    await asyncio.sleep(0.01) 
    
    try:
        # Run Sim
        result = sim.run_simulation()
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

        # UI Reveal
        js.document.getElementById("visual-loading").style.display = "none"
        js.document.getElementById("visual-results-container").style.display = "block"

    except Exception as e:
        js.document.getElementById("visual-loading").innerHTML = f"Error: {e}"

js.document.getElementById("btn-run-single").addEventListener("click", create_proxy(run_single_sim))

# Helper for Modal
def open_group_modal(grp_name):
    matches = LAST_SIM_RESULTS.get("group_matches", {}).get(grp_name, [])
    js.document.getElementById("modal-title").innerText = f"Group {grp_name} Results"
    html = ""
    for m in matches:
        s1 = "font-weight:bold" if m['g1'] > m['g2'] else ""
        s2 = "font-weight:bold" if m['g2'] > m['g1'] else ""
        html += f"""<div class="result-row">
            <span style="flex:1; text-align:right; {s1}">{m['t1'].title()}</span>
            <span class="result-score" style="margin:0 15px;">{m['g1']} - {m['g2']}</span>
            <span style="flex:1; text-align:left; {s2}">{m['t2'].title()}</span>
        </div>"""
    js.document.getElementById("modal-matches").innerHTML = html
    js.document.getElementById("group-modal").style.display = "block"

js.window.view_group_matches = create_proxy(open_group_modal)

# =============================================================================
# --- 2. BULK SIMULATION (ASYNC) ---
# =============================================================================
async def run_bulk_sim(event):
    num = int(js.document.getElementById("bulk-count").value)
    out_div = js.document.getElementById("bulk-results")
    out_div.innerHTML = f"Running {num} simulations... please wait."
    
    await asyncio.sleep(0.01)
    
    # New Data Structure: Dictionary of Dictionaries
    # stats = {'Brazil': {'1st': 5, '2nd': 2, '3rd': 1}, ...}
    stats = {}
    
    for i in range(num):
        res = sim.run_simulation(quiet=True, fast_mode=True)
        
        # Get results
        first = res["champion"]
        second = res["runner_up"]
        third = res["third_place"]
        
        # Helper to safely increment
        def add_stat(team, place):
            if team not in stats: stats[team] = {'1st':0, '2nd':0, '3rd':0}
            stats[team][place] += 1
            
        add_stat(first, '1st')
        add_stat(second, '2nd')
        add_stat(third, '3rd')
        
        if i % 20 == 0: 
            out_div.innerHTML = f"Running... ({i}/{num})"
            await asyncio.sleep(0.01)
            
    gc.collect()
    
    # Sort by Weighted Score (Gold=3, Silver=2, Bronze=1)
    def get_score(item):
        s = item[1]
        return (s['1st'] * 3) + (s['2nd'] * 2) + (s['3rd'] * 1)
        
    sorted_stats = sorted(stats.items(), key=get_score, reverse=True)
    
    # Build Table
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
        # Highlight strong contenders
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

# =============================================================================
# --- 3. DATA VIEW (Standard) ---
# =============================================================================
def load_data_view(event):
    container = js.document.getElementById("data-table-container")
    container.innerHTML = "" 
    
    # Check Filter
    checkbox = js.document.getElementById("data-filter-wc")
    wc_only = checkbox.checked if checkbox else False
    
    html = """<table class="data-table"><thead><tr><th>Rank</th><th>Team</th><th>Elo</th><th>Off</th><th>Def</th><th>Style</th></tr></thead><tbody>"""
    sorted_teams = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)
    
    # We need a separate counter for "Rank" because we might skip rows
    rank_counter = 0
    
    for team, stats in sorted_teams:
        # FILTER:
        if wc_only and team not in sim.WC_TEAMS:
            continue
            
        rank_counter += 1
        
        style = sim.TEAM_PROFILES.get(team, "Balanced")
        display_style = style
        # (Add your style re-naming logic here if you haven't updated simulation_engine.py yet)
        if style == "Hero Ball": display_style = "Star-Centric"
        elif style == "Dark Arts": display_style = "Aggressive"
        elif style == "Diesel Engine": display_style = "Endurance"
        elif style == "Blitzkrieg": display_style = "Fast-Paced"

        rank_style = "font-weight:bold;" if rank_counter <= 10 else ""
        if rank_counter == 1: rank_style += "color:#f1c40f;" 
        elif rank_counter == 2: rank_style += "color:#95a5a6;"
        elif rank_counter == 3: rank_style += "color:#cd7f32;"
        
        html += f"""<tr><td style='{rank_style}'>#{rank_counter}</td><td style='font-weight:600'>{team.title()}</td><td>{int(stats['elo'])}</td><td>{round(stats['off'], 2)}</td><td>{round(stats['def'], 2)}</td><td>{display_style}</td></tr>"""
    
    html += "</tbody></table>"
    container.innerHTML = html

# =============================================================================
# --- 4. HISTORY VIEW (ASYNC CHARTS) ---
# =============================================================================
async def view_team_history(event):
    js.document.getElementById("team-stats-card").innerHTML = "Loading Analysis..."
    await asyncio.sleep(0.01) # Yield
    
    try:
        team = js.document.getElementById("team-select").value
        timeframe = js.document.getElementById("chart-timeframe").value
        
        stats = sim.TEAM_STATS.get(team)
        history = sim.TEAM_HISTORY.get(team)
        
        if not stats or not history:
            js.document.getElementById("team-stats-card").innerHTML = "No data found."
            return

        # RENDER STATS CARD
        style = sim.TEAM_PROFILES.get(team, "Balanced")
        display_style = style
        if style == "Hero Ball": display_style = "Star-Centric"
        elif style == "Dark Arts": display_style = "Aggressive"
        elif style == "Diesel Engine": display_style = "Endurance"
        elif style == "Blitzkrieg": display_style = "Fast-Paced"
        
        card_html = f"""
        <div style='background:#2c3e50; color:white; padding:20px; border-radius:8px;'>
            <h1 style='margin:0; font-size:2.5em;'>{team.title()}</h1>
            <div style='margin-top:10px; font-size:1.2em;'>
                Rating: <strong style='color:#f1c40f'>{int(stats['elo'])}</strong>
            </div>
            <hr style='border-color:#ffffff30;'>
            <p><strong>Play Style:</strong> {display_style}</p>
            <p><strong>Offense:</strong> {round(stats['off'], 2)}x avg</p>
            <p><strong>Defense:</strong> {round(stats['def'], 2)}x avg</p>
        </div>
        """
        js.document.getElementById("team-stats-card").innerHTML = card_html

        # PLOT ELO
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

        # PLOT BAR
        fig2, ax2 = plt.subplots(figsize=(4, 3))
        ax2.bar(['Attack', 'Defense'], [stats['off'], stats['def']], color=['#27ae60', '#e74c3c'])
        ax2.axhline(y=1.0, color='gray', linestyle='--')
        ax2.set_title("Team Strength")
        plt.tight_layout()
        js.document.getElementById("dist-chart-container").innerHTML = ""
        display(fig2, target="dist-chart-container")
        plt.close(fig2)
        
    except Exception as e:
        js.document.getElementById("team-stats-card").innerHTML = f"Error: {e}"

js.document.getElementById("btn-view-history").addEventListener("click", create_proxy(view_team_history))

async def plot_style_map(event):
    js.document.getElementById("main-chart-container").innerHTML = "Generating Global Map..."
    await asyncio.sleep(0.01)
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Colors
    style_colors = {'Star-Centric': '#e74c3c', 'Aggressive': '#34495e', 'Endurance': '#f39c12', 'Fast-Paced': '#2ecc71', 'Balanced': '#95a5a6', 'Hero Ball': '#e74c3c', 'Dark Arts': '#34495e', 'Diesel Engine': '#f39c12', 'Blitzkrieg': '#2ecc71'}
    
    wc_only = js.document.getElementById("hist-filter-wc").checked
    sorted_teams = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)
    
    # Build list of teams to plot
    teams_to_plot = []
    if wc_only:
        # Filter by official list
        teams_to_plot = [t for t in sorted_teams if t[0] in sim.WC_TEAMS]
    else:
        # Default to top 100 if showing global
        teams_to_plot = sorted_teams[:100]

    for team, stats in teams_to_plot:
        x, y = stats.get('style_x', 0), stats.get('style_y', 0)
        style_name = sim.TEAM_PROFILES.get(team, 'Balanced')
        color = style_colors.get(style_name, 'gray')
        
        ax.scatter([x], [y], c=[color], alpha=0.7, edgecolors='w', s=100)
        
        # Label logic
        should_label = False
        # If filtered, label more teams because there is space
        if wc_only: 
             if team in ['argentina', 'france', 'portugal', 'usa', 'england', 'brazil', 'germany', 'spain', 'japan', 'morocco', 'canada', 'mexico']: should_label = True
        else:
             if team in ['argentina', 'france', 'portugal', 'usa', 'england', 'brazil']: should_label = True
        
        if should_label: ax.annotate(team.title(), (x, y), fontsize=8, alpha=0.8)

    ax.set_title(f"Team Style Map ({'Tournament Teams' if wc_only else 'Top 100'})", fontsize=14, fontweight='bold')
    ax.set_xlabel("Star Reliance (Individualism)", fontsize=10)
    ax.set_ylabel("Aggression / Penalty Ratio", fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.3)
    
    # Legend Code (Keep your legend code here!)
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#e74c3c', label='Star-Centric', markersize=10),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#34495e', label='Aggressive', markersize=10),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#f39c12', label='Endurance', markersize=10),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#2ecc71', label='Fast-Paced', markersize=10),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#95a5a6', label='Balanced', markersize=10),
    ]
    ax.legend(handles=legend_elements, title="Play Styles")

    js.document.getElementById("main-chart-container").innerHTML = ""
    display(fig, target="main-chart-container")
    plt.close(fig)