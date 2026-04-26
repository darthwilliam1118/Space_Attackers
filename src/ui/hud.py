"""HUD — score, level, and lives display for RUN_LEVEL.

All text objects are created once and their .text / .color properties
are updated only when values change, avoiding per-frame texture allocation.
Life indicators are rendered as icon sprites loaded by setup_icons().
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import arcade
from agf.player_state import PlayerState
from agf.powerups.effect_base import PowerUpEffect
from agf.ui.hud_base import HUDBase
from agf.ui.text_utils import FONT_MAIN

_WHITE: tuple[int, int, int, int] = (255, 255, 255, 255)
_MUTED: tuple[int, int, int, int] = (128, 128, 128, 255)
_EFFECT_COLOR: tuple[int, int, int, int] = (180, 220, 255, 255)
_FONT_SIZE = 16
_EFFECT_FONT_SIZE = 12
_MAX_LIFE_ICONS = 6  # pre-allocated maximum; extras are hidden


def _default_factory(**kwargs: Any) -> arcade.Text:
    return arcade.Text(**kwargs)


class HUD(HUDBase):
    """Renders score, level, and lives for 1- or 2-player mode.

    Pass *_text_factory* to inject a fake text constructor in tests.
    Call setup_icons() from on_show_view() to attach life icon sprites.
    """

    def __init__(
        self,
        window_width: int,
        window_height: int,
        num_players: int,
        _text_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        super().__init__(window_width, window_height)
        factory = _text_factory if _text_factory is not None else _default_factory
        self._num_players = num_players
        y_top = window_height - 24

        if num_players == 1:
            self._score = factory(
                text="SCORE: 000000",
                x=16,
                y=y_top,
                color=_WHITE,
                font_size=_FONT_SIZE,
                font_name=FONT_MAIN,
                anchor_x="left",
                anchor_y="center",
            )
            self._level = factory(
                text="LEVEL: 1",
                x=window_width / 2,
                y=y_top,
                color=_WHITE,
                font_size=_FONT_SIZE,
                font_name=FONT_MAIN,
                anchor_x="center",
                anchor_y="center",
            )
            # x will be repositioned by setup_icons() to make room for icon sprites
            self._lives = factory(
                text="LIVES:",
                x=window_width - 16,
                y=y_top,
                color=_WHITE,
                font_size=_FONT_SIZE,
                font_name=FONT_MAIN,
                anchor_x="right",
                anchor_y="center",
            )
            self._texts = [self._score, self._level, self._lives]
        else:
            # Two-row 2P layout
            y_bot = window_height - 44
            self._p1_score = factory(
                text="P1: 000000",
                x=16,
                y=y_top,
                color=_WHITE,
                font_size=_FONT_SIZE,
                font_name=FONT_MAIN,
                anchor_x="left",
                anchor_y="center",
            )
            self._level = factory(
                text="LEVEL: 1",
                x=window_width / 2,
                y=y_top,
                color=_WHITE,
                font_size=_FONT_SIZE,
                font_name=FONT_MAIN,
                anchor_x="center",
                anchor_y="center",
            )
            self._p2_score = factory(
                text="P2: 000000",
                x=window_width - 16,
                y=y_top,
                color=_MUTED,
                font_size=_FONT_SIZE,
                font_name=FONT_MAIN,
                anchor_x="right",
                anchor_y="center",
            )
            self._p1_lives = factory(
                text="LIVES:",
                x=16,
                y=y_bot,
                color=_WHITE,
                font_size=_FONT_SIZE,
                font_name=FONT_MAIN,
                anchor_x="left",
                anchor_y="center",
            )
            # x will be repositioned by setup_icons()
            self._p2_lives = factory(
                text="LIVES:",
                x=window_width - 16,
                y=y_bot,
                color=_MUTED,
                font_size=_FONT_SIZE,
                font_name=FONT_MAIN,
                anchor_x="right",
                anchor_y="center",
            )
            self._texts = [
                self._p1_score,
                self._level,
                self._p2_score,
                self._p1_lives,
                self._p2_lives,
            ]

        # Cache: sentinel -1 forces first update to always write
        self._last_scores: list[int] = [-1, -1]
        self._last_lives: list[int] = [-1, -1]
        self._last_level: int = 0
        self._last_active: int = -1

        # Active effects line — single text below the score row
        effects_y = window_height - (44 if num_players == 1 else 64)
        self._effects_text = factory(
            text="",
            x=window_width / 2,
            y=effects_y,
            color=_EFFECT_COLOR,
            font_size=_EFFECT_FONT_SIZE,
            font_name=FONT_MAIN,
            anchor_x="center",
            anchor_y="center",
        )
        self._texts.append(self._effects_text)
        self._last_effects_text: str = ""

        # Life icon sprite lists — None until setup_icons() is called
        self._p1_icon_list: Optional[arcade.SpriteList] = None
        self._p2_icon_list: Optional[arcade.SpriteList] = None

    # ------------------------------------------------------------------
    # Icon setup (call from on_show_view after textures are available)
    # ------------------------------------------------------------------

    def setup_icons(
        self,
        tex_p1: arcade.Texture,
        tex_p2: Optional[arcade.Texture] = None,
        max_icons: int = _MAX_LIFE_ICONS,
    ) -> None:
        """Create life icon SpriteLists and reposition lives labels.

        tex_p1 is the P1 (blue) icon texture; tex_p2 is P2 (red).
        tex_p2 is only used in 2-player mode.
        Icons are pre-allocated up to max_icons; extras are hidden.
        """
        ICON_GAP = 2
        LABEL_GAP = 6
        RIGHT_MARGIN = 10

        def _make_list(
            tex: arcade.Texture, positions: list[tuple[float, float]]
        ) -> arcade.SpriteList:
            sl: arcade.SpriteList = arcade.SpriteList()
            for cx, cy in positions:
                sp = arcade.Sprite(tex)
                sp.center_x = cx
                sp.center_y = cy
                sp.visible = False
                sl.append(sp)
            return sl

        def _right_positions(iw: float, iy: float) -> list[tuple[float, float]]:
            """max_icons positions right-anchored to window_width - RIGHT_MARGIN."""
            result = []
            for i in range(max_icons):
                cx = (
                    self.window_width
                    - RIGHT_MARGIN
                    - iw / 2
                    - (max_icons - 1 - i) * (iw + ICON_GAP)
                )
                result.append((cx, iy))
            return result

        if self._num_players == 1:
            iw = float(tex_p1.width)
            iy = self.window_height - 24
            positions = _right_positions(iw, iy)
            # Reposition "LIVES:" label: right-anchored, left of leftmost icon
            self._lives.x = positions[0][0] - iw / 2 - LABEL_GAP
            self._p1_icon_list = _make_list(tex_p1, positions)
        else:
            iy = self.window_height - 44

            # P1 left side (blue): icons start immediately right of "LIVES:" label
            iw1 = float(tex_p1.width)
            label1_right = self._p1_lives.x + self._p1_lives.content_width
            positions1 = [
                (label1_right + LABEL_GAP + iw1 / 2 + i * (iw1 + ICON_GAP), iy)
                for i in range(max_icons)
            ]
            self._p1_icon_list = _make_list(tex_p1, positions1)

            # P2 right side (red): icons right-anchored, label repositioned left
            if tex_p2 is not None:
                iw2 = float(tex_p2.width)
                positions2 = _right_positions(iw2, iy)
                self._p2_lives.x = positions2[0][0] - iw2 / 2 - LABEL_GAP
                self._p2_icon_list = _make_list(tex_p2, positions2)

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------

    def update(
        self,
        player_states: list[PlayerState],
        active_player_idx: int,
        level: int,
        active_effects: Optional[list[PowerUpEffect]] = None,
    ) -> None:
        """Update text content and icon visibility only when values have changed."""
        self._update_effects(active_effects or [])
        if not player_states:
            return

        if self._num_players == 1:
            p = player_states[0]
            if p.score != self._last_scores[0]:
                self._score.text = f"SCORE: {p.score:06d}"
                self._last_scores[0] = p.score
            if level != self._last_level:
                if level == -2:
                    self._level.text = "BOSS BATTLE!"
                elif level < 0:
                    self._level.text = "METEOR STORM"
                else:
                    self._level.text = f"LEVEL: {level}"
                self._last_level = level
            if p.lives != self._last_lives[0]:
                self._last_lives[0] = p.lives
                self._set_icon_count(self._p1_icon_list, p.lives - 1)
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
                if p1.lives != self._last_lives[0]:
                    self._last_lives[0] = p1.lives
                    self._set_icon_count(self._p1_icon_list, p1.lives - 1)

            if p2 is not None:
                c2 = _WHITE if active_num == 2 else _MUTED
                if p2.score != self._last_scores[1] or active_num != self._last_active:
                    self._p2_score.text = f"P2: {p2.score:06d}"
                    self._p2_score.color = c2
                    self._p2_lives.color = c2
                    self._last_scores[1] = p2.score
                if p2.lives != self._last_lives[1]:
                    self._last_lives[1] = p2.lives
                    self._set_icon_count(self._p2_icon_list, p2.lives - 1)

            if level != self._last_level:
                if level == -2:
                    self._level.text = "BOSS BATTLE!"
                elif level < 0:
                    self._level.text = "METEOR STORM"
                else:
                    self._level.text = f"LEVEL: {level}"
                self._last_level = level

            self._last_active = active_num

    def draw(self) -> None:
        super().draw()
        if self._p1_icon_list is not None:
            self._p1_icon_list.draw()
        if self._p2_icon_list is not None:
            self._p2_icon_list.draw()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_icon_count(self, icon_list: Optional[arcade.SpriteList], count: int) -> None:
        if icon_list is None:
            return
        visible = max(0, count)
        for i, sprite in enumerate(icon_list):
            sprite.visible = i < visible

    def _update_effects(self, active_effects: list[PowerUpEffect]) -> None:
        """Render the active effects line, only rewriting on change."""
        parts: list[str] = []
        for effect in active_effects:
            label = effect.display_label
            if effect.remaining_duration > 0.0:
                parts.append(f"[{label} {effect.remaining_duration:.1f}s]")
            else:
                parts.append(f"[{label}]")
        text = "  ".join(parts)
        if text != self._last_effects_text:
            self._effects_text.text = text
            self._last_effects_text = text
