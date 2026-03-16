"""PlayerBullet — upward-travelling laser fired by the player ship."""

from __future__ import annotations

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
    """Moves straight up at a fixed speed; removes itself when off-screen.

    Pass *texture* to inject a pre-loaded texture (tests, no display needed).
    """

    def __init__(
        self,
        x: float,
        y: float,
        speed: float,
        window_height: int,
        player_num: int = 1,
        texture: Optional[arcade.Texture] = None,
    ) -> None:
        if texture is not None:
            super().__init__(texture)
        else:
            super().__init__(resource_path(bullet_path_for(player_num)))
        self.center_x = x
        self.center_y = y
        self._speed = speed
        self._window_height = window_height

    def update(self, delta_time: float = 1 / 60) -> None:  # type: ignore[override]
        self.center_y += self._speed * delta_time
        if self.center_y > self._window_height:
            self.remove_from_sprite_lists()
