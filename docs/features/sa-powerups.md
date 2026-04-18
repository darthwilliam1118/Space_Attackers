# Feature: Power-Ups (Space Attackers Implementation)

## Overview
Implements the Space Attackers-specific power-up effects, spawner,
manager, and pickup sprites using the agf power-up infrastructure.
Depends on agf powerup infrastructure being implemented first
(see agf-powerups.md).

No changes to agf — all code here lives in Space Attackers src/.

## Prerequisites
- agf powerup infrastructure complete and importable
- Player ship has: shield_active, shield_hits_remaining,
  bullet_scale_multiplier, bullet_damage_multiplier attributes
- ShipConfig has player_bullet_damage field (default 1)
- PlayerShip.try_fire() uses bullet_damage_multiplier and
  bullet_scale_multiplier

## Files to create

```
src/powerups/__init__.py
src/powerups/sa_powerup_type.py     — SA PowerUpType enum
src/powerups/sa_powerup_config.py   — SA PowerUpConfig (extends base)
src/powerups/sa_spawner.py          — SA spawner with weight table
src/powerups/sa_manager.py          — SA manager with create_effect()
src/powerups/effects/__init__.py
src/powerups/effects/shield.py      — ShieldEffect(OverlayEffect)
src/powerups/effects/health.py      — HealthEffect(InstantEffect)
src/powerups/effects/free_move.py   — FreeMovementEffect(ConstraintEffect)
src/powerups/effects/triple_shot.py — TripleShotEffect(BehaviorEffect)
src/powerups/effects/spread_shot.py — SpreadShotEffect(BehaviorEffect)
src/sprites/shield_sprite.py        — ShieldSprite visual overlay
```

## Files to modify

```
src/sprites/player_ship.py          — add powerup-related attributes
src/ship_config.py                  — add player_bullet_damage if missing
src/levels/standard_level.py       — own SAPowerUpManager
src/levels/level_factory.py        — pass manager into StandardLevel
src/views/run_level.py             — firing override, damage interception,
                                      overlay draw, HUD effects
src/ui/hud.py                       — active effects display
src/game_config.py                  — add SAPowerUpConfig section
game_config.toml                    — add [powerups] section
```

---

## SAP owerUpType enum

```python
# src/powerups/sa_powerup_type.py
from enum import Enum

class SAP owerUpType(Enum):
    # Instant
    HEALTH       = "health"

    # Overlay
    SHIELD       = "shield"

    # Stat modifiers
    RAPID_FIRE   = "rapid_fire"
    BIG_GUN      = "big_gun"
    SPEED_BOOST  = "speed_boost"

    # Behavior replacements
    TRIPLE_SHOT  = "triple_shot"
    SPREAD_SHOT  = "spread_shot"
    # Future: GUIDED_MISSILE, LASER_BEAM

    # Constraint modifier
    FREE_MOVE    = "free_move"
```

---

## SAP owerUpConfig

```python
# src/powerups/sa_powerup_config.py
from dataclasses import dataclass
from agf.powerups.config import PowerUpConfigBase

@dataclass
class SAP owerUpConfig(PowerUpConfigBase):
    # Shield
    shield_duration: float = 10.0
    shield_hits: int = 3

    # Health
    health_restore_amount: int = 25

    # Stat modifier durations
    rapid_fire_duration: float = 8.0
    rapid_fire_multiplier: float = 0.35    # fire_cooldown * 0.35
    big_gun_duration: float = 8.0
    big_gun_damage_multiplier: float = 2.0
    big_gun_scale_multiplier: float = 2.0
    speed_boost_duration: float = 6.0
    speed_boost_multiplier: float = 1.5

    # Behavior effect durations
    triple_shot_duration: float = 10.0
    spread_shot_duration: float = 8.0
    spread_shot_angle: float = 20.0  # degrees between bullets

    # Constraint effect durations
    free_move_duration: float = 8.0

    # Spawn weights
    weight_health: float = 8.0
    weight_shield: float = 10.0
    weight_rapid_fire: float = 10.0
    weight_big_gun: float = 8.0
    weight_speed_boost: float = 6.0
    weight_triple_shot: float = 7.0
    weight_spread_shot: float = 6.0
    weight_free_move: float = 3.0
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
shield_hits = 3
health_restore_amount = 25
rapid_fire_duration = 8.0
rapid_fire_multiplier = 0.35
big_gun_duration = 8.0
big_gun_damage_multiplier = 2.0
big_gun_scale_multiplier = 2.0
speed_boost_duration = 6.0
speed_boost_multiplier = 1.5
triple_shot_duration = 10.0
spread_shot_duration = 8.0
spread_shot_angle = 20.0
free_move_duration = 8.0
weight_health = 8.0
weight_shield = 10.0
weight_rapid_fire = 10.0
weight_big_gun = 8.0
weight_speed_boost = 6.0
weight_triple_shot = 7.0
weight_spread_shot = 6.0
weight_free_move = 3.0
```

Add SAP owerUpConfig to GameConfig dataclass and load() / save() methods.

---

## PlayerShip additions

Add to `PlayerShip.__init__()`:

```python
# Power-up state attributes — all reset to defaults on respawn
self.shield_active: bool = False
self.shield_hits_remaining: int = 0
self.bullet_scale_multiplier: float = 1.0
self.bullet_damage_multiplier: int = 1
# rotation_locked and zone constraints already exist as zone_* attrs
# free_move effect will save/restore these directly
```

Update `try_fire()` to pass multipliers:

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

---

## Effect implementations

### ShieldEffect

```python
# src/powerups/effects/shield.py
from agf.powerups.effect_categories import OverlayEffect
import arcade

class ShieldEffect(OverlayEffect):
    """Degrading shield: 3 hits → 2 → 1 → gone.

    shield3.png shown on collect. Degrades texture each hit.
    Duration is a safety fallback — shield primarily expires on hits.
    """

    def __init__(self, config):
        super().__init__(duration=config.shield_duration)
        self._max_hits = config.shield_hits
        self._hits_remaining = config.shield_hits

    @property
    def effect_type(self) -> str:
        return "shield"

    @property
    def hits_remaining(self) -> int:
        return self._hits_remaining

    @property
    def display_label(self) -> str:
        return f"SHIELD {'▓' * self._hits_remaining}{'░' * (self._max_hits - self._hits_remaining)}"

    def create_overlay_sprite(self, scale: float) -> arcade.Sprite:
        from src.sprites.shield_sprite import ShieldSprite
        return ShieldSprite(scale=scale)

    def on_hit_absorbed(self) -> bool:
        self._hits_remaining -= 1
        return self._hits_remaining <= 0

    def update_overlay_sprite(self, ship_x: float,
                               ship_y: float) -> None:
        if self._overlay_sprite is not None:
            from src.sprites.shield_sprite import ShieldSprite
            assert isinstance(self._overlay_sprite, ShieldSprite)
            self._overlay_sprite.update_state(
                self._hits_remaining, ship_x, ship_y
            )

    def apply(self, ship, context: dict) -> None:
        super().apply(ship, context)
        ship.shield_active = True
        ship.shield_hits_remaining = self._hits_remaining

    def remove(self, ship, context: dict) -> None:
        super().remove(ship, context)
        ship.shield_active = False
        ship.shield_hits_remaining = 0
```

### HealthEffect

```python
# src/powerups/effects/health.py
from agf.powerups.effect_categories import InstantEffect

class HealthEffect(InstantEffect):
    """Instant HP restore, capped at max_hit_points."""

    def __init__(self, config):
        self._amount = config.health_restore_amount

    @property
    def effect_type(self) -> str:
        return "health"

    def apply(self, ship, context: dict) -> None:
        ship.hit_points = min(
            ship.hit_points + self._amount,
            ship.max_hit_points
        )
```

### Stat modifier effects — use StatModifierEffect directly

These require no subclassing — instantiate StatModifierEffect with
the right parameters in SAP owerUpManager.create_effect():

```python
# In SAP owerUpManager.create_effect():
case "rapid_fire":
    return StatModifierEffect(
        attribute="fire_cooldown",  # wait — see note below
        duration=cfg.rapid_fire_duration,
        multiplier=cfg.rapid_fire_multiplier,
        effect_type_name="rapid_fire",
        label="RAPID FIRE",
    )
case "big_gun":
    # Big gun is two simultaneous stat modifiers — damage AND scale.
    # Since StatModifierEffect handles one attribute, use a compound
    # approach: return a BigGunEffect that applies both.
    # See BigGunEffect below.
    ...
case "speed_boost":
    return StatModifierEffect(
        attribute="ship_speed",  # wait — see note below
        duration=cfg.speed_boost_duration,
        multiplier=cfg.speed_boost_multiplier,
        effect_type_name="speed_boost",
        label="SPEED BOOST",
    )
```

**Note on ship attribute names:** StatModifierEffect sets attributes
directly on the ship. Verify the exact attribute names in
`player_ship.py` before implementing:
- Fire cooldown: likely `_fire_cooldown_remaining` (private) or a
  config value. If it's a config value, StatModifierEffect can't reach
  it directly. In that case add a public `fire_cooldown_override`
  attribute to PlayerShip that try_fire() checks. Same for ship_speed.
- Simplest approach: add `effective_fire_cooldown` and
  `effective_ship_speed` public attributes to PlayerShip that default
  to config values and are checked at runtime. StatModifierEffect
  modifies these.

### BigGunEffect — two-attribute modifier

Since big gun changes both bullet scale AND damage:

```python
# src/powerups/effects/big_gun.py
from agf.powerups.effect_categories import PowerUpEffect

class BigGunEffect(PowerUpEffect):
    """2x bullet scale and double damage for duration."""

    def __init__(self, config):
        self._duration = config.big_gun_duration
        self._scale = config.big_gun_scale_multiplier
        self._damage = int(config.big_gun_damage_multiplier)
        self._elapsed = 0.0

    @property
    def effect_type(self) -> str:
        return "big_gun"

    @property
    def remaining_duration(self) -> float:
        return max(0.0, self._duration - self._elapsed)

    def apply(self, ship, context: dict) -> None:
        ship.bullet_scale_multiplier = self._scale
        ship.bullet_damage_multiplier = self._damage

    def update(self, delta_time: float, ship) -> bool:
        self._elapsed += delta_time
        return self._elapsed < self._duration

    def remove(self, ship, context: dict) -> None:
        ship.bullet_scale_multiplier = 1.0
        ship.bullet_damage_multiplier = 1
```

### TripleShotEffect

```python
# src/powerups/effects/triple_shot.py
from agf.powerups.effect_categories import BehaviorEffect
from src.sprites.player_bullet import PlayerBullet
from src.paths import resource_path

class TripleShotEffect(BehaviorEffect):
    """Fires three bullets: centre + two angled at +/- 15 degrees."""

    def __init__(self, config):
        super().__init__(duration=config.triple_shot_duration)

    @property
    def effect_type(self) -> str:
        return "triple_shot"

    def get_bullets(self, ship) -> list:
        # Respect ship's own fire cooldown
        if ship._fire_cooldown_remaining > 0:
            return []
        ship._fire_cooldown_remaining = ship._config.fire_cooldown
        bullets = []
        for angle_offset in (-15.0, 0.0, 15.0):
            bullets.append(PlayerBullet(
                x=ship.center_x,
                y=ship.center_y + ship.height / 2.0,
                speed=ship._config.bullet_speed,
                window_width=ship._window_width,
                window_height=ship._window_height,
                angle_deg=ship._tilt_angle + angle_offset,
                player_num=ship._player_num,
                scale=ship._sprite_scale * ship.bullet_scale_multiplier,
                damage=ship._config.player_bullet_damage
                       * ship.bullet_damage_multiplier,
            ))
        return bullets
```

### SpreadShotEffect

```python
# src/powerups/effects/spread_shot.py
from agf.powerups.effect_categories import BehaviorEffect
from src.sprites.player_bullet import PlayerBullet

class SpreadShotEffect(BehaviorEffect):
    """Fires 5 bullets in a wide spread pattern."""

    def __init__(self, config):
        super().__init__(duration=config.spread_shot_duration)
        self._spread_angle = config.spread_shot_angle

    @property
    def effect_type(self) -> str:
        return "spread_shot"

    def get_bullets(self, ship) -> list:
        if ship._fire_cooldown_remaining > 0:
            return []
        ship._fire_cooldown_remaining = ship._config.fire_cooldown
        angles = [-2, -1, 0, 1, 2]
        bullets = []
        for i in angles:
            bullets.append(PlayerBullet(
                x=ship.center_x,
                y=ship.center_y + ship.height / 2.0,
                speed=ship._config.bullet_speed,
                window_width=ship._window_width,
                window_height=ship._window_height,
                angle_deg=ship._tilt_angle + i * self._spread_angle,
                player_num=ship._player_num,
                scale=ship._sprite_scale * ship.bullet_scale_multiplier,
                damage=ship._config.player_bullet_damage
                       * ship.bullet_damage_multiplier,
            ))
        return bullets
```

### FreeMovementEffect

```python
# src/powerups/effects/free_move.py
from agf.powerups.effect_categories import ConstraintEffect

class FreeMovementEffect(ConstraintEffect):
    """Full window movement for duration."""

    def __init__(self, config):
        super().__init__(duration=config.free_move_duration)

    @property
    def effect_type(self) -> str:
        return "free_move"

    def apply_constraints(self, ship, window_width: int,
                          window_height: int) -> None:
        self._saved_constraints = {
            "zone_top": ship._zone_top,
            "zone_bottom": ship._zone_bottom,
            "zone_left": ship._zone_left,
            "zone_right": ship._zone_right,
        }
        ship._zone_top = float(window_height)
        ship._zone_bottom = 0.0
        ship._zone_left = 0.0
        ship._zone_right = float(window_width)

    def restore_constraints(self, ship) -> None:
        for attr, val in self._saved_constraints.items():
            setattr(ship, attr, val)
```

---

## ShieldSprite

```python
# src/sprites/shield_sprite.py
_SHIELD_TEXTURES: dict[int, str] = {
    3: "assets/images/PNG/Effects/shield3.png",
    2: "assets/images/PNG/Effects/shield2.png",
    1: "assets/images/PNG/Effects/shield1.png",
}

class ShieldSprite(arcade.Sprite):
    """Visual shield overlay drawn centered on player ship.
    Not a physics object — no collision detection on this sprite."""

    def __init__(self, scale: float = 1.0,
                 textures: dict | None = None):
        super().__init__()
        self._textures: dict[int, arcade.Texture] = textures or {
            hits: arcade.load_texture(resource_path(path))
            for hits, path in _SHIELD_TEXTURES.items()
        }
        self.scale = scale
        self.texture = self._textures[3]
        self._current_hits = 3
        self._pulse_elapsed = 0.0

    def update_state(self, hits_remaining: int,
                     ship_x: float, ship_y: float) -> None:
        self.center_x = ship_x
        self.center_y = ship_y
        if hits_remaining != self._current_hits:
            self._current_hits = hits_remaining
            if hits_remaining in self._textures:
                self.texture = self._textures[hits_remaining]

    def pulse(self, delta_time: float) -> None:
        """Gentle alpha pulse to indicate active shield."""
        import math
        self._pulse_elapsed += delta_time
        self.alpha = int(180 + 37 * math.sin(self._pulse_elapsed * 4))
```

---

## SAP owerUpSpawner

```python
# src/powerups/sa_spawner.py
from agf.powerups.spawner import PowerUpSpawner
from src.powerups.sa_powerup_config import SAP owerUpConfig

class SAP owerUpSpawner(PowerUpSpawner):

    def _build_weight_table(self) -> dict[str, float]:
        cfg: SAP owerUpConfig = self._config
        weights = {
            "health":      cfg.weight_health,
            "shield":      cfg.weight_shield,
            "rapid_fire":  cfg.weight_rapid_fire,
            "big_gun":     cfg.weight_big_gun,
            "speed_boost": cfg.weight_speed_boost,
            "triple_shot": cfg.weight_triple_shot,
            "spread_shot": cfg.weight_spread_shot,
            "free_move":   cfg.weight_free_move,
        }
        # Boss levels: increase high-impact effects
        if self._level_type == "boss":
            weights["triple_shot"] *= 2.0
            weights["shield"] *= 1.5
            weights["big_gun"] *= 1.5
        return weights
```

---

## SAP owerUpManager

```python
# src/powerups/sa_manager.py
from agf.powerups.manager import PowerUpManager
from agf.powerups.effect_categories import StatModifierEffect
from agf.powerups.powerup_sprite import PowerUpSprite
from src.powerups.sa_powerup_config import SAP owerUpConfig
from src.powerups.sa_spawner import SAP owerUpSpawner
from src.powerups.effects.shield import ShieldEffect
from src.powerups.effects.health import HealthEffect
from src.powerups.effects.big_gun import BigGunEffect
from src.powerups.effects.triple_shot import TripleShotEffect
from src.powerups.effects.spread_shot import SpreadShotEffect
from src.powerups.effects.free_move import FreeMovementEffect
from src.paths import resource_path
import arcade

# Asset paths per type — update once actual Kenney filenames confirmed
_PICKUP_ASSETS: dict[str, str] = {
    "health":      "assets/images/PNG/Power-ups/pill_red.png",
    "shield":      "assets/images/PNG/Power-ups/shield_bronze.png",
    "rapid_fire":  "assets/images/PNG/Power-ups/bolt_bronze.png",
    "big_gun":     "assets/images/PNG/Power-ups/bolt_gold.png",
    "speed_boost": "assets/images/PNG/Power-ups/star_bronze.png",
    "triple_shot": "assets/images/PNG/Power-ups/bolt_silver.png",
    "spread_shot": "assets/images/PNG/Power-ups/star_silver.png",
    "free_move":   "assets/images/PNG/Power-ups/star_gold.png",
}

# Fallback colors if asset not found
_FALLBACK_COLORS: dict[str, tuple] = {
    "health":      (255, 100, 100, 255),
    "shield":      (100, 100, 255, 255),
    "rapid_fire":  (255, 255, 100, 255),
    "big_gun":     (255, 165, 0, 255),
    "speed_boost": (100, 255, 100, 255),
    "triple_shot": (255, 100, 255, 255),
    "spread_shot": (200, 100, 255, 255),
    "free_move":   (100, 255, 255, 255),
}


class SAP owerUpManager(PowerUpManager):

    def create_spawner(self) -> SAP owerUpSpawner:
        return SAP owerUpSpawner(self._config)

    def create_sprite(self, effect_type: str, x: float,
                      y: float) -> PowerUpSprite:
        texture = self._load_texture(effect_type)
        return PowerUpSprite(
            x=x, y=y,
            effect_type=effect_type,
            fall_speed=self._config.fall_speed,
            scale=self._scale,
            texture=texture,
        )

    def _load_texture(self,
                      effect_type: str) -> arcade.Texture | None:
        """Load asset texture, fall back to colored circle if missing."""
        path = _PICKUP_ASSETS.get(effect_type)
        if path:
            try:
                return arcade.load_texture(resource_path(path))
            except Exception:
                pass
        # Fallback: colored circle
        color = _FALLBACK_COLORS.get(effect_type, (200, 200, 200, 255))
        return arcade.make_circle_texture(32, color)

    def create_effect(self, effect_type: str):
        cfg: SAP owerUpConfig = self._config
        match effect_type:
            case "health":
                return HealthEffect(cfg)
            case "shield":
                return ShieldEffect(cfg)
            case "rapid_fire":
                return StatModifierEffect(
                    attribute="_fire_cooldown_remaining",
                    duration=cfg.rapid_fire_duration,
                    multiplier=cfg.rapid_fire_multiplier,
                    effect_type_name="rapid_fire",
                    label="RAPID FIRE",
                )
            case "big_gun":
                return BigGunEffect(cfg)
            case "speed_boost":
                return StatModifierEffect(
                    attribute="_config.ship_speed",
                    duration=cfg.speed_boost_duration,
                    multiplier=cfg.speed_boost_multiplier,
                    effect_type_name="speed_boost",
                    label="SPEED BOOST",
                )
            case "triple_shot":
                return TripleShotEffect(cfg)
            case "spread_shot":
                return SpreadShotEffect(cfg)
            case "free_move":
                return FreeMovementEffect(cfg)
            case _:
                raise ValueError(
                    f"Unknown power-up type: {effect_type!r}"
                )
```

**Note:** The `rapid_fire` and `speed_boost` StatModifierEffects reference
private or nested attributes. Before implementing, verify the cleanest
approach in player_ship.py — it may be cleaner to add public
`effective_fire_cooldown` and `effective_ship_speed` properties that
PlayerShip's logic reads, which StatModifierEffect can then modify cleanly.
Claude Code should check player_ship.py and decide the right approach.

---

## Changes to StandardLevel

```python
# Constructor
def __init__(self, grid, dive_ctrl,
             powerup_manager: SAP owerUpManager | None = None):
    self._grid = grid
    self._dive = dive_ctrl
    self._powerup_manager = powerup_manager

def setup(self, level_number: int) -> None:
    self._grid.setup(level_number)
    self._dive.setup(level_number, self._grid)
    if self._powerup_manager is not None:
        self._powerup_manager.setup(level_number, self.level_type)

def update(self, delta_time: float, player_ship) -> list:
    events = []
    events += self._grid.update(delta_time, player_ship)
    events += self._dive.update(
        delta_time, self._grid, player_ship, arcade.SpriteList()
    )
    if self._powerup_manager is not None and player_ship is not None:
        collected = self._powerup_manager.update(
            delta_time, player_ship,
            {"window_width": ..., "window_height": ...,
             "sprite_scale": ...},
            self.get_enemy_x_positions()
        )
        for _ in collected:
            events.append(GameEvent.POWERUP_COLLECTED)
    return events

def draw(self) -> None:
    self._grid.get_sprite_list().draw()
    self._grid.get_bullet_sprite_list().draw()
    self._dive.get_all_sprites().draw()
    self._dive.get_all_bullets().draw()
    if self._powerup_manager is not None:
        self._powerup_manager.draw()

def get_powerup_manager(self):
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
```

Update `from_snapshot()` to restore SAP owerUpManager similarly to
how DiveController is restored.

## Changes to LevelFactory

```python
# In _create_fresh(), after creating grid and dive:
from src.powerups.sa_manager import SAP owerUpManager
from src.powerups.sa_powerup_config import SAP owerUpConfig

powerup_manager = None
if config is not None and hasattr(config, 'powerups'):
    powerup_manager = SAP owerUpManager(
        config.powerups, window_width, window_height,
        sprite_scale=scale
    )

level = StandardLevel(grid, dive, powerup_manager)
level.setup(level_number)
```

---

## Changes to RunLevelView

### New instance variable
```python
self._shield_sprite_ref: arcade.Sprite | None = None
```

### _fire() — check for active BehaviorEffect

```python
def _fire(self) -> None:
    if self._ship is None or self._dying:
        return
    manager = (self._level.get_powerup_manager()
               if self._level else None)
    behavior = manager.get_active_behavior() if manager else None

    if behavior is not None:
        bullets = behavior.get_bullets(self._ship)
        for b in bullets:
            self._player_bullets.append(b)
            if self._snd_player_shoot:
                arcade.play_sound(self._snd_player_shoot,
                                  volume=self._sfx_volume())
    else:
        bullet = self._ship.try_fire()
        if bullet is not None:
            self._player_bullets.append(bullet)
            if self._snd_player_shoot:
                arcade.play_sound(self._snd_player_shoot,
                                  volume=self._sfx_volume())
```

### _apply_damage_to_ship() — new helper

Add this method to RunLevelView. Replace ALL direct calls to
`self._ship.take_damage()` with `self._apply_damage_to_ship(amount)`:

```python
def _apply_damage_to_ship(self, amount: int) -> bool:
    """Apply damage respecting active overlay (shield).
    Returns True if ship HP reached zero (player killed)."""
    if self._ship is None:
        return False
    manager = (self._level.get_powerup_manager()
               if self._level else None)
    overlay = manager.get_active_overlay() if manager else None

    if overlay is not None:
        depleted = overlay.on_hit_absorbed()
        if depleted:
            manager.remove_effect(overlay, self._ship,
                                  self._make_effect_context())
            self._shield_sprite_ref = None
        return False  # hit absorbed — HP unchanged

    return self._ship.take_damage(amount)

def _make_effect_context(self) -> dict:
    """Build context dict for effect apply/remove calls."""
    cfg = self._manager.context.get("config")
    return {
        "window_width": self.window.width,
        "window_height": self.window.height,
        "sprite_scale": cfg.sprite_scale if cfg else 1.0,
    }
```

### Shield sprite update in on_update()

After the main update block, add:

```python
# Shield overlay tracking
manager = (self._level.get_powerup_manager()
           if self._level else None)
overlay = manager.get_active_overlay() if manager else None
if overlay is not None:
    self._shield_sprite_ref = overlay.get_overlay_sprite()
    if self._shield_sprite_ref is not None:
        from src.sprites.shield_sprite import ShieldSprite
        if isinstance(self._shield_sprite_ref, ShieldSprite):
            self._shield_sprite_ref.pulse(delta_time)
else:
    self._shield_sprite_ref = None
```

### on_draw() — draw shield after ship

```python
self._ship_list.draw()
if self._shield_sprite_ref is not None:
    self._shield_sprite_ref.draw()
```

### _trigger_death() — clear powerups

```python
def _trigger_death(self) -> None:
    # ... existing death setup ...
    manager = (self._level.get_powerup_manager()
               if self._level else None)
    if manager is not None:
        manager.clear_all(self._ship, self._make_effect_context())
    self._shield_sprite_ref = None
```

---

## HUD changes

Add active power-up effects row below the existing score/lives line.

For each active effect from `manager.get_active_effects()`:
- Show `effect.display_label`
- For duration effects: show `effect.remaining_duration` countdown
- For shield: the display_label already encodes hit pips

```
[ RAPID FIRE 6.2s ]  [ TRIPLE SHOT 8.0s ]  [ SHIELD ▓▓░ ]
```

Keep it simple — text labels are fine, polish later.

---

## GameEvent addition

Add to `src/game_event.py`:
```python
POWERUP_COLLECTED = auto()
```

---

## Unit tests

All tests must run without a display.

### SA effects
- ShieldEffect.apply() sets ship.shield_active = True
- ShieldEffect.on_hit_absorbed() decrements hits
- ShieldEffect.on_hit_absorbed() returns True at 0 hits
- ShieldEffect.remove() clears shield_active
- HealthEffect.apply() adds restore amount to hit_points
- HealthEffect.apply() caps at max_hit_points
- BigGunEffect.apply() sets both scale and damage multipliers
- BigGunEffect.remove() resets both to defaults
- TripleShotEffect.get_bullets() returns 3 bullets
- TripleShotEffect.get_bullets() returns [] during cooldown
- SpreadShotEffect.get_bullets() returns 5 bullets
- SpreadShotEffect angles match spread_shot_angle config
- FreeMovementEffect saves and restores zone constraints

### SAP owerUpManager
- create_effect() returns correct type for each effect_type string
- create_effect() raises ValueError for unknown type
- _load_texture() returns fallback circle when asset missing

### RunLevelView helpers
- _apply_damage_to_ship() returns False when overlay active
- _apply_damage_to_ship() calls overlay.on_hit_absorbed()
- _apply_damage_to_ship() calls manager.remove_effect() when depleted
- _apply_damage_to_ship() calls ship.take_damage() when no overlay
- _fire() calls behavior.get_bullets() when BehaviorEffect active
- _fire() calls ship.try_fire() when no BehaviorEffect

---

## Implementation checklist for Claude Code

Work in this order:

1. Add GameEvent.POWERUP_COLLECTED to game_event.py
2. Add powerup attributes to PlayerShip.__init__()
3. Update PlayerShip.try_fire() to use multipliers
4. Confirm player_bullet_damage exists in ShipConfig
5. Add SAP owerUpConfig, SAP owerUpType to src/powerups/
6. Add [powerups] section to game_config.toml
7. Wire SAP owerUpConfig into GameConfig.load() and save()
8. Implement ShieldSprite
9. Implement all effect classes
10. Implement SAP owerUpSpawner
11. Implement SAP owerUpManager
12. Update StandardLevel — constructor, setup, update, draw, snapshot
13. Update LevelFactory — pass manager into StandardLevel
14. Add _apply_damage_to_ship() to RunLevelView
15. Replace all take_damage() calls in RunLevelView with helper
16. Update _fire() in RunLevelView
17. Add shield sprite tracking to on_update() and on_draw()
18. Update _trigger_death() to clear powerups
19. Update HUD to show active effects
20. Run full test suite
21. Add new tests
22. Manual smoke: collect each type, verify visual and game effect,
    verify shield degrades, verify triple shot fires 3 bullets,
    verify free movement expands zone, verify health caps at max

## Implementation notes

- The rapid_fire StatModifierEffect modifying fire_cooldown is
  tricky because fire_cooldown is config-level not ship-level.
  Claude Code should check player_ship.py and decide the cleanest
  approach — adding an `effective_fire_cooldown` property or
  modifying the config reference. Do NOT modify the ShipConfig
  object itself as that would affect all ships.
- SpreadShotEffect and TripleShotEffect access ship private
  attributes (_fire_cooldown_remaining, _config, etc.). This is
  acceptable since they live in the same codebase — document with
  a comment. If it becomes a maintenance issue, add public accessors
  to PlayerShip.
- Pickup asset filenames in _PICKUP_ASSETS are guesses based on
  Kenney naming conventions. Claude Code must check
  assets/images/PNG/ for actual Power-ups folder contents and
  update paths accordingly. Use fallback textures if folder
  doesn't exist yet.
- The context dict passed to effect apply/remove must include
  window_width, window_height, and sprite_scale at minimum.
  Add other fields if effects need them.
- clear_all() on manager during player death removes all active
  effects including free movement — this means dying while in
  free movement mode correctly restores the ship zone before
  respawn spawn safety runs.
