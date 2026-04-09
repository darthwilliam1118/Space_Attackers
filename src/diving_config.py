"""DivingConfig — diving ship parameters loaded from game_config.toml [diving]."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DivingConfig:
    dive_group_size_max: int = 4
    dive_interval_base: float = 12.0
    dive_interval_step: float = 1.0
    dive_interval_min: float = 4.0
    dive_speed_base: float = 200.0
    dive_speed_step: float = 15.0
    dive_speed_max: float = 380.0
    dive_bomb_speed: float = 220.0
    dive_bonus_points: int = 20
    dive_return_speed: float = 160.0
