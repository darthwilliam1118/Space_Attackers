"""EnemyBullet — downward-travelling laser fired by enemy ships."""

from __future__ import annotations

from typing import Optional

import arcade
from agf.paths import resource_path

_BULLET_PATH = "assets/images/PNG/Lasers/laserRed01.png"


class EnemyBullet(arcade.Sprite):
    """Moves straight down; removes itself when it exits the bottom of the screen.

    Pass *texture* to inject a pre-loaded texture (tests, no display needed).
    """

    def __init__(
        self,
        x: float,
        y: float,
        speed: float,
        texture: Optional[arcade.Texture] = None,
        scale: float = 1.0,
        damage: int = 20,
    ) -> None:
        if texture is not None:
            super().__init__(texture)
        else:
            tex = arcade.load_texture(
                resource_path(_BULLET_PATH),
                hit_box_algorithm=arcade.hitbox.algo_simple,
            )
            super().__init__(tex)
        self.scale = scale
        self.damage = damage
        self.center_x = x
        self.center_y = y
        self.angle = 180
        self._speed = speed

    def update(self, delta_time: float = 1 / 60) -> None:  # type: ignore[override]
        self.center_y -= self._speed * delta_time
        if self.center_y < 0:
            self.remove_from_sprite_lists()
