import subprocess
import sys

PYTHON = r"C:\Users\emman\AppData\Local\Python\bin\python.exe"

scripts = [
    "src/fetch_teams.py",
    "src/fetch_players.py",
    "src/fetch_team_standings.py",
    "src/fetch_games.py",
    "src/fetch_stats.py",
    "src/fetch_team_stats.py",
]

def run_pipeline():
    print("Starting NBA Playoffs 2026 Pipeline...\n")

    for script in scripts:
        print(f"Running {script}...")
        result = subprocess.run(
            [PYTHON, script],
            capture_output=False
        )

        if result.returncode != 0:
            print(f"Error in {script} — stopping pipeline")
            sys.exit(1)

        print(f"Completed {script}\n")

    print("Pipeline complete.")

if __name__ == "__main__":
    run_pipeline()