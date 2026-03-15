"""GAME_OVER screen — shows final scores, routes to SCORE_ENTRY or MAIN."""

from __future__ import annotations

from typing import TYPE_CHECKING

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

_DISPLAY_DURATION = 4.0
_LEADERBOARD_TOP_N = 10
_QUALIFY_SCORE = 0  # placeholder — any score qualifies until leaderboard is real


class GameOverView(arcade.View):
    """Displays final scores. Routes to SCORE_ENTRY if a score qualifies."""

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__()
        self._manager = manager
        self._elapsed: float = 0.0

    def _qualifies_for_leaderboard(self) -> bool:
        players = self._manager.context.get("players", [])
        return any(p.score > _QUALIFY_SCORE for p in players)

    def on_update(self, delta_time: float) -> None:
        self._elapsed += delta_time
        if self._elapsed >= _DISPLAY_DURATION:
            from src.state import GameState
            next_state = (
                GameState.SCORE_ENTRY
                if self._qualifies_for_leaderboard()
                else GameState.MAIN
            )
            self._manager.transition(next_state)

    def on_draw(self) -> None:
        self.clear()
        width = self.window.width
        height = self.window.height

        arcade.draw_text(
            "GAME OVER",
            width / 2,
            height / 2 + 80,
            arcade.color.RED,
            font_size=56,
            anchor_x="center",
            bold=True,
        )

        players = self._manager.context.get("players", [])
        for i, player in enumerate(players):
            arcade.draw_text(
                f"Player {player.player_num}:  {player.score}",
                width / 2,
                height / 2 - 10 - i * 35,
                arcade.color.WHITE,
                font_size=24,
                anchor_x="center",
            )
