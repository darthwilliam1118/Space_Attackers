"""LEVEL_COMPLETE screen — awards bonus, shows lives, advances level."""

from __future__ import annotations

from typing import TYPE_CHECKING

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

_LEVEL_BONUS = 1000
_DISPLAY_DURATION = 3.0


class LevelCompleteView(arcade.View):
    """Awards level bonus, displays remaining lives, then continues."""

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__()
        self._manager = manager
        self._elapsed: float = 0.0
        self._apply_bonus()

    def _apply_bonus(self) -> None:
        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        if players:
            player = players[idx]
            player.score += _LEVEL_BONUS
            player.current_level += 1
            player.level_snapshot = None

    def on_update(self, delta_time: float) -> None:
        self._elapsed += delta_time
        if self._elapsed >= _DISPLAY_DURATION:
            from src.state import GameState
            self._manager.transition(GameState.SET_ACTIVE_PLAYER)

    def on_draw(self) -> None:
        self.clear()
        width = self.window.width
        height = self.window.height

        arcade.draw_text(
            "LEVEL COMPLETE!",
            width / 2,
            height / 2 + 80,
            arcade.color.GREEN,
            font_size=48,
            anchor_x="center",
            bold=True,
        )

        arcade.draw_text(
            f"Bonus: +{_LEVEL_BONUS}",
            width / 2,
            height / 2 + 20,
            arcade.color.YELLOW,
            font_size=28,
            anchor_x="center",
        )

        players = self._manager.context.get("players", [])
        alive = [p for p in players if p.is_alive]
        lines = [f"Player {p.player_num}:  {p.lives} lives   Score: {p.score}" for p in alive]
        for i, line in enumerate(lines):
            arcade.draw_text(
                line,
                width / 2,
                height / 2 - 30 - i * 30,
                arcade.color.WHITE,
                font_size=18,
                anchor_x="center",
            )
