# Feature: Power-Up System

## Overview
A power-up system where falling pickup sprites drop from enemy positions
during gameplay. Collecting a pickup applies an effect to the player ship
for a configurable duration (or instantly for health packs). Three initial
power-up types: Shield, Big Gun, and Health Pack. The system lives inside
BaseLevel (Option A) so each level type controls its own spawn policy.
Multiple effects stack simultaneously.

## Files to create

```
src/powerups/__init__.py
src/powerups/powerup_type.py        — PowerUpType enum
src/powerups/powerup_config.py      — PowerUpConfig dataclass
src/powerups/powerup_sprite.py      — falling pickup sprite
src/powerups/spawner.py             — PowerUpSpawner (when/where/what)
src/powerups/manager.py             — PowerUpManager (owns sprites + effects)
src/powerups/effects/__init__.py
src/powerups/effects/base_effect.py — abstract PowerUpEffect
src/powerups/effects/shield_effect.py
src/powerups/effects/big_gun_effect.py
src/powerups/effects/health_effect.py
src/sprites/shield_sprite.py        — visual shield drawn around ship
```

## Files to modify

```
src/levels/base_level.py            — add get_powerup_manager()
src/levels/standard_level.py       — own and tick PowerUpManager
src/game_config.py                  — add PowerUpConfig
src/sprites/player_ship.py         — add shield_active, fire_cooldown_multiplier,
                                      bullet_damage_multiplier
src/sprites/player_bullet.py       — respect damage multiplier
src/ui/hud.py                       — display active effect icons/timers
src/views/run_level.py             — draw shield sprite, pass manager draw call
```

## Files NOT modified

```
src/enemy_grid.py
src/dive_controller.py
src/levels/level_factory.py
src/state.py
```

---

## PowerUpType enum

```python
# src/powerups/powerup_type.py
from enum import Enum, auto

class PowerUpType(Enum):
    SHIELD     = auto()   # degrading shield, 3 hit states
    BIG_GUN    = auto()   # 2x bullet scale, double damage
    HEALTH     = auto()   # instant HP restore (configurable amount)
    # Future types added here
```

---

## PowerUpConfig dataclass

```python
# src/powerups/powerup_config.py
from dataclasses import dataclass, field

@dataclass
class PowerUpConfig:
    # Spawning
    spawn_interval_base: float = 20.0   # seconds between spawns at level 1
    spawn_interval_step: float = 0.5    # seconds reduction per level
    spawn_interval_min: float = 6.0     # floor interval
    spawn_interval_jitter: float = 2.0  # +/- random jitter per interval
    fall_speed: float = 80.0            # pixels/second downward

    # Per-type durations (seconds)
    shield_duration: float = 10.0
    big_gun_duration: float = 8.0
    # health has no duration — instant

    # Shield
    shield_hits: int = 3               # hits before shield breaks

    # Health pack
    health_restore_amount: int = 25    # HP restored on collect

    # Big gun
    big_gun_scale_factor: float = 2.0  # bullet scale multiplier
    big_gun_damage_multiplier: int = 2 # damage multiplier (1-shots 2HP enemies)

    # Weights for random type selection (higher = more likely)
    weight_shield: float = 10.0
    weight_big_gun: float = 10.0
    weight_health: float = 8.0
```

Add to `game_config.toml`:

```toml
[powerups]
spawn_interval_base = 20.0
spawn_interval_step = 0.5
spawn_interval_min = 6.0
spawn_interval_jitter = 2.0
fall_speed = 80.0
shield_duration = 10.0
big_gun_duration = 8.0
shield_hits = 3
health_restore_amount = 25
big_gun_scale_factor = 2.0
big_gun_damage_multiplier = 2
weight_shield = 10.0
weight_big_gun = 10.0
weight_health = 8.0
```

Add `PowerUpConfig` to `GameConfig` alongside existing config sections.

---

## Asset paths

### Power-up pickup sprites
Use Kenney assets. Recommended mappings (verify filenames in assets/):
```
SHIELD   → assets/images/PNG/Power-ups/shield_bronze.png  (or similar)
BIG_GUN  → assets/images/PNG/Power-ups/bolt_bronze.png
HEALTH   → assets/images/PNG/Power-ups/pill_red.png
```
If Kenney power-up sprites are not present, use colored circles generated
via arcade.make_circle_texture() as placeholders — do not block
implementation on assets. Note actual filenames in CLAUDE.md once confirmed.

### Shield overlay sprites
```
assets/images/PNG/Effects/shield1.png  — lowest power (1 hit remaining)
assets/images/PNG/Effects/shield2.png  — medium power (2 hits remaining)
assets/images/PNG/Effects/shield3.png  — full power  (3 hits remaining)
```
shield3 shown on collect, degrades to shield2 on first hit, shield1 on
second hit, removed on third hit.

All assets loaded via resource_path() helper.

---

## PowerUpSprite — falling pickup

```python
# src/powerups/powerup_sprite.py
class PowerUpSprite(arcade.Sprite):
    def __init__(self, x: float, y: float,
                 powerup_type: PowerUpType,
                 fall_speed: float = 80.0,
                 scale: float = 1.0,
                 texture: arcade.Texture | None = None):
        """
        texture: optional injection for tests (no display needed).
        If None, loads asset based on powerup_type via resource_path().
        """
        self.powerup_type = powerup_type
        self._fall_speed = fall_speed

    def update(self, delta_time: float) -> None:  # type: ignore[override]
        self.center_y -= self._fall_speed * delta_time
        if self.center_y < -self.height:
            self.remove_from_sprite_lists()
```

---

## PowerUpEffect — abstract base

```python
# src/powerups/effects/base_effect.py
from abc import ABC, abstractmethod
from src.powerups.powerup_type import PowerUpType

class PowerUpEffect(ABC):

    @abstractmethod
    def apply(self, player_ship, game_context: dict) -> None:
        """Called once when player collects the pickup.
        Modifies player_ship state. game_context provides access to
        players list, config, etc. if needed."""

    @abstractmethod
    def update(self, delta_time: float,
               player_ship) -> bool:
        """Called every frame while effect is active.
        Returns True while still active, False when expired.
        Not called for instant effects."""

    @abstractmethod
    def remove(self, player_ship, game_context: dict) -> None:
        """Called when effect expires. Restore original ship state."""

    @property
    @abstractmethod
    def powerup_type(self) -> PowerUpType:
        ...

    @property
    def is_instant(self) -> bool:
        """True for effects that apply and expire immediately.
        Instant effects: apply() is called, update() and remove()
        are never called. Default False."""
        return False

    @property
    def remaining_duration(self) -> float:
        """Seconds remaining. Used by HUD for timer display.
        Instant effects return 0.0."""
        return 0.0

    @property
    def hits_remaining(self) -> int | None:
        """For hit-based effects (shield): hits remaining before
        expiry. None for duration-based effects."""
        return None
```

---

## ShieldEffect

```python
# src/powerups/effects/shield_effect.py
class ShieldEffect(PowerUpEffect):
    """Degrading shield: 3 hits → 2 → 1 → gone.

    Integrates with PlayerShip by setting shield_active = True and
    intercepting damage via take_damage_shielded(). Shield handles
    the hit count internally — PlayerShip.take_damage() is NOT called
    while shield is active.
    """

    def __init__(self, config: PowerUpConfig):
        self._max_hits = config.shield_hits   # default 3
        self._hits_remaining = config.shield_hits
        self._duration = config.shield_duration  # fallback timer
        self._elapsed = 0.0

    @property
    def powerup_type(self) -> PowerUpType:
        return PowerUpType.SHIELD

    @property
    def hits_remaining(self) -> int:
        return self._hits_remaining

    @property
    def remaining_duration(self) -> float:
        return max(0.0, self._duration - self._elapsed)

    def apply(self, player_ship, game_context: dict) -> None:
        player_ship.shield_active = True
        player_ship.shield_hits_remaining = self._hits_remaining

    def on_hit(self) -> bool:
        """Called by ShieldSprite or RunLevelView when a hit is absorbed.
        Returns True if shield is now broken (hits_remaining == 0)."""
        self._hits_remaining -= 1
        return self._hits_remaining <= 0

    def update(self, delta_time: float, player_ship) -> bool:
        self._elapsed += delta_time
        # Update ship's shield hit count to match (for ShieldSprite draw state)
        player_ship.shield_hits_remaining = self._hits_remaining
        # Duration is a safety fallback — shield primarily expires on hits
        if self._elapsed >= self._duration:
            return False
        return self._hits_remaining > 0

    def remove(self, player_ship, game_context: dict) -> None:
        player_ship.shield_active = False
        player_ship.shield_hits_remaining = 0
```

### Shield hit interception in RunLevelView

When `player_ship.shield_active is True` and a collision would normally
call `player_ship.take_damage()`, instead call the shield effect's
`on_hit()` method. If `on_hit()` returns True (shield broken), call
`remove()` immediately. PlayerShip.take_damage() is NOT called while
shield is active — the hit is fully absorbed.

This logic lives in the damage handling section of `run_level.py` where
enemy bullets and grid collisions currently call `take_damage()`. A helper
method `_apply_damage_to_ship(amount)` should be extracted to centralise
this logic:

```python
def _apply_damage_to_ship(self, amount: int) -> bool:
    """Apply damage to ship, respecting active shield.
    Returns True if ship HP reached zero (player killed)."""
    manager = self._level.get_powerup_manager() if self._level else None
    shield = manager.get_active_shield() if manager else None

    if shield is not None:
        broken = shield.on_hit()
        if broken:
            manager.remove_effect(shield)
        return False  # shield absorbed the hit — ship HP unchanged

    return self._ship.take_damage(amount)
```

---

## BigGunEffect

```python
# src/powerups/effects/big_gun_effect.py
class BigGunEffect(PowerUpEffect):
    """2x bullet scale and double damage for duration."""

    def __init__(self, config: PowerUpConfig):
        self._duration = config.big_gun_duration
        self._scale_factor = config.big_gun_scale_factor
        self._damage_mult = config.big_gun_damage_multiplier
        self._elapsed = 0.0

    @property
    def powerup_type(self) -> PowerUpType:
        return PowerUpType.BIG_GUN

    @property
    def remaining_duration(self) -> float:
        return max(0.0, self._duration - self._elapsed)

    def apply(self, player_ship, game_context: dict) -> None:
        player_ship.bullet_scale_multiplier = self._scale_factor
        player_ship.bullet_damage_multiplier = self._damage_mult

    def update(self, delta_time: float, player_ship) -> bool:
        self._elapsed += delta_time
        return self._elapsed < self._duration

    def remove(self, player_ship, game_context: dict) -> None:
        player_ship.bullet_scale_multiplier = 1.0
        player_ship.bullet_damage_multiplier = 1
```

### PlayerShip changes for BigGun

Add these attributes to `PlayerShip.__init__()`:

```python
self.shield_active: bool = False
self.shield_hits_remaining: int = 0
self.bullet_scale_multiplier: float = 1.0
self.bullet_damage_multiplier: int = 1
```

Update `try_fire()` to pass multipliers to PlayerBullet:

```python
return PlayerBullet(
    x=self.center_x,
    y=self.center_y + self.height / 2.0,
    speed=self._config.bullet_speed,
    window_width=self._window_width,
    window_height=self._window_height,
    angle_deg=self._tilt_angle,
    player_num=self._player_num,
    scale=self._sprite_scale * self.bullet_scale_multiplier,
    damage=self._config.player_bullet_damage * self.bullet_damage_multiplier,
)
```

`PlayerBullet` already accepts `scale` and `damage` parameters — no
changes needed there if damage is already passed through. Confirm
`player_bullet_damage` exists on `ShipConfig`; add if missing
(default: 1).

---

## HealthEffect

```python
# src/powerups/effects/health_effect.py
class HealthEffect(PowerUpEffect):
    """Instant HP restore. Capped at max_hit_points."""

    def __init__(self, config: PowerUpConfig):
        self._amount = config.health_restore_amount

    @property
    def powerup_type(self) -> PowerUpType:
        return PowerUpType.HEALTH

    @property
    def is_instant(self) -> bool:
        return True

    def apply(self, player_ship, game_context: dict) -> None:
        player_ship.hit_points = min(
            player_ship.hit_points + self._amount,
            player_ship.max_hit_points
        )

    def update(self, delta_time: float, player_ship) -> bool:
        return False  # never called for instant effects

    def remove(self, player_ship, game_context: dict) -> None:
        pass  # never called for instant effects
```

---

## ShieldSprite — visual overlay

```python
# src/sprites/shield_sprite.py
_SHIELD_TEXTURES: dict[int, str] = {
    3: "assets/images/PNG/Effects/shield3.png",
    2: "assets/images/PNG/Effects/shield2.png",
    1: "assets/images/PNG/Effects/shield1.png",
}

class ShieldSprite(arcade.Sprite):
    """Visual shield drawn centered on the player ship.

    Tracks ship position every frame. Texture changes based on
    hits_remaining from the active ShieldEffect.
    Not a physics object — collision detection is handled by
    RunLevelView, not this sprite.
    """

    def __init__(self, scale: float = 1.0,
                 textures: dict[int, arcade.Texture] | None = None):
        """
        textures: optional injection for tests.
        If None, loads from _SHIELD_TEXTURES via resource_path().
        """
        super().__init__()
        self._textures: dict[int, arcade.Texture] = textures or {
            hits: arcade.load_texture(resource_path(path))
            for hits, path in _SHIELD_TEXTURES.items()
        }
        self.scale = scale
        self.texture = self._textures[3]
        self._current_hits = 3

    def update_state(self, hits_remaining: int,
                     ship_x: float, ship_y: float) -> None:
        """Call every frame from RunLevelView.on_update() while
        shield is active. Updates position and texture."""
        self.center_x = ship_x
        self.center_y = ship_y
        if hits_remaining != self._current_hits:
            self._current_hits = hits_remaining
            if hits_remaining in self._textures:
                self.texture = self._textures[hits_remaining]

    def pulse_alpha(self, delta_time: float) -> None:
        """Optional: gentle alpha pulse to indicate shield is active.
        Call from RunLevelView.on_update() each frame."""
        # Simple sine pulse between 180 and 255
        import math, time
        self.alpha = int(180 + 37 * math.sin(time.time() * 4))
```

### Shield sprite lifecycle in RunLevelView

```python
# In RunLevelView._setup():
self._shield_sprite: ShieldSprite | None = None

# In RunLevelView.on_update(), after effect processing:
manager = self._level.get_powerup_manager() if self._level else None
shield_effect = manager.get_active_shield() if manager else None
if shield_effect is not None and self._ship is not None:
    if self._shield_sprite is None:
        self._shield_sprite = ShieldSprite(
            scale=cfg.sprite_scale if cfg else 1.0
        )
    self._shield_sprite.update_state(
        shield_effect.hits_remaining,
        self._ship.center_x,
        self._ship.center_y,
    )
    self._shield_sprite.pulse_alpha(delta_time)
else:
    self._shield_sprite = None  # shield gone, clear sprite

# In RunLevelView.on_draw(), after player ship, before HUD:
if self._shield_sprite is not None:
    self._shield_sprite.draw()
```

---

## PowerUpSpawner

```python
# src/powerups/spawner.py
import random
from src.powerups.powerup_type import PowerUpType
from src.powerups.powerup_config import PowerUpConfig

class PowerUpSpawner:
    """Decides when and what type of power-up to spawn.

    Has no knowledge of sprites or effects — returns a PowerUpType
    (or None) each frame. PowerUpManager creates the sprite.
    """

    def __init__(self, config: PowerUpConfig):
        self._config = config
        self._timer: float = 0.0
        self._interval: float = 0.0
        self._level_number: int = 1
        self._level_type: str = "standard"

    def setup(self, level_number: int, level_type: str) -> None:
        self._level_number = level_number
        self._level_type = level_type
        self._interval = self._compute_interval()
        self._timer = 0.0

    def update(self, delta_time: float) -> PowerUpType | None:
        """Returns PowerUpType to spawn this frame, or None."""
        self._timer += delta_time
        if self._timer < self._interval:
            return None
        self._timer = 0.0
        self._interval = self._compute_interval()
        return self._pick_type()

    def _compute_interval(self) -> float:
        cfg = self._config
        base = cfg.spawn_interval_base
        reduction = (self._level_number - 1) * cfg.spawn_interval_step
        interval = max(cfg.spawn_interval_min, base - reduction)
        if self._level_type == "boss":
            interval *= 0.5  # boss levels spawn twice as often
        jitter = random.uniform(-cfg.spawn_interval_jitter,
                                cfg.spawn_interval_jitter)
        return max(cfg.spawn_interval_min, interval + jitter)

    def _pick_type(self) -> PowerUpType:
        cfg = self._config
        weights = {
            PowerUpType.SHIELD:   cfg.weight_shield,
            PowerUpType.BIG_GUN:  cfg.weight_big_gun,
            PowerUpType.HEALTH:   cfg.weight_health,
        }
        types = list(weights.keys())
        probs = list(weights.values())
        return random.choices(types, weights=probs, k=1)[0]

    @property
    def current_interval(self) -> float:
        """Current computed spawn interval. Exposed for tests."""
        return self._interval
```

---

## PowerUpManager

```python
# src/powerups/manager.py
import random
import arcade
from src.powerups.powerup_type import PowerUpType
from src.powerups.powerup_config import PowerUpConfig
from src.powerups.powerup_sprite import PowerUpSprite
from src.powerups.spawner import PowerUpSpawner
from src.powerups.effects.base_effect import PowerUpEffect
from src.powerups.effects.shield_effect import ShieldEffect
from src.powerups.effects.big_gun_effect import BigGunEffect
from src.powerups.effects.health_effect import HealthEffect
from src.game_event import GameEvent


class PowerUpManager:
    """Owns falling pickup sprites and active effects.

    Lives on StandardLevel (and future level types). Level calls
    update() and draw() each frame. RunLevelView queries
    get_active_shield() for visual shield rendering.
    """

    def __init__(self, config: PowerUpConfig,
                 window_width: int, window_height: int,
                 sprite_scale: float = 1.0):
        self._config = config
        self._window_width = window_width
        self._window_height = window_height
        self._scale = sprite_scale
        self._spawner = PowerUpSpawner(config)
        self._sprites = arcade.SpriteList()
        self._active_effects: list[PowerUpEffect] = []

    def setup(self, level_number: int, level_type: str) -> None:
        self._spawner.setup(level_number, level_type)

    def update(self, delta_time: float,
               player_ship,
               game_context: dict,
               enemy_x_positions: list[float]) -> list[GameEvent]:
        """Tick spawner, move sprites, detect collection, tick effects.
        Returns GameEvents generated this frame."""
        events: list[GameEvent] = []

        # Tick spawner
        spawn_type = self._spawner.update(delta_time)
        if spawn_type is not None:
            x = self._pick_spawn_x(enemy_x_positions)
            sprite = PowerUpSprite(
                x=x,
                y=self._window_height - 10,
                powerup_type=spawn_type,
                fall_speed=self._config.fall_speed,
                scale=self._scale,
            )
            self._sprites.append(sprite)

        # Move falling sprites
        for sprite in list(self._sprites):
            sprite.update(delta_time)

        # Detect collection (skip if ship None or invincible)
        if player_ship is not None and not player_ship.is_invincible():
            hits = arcade.check_for_collision_with_list(
                player_ship, self._sprites
            )
            for hit in hits:
                hit.remove_from_sprite_lists()
                effect = self._create_effect(hit.powerup_type)
                effect.apply(player_ship, game_context)
                if not effect.is_instant:
                    self._active_effects.append(effect)
                events.append(GameEvent.POWERUP_COLLECTED)

        # Tick active effects
        expired: list[PowerUpEffect] = []
        for effect in self._active_effects:
            if not effect.update(delta_time, player_ship):
                expired.append(effect)
        for effect in expired:
            effect.remove(player_ship, game_context)
            self._active_effects.remove(effect)

        return events

    def draw(self) -> None:
        self._sprites.draw()
        # Shield sprite drawn by RunLevelView — not here

    def get_active_shield(self) -> ShieldEffect | None:
        """Returns active ShieldEffect if one exists, else None.
        Used by RunLevelView to drive ShieldSprite rendering and
        to intercept damage."""
        for effect in self._active_effects:
            if isinstance(effect, ShieldEffect):
                return effect
        return None

    def remove_effect(self, effect: PowerUpEffect,
                      player_ship=None,
                      game_context: dict | None = None) -> None:
        """Force-remove an effect (e.g. shield broken by hit).
        Calls effect.remove() if player_ship provided."""
        if effect in self._active_effects:
            if player_ship is not None:
                effect.remove(player_ship, game_context or {})
            self._active_effects.remove(effect)

    def get_active_effects(self) -> list[PowerUpEffect]:
        """Returns copy of active effects list. Used by HUD."""
        return list(self._active_effects)

    def clear_all(self) -> None:
        """Remove all sprites and cancel all effects. Called on
        level reset or player death if effects should not persist."""
        self._sprites.clear()
        self._active_effects.clear()

    def to_snapshot(self) -> dict:
        """Serialise spawner timer state for 2P switching.
        Active effects are NOT snapshotted — they expire on switch."""
        return {
            'spawner_timer': self._spawner._timer,
            'spawner_interval': self._spawner._interval,
        }

    @classmethod
    def from_snapshot(cls, snapshot: dict, config: PowerUpConfig,
                      window_width: int, window_height: int,
                      sprite_scale: float = 1.0,
                      level_number: int = 1,
                      level_type: str = "standard") -> 'PowerUpManager':
        manager = cls(config, window_width, window_height, sprite_scale)
        manager.setup(level_number, level_type)
        manager._spawner._timer = snapshot.get('spawner_timer', 0.0)
        manager._spawner._interval = snapshot.get(
            'spawner_interval',
            manager._spawner._interval
        )
        return manager

    def _create_effect(self, powerup_type: PowerUpType) -> PowerUpEffect:
        match powerup_type:
            case PowerUpType.SHIELD:
                return ShieldEffect(self._config)
            case PowerUpType.BIG_GUN:
                return BigGunEffect(self._config)
            case PowerUpType.HEALTH:
                return HealthEffect(self._config)
            case _:
                raise ValueError(f"No effect for {powerup_type!r}")

    def _pick_spawn_x(self, enemy_positions: list[float]) -> float:
        """Spawn beneath a random living enemy if any, else random x."""
        if enemy_positions:
            return random.choice(enemy_positions)
        margin = 40
        return random.uniform(margin, self._window_width - margin)
```

---

## Changes to BaseLevel

Add one abstract method and one concrete default:

```python
# src/levels/base_level.py

@abstractmethod
def get_powerup_manager(self) -> 'PowerUpManager | None':
    """Returns this level's PowerUpManager, or None if the level
    type has no power-ups. RunLevelView uses this for shield
    rendering and damage interception."""
    ...

def get_enemy_x_positions(self) -> list[float]:
    """Returns x positions of all living enemies.
    Used by PowerUpManager to pick spawn positions.
    Default returns empty list — levels with no grid enemies override."""
    return []
```

---

## Changes to StandardLevel

```python
# src/levels/standard_level.py

def __init__(self, grid: EnemyGrid, dive_ctrl: DiveController,
             powerup_manager: PowerUpManager | None = None):
    self._grid = grid
    self._dive = dive_ctrl
    self._powerup_manager = powerup_manager

def setup(self, level_number: int) -> None:
    self._grid.setup(level_number)
    self._dive.setup(level_number, self._grid)
    if self._powerup_manager is not None:
        self._powerup_manager.setup(level_number, self.level_type)

def update(self, delta_time: float, player_ship) -> list[GameEvent]:
    events: list[GameEvent] = []
    events += self._grid.update(delta_time, player_ship)
    events += self._dive.update(
        delta_time, self._grid, player_ship, arcade.SpriteList()
    )
    if self._powerup_manager is not None and player_ship is not None:
        enemy_xs = self.get_enemy_x_positions()
        events += self._powerup_manager.update(
            delta_time, player_ship, {}, enemy_xs
        )
    return events

def draw(self) -> None:
    self._grid.get_sprite_list().draw()
    self._grid.get_bullet_sprite_list().draw()
    self._dive.get_all_sprites().draw()
    self._dive.get_all_bullets().draw()
    if self._powerup_manager is not None:
        self._powerup_manager.draw()

def get_powerup_manager(self) -> PowerUpManager | None:
    return self._powerup_manager

def get_enemy_x_positions(self) -> list[float]:
    return [s.center_x for s in self._grid.get_sprite_list()]

def to_snapshot(self) -> dict:
    snapshot = self._grid.to_snapshot()
    snapshot["level_type"] = "standard"
    snapshot["diving"] = self._dive.to_snapshot()
    if self._powerup_manager is not None:
        snapshot["powerups"] = self._powerup_manager.to_snapshot()
    return snapshot

@classmethod
def from_snapshot(cls, snapshot: dict, config, window_width: int,
                  window_height: int) -> 'StandardLevel':
    # ... existing grid/dive restore unchanged ...

    powerup_manager = None
    if config is not None and hasattr(config, 'powerups'):
        from src.powerups.manager import PowerUpManager
        powerup_manager = PowerUpManager.from_snapshot(
            snapshot.get("powerups", {}),
            config.powerups,
            window_width, window_height,
            sprite_scale=config.sprite_scale,
            level_number=1,  # actual level stored in PlayerState
            level_type="standard",
        )
    return cls(grid, dive_ctrl, powerup_manager)
```

### LevelFactory — pass PowerUpManager into StandardLevel

```python
# In _create_fresh(), after creating grid and dive:
from src.powerups.manager import PowerUpManager

powerup_manager = None
if config is not None and hasattr(config, 'powerups'):
    powerup_manager = PowerUpManager(
        config.powerups, window_width, window_height,
        sprite_scale=scale
    )

level = StandardLevel(grid, dive, powerup_manager)
level.setup(level_number)
return level
```

---

## Changes to RunLevelView

### New instance variables in __init__()
```python
self._shield_sprite: ShieldSprite | None = None
```

### _apply_damage_to_ship() helper — new private method
```python
def _apply_damage_to_ship(self, amount: int) -> bool:
    """Apply damage respecting active shield.
    Returns True if ship HP reached zero."""
    if self._ship is None:
        return False
    manager = (self._level.get_powerup_manager()
               if self._level is not None else None)
    shield = manager.get_active_shield() if manager else None
    if shield is not None:
        broken = shield.on_hit()
        if broken:
            manager.remove_effect(shield, self._ship, {})
            self._shield_sprite = None
        return False  # hit absorbed
    return self._ship.take_damage(amount)
```

Replace all direct `self._ship.take_damage()` calls in on_update()
with `self._apply_damage_to_ship(amount)`.

### Shield sprite update in on_update()
After effect ticking, add:
```python
# Shield sprite tracking
manager = (self._level.get_powerup_manager()
           if self._level is not None else None)
shield = manager.get_active_shield() if manager else None
if shield is not None and self._ship is not None:
    if self._shield_sprite is None:
        cfg = self._manager.context.get("config")
        self._shield_sprite = ShieldSprite(
            scale=cfg.sprite_scale if cfg else 1.0
        )
    self._shield_sprite.update_state(
        shield.hits_remaining,
        self._ship.center_x,
        self._ship.center_y,
    )
    self._shield_sprite.pulse_alpha(delta_time)
else:
    self._shield_sprite = None
```

### on_draw() — add shield after player ship
```python
self._ship_list.draw()
if self._shield_sprite is not None:
    self._shield_sprite.draw()
```

### on_update() death sequence — clear effects
```python
# When _trigger_death() is called, clear active power-up effects:
manager = (self._level.get_powerup_manager()
           if self._level is not None else None)
if manager is not None:
    manager.clear_all()
self._shield_sprite = None
```

---

## HUD changes

Add an active effects row below the existing score/lives/level line.
Display icons or text labels for each active non-instant effect with
a countdown timer:

```
[ SHIELD ▓▓▒░ ]  [ BIG GUN 4.2s ]
```

Shield shows hit pips (filled = remaining, empty = lost).
Duration effects show seconds remaining.

```python
# In HUD.update(), add:
def update_powerup_effects(self,
                           effects: list[PowerUpEffect]) -> None:
    """Update power-up status display. Called from RunLevelView
    after manager.get_active_effects()."""
    ...
```

HUD implementation detail left to Claude Code — keep it simple for
now (text labels are fine, icons can be added later).

---

## GameEvent additions

Add to `src/game_event.py`:
```python
POWERUP_COLLECTED = auto()
```

---

## Unit tests required

All tests must run without a display.

### PowerUpSpawner
- setup() resets timer to 0
- Interval at level 1 equals spawn_interval_base (minus jitter range)
- Interval decreases with level number
- Interval floors at spawn_interval_min
- Boss level type halves the interval
- update() returns None before interval expires
- update() returns a PowerUpType when interval expires
- After spawning, timer resets and new interval computed

### PowerUpSprite
- Moves downward by fall_speed * delta_time each frame
- Removes itself when center_y < -height

### ShieldEffect
- apply() sets player_ship.shield_active = True
- on_hit() decrements hits_remaining
- on_hit() returns True when hits_remaining reaches 0
- update() returns False when hits_remaining == 0
- update() returns False when duration exceeded
- remove() sets player_ship.shield_active = False

### BigGunEffect
- apply() sets bullet_scale_multiplier and bullet_damage_multiplier
- update() returns False after duration
- remove() resets multipliers to 1.0 / 1

### HealthEffect
- is_instant returns True
- apply() adds health_restore_amount to hit_points
- apply() caps at max_hit_points (no overflow)
- apply() with full HP leaves HP unchanged

### PowerUpManager
- update() creates sprite when spawner returns a type
- Sprite spawns at enemy x position when enemies present
- Sprite spawns at random x when no enemies
- Collecting pickup calls effect.apply() on player_ship
- Instant effects not added to _active_effects
- Non-instant effects added to _active_effects
- Expired effects have remove() called and are removed from list
- clear_all() empties sprites and effects lists
- to_snapshot() captures timer and interval
- from_snapshot() restores timer and interval

### ShieldSprite
- update_state() changes texture when hits_remaining changes
- update_state() updates center_x and center_y to match ship position
- Accepts injected texture dict (no display needed in tests)

### _apply_damage_to_ship() (RunLevelView)
- Returns False and does not call take_damage() when shield active
- Calls shield.on_hit() when shield active
- Calls manager.remove_effect() when on_hit() returns True
- Calls take_damage() normally when no shield active
- Returns True when take_damage() returns True (ship dead)

---

## Implementation checklist for Claude Code

Work in this order:

1. Add PowerUpType, PowerUpConfig
2. Add powerups section to game_config.toml and wire into GameConfig
3. Add GameEvent.POWERUP_COLLECTED to game_event.py
4. Add shield_active, shield_hits_remaining, bullet_scale_multiplier,
   bullet_damage_multiplier to PlayerShip.__init__()
5. Update PlayerShip.try_fire() to use multipliers
6. Add player_bullet_damage to ShipConfig if missing (default 1)
7. Implement PowerUpSprite
8. Implement base_effect.py
9. Implement ShieldEffect, BigGunEffect, HealthEffect
10. Implement PowerUpSpawner
11. Implement PowerUpManager
12. Implement ShieldSprite
13. Update BaseLevel with get_powerup_manager() and get_enemy_x_positions()
14. Update StandardLevel — constructor, setup, update, draw, snapshot
15. Update LevelFactory — pass PowerUpManager into StandardLevel
16. Update RunLevelView — shield sprite, _apply_damage_to_ship(),
    damage call sites, on_draw() order
17. Update HUD — active effects display
18. Run full test suite — all existing tests pass
19. Add new tests in tests/test_powerups.py
20. Manual smoke: collect each power-up type, verify visual and effect,
    verify shield degrades correctly, verify big gun bullet is larger
    and kills armoured enemies in one hit, verify health caps at max

## Implementation notes

- PowerUpManager.update() receives player_ship=None during death
  sequence — guard all ship accesses. Do not tick effects or check
  collection when player_ship is None.
- Active effects are cleared on player death (clear_all() in
  _trigger_death()) — effects do not survive a life loss.
- Active effects are NOT snapshotted for 2P switching — only the
  spawner timer is preserved. The incoming player starts with no
  active effects regardless of what the outgoing player had.
- ShieldSprite is purely visual — it has no hitbox and is never added
  to a SpriteList for collision detection. Damage interception is
  handled by _apply_damage_to_ship() in RunLevelView.
- pulse_alpha() uses time.time() for a continuous sine wave — this is
  intentional and does not need to be delta_time based since it is
  purely cosmetic.
- If Kenney power-up pickup sprites are not available in assets, use
  arcade.make_circle_texture() as placeholders and document the
  placeholder in a comment. Do not hardcode missing asset paths.
- Confirm player_bullet_damage exists in ShipConfig before step 6.
  If missing, add to ShipConfig dataclass with default value of 1 and
  add to game_config.toml [ship] section.
