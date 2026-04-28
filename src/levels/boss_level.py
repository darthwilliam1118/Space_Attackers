"""BossLevel — boss encounter level with BossDiveController."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any, Optional

import arcade
from agf.events import GameEvent
from agf.levels.base_level import BaseLevel

from src.dive_controller import DiveController

if TYPE_CHECKING:
    from src.boss_config import BossConfig
    from src.diving_config import DivingConfig
    from src.powerups.sa_manager import SAPowerUpManager
    from src.sprites.boss_sprite import BossSprite


# ---------------------------------------------------------------------------
# BossDiveController
# ---------------------------------------------------------------------------


class BossDiveController(DiveController):
    """DiveController variant for boss levels.

    Divers spawn from the boss position instead of a grid.  Each diver
    loops boss_diver_loop_count times then vanishes silently (no points,
    no explosion).  Group size and interval use boss-specific config values.

    Design notes:
    - DivingShip is NOT modified. Loop tracking is handled entirely here.
    - consume_pending_hits() always returns [] — boss divers award no score
      and no explosion on kill.
    - The parent update() handles all bullet/collision logic. We intercept
      the launch-timer block so the parent never tries to query an enemy grid.
    """

    def __init__(
        self,
        boss_cfg: "BossConfig",
        diving_cfg: "DivingConfig",
        boss_sprite: "BossSprite",
        window_width: int,
        window_height: int,
        debug: bool = False,
        sprite_scale: float = 1.0,
        hp_bar_duration: float = 1.0,
        enemy_cfg: Optional[Any] = None,
    ) -> None:
        super().__init__(
            diving_cfg,
            window_width,
            window_height,
            debug=debug,
            sprite_scale=sprite_scale,
            hp_bar_duration=hp_bar_duration,
        )
        self._boss_cfg = boss_cfg
        self._boss = boss_sprite
        self._enemy_cfg = enemy_cfg
        self._loops_remaining: dict[int, int] = {}
        self._source_color_type: dict[int, tuple[str, int]] = {}

    def setup(self, level: int, enemy_grid: Any = None) -> None:
        """Boss dive setup — boss interval/group from boss config; speed scales with level."""
        self._level = level
        self._dive_group_size = self._boss_cfg.boss_dive_group_size_max
        self._dive_interval = self._boss_cfg.boss_dive_interval_base
        self._dive_timer = self._boss_cfg.boss_dive_interval_base
        cfg = self._config
        self._dive_speed = min(
            cfg.dive_speed_base + (level - 2) * cfg.dive_speed_step,
            cfg.dive_speed_max,
        )

    def update(
        self,
        delta_time: float,
        enemy_grid: Any,
        player_ship: Any,
        player_bullets: arcade.SpriteList,
    ) -> list[GameEvent]:
        from src.sprites.diving_ship import DiveState

        was_blocked = self.new_dive_launches_blocked
        player_x = player_ship.center_x if player_ship else self._window_width / 2

        # Update home position for returning divers so they track the moving boss.
        for ship in self._active_ships:
            if ship._state == DiveState.RETURNING:
                ship._home_x = self._boss.center_x
                ship._home_y = self._boss.center_y

        # Block parent's launch-timer block entirely — we handle it ourselves.
        self.new_dive_launches_blocked = True
        events = super().update(delta_time, None, player_ship, player_bullets)
        self.new_dive_launches_blocked = was_blocked

        if not was_blocked and self._boss.hit_points > 0:
            # Re-launch: detect ships first entering RETURNING state after super() ran.
            # super() transitions DIVING→RETURNING inside ship.update() and leaves
            # them in _active_ships; they are only removed one frame later when DONE.
            # Popping from _loops_remaining on first detection ensures one re-launch
            # per ship, not one per RETURNING frame.
            for ship in self._active_ships:
                if ship._state == DiveState.RETURNING:
                    ship_id = id(ship)
                    if ship_id in self._loops_remaining:
                        loops_left = self._loops_remaining.pop(ship_id)
                        color, ship_type = self._source_color_type.pop(ship_id, ("Black", 1))
                        if loops_left > 0:
                            self._launch_single_diver(color, ship_type, player_x, loops_left - 1)

        # Clean up stale tracking for ships killed mid-dive (never entered RETURNING).
        active_ids = {id(s) for s in self._active_ships}
        for sid in list(self._loops_remaining):
            if sid not in active_ids:
                self._loops_remaining.pop(sid)
                self._source_color_type.pop(sid, None)

        # Our own launch timer (parent's timer is disabled via new_dive_launches_blocked).
        if not was_blocked and self._boss.hit_points > 0:
            self._dive_timer -= delta_time
            if self._dive_timer <= 0.0:
                self._dive_timer = self._boss_cfg.boss_dive_interval_base
                self._launch_boss_group(player_x)

        return events

    def _launch_boss_group(self, player_x: float) -> None:
        from src.sprites.enemy_sprite import EnemySprite

        count = self._boss_cfg.boss_dive_group_size_max
        colors = ["Black", "Blue", "Green", "Red"]
        group = [(random.choice(colors), random.randint(1, 4)) for _ in range(count)]

        # Measure one diver sprite to compute row width, then centre on boss x.
        c0, t0 = group[0]
        diver_w = EnemySprite(c0, t0, col=0, row=0, scale=self._sprite_scale).width
        start_x = self._boss.center_x - count * diver_w / 2.0 + diver_w / 2.0
        spawn_y = self._boss.center_y

        for i, (color, ship_type) in enumerate(group):
            self._launch_single_diver(
                color,
                ship_type,
                player_x,
                self._boss_cfg.boss_diver_loop_count - 1,
                spawn_x=start_x + i * diver_w,
                spawn_y=spawn_y,
            )

    def _launch_single_diver(
        self,
        color: str,
        ship_type: int,
        player_x: float,
        loops_remaining: int,
        spawn_x: Optional[float] = None,
        spawn_y: Optional[float] = None,
    ) -> None:
        from src.dive_path import make_dive_path
        from src.sprites.diving_ship import DivingShip
        from src.sprites.enemy_sprite import EnemySprite

        if spawn_x is not None:
            x = spawn_x
            y = spawn_y if spawn_y is not None else self._boss.center_y
        else:
            x = self._boss.center_x + random.uniform(
                -self._boss.width / 4.0, self._boss.width / 4.0
            )
            y = self._boss.center_y

        source = EnemySprite(color, ship_type, col=0, row=0, scale=self._sprite_scale)
        source.center_x = x
        source.center_y = y
        source.home_x = x
        source.home_y = y
        from src.enemy_config import EnemyConfig

        ecfg = self._enemy_cfg if self._enemy_cfg is not None else EnemyConfig()
        base_hp = ecfg.enemy_hp.get(ship_type, 100)
        scaled_hp = int(base_hp * (ecfg.enemy_hp_level_factor ** (self._level - 1)))
        source.hit_points = scaled_hp
        source.max_hit_points = scaled_hp

        curve_sign = random.choice([-1, 1])
        waypoints = make_dive_path(
            start=(x, y),
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
            launch_delay=0.0,
            scale=self._sprite_scale,
        )
        self._active_ships.append(ship)
        self._ship_list.append(ship)
        self._loops_remaining[id(ship)] = loops_remaining
        self._source_color_type[id(ship)] = (color, ship_type)


# ---------------------------------------------------------------------------
# BossLevel
# ---------------------------------------------------------------------------


class BossLevel(BaseLevel):
    """Boss encounter level.

    One large boss sprite moves side-to-side, descending each bounce.
    Boss fires bullets randomly across its width (spread or single).
    Boss receives shield, big_gun, and spread_shot power-ups.
    Boss spawns periodic diving enemy groups.
    Player also receives full power-up drops independently.
    Boss death triggers a multi-second explosion sequence before LEVEL_COMPLETE.
    """

    def __init__(
        self,
        boss_config: "BossConfig",
        diving_cfg: "DivingConfig",
        window_width: int,
        window_height: int,
        player_powerup_manager: Optional["SAPowerUpManager"] = None,
        debug: bool = False,
        sprite_scale: float = 1.0,
        hp_bar_duration: float = 1.0,
        enemy_cfg: Optional[Any] = None,
    ) -> None:
        self._boss_cfg = boss_config
        self._diving_cfg = diving_cfg
        self._enemy_cfg = enemy_cfg
        self._w = window_width
        self._h = window_height
        self._debug = debug
        self._scale = sprite_scale
        self._hp_bar_duration = hp_bar_duration

        self._boss: Optional["BossSprite"] = None
        self._boss_list: arcade.SpriteList = arcade.SpriteList()
        self._bullet_list: arcade.SpriteList = arcade.SpriteList()
        self._dive_ctrl: Optional[BossDiveController] = None
        self._player_powerup_manager = player_powerup_manager
        self._boss_powerup_manager: Optional[Any] = None

        # Death sequence state
        self._dying: bool = False
        self._death_timer: float = 0.0
        self._death_explosion_count_spawned: int = 0
        self._death_explosion_interval: float = 0.0
        self._death_explosion_timer: float = 0.0
        self._death_explosions: arcade.SpriteList = arcade.SpriteList()
        self._boss_death_center: Optional[tuple[float, float]] = None
        self._level_cleared: bool = False

        # Pending events (extra: non-lethal hits not from boss sprite)
        self._pending_non_lethal: list[tuple[float, float]] = []

        self._encounter: int = 1

    @property
    def level_type(self) -> str:
        return "boss"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def setup(self, level_number: int) -> None:
        from src.sprites.boss_sprite import BossSprite

        self._encounter = level_number // 5

        self._boss = BossSprite(
            config=self._boss_cfg,
            encounter=self._encounter,
            window_width=self._w,
            window_height=self._h,
            scale=self._scale,
        )
        self._boss_list = arcade.SpriteList()
        self._boss_list.append(self._boss)

        self._dive_ctrl = BossDiveController(
            boss_cfg=self._boss_cfg,
            diving_cfg=self._diving_cfg,
            boss_sprite=self._boss,
            window_width=self._w,
            window_height=self._h,
            debug=self._debug,
            sprite_scale=self._scale,
            hp_bar_duration=self._hp_bar_duration,
            enemy_cfg=self._enemy_cfg,
        )
        self._dive_ctrl.setup(level_number)

        # Boss power-up manager
        pu_config = getattr(self._player_powerup_manager, "_config", None)
        if pu_config is not None:
            from src.powerups.boss_manager import BossPowerUpManager

            self._boss_powerup_manager = BossPowerUpManager(
                pu_config,
                self._boss_cfg,
                self._w,
                self._h,
                sprite_scale=self._scale,
            )
            self._boss_powerup_manager.setup(level_number, "boss")

        if self._player_powerup_manager is not None:
            self._player_powerup_manager.setup(level_number, "boss")

    # ------------------------------------------------------------------
    # Per-frame
    # ------------------------------------------------------------------

    def update(
        self,
        delta_time: float,
        player_ship: Any,
        player_bullets: Optional[arcade.SpriteList] = None,
        frame_count: int = 0,
    ) -> list[GameEvent]:
        bullets = player_bullets if player_bullets is not None else arcade.SpriteList()
        events: list[GameEvent] = []

        if self._level_cleared:
            return events

        # Death sequence — continue animating then signal complete
        if self._dying:
            events += self._update_death_sequence(delta_time)
            return events

        if self._boss is None:
            return events

        # Move boss and generate bullets
        self._boss.update_boss(delta_time)

        # Add new boss bullets to list
        for bullet in self._boss.consume_pending_bullets():
            self._bullet_list.append(bullet)

        # Move existing boss bullets (self-remove when off-screen)
        for bullet in list(self._bullet_list):
            bullet.update(delta_time)

        # Boss bullets vs player ship
        if player_ship is not None and not player_ship.is_invincible():
            hits = arcade.check_for_collision_with_list(player_ship, self._bullet_list)
            for hit in hits:
                hit.remove_from_sprite_lists()
                damage = getattr(hit, "damage", self._boss_cfg.boss_bullet_damage)
                killed = player_ship.take_damage(damage)
                if killed:
                    events.append(GameEvent.PLAYER_KILLED)
                    return events
                else:
                    self._pending_non_lethal.append((player_ship.center_x, player_ship.center_y))

        # Direct contact: boss body vs player ship
        if player_ship is not None and not player_ship.is_invincible():
            if arcade.check_for_collision(player_ship, self._boss):
                if player_ship.take_damage(player_ship.hit_points):
                    events.append(GameEvent.PLAYER_KILLED)
                return events

        # Player bullets vs boss
        for bullet in list(bullets):
            if not bullet.sprite_lists:
                continue
            if arcade.check_for_collision(bullet, self._boss):
                bullet.remove_from_sprite_lists()
                damage = getattr(bullet, "damage", 1)
                absorbed = self._apply_damage_to_boss(damage)
                if not absorbed:
                    killed = self._boss.take_damage(damage)
                    if killed:
                        self._boss.record_hit(lethal=True)
                        self._start_death_sequence()
                        events.append(GameEvent.ENEMY_DESTROYED)
                        return events
                    else:
                        self._boss.record_hit(
                            lethal=False, hit_x=bullet.center_x, hit_y=bullet.center_y
                        )

        # Dive controller
        if self._dive_ctrl is not None:
            dive_events = self._dive_ctrl.update(delta_time, None, player_ship, bullets)
            events += dive_events

        # Boss hits bottom or top margin — reverse vertical direction
        zone_top_pct = getattr(getattr(player_ship, "_config", None), "ship_zone_height_pct", 0.33)
        ship_zone_top = self._h * zone_top_pct
        self._boss.check_vertical_boundary(ship_zone_top)

        # Boss power-ups
        if self._boss_powerup_manager is not None and self._boss is not None:
            collected = self._boss_powerup_manager.update(
                delta_time, self._boss, {}, [self._boss.center_x]
            )
            for _ in collected:
                events.append(GameEvent.POWERUP_COLLECTED)

        # Player power-ups
        if self._player_powerup_manager is not None:
            enemy_xs = [self._boss.center_x] if self._boss else []
            collected = self._player_powerup_manager.update(delta_time, player_ship, {}, enemy_xs)
            for _ in collected:
                events.append(GameEvent.POWERUP_COLLECTED)

        return events

    def _apply_damage_to_boss(self, amount: int) -> bool:
        """Check boss shield. Returns True if the hit was absorbed."""
        if self._boss is None or not self._boss.shield_active:
            return False
        overlay = (
            self._boss_powerup_manager.get_active_overlay()
            if self._boss_powerup_manager is not None
            else None
        )
        if overlay is None:
            return False
        depleted = overlay.on_hit_absorbed()
        if depleted:
            self._boss_powerup_manager.remove_effect(overlay, self._boss, {})
        return True

    def _start_death_sequence(self) -> None:
        self._dying = True
        self._death_timer = 0.0
        self._death_explosion_count_spawned = 0
        cfg = self._boss_cfg
        self._death_explosion_interval = cfg.boss_death_duration / cfg.boss_death_explosion_count
        self._death_explosion_timer = 0.0
        if self._boss is not None:
            self._boss_death_center = (self._boss.center_x, self._boss.center_y)
            self._boss_list.clear()  # hide boss sprite immediately

    def _update_death_sequence(self, delta_time: float) -> list[GameEvent]:
        from agf.sprites.explosion import ExplosionSprite

        self._death_timer += delta_time
        self._death_explosion_timer += delta_time

        if (
            self._boss_death_center is not None
            and self._death_explosion_count_spawned < self._boss_cfg.boss_death_explosion_count
            and self._death_explosion_timer >= self._death_explosion_interval
        ):
            self._death_explosion_timer = 0.0
            self._death_explosion_count_spawned += 1
            cx, cy = self._boss_death_center
            half_w = (self._boss.width if self._boss else 60) / 2.0
            half_h = (self._boss.height if self._boss else 60) / 2.0
            x = cx + random.uniform(-half_w, half_w)
            y = cy + random.uniform(-half_h, half_h)
            exp = ExplosionSprite(x=x, y=y, frame_duration=0.05, scale=self._scale * 1.5)
            self._death_explosions.append(exp)

        for exp in list(self._death_explosions):
            exp.update(delta_time)  # auto-removes itself from SpriteList when complete

        if self._death_timer >= self._boss_cfg.boss_death_duration:
            self._level_cleared = True
            return [GameEvent.LEVEL_COMPLETE]

        return []

    def draw(self) -> None:
        if self._dive_ctrl is not None:
            self._dive_ctrl.get_all_sprites().draw()
            self._dive_ctrl.get_all_bullets().draw()

        self._bullet_list.draw()
        self._boss_list.draw()

        if self._boss_powerup_manager is not None:
            self._boss_powerup_manager.draw()

        if self._player_powerup_manager is not None:
            self._player_powerup_manager.draw()

        self._death_explosions.draw()

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def is_cleared(self) -> bool:
        return self._level_cleared

    # ------------------------------------------------------------------
    # Bullet collision (player bullets)
    # ------------------------------------------------------------------

    def apply_player_bullet(self, bullet: Any) -> None:
        """Always returns None — bullet vs boss collision is handled in update().

        RunLevelView's bullet loop calls apply_player_bullet() first, then passes
        the full player_bullets list to level.update().  Returning None here means
        the bullet is NOT removed in the loop, so it reaches update() intact.
        No double damage occurs because update() removes the bullet on first hit.
        """
        return None

    # ------------------------------------------------------------------
    # Hit reporting
    # ------------------------------------------------------------------

    def consume_pending_hits(self) -> list[tuple[float, float, int]]:
        hits: list[tuple[float, float, int]] = []
        if self._boss is not None:
            hits += self._boss.consume_pending_hits()
        if self._dive_ctrl is not None:
            hits += self._dive_ctrl.consume_pending_hits()
        return hits

    def consume_pending_non_lethal_hits(self) -> list[tuple[float, float]]:
        hits = list(self._pending_non_lethal)
        self._pending_non_lethal.clear()
        return hits

    def consume_pending_boss_non_lethal_hits(self) -> list[tuple[float, float]]:
        if self._boss is not None:
            return self._boss.consume_pending_non_lethal_hits()
        return []

    # ------------------------------------------------------------------
    # Sprite lists
    # ------------------------------------------------------------------

    def get_all_enemy_sprites(self) -> arcade.SpriteList:
        # Return diver sprites (have hp_bar_timer); boss has its own dedicated HP bar.
        if self._dive_ctrl is not None:
            return self._dive_ctrl.get_ship_sprite_list()
        return arcade.SpriteList()

    def get_enemy_bullet_sprite_list(self) -> arcade.SpriteList:
        return self._bullet_list

    # ------------------------------------------------------------------
    # Power-ups
    # ------------------------------------------------------------------

    def get_powerup_manager(self) -> Optional[Any]:
        return self._player_powerup_manager

    def get_enemy_x_positions(self) -> list[float]:
        return [self._boss.center_x] if self._boss is not None else []

    # ------------------------------------------------------------------
    # Boss HP bar data — consumed by RunLevelView
    # ------------------------------------------------------------------

    def get_boss_hp_bar_data(self) -> Optional[tuple[float, float, float, int, int]]:
        """Returns (center_x, bar_y, bar_width, hp, max_hp) or None.

        Returns None during the death sequence or before setup().
        bar_y floats just above the boss sprite.
        """
        if self._boss is None or self._dying:
            return None
        return (
            self._boss.center_x,
            self._boss.center_y + self._boss.height / 2.0 + 8,
            self._boss.width,
            self._boss.hit_points,
            self._boss.max_hit_points,
        )

    def get_boss_death_center(self) -> Optional[tuple[float, float]]:
        """Last known boss center before it was hidden. Used by RunLevelView."""
        return self._boss_death_center

    # ------------------------------------------------------------------
    # 2P
    # ------------------------------------------------------------------

    def has_any_airborne(self) -> bool:
        return self._dive_ctrl is not None and self._dive_ctrl.has_any_airborne()

    def block_new_launches(self) -> None:
        if self._dive_ctrl is not None:
            self._dive_ctrl.new_dive_launches_blocked = True

    # ------------------------------------------------------------------
    # Velocity — for explosion drift
    # ------------------------------------------------------------------

    @property
    def velocity(self) -> tuple[float, float]:
        if self._boss is not None:
            return (self._boss._vx, 0.0)
        return (0.0, 0.0)

    # ------------------------------------------------------------------
    # Snapshot / restore
    # ------------------------------------------------------------------

    def to_snapshot(self) -> dict:
        snap: dict = {"level_type": "boss"}
        if self._boss is not None:
            snap["boss"] = {
                "center_x": self._boss.center_x,
                "center_y": self._boss.center_y,
                "vx": self._boss._vx,
                "hp": self._boss.hit_points,
                "encounter": self._encounter,
            }
        if self._dive_ctrl is not None:
            snap["diving"] = self._dive_ctrl.to_snapshot()
        if self._player_powerup_manager is not None:
            snap["powerups"] = self._player_powerup_manager.to_snapshot()
        return snap

    @classmethod
    def from_snapshot(
        cls,
        snapshot: dict,
        config: Any,
        window_width: int,
        window_height: int,
    ) -> "BossLevel":
        from src.boss_config import BossConfig
        from src.diving_config import DivingConfig
        from src.sprites.boss_sprite import BossSprite

        boss_cfg = config.boss if config else BossConfig()
        diving_cfg = config.diving if config else DivingConfig()
        enemy_cfg = config.enemies if config else None
        debug = config.debug if config else False
        scale = config.sprite_scale if config else 1.0
        hp_dur = config.ui.hp_bar_duration if config else 1.0

        boss_snap = snapshot.get("boss", {})
        encounter = boss_snap.get("encounter", 1)
        level_number = encounter * 5

        powerup_manager = None
        pu_cfg = getattr(config, "powerups", None) if config else None
        if pu_cfg is not None:
            from src.powerups.sa_manager import SAPowerUpManager

            pu_snap = snapshot.get("powerups")
            if pu_snap:
                powerup_manager = SAPowerUpManager.from_snapshot(
                    pu_snap,
                    pu_cfg,
                    window_width,
                    window_height,
                    sprite_scale=scale,
                    level_number=level_number,
                    level_type="boss",
                )
            else:
                powerup_manager = SAPowerUpManager(
                    pu_cfg, window_width, window_height, sprite_scale=scale
                )
                powerup_manager.setup(level_number, "boss")

        level = cls(
            boss_cfg,
            diving_cfg,
            window_width,
            window_height,
            powerup_manager,
            debug,
            scale,
            hp_dur,
            enemy_cfg=enemy_cfg,
        )

        level._encounter = encounter
        level._boss = BossSprite(boss_cfg, encounter, window_width, window_height, scale)
        level._boss.center_x = boss_snap.get("center_x", window_width / 2)
        level._boss.center_y = boss_snap.get("center_y", window_height * 0.8)
        level._boss._vx = boss_snap.get("vx", boss_cfg.boss_speed_base)
        level._boss.hit_points = boss_snap.get("hp", level._boss.max_hit_points)
        level._boss_list = arcade.SpriteList()
        level._boss_list.append(level._boss)

        # Restore dive controller
        dive_snap = snapshot.get("diving")
        level._dive_ctrl = BossDiveController(
            boss_cfg=boss_cfg,
            diving_cfg=diving_cfg,
            boss_sprite=level._boss,
            window_width=window_width,
            window_height=window_height,
            debug=debug,
            sprite_scale=scale,
            hp_bar_duration=hp_dur,
            enemy_cfg=enemy_cfg,
        )
        if dive_snap:
            level._dive_ctrl.setup(dive_snap["level"])
            level._dive_ctrl._dive_timer = dive_snap.get(
                "dive_timer", boss_cfg.boss_dive_interval_base
            )
        else:
            level._dive_ctrl.setup(level_number)

        # Recreate boss power-up manager
        if pu_cfg is not None:
            from src.powerups.boss_manager import BossPowerUpManager

            level._boss_powerup_manager = BossPowerUpManager(
                pu_cfg, boss_cfg, window_width, window_height, sprite_scale=scale
            )
            level._boss_powerup_manager.setup(level_number, "boss")

        return level
