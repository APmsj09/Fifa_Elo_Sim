import js
import simulation_engine as sim
from pyodide.ffi import create_proxy

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
def run_single_sim(event):
    # UI Prep
    js.document.getElementById("visual-loading").style.display = "block"
    js.document.getElementById("visual-results-container").style.display = "none"
    
    try:
        # Run Sim
        result = sim.run_simulation()
        champion = result["champion"]
        groups_data = result["groups_data"]
        bracket_data = result["bracket_data"]
        
        # 1. Render Champion
        js.document.getElementById("visual-champion-name").innerText = champion.upper()

        # 2. Render Groups HTML
        groups_html = ""
        for grp_name, team_list in groups_data.items():
            groups_html += f"""
            <div class="group-box">
                <h3>Group {grp_name}</h3>
                <table class="group-table">
                    <thead><tr><th>Team</th><th>P</th><th>W</th><th>D</th><th>L</th><th>GD</th></tr></thead>
                    <tbody>
            """
            for i, row in enumerate(team_list):
                # Top 2 qualify visually
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
                # Determine styling for winner/loser
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
            bracket_html += "</div>" # End bracket-round
            
        js.document.getElementById("bracket-container").innerHTML = bracket_html

        # UI Reveal
        js.document.getElementById("visual-loading").style.display = "none"
        js.document.getElementById("visual-results-container").style.display = "block"

    except Exception as e:
        js.document.getElementById("visual-loading").innerHTML = f"Error: {e}"

js.document.getElementById("btn-run-single").addEventListener("click", create_proxy(run_single_sim))

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
    if container.innerHTML != "": return # Already loaded
    
    html = "<table class='data-table'><thead><tr><th>Team</th><th>Elo</th><th>Off</th><th>Def</th><th>Style</th></tr></thead><tbody>"
    
    sorted_teams = sorted(sim.TEAM_STATS.items(), key=lambda x: x[1]['elo'], reverse=True)
    
    for team, stats in sorted_teams:
        style = sim.TEAM_PROFILES.get(team, "Balanced")
        html += f"""<tr>
            <td>{team.title()}</td>
            <td>{int(stats['elo'])}</td>
            <td>{round(stats['off'], 2)}</td>
            <td>{round(stats['def'], 2)}</td>
            <td>{style}</td>
        </tr>"""
    
    html += "</tbody></table>"
    container.innerHTML = html

js.document.getElementById("btn-tab-data").addEventListener("click", create_proxy(load_data_view))


# =============================================================================
# --- 4. HISTORY VIEW ---
# =============================================================================
def view_team_history(event):
    team = js.document.getElementById("team-select").value
    out = js.document.getElementById("history-output")
    
    stats = sim.TEAM_STATS.get(team)
    style = sim.TEAM_PROFILES.get(team, "Balanced")
    
    if not stats:
        out.innerHTML = "Team data not found."
        return

    html = f"""
    <div style='background:#f8f9fa; padding:15px; border-radius:8px;'>
        <h2>{team.title()}</h2>
        <p><strong>Elo Rating:</strong> {int(stats['elo'])}</p>
        <p><strong>Play Style:</strong> {style}</p>
        <p><strong>Offensive Rating:</strong> {round(stats['off'], 3)}</p>
        <p><strong>Defensive Rating:</strong> {round(stats['def'], 3)}</p>
        <hr>
        <p><em>(Detailed match history coming in v2.0)</em></p>
    </div>
    """
    out.innerHTML = html

js.document.getElementById("btn-view-history").addEventListener("click", create_proxy(view_team_history))