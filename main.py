import js
import simulation_engine as sim
from pyscript import Element

# 1. INITIALIZE ENGINE
print("Initializing Engine...")

# Set up paths and load data
sim.DATA_DIR = "."
sim.TEAM_STATS, sim.TEAM_PROFILES, sim.AVG_GOALS = sim.initialize_engine()

# Enable the button now that Python is ready
btn = js.document.getElementById("kickoff-btn")
btn.innerText = "⚽ Kick Off Simulation"
btn.disabled = False

# 2. EVENT HANDLER
def start_simulation(*args):
    """
    This function is called when the HTML button is clicked.
    """
    champion_box = js.document.getElementById("champion-box")
    log_div = js.document.getElementById("log-container")

    # Reset UI
    champion_box.style.display = "none"
    log_div.style.display = "block"
    log_div.innerHTML = '<div class="log-entry">Simulating tournament... please wait...</div>'

    # Run Logic
    result = sim.run_simulation(verbose=True)
    champion = result["champion"]
    logs = result["logs"]

    # Update Winner
    js.document.getElementById("champion-text").innerText = champion.upper()
    champion_box.style.display = "block"

    # Build Log HTML
    html_parts = []
    for line in logs:
        if "===" in line or "---" in line:
            html_parts.append(f"<div class='log-entry log-header'>{line}</div>")
        else:
            html_parts.append(f"<div class='log-entry'>{line}</div>")

    log_div.innerHTML = "".join(html_parts)