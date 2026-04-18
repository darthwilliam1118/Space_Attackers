"""RapidFireEffect — sets PlayerShip.fire_cooldown_multiplier for the duration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agf.powerups.effect_base import PowerUpEffect

if TYPE_CHECKING:
    from src.powerups.sa_powerup_config import SAPowerUpConfig


class RapidFireEffect(PowerUpEffect):
    """Reduces fire cooldown by multiplier (e.g. 0.35 = ~3x faster)."""

    def __init__(self, config: "SAPowerUpConfig") -> None:
        self._duration = config.rapid_fire_duration
        self._multiplier = config.rapid_fire_multiplier
        self._elapsed = 0.0

    @property
    def effect_type(self) -> str:
        return "rapid_fire"

    @property
    def display_label(self) -> str:
        return "RAPID FIRE"

    @property
    def remaining_duration(self) -> float:
        return max(0.0, self._duration - self._elapsed)

    def apply(self, ship: Any, context: dict) -> None:
        ship.fire_cooldown_multiplier = self._multiplier

    def update(self, delta_time: float, ship: Any) -> bool:
        self._elapsed += delta_time
        return self._elapsed < self._duration

    def remove(self, ship: Any, context: dict) -> None:
        ship.fire_cooldown_multiplier = 1.0
