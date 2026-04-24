# Feature: Boss Level

## Overview
A boss level occurs every 5 levels. If a meteor storm (every 3 levels)
would coincide with a boss level, the boss takes priority and the meteor
storm is skipped — the next meteor storm occurs 3 levels later.

The boss is a single large enemy sprite (3x scale, configurable) that
moves side to side and descends each bounce like a standard grid. It
should reverse and go back up if it gets within bottom margin of window. It
fires bullets randomly distributed across its width, receives power-ups
(shield, big gun, spread shot only), spawns periodic diving enemy groups,
and has a dramatic multi-second death sequence before level complete.

## Files to create

```
src/levels/boss_level.py        — BossLevel(BaseLevel)
src/boss_config.py              — BossConfig dataclass
src/sprites/boss_sprite.py      — BossSprite(arcade.Sprite)
src/sprites/boss_bullet.py      — BossBullet (or reuse EnemyBullet)
```

## Files to modify

```
src/levels/level_factory.py     — add "boss" case, update _get_level_type()
src/game_config.py              — add BossConfig section
game_config.toml                — add [boss] section
src/views/run_level.py          — handle boss death sequence,
                                  boss HP bar rendering
```

## Files NOT modified

```
src/dive_controller.py          — reused as-is
src/sprites/diving_ship.py      — reused as-is
src/enemy_grid.py               — not used in boss level
src/powerups/                   — reused as-is (boss uses SAPowerUpManager)
```

---

## Level sequence logic

Update `_get_level_type()` in `level_factory.py`:

```python
def _get_level_type(level_number: int) -> str:
    """Boss every 5 levels. Meteor every 3 levels.
    When both coincide, boss wins and meteor resets to next interval."""
    is_boss = level_number % 5 == 0
    is_meteor = level_number % 3 == 0

    if is_boss:
        return "boss"   # boss wins over meteor
    if is_meteor:
        return "meteor"
    return "standard"
```

No state tracking needed — the modulo arithmetic handles the skip
naturally. Level 15 is divisible by both 5 and 3 — boss wins.
Next meteor is level 18 (15 + 3), which is not divisible by 5, so
meteor runs normally.

---

## BossConfig dataclass

```python
# src/boss_config.py
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class BossConfig:
    # Sprite
    boss_sprite: str = "assets/images/PNG/Enemies/enemyBlack5.png"
    boss_scale_base: float = 3.0        # sprite scale at first boss level
    boss_scale_per_boss: float = 0.0    # scale increase per boss encounter
                                         # (0 = always same size)

    # HP
    boss_hp_base: int = 500             # HP at first boss level (level 5)
    boss_hp_per_boss: int = 200         # HP added per subsequent boss level

    # Movement — same drop/bounce logic as standard grid
    boss_speed_base: float = 60.0       # px/s horizontal at level 5
    boss_speed_per_boss: float = 8.0    # px/s added per boss encounter
    boss_speed_max: float = 180.0       # ceiling speed
    boss_side_margin: float = 40.0      # px from window edge before reversing
    boss_drop_distance: float = 24.0    # px dropped per bounce

    # Shooting
    boss_fire_interval_base: float = 1.2   # seconds between shots at level 5
    boss_fire_interval_per_boss: float = -0.08  # reduction per boss encounter
    boss_fire_interval_min: float = 0.35   # floor interval
    boss_bullet_speed: float = 280.0
    boss_bullet_damage: int = 1
    boss_spread_chance: float = 0.25    # probability of spread burst vs single
    boss_spread_count: int = 5          # bullets in a spread burst
    boss_spread_angle: float = 30.0     # total spread angle in degrees

    # Scoring
    boss_points_base: int = 1000
    boss_points_per_boss: int = 500     # added per subsequent boss encounter

    # Death sequence
    boss_death_duration: float = 2.5    # seconds for death animation
    boss_death_explosion_count: int = 8 # number of explosions during death
    boss_death_particle_count: int = 60 # particles in death burst

    # Diving
    boss_dive_group_size_max: int = 2   # cap on simultaneous divers
    boss_dive_interval_base: float = 8.0
    boss_dive_interval_min: float = 4.0
    boss_diver_loop_count: int = 3      # times each diver loops before vanishing

    # Power-ups (boss receives these from SAPowerUpManager)
    # Boss power-up weights — boss never gets health or free_move
    boss_pu_weight_shield: float = 8.0
    boss_pu_weight_big_gun: float = 10.0
    boss_pu_weight_spread_shot: float = 10.0
    # All other types have weight 0 — filtered in BossPowerUpManager
```

Add to `game_config.toml`:

```toml
[boss]
boss_sprite = "assets/images/PNG/Enemies/enemyBlack5.png"
boss_scale_base = 3.0
boss_hp_base = 500
boss_hp_per_boss = 200
boss_speed_base = 60.0
boss_speed_per_boss = 8.0
boss_speed_max = 180.0
boss_side_margin = 40.0
boss_drop_distance = 24.0
boss_fire_interval_base = 1.2
boss_fire_interval_per_boss = -0.08
boss_fire_interval_min = 0.35
boss_bullet_speed = 280.0
boss_bullet_damage = 1
boss_spread_chance = 0.25
boss_spread_count = 5
boss_spread_angle = 30.0
boss_points_base = 1000
boss_points_per_boss = 500
boss_death_duration = 2.5
boss_death_explosion_count = 8
boss_death_particle_count = 60
boss_dive_group_size_max = 2
boss_dive_interval_base = 8.0
boss_dive_interval_min = 4.0
boss_diver_loop_count = 3
boss_pu_weight_shield = 8.0
boss_pu_weight_big_gun = 10.0
boss_pu_weight_spread_shot = 10.0
```

Add `BossConfig` to `GameConfig` dataclass and wire into `load()` and
`save()` following the same pattern as `MeteorConfig`.

---

## Boss encounter number

BossLevel needs to know which boss encounter this is (1st, 2nd, 3rd...)
to scale HP, speed, points, and sprite size. Compute from level number:

```python
def _boss_encounter_number(level_number: int) -> int:
    """Returns 1 for level 5, 2 for level 10, etc."""
    return level_number // 5
```

Pass this into `BossLevel.setup()` so scaling is deterministic and
does not require persistent state.

---

## BossSprite

```python
# src/sprites/boss_sprite.py
from __future__ import annotations
import random
import math
from typing import Optional
import arcade
from agf.paths import resource_path
from src.boss_config import BossConfig
from src.sprites.enemy_bullet import EnemyBullet


class BossSprite(arcade.Sprite):
    """Single large enemy sprite with movement, shooting, and HP tracking.

    Movement mirrors standard EnemyGrid: side-to-side with downward
    drop on each wall bounce. Boundary detection uses the boss sprite's
    actual scaled dimensions so margins are always correct regardless
    of scale.
    """

    def __init__(self, config: BossConfig, encounter: int,
                 window_width: int, window_height: int,
                 scale: float = 1.0,
                 texture: Optional[arcade.Texture] = None):
        if texture is not None:
            super().__init__(texture=texture)
        else:
            super().__init__(
                arcade.load_texture(resource_path(config.boss_sprite))
            )
        # Boss scale = configured base + per-encounter increase
        boss_scale = (config.boss_scale_base
                      + config.boss_scale_per_boss * (encounter - 1))
        self.scale = boss_scale * scale   # sprite_scale multiplied in
        self._sprite_scale = scale

        self._config = config
        self._encounter = encounter
        self._window_width = window_width
        self._window_height = window_height

        # Compute scaled HP
        self.hit_points: int = (config.boss_hp_base
                                + config.boss_hp_per_boss * (encounter - 1))
        self.max_hit_points: int = self.hit_points

        # Movement
        speed = min(
            config.boss_speed_base + config.boss_speed_per_boss * (encounter - 1),
            config.boss_speed_max,
        )
        self._vx: float = speed      # positive = moving right
        self._vy: float = 0.0

        # Fire timer
        interval = max(
            config.boss_fire_interval_min,
            config.boss_fire_interval_base
            + config.boss_fire_interval_per_boss * (encounter - 1),
        )
        self._fire_timer: float = interval
        self._fire_interval: float = interval

        # Active power-up state (mirroring PlayerShip attributes)
        self.shield_active: bool = False
        self.shield_hits_remaining: int = 0
        self.bullet_scale_multiplier: float = 1.0
        self.bullet_damage_multiplier: int = 1

        # Pending bullets generated this frame
        self._pending_bullets: list[EnemyBullet] = []

        # Pending hits for RunLevelView consumption
        self._pending_hits: list[tuple[float, float, int]] = []
        self._pending_non_lethal: list[tuple[float, float]] = []

        # Spawn at top centre
        self.center_x = window_width / 2.0
        self.center_y = (window_height
                         - config.boss_side_margin
                         - self.height / 2.0)

        # Points
        self._points: int = (config.boss_points_base
                             + config.boss_points_per_boss * (encounter - 1))

    # ------------------------------------------------------------------
    # Per-frame
    # ------------------------------------------------------------------

    def update_boss(self, delta_time: float) -> None:
        """Move boss and tick fire timer. Call from BossLevel.update()."""
        self._move(delta_time)
        self._tick_fire(delta_time)

    def _move(self, delta_time: float) -> None:
        cfg = self._config
        half_w = self.width / 2.0

        self.center_x += self._vx * delta_time

        # Bounce off side margins
        left_limit = cfg.boss_side_margin + half_w
        right_limit = self._window_width - cfg.boss_side_margin - half_w

        if self._vx > 0 and self.center_x >= right_limit:
            self.center_x = right_limit
            self._vx = -self._vx
            self.center_y -= cfg.boss_drop_distance
        elif self._vx < 0 and self.center_x <= left_limit:
            self.center_x = left_limit
            self._vx = -self._vx
            self.center_y -= cfg.boss_drop_distance

    def _tick_fire(self, delta_time: float) -> None:
        self._fire_timer -= delta_time
        if self._fire_timer <= 0.0:
            self._fire_timer = self._fire_interval
            self._generate_bullets()

    def _generate_bullets(self) -> None:
        """Generate bullets distributed randomly across boss width.

        25% chance of spread burst, otherwise single aimed shot.
        Boss power-ups affect bullet damage and spread pattern.
        """
        cfg = self._config
        import random

        if random.random() < cfg.boss_spread_chance:
            # Spread burst — bullets fan out downward from random x positions
            count = cfg.boss_spread_count
            half_angle = cfg.boss_spread_angle / 2.0
            for i in range(count):
                # Distribute firing x across boss width
                x_offset = random.uniform(-self.width / 2.0, self.width / 2.0)
                angle = random.uniform(-half_angle, half_angle)
                self._pending_bullets.append(self._make_bullet(
                    self.center_x + x_offset,
                    self.center_y - self.height / 2.0,
                    angle,
                ))
        else:
            # Single shot from random x position on boss
            x_offset = random.uniform(-self.width / 2.0, self.width / 2.0)
            self._pending_bullets.append(self._make_bullet(
                self.center_x + x_offset,
                self.center_y - self.height / 2.0,
                0.0,
            ))

    def _make_bullet(self, x: float, y: float,
                     angle_deg: float) -> "EnemyBullet":
        from src.sprites.enemy_bullet import EnemyBullet
        damage = (self._config.boss_bullet_damage
                  * self.bullet_damage_multiplier)
        return EnemyBullet(
            x=x, y=y,
            speed=self._config.boss_bullet_speed,
            window_width=self._window_width,
            window_height=self._window_height,
            angle_deg=angle_deg,
            damage=damage,
            scale=self._sprite_scale * self.bullet_scale_multiplier,
        )

    # ------------------------------------------------------------------
    # Damage
    # ------------------------------------------------------------------

    def take_damage(self, amount: int) -> bool:
        """Apply damage. Returns True if boss is dead."""
        self.hit_points = max(0, self.hit_points - amount)
        return self.hit_points <= 0

    def is_invincible(self) -> bool:
        """Required by SAPowerUpManager interface."""
        return False

    # ------------------------------------------------------------------
    # Bullet consumption
    # ------------------------------------------------------------------

    def consume_pending_bullets(self) -> list["EnemyBullet"]:
        bullets = list(self._pending_bullets)
        self._pending_bullets.clear()
        return bullets

    # ------------------------------------------------------------------
    # Hit reporting (mirrors EnemyGrid/DiveController pattern)
    # ------------------------------------------------------------------

    def consume_pending_hits(self) -> list[tuple[float, float, int]]:
        hits = list(self._pending_hits)
        self._pending_hits.clear()
        return hits

    def consume_pending_non_lethal_hits(self) -> list[tuple[float, float]]:
        hits = list(self._pending_non_lethal)
        self._pending_non_lethal.clear()
        return hits

    def record_hit(self, lethal: bool) -> None:
        """Called when a player bullet hits the boss."""
        if lethal:
            self._pending_hits.append(
                (self.center_x, self.center_y, self._points)
            )
        else:
            self._pending_non_lethal.append(
                (self.center_x, self.center_y)
            )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def points(self) -> int:
        return self._points

    def reaches_bottom(self, ship_zone_top: float) -> bool:
        """True if boss bottom edge enters the player movement zone."""
        return (self.center_y - self.height / 2.0) <= ship_zone_top
```

---

## BossDiveController

Rather than creating a new class, **reuse `DiveController` directly**
with a thin wrapper that enforces boss-specific constraints:

- Group size capped at `boss_dive_group_size_max`
- Dive interval uses boss-specific timing
- Divers spawn from boss position rather than grid position
- Each diver loops `boss_diver_loop_count` times then vanishes
  with no points and no explosion

The cleanest approach is to subclass `DiveController`:

```python
# In boss_level.py — inner class or separate class

class BossDiveController(DiveController):
    """DiveController variant for boss levels.

    Divers spawn from boss position, loop N times, then silently vanish.
    No points awarded. No explosion on vanish.
    """

    def __init__(self, config: BossConfig, diving_cfg,
                 boss_sprite: BossSprite,
                 window_width: int, window_height: int,
                 debug: bool = False, sprite_scale: float = 1.0,
                 hp_bar_duration: float = 1.0):
        super().__init__(diving_cfg, window_width, window_height,
                         debug=debug, sprite_scale=sprite_scale,
                         hp_bar_duration=hp_bar_duration)
        self._boss_cfg = config
        self._boss = boss_sprite
        # Override group size cap
        self._max_group_size = config.boss_dive_group_size_max
        # Override interval
        self._dive_interval = config.boss_dive_interval_base
        self._dive_timer = 0.0

    def setup(self, level_number: int,
              enemy_grid: Any = None) -> None:
        """Boss dive setup — ignores enemy_grid."""
        # Do not call super().setup() — boss has no grid
        self._dive_timer = self._boss_cfg.boss_dive_interval_base

    def _select_divers(self, enemy_grid: Any) -> list:
        """Override: select random ship sprites from asset pool,
        spawn at boss position rather than from grid slots."""
        # Import the enemy sprite factory used by EnemyGrid
        from src.sprites.enemy_sprite import EnemySprite
        import random
        count = min(
            self._boss_cfg.boss_dive_group_size_max,
            random.randint(1, self._boss_cfg.boss_dive_group_size_max)
        )
        divers = []
        colors = ["Black", "Blue", "Green", "Red"]
        for i in range(count):
            color = random.choice(colors)
            ship_type = random.randint(1, 4)
            sprite = EnemySprite(color, ship_type, col=0, row=0)
            # Override spawn position to boss location
            sprite.center_x = self._boss.center_x + random.uniform(
                -self._boss.width / 4, self._boss.width / 4
            )
            sprite.center_y = self._boss.center_y
            divers.append(sprite)
        return divers
```

**Note on diver loop count and silent vanish:** The existing
`DivingShip` state machine has DIVING → BOMBING → RETURNING → DONE.
Add a `loop_count` parameter to `DivingShip.__init__()`. On reaching
DONE, instead of signalling completion, if `loops_remaining > 0`
restart the dive from the boss position. When `loops_remaining == 0`,
set a `vanish_silently` flag that BossDiveController checks —
do not award points, do not spawn explosion.

If modifying `DivingShip` is too invasive, an alternative is to
override `consume_pending_hits()` in `BossDiveController` to always
return an empty list, effectively silencing all diver kills. Claude Code
should choose the least invasive approach after reviewing DivingShip.

---

## BossPowerUpManager

Subclass `SAPowerUpManager` to restrict available power-up types:

```python
# In boss_level.py or src/powerups/boss_manager.py

from src.powerups.sa_manager import SAPowerUpManager
from src.powerups.sa_spawner import SAPowerUpSpawner

class BossPowerUpSpawner(SAPowerUpSpawner):
    """Spawner restricted to shield, big_gun, spread_shot only."""

    def _build_weight_table(self) -> dict[str, float]:
        cfg = self._config
        # Only combat power-ups — no health, no free_move, no rapid_fire
        # Use boss-specific weights from BossConfig
        boss_cfg = getattr(cfg, '_boss_cfg', None)
        if boss_cfg is not None:
            return {
                "shield":      boss_cfg.boss_pu_weight_shield,
                "big_gun":     boss_cfg.boss_pu_weight_big_gun,
                "spread_shot": boss_cfg.boss_pu_weight_spread_shot,
            }
        # Fallback if boss_cfg not attached
        return {
            "shield":      8.0,
            "big_gun":     10.0,
            "spread_shot": 10.0,
        }


class BossPowerUpManager(SAPowerUpManager):
    """Power-up manager for boss levels.

    Restricts available types. Power-ups apply to the BOSS sprite,
    not the player ship. The player still gets power-ups from the
    standard spawner — boss has its own separate manager.
    """

    def create_spawner(self):
        spawner = BossPowerUpSpawner(self._config)
        spawner._boss_cfg = getattr(self._config, '_boss_cfg', None)
        return spawner
```

**Important design note:** The boss level has TWO power-up managers:

1. **Player power-up manager** — standard `SAPowerUpManager`, same as
   any other level. Power-ups fall from the top, player collects them.
   Uses the full SA weight table (all types available).

2. **Boss power-up manager** — `BossPowerUpManager`. Power-ups also
   fall from the top but the boss collects them (collision checked
   against boss sprite). Restricted to shield, big_gun, spread_shot.

Both managers are active simultaneously. Both call `update()` each
frame with their respective ship reference (`player_ship` vs
`boss_sprite`).

---

## BossLevel

```python
# src/levels/boss_level.py
from __future__ import annotations

import random
from typing import Any, Optional
import arcade
from agf.events import GameEvent
from agf.levels.base_level import BaseLevel
from src.boss_config import BossConfig
from src.sprites.boss_sprite import BossSprite
from src.powerups.sa_manager import SAPowerUpManager


class BossLevel(BaseLevel):
    """Boss encounter level.

    One large boss sprite moves side to side, descending each bounce.
    Boss fires bullets randomly across its width. Boss receives power-ups
    (shield, big gun, spread shot). Boss spawns periodic diving enemies.
    Player also receives full power-up drops independently.
    Boss death triggers a 2-3 second animated sequence before level complete.
    """

    def __init__(
        self,
        boss_config: BossConfig,
        diving_cfg: Any,
        window_width: int,
        window_height: int,
        player_powerup_manager: Optional[SAPowerUpManager] = None,
        debug: bool = False,
        sprite_scale: float = 1.0,
        hp_bar_duration: float = 1.0,
    ) -> None:
        self._boss_cfg = boss_config
        self._w = window_width
        self._h = window_height
        self._debug = debug
        self._scale = sprite_scale
        self._diving_cfg = diving_cfg
        self._hp_bar_duration = hp_bar_duration

        self._boss: Optional[BossSprite] = None
        self._boss_list = arcade.SpriteList()
        self._bullet_list = arcade.SpriteList()
        self._dive_ctrl: Optional[BossDiveController] = None
        self._player_powerup_manager = player_powerup_manager
        self._boss_powerup_manager: Optional[BossPowerUpManager] = None

        # Death sequence state
        self._dying: bool = False
        self._death_timer: float = 0.0
        self._death_explosions: list = []   # ExplosionSprite instances
        self._death_explosion_timer: float = 0.0
        self._death_explosion_interval: float = 0.0
        self._level_cleared: bool = False

        # Pending events
        self._pending_hits: list[tuple[float, float, int]] = []
        self._pending_non_lethal: list[tuple[float, float]] = []

        self._encounter: int = 1   # set in setup()

    @property
    def level_type(self) -> str:
        return "boss"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def setup(self, level_number: int) -> None:
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

        # Dive controller — pass a dummy EnemyGrid-like object
        self._dive_ctrl = BossDiveController(
            config=self._boss_cfg,
            diving_cfg=self._diving_cfg,
            boss_sprite=self._boss,
            window_width=self._w,
            window_height=self._h,
            debug=self._debug,
            sprite_scale=self._scale,
            hp_bar_duration=self._hp_bar_duration,
        )
        self._dive_ctrl.setup(level_number)

        # Boss power-up manager
        if hasattr(self._boss_cfg, 'boss_pu_weight_shield'):
            from src.powerups.boss_manager import BossPowerUpManager
            self._boss_powerup_manager = BossPowerUpManager(
                # Pass SA powerup config but override spawner weights
                # via boss_cfg attached to config
                self._player_powerup_manager._config
                if self._player_powerup_manager else None,
                self._w, self._h,
                sprite_scale=self._scale,
            )
            if self._boss_powerup_manager._config is not None:
                self._boss_powerup_manager._config._boss_cfg = self._boss_cfg
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
    ) -> list[GameEvent]:
        bullets = player_bullets or arcade.SpriteList()
        events: list[GameEvent] = []

        if self._level_cleared:
            return events

        # Death sequence — animate then signal complete
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

        # Move existing boss bullets
        for bullet in list(self._bullet_list):
            bullet.update(delta_time)

        # Boss bullet vs player ship collision
        if player_ship is not None and not player_ship.is_invincible():
            hits = arcade.check_for_collision_with_list(
                player_ship, self._bullet_list
            )
            for hit in hits:
                hit.remove_from_sprite_lists()
                killed = player_ship.take_damage(
                    self._boss_cfg.boss_bullet_damage
                )
                if killed:
                    events.append(GameEvent.PLAYER_KILLED)
                else:
                    self._pending_non_lethal.append(
                        (player_ship.center_x, player_ship.center_y)
                    )

        # Boss vs player ship collision (direct contact)
        if player_ship is not None and not player_ship.is_invincible():
            if arcade.check_for_collision(player_ship, self._boss):
                events.append(GameEvent.PLAYER_KILLED)

        # Player bullets vs boss
        for bullet in list(bullets):
            if not bullet.sprite_lists:
                continue
            if arcade.check_for_collision(bullet, self._boss):
                bullet.remove_from_sprite_lists()
                damage = getattr(bullet, 'damage', 1)
                # Respect boss shield
                absorbed = self._apply_damage_to_boss(damage)
                if not absorbed:
                    killed = self._boss.take_damage(damage)
                    if killed:
                        self._boss.record_hit(lethal=True)
                        self._start_death_sequence()
                        events.append(GameEvent.ENEMY_DESTROYED)
                        return events
                    else:
                        self._boss.record_hit(lethal=False)

        # Dive controller
        if self._dive_ctrl is not None:
            self._dive_ctrl.update(
                delta_time, None, player_ship, bullets
            )

        # Boss reaches bottom — player killed
        from src.ship_config import ShipConfig
        ship_zone_top = self._h * (
            getattr(player_ship, '_zone_top', self._h * 0.2)
            if player_ship else self._h * 0.2
        )
        if self._boss.reaches_bottom(ship_zone_top):
            events.append(GameEvent.PLAYER_KILLED)

        # Boss power-ups
        if self._boss_powerup_manager is not None:
            collected = self._boss_powerup_manager.update(
                delta_time, self._boss, {}, [self._boss.center_x]
            )
            for _ in collected:
                events.append(GameEvent.POWERUP_COLLECTED)

        # Player power-ups
        if self._player_powerup_manager is not None:
            collected = self._player_powerup_manager.update(
                delta_time, player_ship,
                self._effect_context(),
                [self._boss.center_x],  # spawn under boss
            )
            for _ in collected:
                events.append(GameEvent.POWERUP_COLLECTED)

        return events

    def _apply_damage_to_boss(self, amount: int) -> bool:
        """Check boss shield. Returns True if hit was absorbed."""
        if not self._boss or not self._boss.shield_active:
            return False
        overlay = (self._boss_powerup_manager.get_active_overlay()
                   if self._boss_powerup_manager else None)
        if overlay is None:
            return False
        depleted = overlay.on_hit_absorbed()
        if depleted:
            self._boss_powerup_manager.remove_effect(
                overlay, self._boss, {}
            )
        return True

    def _start_death_sequence(self) -> None:
        self._dying = True
        self._death_timer = 0.0
        cfg = self._boss_cfg
        self._death_explosion_interval = (
            cfg.boss_death_duration / cfg.boss_death_explosion_count
        )
        self._death_explosion_timer = 0.0
        if self._boss:
            self._boss_list.clear()  # hide boss sprite immediately

    def _update_death_sequence(self,
                                delta_time: float) -> list[GameEvent]:
        from agf.sprites.explosion import ExplosionSprite
        from agf.sprites.particles import ParticleEmitter, ShockwaveSprite

        self._death_timer += delta_time
        self._death_explosion_timer += delta_time

        # Spawn periodic explosions at random positions around boss center
        if (self._boss is not None
                and self._death_explosion_timer
                >= self._death_explosion_interval):
            self._death_explosion_timer = 0.0
            import random
            x = self._boss.center_x + random.uniform(
                -self._boss.width / 2, self._boss.width / 2
            )
            y = self._boss.center_y + random.uniform(
                -self._boss.height / 2, self._boss.height / 2
            )
            exp = ExplosionSprite(x=x, y=y, frame_duration=0.05,
                                  scale=self._scale * 1.5)
            self._death_explosions.append(exp)

        # Update active explosions
        for exp in list(self._death_explosions):
            exp.update(delta_time)
            if exp.is_complete:
                self._death_explosions.remove(exp)

        if self._death_timer >= self._boss_cfg.boss_death_duration:
            self._level_cleared = True
            return [GameEvent.LEVEL_COMPLETE]

        return []

    def draw(self) -> None:
        # Diving ships BELOW boss in z-order
        if self._dive_ctrl is not None:
            self._dive_ctrl.get_all_sprites().draw()
            self._dive_ctrl.get_all_bullets().draw()

        # Boss bullets
        self._bullet_list.draw()

        # Boss sprite (above divers)
        self._boss_list.draw()

        # Boss power-up pickups (above boss)
        if self._boss_powerup_manager is not None:
            self._boss_powerup_manager.draw()

        # Player power-up pickups
        if self._player_powerup_manager is not None:
            self._player_powerup_manager.draw()

        # Death explosions
        for exp in self._death_explosions:
            exp.draw()

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def is_cleared(self) -> bool:
        return self._level_cleared

    # ------------------------------------------------------------------
    # Bullet collision (player bullets)
    # ------------------------------------------------------------------

    def apply_player_bullet(self, bullet: Any) -> Any:
        """Check player bullet vs boss. Returns hit result or None.

        Unlike EnemyGrid which removes enemies, we just signal the hit
        and let update() handle damage — bullet collision is also
        checked in update() for correctness. This method exists to
        satisfy the BaseLevel interface but returns None to avoid
        double-processing. The bullet loop in RunLevelView should
        route through update() for boss levels.
        """
        return None

    # ------------------------------------------------------------------
    # Hit reporting
    # ------------------------------------------------------------------

    def consume_pending_hits(self) -> list[tuple[float, float, int]]:
        hits = list(self._pending_hits)
        if self._boss:
            hits += self._boss.consume_pending_hits()
        self._pending_hits.clear()
        return hits

    def consume_pending_non_lethal_hits(self) -> list[tuple[float, float]]:
        hits = list(self._pending_non_lethal)
        if self._boss:
            hits += self._boss.consume_pending_non_lethal_hits()
        self._pending_non_lethal.clear()
        return hits

    # ------------------------------------------------------------------
    # Sprite lists
    # ------------------------------------------------------------------

    def get_all_enemy_sprites(self) -> arcade.SpriteList:
        return self._boss_list

    def get_enemy_bullet_sprite_list(self) -> arcade.SpriteList:
        return self._bullet_list

    # ------------------------------------------------------------------
    # Power-ups
    # ------------------------------------------------------------------

    def get_powerup_manager(self) -> Optional[SAPowerUpManager]:
        return self._player_powerup_manager

    def get_enemy_x_positions(self) -> list[float]:
        return [self._boss.center_x] if self._boss else []

    # ------------------------------------------------------------------
    # 2P
    # ------------------------------------------------------------------

    def has_any_airborne(self) -> bool:
        return (self._dive_ctrl is not None
                and self._dive_ctrl.has_any_airborne())

    def block_new_launches(self) -> None:
        if self._dive_ctrl is not None:
            self._dive_ctrl.new_dive_launches_blocked = True

    # ------------------------------------------------------------------
    # Velocity
    # ------------------------------------------------------------------

    @property
    def velocity(self) -> tuple[float, float]:
        if self._boss:
            return (self._boss._vx, 0.0)
        return (0.0, 0.0)

    # ------------------------------------------------------------------
    # HP bar data — consumed by RunLevelView
    # ------------------------------------------------------------------

    def get_boss_hp_bar_data(self) -> Optional[tuple]:
        """Returns (center_x, center_y, width, hp, max_hp) or None.

        Width matches boss sprite width so HP bar spans the boss.
        RunLevelView calls this to draw the boss HP bar.
        """
        if self._boss is None or self._dying:
            return None
        return (
            self._boss.center_x,
            self._boss.center_y - self._boss.height / 2.0 - 8,
            self._boss.width,
            self._boss.hit_points,
            self._boss.max_hit_points,
        )

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def to_snapshot(self) -> dict:
        snap: dict = {"level_type": "boss"}
        if self._boss:
            snap["boss"] = {
                "center_x": self._boss.center_x,
                "center_y": self._boss.center_y,
                "vx": self._boss._vx,
                "hp": self._boss.hit_points,
                "encounter": self._encounter,
            }
        if self._dive_ctrl:
            snap["diving"] = self._dive_ctrl.to_snapshot()
        if self._player_powerup_manager:
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

        boss_cfg = config.boss if config else BossConfig()
        diving_cfg = config.diving if config else DivingConfig()
        debug = config.debug if config else False
        scale = config.sprite_scale if config else 1.0
        hp_dur = config.ui.hp_bar_duration if config else 1.0

        powerup_manager = None
        if config and getattr(config, "powerups", None):
            from src.powerups.sa_manager import SAPowerUpManager
            pu_snap = snapshot.get("powerups")
            if pu_snap:
                powerup_manager = SAPowerUpManager.from_snapshot(
                    pu_snap, config.powerups, window_width, window_height,
                    sprite_scale=scale, level_type="boss",
                )
            else:
                powerup_manager = SAPowerUpManager(
                    config.powerups, window_width, window_height,
                    sprite_scale=scale,
                )

        level = cls(boss_cfg, diving_cfg, window_width, window_height,
                    powerup_manager, debug, scale, hp_dur)

        # Restore boss state
        boss_snap = snapshot.get("boss", {})
        encounter = boss_snap.get("encounter", 1)
        level._encounter = encounter
        level._boss = BossSprite(
            boss_cfg, encounter, window_width, window_height, scale
        )
        level._boss.center_x = boss_snap.get("center_x",
                                               window_width / 2)
        level._boss.center_y = boss_snap.get("center_y",
                                               window_height * 0.8)
        level._boss._vx = boss_snap.get("vx", boss_cfg.boss_speed_base)
        level._boss.hit_points = boss_snap.get("hp",
                                                level._boss.max_hit_points)
        level._boss_list = arcade.SpriteList()
        level._boss_list.append(level._boss)

        return level

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _effect_context(self) -> dict:
        return {
            "window_width": self._w,
            "window_height": self._h,
            "sprite_scale": self._scale,
        }
```

---

## LevelFactory changes

### _get_level_type()

```python
def _get_level_type(level_number: int) -> str:
    is_boss = level_number % 5 == 0
    is_meteor = level_number % 3 == 0
    if is_boss:
        return "boss"
    if is_meteor:
        return "meteor"
    return "standard"
```

### Add "boss" case to _create_fresh()

```python
case "boss":
    from src.boss_config import BossConfig
    from src.diving_config import DivingConfig
    from src.levels.boss_level import BossLevel

    boss_cfg = config.boss if config else BossConfig()
    diving_cfg = config.diving if config else DivingConfig()
    debug = config.debug if config else False
    scale = config.sprite_scale if config else 1.0
    hp_dur = config.ui.hp_bar_duration if config else 1.0

    powerup_manager = None
    if config is not None and getattr(config, "powerups", None) is not None:
        from src.powerups.sa_manager import SAPowerUpManager
        powerup_manager = SAPowerUpManager(
            config.powerups, window_width, window_height,
            sprite_scale=scale,
        )

    level = BossLevel(
        boss_cfg, diving_cfg, window_width, window_height,
        powerup_manager, debug, scale, hp_dur,
    )
    level.setup(level_number)
    return level
```

### Add "boss" case to _restore_from_snapshot()

```python
case "boss":
    from src.levels.boss_level import BossLevel
    return BossLevel.from_snapshot(
        snapshot, config, window_width, window_height
    )
```

---

## RunLevelView changes

### Boss HP bar rendering

`BossLevel.get_boss_hp_bar_data()` returns HP bar parameters. Call
this in `_draw_enemy_hp_bars()` or add a dedicated `_draw_boss_hp_bar()`
method:

```python
def _draw_boss_hp_bar(self) -> None:
    if self._level is None:
        return
    data = getattr(self._level, 'get_boss_hp_bar_data', lambda: None)()
    if data is None:
        return
    cx, y, bar_width, hp, max_hp = data
    pct = hp / max_hp if max_hp > 0 else 0.0
    filled = bar_width * pct
    # Background
    arcade.draw_lrbt_rectangle_filled(
        cx - bar_width / 2, cx + bar_width / 2,
        y - 4, y + 4,
        (80, 0, 0, 200)
    )
    # Fill
    if filled > 0:
        arcade.draw_lrbt_rectangle_filled(
            cx - bar_width / 2,
            cx - bar_width / 2 + filled,
            y - 4, y + 4,
            (220, 40, 40, 255)
        )
```

Call `_draw_boss_hp_bar()` from `on_draw()` after `self._level.draw()`.

### Death sequence — large particle explosion

When `GameEvent.ENEMY_DESTROYED` arrives from a boss level, spawn the
large death effect before transitioning:

```python
# In RunLevelView event handling:
elif event == GameEvent.ENEMY_DESTROYED:
    # Check if this is a boss kill (large death effect)
    if hasattr(self._level, 'get_boss_hp_bar_data'):
        # Boss killed — spawn oversized particle explosion
        if self._boss is not None:
            self.spawn_destruction_effect(
                self._boss.center_x,
                self._boss.center_y,
                vx=0, vy=0,
                particle_count=self._level._boss_cfg.boss_death_particle_count,
                explosion_scale=3.0,
            )
    # Level cleared check happens inside BossLevel — do not
    # transition here, let BossLevel.update() return LEVEL_COMPLETE
    # after death animation completes
```

`spawn_destruction_effect()` should accept optional `particle_count`
and `explosion_scale` parameters if it doesn't already. Claude Code
should check the existing signature and add these if missing.

### Debug shortcuts

Add to existing debug block in `on_key_press()`:

```python
# Shift+B — skip to boss level (debug only)
if (self._debug and key == arcade.key.B
        and modifiers & arcade.key.MOD_SHIFT):
    from src.levels.level_factory import create_level
    self._level = create_level(
        5, cfg, self.window.width, self.window.height,
        force_level_type="boss"
    )
    # DEBUG
```

---

## game_config.toml — _get_level_type debug overrides

Consider adding a `force_level_type` override to `game_config.toml`
for testing boss levels without playing to level 5:

```toml
[game]
# ... existing fields ...
force_level_type = ""   # set to "boss" or "meteor" to force all levels
```

This lets QA testing jump straight to boss behaviour without cheat
code shortcuts in the view.

---

## Unit tests required

All tests without a display.

### BossConfig
- Default values load correctly
- boss_encounter_number(5) == 1, boss_encounter_number(10) == 2

### Level sequence (_get_level_type)
- Level 1, 2, 4: standard
- Level 3, 6, 9, 12: meteor
- Level 5, 10, 20, 25: boss
- Level 15: boss (divisible by both 5 and 3 — boss wins)
- Level 30: boss
- Level 18: meteor (first meteor after level 15 boss)
- Level 21: meteor

### BossSprite
- HP scales correctly: base + per_boss * (encounter - 1)
- Speed capped at boss_speed_max
- Bounces direction on hitting left margin
- Bounces direction on hitting right margin
- Descends by drop_distance on each bounce
- _generate_bullets() produces multiple bullets for spread
- _generate_bullets() produces single bullet for single shot
- take_damage() returns True when HP reaches 0
- consume_pending_bullets() clears the list

### BossLevel
- setup() creates boss sprite at correct starting position
- is_cleared() returns False before death sequence completes
- is_cleared() returns True after death duration elapses
- consume_pending_hits() returns boss hit data
- get_boss_hp_bar_data() returns None when boss is dead
- get_boss_hp_bar_data() bar_width matches boss.width
- has_any_airborne() delegates to BossDiveController

### LevelFactory
- create_level(5, ...) returns BossLevel
- create_level(10, ...) returns BossLevel
- create_level(15, ...) returns BossLevel (not MeteorLevel)
- create_level(3, ...) returns MeteorLevel
- create_level(18, ...) returns MeteorLevel
- create_level(1, ...) returns StandardLevel
- from_snapshot with level_type="boss" returns BossLevel
- force_level_type="boss" overrides standard

---

## Implementation checklist for Claude Code

Work in this order:

1. Add BossConfig to src/boss_config.py
2. Add [boss] section to game_config.toml
3. Wire BossConfig into GameConfig.load() and save()
4. Update _get_level_type() in level_factory.py — add level sequence tests
5. Implement BossSprite in src/sprites/boss_sprite.py
6. Implement BossDiveController (in boss_level.py or separate file)
   — check DivingShip for least-invasive loop_count approach first
7. Implement BossPowerUpSpawner and BossPowerUpManager
8. Implement BossLevel in src/levels/boss_level.py
9. Add "boss" cases to LevelFactory _create_fresh() and
   _restore_from_snapshot()
10. Add _draw_boss_hp_bar() to RunLevelView, call from on_draw()
11. Handle ENEMY_DESTROYED from boss in RunLevelView event loop
12. Add Shift+B debug shortcut
13. Run full test suite — all existing tests pass
14. Add new tests in tests/test_boss_level.py
15. Manual smoke test:
    - Force level type to "boss" via config
    - Confirm boss appears at correct size and position
    - Confirm side-to-side movement and descent
    - Confirm bullets fire from random x positions
    - Confirm spread burst fires multiple bullets
    - Confirm player bullets damage boss HP bar
    - Confirm boss shield absorbs player bullets
    - Confirm diving ships spawn from boss position
    - Confirm death sequence plays for correct duration
    - Confirm LEVEL_COMPLETE fires after death sequence
    - Confirm normal level 3 is still meteor
    - Confirm level 5 is boss, level 15 is boss, level 18 is meteor

## Implementation notes

- Any differences between this brief and source files use source files as ground truth.

- BossLevel.apply_player_bullet() returns None deliberately — player
  bullet vs boss collision is handled inside BossLevel.update() to
  avoid double-processing. RunLevelView's bullet loop calls both
  apply_player_bullet() and passes bullets into level.update(). For
  boss levels only update() should handle bullet collision. Claude Code
  should check RunLevelView's bullet loop and ensure boss bullets are
  not double-processed.

- The BossDiveController approach (subclassing DiveController) is
  preferred but Claude Code must review DivingShip.py first. If adding
  loop_count to DivingShip requires too many changes, the silent-vanish
  approach (override consume_pending_hits() to return []) is acceptable
  for initial implementation and can be refined later.

- Boss power-up manager attaches to boss sprite as the "ship". The
  SAPowerUpManager.update() takes any object with is_invincible() and
  take_damage() — BossSprite implements both. The power-up effects
  (ShieldEffect, BigGunEffect, SpreadShotEffect) modify attributes
  (shield_active, bullet_damage_multiplier, etc.) that BossSprite
  exposes. This should work without changes to the effect classes.

- The force_level_type parameter already exists in create_level() —
  no changes needed to support debug override via config. Just read
  the config value in states.py _handle_start_level() and pass it
  through.

- Boss HP bar uses arcade.draw_lrbt_rectangle_filled() not sprites —
  same approach as existing enemy HP bars in RunLevelView. Check
  _draw_enemy_hp_bars() for the exact existing pattern and match it.

- spawn_destruction_effect() in RunLevelView may not yet accept
  particle_count or explosion_scale parameters. Claude Code should
  check the existing signature. If not present, add optional parameters
  with defaults matching current behaviour so no existing calls break.
