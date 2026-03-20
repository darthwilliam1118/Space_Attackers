"""HUD — score, level, and lives display for RUN_LEVEL.

All text objects are created once and their .text / .color properties
are updated only when values change, avoiding per-frame texture allocation.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import arcade

from src.player_state import PlayerState
from src.ui.text_utils import FONT_MAIN

_WHITE: tuple[int, int, int, int] = (255, 255, 255, 255)
_MUTED: tuple[int, int, int, int] = (128, 128, 128, 255)
_FONT_SIZE = 16


def _default_factory(**kwargs: Any) -> arcade.Text:
    return arcade.Text(**kwargs)


class HUD:
    """Renders score, level, and lives for 1- or 2-player mode.

    Pass *_text_factory* to inject a fake text constructor in tests.
    """

    def __init__(
        self,
        window_width: int,
        window_height: int,
        num_players: int,
        _text_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        factory = _text_factory if _text_factory is not None else _default_factory
        self._num_players = num_players
        y_top = window_height - 24

        if num_players == 1:
            self._score = factory(
                text="SCORE: 000000",
                x=16, y=y_top,
                color=_WHITE, font_size=_FONT_SIZE,
                font_name=FONT_MAIN, anchor_x="left", anchor_y="center",
            )
            self._level = factory(
                text="LEVEL: 1",
                x=window_width / 2, y=y_top,
                color=_WHITE, font_size=_FONT_SIZE,
                font_name=FONT_MAIN, anchor_x="center", anchor_y="center",
            )
            self._lives = factory(
                text="LIVES: ♥",
                x=window_width - 16, y=y_top,
                color=_WHITE, font_size=_FONT_SIZE,
                font_name=FONT_MAIN, anchor_x="right", anchor_y="center",
            )
            self._texts = [self._score, self._level, self._lives]
        else:
            # Two-row 2P layout
            y_bot = window_height - 44
            self._p1_score = factory(
                text="P1: 000000",
                x=16, y=y_top,
                color=_WHITE, font_size=_FONT_SIZE,
                font_name=FONT_MAIN, anchor_x="left", anchor_y="center",
            )
            self._level = factory(
                text="LEVEL: 1",
                x=window_width / 2, y=y_top,
                color=_WHITE, font_size=_FONT_SIZE,
                font_name=FONT_MAIN, anchor_x="center", anchor_y="center",
            )
            self._p2_score = factory(
                text="P2: 000000",
                x=window_width - 16, y=y_top,
                color=_MUTED, font_size=_FONT_SIZE,
                font_name=FONT_MAIN, anchor_x="right", anchor_y="center",
            )
            self._p1_lives = factory(
                text="LIVES: ♥",
                x=16, y=y_bot,
                color=_WHITE, font_size=_FONT_SIZE,
                font_name=FONT_MAIN, anchor_x="left", anchor_y="center",
            )
            self._p2_lives = factory(
                text="LIVES: ♥",
                x=window_width - 16, y=y_bot,
                color=_MUTED, font_size=_FONT_SIZE,
                font_name=FONT_MAIN, anchor_x="right", anchor_y="center",
            )
            self._texts = [
                self._p1_score, self._level, self._p2_score,
                self._p1_lives, self._p2_lives,
            ]

        # Cache: sentinel -1 forces first update to always write
        self._last_scores: list[int] = [-1, -1]
        self._last_lives: list[int] = [-1, -1]
        self._last_level: int = -1
        self._last_active: int = -1

    def update(
        self,
        player_states: list[PlayerState],
        active_player_idx: int,
        level: int,
    ) -> None:
        """Update text content only when values have changed."""
        if not player_states:
            return

        if self._num_players == 1:
            p = player_states[0]
            if p.score != self._last_scores[0]:
                self._score.text = f"SCORE: {p.score:06d}"
                self._last_scores[0] = p.score
            if level != self._last_level:
                self._level.text = f"LEVEL: {level}"
                self._last_level = level
            if p.lives != self._last_lives[0]:
                self._lives.text = "LIVES: " + "♥" * max(0, p.lives)
                self._last_lives[0] = p.lives
        else:
            # Resolve P1 and P2 objects (may not always be index 0/1)
            p1 = next((p for p in player_states if p.player_num == 1), None)
            p2 = next((p for p in player_states if p.player_num == 2), None)
            active_num = player_states[active_player_idx].player_num if player_states else 1

            if p1 is not None:
                c1 = _WHITE if active_num == 1 else _MUTED
                if p1.score != self._last_scores[0] or active_num != self._last_active:
                    self._p1_score.text = f"P1: {p1.score:06d}"
                    self._p1_score.color = c1
                    self._p1_lives.color = c1
                    self._last_scores[0] = p1.score
                if p1.lives != self._last_lives[0] or active_num != self._last_active:
                    self._p1_lives.text = "LIVES: " + "♥" * max(0, p1.lives)
                    self._last_lives[0] = p1.lives

            if p2 is not None:
                c2 = _WHITE if active_num == 2 else _MUTED
                if p2.score != self._last_scores[1] or active_num != self._last_active:
                    self._p2_score.text = f"P2: {p2.score:06d}"
                    self._p2_score.color = c2
                    self._p2_lives.color = c2
                    self._last_scores[1] = p2.score
                if p2.lives != self._last_lives[1] or active_num != self._last_active:
                    self._p2_lives.text = "LIVES: " + "♥" * max(0, p2.lives)
                    self._last_lives[1] = p2.lives

            if level != self._last_level:
                self._level.text = f"LEVEL: {level}"
                self._last_level = level

            self._last_active = active_num

    def draw(self) -> None:
        """Draw all HUD text objects."""
        for t in self._texts:
            t.draw()
