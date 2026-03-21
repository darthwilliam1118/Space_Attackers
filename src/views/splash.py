"""Splash screen — title card shown on launch."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

from src.ui.text_utils import FONT_MAIN, FONT_THIN, centered_text


class SplashView(arcade.View):
    """Displays the game title and waits for any key to proceed to MAIN."""

    TITLE = "Space Attackers!"
    PROMPT = "Press any key to continue..."

    _AUTO_ADVANCE = 5.0

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__()
        self._manager = manager
        self._elapsed: float = 0.0
        self._title_text: Optional[arcade.Text] = None
        self._prompt_text: Optional[arcade.Text] = None

    def on_show_view(self) -> None:
        self.window.music.play("ending")  # type: ignore[attr-defined]
        w, h = self.window.width, self.window.height
        self._title_text = centered_text(
            self.TITLE, w, h // 2 + 40,
            font_size=64, color=arcade.color.YELLOW, font_name=FONT_MAIN, bold=True,
        )
        self._prompt_text = centered_text(
            self.PROMPT, w, 40,
            font_size=18, color=arcade.color.WHITE, font_name=FONT_THIN,
        )

    def on_update(self, delta_time: float) -> None:
        self.window.star_field.update(delta_time)  # type: ignore[attr-defined]
        self._elapsed += delta_time
        if self._elapsed >= self._AUTO_ADVANCE:
            self._go_to_main()

    def _go_to_main(self) -> None:
        from src.state import GameState
        self._manager.transition(GameState.MAIN)

    def on_draw(self) -> None:
        self.clear()
        self.window.background.draw()  # type: ignore[attr-defined]
        self.window.star_field.draw()  # type: ignore[attr-defined]
        if self._title_text:
            self._title_text.draw()
        if self._prompt_text:
            self._prompt_text.draw()

    def on_key_press(self, key: int, modifiers: int) -> None:
        self._go_to_main()
