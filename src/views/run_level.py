"""RUN_LEVEL placeholder — countdown with W/L shortcuts until real gameplay."""

from __future__ import annotations

from typing import TYPE_CHECKING

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

_PLACEHOLDER_DURATION = 5.0


class RunLevelView(arcade.View):
    """Temporary placeholder for the main game loop.

    Displays a countdown. Press W to win the level, L to lose a life.
    """

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__()
        self._manager = manager
        self._elapsed: float = 0.0

    def on_update(self, delta_time: float) -> None:
        self._elapsed += delta_time
        if self._elapsed >= _PLACEHOLDER_DURATION:
            from src.state import GameState
            self._manager.transition(GameState.LEVEL_COMPLETE)

    def on_draw(self) -> None:
        self.clear()
        width = self.window.width
        height = self.window.height
        remaining = max(0.0, _PLACEHOLDER_DURATION - self._elapsed)

        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        if players:
            p = players[idx]
            player_label = f"Player {p.player_num}  Level {p.current_level}"
        else:
            player_label = "Player 1  Level 1"

        arcade.draw_text(
            f"{player_label} — (placeholder)",
            width / 2,
            height / 2 + 40,
            arcade.color.WHITE,
            font_size=24,
            anchor_x="center",
            anchor_y="center",
        )

        arcade.draw_text(
            f"Auto-advancing in {remaining:.1f}s",
            width / 2,
            height / 2 - 10,
            arcade.color.LIGHT_GRAY,
            font_size=18,
            anchor_x="center",
            anchor_y="center",
        )

        arcade.draw_text(
            "W = Level Complete    L = Player Killed",
            width / 2,
            40,
            arcade.color.YELLOW,
            font_size=14,
            anchor_x="center",
            anchor_y="center",
        )

    def on_key_press(self, key: int, modifiers: int) -> None:
        from src.state import GameState

        match key:
            case arcade.key.W:
                self._manager.transition(GameState.LEVEL_COMPLETE)
            case arcade.key.L:
                self._manager.transition(GameState.PLAYER_KILLED)
