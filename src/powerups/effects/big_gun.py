"""BigGunEffect — boosts bullet scale and damage simultaneously."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agf.powerups.effect_base import PowerUpEffect

if TYPE_CHECKING:
    from src.powerups.sa_powerup_config import SAPowerUpConfig


class BigGunEffect(PowerUpEffect):
    """Multiplies bullet scale and damage for the duration."""

    def __init__(self, config: "SAPowerUpConfig") -> None:
        self._duration = config.big_gun_duration
        self._scale = config.big_gun_scale_multiplier
        self._damage = int(config.big_gun_damage_multiplier)
        self._elapsed = 0.0

    @property
    def effect_type(self) -> str:
        return "big_gun"

    @property
    def display_label(self) -> str:
        return "BIG GUN"

    @property
    def remaining_duration(self) -> float:
        return max(0.0, self._duration - self._elapsed)

    def apply(self, ship: Any, context: dict) -> None:
        ship.bullet_scale_multiplier = self._scale
        ship.bullet_damage_multiplier = self._damage

    def update(self, delta_time: float, ship: Any) -> bool:
        self._elapsed += delta_time
        return self._elapsed < self._duration

    def remove(self, ship: Any, context: dict) -> None:
        ship.bullet_scale_multiplier = 1.0
        ship.bullet_damage_multiplier = 1
