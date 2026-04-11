"""UIConfig — UI / HUD parameters loaded from game_config.toml [ui]."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UIConfig:
    popup_duration: float = 0.8
    popup_rise_speed: float = 60.0
    hp_bar_duration: float = 1.0
    hp_bar_height: int = 6
    hp_bar_y_offset: int = 10
