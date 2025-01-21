import os
import sys
from typing import Dict, List, Optional, Any
from loguru import logger
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from .agents.agents import JudgeContext, get_judge_agent
from .models.models import Base, Clue
from .queries import (
    get_all_airdates_for_category_and_round,
    get_clue_by_id,
    get_clues_for_category_round_and_airdate,
    get_first_matching_category_by_name,
    get_random_categories_matching_round
)

app = FastAPI()

# Update log file path to use absolute path
log_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "logs", "app.log")
)
os.makedirs(os.path.dirname(log_path), exist_ok=True)

logger.remove()  # Remove default handler
logger.add(
    log_path,
    rotation="250 KB",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}",
    backtrace=True,
    diagnose=True,
)
logger.add(sys.stderr, level="INFO")


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
logger.info("Database path {}", db_path)

# Database setup
db_engine = create_engine(f"sqlite:///{db_path}", echo=True)  # Enable SQL logging
Base.metadata.bind = db_engine


# Create tables if they don't exist
Base.metadata.create_all(db_engine)


@app.get("/", response_model=Dict[str, str])
async def root() -> Dict[str, str]:
    return {"message": "Hello, World!"}


@app.get("/round/{round_value}", response_model=Dict[str, List[Dict[str, Any]]])
async def get_round(round_value: int, category: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    if round_value not in [1, 2]:
        raise HTTPException(
            status_code=400,
            detail="Round value must be 1 (Single Jeopardy) or 2 (Double Jeopardy)",
        )

    try:
        # Create session with immediate execution mode
        db_session = Session(db_engine, future=True)
        try:
            logger.info("Fetching categories for round {}", round_value)
            # Get 6 random categories for this round using GROUP BY for uniqueness
            categories_query = (get_random_categories_matching_round(round_value, 6) if not category 
                                else get_random_categories_matching_round(round_value, 5))
            categories = db_session.scalars(categories_query).all()

            # If specific category requested, ensure it's included
            if category:
                # Verify category exists
                category_exists = db_session.scalar(get_first_matching_category_by_name(category))
                if not category_exists:
                    raise HTTPException(
                        status_code=404, detail=f"Category '{category}' not found"
                    )

                # Add the requested category and ensure we have exactly 6 unique categories
                categories = [category] + [c for c in categories if c != category][:5]
            logger.info("Found {} random categories: {}", len(categories), categories)

            if not categories:
                logger.warning("No categories found")
                raise HTTPException(
                    status_code=404, detail="No categories found for this round"
                )

            round_data = {}
            for category in categories:
                logger.info("Fetching clues for category: {}", category)

                # Get all air dates for this category and round
                air_dates = db_session.scalars(
                    get_all_airdates_for_category_and_round(category, round_value)
                ).all()

                #TODO: Right now this will terminate with the first airdate that has 5 clues.
                #We should instead pick a random airdate and keep trying until we have 5 clues.
                clues = []
                for air_date in air_dates:
                    clues = db_session.scalars(get_clues_for_category_round_and_airdate(category, round_value, air_date)).all()

                    if len(clues) == 5:
                        break

                if len(clues) != 5:
                    # TODO: Add logic to fetch new random category if we can't find 5 for this category
                    logger.error(
                        "Could not find 5 clues for category {} with matching air date",
                        category,
                    )
                logger.info("Found {} clues for category {}", len(clues), category)

                # Convert SQLAlchemy objects to dicts and sort by clue_value
                clues_list = []
                for clue in clues:
                    # Ensure we have a proper Clue object
                    if not hasattr(clue, "id"):
                        clue = db_session.merge(clue)
                    clues_list.append(
                        {
                            "id": clue.id,
                            "clue_value": clue.clue_value,
                            "is_daily_double": clue.is_daily_double,
                            "clue_text": clue.clue_text,  # The clue/question shown to player
                            "correct_answer": clue.correct_answer,  # The answer they need to guess
                            "air_date": clue.air_date.isoformat(),
                            "notes": clue.notes,
                        }
                    )

                # Sort clues by value (200, 400, 600, 800, 1000)
                clues_list.sort(key=lambda x: x["clue_value"])
                round_data[category] = clues_list

            return round_data

        finally:
            db_session.close()

    except Exception as e:
        logger.error("Error fetching round data: {}", e)
        raise HTTPException(status_code=500, detail="Internal server error")

judge_agent_singleton = get_judge_agent()
@app.post("/answer", response_model=Dict[str, Any])
async def submit_answer(request: Request) -> Dict[str, Any]:
    """
    Submit a user's answer for judging.

    Request body must include:
    - clue_id: ID of the clue being answered
    - user_answer: The user's submitted answer
    
    Returns:
        Dict containing:
        - correct: bool
        - try_again: bool
        - feedback: str
        - user_answer: str
        - correct_answer: str
    """
    try:
        # Parse request body
        body = await request.json()
        logger.debug("Received answer submission: {}", body)

        # Validate required fields
        if not body.get("clue_id"):
            raise HTTPException(status_code=400, detail="clue_id is required")
        if not body.get("user_answer"):
            raise HTTPException(status_code=400, detail="user_answer is required")

        clue_id = body["clue_id"]
        user_answer = body["user_answer"]

        # Create session
        session = Session(db_engine, future=True)
        try:
            # Get clue data from database
            clue = session.scalar(get_clue_by_id(clue_id))
            if not clue:
                logger.warning("Clue not found: id={}", clue_id)
                raise HTTPException(status_code=404, detail="Clue not found")

            logger.info(
                "Processing answer for clue_id={}: category='{}', clue='{}', correct_answer='{}', user_answer='{}'",
                clue_id,
                clue.category,
                clue.clue_text,
                clue.correct_answer,
                user_answer,
            )

            try:
                # Create judge context
                judge_context = JudgeContext(
                    category=clue.category,
                    clue=clue.clue_text,
                    comments=clue.notes if clue.comments else "",
                    correct_answer=clue.correct_answer,
                    user_answer=user_answer,
                )

                # Get judgement from AI agent
                logger.debug("Calling judge agent with context: {}", judge_context)
                judge_agent = judge_agent_singleton
                judgement = await judge_agent.run(
                    "Please evaluate this answer", deps=judge_context
                )
                logger.debug("Received judgement response: {}", judgement)

                # Convert judgement to response format
                response = {
                    "correct": judgement.data.correct,
                    "feedback": judgement.data.feedback,
                    "user_answer": user_answer,
                    "correct_answer": clue.correct_answer,
                }
            except Exception as e:
                logger.error("Error from judge agent: {}", str(e))
                if hasattr(e, "__dict__"):
                    logger.error("Full error details: {}", e.__dict__)
                raise

            logger.info("Answer judged: clue_id={}, result={}", clue_id, response)
            return response

        finally:
            session.close()

    except HTTPException:
        raise
    except ValueError as e:
        logger.error("Invalid request data: {}", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error processing answer: {}", str(e))
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your answer",
        )
