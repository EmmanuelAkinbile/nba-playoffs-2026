import sys
sys.path.append('.')
from db import get_engine
from nba_api.stats.endpoints import playerawards
from sqlalchemy import text
import pandas as pd
import time


def get_allstar_count(player_id):
    try:
        awards = playerawards.PlayerAwards(player_id=player_id)
        df = awards.get_data_frames()[0]
        count = len(df[df['DESCRIPTION'].str.contains('All-Star', na=False)])
        return count
    except Exception:
        return 0


def update_allstar():
    engine = get_engine()

    players_df = pd.read_sql('SELECT player_id, name FROM players', engine)
    print(f"Updating allstar_selections for {len(players_df)} players...\n")

    with engine.connect() as conn:
        for _, row in players_df.iterrows():
            count = get_allstar_count(row['player_id'])

            conn.execute(
                text("""
                    UPDATE players
                    SET allstar_selections = :count
                    WHERE player_id = :player_id
                """),
                {'count': count, 'player_id': int(row['player_id'])}
            )
            conn.commit()

            print(f"{row['name']}: {count} All-Star selection(s)")
            time.sleep(1.5)

    print("\nDone — allstar_selections updated.")


if __name__ == "__main__":
    update_allstar()