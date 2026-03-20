"""BackgroundConfig — static + star-field background configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BackgroundConfig:
    background_image: str = "assets/images/Backgrounds/darkPurple.png"
    star_count: int = 300
    star_speed_min: float = 20.0
    star_speed_max: float = 120.0
