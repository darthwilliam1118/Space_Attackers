"""Main menu — cycles pages and routes key presses to game states."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

from src.ui.text_utils import FONT_MAIN, FONT_THIN, centered_text

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
        self._prompt_elapsed: float = 0.0

        self._title_text: Optional[arcade.Text] = None
        self._subtitle_text: Optional[arcade.Text] = None
        self._start_prompt: Optional[arcade.Text] = None
        self._hints_text: Optional[arcade.Text] = None

    # ------------------------------------------------------------------
    # Arcade callbacks
    # ------------------------------------------------------------------

    def on_show_view(self) -> None:
        self.window.music.play("ending")  # type: ignore[attr-defined]
        w, h = self.window.width, self.window.height
        self._title_text = centered_text(
            "Space Attackers!", w, int(h * 0.75),
            font_size=48, color=arcade.color.YELLOW, font_name=FONT_MAIN, bold=True,
        )
        self._subtitle_text = centered_text(
            f"[ {_PAGES[self._page_index]} ]", w, h // 2,
            font_size=18, color=arcade.color.CYAN, font_name=FONT_THIN,
        )
        self._start_prompt = centered_text(
            "PRESS 1 OR 2 TO START", w, 56,
            font_size=16, color=arcade.color.WHITE, font_name=FONT_MAIN,
        )
        self._hints_text = centered_text(
            "C — CONFIG    X — EXIT", w, 24,
            font_size=14, color=(160, 160, 160, 255), font_name=FONT_THIN,
        )

    def on_update(self, delta_time: float) -> None:
        self.window.star_field.update(delta_time)  # type: ignore[attr-defined]

        self._elapsed += delta_time
        if self._elapsed >= _CYCLE_INTERVAL:
            self._elapsed = 0.0
            self._page_index = (self._page_index + 1) % len(_PAGES)
            if self._subtitle_text is not None:
                self._subtitle_text.text = f"[ {_PAGES[self._page_index]} ]"

        # Pulsing alpha on start prompt
        self._prompt_elapsed += delta_time
        if self._start_prompt is not None:
            alpha = int(abs(math.sin(self._prompt_elapsed * 3.0)) * 255)
            self._start_prompt.color = (255, 255, 255, alpha)

    def on_draw(self) -> None:
        self.clear()
        self.window.background.draw()  # type: ignore[attr-defined]
        self.window.star_field.draw()  # type: ignore[attr-defined]
        if self._title_text:
            self._title_text.draw()
        if self._subtitle_text:
            self._subtitle_text.draw()
        if self._start_prompt:
            self._start_prompt.draw()
        if self._hints_text:
            self._hints_text.draw()

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
