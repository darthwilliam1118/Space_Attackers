"""SAPowerUpConfig — Space Attackers power-up tuning."""

from __future__ import annotations

from dataclasses import dataclass

from agf.powerups.config import PowerUpConfigBase


@dataclass
class SAPowerUpConfig(PowerUpConfigBase):
    # Shield
    shield_duration: float = 10.0
    shield_hits: int = 3

    # Health
    health_restore_amount: int = 25

    # Stat-modifier durations and magnitudes
    rapid_fire_duration: float = 8.0
    rapid_fire_multiplier: float = 0.35

    big_gun_duration: float = 8.0
    big_gun_damage_multiplier: float = 2.0
    big_gun_scale_multiplier: float = 2.0

    speed_boost_duration: float = 6.0
    speed_boost_multiplier: float = 1.5

    # Behavior effect durations
    triple_shot_duration: float = 10.0
    spread_shot_duration: float = 8.0
    spread_shot_angle: float = 20.0

    # Constraint effect duration
    free_move_duration: float = 8.0

    # Spawn interval divisor for meteor levels (>1 = more frequent)
    meteor_spawn_interval_factor: float = 2.0

    # Pickup sprite scale (independent of global sprite_scale)
    powerups_scale: float = 1.0

    # Spawn weights (relative)
    weight_health: float = 8.0
    weight_shield: float = 10.0
    weight_rapid_fire: float = 10.0
    weight_big_gun: float = 8.0
    weight_speed_boost: float = 6.0
    weight_triple_shot: float = 7.0
    weight_spread_shot: float = 6.0
    weight_free_move: float = 3.0
