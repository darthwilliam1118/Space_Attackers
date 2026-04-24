"""BossPowerUpSpawner + BossPowerUpManager — restricted to boss-compatible effects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agf.powerups.effect_base import PowerUpEffect

from src.powerups.effects.big_gun import BigGunEffect
from src.powerups.effects.shield import ShieldEffect
from src.powerups.sa_manager import SAPowerUpManager
from src.powerups.sa_spawner import SAPowerUpSpawner

if TYPE_CHECKING:
    from src.boss_config import BossConfig
    from src.powerups.sa_powerup_config import SAPowerUpConfig


class BossPowerUpSpawner(SAPowerUpSpawner):
    """Spawner restricted to shield, big_gun, and spread_shot only.

    Weights come from BossConfig so the boss's power-up rate is tunable
    separately from the player's.  Unlocks at all levels — the boss exists
    only on level-5 multiples where all player types are already unlocked,
    so no level-gating is needed.
    """

    def __init__(self, config: "SAPowerUpConfig", boss_cfg: "BossConfig") -> None:
        self._boss_cfg = boss_cfg
        super().__init__(config)

    def _available_types(self) -> list[str]:
        return ["shield", "big_gun", "spread_shot"]

    def _build_weight_table(self) -> dict[str, float]:
        bc = self._boss_cfg
        return {
            "shield": bc.boss_pu_weight_shield,
            "big_gun": bc.boss_pu_weight_big_gun,
            "spread_shot": bc.boss_pu_weight_spread_shot,
        }


class BossPowerUpManager(SAPowerUpManager):
    """Power-up manager targeting the boss sprite.

    Power-up pickups fall from the top and the boss sprite collects them.
    Only shield, big_gun, and spread_shot are available.  SpreadShotEffect
    is replaced by BossSpreadShotEffect which sets _spread_chance_override
    instead of calling PlayerShip-specific methods.
    """

    def __init__(
        self,
        config: "SAPowerUpConfig",
        boss_cfg: "BossConfig",
        window_width: int,
        window_height: int,
        sprite_scale: float = 1.0,
    ) -> None:
        # Set before super().__init__() so create_spawner() can access it
        self._boss_cfg = boss_cfg
        super().__init__(config, window_width, window_height, sprite_scale)

    def create_spawner(self) -> BossPowerUpSpawner:
        return BossPowerUpSpawner(self._config, self._boss_cfg)  # type: ignore[arg-type]

    def create_effect(self, effect_type: str) -> PowerUpEffect:
        cfg: "SAPowerUpConfig" = self._config  # type: ignore[assignment]
        match effect_type:
            case "spread_shot":
                from src.powerups.effects.boss_spread_shot import BossSpreadShotEffect

                return BossSpreadShotEffect(cfg)
            case "shield":
                return ShieldEffect(cfg)
            case "big_gun":
                return BigGunEffect(cfg)
            case _:
                raise ValueError(f"BossPowerUpManager: unknown effect type {effect_type!r}")
