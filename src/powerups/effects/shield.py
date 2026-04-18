"""ShieldEffect — degrading damage absorber overlay."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agf.powerups.effect_categories import OverlayEffect

if TYPE_CHECKING:
    import arcade

    from src.powerups.sa_powerup_config import SAPowerUpConfig


class ShieldEffect(OverlayEffect):
    """3-hit shield. Each hit absorbs damage and degrades the overlay texture."""

    def __init__(self, config: "SAPowerUpConfig") -> None:
        super().__init__(duration=config.shield_duration)
        self._max_hits = config.shield_hits
        self._hits_remaining = config.shield_hits

    @property
    def effect_type(self) -> str:
        return "shield"

    @property
    def hits_remaining(self) -> int:
        return self._hits_remaining

    @property
    def display_label(self) -> str:
        full = "\u2593" * self._hits_remaining
        empty = "\u2591" * (self._max_hits - self._hits_remaining)
        return f"SHIELD {full}{empty}"

    def create_overlay_sprite(self, scale: float) -> "arcade.Sprite":
        from src.sprites.shield_sprite import ShieldSprite

        return ShieldSprite(scale=scale)

    def on_hit_absorbed(self) -> bool:
        self._hits_remaining -= 1
        return self._hits_remaining <= 0

    def update_overlay_sprite(self, ship_x: float, ship_y: float) -> None:
        if self._overlay_sprite is None:
            return
        from src.sprites.shield_sprite import ShieldSprite

        if isinstance(self._overlay_sprite, ShieldSprite):
            self._overlay_sprite.update_state(self._hits_remaining, ship_x, ship_y)

    def apply(self, ship: Any, context: dict) -> None:
        super().apply(ship, context)
        ship.shield_active = True
        ship.shield_hits_remaining = self._hits_remaining

    def remove(self, ship: Any, context: dict) -> None:
        super().remove(ship, context)
        ship.shield_active = False
        ship.shield_hits_remaining = 0
