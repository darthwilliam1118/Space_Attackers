"""TripleShotEffect — fires three bullets per cooldown cycle."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agf.powerups.effect_categories import BehaviorEffect

from src.sprites.player_bullet import PlayerBullet

if TYPE_CHECKING:
    from src.powerups.sa_powerup_config import SAPowerUpConfig


_OFFSETS_DEG: tuple[float, ...] = (-15.0, 0.0, 15.0)


class TripleShotEffect(BehaviorEffect):
    """Replaces try_fire() with three angled bullets while active."""

    def __init__(self, config: "SAPowerUpConfig") -> None:
        super().__init__(duration=config.triple_shot_duration)

    @property
    def effect_type(self) -> str:
        return "triple_shot"

    @property
    def display_label(self) -> str:
        return "TRIPLE SHOT"

    def get_bullets(self, ship: Any) -> list[Any]:
        # Reach into ship internals — same package, documented coupling.
        if ship._fire_cooldown_remaining > 0.0:
            return []
        ship._fire_cooldown_remaining = ship._config.fire_cooldown * ship.fire_cooldown_multiplier
        bullets: list[Any] = []
        for offset in _OFFSETS_DEG:
            bullets.append(
                PlayerBullet(
                    x=ship.center_x,
                    y=ship.center_y + ship.height / 2.0,
                    speed=ship._config.bullet_speed,
                    window_width=ship._window_width,
                    window_height=ship._window_height,
                    angle_deg=ship._tilt_angle + offset,
                    player_num=ship._player_num,
                    scale=ship._sprite_scale * ship.bullet_scale_multiplier,
                    damage=ship._config.player_bullet_damage * ship.bullet_damage_multiplier,
                )
            )
        return bullets
