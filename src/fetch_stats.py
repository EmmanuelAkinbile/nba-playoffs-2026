from nba_api.stats.endpoints import (
    boxscoretraditionalv2,
    playercareerstats,
    leaguedashplayerstats
)
from sqlalchemy import text
import pandas as pd
import time
import sys
sys.path.append('.')
from db import get_engine, upsert


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


# ─────────────────────────────────────────
# 1. PLAYER GAME STATS — append only
# ─────────────────────────────────────────
def fetch_player_game_stats():
    print("Fetching player game stats...")
    engine = get_engine()

    games_df = pd.read_sql('SELECT game_id FROM games', engine)
    game_ids = games_df['game_id'].tolist()

    existing_df = pd.read_sql(
        'SELECT game_id, player_id FROM player_game_stats', engine
    )
    existing_pairs = set(
        zip(existing_df['game_id'].astype(str), existing_df['player_id'].astype(str))
    )

    all_stats = []

    for game_id in game_ids:
        try:
            boxscore = fetch_with_retry(
                lambda gid=game_id: boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=gid),
                label=f"box score game {game_id}"
            )
            df = boxscore.player_stats.get_data_frame()

            df = df[[
                'GAME_ID', 'PLAYER_ID', 'TEAM_ID', 'START_POSITION',
                'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK',
                'PLUS_MINUS', 'FG_PCT'
            ]].copy()

            df = df.rename(columns={
                'GAME_ID': 'game_id',
                'PLAYER_ID': 'player_id',
                'TEAM_ID': 'team_id',
                'START_POSITION': 'is_starter',
                'MIN': 'minutes',
                'PTS': 'points',
                'REB': 'rebounds',
                'AST': 'assists',
                'STL': 'steals',
                'BLK': 'blocks',
                'PLUS_MINUS': 'plus_minus',
                'FG_PCT': 'fg_pct'
            })

            df['is_starter'] = df['is_starter'].apply(
                lambda x: True if x and x != '' else False
            )

            df['season_type'] = 'playoffs'

            def convert_minutes(min_str):
                if pd.isna(min_str) or min_str == '':
                    return None
                try:
                    parts = str(min_str).split(':')
                    return round(float(parts[0]) + float(parts[1]) / 60, 2)
                except:
                    return None

            df['minutes'] = df['minutes'].apply(convert_minutes)
            df = df.where(pd.notnull(df), None)

            df = df[~df.apply(
                lambda r: (str(r['game_id']), str(r['player_id'])) in existing_pairs,
                axis=1
            )]

            if not df.empty:
                all_stats.append(df)
                print(f"Fetched box score for game {game_id} ({len(df)} new rows)")
            else:
                print(f"Game {game_id} already in DB — skipping.")

            time.sleep(1)

        except Exception as e:
            print(f"Error on game {game_id}: {e}")
            continue

    if all_stats:
        final_df = pd.concat(all_stats, ignore_index=True)
        upsert(final_df, 'player_game_stats', ['player_id', 'game_id'])
        print(f"Inserted {len(final_df)} new player game stat rows")
    else:
        print("No new player game stats to insert.")


# ─────────────────────────────────────────
# 2. REGULAR SEASON STATS — run once, store totals
# ─────────────────────────────────────────
def fetch_regular_season_stats():
    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM player_regular_season_stats'))
        count = result.scalar()
        if count > 0:
            print(f"Regular season stats already populated ({count} rows) — skipping.")
            return

    print("Fetching regular season stats...")

    players_df = pd.read_sql('SELECT player_id FROM players', engine)
    player_ids = players_df['player_id'].tolist()

    all_stats = []

    for player_id in player_ids:
        try:
            career = fetch_with_retry(
                lambda pid=player_id: playercareerstats.PlayerCareerStats(player_id=pid),
                label=f"career stats player {player_id}"
            )
            df = career.season_totals_regular_season.get_data_frame()
            df = df[df['SEASON_ID'] == '2025-26']

            if df.empty:
                continue

            if 'PLUS_MINUS' not in df.columns:
                df['PLUS_MINUS'] = None

            df = df[[
                'PLAYER_ID', 'SEASON_ID', 'GP',
                'PTS', 'REB', 'AST',
                'FG_PCT', 'PLUS_MINUS', 'MIN',
                'FTA', 'FTM', 'FGA', 'FGM', 'FG3A', 'FG3M'
            ]].copy()

            df = df.rename(columns={
                'PLAYER_ID': 'player_id',
                'SEASON_ID': 'season',
                'GP': 'games_played',
                'PTS': 'points',
                'REB': 'rebounds',
                'AST': 'assists',
                'PLUS_MINUS': 'plus_minus',
                'MIN': 'minutes',
                'FG_PCT': 'fg_pct',
                'FTA': 'fta',
                'FTM': 'ftm',
                'FGA': 'fga',
                'FGM': 'fgm',
                'FG3A': 'fg3a',
                'FG3M': 'fg3m',
            })

            df['ts_pct'] = (
                df['points'] / (2 * (df['fga'] + 0.44 * df['fta']))
            ).round(4)

            df = df[[
                'player_id', 'season', 'games_played',
                'points', 'rebounds', 'assists',
                'plus_minus', 'minutes', 'fg_pct',
                'fta', 'ftm', 'fga', 'fgm', 'fg3a', 'fg3m',
                'ts_pct'
            ]]

            all_stats.append(df)
            time.sleep(1)

        except Exception as e:
            print(f"Error on player {player_id}: {e}")
            continue

    if all_stats:
        final_df = pd.concat(all_stats, ignore_index=True)
        upsert(final_df, 'player_regular_season_stats', ['player_id', 'season'])
        print(f"Inserted {len(final_df)} regular season stat rows")


# ─────────────────────────────────────────
# 3. PLAYER EFFICIENCY — run once
# ─────────────────────────────────────────
def fetch_player_efficiency():
    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT COUNT(*) FROM player_regular_season_stats WHERE usg_pct IS NOT NULL"
        ))
        count = result.scalar()
        if count > 0:
            print(f"Player efficiency already populated ({count} rows) — skipping.")
            return

    print("Fetching player efficiency stats (Advanced)...")

    stats = fetch_with_retry(
        lambda: leaguedashplayerstats.LeagueDashPlayerStats(
            season='2025-26',
            season_type_all_star='Regular Season',
            measure_type_detailed_defense='Advanced'
        ),
        label="player efficiency stats"
    )
    df = stats.get_data_frames()[0]
    print("Advanced player stat columns:", df.columns.tolist())

    df_clean = pd.DataFrame({
        'player_id': df['PLAYER_ID'].astype('Int64'),
        'per': df['E_NET_RATING'].round(4) if 'E_NET_RATING' in df.columns else None,
        'usg_pct': df['USG_PCT'].round(4) if 'USG_PCT' in df.columns else None,
    })

    base_stats = fetch_with_retry(
    lambda: leaguedashplayerstats.LeagueDashPlayerStats(
        season='2025-26',
        season_type_all_star='Regular Season',
        measure_type_detailed_defense='Base'
    ),
    label="player base stats"
    )
    base_df = base_stats.get_data_frames()[0]

    plus_minus_map = dict(zip(
        base_df['PLAYER_ID'].astype('Int64'),
        base_df['PLUS_MINUS']
    ))

    df_clean['plus_minus'] = df_clean['player_id'].map(plus_minus_map).round(1)

    with engine.connect() as conn:
        for _, row in df_clean.iterrows():
            conn.execute(
                text("""
                    UPDATE player_regular_season_stats
                    SET per = :per, usg_pct = :usg_pct, plus_minus = :plus_minus
                    WHERE player_id = :player_id AND season = '2025-26'
                """),
                {'per': row['per'], 'usg_pct': row['usg_pct'],
                'plus_minus': row['plus_minus'], 'player_id': row['player_id']}
            )
        conn.commit()
    print(f"Updated efficiency stats for {len(df_clean)} players")


if __name__ == "__main__":
    print("Fetching player game stats...")
    fetch_player_game_stats()

    print("\nFetching regular season stats...")
    fetch_regular_season_stats()

    print("\nFetching player efficiency stats...")
    fetch_player_efficiency()