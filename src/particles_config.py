"""ParticlesConfig — particle effect parameters loaded from game_config.toml [particles]."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParticlesConfig:
    particle_count: int = 20
    particle_speed_min: float = 50.0
    particle_speed_max: float = 200.0
    particle_lifetime_min: float = 0.3
    particle_lifetime_max: float = 0.8
    particle_gravity: float = 150.0
    shockwave_duration: float = 0.3
    shockwave_max_scale: float = 2.5
