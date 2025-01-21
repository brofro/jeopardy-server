import csv
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base
from datetime import datetime
from pathlib import Path
from loguru import logger
from .models import Clue

# Database setup
Base = declarative_base()

def create_db_engine():
    """Create SQLite database engine"""
    return sa.create_engine('sqlite:///jeopardy.db')

def load_data(engine):
    """Load data from TSV file into database"""
    Base.metadata.create_all(engine)
    
    data_path = Path(__file__).parent.parent / 'combined_season1-40.tsv'
    
    if not data_path.exists():
        logger.error("Data file not found at {}", data_path)
        return

    logger.info("Loading data from {}", data_path)
    
    with engine.begin() as conn:
        with open(data_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            total_rows = 0
            
            for row in reader:
                try:
                    # Convert daily_double_value to boolean
                    is_daily_double = bool(int(row['daily_double_value']))
                    
                    # Parse air date
                    air_date = datetime.strptime(row['air_date'], '%Y-%m-%d').date()
                    
                    # Create clue instance
                    clue = Clue(
                        round=int(row['round']),
                        clue_value=int(row['clue_value']),
                        is_daily_double=is_daily_double,
                        category=row['category'],
                        comments=row['comments'],
                        clue_text=row['answer'],
                        correct_answer=row['question'],
                        air_date=air_date,
                        notes=row['notes']
                    )
                    
                    # Insert row
                    conn.execute(sa.insert(Clue), [clue.__dict__])
                    total_rows += 1
                    
                    if total_rows % 1000 == 0:
                        logger.info("Processed {} rows...", total_rows)
                    
                except Exception as e:
                    logger.error("Error processing row {}: {}", row, e)
                    continue
            
            logger.info("Successfully loaded {} rows", total_rows)

if __name__ == '__main__':
    engine = create_db_engine()
    load_data(engine)
    logger.info("Data loading completed")
