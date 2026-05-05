from nba_api.stats.static import teams
import pandas as pd
import sys
sys.path.append('.')
from db import get_engine, upsert

def fetch_teams():
    engine = get_engine()

    # Skip if already populated
    with engine.connect() as conn:
        result = conn.execute(__import__('sqlalchemy').text('SELECT COUNT(*) FROM teams'))
        count = result.scalar()
        if count > 0:
            print(f"Teams table already populated ({count} rows) — skipping.")
            return

    TEAM_INFO = {
        1610612737: {'conference': 'East', 'division': 'Southeast'},
        1610612738: {'conference': 'East', 'division': 'Atlantic'},
        1610612751: {'conference': 'East', 'division': 'Atlantic'},
        1610612766: {'conference': 'East', 'division': 'Southeast'},
        1610612741: {'conference': 'East', 'division': 'Central'},
        1610612739: {'conference': 'East', 'division': 'Central'},
        1610612742: {'conference': 'West', 'division': 'Southwest'},
        1610612743: {'conference': 'West', 'division': 'Northwest'},
        1610612765: {'conference': 'East', 'division': 'Central'},
        1610612744: {'conference': 'West', 'division': 'Pacific'},
        1610612745: {'conference': 'West', 'division': 'Southwest'},
        1610612754: {'conference': 'East', 'division': 'Central'},
        1610612746: {'conference': 'West', 'division': 'Pacific'},
        1610612747: {'conference': 'West', 'division': 'Pacific'},
        1610612763: {'conference': 'West', 'division': 'Southwest'},
        1610612748: {'conference': 'East', 'division': 'Southeast'},
        1610612749: {'conference': 'East', 'division': 'Central'},
        1610612750: {'conference': 'West', 'division': 'Northwest'},
        1610612740: {'conference': 'West', 'division': 'Southwest'},
        1610612752: {'conference': 'East', 'division': 'Atlantic'},
        1610612760: {'conference': 'West', 'division': 'Northwest'},
        1610612753: {'conference': 'East', 'division': 'Southeast'},
        1610612755: {'conference': 'East', 'division': 'Atlantic'},
        1610612756: {'conference': 'West', 'division': 'Pacific'},
        1610612757: {'conference': 'West', 'division': 'Northwest'},
        1610612758: {'conference': 'West', 'division': 'Pacific'},
        1610612759: {'conference': 'West', 'division': 'Southwest'},
        1610612761: {'conference': 'East', 'division': 'Atlantic'},
        1610612762: {'conference': 'West', 'division': 'Northwest'},
        1610612764: {'conference': 'East', 'division': 'Southeast'},
    }

    all_teams = teams.get_teams()
    df = pd.DataFrame(all_teams)

    df = df.rename(columns={
        'id': 'team_id',
        'full_name': 'name',
    })

    df = df[['team_id', 'name', 'abbreviation']]

    df['conference'] = df['team_id'].map(
        lambda x: TEAM_INFO.get(x, {}).get('conference')
    )
    df['division'] = df['team_id'].map(
        lambda x: TEAM_INFO.get(x, {}).get('division')
    )

    upsert(df, 'teams', ['team_id'])
    print(f"Inserted {len(df)} teams into database")

if __name__ == "__main__":
    fetch_teams()