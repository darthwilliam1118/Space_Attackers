"""GAME_CONFIG screen — displays and edits config parameters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

from agf.ui.text_utils import FONT_MAIN, FONT_THIN, centered_text

_FIELDS = ["starting_level", "num_lives", "spawn_safe_radius", "music_volume", "effects_volume"]
_FIELD_LABELS = {
    "starting_level": "Starting Level",
    "num_lives": "Number of Lives",
    "spawn_safe_radius": "Spawn Safe Radius (px)",
    "music_volume": "Music Volume (0-100)",
    "effects_volume": "Effects Volume (0-100)",
}
_FIELD_CLAMP = {
    "starting_level": (1, 999),
    "num_lives": (1, 99),
    "spawn_safe_radius": (0, 9999),
    "music_volume": (0, 100),
    "effects_volume": (0, 100),
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

        # Key-repeat state for LEFT/RIGHT held
        self._repeat_key: Optional[int] = None  # arcade.key.LEFT or RIGHT
        self._repeat_initial: float = 0.4  # seconds before repeat starts
        self._repeat_interval: float = 0.08  # seconds between repeats
        self._repeat_timer: float = 0.0

    def on_show_view(self) -> None:
        self.window.music.play("ending")  # type: ignore[attr-defined]
        w, h = self.window.width, self.window.height
        self._title_text = centered_text(
            "GAME CONFIG",
            w,
            h - 80,
            font_size=40,
            color=arcade.color.CYAN,
            font_name=FONT_MAIN,
        )
        top_y = h // 2 + (len(_FIELDS) // 2) * 46
        self._field_texts = [
            centered_text(
                "",
                w,
                top_y - i * 46,
                font_size=22,
                color=arcade.color.WHITE,
                font_name=FONT_THIN,
            )
            for i in range(len(_FIELDS))
        ]
        self._hint_text = centered_text(
            "↑ ↓ = select    ← → = change value    ESC = save & return",
            w,
            int(h * 0.05),
            font_size=14,
            color=(160, 160, 160, 255),
            font_name=FONT_THIN,
        )
        self._refresh_fields()

    def on_update(self, delta_time: float) -> None:
        self.window.star_field.update(delta_time)  # type: ignore[attr-defined]
        if self._repeat_key is not None:
            self._repeat_timer -= delta_time
            if self._repeat_timer <= 0.0:
                delta = -1 if self._repeat_key == arcade.key.LEFT else 1
                self._adjust(delta)
                self._repeat_timer = self._repeat_interval

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
                self._repeat_key = arcade.key.LEFT
                self._repeat_timer = self._repeat_initial
            case arcade.key.RIGHT:
                self._adjust(1)
                self._repeat_key = arcade.key.RIGHT
                self._repeat_timer = self._repeat_initial
            case arcade.key.ESCAPE:
                self._cfg.save()
                self._manager.context["config"] = self._cfg
                self._manager.transition(GameState.MAIN)

    def on_key_release(self, key: int, modifiers: int) -> None:
        if key in (arcade.key.LEFT, arcade.key.RIGHT):
            self._repeat_key = None

    def _adjust(self, delta: int) -> None:
        field = _FIELDS[self._selected]
        current = getattr(self._cfg, field)
        lo, hi = _FIELD_CLAMP.get(field, (1, 999))
        setattr(self._cfg, field, max(lo, min(hi, current + delta)))
        # Apply volume changes immediately so the user can hear the effect
        if field == "music_volume":
            self.window.music.set_volume(self._cfg.music_volume)  # type: ignore[attr-defined]
        self._refresh_fields()

    def _refresh_fields(self) -> None:
        """Update text content and colour for all field rows."""
        for i, (field, text_obj) in enumerate(zip(_FIELDS, self._field_texts)):
            value = getattr(self._cfg, field)
            label = _FIELD_LABELS[field]
            prefix = "▶  " if i == self._selected else "    "
            text_obj.text = f"{prefix}{label}: {value}"
            text_obj.color = arcade.color.YELLOW if i == self._selected else arcade.color.WHITE
