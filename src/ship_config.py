"""ShipConfig — player ship parameters loaded from game_config.toml [ship]."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ShipConfig:
    ship_speed: float = 300.0
    fire_cooldown: float = 0.3
    bullet_speed: float = 500.0
    spawn_invincible_duration: float = 2.0
    ship_zone_height_pct: float = 0.20
    explosion_frame_duration: float = 0.05
