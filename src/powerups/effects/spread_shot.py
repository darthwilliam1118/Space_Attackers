"""SpreadShotEffect — fires five bullets in a wide spread."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agf.powerups.effect_categories import BehaviorEffect

from src.sprites.player_bullet import PlayerBullet

if TYPE_CHECKING:
    from src.powerups.sa_powerup_config import SAPowerUpConfig


_STEPS: tuple[int, ...] = (-2, -1, 0, 1, 2)


class SpreadShotEffect(BehaviorEffect):
    """Replaces try_fire() with five bullets fanned by spread_shot_angle."""

    def __init__(self, config: "SAPowerUpConfig") -> None:
        super().__init__(duration=config.spread_shot_duration)
        self._spread_angle = config.spread_shot_angle

    @property
    def effect_type(self) -> str:
        return "spread_shot"

    @property
    def display_label(self) -> str:
        return "SPREAD SHOT"

    def get_bullets(self, ship: Any) -> list[Any]:
        if ship._fire_cooldown_remaining > 0.0:
            return []
        ship._fire_cooldown_remaining = ship._config.fire_cooldown * ship.fire_cooldown_multiplier
        bullets: list[Any] = []
        for step in _STEPS:
            bullets.append(
                PlayerBullet(
                    x=ship.center_x,
                    y=ship.center_y + ship.height / 2.0,
                    speed=ship._config.bullet_speed,
                    window_width=ship._window_width,
                    window_height=ship._window_height,
                    angle_deg=ship._tilt_angle + step * self._spread_angle,
                    player_num=ship._player_num,
                    scale=ship._sprite_scale * ship.bullet_scale_multiplier,
                    damage=ship._config.player_bullet_damage * ship.bullet_damage_multiplier,
                )
            )
        return bullets
