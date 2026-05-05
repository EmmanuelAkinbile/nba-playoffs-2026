import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nba_api.stats.endpoints import leaguestandingsv3, leaguedashteamstats
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


def split_record(record_str, index):
    try:
        return int(str(record_str).split('-')[index])
    except:
        return None


def fetch_team_standings():
    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM team_standings'))
        count = result.scalar()
        if count > 0:
            print(f"Team standings already populated ({count} rows) — skipping.")
            return

    # --- Standings (wins, losses, home/away records) ---
    standings = fetch_with_retry(
        lambda: leaguestandingsv3.LeagueStandingsV3(
            season="2025-26",
            season_type="Regular Season"
        ),
        label="team standings"
    )
    df = standings.get_data_frames()[0]

    df_clean = pd.DataFrame({
        "team_id": df["TeamID"].astype("Int64"),
        "season": "2025-26",
        "wins": df["WINS"].astype("Int64"),
        "losses": df["LOSSES"].astype("Int64"),
        "win_pct": df["WinPCT"].astype(float),
        "conference_rank": df["PlayoffRank"].astype("Int64"),
        "division_rank": df["DivisionRank"].astype("Int64"),
        "home_wins": df["HOME"].apply(lambda x: split_record(x, 0)),
        "home_losses": df["HOME"].apply(lambda x: split_record(x, 1)),
        "away_wins": df["ROAD"].apply(lambda x: split_record(x, 0)),
        "away_losses": df["ROAD"].apply(lambda x: split_record(x, 1)),
    })

    time.sleep(3)

    # --- Base stats (ppg, opp_ppg, rebounds, assists) — divide by GP ---
    print("Fetching regular season base team stats...")

    base = fetch_with_retry(
        lambda: leaguedashteamstats.LeagueDashTeamStats(
            season="2025-26",
            season_type_all_star="Regular Season",
            measure_type_detailed_defense="Base"
        ),
        label="regular season team stats base"
    )
    base_df = base.get_data_frames()[0]
    print("Base columns:", base_df.columns.tolist())

    time.sleep(3)

    # --- Advanced stats (offensive_rating, defensive_rating, pace) ---
    print("Fetching regular season advanced team stats...")

    advanced = fetch_with_retry(
        lambda: leaguedashteamstats.LeagueDashTeamStats(
            season="2025-26",
            season_type_all_star="Regular Season",
            measure_type_detailed_defense="Advanced"
        ),
        label="regular season team stats advanced"
    )
    adv_df = advanced.get_data_frames()[0]
    print("Advanced columns:", adv_df.columns.tolist())

    # --- Build stats dataframe ---
    base_clean = pd.DataFrame({
        "team_id": base_df["TEAM_ID"].astype("Int64"),
        "ppg": (base_df["PTS"] / base_df["GP"]).round(1),
        "opp_ppg": (base_df["OPP_PTS"] / base_df["GP"]).round(1) if "OPP_PTS" in base_df.columns else None,
        "rebounds_pg": (base_df["REB"] / base_df["GP"]).round(1),
        "assists_pg": (base_df["AST"] / base_df["GP"]).round(1),
    })

    adv_clean = pd.DataFrame({
        "team_id": adv_df["TEAM_ID"].astype("Int64"),
        "offensive_rating": adv_df["OFF_RATING"].round(1) if "OFF_RATING" in adv_df.columns else None,
        "defensive_rating": adv_df["DEF_RATING"].round(1) if "DEF_RATING" in adv_df.columns else None,
        "pace": adv_df["PACE"].round(1) if "PACE" in adv_df.columns else None,
    })

    # --- Merge everything ---
    stats_merged = base_clean.merge(adv_clean, on="team_id", how="left")
    df_final = df_clean.merge(stats_merged, on="team_id", how="left")

    upsert(df_final, "team_standings", ["team_id", "season"])
    print(f"Upserted {len(df_final)} team standings rows.")


if __name__ == "__main__":
    fetch_team_standings()