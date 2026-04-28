"""RUN_LEVEL view — player ship, enemy grid, bullets, explosions, and HUD."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

import arcade
import pyglet.media as media

if TYPE_CHECKING:
    from src.state import GameStateManager

from agf.levels.base_level import BaseLevel
from agf.music import track_key_for_level
from agf.paths import resource_path
from agf.sprites.explosion import ExplosionSprite
from agf.sprites.particles import ParticleEmitter, ShockwaveSprite
from agf.ui.score_popup import ScorePopup
from agf.ui.text_utils import FONT_MAIN, FONT_THIN, centered_text

from src.game_event import GameEvent
from src.ship_config import ShipConfig
from src.sound_manager import SoundManager
from src.sprites.player_ship import PlayerShip
from src.ui.hud import HUD
from src.ui_config import UIConfig

_SND_ENEMY_KILLED = "assets/sounds/explosionCrunch_000.wav"
_SND_PLAYER_KILLED = "assets/sounds/explosionCrunch_004.wav"
_SND_ENEMY_SHOOT = "assets/sounds/laserLarge_000.wav"
_SND_PLAYER_SHOOT = "assets/sounds/laserSmall_000.wav"
_SND_POWERUP_PICKUP = "assets/sounds/laserSmall_001.wav"
_SND_EXTRA_LIFE = "assets/sounds/extraLife.wav"
_EXTRA_LIFE_INTERVAL = 10_000


class RunLevelView(arcade.View):
    """Active gameplay screen.

    Drives input, movement, collision detection, and rendering.
    Transitions via GameStateManager — never called from EnemyGrid directly.

    Debug shortcuts (active only when config.debug is True):
      Shift+E — instantly clear all enemies -> LEVEL_COMPLETE
      Shift+D — force a dive attack
      Shift+G — toggle god mode
      Shift+K — trigger player death
      Shift+P — spawn a random power-up instantly
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
        self._level: Optional[BaseLevel] = None

        self._paused: bool = False
        self._pause_overlay_list: arcade.SpriteList = arcade.SpriteList()

        self._dying: bool = False
        self._death_explosion: Optional[ExplosionSprite] = None
        self._death_timer: float = 0.0
        self._level_cleared: bool = False

        self._waiting_for_dives: bool = False  # 2P: wait for airborne ships after death

        self._score_popups: list[ScorePopup] = []

        self._hud: Optional[HUD] = None
        self._hp_label: Optional[arcade.Text] = None
        self._paused_text: Optional[arcade.Text] = None
        self._debug_text: Optional[arcade.Text] = None
        self._god_mode_text: Optional[arcade.Text] = None
        self._debug: bool = False

        self._snd_enemy_killed: Optional[arcade.Sound] = None
        self._snd_player_killed: Optional[arcade.Sound] = None
        self._snd_enemy_shoot: Optional[arcade.Sound] = None
        self._snd_player_shoot: Optional[arcade.Sound] = None
        self._snd_powerup_pickup: Optional[arcade.Sound] = None
        self._snd_extra_life: Optional[arcade.Sound] = None

        self._shield_sprite_ref: Optional[arcade.Sprite] = None
        self._overlay_list: arcade.SpriteList = arcade.SpriteList()
        self._frame_count: int = 0
        self._debug_timer: float = 0.0

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
        # Carry HP from the previous level if set; new life always starts at max
        active_player = players[idx] if players else None
        if active_player is not None and active_player.current_hp is not None:
            self._ship.hit_points = active_player.current_hp
        self._ship_list.append(self._ship)
        # Install damage filter so overlay effects (shield) can absorb hits
        self._ship.damage_filter = self._filter_damage
        self._level = ctx.get("current_level")
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
        self._snd_powerup_pickup = arcade.load_sound(resource_path(_SND_POWERUP_PICKUP))
        self._snd_extra_life = arcade.load_sound(resource_path(_SND_EXTRA_LIFE))

        self._sm_enemy_killed = SoundManager(max_simultaneous=2)
        self._sm_enemy_shoot = SoundManager(max_simultaneous=3)
        self._sm_player_shoot = SoundManager(max_simultaneous=2)

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
        _life_tex_p1 = arcade.load_texture(
            resource_path("assets/images/PNG/UI/playerLife1_blue.png")
        )
        _life_tex_p2 = arcade.load_texture(
            resource_path("assets/images/PNG/UI/playerLife2_red.png")
        )
        self._hud.setup_icons(_life_tex_p1, _life_tex_p2 if num_players >= 2 else None)
        self._paused_text = arcade.Text(
            "PAUSED",
            self.window.width / 2,
            self.window.height / 2,
            arcade.color.WHITE,
            font_size=48,
            font_name=FONT_THIN,
            anchor_x="center",
            anchor_y="center",
        )
        # Pre-bake the pause dim overlay as a sprite so on_draw() never calls
        # immediate-mode draw functions (which call buffer.orphan() every frame).
        overlay_sprite = arcade.SpriteSolidColor(
            self.window.width,
            self.window.height,
            center_x=self.window.width / 2,
            center_y=self.window.height / 2,
            color=(0, 0, 0, 120),
        )
        self._pause_overlay_list.clear()
        self._pause_overlay_list.append(overlay_sprite)
        if self._debug:
            self._debug_text = centered_text(
                "Shift+E=Clear  Shift+D=Dive  Shift+G=God  Shift+K=Kill  Shift+P=PowerUp",
                self.window.width,
                self.window.height - 10,
                font_size=11,
                color=(180, 180, 180, 255),
                font_name=FONT_THIN,
            )
            self._god_mode_text = arcade.Text(
                "GOD MODE ON",
                self.window.width / 2,
                self.window.height - 62,
                (255, 220, 0, 255),
                font_size=13,
                font_name=FONT_THIN,
                anchor_x="center",
                anchor_y="center",
            )

    def on_update(self, delta_time: float) -> None:
        from src.state import GameState

        delta_time = min(delta_time, 1.0 / 15.0)  # cap to ~66ms to survive debugger pauses

        if self._debug and delta_time > 0.025:
            print(f"Frame spike: {delta_time*1000:.1f}ms")

        self._debug_timer += delta_time
        if self._debug_timer > 1.0:
            self._debug_timer = 0.0
            print(f"Active audio players: {len(media.Source._players)}")

        self._frame_count = (self._frame_count + 1) & 0xF

        if self._paused:
            # Run a gen-0 sweep each frame to prevent orphaned GL buffer objects
            # (created by any remaining on_draw allocations) from building up and
            # triggering a slow gen-2 collection the moment gameplay resumes.
            import gc

            gc.collect(0)
            return

        # Safety net: if HP reached zero via any path that didn't fire PLAYER_KILLED
        # (e.g. shield filter edge case, simultaneous last-enemy-kill + lethal hit),
        # trigger death here before the is_cleared() guard promotes it to LEVEL_COMPLETE.
        _cfg_early = self._manager.context.get("config")
        _god_early: bool = _cfg_early.god_mode if _cfg_early is not None else False
        if (
            not self._dying
            and not _god_early
            and self._ship is not None
            and self._ship.hit_points <= 0
        ):
            self._trigger_death()
            return

        # Guard: respawned into an empty level (last enemy died during death sequence)
        if not self._dying and not self._waiting_for_dives and not self._level_cleared:
            if self._level is None or self._level.is_cleared():
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
            if self._level is not None:
                self._level.update(
                    delta_time, None
                )  # keep enemy animations alive; no player to collide
            for popup in self._score_popups:
                popup.update(delta_time)
            self._score_popups = [p for p in self._score_popups if not p.is_done]
            explosion_done = self._death_explosion is None or self._death_explosion.is_complete
            if explosion_done or self._death_timer >= 2.0:
                players = self._manager.context.get("players", [])
                is_multiplayer = len(players) > 1
                if is_multiplayer and self._level is not None and self._level.has_any_airborne():
                    self._dying = False
                    self._waiting_for_dives = True
                    self._level.block_new_launches()
                else:
                    self._manager.transition(GameState.PLAYER_KILLED)
            return

        # 2P wait: dives must complete before we snapshot and switch players
        if self._waiting_for_dives:
            if self._level is not None:
                self._level.update(delta_time, None)
                if not self._level.has_any_airborne():
                    self._waiting_for_dives = False
                    self._manager.transition(GameState.PLAYER_KILLED)
            return

        if self._ship is None:
            return

        self._ship.apply_movement(self._keys_held, delta_time)
        self._ship.update(delta_time)

        # Auto-fire while space is held (rate-limited by ship's fire_cooldown)
        if arcade.key.SPACE in self._keys_held and not self._dying:
            self._fire()

        # Update HUD
        if self._hud is not None:
            ctx = self._manager.context
            players = ctx.get("players", [])
            idx = ctx.get("active_player_index", 0)
            is_meteor = ctx.get("current_level_is_meteor", False)
            is_boss = ctx.get("current_level_is_boss", False)
            current = players[idx].current_level if players else 1
            level_display = -2 if is_boss else (-1 if is_meteor else current)
            manager = self._level.get_powerup_manager() if self._level is not None else None
            active_effects = manager.get_active_effects() if manager is not None else []
            self._hud.update(players, idx, level_display, active_effects)

        # Update score popups
        for popup in self._score_popups:
            popup.update(delta_time)
        self._score_popups = [p for p in self._score_popups if not p.is_done]

        # Update non-enemy explosions (enemy hit effects)
        for exp in list(self._explosions):
            exp.update(delta_time)  # type: ignore[arg-type]

        # Level-cleared: continue bullet and powerup animations, wait for explosions to finish
        if self._level_cleared:
            for bullet in list(self._player_bullets):
                bullet.update(delta_time)  # type: ignore[arg-type]
            if self._level is not None:
                for bullet in list(self._level.get_enemy_bullet_sprite_list()):
                    bullet.update(delta_time)
                _pu_manager = self._level.get_powerup_manager()
                if _pu_manager is not None:
                    from src.powerups.sa_manager import SAPowerUpManager

                    if isinstance(_pu_manager, SAPowerUpManager):
                        _pu_manager.update_sprites_only(delta_time)
            if not self._explosions:
                self._save_player_hp()
                self._manager.transition(GameState.LEVEL_COMPLETE)
            return

        if self._level is None:
            return

        # Player bullets vs enemy grid (via BaseLevel interface)
        _t0 = time.perf_counter()
        _check_grid = self._frame_count % 3 == 0
        for bullet in list(self._player_bullets):
            bullet.update(delta_time)  # type: ignore[arg-type]
            if bullet.sprite_lists and _check_grid:  # still alive; collision every 3rd frame
                hit = self._level.apply_player_bullet(bullet)
                if hit is not None:
                    bullet.remove_from_sprite_lists()
                    if hit.killed:
                        hit_x, hit_y, points = hit.cx, hit.cy, hit.points
                        vx, vy = self._level.velocity
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
                            self._sm_enemy_killed.play(
                                self._snd_enemy_killed, volume=self._sfx_volume()
                            )
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
                        if self._level is not None and self._level.is_cleared():
                            self._level_cleared = True
                    else:
                        vx, vy = self._level.velocity
                        self._spawn_hit_ring(hit.cx, hit.cy, vx, vy)

        # Level update: enemy movement, shooting, dive attacks, all collisions
        # (DiveController receives remaining player_bullets to handle dive-ship hits)
        _t1 = time.perf_counter()
        collision_target = self._ship if not self._ship.is_invincible() else None
        ship_hp_before = self._ship.hit_points
        events = self._level.update(
            delta_time,
            collision_target,
            self._player_bullets,
            frame_count=self._frame_count,
        )
        _t2 = time.perf_counter()
        if self._debug and delta_time > 0.025:
            print(
                f"  PlayerBullets: {(_t1 - _t0) * 1000:.1f}ms"
                f"  LevelUpdate: {(_t2 - _t1) * 1000:.1f}ms"
            )
            cfg = self._manager.context.get("config")
            if cfg is not None and cfg.debug_show_collision_timing:
                _timing = self._level.get_last_timing()
                if _timing:
                    _ms = lambda t: f"{t * 1000:.1f}ms" if t is not None else "skip"  # noqa: E731
                    print(
                        f"  Grid[move+shoot]: {_ms(_timing.get('grid_move_shoot', 0.0))}"
                        f"  Grid[bullets]: {_ms(_timing.get('grid_bullets'))}"
                        f"  Grid[bodies]: {_ms(_timing.get('grid_bodies'))}"
                        f"  Dive[bodies]: {_ms(_timing.get('dive_bodies'))}"
                        f"  Dive[bombs]: {_ms(_timing.get('dive_bombs'))}"
                    )
        if GameEvent.ENEMY_SHOT in events and self._snd_enemy_shoot is not None:
            self._sm_enemy_shoot.play(self._snd_enemy_shoot, volume=self._sfx_volume())

        # Process all pending hits (grid body-collisions + dive kills)
        cfg = self._manager.context.get("config")
        vx, vy = self._level.velocity
        for hit_x, hit_y, points in self._level.consume_pending_hits():
            self._update_score(points)
            ui_cfg: UIConfig = cfg.ui if cfg is not None else UIConfig()
            if points > 0:
                # Grid body-collision hits have points=0; no popup for those
                self._score_popups.append(
                    ScorePopup(
                        hit_x,
                        hit_y,
                        points,
                        duration=ui_cfg.popup_duration,
                        rise_speed=ui_cfg.popup_rise_speed,
                    )
                )
            exp = ExplosionSprite(
                x=hit_x,
                y=hit_y,
                frame_duration=0.05,
                vx=vx,
                vy=vy,
                scale=cfg.sprite_scale if cfg is not None else 1.0,
            )
            self._explosions.append(exp)
            self.spawn_destruction_effect(hit_x, hit_y, vx, vy)
            if self._snd_enemy_killed is not None:
                self._sm_enemy_killed.play(self._snd_enemy_killed, volume=self._sfx_volume())

        for hit_x, hit_y in self._level.consume_pending_non_lethal_hits():
            self._spawn_hit_ring(hit_x, hit_y)

        if hasattr(self._level, "consume_pending_boss_non_lethal_hits"):
            from typing import cast as _cast

            from src.levels.boss_level import BossLevel as _BossLevel

            _boss_level = _cast(_BossLevel, self._level)
            for hit_x, hit_y in _boss_level.consume_pending_boss_non_lethal_hits():
                _cfg = self._manager.context.get("config")
                _vx, _vy = self._level.velocity
                exp = ExplosionSprite(
                    x=hit_x,
                    y=hit_y,
                    frame_duration=0.05,
                    vx=_vx,
                    vy=_vy,
                    scale=_cfg.sprite_scale if _cfg is not None else 1.0,
                )
                self._explosions.append(exp)
                if self._snd_enemy_killed is not None:
                    self._sm_enemy_killed.play(self._snd_enemy_killed, volume=self._sfx_volume())

        if self._ship.hit_points < ship_hp_before and GameEvent.PLAYER_KILLED not in events:
            self._spawn_hit_ring(self._ship.center_x, self._ship.center_y)

        healed = self._ship.hit_points - ship_hp_before
        if healed > 0:
            ui_cfg = cfg.ui if cfg is not None else UIConfig()
            self._score_popups.append(
                ScorePopup(
                    self._ship.center_x,
                    self._ship.center_y + self._ship.height / 2,
                    healed,
                    duration=ui_cfg.popup_duration,
                    rise_speed=ui_cfg.popup_rise_speed,
                )
            )

        god_mode: bool = cfg.god_mode if cfg is not None else False
        # PLAYER_KILLED must be checked before level-clear so that a simultaneous
        # last-enemy-kill + player-death in the same frame doesn't silently drop the death.
        if GameEvent.PLAYER_KILLED in events and not god_mode:
            self._trigger_death()
            return
        for event in events:
            if event == GameEvent.POWERUP_COLLECTED:
                if self._snd_powerup_pickup is not None:
                    arcade.play_sound(self._snd_powerup_pickup, volume=self._sfx_volume())
            elif event == GameEvent.ENEMY_DESTROYED:
                # Boss kill — spawn a large particle burst at boss death position
                if self._level is not None and hasattr(self._level, "get_boss_death_center"):
                    pos = self._level.get_boss_death_center()
                    if pos is not None:
                        self.spawn_destruction_effect(pos[0], pos[1])
                if self._level is not None and self._level.is_cleared():
                    self._level_cleared = True
                    return
            elif event == GameEvent.LEVEL_COMPLETE:
                if self._level is not None and self._level.is_cleared():
                    self._level_cleared = True
                    return

        # Refresh shield overlay reference and pulse it
        manager = self._level.get_powerup_manager() if self._level is not None else None
        overlay = manager.get_active_overlay() if manager is not None else None
        if overlay is not None:
            new_ref = overlay.get_overlay_sprite()
            if new_ref is not self._shield_sprite_ref:
                self._overlay_list.clear()
                if new_ref is not None:
                    self._overlay_list.append(new_ref)
                self._shield_sprite_ref = new_ref
            if self._shield_sprite_ref is not None:
                from src.sprites.shield_sprite import ShieldSprite

                if isinstance(self._shield_sprite_ref, ShieldSprite):
                    self._shield_sprite_ref.pulse(delta_time)
        else:
            if self._shield_sprite_ref is not None:
                self._overlay_list.clear()
                self._shield_sprite_ref = None

        # If the bullet loop set _level_cleared this frame, don't double-process next turn.
        if self._level_cleared:
            return

    def on_draw(self) -> None:
        self.clear()
        self.window.background.draw()  # type: ignore[attr-defined]
        self.window.star_field.draw()  # type: ignore[attr-defined]

        if self._level is not None:
            self._level.draw()

        self._player_bullets.draw()
        if not self._paused:
            self._draw_enemy_hp_bars()
            self._draw_boss_hp_bar()
            self._draw_player_hp_bar()
        self._ship_list.draw()
        if self._shield_sprite_ref is not None:
            if self._ship is not None:
                self._shield_sprite_ref.center_x = self._ship.center_x
                self._shield_sprite_ref.center_y = self._ship.center_y
            self._overlay_list.draw()
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
        if self._debug and self._god_mode_text is not None:
            cfg = self._manager.context.get("config")
            if cfg is not None and cfg.god_mode:
                self._god_mode_text.draw()

        if self._paused:
            self._pause_overlay_list.draw()
            if self._paused_text is not None:
                self._paused_text.draw()

    def on_key_press(self, key: int, modifiers: int) -> None:
        from src.state import GameState

        if self._debug and key == arcade.key.E and (modifiers & arcade.key.MOD_SHIFT):
            self._manager.transition(GameState.LEVEL_COMPLETE)
            return

        if self._debug and key == arcade.key.B and (modifiers & arcade.key.MOD_SHIFT):
            from src.levels.level_factory import create_level

            cfg = self._manager.context.get("config")
            level_number = self._manager.context.get("level_number", 5)
            self._level = create_level(
                level_number,
                cfg,
                self.window.width,
                self.window.height,
                force_level_type="boss",
            )
            self._manager.context["current_level"] = self._level
            return

        if (
            self._debug
            and key == arcade.key.D
            and (modifiers & arcade.key.MOD_SHIFT)
            and self._level is not None
            and self._ship is not None
        ):
            self._level.debug_force_dive(self._ship.center_x)
            return

        if self._debug and key == arcade.key.G and (modifiers & arcade.key.MOD_SHIFT):
            cfg = self._manager.context.get("config")
            if cfg is not None:
                cfg.god_mode = not cfg.god_mode
            return

        if (
            self._debug
            and key == arcade.key.K
            and (modifiers & arcade.key.MOD_SHIFT)
            and not self._dying
            and self._ship is not None
        ):
            self._trigger_death()
            return

        if (
            self._debug
            and key == arcade.key.P
            and (modifiers & arcade.key.MOD_SHIFT)
            and self._level is not None
            and self._ship is not None
        ):
            manager = self._level.get_powerup_manager()
            if manager is not None:
                import random

                from src.powerups.sa_spawner import SAPowerUpSpawner

                effect_type = random.choice(SAPowerUpSpawner.UNLOCK_ORDER)
                sprite = manager.create_sprite(
                    effect_type,
                    random.uniform(40, self.window.width - 40),
                    0,  # y ignored — create_sprite spawns above window top
                )
                manager._sprites.append(sprite)
            return

        if key == arcade.key.P:
            self._paused = not self._paused
            if self._paused:
                import gc

                gc.collect()  # full collection now so nothing accumulates during pause
                self.window.music.pause()  # type: ignore[attr-defined]
            else:
                self.window.music.resume()  # type: ignore[attr-defined]
            return

        if self._paused:
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
        manager = self._level.get_powerup_manager() if self._level is not None else None
        behavior = manager.get_active_behavior() if manager is not None else None
        if behavior is not None:
            bullets = behavior.get_bullets(self._ship)
            if bullets and self._snd_player_shoot is not None:
                self._sm_player_shoot.play(self._snd_player_shoot, volume=self._sfx_volume())
            for b in bullets:
                self._player_bullets.append(b)
            return

        bullet = self._ship.try_fire()
        if bullet is not None:
            self._player_bullets.append(bullet)
            if self._snd_player_shoot is not None:
                self._sm_player_shoot.play(self._snd_player_shoot, volume=self._sfx_volume())

    def _filter_damage(self, amount: int) -> int:
        """Damage filter installed on PlayerShip — absorbs hits via active overlay."""
        if self._level is None:
            return amount
        manager = self._level.get_powerup_manager()
        if manager is None:
            return amount
        overlay = manager.get_active_overlay()
        if overlay is None:
            return amount
        depleted = overlay.on_hit_absorbed()
        if depleted:
            manager.remove_effect(overlay, self._ship, self._make_effect_context())
            self._shield_sprite_ref = None
            self._overlay_list.clear()
        return 0

    def _make_effect_context(self) -> dict:
        cfg = self._manager.context.get("config")
        return {
            "window_width": self.window.width,
            "window_height": self.window.height,
            "sprite_scale": cfg.sprite_scale if cfg is not None else 1.0,
        }

    def _trigger_death(self) -> None:
        """Begin death sequence: explosion plays, then PLAYER_KILLED transition."""
        if self._dying or self._ship is None:
            return
        self._dying = True
        self._death_timer = 0.0
        if self._snd_player_killed is not None:
            arcade.play_sound(self._snd_player_killed, volume=self._sfx_volume())
        manager = self._level.get_powerup_manager() if self._level is not None else None
        if manager is not None:
            from src.powerups.sa_manager import SAPowerUpManager

            if isinstance(manager, SAPowerUpManager):
                manager.clear_effects_only(self._ship, self._make_effect_context())
            else:
                manager.clear_all(self._ship, self._make_effect_context())
        self._shield_sprite_ref = None
        self._overlay_list.clear()
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

        sprites = list(self._level.get_all_enemy_sprites()) if self._level is not None else []

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

    def _draw_boss_hp_bar(self) -> None:
        """Draw the boss HP bar directly below the boss sprite."""
        if self._level is None:
            return
        data = getattr(self._level, "get_boss_hp_bar_data", lambda: None)()
        if data is None:
            return
        cx, bar_y, bar_width, hp, max_hp = data
        pct = hp / max_hp if max_hp > 0 else 0.0
        filled = bar_width * pct
        arcade.draw_lrbt_rectangle_filled(
            cx - bar_width / 2, cx + bar_width / 2, bar_y - 4, bar_y + 4, (80, 0, 0, 200)
        )
        if filled > 0:
            arcade.draw_lrbt_rectangle_filled(
                cx - bar_width / 2,
                cx - bar_width / 2 + filled,
                bar_y - 4,
                bar_y + 4,
                (220, 40, 40, 255),
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

    def _save_player_hp(self) -> None:
        """Persist the active player's current HP into PlayerState for level carry-over."""
        if self._ship is None:
            return
        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        if players:
            players[idx].current_hp = self._ship.hit_points

    def _update_score(self, points: int) -> None:
        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        if players:
            player = players[idx]
            old_milestones = player.score // _EXTRA_LIFE_INTERVAL
            player.score += points
            earned = player.score // _EXTRA_LIFE_INTERVAL - old_milestones
            for _ in range(earned):
                player.lives += 1
                if self._snd_extra_life is not None:
                    arcade.play_sound(self._snd_extra_life, volume=self._sfx_volume())
