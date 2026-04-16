"""StandardLevel — wraps EnemyGrid + DiveController behind BaseLevel interface.

Preserves all existing behaviour exactly. No logic changes to EnemyGrid
or DiveController — this class is a pure adapter.
"""

from __future__ import annotations

from typing import Any, Optional

import arcade
from agf.levels.base_level import BaseLevel

from src.dive_controller import DiveController
from src.enemy_grid import EnemyGrid
from src.game_event import GameEvent


class StandardLevel(BaseLevel):
    """Standard space-shooter level: fixed grid + periodic dive attacks."""

    def __init__(self, grid: EnemyGrid, dive_ctrl: DiveController) -> None:
        self._grid = grid
        self._dive = dive_ctrl

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def level_type(self) -> str:
        return "standard"

    def setup(self, level_number: int) -> None:
        self._grid.setup(level_number)
        self._dive.setup(level_number, self._grid)

    # ------------------------------------------------------------------
    # Per-frame
    # ------------------------------------------------------------------

    def update(
        self,
        delta_time: float,
        player_ship: Any,
        player_bullets: Optional[arcade.SpriteList] = None,
    ) -> list[GameEvent]:
        """Update grid and dive controller.

        player_bullets is passed directly to DiveController so it can
        handle bullet vs diving-ship collision internally (existing behaviour).
        """
        bullets = player_bullets if player_bullets is not None else arcade.SpriteList()
        events: list[GameEvent] = []
        events += self._grid.update(delta_time, player_ship)
        events += self._dive.update(delta_time, self._grid, player_ship, bullets)
        return events

    def draw(self) -> None:
        self._grid.get_sprite_list().draw()
        self._grid.get_bullet_sprite_list().draw()
        self._dive.get_all_sprites().draw()
        self._dive.get_all_bullets().draw()

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def is_cleared(self) -> bool:
        return self._grid.is_cleared() and not self._dive.has_any_airborne()

    # ------------------------------------------------------------------
    # Bullet collision
    # ------------------------------------------------------------------

    def apply_player_bullet(self, bullet: Any) -> Any:
        """Check bullet against the enemy grid only.

        DiveController handles its own bullet collision inside update()
        via the player_bullets list, so diving ships are NOT checked here.
        """
        return self._grid.apply_player_bullet(bullet)

    # ------------------------------------------------------------------
    # Hit reporting
    # ------------------------------------------------------------------

    def consume_pending_hits(self) -> list[tuple[float, float, int]]:
        hits = list(self._grid.consume_pending_hits())
        hits += list(self._dive.consume_pending_hits())
        return hits

    def consume_pending_non_lethal_hits(self) -> list[tuple[float, float]]:
        hits: list[tuple[float, float]] = []
        if hasattr(self._grid, "consume_pending_non_lethal_hits"):
            hits += list(self._grid.consume_pending_non_lethal_hits())
        hits += list(self._dive.consume_pending_non_lethal_hits())
        return hits

    # ------------------------------------------------------------------
    # Sprite lists
    # ------------------------------------------------------------------

    def get_all_enemy_sprites(self) -> arcade.SpriteList:
        combined: arcade.SpriteList = arcade.SpriteList()
        for s in self._grid.get_sprite_list():
            combined.append(s)
        for s in self._dive.get_all_sprites():
            combined.append(s)
        return combined

    def get_enemy_bullet_sprite_list(self) -> arcade.SpriteList:
        combined: arcade.SpriteList = arcade.SpriteList()
        for s in self._grid.get_bullet_sprite_list():
            combined.append(s)
        for s in self._dive.get_all_bullets():
            combined.append(s)
        return combined

    # ------------------------------------------------------------------
    # 2P dive wait
    # ------------------------------------------------------------------

    def has_any_airborne(self) -> bool:
        return self._dive.has_any_airborne()

    def block_new_launches(self) -> None:
        self._dive.new_dive_launches_blocked = True

    # ------------------------------------------------------------------
    # Velocity
    # ------------------------------------------------------------------

    @property
    def velocity(self) -> tuple[float, float]:
        return self._grid.velocity if self._grid is not None else (0.0, 0.0)

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def debug_force_dive(self, player_x: float) -> None:
        self._dive.launch_group(self._grid, player_x)

    # ------------------------------------------------------------------
    # Snapshot / restore
    # ------------------------------------------------------------------

    def to_snapshot(self) -> dict:
        snapshot = self._grid.to_snapshot()
        snapshot["level_type"] = "standard"
        snapshot["diving"] = self._dive.to_snapshot()
        return snapshot

    @classmethod
    def from_snapshot(
        cls,
        snapshot: dict,
        config: Any,
        window_width: int,
        window_height: int,
    ) -> "StandardLevel":
        from src.diving_config import DivingConfig
        from src.enemy_config import EnemyConfig

        enemy_cfg = config.enemies if config else EnemyConfig()
        diving_cfg = config.diving if config else DivingConfig()
        debug = config.debug if config else False
        scale = config.sprite_scale if config else 1.0
        hp_dur = config.ui.hp_bar_duration if config else 1.0

        grid = EnemyGrid.from_snapshot(
            snapshot,
            enemy_cfg,
            window_width,
            window_height,
            debug=debug,
            sprite_scale=scale,
            hp_bar_duration=hp_dur,
        )
        dive_ctrl = DiveController.from_snapshot(
            snapshot.get("diving", {}),
            diving_cfg,
            window_width,
            window_height,
            debug=debug,
            sprite_scale=scale,
            hp_bar_duration=hp_dur,
        )
        return cls(grid, dive_ctrl)
