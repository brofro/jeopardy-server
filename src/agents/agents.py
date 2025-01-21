import os
import json
from typing import Literal, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from loguru import logger
from dotenv import load_dotenv, get_key

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(env_path)

# Set OpenAI API key for OpenRouter using dotenv's get_key
api_key = get_key(env_path, "OPENROUTER_API_KEY")
if not api_key:
    logger.error("OPENROUTER_API_KEY environment variable is not set")
    raise ValueError("OPENROUTER_API_KEY environment variable is required")


class Judgement(BaseModel):
    correct: bool
    feedback: str


class JudgeContext(BaseModel):
    category: str
    clue: str
    comments: str
    correct_answer: str
    user_answer: str


def get_judge_agent():
    agent = Agent(
        system_prompt="""
        You are a Jeopardy game judge. Evaluate answers based on what you know about Jeopardy rules. We SHOULD NOT care about the phrasing of the answer (ie. answers do not need to be in form of a question)",
        Spelling or capitalization shouldn't matter if the answer is close enough to being correct (unless the category requires it)
        Only provide feedback on incorrect answers.
        NEVER DISCLOSE THE CORRECT ANSWER IN THE FEEDBACK.
        """,
        result_type=Judgement,
        model=OpenAIModel(
            model_name="google/gemini-flash-1.5",
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        ),
        deps_type=JudgeContext,
    )

    @agent.system_prompt
    def add_category_prompt(ctx: RunContext[JudgeContext]) -> str:
        return f"The category is: {ctx.deps.category}"

    @agent.system_prompt
    def add_clue_prompt(ctx: RunContext[JudgeContext]) -> str:
        return f"The clue is: {ctx.deps.clue}"

    @agent.system_prompt
    def add_correct_answer_prompt(ctx: RunContext[JudgeContext]) -> str:
        return f"The correct answer is: {ctx.deps.correct_answer}"

    @agent.system_prompt
    def add_user_answer_prompt(ctx: RunContext[JudgeContext]) -> str:
        return f"The user answered: {ctx.deps.user_answer}"

    @agent.system_prompt
    def add_comments_prompt(ctx: RunContext[JudgeContext]) -> str:
        if ctx.deps.comments:
            return f"Additional context: {ctx.deps.comments}"
        return ""

    return agent


# Example usage
if __name__ == "__main__":
    # Create sample context
    context = JudgeContext(
        category="American History",
        clue="This was president during the Cuban Missle Crisis",
        comments="",
        correct_answer="John F. Kennedy",
        user_answer="JFK"
    )
    
    # Run the agent with context
    result = get_judge_agent().run_sync(
        "Please evaluate this answer",
        deps=context
    )
    
    print("Judgement:", result.data)
