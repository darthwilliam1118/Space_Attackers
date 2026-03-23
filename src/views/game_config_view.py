"""GAME_CONFIG screen — displays and edits config parameters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

from src.ui.text_utils import FONT_MAIN, FONT_THIN, centered_text

_FIELDS = ["starting_level", "num_lives", "spawn_safe_radius"]
_FIELD_LABELS = {
    "starting_level": "Starting Level",
    "num_lives": "Number of Lives",
    "spawn_safe_radius": "Spawn Safe Radius (px)",
}


class GameConfigView(arcade.View):
    """Editable config screen. Arrow keys change values; ESC saves and returns."""

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__()
        self._manager = manager
        from src.game_config import GameConfig
        self._cfg = manager.context.get("config") or GameConfig.load()
        self._selected: int = 0  # index into _FIELDS

        self._title_text: Optional[arcade.Text] = None
        self._field_texts: list[arcade.Text] = []
        self._hint_text: Optional[arcade.Text] = None

    def on_show_view(self) -> None:
        self.window.music.play("ending")  # type: ignore[attr-defined]
        w, h = self.window.width, self.window.height
        self._title_text = centered_text(
            "GAME CONFIG", w, h - 80,
            font_size=40, color=arcade.color.CYAN, font_name=FONT_MAIN, bold=True,
        )
        self._field_texts = [
            centered_text(
                "", w, h // 2 + 40 - i * 50,
                font_size=22, color=arcade.color.WHITE, font_name=FONT_THIN,
            )
            for i in range(len(_FIELDS))
        ]
        self._hint_text = centered_text(
            "↑ ↓ = select    ← → = change value    ESC = save & return",
            w, int(h * 0.05), font_size=14, color=(160, 160, 160, 255), font_name=FONT_THIN,
        )
        self._refresh_fields()

    def on_update(self, delta_time: float) -> None:
        self.window.star_field.update(delta_time)  # type: ignore[attr-defined]

    def on_draw(self) -> None:
        self.clear()
        self.window.background.draw()  # type: ignore[attr-defined]
        self.window.star_field.draw()  # type: ignore[attr-defined]
        if self._title_text:
            self._title_text.draw()
        for t in self._field_texts:
            t.draw()
        if self._hint_text:
            self._hint_text.draw()

    def on_key_press(self, key: int, modifiers: int) -> None:
        from src.state import GameState

        match key:
            case arcade.key.UP:
                self._selected = (self._selected - 1) % len(_FIELDS)
                self._refresh_fields()
            case arcade.key.DOWN:
                self._selected = (self._selected + 1) % len(_FIELDS)
                self._refresh_fields()
            case arcade.key.LEFT:
                self._adjust(-1)
            case arcade.key.RIGHT:
                self._adjust(1)
            case arcade.key.ESCAPE:
                self._cfg.save()
                self._manager.context["config"] = self._cfg
                self._manager.transition(GameState.MAIN)

    def _adjust(self, delta: int) -> None:
        field = _FIELDS[self._selected]
        current = getattr(self._cfg, field)
        setattr(self._cfg, field, max(1, current + delta))
        self._refresh_fields()

    def _refresh_fields(self) -> None:
        """Update text content and colour for all field rows."""
        for i, (field, text_obj) in enumerate(zip(_FIELDS, self._field_texts)):
            value = getattr(self._cfg, field)
            label = _FIELD_LABELS[field]
            prefix = "▶  " if i == self._selected else "    "
            text_obj.text = f"{prefix}{label}: {value}"
            text_obj.color = arcade.color.YELLOW if i == self._selected else arcade.color.WHITE
