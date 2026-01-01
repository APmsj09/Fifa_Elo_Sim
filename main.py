import js
import simulation_engine as sim
from pyodide.ffi import create_proxy
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 1. INITIALIZE
print("Initializing Engine...")
sim.DATA_DIR = "."
sim.TEAM_STATS, sim.TEAM_PROFILES, sim.AVG_GOALS = sim.initialize_engine()

# Remove loading screen, show main dashboard
js.document.getElementById("loading-screen").style.display = "none"
js.document.getElementById("main-dashboard").style.display = "block"

# =============================================================================
# --- TAB NAVIGATION ---
# =============================================================================
def switch_tab(tab_id):
    # Hide all tabs
    for t in ["tab-single", "tab-bulk", "tab-data", "tab-history"]:
        js.document.getElementById(t).style.display = "none"
    # Show selected
    js.document.getElementById(tab_id).style.display = "block"

def setup_tabs():
    js.document.getElementById("btn-tab-single").addEventListener("click", create_proxy(lambda e: switch_tab("tab-single")))
    js.document.getElementById("btn-tab-bulk").addEventListener("click", create_proxy(lambda e: switch_tab("tab-bulk")))
    js.document.getElementById("btn-tab-data").addEventListener("click", create_proxy(lambda e: switch_tab("tab-data")))
    js.document.getElementById("btn-tab-history").addEventListener("click", create_proxy(lambda e: switch_tab("tab-history")))
    
    # Populate Team Dropdown for History Tab
    select = js.document.getElementById("team-select")
    sorted_teams = sorted(sim.TEAM_STATS.keys())
    for t in sorted_teams:
        opt = js.document.createElement("option")
        opt.value = t
        opt.text = t.title()
        select.appendChild(opt)

setup_tabs()

# =============================================================================
# --- 1. SINGLE SIMULATION ---
# =============================================================================
# Global to store current sim results
LAST_SIM_RESULTS = {}

def run_single_sim(event):
    global LAST_SIM_RESULTS
    
    # UI Prep
    js.document.getElementById("visual-loading").style.display = "block"
    js.document.getElementById("visual-results-container").style.display = "none"
    
    try:
        # Run Sim
        result = sim.run_simulation()
        LAST_SIM_RESULTS = result # Store for modal access
        
        champion = result["champion"]
        groups_data = result["groups_data"]
        bracket_data = result["bracket_data"]
        
        # 1. Render Champion
        js.document.getElementById("visual-champion-name").innerText = champion.upper()

        # 2. Render Groups HTML
        groups_html = ""
        for grp_name, team_list in groups_data.items():
            # Added onclick event to the div
            groups_html += f"""
            <div class="group-box" onclick="window.view_group_matches('{grp_name}')" title="Click to view match results">
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

        # 3. Render Bracket HTML
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

# --- NEW FUNCTION TO HANDLE MODAL ---
def open_group_modal(grp_name):
    matches = LAST_SIM_RESULTS.get("group_matches", {}).get(grp_name, [])
    
    js.document.getElementById("modal-title").innerText = f"Group {grp_name} Results"
    
    html = ""
    for m in matches:
        # Style winner
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

# EXPOSE FUNCTION TO JS WINDOW
js.window.view_group_matches = create_proxy(open_group_modal)

# =============================================================================
# --- 2. BULK SIMULATION ---
# =============================================================================
def run_bulk_sim(event):
    num = int(js.document.getElementById("bulk-count").value)
    out_div = js.document.getElementById("bulk-results")
    out_div.innerHTML = f"Running {num} simulations... please wait."
    
    winners = {}
    
    # Run loop
    for i in range(num):
        res = sim.run_simulation(quiet=True)
        w = res["champion"]
        winners[w] = winners.get(w, 0) + 1
    
    # Sort and Display
    sorted_w = sorted(winners.items(), key=lambda x: x[1], reverse=True)
    
    html = "<h3>Results</h3><table><tr><th>Team</th><th>Wins</th><th>%</th></tr>"
    for team, wins in sorted_w:
        perc = round((wins / num) * 100, 1)
        html += f"<tr><td>{team.title()}</td><td>{wins}</td><td>{perc}%</td></tr>"
    html += "</table>"
    
    out_div.innerHTML = html

js.document.getElementById("btn-run-bulk").addEventListener("click", create_proxy(run_bulk_sim))


# =============================================================================
# --- 3. DATA VIEW ---
# =============================================================================
def load_data_view(event):
    container = js.document.getElementById("data-table-container")
    container.innerHTML = "" 
    
    # Check Filter Status
    wc_only = js.document.getElementById("data-filter-wc").checked
    
    html = """
    <table class="data-table">
        <thead>
            <tr>
                <th>Rank</th>
                <th>Team</th>
                <th>Elo Rating</th>
                <th>Offense</th>
                <th>Defense</th>
                <th>Play Style</th>
            </tr>
        </thead>
        <tbody>
    """
    
    sorted_teams = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)
    
    count = 0
    for i, (team, stats) in enumerate(sorted_teams):
        rank = i + 1
        
        # FILTER LOGIC:
        # If "WC Only" is checked, we stop after the top 48 teams
        if wc_only and rank > 48:
            break
            
        style = sim.TEAM_PROFILES.get(team, "Balanced")
        
        # Style mapping for display (Technical Name -> Display Name)
        display_style = style
        if style == "Hero Ball": display_style = "Star-Centric"
        elif style == "Dark Arts": display_style = "Aggressive"
        elif style == "Diesel Engine": display_style = "Endurance"
        elif style == "Blitzkrieg": display_style = "Fast-Paced"

        rank_style = "font-weight:bold;" if rank <= 10 else ""
        if rank == 1: rank_style += "color:#f1c40f;" 
        elif rank == 2: rank_style += "color:#95a5a6;"
        elif rank == 3: rank_style += "color:#cd7f32;"
        
        html += f"""
        <tr>
            <td style='{rank_style}'>#{rank}</td>
            <td style='font-weight:600'>{team.title()}</td>
            <td>{int(stats['elo'])}</td>
            <td>{round(stats['off'], 2)}</td>
            <td>{round(stats['def'], 2)}</td>
            <td>{display_style}</td>
        </tr>
        """
    
    html += "</tbody></table>"
    container.innerHTML = html

js.document.getElementById("btn-tab-data").addEventListener("click", create_proxy(load_data_view))
# Re-load when checkbox is clicked
js.document.getElementById("data-filter-wc").addEventListener("change", create_proxy(load_data_view))


# =============================================================================
# --- 4. HISTORY VIEW ---
# =============================================================================
def view_team_history(event):
    try:
        # 1. GET INPUTS
        # We use defensive checks in case HTML is outdated
        team_el = js.document.getElementById("team-select")
        time_el = js.document.getElementById("chart-timeframe")
        
        if not team_el or not time_el:
            js.document.getElementById("history-output").innerHTML = "Error: HTML elements missing. Please update index.html."
            return

        team = team_el.value
        timeframe = time_el.value
        
        # 2. GET DATA
        # Ensure sim.TEAM_HISTORY exists. If not, engine didn't initialize correctly.
        if not hasattr(sim, 'TEAM_HISTORY') or not sim.TEAM_HISTORY:
            js.document.getElementById("team-stats-card").innerHTML = "Error: History data not loaded. Check simulation_engine.py."
            return

        stats = sim.TEAM_STATS.get(team)
        history = sim.TEAM_HISTORY.get(team)
        
        if not stats or not history:
            js.document.getElementById("team-stats-card").innerHTML = f"No data found for {team}."
            return

        # 3. RENDER STATS CARD
        style = sim.TEAM_PROFILES.get(team, "Balanced")
        card_html = f"""
        <div style='background:#2c3e50; color:white; padding:20px; border-radius:8px;'>
            <h1 style='margin:0; font-size:2.5em;'>{team.title()}</h1>
            <div style='margin-top:10px; font-size:1.2em;'>
                Rating: <strong style='color:#f1c40f'>{int(stats['elo'])}</strong>
            </div>
            <hr style='border-color:#ffffff30;'>
            <p><strong>Play Style:</strong> {style}</p>
            <p><strong>Offense:</strong> {round(stats['off'], 2)}x avg</p>
            <p><strong>Defense:</strong> {round(stats['def'], 2)}x avg</p>
        </div>
        """
        js.document.getElementById("team-stats-card").innerHTML = card_html

        # 4. PREPARE DATA FOR PLOTTING
        dates = history['dates']
        elos = history['elo']
        
        limit = 0
        if timeframe == "10y": limit = -150 
        elif timeframe == "4y": limit = -60 
        
        if limit != 0 and abs(limit) < len(dates):
            plot_dates = dates[limit:]
            plot_elos = elos[limit:]
        else:
            plot_dates = dates
            plot_elos = elos

        # 5. PLOT ELO HISTORY
        fig1, ax1 = plt.subplots(figsize=(8, 4))
        ax1.plot(plot_dates, plot_elos, color='#2980b9', linewidth=2)
        ax1.set_title(f"{team.title()} - Elo Rating History", fontsize=12)
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.fill_between(plot_dates, plot_elos, min(plot_elos)-50, color='#3498db', alpha=0.1)
        
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Clear previous chart and display new one
        js.document.getElementById("main-chart-container").innerHTML = ""
        display(fig1, target="main-chart-container")
        plt.close(fig1)

        # 6. PLOT BAR CHART (Off/Def)
        fig2, ax2 = plt.subplots(figsize=(4, 3))
        categories = ['Attack', 'Defense']
        values = [stats['off'], stats['def']]
        colors = ['#27ae60', '#e74c3c']
        
        ax2.bar(categories, values, color=colors)
        ax2.axhline(y=1.0, color='gray', linestyle='--', label="Avg")
        ax2.set_title("Team Strength")
        plt.tight_layout()
        
        js.document.getElementById("dist-chart-container").innerHTML = ""
        display(fig2, target="dist-chart-container")
        plt.close(fig2)
        
    except Exception as e:
        # Print error to screen so we can see it
        js.document.getElementById("team-stats-card").innerHTML = f"PYTHON ERROR: {str(e)}"

js.document.getElementById("btn-view-history").addEventListener("click", create_proxy(view_team_history))

def plot_style_map(event):
    # Setup
    fig, ax = plt.subplots(figsize=(8, 6))
    
    x_vals = []
    y_vals = []
    colors = []
    
    # Updated Colors for New Names
    style_colors = {
        'Star-Centric': '#e74c3c', # Red
        'Aggressive': '#34495e',   # Dark Blue
        'Endurance': '#f39c12',    # Orange
        'Fast-Paced': '#2ecc71',   # Green
        'Balanced': '#95a5a6',     # Grey
        # Fallbacks for old data if names didn't update yet
        'Hero Ball': '#e74c3c',
        'Dark Arts': '#34495e',
        'Diesel Engine': '#f39c12',
        'Blitzkrieg': '#2ecc71'
    }
    
    # FILTER LOGIC
    wc_only = js.document.getElementById("hist-filter-wc").checked
    
    # Sort by Elo
    sorted_teams = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)
    
    # Determine how many teams to plot
    # If WC Only: Top 48. If All: Top 100 (plotting 200+ makes the graph unreadable)
    limit = 48 if wc_only else 100
    
    teams_to_plot = sorted_teams[:limit]
    
    for team, stats in teams_to_plot:
        x = stats.get('style_x', 0)
        y = stats.get('style_y', 0)
        style_name = sim.TEAM_PROFILES.get(team, 'Balanced')
        
        x_vals.append(x)
        y_vals.append(y)
        colors.append(style_colors.get(style_name, 'gray'))
        
        # Label prominent teams
        # We label more teams if we are in "WC Only" mode since there's less clutter
        if wc_only:
             if team in ['argentina', 'france', 'portugal', 'usa', 'england', 'brazil', 'germany', 'spain', 'japan', 'morocco']:
                ax.annotate(team.title(), (x, y), fontsize=8, alpha=0.8)
        else:
             if team in ['argentina', 'france', 'portugal', 'usa', 'england', 'brazil']:
                ax.annotate(team.title(), (x, y), fontsize=8, alpha=0.8)

    ax.scatter(x_vals, y_vals, c=colors, alpha=0.7, edgecolors='w', s=100)
    
    ax.set_title(f"Team Style Map ({'Top 48' if wc_only else 'Top 100'})", fontsize=14, fontweight='bold')
    ax.set_xlabel("Star Reliance (Individualism)", fontsize=10)
    ax.set_ylabel("Aggression / Penalty Ratio", fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.3)
    
    # Clean Legend
    from matplotlib.lines import Line2D
    # Only show legend items for the new clear names
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