"""EnemyConfig — enemy grid parameters loaded from game_config.toml [enemies]."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EnemyConfig:
    # Grid size — grows each level up to the max
    enemy_cols_start: int = 7
    enemy_rows_start: int = 4
    enemy_cols_max: int = 15
    enemy_rows_max: int = 10
    enemy_cols_per_level: int = 2
    enemy_rows_per_level: int = 1

    # Movement
    enemy_col_width_factor: float = 1.2
    enemy_speed_initial: float = 30.0
    enemy_speed_max_bonus: float = 150.0
    enemy_speed_level_pct: float = 0.1  # multiplicative per-level base speed increase
    enemy_side_margin: float = 60.0
    enemy_drop_distance: float = 32.0
    enemy_bottom_margin: float = 150.0

    # Shooting — intervals scale by enemy_fire_interval_scale each level
    enemy_fire_interval_min_l1: float = 2.0
    enemy_fire_interval_max_l1: float = 4.0
    enemy_fire_interval_scale: float = 0.95  # 0.95 = 5% faster each level
    enemy_fire_interval_min_cap: float = 1.0
    enemy_fire_interval_max_cap: float = 2.0
    enemy_bullet_speed: float = 250.0
    enemy_bullet_damage: int = 20

    # Hit points per ship_type (1–5); scaled by level via enemy_hp_level_factor
    enemy_hp: dict[int, int] = field(
        default_factory=lambda: {1: 200, 2: 150, 3: 150, 4: 100, 5: 100}
    )
    enemy_hp_level_factor: float = 1.1
