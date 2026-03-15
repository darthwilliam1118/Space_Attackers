"""Splash screen — title card shown on launch."""

from __future__ import annotations

from typing import TYPE_CHECKING

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager


class SplashView(arcade.View):
    """Displays the game title and waits for any key to proceed to MAIN."""

    TITLE = "Space Attackers!"
    PROMPT = "Press any key to continue..."

    _AUTO_ADVANCE = 5.0

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__()
        self._manager = manager
        self._elapsed: float = 0.0

    def on_update(self, delta_time: float) -> None:
        self._elapsed += delta_time
        if self._elapsed >= self._AUTO_ADVANCE:
            self._go_to_main()

    def _go_to_main(self) -> None:
        from src.state import GameState
        self._manager.transition(GameState.MAIN)

    def on_draw(self) -> None:
        self.clear()
        width = self.window.width
        height = self.window.height

        arcade.draw_text(
            self.TITLE,
            width / 2,
            height / 2 + 40,
            arcade.color.YELLOW,
            font_size=64,
            anchor_x="center",
            anchor_y="center",
            bold=True,
        )

        arcade.draw_text(
            self.PROMPT,
            width / 2,
            40,
            arcade.color.WHITE,
            font_size=18,
            anchor_x="center",
            anchor_y="center",
        )

    def on_key_press(self, key: int, modifiers: int) -> None:
        self._go_to_main()
