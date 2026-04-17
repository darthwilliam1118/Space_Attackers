"""LEVEL_COMPLETE screen — awards bonus, shows lives, advances level."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agf.views.level_complete import LevelCompleteView as _LevelCompleteViewBase

if TYPE_CHECKING:
    from src.state import GameStateManager

_LEVEL_BONUS = 1000


class LevelCompleteView(_LevelCompleteViewBase):
    """Awards level bonus, displays remaining lives, then continues."""

    def __init__(self, manager: "GameStateManager") -> None:
        self._manager = manager
        super().__init__(on_complete=self._advance)

    def apply_bonus(self) -> None:
        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        if players:
            player = players[idx]
            player.score += _LEVEL_BONUS
            player.current_level += 1
            player.level_snapshot = None

    def build_bonus_text(self) -> str:
        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        level = players[idx].current_level if players else 1
        return f"LEVEL {level}    Bonus: +{_LEVEL_BONUS}"

    def build_player_rows(self) -> list[str]:
        players = self._manager.context.get("players", [])
        return [
            f"Player {p.player_num}:  {p.lives} lives   Score: {p.score}"
            for p in players
            if p.is_alive
        ]

    def _advance(self) -> None:
        from src.state import GameState

        self._manager.transition(GameState.SET_ACTIVE_PLAYER)
