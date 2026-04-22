"""MeteorSprite — a single falling meteor with HP and drift physics."""

from __future__ import annotations

import arcade


class MeteorSprite(arcade.Sprite):
    """Falling meteor with HP tracking and rotation.

    Created by MeteorLevel._spawn_meteor(); updated each frame via update().
    Exposes hit_points / max_hit_points / hp_bar_timer so RunLevelView's
    _draw_enemy_hp_bars() can render the HP bar without changes.
    """

    def __init__(
        self,
        texture: arcade.Texture,
        hit_points: int,
        vx: float,
        vy: float,
        spin_deg_per_sec: float,
    ) -> None:
        super().__init__(texture)
        self.hit_points: int = hit_points
        self.max_hit_points: int = hit_points
        self.hp_bar_timer: float = 0.0
        self._vx: float = vx
        self._vy: float = vy
        self._spin: float = spin_deg_per_sec

    def update(self, delta_time: float = 1 / 60) -> None:  # type: ignore[override]
        self.center_x += self._vx * delta_time
        self.center_y += self._vy * delta_time
        self.angle += self._spin * delta_time
        if self.hp_bar_timer > 0.0:
            self.hp_bar_timer -= delta_time
