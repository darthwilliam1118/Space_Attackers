"""ShipConfig — player ship parameters loaded from game_config.toml [ship]."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ShipConfig:
    ship_speed: float = 300.0        # reference / slow speed (px/s); max = 2×
    ship_accel: float = 1000.0       # acceleration rate (px/s²) when key held
    ship_decel: float = 1200.0       # deceleration rate (px/s²) when key released
    ship_tilt_rate: float = 90.0     # tilt animation speed (degrees/second)
    fire_cooldown: float = 0.3
    bullet_speed: float = 500.0
    spawn_invincible_duration: float = 2.0
    ship_zone_height_pct: float = 0.33
    explosion_frame_duration: float = 0.05
