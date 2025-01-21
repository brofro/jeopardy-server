from datetime import date
from sqlalchemy import Column, Integer, String, Boolean, Date
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Clue(Base):
    __tablename__ = 'clues'
    
    id = Column(Integer, primary_key=True)
    round = Column(Integer)
    clue_value = Column(Integer)
    is_daily_double = Column(Boolean)
    category = Column(String)
    comments = Column(String)
    clue_text = Column(String)
    correct_answer = Column(String)
    air_date = Column(Date)
    notes = Column(String)
