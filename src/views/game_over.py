"""GAME_OVER screen — shows final scores, routes to SCORE_ENTRY or MAIN."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from agf.high_scores import HighScoreTable, scores_path
from agf.views.game_over import GameOverView as _GameOverViewBase

if TYPE_CHECKING:
    from src.state import GameStateManager


class GameOverView(_GameOverViewBase):
    """Displays final scores. Routes to SCORE_ENTRY if a score qualifies."""

    def __init__(self, manager: "GameStateManager") -> None:
        self._manager = manager
        super().__init__(on_complete=self._advance)

    def get_players(self) -> Sequence:
        return self._manager.context.get("players", [])

    def _qualifies_for_leaderboard(self) -> bool:
        table = HighScoreTable.load(scores_path())
        self._manager.context["high_score_table"] = table
        players = self._manager.context.get("players", [])
        return any(table.qualifies(p.score) for p in players)

    def _advance(self) -> None:
        from src.state import GameState

        next_state = GameState.SCORE_ENTRY if self._qualifies_for_leaderboard() else GameState.MAIN
        self._manager.transition(next_state)
