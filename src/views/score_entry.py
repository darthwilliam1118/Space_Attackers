"""SCORE_ENTRY view — keyboard name entry and persistent leaderboard display."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from agf.high_scores import HighScoreTable, scores_path
from agf.views.score_entry import ScoreEntryView as _ScoreEntryViewBase

if TYPE_CHECKING:
    from src.state import GameStateManager


class ScoreEntryView(_ScoreEntryViewBase):
    """Routes to GameState.MAIN after entries are saved."""

    def __init__(self, manager: "GameStateManager") -> None:
        self._manager = manager
        super().__init__(on_complete=self._return_to_menu)

    def get_high_score_table(self) -> HighScoreTable:
        return self._manager.context.get("high_score_table") or HighScoreTable.load(scores_path())

    def get_all_players(self) -> Sequence:
        return self._manager.context.get("players", [])

    def on_table_saved(self, table: HighScoreTable) -> None:
        self._manager.context["high_score_table"] = table

    def _return_to_menu(self) -> None:
        from src.state import GameState

        self._manager.transition(GameState.MAIN)
