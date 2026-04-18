"""HealthEffect — instant HP restore."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agf.powerups.effect_categories import InstantEffect

if TYPE_CHECKING:
    from src.powerups.sa_powerup_config import SAPowerUpConfig


class HealthEffect(InstantEffect):
    """Instant HP restore, capped at max_hit_points."""

    def __init__(self, config: "SAPowerUpConfig") -> None:
        self._amount = config.health_restore_amount

    @property
    def effect_type(self) -> str:
        return "health"

    def apply(self, ship: Any, context: dict) -> None:
        ship.hit_points = min(ship.hit_points + self._amount, ship.max_hit_points)
