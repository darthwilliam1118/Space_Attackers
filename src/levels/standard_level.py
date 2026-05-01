"""StandardLevel — wraps EnemyGrid + DiveController behind BaseLevel interface.

Owns the optional SAPowerUpManager and forwards lifecycle calls to it.
"""

from __future__ import annotations

import time
from typing import Any, Optional

import arcade
from agf.events import GameEvent
from agf.levels.base_level import BaseLevel

from src.dive_controller import DiveController
from src.enemy_grid import EnemyGrid
from src.powerups.sa_manager import SAPowerUpManager


class StandardLevel(BaseLevel):
    """Standard space-shooter level: fixed grid + periodic dive attacks."""

    def __init__(
        self,
        grid: EnemyGrid,
        dive_ctrl: DiveController,
        powerup_manager: Optional[SAPowerUpManager] = None,
    ) -> None:
        self._grid = grid
        self._dive = dive_ctrl
        self._powerup_manager = powerup_manager
        self._last_timing: dict[str, float | None] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def level_type(self) -> str:
        return "standard"

    def setup(self, level_number: int) -> None:
        self._grid.setup(level_number)
        self._dive.setup(level_number, self._grid)
        if self._powerup_manager is not None:
            self._powerup_manager.setup(level_number, self.level_type)

    # ------------------------------------------------------------------
    # Per-frame
    # ------------------------------------------------------------------

    def update(
        self,
        delta_time: float,
        player_ship: Any,
        player_bullets: arcade.SpriteList,
        frame_count: int = 0,
    ) -> list[GameEvent]:
        events: list[GameEvent] = []

        check_enemy_bullets = frame_count % 2 == 0
        check_enemy_bodies = frame_count % 3 == 1
        check_enemy_shooting = frame_count % 3 == 0
        check_dive_bombs = frame_count % 2 == 1
        check_dive_bodies = frame_count % 3 == 2

        _t0 = time.perf_counter()
        events += self._grid.update(
            delta_time,
            player_ship,
            check_bullets=check_enemy_bullets,
            check_bodies=check_enemy_bodies,
            check_shooting=check_enemy_shooting,
            frame_count=frame_count,
        )
        _t1 = time.perf_counter()
        events += self._dive.update(
            delta_time,
            self._grid,
            player_ship,
            player_bullets,
            check_bodies=check_dive_bodies,
            check_bombs=check_dive_bombs,
        )
        _t2 = time.perf_counter()

        self._last_timing = {
            **self._grid.last_timing,
            **self._dive.last_timing,
            "grid_total": _t1 - _t0,
            "dive_total": _t2 - _t1,
        }
        if self._powerup_manager is not None:
            collected = self._powerup_manager.update(
                delta_time,
                player_ship,
                self._effect_context(),
                self.get_enemy_x_positions(),
            )
            for _ in collected:
                events.append(GameEvent.POWERUP_COLLECTED)
        return events

    def draw(self) -> None:
        self._grid.get_sprite_list().draw()
        self._grid.get_bullet_sprite_list().draw()
        self._dive.get_all_sprites().draw()
        self._dive.get_all_bullets().draw()
        if self._powerup_manager is not None:
            self._powerup_manager.draw()

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def is_cleared(self) -> bool:
        return self._grid.is_cleared() and not self._dive.has_any_airborne()

    # ------------------------------------------------------------------
    # Bullet collision
    # ------------------------------------------------------------------

    def apply_player_bullet(self, bullet: Any) -> Any:
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

    def get_all_enemy_sprites(self) -> list[arcade.Sprite]:
        # Plain list — appending shared sprites into a fresh arcade.SpriteList
        # every frame registers them with that temp list (Sprite.sprite_lists),
        # creating a cycle the disabled cyclic GC cannot break.
        return list(self._grid.get_sprite_list()) + list(self._dive.get_all_sprites())

    def get_enemy_bullet_sprite_list(self) -> list[arcade.Sprite]:
        return list(self._grid.get_bullet_sprite_list()) + list(self._dive.get_all_bullets())

    # ------------------------------------------------------------------
    # Power-ups
    # ------------------------------------------------------------------

    def get_powerup_manager(self) -> Optional[SAPowerUpManager]:
        return self._powerup_manager

    def get_enemy_x_positions(self) -> list[float]:
        return [s.center_x for s in self._grid.get_sprite_list()]

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

    def get_last_timing(self) -> dict[str, float | None]:
        return self._last_timing

    def debug_force_dive(self, player_x: float) -> None:
        self._dive.launch_group(self._grid, player_x)

    # ------------------------------------------------------------------
    # Snapshot / restore
    # ------------------------------------------------------------------

    def to_snapshot(self) -> dict:
        snapshot = self._grid.to_snapshot()
        snapshot["level_type"] = "standard"
        snapshot["diving"] = self._dive.to_snapshot()
        if self._powerup_manager is not None:
            snapshot["powerups"] = self._powerup_manager.to_snapshot()
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

        level_number = snapshot.get("diving", {}).get("level", 1)

        powerup_manager: Optional[SAPowerUpManager] = None
        if config is not None and getattr(config, "powerups", None) is not None:
            pu_snapshot = snapshot.get("powerups")
            if pu_snapshot is not None:
                powerup_manager = SAPowerUpManager.from_snapshot(  # type: ignore[assignment]
                    pu_snapshot,
                    config.powerups,
                    window_width,
                    window_height,
                    sprite_scale=scale,
                    level_number=level_number,
                    level_type="standard",
                )
            else:
                powerup_manager = SAPowerUpManager(
                    config.powerups,
                    window_width,
                    window_height,
                    sprite_scale=scale,
                )
                powerup_manager.setup(level_number, "standard")

        return cls(grid, dive_ctrl, powerup_manager)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _effect_context(self) -> dict:
        # Power-up sprites already know window dims via the manager;
        # this dict is what gets passed to effect.apply / .remove.
        # Width/height pulled from the manager so we don't duplicate state.
        return {
            "window_width": self._powerup_manager._window_width,  # type: ignore[union-attr]
            "window_height": self._powerup_manager._window_height,  # type: ignore[union-attr]
            "sprite_scale": self._powerup_manager._scale,  # type: ignore[union-attr]
        }
