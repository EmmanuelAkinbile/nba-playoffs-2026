from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, playerawards
import pandas as pd
import time
import sys
from datetime import date
sys.path.append('.')
from db import get_engine, upsert
from sqlalchemy import text


def get_experience_level(years):
    if years is None:
        return 'Unknown'
    elif years == 0:
        return 'Rookie'
    elif years == 1:
        return 'Sophomore'
    elif years <= 5:
        return 'Early Career'
    elif years <= 10:
        return 'Veteran'
    else:
        return 'Seasoned Veteran'


def calculate_age(birth_date_str):
    try:
        birth_date = pd.to_datetime(birth_date_str).date()
        today = date.today()
        return today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
    except:
        return None


def get_allstar_count(player_id):
    try:
        awards = playerawards.PlayerAwards(player_id=player_id)
        df = awards.get_data_frames()[0]
        count = len(df[df['DESCRIPTION'].str.contains('All-Star', na=False)])
        return count
    except Exception:
        return 0


def fetch_players():
    engine = get_engine()

    # Skip if already populated
    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM players'))
        count = result.scalar()
        if count > 0:
            print(f"Players table already populated ({count} rows) — skipping.")
            return

    # Get playoff team IDs dynamically from games table
    playoff_teams_df = pd.read_sql(
        """
        SELECT DISTINCT home_team_id AS team_id FROM games
        UNION
        SELECT DISTINCT away_team_id FROM games
        """,
        engine
    )
    playoff_team_ids = set(playoff_teams_df['team_id'].tolist())
    print(f"Found {len(playoff_team_ids)} playoff teams.")

    all_teams = teams.get_teams()
    # Filter to playoff teams only
    playoff_teams = [t for t in all_teams if t['id'] in playoff_team_ids]
    print(f"Fetching rosters for {len(playoff_teams)} playoff teams...")

    all_players = []

    for team in playoff_teams:
        team_id = team['id']
        max_retries = 5
        attempt = 0

        while attempt < max_retries:
            try:
                roster = commonteamroster.CommonTeamRoster(
                    team_id=team_id,
                    season='2025-26'
                )
                df = roster.common_team_roster.get_data_frame()

                df = df[['PLAYER_ID', 'PLAYER', 'POSITION', 'EXP', 'TeamID', 'BIRTH_DATE']]
                df = df.rename(columns={
                    'PLAYER_ID': 'player_id',
                    'PLAYER': 'name',
                    'POSITION': 'position',
                    'EXP': 'years_in_league',
                    'TeamID': 'team_id'
                })

                df['years_in_league'] = df['years_in_league'].replace('R', 0)
                df['years_in_league'] = pd.to_numeric(
                    df['years_in_league'], errors='coerce'
                )

                df['experience_level'] = df['years_in_league'].apply(
                    get_experience_level
                )

                df['age'] = df['BIRTH_DATE'].apply(calculate_age)
                df = df.drop(columns=['BIRTH_DATE'])

                # Fetch allstar_selections via playerawards
                allstar_counts = {}
                for pid in df['player_id']:
                    allstar_counts[pid] = get_allstar_count(pid)
                    time.sleep(1.5)

                df['allstar_selections'] = df['player_id'].map(
                    allstar_counts
                ).fillna(0).astype(int)

                all_players.append(df)
                print(f"Fetched {len(df)} players for {team['full_name']}")
                time.sleep(1)
                break

            except Exception as e:
                attempt += 1
                print(f"Attempt {attempt} failed for {team['full_name']}: {e}")
                if attempt < max_retries:
                    print(f"Retrying in 10 seconds...")
                    time.sleep(10)
                else:
                    print(f"All {max_retries} attempts failed for {team['full_name']} — skipping.")

    if not all_players:
        print("No players fetched — check games table and API connection.")
        return

    final_df = pd.concat(all_players, ignore_index=True)
    final_df = final_df.drop_duplicates(subset='player_id')

    upsert(final_df, 'players', ['player_id'])
    print(f"\nTotal players inserted: {len(final_df)}")


if __name__ == "__main__":
    fetch_players()