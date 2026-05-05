from nba_api.stats.endpoints import leaguegamefinder
import pandas as pd
import sys
sys.path.append('.')
from db import get_engine, upsert
from sqlalchemy import text
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

def get_round(game_id):
    try:
        gid = str(game_id)
        print(f"Sample game_id: {gid}")
        return int(gid[7])
    except:
        return None

def fetch_games():
    engine = get_engine()

    gamefinder = fetch_with_retry(
        lambda: leaguegamefinder.LeagueGameFinder(
            season_nullable='2025-26',
            season_type_nullable='Playoffs',
            league_id_nullable='00'
        ),
        label="playoff games"
    )

    df = gamefinder.get_data_frames()[0]

    # Separate home and away
    home = df[df['MATCHUP'].str.contains('vs.')].copy()
    away = df[df['MATCHUP'].str.contains('@')].copy()

    # Merge on GAME_ID
    games = home.merge(away, on='GAME_ID', suffixes=('_home', '_away'))

    games = games.rename(columns={
        'GAME_ID': 'game_id',
        'GAME_DATE_home': 'game_date',
        'TEAM_ID_home': 'home_team_id',
        'TEAM_ID_away': 'away_team_id',
        'PTS_home': 'home_score',
        'PTS_away': 'away_score',
    })

    games['season_type'] = 'playoffs'
    games['round'] = games['game_id'].apply(get_round)

    games = games[[
        'game_id', 'game_date', 'season_type',
        'home_team_id', 'away_team_id',
        'home_score', 'away_score',
        'round'
    ]]

    games = games.drop_duplicates(subset='game_id')

    # Append only — skip game_ids already in DB
    with engine.connect() as conn:
        existing = pd.read_sql('SELECT game_id FROM games', conn)
        existing_ids = set(existing['game_id'].astype(str))

    new_games = games[~games['game_id'].astype(str).isin(existing_ids)]

    if new_games.empty:
        print("No new games to insert — skipping.")
        return

    upsert(new_games, 'games', ['game_id'])
    print(f"Inserted {len(new_games)} new playoff games")

if __name__ == "__main__":
    fetch_games()