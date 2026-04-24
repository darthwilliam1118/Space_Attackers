"""BossConfig — configuration dataclass for boss encounter levels."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BossConfig:
    # Sprite
    boss_sprite: str = "assets/images/PNG/Enemies/enemyBlack5.png"
    boss_scale_base: float = 3.0
    boss_scale_per_boss: float = 0.0

    # HP
    boss_hp_base: int = 500
    boss_hp_per_boss: int = 200

    # Movement
    boss_speed_base: float = 60.0
    boss_speed_per_boss: float = 8.0
    boss_speed_max: float = 180.0
    boss_side_margin: float = 40.0
    boss_drop_distance: float = 24.0

    # Shooting
    boss_fire_interval_base: float = 1.2
    boss_fire_interval_per_boss: float = -0.08
    boss_fire_interval_min: float = 0.35
    boss_bullet_speed: float = 280.0
    boss_bullet_damage: int = 1
    boss_spread_chance: float = 0.25
    boss_spread_count: int = 5
    boss_spread_angle: float = 30.0

    # Scoring
    boss_points_base: int = 1000
    boss_points_per_boss: int = 500

    # Death sequence
    boss_death_duration: float = 2.5
    boss_death_explosion_count: int = 8
    boss_death_particle_count: int = 60

    # Diving
    boss_dive_group_size_max: int = 2
    boss_dive_interval_base: float = 8.0
    boss_dive_interval_min: float = 4.0
    boss_diver_loop_count: int = 3

    # Boss power-up weights (restricted to shield, big_gun, spread_shot)
    boss_pu_weight_shield: float = 8.0
    boss_pu_weight_big_gun: float = 10.0
    boss_pu_weight_spread_shot: float = 10.0
