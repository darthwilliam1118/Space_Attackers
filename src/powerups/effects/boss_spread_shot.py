"""BossSpreadShotEffect — forces every boss shot to be a spread burst."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agf.powerups.effect_base import PowerUpEffect

if TYPE_CHECKING:
    from src.powerups.sa_powerup_config import SAPowerUpConfig


class BossSpreadShotEffect(PowerUpEffect):
    """Sets boss._spread_chance_override = 1.0 for the duration.

    While active, every boss shot fires as a spread burst instead of the
    normal boss_spread_chance probability.  Uses the same duration as the
    player-facing SpreadShotEffect so the TOML value governs both.
    """

    def __init__(self, config: "SAPowerUpConfig") -> None:
        self._duration = config.spread_shot_duration
        self._elapsed: float = 0.0

    @property
    def effect_type(self) -> str:
        return "spread_shot"

    @property
    def display_label(self) -> str:
        return "SPREAD SHOT"

    @property
    def remaining_duration(self) -> float:
        return max(0.0, self._duration - self._elapsed)

    def apply(self, ship: Any, context: dict) -> None:
        ship._spread_chance_override = 1.0

    def update(self, delta_time: float, ship: Any) -> bool:
        self._elapsed += delta_time
        return self._elapsed < self._duration

    def remove(self, ship: Any, context: dict) -> None:
        ship._spread_chance_override = None
