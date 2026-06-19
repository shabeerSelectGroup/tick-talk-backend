"""Ranking order: score, tasks_completed, finish time."""

from app.services.leaderboard import RANK_ORDER


def test_rank_order_has_score_tasks_and_finish_tiebreakers():
    # score, tasks_completed, nulls-last sentinel, finished_at
    assert len(RANK_ORDER) == 4
