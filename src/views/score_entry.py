"""SCORE_ENTRY stub — displays HIGH SCORES message, then returns to MAIN."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

from src.ui.text_utils import FONT_MAIN, FONT_THIN, centered_text

_DISPLAY_DURATION = 5.0


class ScoreEntryView(arcade.View):
    """Stub: shows HIGH SCORES for 5 seconds then transitions to MAIN."""

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__()
        self._manager = manager
        self._elapsed: float = 0.0

        self._title_text: Optional[arcade.Text] = None
        self._subtitle_text: Optional[arcade.Text] = None

    def on_show_view(self) -> None:
        self.window.music.play("ending")  # type: ignore[attr-defined]
        w, h = self.window.width, self.window.height
        self._title_text = centered_text(
            "HIGH SCORES", w, h // 2 + 20,
            font_size=52, color=arcade.color.GOLD, font_name=FONT_MAIN, bold=True,
        )
        self._subtitle_text = centered_text(
            "(full leaderboard coming soon)", w, h // 2 - 40,
            font_size=16, color=(180, 180, 180, 255), font_name=FONT_THIN,
        )

    def on_update(self, delta_time: float) -> None:
        self.window.star_field.update(delta_time)  # type: ignore[attr-defined]
        self._elapsed += delta_time
        if self._elapsed >= _DISPLAY_DURATION:
            from src.state import GameState
            self._manager.transition(GameState.MAIN)

    def on_draw(self) -> None:
        self.clear()
        self.window.background.draw()  # type: ignore[attr-defined]
        self.window.star_field.draw()  # type: ignore[attr-defined]
        if self._title_text:
            self._title_text.draw()
        if self._subtitle_text:
            self._subtitle_text.draw()
