"""RUN_LEVEL view — player ship, enemy grid, bullets, explosions, and HUD."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

from src.enemy_grid import EnemyGrid
from src.game_event import GameEvent
from src.ship_config import ShipConfig
from src.sprites.explosion import ExplosionSprite
from src.sprites.player_ship import PlayerShip


class RunLevelView(arcade.View):
    """Active gameplay screen.

    Drives input, movement, collision detection, and rendering.
    Transitions via GameStateManager — never called from EnemyGrid directly.

    Debug shortcuts (# DEBUG):
      Shift+E — instantly clear all enemies → LEVEL_COMPLETE
    """

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__()
        self._manager = manager
        self._keys_held: set[int] = set()

        self._ship: Optional[PlayerShip] = None
        self._ship_list = arcade.SpriteList()
        self._player_bullets = arcade.SpriteList()
        self._explosions = arcade.SpriteList()
        self._grid: Optional[EnemyGrid] = None

        self._dying: bool = False
        self._death_explosion: Optional[ExplosionSprite] = None
        self._level_cleared: bool = False

        self._setup()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup(self) -> None:
        ctx = self._manager.context
        players = ctx.get("players", [])
        idx = ctx.get("active_player_index", 0)
        cfg = ctx.get("config")

        ship_cfg: ShipConfig = cfg.ship if cfg else ShipConfig()
        player_num = players[idx].player_num if players else 1

        self._ship = PlayerShip(
            player_num=player_num,
            config=ship_cfg,
            window_width=self.window.width,
            window_height=self.window.height,
        )
        self._ship_list.append(self._ship)
        self._grid = ctx.get("enemy_grid")

    # ------------------------------------------------------------------
    # Arcade callbacks
    # ------------------------------------------------------------------

    def on_show_view(self) -> None:
        arcade.set_background_color(arcade.color.BLACK)

    def on_update(self, delta_time: float) -> None:
        from src.state import GameState

        # Death explosion plays out before transitioning
        if self._dying:
            if self._death_explosion is not None:
                self._death_explosion.update(delta_time)
                if self._death_explosion.is_complete:
                    self._manager.transition(GameState.PLAYER_KILLED)
            return

        if self._ship is None:
            return

        self._ship.apply_movement(self._keys_held, delta_time)
        self._ship.update(delta_time)

        # Update non-enemy explosions (enemy hit effects)
        for exp in list(self._explosions):
            exp.update(delta_time)  # type: ignore[arg-type]

        # Level-cleared: wait for the final enemy explosion to finish
        if self._level_cleared:
            if not self._explosions:
                self._manager.transition(GameState.LEVEL_COMPLETE)
            return

        if self._grid is None:
            return

        # Player bullets vs enemy grid
        for bullet in list(self._player_bullets):
            bullet.update(delta_time)  # type: ignore[arg-type]
            if bullet.sprite_lists:  # still alive (not self-removed from off-screen)
                hit_pos = self._grid.apply_player_bullet(bullet)
                if hit_pos is not None:
                    exp = ExplosionSprite(
                        x=hit_pos[0],
                        y=hit_pos[1],
                        frame_duration=0.05,
                    )
                    self._explosions.append(exp)
                    bullet.remove_from_sprite_lists()
                    self._update_score(10)
                    if self._grid.is_cleared():
                        self._level_cleared = True
                        return

        # Enemy grid: movement, shooting, collision detection
        # Collisions are skipped while player is invincible
        collision_target = self._ship if not self._ship.is_invincible() else None
        events = self._grid.update(delta_time, collision_target)

        for event in events:
            if event == GameEvent.PLAYER_KILLED:
                self._trigger_death()
                return
            elif event == GameEvent.LEVEL_COMPLETE:
                self._manager.transition(GameState.LEVEL_COMPLETE)
                return

    def on_draw(self) -> None:
        self.clear()
        self._draw_hud()

        if self._grid is not None:
            self._grid.get_sprite_list().draw()
            self._grid.get_bullet_sprite_list().draw()

        self._player_bullets.draw()
        self._ship_list.draw()
        self._explosions.draw()

    def on_key_press(self, key: int, modifiers: int) -> None:
        from src.state import GameState

        # DEBUG: Shift+E = instantly advance to LEVEL_COMPLETE
        if key == arcade.key.E and (modifiers & arcade.key.MOD_SHIFT):  # DEBUG
            self._manager.transition(GameState.LEVEL_COMPLETE)  # DEBUG
            return  # DEBUG

        self._keys_held.add(key)

        if key == arcade.key.SPACE and not self._dying:
            self._fire()

    def on_key_release(self, key: int, modifiers: int) -> None:
        self._keys_held.discard(key)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fire(self) -> None:
        if self._ship is None:
            return
        bullet = self._ship.try_fire()
        if bullet is not None:
            self._player_bullets.append(bullet)

    def _trigger_death(self) -> None:
        """Begin death sequence: explosion plays, then PLAYER_KILLED transition."""
        if self._dying or self._ship is None:
            return
        self._dying = True
        explosion = self._ship.kill()
        self._death_explosion = explosion
        self._explosions.append(explosion)
        self._ship = None
        self._ship_list.clear()

    def _draw_hud(self) -> None:
        """Player 1 score top-left, Player 2 score top-right."""
        players = self._manager.context.get("players", [])
        w = self.window.width
        h = self.window.height

        for player in players:
            if player.player_num == 1:
                arcade.draw_text(
                    f"P1  {player.score:06d}  Lv{player.current_level}  x{player.lives}",
                    10,
                    h - 20,
                    arcade.color.WHITE,
                    font_size=14,
                    anchor_x="left",
                    anchor_y="center",
                )
            elif player.player_num == 2:
                arcade.draw_text(
                    f"P2  {player.score:06d}  Lv{player.current_level}  x{player.lives}",
                    w - 10,
                    h - 20,
                    arcade.color.WHITE,
                    font_size=14,
                    anchor_x="right",
                    anchor_y="center",
                )

        arcade.draw_text(
            "Shift+E = Clear enemies",  # DEBUG
            w / 2,
            h - 20,
            arcade.color.DARK_GRAY,
            font_size=11,
            anchor_x="center",
            anchor_y="center",
        )

    def _update_score(self, points: int) -> None:
        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        if players:
            players[idx].score += points
