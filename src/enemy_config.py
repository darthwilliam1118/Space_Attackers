"""EnemyConfig — enemy grid parameters loaded from game_config.toml [enemies]."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EnemyConfig:
    enemy_cols: int = 5
    enemy_rows: int = 4
    enemy_speed_initial: float = 80.0
    enemy_speed_max_bonus: float = 120.0
    enemy_side_margin: float = 40.0
    enemy_drop_distance: float = 48.0
    enemy_fire_interval_min: float = 1.5
    enemy_fire_interval_max: float = 4.0
    enemy_bullet_speed: float = 250.0
