"""BossBullet — EnemyBullet variant that supports diagonal firing angles."""

from __future__ import annotations

import math
from typing import Optional

import arcade

from src.sprites.enemy_bullet import EnemyBullet


class BossBullet(EnemyBullet):
    """Angled enemy bullet fired by the boss.

    angle_deg=0 fires straight down, positive angles tilt right,
    negative angles tilt left (matching Arcade's CCW-positive convention
    where 0 points down).
    """

    def __init__(
        self,
        x: float,
        y: float,
        speed: float,
        angle_deg: float = 0.0,
        texture: Optional[arcade.Texture] = None,
        scale: float = 1.0,
        damage: int = 20,
    ) -> None:
        super().__init__(x=x, y=y, speed=speed, texture=texture, scale=scale, damage=damage)
        rad = math.radians(angle_deg)
        self._vx: float = math.sin(rad) * speed
        self._vy: float = -math.cos(rad) * speed  # negative = downward
        # Orient sprite to match travel direction
        self.angle = 180.0 + angle_deg

    def update(self, delta_time: float = 1 / 60) -> None:  # type: ignore[override]
        self.center_x += self._vx * delta_time
        self.center_y += self._vy * delta_time
        if self.center_y < 0:
            self.remove_from_sprite_lists()
