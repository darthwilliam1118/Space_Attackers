"""SAPowerUpManager — wires sprite asset loading and effect creation."""

from __future__ import annotations

import math
import random
from typing import Optional

import arcade
from agf.paths import resource_path
from agf.powerups.effect_base import PowerUpEffect
from agf.powerups.manager import PowerUpManager
from agf.powerups.powerup_sprite import PowerUpSprite

from src.powerups.effects.big_gun import BigGunEffect
from src.powerups.effects.free_move import FreeMovementEffect
from src.powerups.effects.health import HealthEffect
from src.powerups.effects.rapid_fire import RapidFireEffect
from src.powerups.effects.shield import ShieldEffect
from src.powerups.effects.speed_boost import SpeedBoostEffect
from src.powerups.effects.spread_shot import SpreadShotEffect
from src.powerups.effects.triple_shot import TripleShotEffect
from src.powerups.sa_powerup_config import SAPowerUpConfig
from src.powerups.sa_spawner import SAPowerUpSpawner

_PICKUP_ASSETS: dict[str, str] = {
    "health": "assets/images/PNG/Power-ups/pill_red.png",
    "shield": "assets/images/PNG/Power-ups/powerupBlue_shield.png",
    "rapid_fire": "assets/images/PNG/Power-ups/bolt_bronze.png",
    "big_gun": "assets/images/PNG/Power-ups/bolt_gold.png",
    "speed_boost": "assets/images/PNG/Power-ups/star_bronze.png",
    "triple_shot": "assets/images/PNG/Power-ups/bolt_silver.png",
    "spread_shot": "assets/images/PNG/Power-ups/star_silver.png",
    "free_move": "assets/images/PNG/Power-ups/star_gold.png",
}

_FALLBACK_COLORS: dict[str, tuple[int, int, int, int]] = {
    "health": (255, 100, 100, 255),
    "shield": (100, 100, 255, 255),
    "rapid_fire": (255, 255, 100, 255),
    "big_gun": (255, 165, 0, 255),
    "speed_boost": (100, 255, 100, 255),
    "triple_shot": (255, 100, 255, 255),
    "spread_shot": (200, 100, 255, 255),
    "free_move": (100, 255, 255, 255),
}


class SAPowerUpManager(PowerUpManager):
    """Space Attackers power-up manager — supplies spawner, sprites, effects."""

    def create_spawner(self) -> SAPowerUpSpawner:
        return SAPowerUpSpawner(self._config)

    def create_sprite(self, effect_type: str, x: float, y: float) -> PowerUpSprite:
        cfg: SAPowerUpConfig = self._config  # type: ignore[assignment]
        fall_speed = random.uniform(cfg.fall_speed_min, cfg.fall_speed_max)
        spawn_y = self._window_height + cfg.spawn_height_offset
        angle_deg = self._safe_angle(x, spawn_y, cfg.fall_angle_max)
        texture = self._load_texture(effect_type)
        return PowerUpSprite(
            x=x,
            y=spawn_y,
            effect_type=effect_type,
            fall_speed=fall_speed,
            angle_deg=angle_deg,
            spin_rpm=cfg.spin_rpm,
            scale=cfg.powerups_scale,
            texture=texture,
        )

    def create_effect(self, effect_type: str) -> PowerUpEffect:
        cfg: SAPowerUpConfig = self._config  # type: ignore[assignment]
        match effect_type:
            case "health":
                return HealthEffect(cfg)
            case "shield":
                return ShieldEffect(cfg)
            case "rapid_fire":
                return RapidFireEffect(cfg)
            case "big_gun":
                return BigGunEffect(cfg)
            case "speed_boost":
                return SpeedBoostEffect(cfg)
            case "triple_shot":
                return TripleShotEffect(cfg)
            case "spread_shot":
                return SpreadShotEffect(cfg)
            case "free_move":
                return FreeMovementEffect(cfg)
            case _:
                raise ValueError(f"Unknown power-up type: {effect_type!r}")

    def clear_effects_only(self, ship: object, context: dict) -> None:
        """Cancel active effects and restore ship state, but keep falling sprites alive."""
        for effect in list(self._active_effects):
            effect.remove(ship, context)
        self._active_effects.clear()

    def update_sprites_only(self, delta_time: float) -> None:
        """Advance falling pickup sprites only — no spawning, no collection, no effect ticks."""
        for sprite in list(self._sprites):
            sprite.update(delta_time)

    def _add_effect(self, effect: PowerUpEffect, ship: object, context: dict) -> None:
        """Extend duration when same type is already active instead of stacking."""
        if not effect.is_instant:
            for existing in self._active_effects:
                if existing.effect_type == effect.effect_type:
                    extra = getattr(effect, "_duration", 0.0)
                    existing._elapsed = max(0.0, existing._elapsed - extra)  # type: ignore[attr-defined]
                    if isinstance(existing, ShieldEffect):
                        existing._hits_remaining = existing._max_hits
                    return
        super()._add_effect(effect, ship, context)

    def _safe_angle(self, x: float, spawn_y: float, max_angle: float) -> float:
        """Return a random drift angle that keeps the sprite inside the window.

        Given spawn position x and the vertical distance to y=0 (spawn_y),
        the horizontal displacement at the window bottom is spawn_y * tan(angle).
        We clamp the drawable angle so x_final stays within [margin, w-margin].
        """
        margin = 30.0
        w = float(self._window_width)
        # angle that would land exactly on left/right margin
        angle_min = math.degrees(math.atan((margin - x) / spawn_y))
        angle_max = math.degrees(math.atan((w - margin - x) / spawn_y))
        # further restrict to the configured aesthetic max
        angle_min = max(angle_min, -max_angle)
        angle_max = min(angle_max, max_angle)
        if angle_min >= angle_max:
            return 0.0
        return random.uniform(angle_min, angle_max)

    def _load_texture(self, effect_type: str) -> Optional[arcade.Texture]:
        path = _PICKUP_ASSETS.get(effect_type)
        if path:
            try:
                return arcade.load_texture(resource_path(path))
            except Exception:
                pass
        color = _FALLBACK_COLORS.get(effect_type, (200, 200, 200, 255))
        return arcade.make_circle_texture(32, color)
