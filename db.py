from sqlalchemy import create_engine, text
from config import DATABASE_URL
import math

def get_engine():
    engine = create_engine(DATABASE_URL)
    return engine

def upsert(df, table_name, conflict_columns):
    engine = get_engine()
    
    with engine.connect() as conn:
        for _, row in df.iterrows():
            # Convert nan to None
            clean_row = {
                k: (None if isinstance(v, float) and math.isnan(v) else v)
                for k, v in row.to_dict().items()
            }
            
            cols = ', '.join(clean_row.keys())
            vals = ', '.join([f':{col}' for col in clean_row.keys()])
            conflict = ', '.join(conflict_columns)
            
            sql = text(f"""
                INSERT INTO {table_name} ({cols})
                VALUES ({vals})
                ON CONFLICT ({conflict}) DO NOTHING
            """)
            
            conn.execute(sql, clean_row)
        conn.commit()