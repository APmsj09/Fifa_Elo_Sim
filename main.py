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
    log_div = js.document.getElementById("single-log-container")
    log_div.innerHTML = "Simulating..."
    
    try:
        result = sim.run_simulation(verbose=True)
        champion = result["champion"]
        logs = result["logs"]
        
        js.document.getElementById("single-champion").innerText = champion.upper()
        
        html_parts = []
        for line in logs:
            c = "log-header" if ("===" in line or "---" in line) else ""
            html_parts.append(f"<div class='log-entry {c}'>{line}</div>")
        log_div.innerHTML = "".join(html_parts)
    except Exception as e:
        log_div.innerHTML = f"Error: {e}"

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