"""MeteorConfig — tunable parameters for meteor storm levels."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MeteorConfig:
    storm_duration: float = 30.0
    spawn_rate_base: float = 3.0
    spawn_rate_scale_pct: float = 0.10
    spawn_rate_max: float = 15.0
    fall_speed_min: float = 150.0
    fall_speed_max: float = 350.0
    fall_angle_max: float = 25.0
    spin_rpm_min: float = 30.0
    spin_rpm_max: float = 180.0
    spawn_height_offset: float = 60.0
    hp_bar_duration: float = 1.0
    prob_large: float = 0.30
    prob_med: float = 0.40
    prob_small: float = 0.20
    prob_tiny: float = 0.10
    hp_large: int = 1000
    hp_med: int = 500
    hp_small: int = 100
    hp_tiny: int = 25
    points_large: int = 200
    points_med: int = 100
    points_small: int = 50
    points_tiny: int = 25
