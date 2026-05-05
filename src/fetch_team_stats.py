import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nba_api.stats.endpoints import leaguedashteamstats
from db import get_engine, upsert
from sqlalchemy import text
import pandas as pd
import time


def fetch_with_retry(fetch_func, label, max_retries=5, sleep_between=10):
    for attempt in range(1, max_retries + 1):
        try:
            result = fetch_func()
            return result
        except Exception as e:
            print(f"Attempt {attempt} failed for {label}: {e}")
            if attempt < max_retries:
                print(f"Retrying in {sleep_between} seconds...")
                time.sleep(sleep_between)
            else:
                raise Exception(f"All {max_retries} attempts failed for {label}")


def fetch_team_stats():
    engine = get_engine()

    # --- Base stats ---
    print("Fetching playoff team stats (Base)...")
    base = fetch_with_retry(
        lambda: leaguedashteamstats.LeagueDashTeamStats(
            season="2025-26",
            season_type_all_star="Playoffs",
            measure_type_detailed_defense="Base"
        ),
        label="playoff team stats base"
    )
    base_df = base.get_data_frames()[0]
    print("Base columns:", base_df.columns.tolist())

    time.sleep(3)

    # --- Advanced stats ---
    print("Fetching playoff team stats (Advanced)...")
    advanced = fetch_with_retry(
        lambda: leaguedashteamstats.LeagueDashTeamStats(
            season="2025-26",
            season_type_all_star="Playoffs",
            measure_type_detailed_defense="Advanced"
        ),
        label="playoff team stats advanced"
    )
    adv_df = advanced.get_data_frames()[0]
    print("Advanced columns:", adv_df.columns.tolist())

    # --- Build base dataframe (divide totals by GP) ---
    base_clean = pd.DataFrame({
        "team_id": base_df["TEAM_ID"].astype("Int64"),
        "season": "2025-26",
        "season_type": "playoffs",
        "ppg": (base_df["PTS"] / base_df["GP"]).round(1),
        "rebounds_pg": (base_df["REB"] / base_df["GP"]).round(1),
        "assists_pg": (base_df["AST"] / base_df["GP"]).round(1),
    })

    # --- Build advanced dataframe ---
    adv_clean = pd.DataFrame({
        "team_id": adv_df["TEAM_ID"].astype("Int64"),
        "offensive_rating": adv_df["OFF_RATING"].round(1) if "OFF_RATING" in adv_df.columns else None,
        "defensive_rating": adv_df["DEF_RATING"].round(1) if "DEF_RATING" in adv_df.columns else None,
        "pace": adv_df["PACE"].round(1) if "PACE" in adv_df.columns else None,
    })

    # --- Merge ---
    df_clean = base_clean.merge(adv_clean, on="team_id", how="left")

    # --- Delete and reinsert ---
    with engine.connect() as conn:
        conn.execute(text(
            "DELETE FROM team_stats WHERE season_type = 'playoffs' AND season = '2025-26'"
        ))
        conn.commit()
        print("Cleared existing playoff team stats rows.")

    upsert(df_clean, "team_stats", ["team_id", "season", "season_type"])
    print(f"Inserted {len(df_clean)} playoff team stats rows.")


if __name__ == "__main__":
    fetch_team_stats()