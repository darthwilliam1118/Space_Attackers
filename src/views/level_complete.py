"""LEVEL_COMPLETE screen — awards bonus, shows lives, advances level."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

from src.ui.text_utils import FONT_MAIN, FONT_THIN, centered_text

_LEVEL_BONUS = 1000
_DISPLAY_DURATION = 3.0
_GET_READY_DELAY = 1.0


class LevelCompleteView(arcade.View):
    """Awards level bonus, displays remaining lives, then continues."""

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__()
        self._manager = manager
        self._elapsed: float = 0.0
        self._apply_bonus()

        self._title_text: Optional[arcade.Text] = None
        self._bonus_text: Optional[arcade.Text] = None
        self._player_texts: list[arcade.Text] = []
        self._get_ready_text: Optional[arcade.Text] = None

    def _apply_bonus(self) -> None:
        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        if players:
            player = players[idx]
            player.score += _LEVEL_BONUS
            player.current_level += 1
            player.level_snapshot = None

    def on_show_view(self) -> None:
        self.window.music.play("ending")  # type: ignore[attr-defined]
        w, h = self.window.width, self.window.height
        self._title_text = centered_text(
            "LEVEL COMPLETE!", w, h // 2 + 100,
            font_size=48, color=arcade.color.GREEN, font_name=FONT_MAIN, bold=True,
        )

        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        level = players[idx].current_level if players else 1

        self._bonus_text = centered_text(
            f"LEVEL {level}    Bonus: +{_LEVEL_BONUS}", w, h // 2 + 40,
            font_size=24, color=arcade.color.YELLOW, font_name=FONT_MAIN,
        )

        alive = [p for p in players if p.is_alive]
        self._player_texts = [
            centered_text(
                f"Player {p.player_num}:  {p.lives} lives   Score: {p.score}",
                w, h // 2 - 10 - i * 32,
                font_size=18, color=arcade.color.WHITE, font_name=FONT_THIN,
            )
            for i, p in enumerate(alive)
        ]

        self._get_ready_text = centered_text(
            "GET READY...", w, h // 2 - 90,
            font_size=16, color=(255, 255, 255, 0), font_name=FONT_MAIN,
        )

    def on_update(self, delta_time: float) -> None:
        self.window.star_field.update(delta_time)  # type: ignore[attr-defined]
        self._elapsed += delta_time

        if self._get_ready_text is not None and self._elapsed >= _GET_READY_DELAY:
            self._get_ready_text.color = arcade.color.WHITE

        if self._elapsed >= _DISPLAY_DURATION:
            from src.state import GameState
            self._manager.transition(GameState.SET_ACTIVE_PLAYER)

    def on_draw(self) -> None:
        self.clear()
        self.window.background.draw()  # type: ignore[attr-defined]
        self.window.star_field.draw()  # type: ignore[attr-defined]
        if self._title_text:
            self._title_text.draw()
        if self._bonus_text:
            self._bonus_text.draw()
        for t in self._player_texts:
            t.draw()
        if self._get_ready_text:
            self._get_ready_text.draw()
