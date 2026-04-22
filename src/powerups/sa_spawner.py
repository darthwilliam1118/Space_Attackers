"""SAPowerUpSpawner — gates power-up types by level via UNLOCK_ORDER."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agf.powerups.spawner import PowerUpSpawner

if TYPE_CHECKING:
    from src.powerups.sa_powerup_config import SAPowerUpConfig


class SAPowerUpSpawner(PowerUpSpawner):
    # Level 1: nothing. Level N >= 2: first (N - 1) entries are unlocked.
    UNLOCK_ORDER: list[str] = [
        "health",
        "shield",
        "rapid_fire",
        "big_gun",
        "triple_shot",
        "speed_boost",
        "spread_shot",
        "free_move",
    ]

    def _compute_interval(self) -> float:
        interval = super()._compute_interval()
        if self._level_type == "meteor":
            cfg: "SAPowerUpConfig" = self._config  # type: ignore[assignment]
            factor = cfg.meteor_spawn_interval_factor
            if factor > 0:
                interval = max(self._config.spawn_interval_min / factor, interval / factor)
        return interval

    def _available_types(self) -> list[str]:
        if self._level_type == "meteor":
            return list(self.UNLOCK_ORDER)
        unlocked_count = max(0, self._level_number - 1)
        return self.UNLOCK_ORDER[:unlocked_count]

    def _build_weight_table(self) -> dict[str, float]:
        available = self._available_types()
        if not available:
            return {}

        cfg: "SAPowerUpConfig" = self._config  # type: ignore[assignment]
        base_weights: dict[str, float] = {
            "health": cfg.weight_health,
            "shield": cfg.weight_shield,
            "rapid_fire": cfg.weight_rapid_fire,
            "big_gun": cfg.weight_big_gun,
            "triple_shot": cfg.weight_triple_shot,
            "speed_boost": cfg.weight_speed_boost,
            "spread_shot": cfg.weight_spread_shot,
            "free_move": cfg.weight_free_move,
        }
        weights = {t: base_weights[t] for t in available if t in base_weights}

        if self._level_type == "boss":
            for t in ("triple_shot", "shield", "big_gun"):
                if t in weights:
                    weights[t] *= 2.0

        return weights
