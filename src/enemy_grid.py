"""EnemyGrid — manages the enemy formation, movement, shooting, and snapshot state."""

from __future__ import annotations

import random
from typing import Any, Optional

import arcade

from src.enemy_config import EnemyConfig
from src.game_event import GameEvent
from src.sprites.enemy_bullet import EnemyBullet
from src.sprites.enemy_sprite import EnemySprite, ROW_MAPPING, sprite_path_for


class EnemyGrid:
    """Owns all enemy sprites, the grid movement state, and enemy shooting.

    No direct state machine calls — events are returned from update() so
    RUN_LEVEL can drive transitions.  Instantiatable without a display by
    passing *enemy_texture* / *bullet_texture* for tests.
    """

    def __init__(
        self,
        config: EnemyConfig,
        window_width: int,
        window_height: int,
        enemy_texture: Optional[arcade.Texture] = None,
        bullet_texture: Optional[arcade.Texture] = None,
        debug: bool = False,
    ) -> None:
        self._config = config
        self._window_width = window_width
        self._window_height = window_height
        self._enemy_texture = enemy_texture
        self._bullet_texture = bullet_texture
        self._debug = debug

        # Formation offsets: list of (col_offset, row_offset) per grid cell
        self._col_offsets: list[float] = []
        self._row_offsets: list[float] = []

        # Grid origin (top-left anchor of the formation bounding box)
        self._origin_x: float = 0.0
        self._origin_y: float = 0.0

        self._direction: float = 1.0          # 1 = right, -1 = left
        self._drop_direction: int = -1        # -1 = dropping, +1 = rising
        self._spawn_y: float = 0.0            # ceiling: grid rises back to this Y
        self._level: int = 1
        self._speed: float = config.enemy_speed_initial
        self._total_enemies: int = 0
        self._enemies_destroyed: int = 0

        # Level-computed grid dimensions and fire intervals
        self._cols: int = config.enemy_cols_start
        self._rows: int = config.enemy_rows_start
        self._fire_min: float = config.enemy_fire_interval_min_l1
        self._fire_max: float = config.enemy_fire_interval_max_l1

        # Per-column shoot timers {col_index: seconds_until_next_shot}
        self._shoot_timers: dict[int, float] = {}

        # Last known outermost occupied column indices — used as virtual bounds
        # when all ships are temporarily airborne (diving).  Column-index based
        # so they stay valid as the grid moves (no need to update in _move()).
        self._last_right_col: int = 0
        self._last_left_col: int = 0
        self._last_bottom_row: int = 0   # cached bottom row index for airborne fallback

        self._sprite_list = arcade.SpriteList(use_spatial_hash=True)
        self._bullet_list = arcade.SpriteList(use_spatial_hash=False)

    # ------------------------------------------------------------------
    # Setup / spawn
    # ------------------------------------------------------------------

    def setup(self, level: int) -> None:
        """Spawn a fresh enemy formation."""
        self._level = level
        cfg = self._config
        w, h = self._window_width, self._window_height

        # Compute level-scaled grid dimensions and fire intervals
        self._cols = min(
            cfg.enemy_cols_start + (level - 1) * cfg.enemy_cols_per_level,
            cfg.enemy_cols_max,
        )
        self._rows = min(
            cfg.enemy_rows_start + (level - 1) * cfg.enemy_rows_per_level,
            cfg.enemy_rows_max,
        )
        scale = cfg.enemy_fire_interval_scale ** (level - 1)
        self._fire_min = max(cfg.enemy_fire_interval_min_l1 * scale, cfg.enemy_fire_interval_min_cap)
        self._fire_max = max(cfg.enemy_fire_interval_max_l1 * scale, cfg.enemy_fire_interval_max_cap)

        # Fixed column spacing: probe one sprite to get its rendered width,
        # then scale by the config factor (e.g. 1.1 = 10% wider than sprite).
        _probe = EnemySprite(
            color=ROW_MAPPING[0][0],
            ship_type=ROW_MAPPING[0][1],
            col=0,
            row=0,
            texture=self._enemy_texture,
        )
        col_spacing = _probe.width * cfg.enemy_col_width_factor

        # Centre the formation horizontally on the window.
        total_span = (self._cols - 1) * col_spacing
        self._origin_x = w / 2.0 - total_span / 2.0

        # Vertical layout: topmost row at 80% of window height
        top_y = h * 0.80
        row_spacing = (h * 0.30) / max(cfg.enemy_rows_max - 1, 1)

        self._origin_y = top_y
        self._spawn_y = top_y
        self._drop_direction = -1
        self._last_bottom_row = self._rows - 1

        self._col_offsets = [c * col_spacing for c in range(self._cols)]
        self._row_offsets = [r * (-row_spacing) for r in range(self._rows)]

        self._sprite_list = arcade.SpriteList(use_spatial_hash=True)
        self._total_enemies = self._cols * self._rows
        self._enemies_destroyed = 0
        self.recalculate_speed()  # sets initial speed for this level

        # Pre-seed column extent so virtual fallback works immediately.
        self._last_right_col = self._cols - 1
        self._last_left_col  = 0

        for row in range(self._rows):
            color, ship_type = ROW_MAPPING[row % 5]
            for col in range(self._cols):
                sprite = EnemySprite(
                    color=color,
                    ship_type=ship_type,
                    col=col,
                    row=row,
                    texture=self._enemy_texture,
                )
                sprite.center_x = self._origin_x + self._col_offsets[col]
                sprite.center_y = self._origin_y + self._row_offsets[row]
                sprite.home_x = sprite.center_x
                sprite.home_y = sprite.center_y
                self._sprite_list.append(sprite)

        self._shoot_timers = {
            col: random.uniform(self._fire_min, self._fire_max)
            for col in range(self._cols)
        }
        self._bullet_list = arcade.SpriteList(use_spatial_hash=False)

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------

    def update(
        self,
        delta_time: float,
        player_ship: Optional[arcade.Sprite],
    ) -> list[GameEvent]:
        """Move grid, handle shooting, check collisions.  Returns events."""
        events: list[GameEvent] = []

        self._move(delta_time)
        self.check_boundary()

        # Per-enemy bottom snap: if an enemy leaves the bottom of the window,
        # teleport it directly to its spawn-time home position.
        # Future diving recovery will reuse home_x/home_y with an animated path.
        for enemy in self._sprite_list:  # type: ignore[attr-defined]
            if enemy.bottom <= 0:
                enemy.center_x = enemy.home_x
                enemy.center_y = enemy.home_y

        # Update enemy bullets
        for bullet in list(self._bullet_list):  # type: ignore[attr-defined]
            bullet.update(delta_time)

        # Enemy shooting
        bottom_enemies = self.get_bottom_enemies()
        cols_with_bullet = {
            int(b.center_x) for b in self._bullet_list  # type: ignore[attr-defined]
        }
        _ = cols_with_bullet  # used implicitly via per-column lock below

        # Track which columns already have an active bullet
        active_cols: set[int] = set()
        for bullet in self._bullet_list:  # type: ignore[attr-defined]
            # Identify bullet's column via proximity to col offsets
            for col, sprite in bottom_enemies.items():
                if sprite is not None:
                    if abs(bullet.center_x - sprite.center_x) < 5:
                        active_cols.add(col)
                        break

        cfg = self._config
        for col, enemy in bottom_enemies.items():
            if enemy is None or col in active_cols:
                continue
            self._shoot_timers[col] = self._shoot_timers.get(col, self._fire_max)
            self._shoot_timers[col] -= delta_time
            if self._shoot_timers[col] <= 0.0:
                self._shoot_timers[col] = random.uniform(self._fire_min, self._fire_max)
                bullet = EnemyBullet(
                    x=enemy.center_x,
                    y=enemy.bottom,
                    speed=cfg.enemy_bullet_speed,
                    texture=self._bullet_texture,
                )
                self._bullet_list.append(bullet)
                active_cols.add(col)

        # Collision: enemy bullet vs player ship
        if player_ship is not None:
            hits = arcade.check_for_collision_with_list(player_ship, self._bullet_list)
            if hits:
                for b in hits:
                    b.remove_from_sprite_lists()
                events.append(GameEvent.PLAYER_KILLED)
                return events

            # Collision: enemy sprite vs player ship
            hits = arcade.check_for_collision_with_list(player_ship, self._sprite_list)
            if hits:
                events.append(GameEvent.PLAYER_KILLED)
                return events

        return events

    # ------------------------------------------------------------------
    # Player bullet hit
    # ------------------------------------------------------------------

    def apply_player_bullet(self, bullet: arcade.Sprite) -> Optional[tuple[float, float, int]]:
        """Check *bullet* against the grid.

        Returns (cx, cy, points) on a hit, or None on a miss.
        Points are row-based (top row highest) plus a per-5-level band bonus.
        Caller is responsible for removing the bullet.
        """
        hits = arcade.check_for_collision_with_list(bullet, self._sprite_list)
        if not hits:
            return None
        enemy = hits[0]  # at most one enemy hit per bullet
        cx, cy = enemy.center_x, enemy.center_y
        row_pts = (self._rows - enemy.row) * 10
        band_bonus = ((self._level - 1) // 5) * 10
        points = row_pts + band_bonus
        enemy.remove_from_sprite_lists()
        self._enemies_destroyed += 1
        self.recalculate_speed()
        self._update_col_cache()
        return cx, cy, points

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_bottom_enemies(self) -> dict[int, Optional[EnemySprite]]:
        """Returns {col: lowest-surviving EnemySprite} for each column."""
        bottom: dict[int, Optional[EnemySprite]] = {
            c: None for c in range(self._cols)
        }
        for sprite in self._sprite_list:  # type: ignore[attr-defined]
            col = sprite.col
            current = bottom.get(col)
            if current is None or sprite.row > current.row:
                bottom[col] = sprite
        return bottom

    @property
    def velocity(self) -> tuple[float, float]:
        """Current horizontal velocity of the grid for momentum transfer."""
        return (self._direction * self._speed, 0.0)

    def is_cleared(self) -> bool:
        return len(self._sprite_list) == 0

    def get_sprite_list(self) -> arcade.SpriteList:
        return self._sprite_list

    def get_bullet_sprite_list(self) -> arcade.SpriteList:
        return self._bullet_list

    # ------------------------------------------------------------------
    # Dive hooks
    # ------------------------------------------------------------------

    def remove_for_dive(self, ship: "EnemySprite") -> None:
        """Extract *ship* from the formation (slot becomes visually empty).

        The ship is not counted as destroyed — speed is not recalculated here.
        The grid boundary check naturally skips the now-absent sprite.
        """
        ship.remove_from_sprite_lists()

    def get_slot_position(self, col: int, row: int) -> tuple[float, float]:
        """Return the current world position of grid slot (col, row)."""
        return (
            self._origin_x + self._col_offsets[col],
            self._origin_y + self._row_offsets[row],
        )

    def return_from_dive(self, ship: "EnemySprite") -> None:
        """Re-insert an EnemySprite back into the formation after a completed dive.

        Snaps to the current grid position (which may have drifted since launch).
        """
        self._sprite_list.append(ship)
        ship.center_x = self._origin_x + self._col_offsets[ship.col]
        ship.center_y = self._origin_y + self._row_offsets[ship.row]
        ship.home_x = ship.center_x
        ship.home_y = ship.center_y
        self._oob_check(ship, "return_from_dive")
        if self._debug:
            print(
                f"[GRID] return_from_dive col={ship.col} row={ship.row} "
                f"placed at ({ship.center_x:.0f}, {ship.center_y:.0f}) "
                f"origin_x={self._origin_x:.0f} "
                f"cached cols L={self._last_left_col} R={self._last_right_col}"
            )

    # ------------------------------------------------------------------
    # Speed / boundary
    # ------------------------------------------------------------------

    def recalculate_speed(self) -> None:
        """speed = initial × 1.15^(level-1)  +  sqrt(kill_pct) × max_bonus.

        Multiplicative base ensures the level ramp feels proportionally faster.
        Square-root kill curve keeps classic feel: big jump on first kill,
        steady acceleration to the last enemy.
        """
        cfg = self._config
        level_floor = cfg.enemy_speed_initial * ((1.0 + cfg.enemy_speed_level_pct) ** (self._level - 1))
        pct = self._enemies_destroyed / max(self._total_enemies, 1)
        self._speed = level_floor + (pct ** 0.5) * cfg.enemy_speed_max_bonus

    def check_boundary(self) -> None:
        """Bounce off margins using grid-position geometry (not sprite pixel edges).

        Edges are computed from _origin_x + _col_offsets[outermost_col] so that
        different sprite sizes don't affect when bouncing occurs.  When all ships
        are temporarily airborne the last-known outermost column indices are reused
        — they stay valid as the grid moves because they're index-based.
        """
        margin = self._config.enemy_side_margin
        drop   = self._config.enemy_drop_distance

        sprites = list(self._sprite_list)  # type: ignore[attr-defined]
        if sprites:
            right_col = max(s.col for s in sprites)
            left_col  = min(s.col for s in sprites)
            self._last_right_col = right_col
            self._last_left_col  = left_col
        elif self._col_offsets:
            # All ships temporarily airborne — use cached column indices.
            right_col = self._last_right_col
            left_col  = self._last_left_col
        else:
            return

        right_edge = self._origin_x + self._col_offsets[right_col]
        left_edge  = self._origin_x + self._col_offsets[left_col]

        if self._direction > 0:
            if right_edge >= self._window_width - margin:
                self._direction = -1.0
                self._drop(drop)
                self._check_vertical_boundary()
                if self._debug:
                    print(
                        f"[GRID] BOUNCE >< at right_col={right_col} "
                        f"right_edge={right_edge:.0f} origin_x={self._origin_x:.0f}"
                    )
        else:
            if left_edge <= margin:
                self._direction = 1.0
                self._drop(drop)
                self._check_vertical_boundary()
                if self._debug:
                    print(
                        f"[GRID] BOUNCE <> at left_col={left_col} "
                        f"left_edge={left_edge:.0f} origin_x={self._origin_x:.0f}"
                    )

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def to_snapshot(self) -> dict[str, Any]:
        """Serialise full grid state (projectiles included)."""
        enemies = []
        for sprite in self._sprite_list:  # type: ignore[attr-defined]
            col_off = self._col_offsets[sprite.col] if sprite.col < len(self._col_offsets) else 0.0
            row_off = self._row_offsets[sprite.row] if sprite.row < len(self._row_offsets) else 0.0
            enemies.append({
                "pos": [sprite.center_x, sprite.center_y],
                "home": [sprite.home_x, sprite.home_y],
                "formation_pos": [
                    self._origin_x + col_off,
                    self._origin_y + row_off,
                ],
                "diving": False,
                "col": sprite.col,
                "row": sprite.row,
                "color": sprite.color_name,
                "ship_type": sprite.ship_type,
            })
        projectiles = [
            {"x": b.center_x, "y": b.center_y}
            for b in self._bullet_list  # type: ignore[attr-defined]
        ]
        return {
            "enemies": enemies,
            "level": self._level,
            "direction": self._direction,
            "speed": self._speed,
            "shoot_timers": dict(self._shoot_timers),
            "projectiles": projectiles,
            "origin_x": self._origin_x,
            "origin_y": self._origin_y,
            "drop_direction": self._drop_direction,
            "spawn_y": self._spawn_y,
            "last_bottom_row": self._last_bottom_row,
            "col_offsets": list(self._col_offsets),
            "row_offsets": list(self._row_offsets),
            "total_enemies": self._total_enemies,
            "enemies_destroyed": self._enemies_destroyed,
        }

    @classmethod
    def from_snapshot(
        cls,
        snapshot: dict[str, Any],
        config: EnemyConfig,
        window_width: int,
        window_height: int,
        enemy_texture: Optional[arcade.Texture] = None,
        bullet_texture: Optional[arcade.Texture] = None,
        debug: bool = False,
    ) -> "EnemyGrid":
        """Restore an EnemyGrid from a saved snapshot.

        Spawn safety must already have been applied to the snapshot before
        calling this (done by apply_spawn_safety() in START_LEVEL).
        """
        grid = cls(config, window_width, window_height, enemy_texture, bullet_texture, debug=debug)
        grid._level = int(snapshot.get("level", 1))
        level = grid._level
        grid._cols = min(
            config.enemy_cols_start + (level - 1) * config.enemy_cols_per_level,
            config.enemy_cols_max,
        )
        grid._rows = min(
            config.enemy_rows_start + (level - 1) * config.enemy_rows_per_level,
            config.enemy_rows_max,
        )
        scale = config.enemy_fire_interval_scale ** (level - 1)
        grid._fire_min = max(config.enemy_fire_interval_min_l1 * scale, config.enemy_fire_interval_min_cap)
        grid._fire_max = max(config.enemy_fire_interval_max_l1 * scale, config.enemy_fire_interval_max_cap)
        grid._direction = float(snapshot.get("direction", 1.0))
        grid._speed = float(snapshot.get("speed", config.enemy_speed_initial))
        grid._origin_x = float(snapshot.get("origin_x", 0.0))
        grid._origin_y = float(snapshot.get("origin_y", 0.0))
        grid._drop_direction = int(snapshot.get("drop_direction", -1))
        grid._spawn_y = float(snapshot.get("spawn_y", grid._origin_y))
        grid._last_bottom_row = int(snapshot.get("last_bottom_row", grid._rows - 1))
        grid._col_offsets = list(snapshot.get("col_offsets", []))
        grid._row_offsets = list(snapshot.get("row_offsets", []))
        grid._total_enemies = int(snapshot.get("total_enemies", 1))
        grid._enemies_destroyed = int(snapshot.get("enemies_destroyed", 0))
        grid._shoot_timers = {
            int(k): float(v) for k, v in snapshot.get("shoot_timers", {}).items()
        }

        grid._sprite_list = arcade.SpriteList(use_spatial_hash=True)
        for edata in snapshot.get("enemies", []):
            color = edata["color"]
            ship_type = int(edata["ship_type"])
            col = int(edata["col"])
            row = int(edata["row"])
            sprite = EnemySprite(
                color=color,
                ship_type=ship_type,
                col=col,
                row=row,
                texture=enemy_texture,
            )
            pos = edata["pos"]
            sprite.center_x = float(pos[0])
            sprite.center_y = float(pos[1])
            home = edata.get("home", pos)
            sprite.home_x = float(home[0])
            sprite.home_y = float(home[1])
            grid._sprite_list.append(sprite)

        # Seed cached column extents from restored sprites (or full formation).
        sprites = list(grid._sprite_list)
        if sprites:
            grid._last_right_col = max(s.col for s in sprites)
            grid._last_left_col  = min(s.col for s in sprites)
        elif grid._col_offsets:
            grid._last_right_col = len(grid._col_offsets) - 1
            grid._last_left_col  = 0

        # Projectiles are stripped by SAVE_SNAPSHOT_AND_SWITCH before storage,
        # but restore them if present (e.g. from a test snapshot).
        grid._bullet_list = arcade.SpriteList(use_spatial_hash=False)
        for pdata in snapshot.get("projectiles", []):
            bullet = EnemyBullet(
                x=float(pdata["x"]),
                y=float(pdata["y"]),
                speed=config.enemy_bullet_speed,
                texture=bullet_texture,
            )
            grid._bullet_list.append(bullet)

        return grid

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_vertical_boundary(self) -> None:
        """Flip drop direction at bottom margin or spawn Y ceiling.

        Uses cached bottom row index as fallback when all ships are airborne,
        mirroring the _last_right_col / _last_left_col pattern.
        """
        sprites = list(self._sprite_list)  # type: ignore[attr-defined]
        if sprites:
            bottom_row = max(s.row for s in sprites)
            self._last_bottom_row = bottom_row
        elif self._row_offsets:
            bottom_row = self._last_bottom_row
        else:
            return

        bottom_y = self._origin_y + self._row_offsets[bottom_row]

        if self._drop_direction == -1 and bottom_y <= self._config.enemy_bottom_margin:
            self._drop_direction = 1
        elif self._drop_direction == 1 and self._origin_y >= self._spawn_y:
            # Snap to ceiling to avoid float drift, then resume dropping
            self._origin_y = self._spawn_y
            for s in sprites:
                s.center_y = self._origin_y + self._row_offsets[s.row]
            self._drop_direction = -1

    def _update_col_cache(self) -> None:
        """Recompute cached outermost column indices from current sprite list."""
        sprites = list(self._sprite_list)
        if sprites:
            self._last_right_col = max(s.col for s in sprites)
            self._last_left_col  = min(s.col for s in sprites)

    def _oob_check(self, sprite: "EnemySprite", context: str) -> None:
        """Log if sprite has moved outside the window bounds (debug mode only)."""
        if not self._debug:
            return
        if sprite.center_x < 0 or sprite.center_x > self._window_width:
            print(
                f"[OOB] grid {context} col={sprite.col} row={sprite.row} "
                f"x={sprite.center_x:.1f} window_w={self._window_width}"
            )
            pass  # set breakpoint here

    def _move(self, delta_time: float) -> None:
        dx = self._direction * self._speed * delta_time
        self._origin_x += dx
        for sprite in self._sprite_list:  # type: ignore[attr-defined]
            sprite.center_x += dx
            self._oob_check(sprite, "_move")

    def _drop(self, distance: float) -> None:
        delta = distance * self._drop_direction   # negative = down, positive = up
        self._origin_y += delta
        for sprite in self._sprite_list:  # type: ignore[attr-defined]
            sprite.center_y += delta
            self._oob_check(sprite, "_drop")
