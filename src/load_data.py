import csv
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base
from datetime import datetime
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
Base = declarative_base()

class Clue(Base):
    __tablename__ = 'clues'
    
    id = sa.Column(sa.Integer, primary_key=True)
    round = sa.Column(sa.Integer)
    clue_value = sa.Column(sa.Integer)
    is_daily_double = sa.Column(sa.Boolean)
    category = sa.Column(sa.String)
    comments = sa.Column(sa.String)
    clue_text = sa.Column(sa.String)
    correct_answer = sa.Column(sa.String)
    air_date = sa.Column(sa.Date)
    notes = sa.Column(sa.String)

def create_db_engine():
    """Create SQLite database engine"""
    return sa.create_engine('sqlite:///jeopardy.db')

def load_data(engine):
    """Load data from TSV file into database"""
    Base.metadata.create_all(engine)
    
    data_path = Path(__file__).parent.parent / 'combined_season1-40.tsv'
    
    if not data_path.exists():
        logger.error(f"Data file not found at {data_path}")
        return

    logger.info(f"Loading data from {data_path}")
    
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
                        logger.info(f"Processed {total_rows} rows...")
                    
                except Exception as e:
                    logger.error(f"Error processing row {row}: {str(e)}")
                    continue
            
            logger.info(f"Successfully loaded {total_rows} rows")

if __name__ == '__main__':
    engine = create_db_engine()
    load_data(engine)
    logger.info("Data loading completed")
