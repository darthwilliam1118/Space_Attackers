"""GAME_CONFIG screen — displays and edits config parameters."""

from __future__ import annotations

from typing import TYPE_CHECKING

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

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

    def on_draw(self) -> None:
        self.clear()
        width = self.window.width
        height = self.window.height

        arcade.draw_text(
            "GAME CONFIG",
            width / 2,
            height - 80,
            arcade.color.CYAN,
            font_size=40,
            anchor_x="center",
            bold=True,
        )

        for i, field in enumerate(_FIELDS):
            value = getattr(self._cfg, field)
            label = _FIELD_LABELS[field]
            color = arcade.color.YELLOW if i == self._selected else arcade.color.WHITE
            prefix = "▶ " if i == self._selected else "  "
            arcade.draw_text(
                f"{prefix}{label}: {value}",
                width / 2,
                height / 2 + 40 - i * 50,
                color,
                font_size=22,
                anchor_x="center",
            )

        arcade.draw_text(
            "↑ ↓ = select    ← → = change value    ESC = save & return",
            width / 2,
            40,
            arcade.color.LIGHT_GRAY,
            font_size=14,
            anchor_x="center",
        )

    def on_key_press(self, key: int, modifiers: int) -> None:
        from src.state import GameState

        match key:
            case arcade.key.UP:
                self._selected = (self._selected - 1) % len(_FIELDS)
            case arcade.key.DOWN:
                self._selected = (self._selected + 1) % len(_FIELDS)
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
