"""SCORE_ENTRY stub — displays HIGH SCORES message, then returns to MAIN."""

from __future__ import annotations

from typing import TYPE_CHECKING

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

_DISPLAY_DURATION = 5.0


class ScoreEntryView(arcade.View):
    """Stub: shows HIGH SCORES for 5 seconds then transitions to MAIN."""

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__()
        self._manager = manager
        self._elapsed: float = 0.0

    def on_update(self, delta_time: float) -> None:
        self._elapsed += delta_time
        if self._elapsed >= _DISPLAY_DURATION:
            from src.state import GameState
            self._manager.transition(GameState.MAIN)

    def on_draw(self) -> None:
        self.clear()
        width = self.window.width
        height = self.window.height

        arcade.draw_text(
            "HIGH SCORES",
            width / 2,
            height / 2 + 20,
            arcade.color.GOLD,
            font_size=52,
            anchor_x="center",
            bold=True,
        )

        arcade.draw_text(
            "(full leaderboard coming soon)",
            width / 2,
            height / 2 - 40,
            arcade.color.LIGHT_GRAY,
            font_size=16,
            anchor_x="center",
        )
