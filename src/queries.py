from sqlalchemy import select, func

from .models.models import Clue


def get_first_matching_category_by_name(category_name):
    return select(Clue.category).where(Clue.category == category_name).limit(1)


def get_random_categories_matching_round(round, num_categories):
    query = (
        select(Clue.category)
        .where(Clue.round == round)
        .group_by(Clue.category)
        .order_by(func.random())
        .limit(num_categories)
    )
    return query

def get_all_airdates_for_category_and_round(category, round):
    return (
        select(Clue.air_date)
        .where(Clue.category == category, Clue.round == round)
        .distinct()
        .order_by(Clue.air_date.desc())
    )

def get_clues_for_category_round_and_airdate(category, round, air_date):
    return (
        select(Clue)
        .where(
            Clue.category == category, 
            Clue.round == round, 
            Clue.air_date == air_date)
        .group_by(Clue.clue_value)
        .order_by(Clue.clue_value)
    )

def get_clue_by_id(clue_id):
    return select(Clue).where(Clue.id == clue_id)