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
    ) -> None:
        self._config = config
        self._window_width = window_width
        self._window_height = window_height
        self._enemy_texture = enemy_texture
        self._bullet_texture = bullet_texture

        # Formation offsets: list of (col_offset, row_offset) per grid cell
        self._col_offsets: list[float] = []
        self._row_offsets: list[float] = []

        # Grid origin (top-left anchor of the formation bounding box)
        self._origin_x: float = 0.0
        self._origin_y: float = 0.0

        self._direction: float = 1.0          # 1 = right, -1 = left
        self._speed: float = config.enemy_speed_initial
        self._total_enemies: int = 0
        self._enemies_destroyed: int = 0

        # Per-column shoot timers {col_index: seconds_until_next_shot}
        self._shoot_timers: dict[int, float] = {}

        self._sprite_list = arcade.SpriteList(use_spatial_hash=True)
        self._bullet_list = arcade.SpriteList(use_spatial_hash=False)

    # ------------------------------------------------------------------
    # Setup / spawn
    # ------------------------------------------------------------------

    def setup(self, level: int) -> None:  # noqa: ARG002  (level reserved for future use)
        """Spawn a fresh enemy formation."""
        cfg = self._config
        w, h = self._window_width, self._window_height
        margin = cfg.enemy_side_margin

        # Horizontal spacing: divide usable width into (cols + 2) slots so
        # there is one empty column-width of buffer on each side of the grid.
        # This gives the formation room to travel before bouncing down.
        usable_w = w - 2 * margin
        col_spacing = usable_w / (cfg.enemy_cols + 1)

        # Vertical layout: topmost row at 80% of window height
        top_y = h * 0.80
        row_spacing = (h * 0.30) / max(cfg.enemy_rows - 1, 1) if cfg.enemy_rows > 1 else 0.0

        # Grid origin = first enemy is one buffer column in from the left margin
        self._origin_x = margin + col_spacing
        self._origin_y = top_y

        self._col_offsets = [c * col_spacing for c in range(cfg.enemy_cols)]
        self._row_offsets = [r * (-row_spacing) for r in range(cfg.enemy_rows)]

        self._sprite_list = arcade.SpriteList(use_spatial_hash=True)
        self._total_enemies = cfg.enemy_cols * cfg.enemy_rows
        self._enemies_destroyed = 0
        self._speed = cfg.enemy_speed_initial

        for row in range(cfg.enemy_rows):
            color, ship_type = ROW_MAPPING[row % 5]
            for col in range(cfg.enemy_cols):
                sprite = EnemySprite(
                    color=color,
                    ship_type=ship_type,
                    col=col,
                    row=row,
                    texture=self._enemy_texture,
                )
                sprite.center_x = self._origin_x + self._col_offsets[col]
                sprite.center_y = self._origin_y + self._row_offsets[row]
                self._sprite_list.append(sprite)

        self._shoot_timers = {
            col: random.uniform(cfg.enemy_fire_interval_min, cfg.enemy_fire_interval_max)
            for col in range(cfg.enemy_cols)
        }
        self._bullet_list = arcade.SpriteList(use_spatial_hash=False)

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------

    def update(
        self,
        delta_time: float,
        player_ship: Optional[arcade.Sprite],
        ship_zone_top: float,
    ) -> list[GameEvent]:
        """Move grid, handle shooting, check collisions.  Returns events."""
        events: list[GameEvent] = []

        self._move(delta_time)
        self.check_boundary()

        # Check if grid has descended into the player zone
        for enemy in list(self._sprite_list):  # type: ignore[attr-defined]
            if enemy.bottom <= ship_zone_top:
                events.append(GameEvent.PLAYER_KILLED)
                return events  # no need to process further this frame

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
            self._shoot_timers[col] = self._shoot_timers.get(col, cfg.enemy_fire_interval_max)
            self._shoot_timers[col] -= delta_time
            if self._shoot_timers[col] <= 0.0:
                self._shoot_timers[col] = random.uniform(
                    cfg.enemy_fire_interval_min, cfg.enemy_fire_interval_max
                )
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

    def apply_player_bullet(self, bullet: arcade.Sprite) -> Optional[tuple[float, float]]:
        """Check *bullet* against the grid.

        Returns the hit enemy's center (cx, cy) on a hit, or None on a miss.
        Caller is responsible for removing the bullet.
        """
        hits = arcade.check_for_collision_with_list(bullet, self._sprite_list)
        if not hits:
            return None
        enemy = hits[0]  # at most one enemy hit per bullet
        cx, cy = enemy.center_x, enemy.center_y
        enemy.remove_from_sprite_lists()
        self._enemies_destroyed += 1
        self.recalculate_speed()
        return cx, cy

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_bottom_enemies(self) -> dict[int, Optional[EnemySprite]]:
        """Returns {col: lowest-surviving EnemySprite} for each column."""
        bottom: dict[int, Optional[EnemySprite]] = {
            c: None for c in range(self._config.enemy_cols)
        }
        for sprite in self._sprite_list:  # type: ignore[attr-defined]
            col = sprite.col
            current = bottom.get(col)
            if current is None or sprite.row > current.row:
                bottom[col] = sprite
        return bottom

    def is_cleared(self) -> bool:
        return len(self._sprite_list) == 0

    def get_sprite_list(self) -> arcade.SpriteList:
        return self._sprite_list

    def get_bullet_sprite_list(self) -> arcade.SpriteList:
        return self._bullet_list

    # ------------------------------------------------------------------
    # Speed / boundary
    # ------------------------------------------------------------------

    def recalculate_speed(self) -> None:
        cfg = self._config
        pct = self._enemies_destroyed / max(self._total_enemies, 1)
        self._speed = cfg.enemy_speed_initial + pct * cfg.enemy_speed_max_bonus

    def check_boundary(self) -> None:
        """Bounce off margins using the outermost *surviving* enemy."""
        sprites = list(self._sprite_list)  # type: ignore[attr-defined]
        if not sprites:
            return
        margin = self._config.enemy_side_margin
        drop = self._config.enemy_drop_distance

        if self._direction > 0:
            rightmost = max(s.right for s in sprites)
            if rightmost >= self._window_width - margin:
                self._direction = -1.0
                self._drop(drop)
        else:
            leftmost = min(s.left for s in sprites)
            if leftmost <= margin:
                self._direction = 1.0
                self._drop(drop)

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
            "direction": self._direction,
            "speed": self._speed,
            "shoot_timers": dict(self._shoot_timers),
            "projectiles": projectiles,
            "origin_x": self._origin_x,
            "origin_y": self._origin_y,
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
    ) -> "EnemyGrid":
        """Restore an EnemyGrid from a saved snapshot.

        Spawn safety must already have been applied to the snapshot before
        calling this (done by apply_spawn_safety() in START_LEVEL).
        """
        grid = cls(config, window_width, window_height, enemy_texture, bullet_texture)
        grid._direction = float(snapshot.get("direction", 1.0))
        grid._speed = float(snapshot.get("speed", config.enemy_speed_initial))
        grid._origin_x = float(snapshot.get("origin_x", 0.0))
        grid._origin_y = float(snapshot.get("origin_y", 0.0))
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
            grid._sprite_list.append(sprite)

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

    def _move(self, delta_time: float) -> None:
        dx = self._direction * self._speed * delta_time
        self._origin_x += dx
        for sprite in self._sprite_list:  # type: ignore[attr-defined]
            sprite.center_x += dx

    def _drop(self, distance: float) -> None:
        self._origin_y -= distance
        for sprite in self._sprite_list:  # type: ignore[attr-defined]
            sprite.center_y -= distance
