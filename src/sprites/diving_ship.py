"""DivingShip — an enemy sprite executing a Bézier dive arc."""

from __future__ import annotations

import math
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

import arcade

if TYPE_CHECKING:
    from src.diving_config import DivingConfig
    from src.sprites.enemy_bullet import EnemyBullet
    from src.sprites.enemy_sprite import EnemySprite


class DiveState(Enum):
    WAITING = auto()  # counting down launch_delay before movement starts
    DIVING = auto()  # advancing along waypoint path
    RETURNING = auto()  # path complete; flying directly back to home position
    DONE = auto()  # reached home; ready for re-insertion into grid


class DivingShip(arcade.Sprite):
    """Enemy ship extracted from the grid to follow a Bézier dive arc.

    The ship copies its texture, col, and row from *source_sprite* so it
    appears visually identical to the original grid occupant.

    Bomb trigger: when *center_y* drops below ``window_height * 0.55`` on the
    forward path, the ship fires one EnemyBullet downward.  The bomb is
    available via :py:attr:`get_bomb` until it is consumed by DiveController.

    Pass *texture* to inject a pre-loaded texture (tests, no display needed).
    """

    # How close (pixels) the ship must be to home before declaring DONE.
    _ARRIVAL_THRESHOLD: float = 4.0
    # Degrees per second the ship rotates back to upright during RETURNING.
    _ANGLE_RETURN_RATE: float = 180.0
    # Horizontal distance (pixels) to player that triggers bomb release.
    _AIM_THRESHOLD: float = 30.0

    def __init__(
        self,
        source_sprite: "EnemySprite",
        waypoints: list[tuple[float, float]],
        config: "DivingConfig",
        window_height: int,
        dive_speed: float = 200.0,
        launch_delay: float = 0.0,
        bullet_texture: Optional[arcade.Texture] = None,
        scale: float = 1.0,
    ) -> None:
        super().__init__(source_sprite.texture)
        self.scale = scale
        self._sprite_scale = scale
        self.center_x = source_sprite.center_x
        self.center_y = source_sprite.center_y

        self.col: int = source_sprite.col
        self.row: int = source_sprite.row
        self.color_name: str = source_sprite.color_name

        self._home_x: float = source_sprite.home_x
        self._home_y: float = source_sprite.home_y
        self._waypoints: list[tuple[float, float]] = waypoints
        self._config = config
        self._dive_speed: float = dive_speed
        self._window_height: int = window_height
        self._launch_delay: float = launch_delay
        self._bullet_texture: Optional[arcade.Texture] = bullet_texture

        # Path tracking
        self._path_dist: float = 0.0  # distance travelled along path so far
        self._segment_starts: list[float]  # cumulative distance at each waypoint
        self._total_path_length: float
        self._segment_starts, self._total_path_length = self._precompute_lengths()

        # State
        self._state: DiveState = DiveState.WAITING if launch_delay > 0.0 else DiveState.DIVING
        self._has_fired_bomb: bool = False
        self._pending_bomb: Optional["EnemyBullet"] = None  # set when bomb is fired

        # Lowest y on the dive path — fallback fire point if player aim never lines up.
        self._lowest_path_y: float = min(y for _, y in waypoints)
        self._past_lowest: bool = False  # flips True once we start climbing back up

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_done(self) -> bool:
        return self._state == DiveState.DONE

    @property
    def grid_position(self) -> tuple[int, int]:
        return (self.col, self.row)

    def get_bomb(self) -> Optional["EnemyBullet"]:
        """Return the newly-fired bomb once (consumed after first call)."""
        bomb = self._pending_bomb
        self._pending_bomb = None
        return bomb

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, delta_time: float, player_x: float) -> None:  # type: ignore[override]
        if self._state == DiveState.DONE:
            return

        if self._state == DiveState.WAITING:
            self._launch_delay -= delta_time
            if self._launch_delay <= 0.0:
                self._state = DiveState.DIVING
            return

        if self._state == DiveState.DIVING:
            prev_y = self.center_y
            self._advance_path(delta_time)

            if not self._has_fired_bomb:
                # Detect when we've passed the lowest point and are climbing back up
                if not self._past_lowest and self.center_y > prev_y:
                    self._past_lowest = True

                # Fire when horizontally over the player
                if abs(self.center_x - player_x) <= self._AIM_THRESHOLD:
                    self._fire_bomb()
                # Fallback: fire at the lowest point if we just passed it
                elif self._past_lowest:
                    self._fire_bomb()

            return

        if self._state == DiveState.RETURNING:
            self._move_toward_home(delta_time)
            return

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _precompute_lengths(self) -> tuple[list[float], float]:
        """Compute cumulative arc-length at each waypoint for uniform-speed travel."""
        starts: list[float] = [0.0]
        total = 0.0
        pts = self._waypoints
        for i in range(1, len(pts)):
            dx = pts[i][0] - pts[i - 1][0]
            dy = pts[i][1] - pts[i - 1][1]
            total += math.hypot(dx, dy)
            starts.append(total)
        return starts, total

    def _advance_path(self, delta_time: float) -> None:
        """Move *dive_speed * delta_time* pixels along the waypoint path."""
        self._path_dist += self._dive_speed * delta_time

        if self._path_dist >= self._total_path_length:
            # Reached end of Bézier path — switch to returning
            self.center_x, self.center_y = self._waypoints[-1]
            self._state = DiveState.RETURNING
            return

        # Binary search for the segment containing _path_dist
        lo, hi = 0, len(self._segment_starts) - 1
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if self._segment_starts[mid] <= self._path_dist:
                lo = mid
            else:
                hi = mid

        seg_start = self._segment_starts[lo]
        seg_end = self._segment_starts[lo + 1]
        seg_len = seg_end - seg_start
        if seg_len > 0:
            frac = (self._path_dist - seg_start) / seg_len
        else:
            frac = 0.0

        ax, ay = self._waypoints[lo]
        bx, by = self._waypoints[lo + 1]
        self.center_x = ax + frac * (bx - ax)
        self.center_y = ay + frac * (by - ay)

        # Rotate sprite to face direction of travel along the current segment.
        # Arcade angle: CCW-positive. Enemy sprites face DOWN at 0°.
        # Rotating (0,-1) CCW by θ gives (sin θ, -cos θ), so to point at (dx,dy):
        #   θ = atan2(-dx, -dy)
        # Verified: down(0,-1)→0°, up(0,+1)→180°, right(+1,0)→-90°, left(-1,0)→+90°
        seg_dx = bx - ax
        seg_dy = by - ay
        if seg_dx != 0.0 or seg_dy != 0.0:
            self.angle = math.degrees(math.atan2(-seg_dx, -seg_dy))

    def _move_toward_home(self, delta_time: float) -> None:
        """Fly toward the (possibly live-updated) home grid position at dive_return_speed,
        smoothly rotating back to upright (0°) as the ship returns."""
        dx = self._home_x - self.center_x
        dy = self._home_y - self.center_y
        dist = math.hypot(dx, dy)
        if dist <= self._ARRIVAL_THRESHOLD:
            self.center_x = self._home_x
            self.center_y = self._home_y
            self.angle = 0.0
            self._state = DiveState.DONE
            return
        step = self._config.dive_return_speed * delta_time
        ratio = min(step / dist, 1.0)
        self.center_x += dx * ratio
        self.center_y += dy * ratio

        # Smoothly rotate back to 0° (upright) during the return flight.
        if self.angle != 0.0:
            rot_delta = self._ANGLE_RETURN_RATE * delta_time
            # Normalise to (-180, 180] for shortest-path rotation.
            a = (self.angle + 180.0) % 360.0 - 180.0
            if abs(a) <= rot_delta:
                self.angle = 0.0
            elif a > 0:
                self.angle = (self.angle - rot_delta) % 360.0
            else:
                self.angle = (self.angle + rot_delta) % 360.0

    def _fire_bomb(self) -> None:
        from src.sprites.enemy_bullet import EnemyBullet

        self._has_fired_bomb = True
        self._pending_bomb = EnemyBullet(
            x=self.center_x,
            y=self.center_y,
            speed=self._config.dive_bomb_speed,
            texture=self._bullet_texture,
            scale=self._sprite_scale,
        )
