import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from thefuzz import fuzz

from .models import Base, Clue

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get absolute path to database - use the root jeopardy.db
db_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "jeopardy.db")
)
logger.info(f"Database path: {db_path}")

# Database setup
engine = create_engine(f"sqlite:///{db_path}", echo=True)  # Enable SQL logging
Base.metadata.bind = engine

# Create tables if they don't exist
Base.metadata.create_all(engine)


@app.get("/")
async def root():
    return {"message": "Hello, World!"}


@app.get("/round/{round_value}")
async def get_round(round_value: int, category: str = None):
    if round_value not in [1, 2]:
        raise HTTPException(
            status_code=400,
            detail="Round value must be 1 (Single Jeopardy) or 2 (Double Jeopardy)",
        )

    try:
        # Create session with immediate execution mode
        session = Session(engine, future=True)
        try:
            logger.info(f"Fetching categories for round {round_value}")
            # Get 6 random categories for this round using GROUP BY for uniqueness
            stmt = (
                select(Clue.category)
                .where(Clue.round == round_value)
                .group_by(Clue.category)
                .order_by(func.random())
                .limit(
                    6 if not category else 5
                )  # Get 5 if we need to add a specific category
            )
            categories = session.scalars(stmt).all()

            # If specific category requested, ensure it's included
            if category:
                # Verify category exists
                category_exists = session.scalar(
                    select(Clue.category).where(Clue.category == category).limit(1)
                )
                if not category_exists:
                    raise HTTPException(
                        status_code=404, detail=f"Category '{category}' not found"
                    )

                # Add the requested category and ensure we have exactly 6 unique categories
                categories = [category] + [c for c in categories if c != category][:5]
            logger.info(f"Found {len(categories)} random categories: {categories}")

            if not categories:
                logger.warning("No categories found")
                raise HTTPException(
                    status_code=404, detail="No categories found for this round"
                )

            round_data = {}
            for category in categories:
                logger.info(f"Fetching clues for category: {category}")

                # Get all air dates for this category and round
                air_dates = session.scalars(
                    select(Clue.air_date)
                    .where(Clue.category == category, Clue.round == round_value)
                    .distinct()
                    .order_by(Clue.air_date.desc())
                ).all()

                # Try each air date until we find one with 5 clues
                clues = []
                for air_date in air_dates:
                    # Get one random clue per value for this category/round/air_date
                    value_subq = (
                        select(
                            Clue.clue_value,
                            func.min(Clue.id).label("min_id"),  # Get one ID per value
                        )
                        .where(
                            Clue.category == category,
                            Clue.round == round_value,
                            Clue.air_date == air_date,
                        )
                        .group_by(Clue.clue_value)
                        .order_by(Clue.clue_value)
                        .subquery()
                    )

                    stmt = (
                        select(Clue)
                        .join(value_subq, Clue.id == value_subq.c.min_id)
                        .order_by(Clue.clue_value)
                    )
                    clues = session.scalars(stmt).all()

                    if len(clues) == 5:
                        break

                if len(clues) != 5:
                    # TODO: Add logic to fetch new random category if we can't find 5 for this category
                    logger.error(
                        f"Could not find 5 clues for category {category} with matching air date"
                    )
                logger.info(f"Found {len(clues)} clues for category {category}")

                # Convert SQLAlchemy objects to dicts and sort by clue_value
                clues_list = []
                for clue in clues:
                    # Ensure we have a proper Clue object
                    if not hasattr(clue, "id"):
                        clue = session.merge(clue)
                    clues_list.append(
                        {
                            "id": clue.id,
                            "clue_value": clue.clue_value,
                            "is_daily_double": clue.is_daily_double,
                            "clue_text": clue.clue_text,  # The clue/question shown to player
                            "correct_answer": clue.correct_answer,  # The answer they need to guess
                            "air_date": clue.air_date.isoformat()
                            if clue.air_date
                            else None,
                            "notes": clue.notes,
                        }
                    )

                # Sort clues by value (200, 400, 600, 800, 1000)
                clues_list.sort(key=lambda x: x["clue_value"])
                round_data[category] = clues_list

            return round_data

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Error fetching round data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/answer")
async def submit_answer(request: Request):
    try:
        # Parse request body
        body = await request.json()
        if not body.get("clue_id") or not body.get("user_answer"):
            raise HTTPException(
                status_code=400, detail="Both clue_id and user_answer are required"
            )

        clue_id = body["clue_id"]
        user_answer = body["user_answer"]

        # Create session
        session = Session(engine, future=True)
        try:
            # Get correct answer from database
            stmt = select(Clue).where(Clue.id == clue_id)
            clue = session.scalar(stmt)
            if not clue:
                raise HTTPException(status_code=404, detail="Clue not found")

            # Calculate similarity using thefuzz
            correct_answer = clue.correct_answer
            similarity = fuzz.partial_token_set_ratio(
                user_answer.lower(), correct_answer.lower()
            )

            return {
                "clue_id": clue_id,
                "similarity": similarity,
                "correct_answer": correct_answer,
                "user_answer": user_answer,
            }

        finally:
            session.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing answer: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
