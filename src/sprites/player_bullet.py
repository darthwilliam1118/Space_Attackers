"""PlayerBullet — laser fired by the player ship at the ship's current tilt angle."""

from __future__ import annotations

import math
from typing import Optional

import arcade

from src.paths import resource_path

# Sprite paths indexed by player_num (1-based).
_BULLET_PATHS: dict[int, str] = {
    1: "assets/images/PNG/Lasers/laserBlue01.png",
    2: "assets/images/PNG/Lasers/laserRed01.png",
}


def bullet_path_for(player_num: int) -> str:
    """Return the asset path for *player_num*'s bullet."""
    return _BULLET_PATHS.get(player_num, _BULLET_PATHS[1])


class PlayerBullet(arcade.Sprite):
    """Travels in the direction of the ship's tilt; removes itself on any screen edge.

    *angle_deg* follows the ship's tilt convention: positive = right of vertical,
    negative = left of vertical.  Pass *texture* to inject a pre-loaded texture
    (tests, no display needed).
    """

    def __init__(
        self,
        x: float,
        y: float,
        speed: float,
        window_width: int,
        window_height: int,
        angle_deg: float = 0.0,
        player_num: int = 1,
        texture: Optional[arcade.Texture] = None,
        scale: float = 1.0,
    ) -> None:
        if texture is not None:
            super().__init__(texture)
        else:
            tex = arcade.load_texture(
                resource_path(bullet_path_for(player_num)),
                hit_box_algorithm=arcade.hitbox.algo_simple,
            )
            super().__init__(tex)
        self.scale = scale
        self.center_x = x
        self.center_y = y
        self.angle = angle_deg
        self._window_width = window_width
        self._window_height = window_height

        # Decompose speed into x/y components.
        # angle_deg=0 → straight up; positive → right of vertical.
        rad = math.radians(angle_deg)
        self._vx = speed * math.sin(rad)
        self._vy = speed * math.cos(rad)

    def update(self, delta_time: float = 1 / 60) -> None:  # type: ignore[override]
        self.center_x += self._vx * delta_time
        self.center_y += self._vy * delta_time
        if (
            self.center_y > self._window_height
            or self.center_y < 0
            or self.center_x > self._window_width
            or self.center_x < 0
        ):
            self.remove_from_sprite_lists()
