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
from src.ui.hud import HUD
from src.ui.text_utils import FONT_THIN, centered_text


class RunLevelView(arcade.View):
    """Active gameplay screen.

    Drives input, movement, collision detection, and rendering.
    Transitions via GameStateManager — never called from EnemyGrid directly.

    Debug shortcuts (active only when config.debug is True):
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

        self._hud: Optional[HUD] = None
        self._debug_text: Optional[arcade.Text] = None
        self._debug: bool = False

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
        self._debug = cfg.debug if cfg else False

    # ------------------------------------------------------------------
    # Arcade callbacks
    # ------------------------------------------------------------------

    def on_show_view(self) -> None:
        arcade.set_background_color(arcade.color.BLACK)
        ctx = self._manager.context
        players = ctx.get("players", [])
        num_players = len(players)
        self._hud = HUD(self.window.width, self.window.height, num_players)
        if self._debug:
            self._debug_text = centered_text(
                "Shift+E = Clear enemies",
                self.window.width,
                self.window.height - 20,
                font_size=11,
                color=(80, 80, 80, 255),
                font_name=FONT_THIN,
            )

    def on_update(self, delta_time: float) -> None:
        from src.state import GameState

        self.window.star_field.update(delta_time)  # type: ignore[attr-defined]

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

        # Update HUD
        if self._hud is not None:
            ctx = self._manager.context
            players = ctx.get("players", [])
            idx = ctx.get("active_player_index", 0)
            level = players[idx].current_level if players else 1
            self._hud.update(players, idx, level)

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
        self.window.background.draw()  # type: ignore[attr-defined]
        self.window.star_field.draw()  # type: ignore[attr-defined]

        if self._grid is not None:
            self._grid.get_sprite_list().draw()
            self._grid.get_bullet_sprite_list().draw()

        self._player_bullets.draw()
        self._ship_list.draw()
        self._explosions.draw()

        if self._hud is not None:
            self._hud.draw()

        if self._debug and self._debug_text is not None:
            self._debug_text.draw()

    def on_key_press(self, key: int, modifiers: int) -> None:
        from src.state import GameState

        if self._debug and key == arcade.key.E and (modifiers & arcade.key.MOD_SHIFT):
            self._manager.transition(GameState.LEVEL_COMPLETE)
            return

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

    def _update_score(self, points: int) -> None:
        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        if players:
            players[idx].score += points
