# Jeopardy Game Backend

This repository contains the backend code for a Jeopardy game.

## Project Structure

The project is structured as follows:

- **`__init__.py`**:  Empty initialization files for proper Python package structure.
- **`.gitignore`**: Specifies files and directories to ignore for Git version control.
- **`pyproject.toml`**:  Project configuration file for build system and dependencies (likely using `poetry`).
- **`logs/`**: Directory to store log files generated during the game's execution.
- **`src/`**: Contains the source code for the game's logic.
    - **`__init__.py`**: Empty initialization file.
    - **`judge_special_rules.json`**: Defines special rules for judging answers in specific Jeopardy categories. These rules handle cases where standard answer evaluation might not be sufficient (e.g., rhyming answers, answers containing specific letters).
    - **`load_data.py`**: Loads Jeopardy clue data from a TSV file (`combined_season1-40.tsv`) into a SQLite database using SQLAlchemy.  Handles error conditions during data loading.
    - **`main.py`**: This file implements the main FastAPI application. It handles routing, database interactions (using SQLAlchemy and SQLite), and manages the game logic.  It includes endpoints for fetching Jeopardy clues (`/round/{round_value}`) and judging user answers (`/answer`).
    - **`queries.py`**: Contains SQLAlchemy queries for retrieving Jeopardy clue data. Functions are provided to fetch categories, clues based on round and air date, and individual clues by ID.
    - **`agents/`**: Contains code for different game agents.
        - **`__init__.py`**: Empty initialization file.
        - **`agents.py`**: Defines a Pydantic agent that uses the OpenRouter API (with a Gemini model) to judge Jeopardy answers.  It defines data models for the judgement and context, and includes prompts to provide the agent with the necessary information for evaluation. The OpenRouter API key is loaded from a .env file.
        - **`judge.py`**:  This file could not be accessed for analysis.  Further investigation is needed.
    - **`models/`**: Contains data models for the game.
        - **`__init__.py`**: Empty initialization file.
        - **`models.py`**: Defines a SQLAlchemy model `Clue` representing a Jeopardy clue. The model includes fields for round, clue value, whether it's a daily double, category, comments, clue text, correct answer, air date, and notes.
- **`tests/`**: Contains unit tests for the game's logic.
    - **`test_models.py`**: Contains unit tests for the `Clue` model using pytest.  Tests verify the creation and saving of `Clue` objects to the database.


## Functionality Summary

- **`src/main.py`**: This file implements the main FastAPI application. It handles routing, database interactions (using SQLAlchemy and SQLite), and manages the game logic.  It includes two main endpoints:
    - `/round/{round_value}`: This endpoint fetches Jeopardy clues for a given round (1 or 2). It accepts an optional `category` parameter to filter the results.  The response includes a list of clues for each category, sorted by clue value.  Error handling is included for invalid round values and missing categories.
    - `/answer`: This endpoint handles user answer submissions. It receives the `clue_id` and `user_answer` and uses an AI agent to judge the answer's correctness. The response includes whether the answer was correct, feedback (if incorrect), the user's answer, and the correct answer.  Error handling is included for missing data and errors from the AI agent.

- **`src/load_data.py`**: Loads Jeopardy clue data from a TSV file (`combined_season1-40.tsv`) into a SQLite database using SQLAlchemy.  Handles error conditions during data loading.

- **`src/agents/agents.py`**: Defines a Pydantic agent that uses the OpenRouter API (with a Gemini model) to judge Jeopardy answers.  It defines data models for the judgement and context, and includes prompts to provide the agent with the necessary information for evaluation. The OpenRouter API key is loaded from a .env file.

- **`src/agents/judge.py`**:  This file could not be accessed for analysis.  Further investigation is needed.

- **`src/models/models.py`**: Defines a SQLAlchemy model `Clue` representing a Jeopardy clue. The model includes fields for round, clue value, whether it's a daily double, category, comments, clue text, correct answer, air date, and notes.

- **`src/queries.py`**: Contains SQLAlchemy queries for retrieving Jeopardy clue data. Functions are provided to fetch categories, clues based on round and air date, and individual clues by ID.

- **`src/hello.py`**: A simple script that prints "Hello from backend!". Likely a placeholder or test script.

- **`src/judge_prompt_template.json`**: Contains a JSON template for prompts used by the judge AI agent. It includes placeholders for category, clue, correct answer, submitted answer, comments, and special rules.  It also provides examples of how the judge should respond.

- **`src/judge_special_rules.json`**: Defines special rules for judging answers in specific Jeopardy categories.  These rules handle cases where standard answer evaluation might not be sufficient (e.g., rhyming answers, answers containing specific letters).

- **`tests/test_models.py`**: Contains unit tests for the `Clue` model using pytest. Tests verify the creation and saving of `Clue` objects to the database.
