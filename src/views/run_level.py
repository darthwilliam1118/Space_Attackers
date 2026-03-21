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
from src.sprites.particles import ParticleEmitter, ShockwaveSprite
from src.sprites.player_ship import PlayerShip
from src.ui.hud import HUD
from src.ui.score_popup import ScorePopup
from src.ui.text_utils import FONT_THIN, centered_text
from src.ui_config import UIConfig


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
        self._shockwaves = arcade.SpriteList()
        self._particle_emitter: Optional[ParticleEmitter] = None
        self._grid: Optional[EnemyGrid] = None

        self._dying: bool = False
        self._death_explosion: Optional[ExplosionSprite] = None
        self._death_timer: float = 0.0
        self._level_cleared: bool = False

        self._score_popups: list[ScorePopup] = []

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
        if cfg is not None:
            self._particle_emitter = ParticleEmitter(cfg.particles)

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

        if self._particle_emitter is not None:
            self._particle_emitter.update(delta_time)
        for shockwave in list(self._shockwaves):
            shockwave.update(delta_time)

        # Death sequence: let animations run for up to 2 seconds, then transition
        if self._dying:
            self._death_timer += delta_time
            if self._death_explosion is not None:
                self._death_explosion.update(delta_time)
            for exp in list(self._explosions):
                exp.update(delta_time)
            for bullet in list(self._player_bullets):
                bullet.update(delta_time)  # type: ignore[arg-type]
            if self._grid is not None:
                for bullet in list(self._grid.get_bullet_sprite_list()):
                    bullet.update(delta_time)
            for popup in self._score_popups:
                popup.update(delta_time)
            self._score_popups = [p for p in self._score_popups if not p.is_done]
            explosion_done = (
                self._death_explosion is None or self._death_explosion.is_complete
            )
            if explosion_done or self._death_timer >= 2.0:
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

        # Update score popups
        for popup in self._score_popups:
            popup.update(delta_time)
        self._score_popups = [p for p in self._score_popups if not p.is_done]

        # Update non-enemy explosions (enemy hit effects)
        for exp in list(self._explosions):
            exp.update(delta_time)  # type: ignore[arg-type]

        # Level-cleared: continue bullet animations, wait for explosions to finish
        if self._level_cleared:
            for bullet in list(self._player_bullets):
                bullet.update(delta_time)  # type: ignore[arg-type]
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
                    vx, vy = self._grid.velocity if self._grid is not None else (0.0, 0.0)
                    exp = ExplosionSprite(
                        x=hit_pos[0],
                        y=hit_pos[1],
                        frame_duration=0.05,
                        vx=vx,
                        vy=vy,
                    )
                    self._explosions.append(exp)
                    bullet.remove_from_sprite_lists()
                    self._update_score(10)
                    cfg = self._manager.context.get("config")
                    ui_cfg: UIConfig = cfg.ui if cfg is not None else UIConfig()
                    self._score_popups.append(ScorePopup(
                        hit_pos[0], hit_pos[1], 10,
                        duration=ui_cfg.popup_duration,
                        rise_speed=ui_cfg.popup_rise_speed,
                    ))
                    self.spawn_destruction_effect(hit_pos[0], hit_pos[1], vx, vy)
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
        self._shockwaves.draw()
        self._explosions.draw()
        if self._particle_emitter is not None:
            self._particle_emitter.draw()

        for popup in self._score_popups:
            popup.draw()

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
        self._death_timer = 0.0
        vx, vy = self._ship.velocity
        x, y = self._ship.center_x, self._ship.center_y
        explosion = self._ship.kill(vx=vx, vy=vy)
        self._death_explosion = explosion
        self._explosions.append(explosion)
        self._ship = None
        self._ship_list.clear()
        self.spawn_destruction_effect(x, y, vx, vy)

    def spawn_destruction_effect(
        self, x: float, y: float, vx: float = 0.0, vy: float = 0.0
    ) -> None:
        """Spawn particle burst and shockwave ring at *(x, y)* with momentum."""
        if self._particle_emitter is not None:
            self._particle_emitter.explode(x, y, vx, vy)
        ctx = self._manager.context
        cfg = ctx.get("config")
        if cfg is not None:
            shockwave = ShockwaveSprite(x, y, cfg.particles, vx, vy)
            self._shockwaves.append(shockwave)

    def _update_score(self, points: int) -> None:
        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        if players:
            players[idx].score += points
