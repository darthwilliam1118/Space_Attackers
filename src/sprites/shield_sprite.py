"""ShieldSprite — visual overlay drawn centred on the player ship while shielded."""

from __future__ import annotations

import math
from typing import Optional

import arcade
from agf.paths import resource_path

_SHIELD_TEXTURES: dict[int, str] = {
    3: "assets/images/PNG/Effects/shield3.png",
    2: "assets/images/PNG/Effects/shield2.png",
    1: "assets/images/PNG/Effects/shield1.png",
}


class ShieldSprite(arcade.Sprite):
    """Visual shield overlay. Not a physics object — no collisions."""

    def __init__(
        self,
        scale: float = 1.0,
        textures: Optional[dict[int, arcade.Texture]] = None,
    ) -> None:
        super().__init__()
        self._textures: dict[int, arcade.Texture] = textures or {
            hits: arcade.load_texture(resource_path(path))
            for hits, path in _SHIELD_TEXTURES.items()
        }
        self.scale = scale
        self.texture = self._textures[3]
        self._current_hits = 3
        self._pulse_elapsed = 0.0

    def update_state(self, hits_remaining: int, ship_x: float, ship_y: float) -> None:
        self.center_x = ship_x
        self.center_y = ship_y
        if hits_remaining != self._current_hits:
            self._current_hits = hits_remaining
            if hits_remaining in self._textures:
                self.texture = self._textures[hits_remaining]

    def pulse(self, delta_time: float) -> None:
        """Gentle alpha pulse to indicate active shield."""
        self._pulse_elapsed += delta_time
        self.alpha = int(180 + 37 * math.sin(self._pulse_elapsed * 4))
