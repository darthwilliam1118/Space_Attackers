"""RUN_LEVEL view — player ship, enemy grid, bullets, explosions, and HUD."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

from src.dive_controller import DiveController
from src.enemy_grid import EnemyGrid
from src.game_event import GameEvent
from src.music import track_key_for_level
from src.paths import resource_path
from src.ship_config import ShipConfig
from src.sprites.explosion import ExplosionSprite
from src.sprites.particles import ParticleEmitter, ShockwaveSprite
from src.sprites.player_ship import PlayerShip
from src.ui.hud import HUD
from src.ui.score_popup import ScorePopup
from src.ui.text_utils import FONT_MAIN, FONT_THIN, centered_text
from src.ui_config import UIConfig

_SND_ENEMY_KILLED = "assets/sounds/explosionCrunch_000.ogg"
_SND_PLAYER_KILLED = "assets/sounds/explosionCrunch_004.ogg"
_SND_ENEMY_SHOOT = "assets/sounds/laserLarge_000.ogg"
_SND_PLAYER_SHOOT = "assets/sounds/laserSmall_000.ogg"


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

        self._paused: bool = False

        self._dying: bool = False
        self._death_explosion: Optional[ExplosionSprite] = None
        self._death_timer: float = 0.0
        self._level_cleared: bool = False

        self._dive_controller: Optional[DiveController] = None
        self._waiting_for_dives: bool = False  # 2P: wait for airborne ships after death

        self._score_popups: list[ScorePopup] = []

        self._hud: Optional[HUD] = None
        self._hp_label: Optional[arcade.Text] = None
        self._debug_text: Optional[arcade.Text] = None
        self._debug: bool = False

        self._snd_enemy_killed: Optional[arcade.Sound] = None
        self._snd_player_killed: Optional[arcade.Sound] = None
        self._snd_enemy_shoot: Optional[arcade.Sound] = None
        self._snd_player_shoot: Optional[arcade.Sound] = None

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
            scale=cfg.sprite_scale if cfg is not None else 1.0,
        )
        self._ship_list.append(self._ship)
        self._grid = ctx.get("enemy_grid")
        self._dive_controller = ctx.get("dive_controller")
        self._debug = cfg.debug if cfg else False
        if cfg is not None:
            self._particle_emitter = ParticleEmitter(cfg.particles)

        w = self.window.width
        self._hp_label = arcade.Text(
            text="HP",
            x=w / 2 - 100 - 8,
            y=24,
            color=(255, 255, 255, 255),
            font_size=16,
            font_name=FONT_MAIN,
            anchor_x="right",
            anchor_y="center",
        )

        self._snd_enemy_killed = arcade.load_sound(resource_path(_SND_ENEMY_KILLED))
        self._snd_player_killed = arcade.load_sound(resource_path(_SND_PLAYER_KILLED))
        self._snd_enemy_shoot = arcade.load_sound(resource_path(_SND_ENEMY_SHOOT))
        self._snd_player_shoot = arcade.load_sound(resource_path(_SND_PLAYER_SHOOT))

    # ------------------------------------------------------------------
    # Arcade callbacks
    # ------------------------------------------------------------------

    def on_show_view(self) -> None:
        arcade.set_background_color(arcade.color.BLACK)
        ctx = self._manager.context
        players = ctx.get("players", [])
        idx = ctx.get("active_player_index", 0)
        level = players[idx].current_level if players else 1
        self.window.music.play(track_key_for_level(level))  # type: ignore[attr-defined]
        num_players = len(players)
        self._hud = HUD(self.window.width, self.window.height, num_players)
        if self._debug:
            self._debug_text = centered_text(
                "Shift+E = Clear enemies  |  Shift+D = Force dive",
                self.window.width,
                self.window.height - 10,
                font_size=11,
                color=(180, 180, 180, 255),
                font_name=FONT_THIN,
            )

    def on_update(self, delta_time: float) -> None:
        from src.state import GameState

        delta_time = min(delta_time, 1.0 / 15.0)  # cap to ~66ms to survive debugger pauses

        if self._paused:
            return

        # Guard: respawned into an empty level (last enemy died during death sequence)
        if not self._dying and not self._waiting_for_dives and not self._level_cleared:
            grid_empty = self._grid is None or self._grid.is_cleared()
            no_airborne = (
                self._dive_controller is None or not self._dive_controller.has_any_airborne()
            )
            if grid_empty and no_airborne:
                self._level_cleared = True
                return

        self.window.star_field.update(delta_time)  # type: ignore[attr-defined]

        if self._particle_emitter is not None:
            self._particle_emitter.update(delta_time)
        for shockwave in list(self._shockwaves):
            shockwave.update(delta_time)

        # Death sequence: let animations run for up to 2 seconds, then transition
        if self._dying:
            self._death_timer += delta_time
            for exp in list(self._explosions):
                exp.update(delta_time)
            for bullet in list(self._player_bullets):
                bullet.update(delta_time)  # type: ignore[arg-type]
            if self._grid is not None:
                self._grid.update(
                    delta_time, None
                )  # keep enemy animations alive; no player to collide
            if self._dive_controller is not None:
                self._dive_controller.update(delta_time, self._grid, None, arcade.SpriteList())
            for popup in self._score_popups:
                popup.update(delta_time)
            self._score_popups = [p for p in self._score_popups if not p.is_done]
            explosion_done = self._death_explosion is None or self._death_explosion.is_complete
            if explosion_done or self._death_timer >= 2.0:
                ctx = self._manager.context
                if self._dive_controller is not None and self._dive_controller.has_any_airborne():
                    self._dying = False
                    self._waiting_for_dives = True
                    self._dive_controller.new_dive_launches_blocked = True
                else:
                    self._manager.transition(GameState.PLAYER_KILLED)
            return

        # 2P wait: dives must complete before we snapshot and switch players
        if self._waiting_for_dives:
            if self._grid is not None:
                self._grid.update(delta_time, None)  # grid moves; no player to collide
            if self._dive_controller is not None:
                self._dive_controller.update(delta_time, self._grid, None, arcade.SpriteList())
                if not self._dive_controller.has_any_airborne():
                    self._waiting_for_dives = False
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
            if self._grid is not None:
                for bullet in list(self._grid.get_bullet_sprite_list()):
                    bullet.update(delta_time)
            if self._dive_controller is not None:
                for bullet in list(self._dive_controller.get_all_bullets()):
                    bullet.update(delta_time)
            if not self._explosions:
                self._manager.transition(GameState.LEVEL_COMPLETE)
            return

        # Helper: both grid and dive controller must be empty for the level to clear
        def _is_level_cleared() -> bool:
            grid_empty = self._grid is None or self._grid.is_cleared()
            no_airborne = (
                self._dive_controller is None or not self._dive_controller.has_any_airborne()
            )
            return grid_empty and no_airborne

        if self._grid is None:
            return

        # Player bullets vs enemy grid
        for bullet in list(self._player_bullets):
            bullet.update(delta_time)  # type: ignore[arg-type]
            if bullet.sprite_lists:  # still alive (not self-removed from off-screen)
                hit = self._grid.apply_player_bullet(bullet)
                if hit is not None:
                    bullet.remove_from_sprite_lists()
                    if hit.killed:
                        hit_x, hit_y, points = hit.cx, hit.cy, hit.points
                        vx, vy = self._grid.velocity if self._grid is not None else (0.0, 0.0)
                        _cfg = self._manager.context.get("config")
                        exp = ExplosionSprite(
                            x=hit_x,
                            y=hit_y,
                            frame_duration=0.05,
                            vx=vx,
                            vy=vy,
                            scale=_cfg.sprite_scale if _cfg is not None else 1.0,
                        )
                        self._explosions.append(exp)
                        if self._snd_enemy_killed is not None:
                            arcade.play_sound(self._snd_enemy_killed, volume=self._sfx_volume())
                        self._update_score(points)
                        cfg = self._manager.context.get("config")
                        ui_cfg: UIConfig = cfg.ui if cfg is not None else UIConfig()
                        self._score_popups.append(
                            ScorePopup(
                                hit_x,
                                hit_y,
                                points,
                                duration=ui_cfg.popup_duration,
                                rise_speed=ui_cfg.popup_rise_speed,
                            )
                        )
                        self.spawn_destruction_effect(hit_x, hit_y, vx, vy)
                        if _is_level_cleared():
                            self._level_cleared = True
                            return
                    else:
                        vx, vy = self._grid.velocity if self._grid is not None else (0.0, 0.0)
                        self._spawn_hit_ring(hit.cx, hit.cy, vx, vy)

        # Enemy grid: movement, shooting, collision detection
        # Collisions are skipped while player is invincible
        collision_target = self._ship if not self._ship.is_invincible() else None
        bullets_before = len(self._grid.get_bullet_sprite_list())
        ship_hp_before_grid = self._ship.hit_points
        events = self._grid.update(delta_time, collision_target)
        if (
            len(self._grid.get_bullet_sprite_list()) > bullets_before
            and self._snd_enemy_shoot is not None
        ):
            arcade.play_sound(self._snd_enemy_shoot, volume=self._sfx_volume())

        # Spawn explosions for grid enemies that collided with the player
        for hit_x, hit_y, _ in self._grid.consume_pending_hits():
            _cfg2 = self._manager.context.get("config")
            exp = ExplosionSprite(
                x=hit_x,
                y=hit_y,
                frame_duration=0.05,
                scale=_cfg2.sprite_scale if _cfg2 is not None else 1.0,
            )
            self._explosions.append(exp)
            self.spawn_destruction_effect(hit_x, hit_y, 0.0, 0.0)
            if self._snd_enemy_killed is not None:
                arcade.play_sound(self._snd_enemy_killed, volume=self._sfx_volume())

        _cfg = self._manager.context.get("config")
        god_mode: bool = _cfg.god_mode if _cfg is not None else False

        if self._ship.hit_points < ship_hp_before_grid and GameEvent.PLAYER_KILLED not in events:
            self._spawn_hit_ring(self._ship.center_x, self._ship.center_y)

        for event in events:
            if event == GameEvent.PLAYER_KILLED:
                if not god_mode:
                    self._trigger_death()
                    return
            elif event == GameEvent.LEVEL_COMPLETE:
                self._manager.transition(GameState.LEVEL_COMPLETE)
                return

        # Dive controller: update and handle events
        if self._dive_controller is not None:
            ship_hp_before_dive = self._ship.hit_points
            dive_events = self._dive_controller.update(
                delta_time, self._grid, self._ship, self._player_bullets
            )
            # Spawn effects for destroyed diving ships
            ctx = self._manager.context
            cfg = ctx.get("config")
            ui_cfg: UIConfig = cfg.ui if cfg is not None else UIConfig()
            for hit_x, hit_y, points in self._dive_controller.consume_pending_hits():
                self._update_score(points)
                self._score_popups.append(
                    ScorePopup(
                        hit_x,
                        hit_y,
                        points,
                        duration=ui_cfg.popup_duration,
                        rise_speed=ui_cfg.popup_rise_speed,
                    )
                )
                _cfg3 = self._manager.context.get("config")
                exp = ExplosionSprite(
                    x=hit_x,
                    y=hit_y,
                    frame_duration=0.05,
                    scale=_cfg3.sprite_scale if _cfg3 is not None else 1.0,
                )
                self._explosions.append(exp)
                self.spawn_destruction_effect(hit_x, hit_y, 0.0, 0.0)
                if self._snd_enemy_killed is not None:
                    arcade.play_sound(self._snd_enemy_killed, volume=self._sfx_volume())
            for hit_x, hit_y in self._dive_controller.consume_pending_non_lethal_hits():
                self._spawn_hit_ring(hit_x, hit_y)
            if (
                self._ship.hit_points < ship_hp_before_dive
                and GameEvent.PLAYER_KILLED not in dive_events
            ):
                self._spawn_hit_ring(self._ship.center_x, self._ship.center_y)
            for event in dive_events:
                if event == GameEvent.PLAYER_KILLED:
                    if not god_mode:
                        self._trigger_death()
                        return
                elif event == GameEvent.ENEMY_DESTROYED:
                    if _is_level_cleared():
                        self._level_cleared = True
                        return

    def on_draw(self) -> None:
        self.clear()
        self.window.background.draw()  # type: ignore[attr-defined]
        self.window.star_field.draw()  # type: ignore[attr-defined]

        if self._grid is not None:
            self._grid.get_sprite_list().draw()
            self._grid.get_bullet_sprite_list().draw()

        if self._dive_controller is not None:
            self._dive_controller.get_all_sprites().draw()
            self._dive_controller.get_all_bullets().draw()

        self._player_bullets.draw()
        self._ship_list.draw()
        self._shockwaves.draw()
        self._explosions.draw()
        if self._particle_emitter is not None:
            self._particle_emitter.draw()

        self._draw_enemy_hp_bars()
        self._draw_player_hp_bar()

        for popup in self._score_popups:
            popup.draw()

        if self._hud is not None:
            self._hud.draw()

        if self._debug and self._debug_text is not None:
            self._debug_text.draw()

        if self._paused:
            w, h = self.window.width, self.window.height
            arcade.draw_lrbt_rectangle_filled(0, w, 0, h, (0, 0, 0, 120))
            arcade.draw_text(
                "PAUSED",
                w / 2,
                h / 2,
                arcade.color.WHITE,
                font_size=48,
                font_name=FONT_THIN,
                anchor_x="center",
                anchor_y="center",
            )

    def on_key_press(self, key: int, modifiers: int) -> None:
        from src.state import GameState

        if self._debug and key == arcade.key.E and (modifiers & arcade.key.MOD_SHIFT):
            self._manager.transition(GameState.LEVEL_COMPLETE)
            return

        if (
            self._debug
            and key == arcade.key.D
            and (modifiers & arcade.key.MOD_SHIFT)
            and self._dive_controller is not None
            and self._grid is not None
            and self._ship is not None
        ):
            self._dive_controller.launch_group(self._grid, self._ship.center_x)
            return

        if key == arcade.key.P:
            self._paused = not self._paused
            if self._paused:
                self.window.music.pause()  # type: ignore[attr-defined]
            else:
                self.window.music.resume()  # type: ignore[attr-defined]
            return

        self._keys_held.add(key)

        if key == arcade.key.SPACE and not self._dying:
            self._fire()

    def on_key_release(self, key: int, modifiers: int) -> None:
        self._keys_held.discard(key)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _sfx_volume(self) -> float:
        """Return effects volume (0.0-1.0) from config."""
        cfg = self._manager.context.get("config")
        return (cfg.effects_volume / 100.0) if cfg is not None else 1.0

    def _fire(self) -> None:
        if self._ship is None:
            return
        bullet = self._ship.try_fire()
        if bullet is not None:
            self._player_bullets.append(bullet)
            if self._snd_player_shoot is not None:
                arcade.play_sound(self._snd_player_shoot, volume=self._sfx_volume())

    def _trigger_death(self) -> None:
        """Begin death sequence: explosion plays, then PLAYER_KILLED transition."""
        if self._dying or self._ship is None:
            return
        self._dying = True
        self._death_timer = 0.0
        if self._snd_player_killed is not None:
            arcade.play_sound(self._snd_player_killed, volume=self._sfx_volume())
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

    # ------------------------------------------------------------------
    # HP bar and flash rendering
    # ------------------------------------------------------------------

    def _spawn_hit_ring(self, x: float, y: float, vx: float = 0.0, vy: float = 0.0) -> None:
        """Spawn a small expanding shockwave ring at *(x, y)* for a non-lethal hit."""
        cfg = self._manager.context.get("config")
        if cfg is not None:
            ring = ShockwaveSprite(x, y, cfg.particles, vx=vx, vy=vy, duration=0.3, max_scale=1.2)
            self._shockwaves.append(ring)

    def _draw_enemy_hp_bars(self) -> None:
        """Draw HP bars above any enemy with an active hp_bar_timer."""
        cfg = self._manager.context.get("config")
        ui_cfg: UIConfig = cfg.ui if cfg is not None else UIConfig()
        bar_h = ui_cfg.hp_bar_height
        y_off = ui_cfg.hp_bar_y_offset

        sprites = []
        if self._grid is not None:
            sprites.extend(self._grid.get_sprite_list())
        if self._dive_controller is not None:
            sprites.extend(self._dive_controller.get_ship_sprite_list())

        for enemy in sprites:
            if enemy.hp_bar_timer <= 0 or enemy.max_hit_points == 0:
                continue
            hp_pct = max(0.0, enemy.hit_points / enemy.max_hit_points)
            bar_w = enemy.width
            bar_x = enemy.center_x
            bar_y = enemy.center_y + enemy.height / 2 + y_off

            if hp_pct > 0.75:
                fill_color = (0, 191, 0)
            elif hp_pct > 0.25:
                fill_color = (191, 191, 0)
            else:
                fill_color = (191, 0, 0)

            arcade.draw_lbwh_rectangle_outline(
                bar_x - bar_w / 2, bar_y - bar_h / 2, bar_w, bar_h, (191, 191, 191), 2
            )
            filled_w = bar_w * hp_pct
            if filled_w > 0:
                arcade.draw_lbwh_rectangle_filled(
                    bar_x - bar_w / 2,
                    bar_y - bar_h / 2,
                    filled_w,
                    bar_h,
                    fill_color,
                )

    def _draw_player_hp_bar(self) -> None:
        """Draw the player HP bar at the bottom-centre of the screen."""
        if self._ship is None or self._hp_label is None:
            return
        bar_w = 200
        bar_h = 18
        bar_x = self.window.width / 2.0
        bar_y = 24.0

        hp_pct = max(0.0, self._ship.hit_points / self._ship.max_hit_points)
        if hp_pct > 0.75:
            fill_color = (0, 191, 0)
        elif hp_pct > 0.25:
            fill_color = (191, 191, 0)
        else:
            fill_color = (191, 0, 0)

        arcade.draw_lbwh_rectangle_outline(
            bar_x - bar_w / 2, bar_y - bar_h / 2, bar_w, bar_h, (191, 191, 191), 2
        )
        filled_w = bar_w * hp_pct
        if filled_w > 0:
            arcade.draw_lbwh_rectangle_filled(
                bar_x - bar_w / 2,
                bar_y - bar_h / 2,
                filled_w,
                bar_h,
                fill_color,
            )
        self._hp_label.draw()

    def _update_score(self, points: int) -> None:
        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        if players:
            players[idx].score += points
