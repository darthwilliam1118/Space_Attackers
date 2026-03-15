"""Main menu — cycles pages and routes key presses to game states."""

from __future__ import annotations

from typing import TYPE_CHECKING

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

_PAGES = ["LEADERBOARD", "INSTRUCTIONS", "DEMO"]
_CYCLE_INTERVAL = 4.0  # seconds per page


class MainMenuView(arcade.View):
    """Cycles leaderboard / instructions / demo pages.

    Keys:
        1 → 1-player game
        2 → 2-player game
        C → game config
        X → exit
    """

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__()
        self._manager = manager
        self._page_index: int = 0
        self._elapsed: float = 0.0

    # ------------------------------------------------------------------
    # Arcade callbacks
    # ------------------------------------------------------------------

    def on_update(self, delta_time: float) -> None:
        self._elapsed += delta_time
        if self._elapsed >= _CYCLE_INTERVAL:
            self._elapsed = 0.0
            self._page_index = (self._page_index + 1) % len(_PAGES)

    def on_draw(self) -> None:
        self.clear()
        width = self.window.width
        height = self.window.height
        page = _PAGES[self._page_index]

        arcade.draw_text(
            "Space Attackers!",
            width / 2,
            height - 80,
            arcade.color.YELLOW,
            font_size=48,
            anchor_x="center",
            bold=True,
        )

        arcade.draw_text(
            f"[ {page} ]",
            width / 2,
            height / 2,
            arcade.color.CYAN,
            font_size=28,
            anchor_x="center",
            anchor_y="center",
        )

        hints = "1 = 1 Player    2 = 2 Players    C = Config    X = Exit"
        arcade.draw_text(
            hints,
            width / 2,
            40,
            arcade.color.LIGHT_GRAY,
            font_size=14,
            anchor_x="center",
            anchor_y="center",
        )

    def on_key_press(self, key: int, modifiers: int) -> None:
        from src.state import GameState

        match key:
            case arcade.key.KEY_1:
                cfg = self._manager.context.get("config")
                self._manager.transition(GameState.GAME_INIT, num_players=1, config=cfg)
            case arcade.key.KEY_2:
                cfg = self._manager.context.get("config")
                self._manager.transition(GameState.GAME_INIT, num_players=2, config=cfg)
            case arcade.key.C:
                self._manager.transition(GameState.GAME_CONFIG)
            case arcade.key.X:
                self._manager.transition(GameState.EXIT)
