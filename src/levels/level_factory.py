"""LevelFactory — maps level number to a BaseLevel instance.

All level creation and snapshot restoration is centralised here so
that RunLevelView and GameStateManager never import EnemyGrid or
DiveController directly.
"""

from __future__ import annotations

from typing import Any, Optional

from agf.levels.base_level import BaseLevel


def create_level(
    level_number: int,
    config: Any,
    window_width: int,
    window_height: int,
    snapshot: Optional[dict] = None,
    force_level_type: Optional[str] = None,
) -> BaseLevel:
    """Create or restore the appropriate level for *level_number*.

    If *snapshot* is provided, restores from saved state.
    If *force_level_type* is given, overrides the type detection (used to
    insert meteor storms at the right point in the level sequence).
    Otherwise creates a fresh level and calls setup().
    """
    if snapshot is not None:
        return _restore_from_snapshot(snapshot, config, window_width, window_height)
    level_type = force_level_type if force_level_type is not None else _get_level_type(level_number)
    return _create_fresh(level_type, level_number, config, window_width, window_height)


def _get_level_type(level_number: int) -> str:
    """Define the level sequence.

    All levels are standard for now. Extend here when new level
    types are added:
      if level_number % 10 == 0: return "boss"
      if level_number % 5 == 0: return "bonus"
    """
    return "standard"


def _create_fresh(
    level_type: str,
    level_number: int,
    config: Any,
    window_width: int,
    window_height: int,
) -> BaseLevel:
    match level_type:
        case "standard":
            from src.dive_controller import DiveController
            from src.diving_config import DivingConfig
            from src.enemy_config import EnemyConfig
            from src.enemy_grid import EnemyGrid
            from src.levels.standard_level import StandardLevel
            from src.powerups.sa_manager import SAPowerUpManager

            cfg_e = config.enemies if config else EnemyConfig()
            cfg_d = config.diving if config else DivingConfig()
            debug = config.debug if config else False
            scale = config.sprite_scale if config else 1.0
            hp_dur = config.ui.hp_bar_duration if config else 1.0

            grid = EnemyGrid(
                cfg_e,
                window_width,
                window_height,
                debug=debug,
                sprite_scale=scale,
                hp_bar_duration=hp_dur,
            )
            dive = DiveController(
                cfg_d,
                window_width,
                window_height,
                debug=debug,
                sprite_scale=scale,
                hp_bar_duration=hp_dur,
            )
            powerup_manager = None
            if config is not None and getattr(config, "powerups", None) is not None:
                powerup_manager = SAPowerUpManager(
                    config.powerups,
                    window_width,
                    window_height,
                    sprite_scale=scale,
                )
            level = StandardLevel(grid, dive, powerup_manager)
            level.setup(level_number)
            return level
        case "meteor":
            from src.levels.meteor_level import MeteorLevel
            from src.meteor_config import MeteorConfig

            meteor_cfg = config.meteors if config is not None else MeteorConfig()
            scale = config.sprite_scale if config is not None else 1.0
            powerup_manager = None
            if config is not None and getattr(config, "powerups", None) is not None:
                from src.powerups.sa_manager import SAPowerUpManager

                powerup_manager = SAPowerUpManager(
                    config.powerups, window_width, window_height, sprite_scale=scale
                )
            level = MeteorLevel(meteor_cfg, window_width, window_height, powerup_manager)
            level.setup(level_number)
            return level

        case _:
            raise ValueError(f"Unknown level type: {level_type!r}")


def _restore_from_snapshot(
    snapshot: dict,
    config: Any,
    window_width: int,
    window_height: int,
) -> BaseLevel:
    # Default to "standard" for backwards compatibility with snapshots
    # that predate this refactor (they have no level_type key).
    level_type = snapshot.get("level_type", "standard")
    match level_type:
        case "standard":
            from src.levels.standard_level import StandardLevel

            return StandardLevel.from_snapshot(snapshot, config, window_width, window_height)
        case "meteor":
            from src.levels.meteor_level import MeteorLevel

            return MeteorLevel.from_snapshot(snapshot, config, window_width, window_height)
        case _:
            raise ValueError(f"Cannot restore unknown level type: {level_type!r}")
