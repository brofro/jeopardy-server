import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Clue

@pytest.fixture
def db_session():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_clue_model(db_session):
    # Test creating a new clue
    clue = Clue(
        round=1,
        clue_value=200,
        is_daily_double=False,
        category="HISTORY",
        comments="",
        answer="George Washington",
        question="He was the first U.S. president",
        air_date=date.fromisoformat("2023-01-01"),
        notes=""
    )
    
    db_session.add(clue)
    db_session.commit()
    
    # Verify the clue was saved correctly
    saved_clue = db_session.query(Clue).first()
    assert saved_clue.category == "HISTORY"
    assert saved_clue.answer == "George Washington"
    assert saved_clue.is_daily_double is False
