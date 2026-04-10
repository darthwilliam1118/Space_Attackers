"""GAME_OVER screen — shows final scores, routes to SCORE_ENTRY or MAIN."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

from src.high_scores import HighScoreTable, scores_path
from src.ui.text_utils import FONT_MAIN, FONT_THIN, centered_text

_DISPLAY_DURATION = 4.0


class GameOverView(arcade.View):
    """Displays final scores. Routes to SCORE_ENTRY if a score qualifies."""

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__()
        self._manager = manager
        self._elapsed: float = 0.0
        self._flash_elapsed: float = 0.0

        self._title_text: Optional[arcade.Text] = None
        self._score_texts: list[arcade.Text] = []
        self._press_key_text: Optional[arcade.Text] = None

    def _qualifies_for_leaderboard(self) -> bool:
        table = HighScoreTable.load(scores_path())
        self._manager.context["high_score_table"] = table
        players = self._manager.context.get("players", [])
        return any(table.qualifies(p.score) for p in players)

    def on_show_view(self) -> None:
        self.window.music.play("ending")  # type: ignore[attr-defined]
        w, h = self.window.width, self.window.height
        self._title_text = centered_text(
            "GAME OVER",
            w,
            h // 2 + 100,
            font_size=48,
            color=arcade.color.RED,
            font_name=FONT_MAIN,
            bold=True,
        )

        players = self._manager.context.get("players", [])
        self._score_texts = [
            centered_text(
                f"Player {p.player_num}:  {p.score}",
                w,
                h // 2 + 20 - i * 36,
                font_size=24,
                color=arcade.color.WHITE,
                font_name=FONT_MAIN,
            )
            for i, p in enumerate(players)
        ]

        self._press_key_text = centered_text(
            "PRESS ANY KEY",
            w,
            h // 2 - 80,
            font_size=14,
            color=arcade.color.WHITE,
            font_name=FONT_THIN,
        )

    def on_update(self, delta_time: float) -> None:
        self.window.star_field.update(delta_time)  # type: ignore[attr-defined]

        # Flashing "PRESS ANY KEY"
        self._flash_elapsed += delta_time
        if self._press_key_text is not None:
            visible = int(self._flash_elapsed / 0.5) % 2 == 0
            self._press_key_text.color = (255, 255, 255, 255 if visible else 0)

        self._elapsed += delta_time
        if self._elapsed >= _DISPLAY_DURATION:
            from src.state import GameState

            next_state = (
                GameState.SCORE_ENTRY if self._qualifies_for_leaderboard() else GameState.MAIN
            )
            self._manager.transition(next_state)

    def on_draw(self) -> None:
        self.clear()
        self.window.background.draw()  # type: ignore[attr-defined]
        self.window.star_field.draw()  # type: ignore[attr-defined]
        if self._title_text:
            self._title_text.draw()
        for t in self._score_texts:
            t.draw()
        if self._press_key_text:
            self._press_key_text.draw()
