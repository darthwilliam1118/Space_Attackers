"""DiveController — manages dive groups: timing, selection, and lifecycle."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional

import arcade

from src.game_event import GameEvent

if TYPE_CHECKING:
    from src.diving_config import DivingConfig
    from src.enemy_grid import EnemyGrid
    from src.sprites.diving_ship import DivingShip
    from src.sprites.enemy_sprite import EnemySprite
    from src.sprites.player_ship import PlayerShip


class DiveController:
    """Orchestrates periodic dive groups from the enemy formation.

    Level-scaled parameters are computed in :py:meth:`setup` from the level
    number and :py:class:`DivingConfig` constants.  The controller returns
    :py:class:`GameEvent` values from :py:meth:`update` — no direct state
    machine calls.
    """

    _STAGGER_DELAY: float = 0.3  # seconds between successive ships in a group

    def __init__(
        self,
        config: "DivingConfig",
        window_width: int,
        window_height: int,
        debug: bool = False,
        sprite_scale: float = 1.0,
        hp_bar_duration: float = 1.0,
    ) -> None:
        self._config = config
        self._window_width = window_width
        self._window_height = window_height
        self._debug = debug
        self._sprite_scale = sprite_scale
        self._hp_bar_duration = hp_bar_duration

        # Level-scaled (set by setup())
        self._level: int = 1
        self._dive_group_size: int = 0
        self._dive_interval: float = 0.0
        self._dive_speed: float = 0.0

        # Runtime state
        self._dive_timer: float = 0.0
        self._active_ships: list["DivingShip"] = []
        self._ship_list: arcade.SpriteList = arcade.SpriteList()
        self._bomb_list: arcade.SpriteList = arcade.SpriteList()
        # Maps each DivingShip back to its original EnemySprite for grid re-insertion
        self._source_map: dict[int, "EnemySprite"] = {}  # id(DivingShip) → EnemySprite

        # Set True to block new group launches (2P waiting state)
        self.new_dive_launches_blocked: bool = False

        # Pending hit data for RunLevelView to consume: (x, y, points)
        self._pending_hits: list[tuple[float, float, int]] = []
        # Non-lethal bullet hits (enemy survived): (x, y) for hit-ring effect
        self._pending_non_lethal_hits: list[tuple[float, float]] = []

    # ------------------------------------------------------------------
    # Setup / snapshot
    # ------------------------------------------------------------------

    def setup(self, level: int, enemy_grid: Optional["EnemyGrid"]) -> None:
        """Compute level-scaled parameters and reset the dive timer.

        *enemy_grid* may be None when restoring from snapshot.
        """
        cfg = self._config
        self._level = level

        self._dive_group_size = min(max(level - 1, 0), cfg.dive_group_size_max)

        self._dive_interval = max(
            cfg.dive_interval_min,
            cfg.dive_interval_base - (level - 2) * cfg.dive_interval_step,
        )

        self._dive_speed = min(
            cfg.dive_speed_base + (level - 2) * cfg.dive_speed_step,
            cfg.dive_speed_max,
        )

        self._dive_timer = self._dive_interval

    def to_snapshot(self) -> dict:
        """Return minimal state — guaranteed no airborne ships when called."""
        return {
            "dive_timer": self._dive_timer,
            "level": self._level,
        }

    @classmethod
    def from_snapshot(
        cls,
        snapshot: dict,
        config: "DivingConfig",
        window_width: int,
        window_height: int,
        debug: bool = False,
        sprite_scale: float = 1.0,
        hp_bar_duration: float = 1.0,
    ) -> "DiveController":
        """Restore DiveController from snapshot.  No airborne ships to restore."""
        ctrl = cls(
            config,
            window_width,
            window_height,
            debug=debug,
            sprite_scale=sprite_scale,
            hp_bar_duration=hp_bar_duration,
        )
        ctrl.setup(snapshot["level"], enemy_grid=None)
        ctrl._dive_timer = snapshot["dive_timer"]
        return ctrl

    # ------------------------------------------------------------------
    # Debug helpers
    # ------------------------------------------------------------------

    def _oob_check(self, ship: "DivingShip", context: str) -> None:
        """Log if a diving ship has moved outside the window bounds (debug only)."""
        if not self._debug:
            return
        if ship.center_x < 0 or ship.center_x > self._window_width:
            print(
                f"[OOB] dive {context} col={ship.col} row={ship.row} "
                f"x={ship.center_x:.1f} state={ship._state.name} "
                f"window_w={self._window_width}"
            )
            pass  # set breakpoint here

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------

    def update(
        self,
        delta_time: float,
        enemy_grid: Optional["EnemyGrid"],
        player_ship: Optional["PlayerShip"],
        player_bullets: arcade.SpriteList,
    ) -> list[GameEvent]:
        """Advance timer, update active ships, handle collisions, return events."""
        events: list[GameEvent] = []
        self._pending_hits.clear()
        self._pending_non_lethal_hits.clear()

        # Advance dive timer (blocked during 2P wait)
        if not self.new_dive_launches_blocked and self._dive_group_size > 0:
            self._dive_timer -= delta_time
            if self._dive_timer <= 0.0 and enemy_grid is not None:
                player_x = player_ship.center_x if player_ship else self._window_width / 2
                self.launch_group(enemy_grid, player_x)
                self._dive_timer = self._dive_interval

        # Tick HP bar timer on active diving ships
        for ship in self._active_ships:
            if ship.hp_bar_timer > 0:
                ship.hp_bar_timer -= delta_time

        # Update active diving ships
        done_ships: list["DivingShip"] = []
        for ship in list(self._active_ships):
            player_x = player_ship.center_x if player_ship else self._window_width / 2

            # During RETURNING, track the live grid slot so the ship lands
            # exactly where the formation has drifted to.
            from src.sprites.diving_ship import DiveState

            if ship._state == DiveState.RETURNING and enemy_grid is not None:
                tx, ty = enemy_grid.get_slot_position(ship.col, ship.row)
                ship._home_x = tx
                ship._home_y = ty

            ship.update(delta_time, player_x)
            self._oob_check(ship, "update")

            # Collect newly fired bomb
            bomb = ship.get_bomb()
            if bomb is not None:
                self._bomb_list.append(bomb)

            if ship.is_done:
                done_ships.append(ship)

        # Keep enemy_grid col cache in sync with ALL living ships (grid + airborne).
        # Without this, when the last grid sprite dives the cache freezes on that
        # column, letting _origin_x drift past the margin for other columns' ships.
        if enemy_grid is not None and self._active_ships:
            all_cols = [s.col for s in self._active_ships]
            all_cols.extend(s.col for s in enemy_grid._sprite_list)  # type: ignore[attr-defined]
            enemy_grid._last_left_col = min(all_cols)
            enemy_grid._last_right_col = max(all_cols)

        # Return completed ships to grid
        for ship in done_ships:
            self._active_ships.remove(ship)
            ship.remove_from_sprite_lists()
            source = self._source_map.pop(id(ship), None)
            if enemy_grid is not None and source is not None:
                enemy_grid.return_from_dive(source)

        # Update bombs (self-remove off-screen)
        for bomb in list(self._bomb_list):
            bomb.update(delta_time)

        # Check player bullets vs diving ships
        for bullet in list(player_bullets):
            if not bullet.sprite_lists:
                continue
            hits = arcade.check_for_collision_with_list(bullet, self._ship_list)
            for ship in hits:
                bullet_damage = getattr(bullet, "damage", 100)
                ship.hit_points -= bullet_damage
                bullet.remove_from_sprite_lists()
                if ship.hit_points <= 0:
                    self._pending_hits.append(
                        (
                            ship.center_x,
                            ship.center_y,
                            self._config.dive_bonus_points,
                        )
                    )
                    ship.remove_from_sprite_lists()
                    if ship in self._active_ships:
                        self._active_ships.remove(ship)
                    self._source_map.pop(id(ship), None)
                    events.append(GameEvent.ENEMY_DESTROYED)
                else:
                    ship.hp_bar_timer = self._hp_bar_duration
                    self._pending_non_lethal_hits.append((ship.center_x, ship.center_y))
                break  # one bullet hits one ship

        # Check diving ships vs player ship
        if player_ship is not None and not player_ship.is_invincible():
            hits = arcade.check_for_collision_with_list(player_ship, self._ship_list)
            if hits:
                for ship in hits:
                    self._pending_hits.append(
                        (
                            ship.center_x,
                            ship.center_y,
                            self._config.dive_bonus_points,
                        )
                    )
                    ship.remove_from_sprite_lists()
                    if ship in self._active_ships:
                        self._active_ships.remove(ship)
                    self._source_map.pop(id(ship), None)
                events.append(GameEvent.PLAYER_KILLED)

        # Check dive bombs vs player ship
        if player_ship is not None and not player_ship.is_invincible():
            hits = arcade.check_for_collision_with_list(player_ship, self._bomb_list)
            if hits:
                for bomb in hits:
                    bomb.remove_from_sprite_lists()
                events.append(GameEvent.PLAYER_KILLED)

        return events

    # ------------------------------------------------------------------
    # Group launching
    # ------------------------------------------------------------------

    def launch_group(self, enemy_grid: "EnemyGrid", player_x: float) -> None:
        """Select random eligible ships and launch them as a staggered group."""
        from src.dive_path import make_dive_path
        from src.sprites.diving_ship import DivingShip

        eligible: list["EnemySprite"] = list(enemy_grid.get_sprite_list())  # type: ignore[arg-type]
        if not eligible:
            return

        count = min(self._dive_group_size, len(eligible))
        if count == 0:
            return

        selected: list["EnemySprite"] = random.sample(eligible, count)

        # All ships in the group arc the same direction for visual cohesion
        curve_sign = random.choice([-1, 1])

        for i, source in enumerate(selected):
            start = (source.center_x, source.center_y)
            waypoints = make_dive_path(
                start=start,
                player_x=player_x,
                window_height=self._window_height,
                window_width=self._window_width,
                curve_sign=curve_sign,
            )
            ship = DivingShip(
                source_sprite=source,
                waypoints=waypoints,
                config=self._config,
                window_height=self._window_height,
                dive_speed=self._dive_speed,
                launch_delay=i * self._STAGGER_DELAY,
                scale=self._sprite_scale,
            )
            enemy_grid.remove_for_dive(source)
            self._active_ships.append(ship)
            self._ship_list.append(ship)
            self._source_map[id(ship)] = source

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_all_sprites(self) -> arcade.SpriteList:
        """SpriteList of all currently airborne diving ships."""
        return self._ship_list

    def get_all_bullets(self) -> arcade.SpriteList:
        """SpriteList of all active dive bombs."""
        return self._bomb_list

    def active_count(self) -> int:
        """Number of ships currently in flight."""
        return len(self._active_ships)

    def has_any_airborne(self) -> bool:
        """True if any ships are currently diving or returning."""
        return len(self._active_ships) > 0

    def get_ship_sprite_list(self) -> arcade.SpriteList:
        """Return the active diving ship sprite list (for HP bars and flash effects)."""
        return self._ship_list

    def consume_pending_hits(self) -> list[tuple[float, float, int]]:
        """Return pending hit data (x, y, points) and clear the list."""
        hits = list(self._pending_hits)
        self._pending_hits.clear()
        return hits

    def consume_pending_non_lethal_hits(self) -> list[tuple[float, float]]:
        """Return (x, y) positions of non-lethal bullet hits this frame and clear the list."""
        hits = list(self._pending_non_lethal_hits)
        self._pending_non_lethal_hits.clear()
        return hits
