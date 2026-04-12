"""LevelFactory — maps level number to a BaseLevel instance.

All level creation and snapshot restoration is centralised here so
that RunLevelView and GameStateManager never import EnemyGrid or
DiveController directly.
"""

from __future__ import annotations

from typing import Any, Optional

from src.levels.base_level import BaseLevel


def create_level(
    level_number: int,
    config: Any,
    window_width: int,
    window_height: int,
    snapshot: Optional[dict] = None,
) -> BaseLevel:
    """Create or restore the appropriate level for *level_number*.

    If *snapshot* is provided, restores from saved state.
    Otherwise creates a fresh level and calls setup().
    """
    if snapshot is not None:
        return _restore_from_snapshot(snapshot, config, window_width, window_height)
    level_type = _get_level_type(level_number)
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
            level = StandardLevel(grid, dive)
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
        case _:
            raise ValueError(f"Cannot restore unknown level type: {level_type!r}")
