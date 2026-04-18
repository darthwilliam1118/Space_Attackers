# AGF Feature: Power-Up Infrastructure

## Overview
Generic power-up infrastructure for the arcade-game-framework package.
Defines effect categories, the spawner, manager, and pickup sprite.
Contains no game-specific logic — games implement concrete effects by
subclassing the effect category base classes defined here.

## Files to create in agf

```
src/agf/powerups/__init__.py
src/agf/powerups/effect_base.py       — PowerUpEffect abstract base
src/agf/powerups/effect_categories.py — StatModifier, Behavior,
                                         Constraint, Overlay, Instant
src/agf/powerups/powerup_sprite.py    — falling pickup sprite
src/agf/powerups/spawner.py           — PowerUpSpawner
src/agf/powerups/manager.py           — PowerUpManager
src/agf/powerups/config.py            — PowerUpConfigBase dataclass
```

---

## PowerUpEffect — abstract base

```python
# src/agf/powerups/effect_base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class PowerUpEffect(ABC):
    """Abstract base for all power-up effects.

    Subclass one of the effect category classes (StatModifierEffect,
    BehaviorEffect, ConstraintEffect, OverlayEffect, InstantEffect)
    rather than this class directly.
    """

    @abstractmethod
    def apply(self, ship: Any, context: dict) -> None:
        """Called once when player collects the pickup.
        Modifies ship state. context provides window size, config, etc."""

    @abstractmethod
    def update(self, delta_time: float, ship: Any) -> bool:
        """Called every frame while effect is active.
        Returns True while still active, False when expired.
        Never called for instant effects."""

    @abstractmethod
    def remove(self, ship: Any, context: dict) -> None:
        """Called when effect expires or is force-removed.
        Restores original ship state."""

    @property
    @abstractmethod
    def effect_type(self) -> str:
        """String identifier matching PowerUpType value.
        e.g. 'shield', 'rapid_fire', 'triple_shot'"""

    @property
    def is_instant(self) -> bool:
        """True for one-shot effects (health restore, extra life).
        Instant effects: apply() is called, update() and remove()
        are never called. Default False."""
        return False

    @property
    def remaining_duration(self) -> float:
        """Seconds remaining for HUD display.
        Override in duration-based effects. Default 0.0."""
        return 0.0

    @property
    def display_label(self) -> str:
        """Short label for HUD display. Default uses effect_type."""
        return self.effect_type.replace("_", " ").upper()
```

---

## Effect category base classes

```python
# src/agf/powerups/effect_categories.py
from __future__ import annotations
from abc import abstractmethod
from typing import Any
import arcade
from agf.powerups.effect_base import PowerUpEffect


# ------------------------------------------------------------------
# StatModifierEffect — fully generic, no subclassing needed
# ------------------------------------------------------------------

class StatModifierEffect(PowerUpEffect):
    """Multiplies or adds to a numeric ship attribute for a duration.

    Fully implemented — games use this directly via configuration,
    no subclassing required for simple stat changes.

    Examples:
        # Rapid fire: fire_cooldown * 0.4 for 8 seconds
        StatModifierEffect("fire_cooldown", duration=8.0, multiplier=0.4)

        # Speed boost: ship_speed * 1.5 for 6 seconds
        StatModifierEffect("ship_speed", duration=6.0, multiplier=1.5)

        # Damage boost: bullet_damage_multiplier * 2 for 8 seconds
        StatModifierEffect("bullet_damage_multiplier", duration=8.0,
                           multiplier=2.0)
    """

    def __init__(self, attribute: str, duration: float,
                 multiplier: float = 1.0, additive: float = 0.0,
                 effect_type_name: str = "stat_modifier",
                 label: str = ""):
        self._attribute = attribute
        self._duration = duration
        self._multiplier = multiplier
        self._additive = additive
        self._effect_type_name = effect_type_name
        self._label = label or effect_type_name.replace("_", " ").upper()
        self._elapsed = 0.0
        self._original: Any = None

    @property
    def effect_type(self) -> str:
        return self._effect_type_name

    @property
    def display_label(self) -> str:
        return self._label

    @property
    def remaining_duration(self) -> float:
        return max(0.0, self._duration - self._elapsed)

    def apply(self, ship: Any, context: dict) -> None:
        self._original = getattr(ship, self._attribute)
        new_value = self._original * self._multiplier + self._additive
        # Preserve the original type (int stays int)
        if isinstance(self._original, int):
            new_value = int(round(new_value))
        setattr(ship, self._attribute, new_value)

    def update(self, delta_time: float, ship: Any) -> bool:
        self._elapsed += delta_time
        return self._elapsed < self._duration

    def remove(self, ship: Any, context: dict) -> None:
        if self._original is not None:
            setattr(ship, self._attribute, self._original)


# ------------------------------------------------------------------
# BehaviorEffect — games implement get_bullets()
# ------------------------------------------------------------------

class BehaviorEffect(PowerUpEffect):
    """Replaces the ship's firing behavior for a duration.

    While active, RunLevelView calls get_bullets() instead of
    ship.try_fire(). Games subclass this to implement alternate
    firing modes: spread shot, triple shot, guided missiles,
    laser beam, etc.

    Only one BehaviorEffect can be active at a time.
    PowerUpManager enforces this — a new BehaviorEffect replaces
    any existing one.
    """

    def __init__(self, duration: float):
        self._duration = duration
        self._elapsed = 0.0

    @property
    @abstractmethod
    def effect_type(self) -> str: ...

    @property
    def remaining_duration(self) -> float:
        return max(0.0, self._duration - self._elapsed)

    @abstractmethod
    def get_bullets(self, ship: Any) -> list[Any]:
        """Return list of bullet sprites to fire this frame.
        Called by RunLevelView instead of ship.try_fire() while
        this effect is active. Return empty list if on cooldown."""

    def apply(self, ship: Any, context: dict) -> None:
        pass  # override if needed

    def update(self, delta_time: float, ship: Any) -> bool:
        self._elapsed += delta_time
        return self._elapsed < self._duration

    def remove(self, ship: Any, context: dict) -> None:
        pass  # override if cleanup needed


# ------------------------------------------------------------------
# ConstraintEffect — games implement apply/restore constraints
# ------------------------------------------------------------------

class ConstraintEffect(PowerUpEffect):
    """Modifies player ship movement constraints for a duration.

    Games subclass to implement free movement, full rotation,
    expanded movement zone, etc.

    Only one ConstraintEffect can be active at a time.
    """

    def __init__(self, duration: float):
        self._duration = duration
        self._elapsed = 0.0
        self._saved_constraints: dict = {}

    @property
    @abstractmethod
    def effect_type(self) -> str: ...

    @property
    def remaining_duration(self) -> float:
        return max(0.0, self._duration - self._elapsed)

    @abstractmethod
    def apply_constraints(self, ship: Any,
                          window_width: int,
                          window_height: int) -> None:
        """Override ship movement zone, rotation limits, etc.
        Save original values to self._saved_constraints for restore."""

    @abstractmethod
    def restore_constraints(self, ship: Any) -> None:
        """Restore original constraints from self._saved_constraints."""

    def apply(self, ship: Any, context: dict) -> None:
        w = context.get("window_width", 800)
        h = context.get("window_height", 600)
        self.apply_constraints(ship, w, h)

    def update(self, delta_time: float, ship: Any) -> bool:
        self._elapsed += delta_time
        return self._elapsed < self._duration

    def remove(self, ship: Any, context: dict) -> None:
        self.restore_constraints(ship)


# ------------------------------------------------------------------
# OverlayEffect — games implement visual overlay + hit absorption
# ------------------------------------------------------------------

class OverlayEffect(PowerUpEffect):
    """Effect with a persistent visual overlay on the ship and
    hit absorption logic.

    While active, RunLevelView intercepts damage via on_hit_absorbed()
    instead of calling ship.take_damage(). The overlay sprite is
    drawn centered on the ship each frame.

    Only one OverlayEffect can be active at a time.
    """

    def __init__(self, duration: float):
        self._duration = duration
        self._elapsed = 0.0
        self._overlay_sprite: arcade.Sprite | None = None

    @property
    @abstractmethod
    def effect_type(self) -> str: ...

    @property
    def remaining_duration(self) -> float:
        return max(0.0, self._duration - self._elapsed)

    @abstractmethod
    def create_overlay_sprite(self, scale: float) -> arcade.Sprite:
        """Return sprite to draw centered on ship each frame.
        Called once on apply(). Store in self._overlay_sprite."""

    @abstractmethod
    def on_hit_absorbed(self) -> bool:
        """Called when a hit is intercepted by this overlay.
        Returns True if the overlay is now depleted (should be
        removed). Returns False if overlay still has capacity."""

    @abstractmethod
    def update_overlay_sprite(self, ship_x: float,
                               ship_y: float) -> None:
        """Update overlay sprite position and visual state.
        Called every frame from RunLevelView while active."""

    def get_overlay_sprite(self) -> arcade.Sprite | None:
        """Returns the overlay sprite for RunLevelView to draw."""
        return self._overlay_sprite

    def apply(self, ship: Any, context: dict) -> None:
        scale = context.get("sprite_scale", 1.0)
        self._overlay_sprite = self.create_overlay_sprite(scale)

    def update(self, delta_time: float, ship: Any) -> bool:
        self._elapsed += delta_time
        if self._overlay_sprite is not None:
            self.update_overlay_sprite(ship.center_x, ship.center_y)
        return self._elapsed < self._duration

    def remove(self, ship: Any, context: dict) -> None:
        self._overlay_sprite = None


# ------------------------------------------------------------------
# InstantEffect — games implement apply() only
# ------------------------------------------------------------------

class InstantEffect(PowerUpEffect):
    """One-shot effect applied immediately on collection.

    apply() is called once. update() and remove() are never called.
    Games subclass to implement health restore, extra life, etc.
    """

    @property
    def is_instant(self) -> bool:
        return True

    @property
    @abstractmethod
    def effect_type(self) -> str: ...

    @abstractmethod
    def apply(self, ship: Any, context: dict) -> None:
        """Apply the instant effect. No state to restore."""

    def update(self, delta_time: float, ship: Any) -> bool:
        return False  # never called

    def remove(self, ship: Any, context: dict) -> None:
        pass  # never called
```

---

## PowerUpConfigBase

```python
# src/agf/powerups/config.py
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class PowerUpConfigBase:
    """Base config for the power-up system.

    Games subclass this and add their own effect-specific fields.
    All spawning and timing fields live here — effect parameters
    live in the game's subclass.
    """
    # Spawning timing
    spawn_interval_base: float = 20.0   # seconds between spawns at level 1
    spawn_interval_step: float = 0.5    # seconds reduction per level
    spawn_interval_min: float = 6.0     # floor interval regardless of level
    spawn_interval_jitter: float = 2.0  # +/- random added per interval

    # Pickup sprite
    fall_speed: float = 80.0            # pixels/second downward

    # Weight table — games override _build_weight_table() in spawner
    # to add game-specific types. Base weights are placeholders.
    # Games that define their own weight fields add them in their subclass.
```

---

## PowerUpSprite — falling pickup

```python
# src/agf/powerups/powerup_sprite.py
from __future__ import annotations
from typing import Optional
import arcade


class PowerUpSprite(arcade.Sprite):
    """Falling power-up pickup sprite.

    Games pass a pre-loaded texture so the sprite itself has
    no knowledge of asset paths. Removes itself when it scrolls
    off the bottom of the screen.
    """

    def __init__(self, x: float, y: float,
                 effect_type: str,
                 fall_speed: float = 80.0,
                 scale: float = 1.0,
                 texture: Optional[arcade.Texture] = None):
        if texture is not None:
            super().__init__(texture=texture)
        else:
            super().__init__()
        self.scale = scale
        self.effect_type = effect_type   # string matching PowerUpType
        self._fall_speed = fall_speed

    def update(self, delta_time: float) -> None:  # type: ignore[override]
        self.center_y -= self._fall_speed * delta_time
        if self.center_y < -self.height:
            self.remove_from_sprite_lists()
```

---

## PowerUpSpawner

```python
# src/agf/powerups/spawner.py
from __future__ import annotations
import random
from typing import Any
from agf.powerups.config import PowerUpConfigBase


class PowerUpSpawner:
    """Decides when to spawn a power-up and which type.

    Has no knowledge of sprites or effects — returns an effect_type
    string (or None) each frame. PowerUpManager creates the sprite.

    Games subclass and override _build_weight_table() to define
    which effect types are available and their spawn weights.
    The weight table can vary by level_type for level-specific drops
    (e.g. boss levels get exclusive power-up types).
    """

    def __init__(self, config: PowerUpConfigBase):
        self._config = config
        self._timer: float = 0.0
        self._interval: float = config.spawn_interval_base
        self._level_number: int = 1
        self._level_type: str = "standard"

    def setup(self, level_number: int, level_type: str) -> None:
        """Call at level start to configure scaling."""
        self._level_number = level_number
        self._level_type = level_type
        self._interval = self._compute_interval()
        self._timer = 0.0

    def update(self, delta_time: float) -> str | None:
        """Advance timer. Returns effect_type string to spawn, or None."""
        self._timer += delta_time
        if self._timer < self._interval:
            return None
        self._timer = 0.0
        self._interval = self._compute_interval()
        weights = self._build_weight_table()
        if not weights:
            return None
        types = list(weights.keys())
        probs = list(weights.values())
        return random.choices(types, weights=probs, k=1)[0]

    def _compute_interval(self) -> float:
        """Compute next spawn interval based on level number.
        Override to customise scaling behaviour."""
        cfg = self._config
        base = cfg.spawn_interval_base
        reduction = (self._level_number - 1) * cfg.spawn_interval_step
        interval = max(cfg.spawn_interval_min, base - reduction)
        jitter = random.uniform(
            -cfg.spawn_interval_jitter,
            cfg.spawn_interval_jitter
        )
        return max(cfg.spawn_interval_min, interval + jitter)

    def _build_weight_table(self) -> dict[str, float]:
        """Return {effect_type: weight} dict for random selection.

        Override in games to define available types and weights.
        Weights can vary by self._level_type for level-specific drops.
        Higher weight = more likely to spawn.

        Example override in SA:
            def _build_weight_table(self):
                weights = {
                    "shield": 10.0,
                    "rapid_fire": 10.0,
                    "health": 8.0,
                    "triple_shot": 6.0,
                }
                if self._level_type == "boss":
                    weights["guided_missile"] = 12.0
                return weights
        """
        return {}  # base returns nothing — games must override

    @property
    def current_interval(self) -> float:
        """Current computed interval. Exposed for tests and debug."""
        return self._interval

    @property
    def timer(self) -> float:
        return self._timer

    @timer.setter
    def timer(self, value: float) -> None:
        self._timer = value
```

---

## PowerUpManager

```python
# src/agf/powerups/manager.py
from __future__ import annotations
import random
from typing import Any, Optional
import arcade
from agf.powerups.effect_base import PowerUpEffect
from agf.powerups.effect_categories import (
    BehaviorEffect, ConstraintEffect, OverlayEffect, InstantEffect
)
from agf.powerups.powerup_sprite import PowerUpSprite
from agf.powerups.spawner import PowerUpSpawner
from agf.powerups.config import PowerUpConfigBase


class PowerUpManager:
    """Owns falling pickup sprites and active effects.

    Lives on BaseLevel subclasses. Level calls update() and draw()
    each frame. RunLevelView queries typed getters for effect-category
    specific behaviour (firing override, damage interception, etc.)

    Games subclass and override:
      create_spawner() — return a game-specific PowerUpSpawner subclass
      create_sprite()  — return a PowerUpSprite with game asset texture
      create_effect()  — map effect_type string to PowerUpEffect instance
    """

    def __init__(self, config: PowerUpConfigBase,
                 window_width: int, window_height: int,
                 sprite_scale: float = 1.0):
        self._config = config
        self._window_width = window_width
        self._window_height = window_height
        self._scale = sprite_scale
        self._spawner: PowerUpSpawner = self.create_spawner()
        self._sprites = arcade.SpriteList()
        self._active_effects: list[PowerUpEffect] = []

    # ------------------------------------------------------------------
    # Overridable factory methods
    # ------------------------------------------------------------------

    def create_spawner(self) -> PowerUpSpawner:
        """Return a PowerUpSpawner instance.
        Override to return a game-specific subclass."""
        return PowerUpSpawner(self._config)

    def create_sprite(self, effect_type: str, x: float,
                      y: float) -> PowerUpSprite:
        """Return a PowerUpSprite for the given effect_type.
        Override to load game-specific textures per type."""
        return PowerUpSprite(
            x=x, y=y,
            effect_type=effect_type,
            fall_speed=self._config.fall_speed,
            scale=self._scale,
        )

    def create_effect(self, effect_type: str) -> PowerUpEffect:
        """Map effect_type string to a PowerUpEffect instance.
        Games MUST override this to return their concrete effects."""
        raise NotImplementedError(
            f"PowerUpManager.create_effect() not implemented "
            f"for effect_type={effect_type!r}. "
            f"Override create_effect() in your game's PowerUpManager subclass."
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def setup(self, level_number: int, level_type: str) -> None:
        self._spawner.setup(level_number, level_type)

    # ------------------------------------------------------------------
    # Per-frame
    # ------------------------------------------------------------------

    def update(self, delta_time: float,
               player_ship: Any,
               context: dict,
               enemy_x_positions: list[float]) -> list[str]:
        """Tick spawner, move sprites, detect collection, tick effects.

        Returns list of effect_type strings for effects collected
        this frame (for GameEvent generation in RunLevelView).
        player_ship may be None during death sequence — guard all
        ship accesses.
        """
        collected: list[str] = []

        # Tick spawner
        spawn_type = self._spawner.update(delta_time)
        if spawn_type is not None:
            x = self._pick_spawn_x(enemy_x_positions)
            sprite = self.create_sprite(spawn_type, x,
                                        self._window_height - 10)
            self._sprites.append(sprite)

        # Move falling sprites
        for sprite in list(self._sprites):
            sprite.update(delta_time)

        # Detect collection
        if player_ship is not None and not player_ship.is_invincible():
            hits = arcade.check_for_collision_with_list(
                player_ship, self._sprites
            )
            for hit in hits:
                hit.remove_from_sprite_lists()
                effect = self.create_effect(hit.effect_type)
                self._add_effect(effect, player_ship, context)
                collected.append(hit.effect_type)

        # Tick active effects
        expired: list[PowerUpEffect] = []
        for effect in self._active_effects:
            if not effect.update(delta_time, player_ship):
                expired.append(effect)
        for effect in expired:
            self.remove_effect(effect, player_ship, context)

        return collected

    def draw(self) -> None:
        """Draw falling pickup sprites.
        Overlay sprites are drawn by RunLevelView via get_active_overlay()."""
        self._sprites.draw()

    # ------------------------------------------------------------------
    # Effect management
    # ------------------------------------------------------------------

    def _add_effect(self, effect: PowerUpEffect,
                    ship: Any, context: dict) -> None:
        """Add effect, enforcing one-per-category rules."""
        if effect.is_instant:
            effect.apply(ship, context)
            return

        # One BehaviorEffect at a time — replace existing
        if isinstance(effect, BehaviorEffect):
            for existing in list(self._active_effects):
                if isinstance(existing, BehaviorEffect):
                    self.remove_effect(existing, ship, context)

        # One ConstraintEffect at a time — replace existing
        if isinstance(effect, ConstraintEffect):
            for existing in list(self._active_effects):
                if isinstance(existing, ConstraintEffect):
                    self.remove_effect(existing, ship, context)

        # One OverlayEffect at a time — replace existing
        if isinstance(effect, OverlayEffect):
            for existing in list(self._active_effects):
                if isinstance(existing, OverlayEffect):
                    self.remove_effect(existing, ship, context)

        # StatModifier: multiple allowed simultaneously
        effect.apply(ship, context)
        self._active_effects.append(effect)

    def remove_effect(self, effect: PowerUpEffect,
                      ship: Any = None,
                      context: dict | None = None) -> None:
        """Force-remove an effect (e.g. overlay depleted by hit)."""
        if effect in self._active_effects:
            if ship is not None:
                effect.remove(ship, context or {})
            self._active_effects.remove(effect)

    def clear_all(self, ship: Any = None,
                  context: dict | None = None) -> None:
        """Remove all sprites and cancel all active effects.
        Call on player death."""
        self._sprites.clear()
        for effect in list(self._active_effects):
            if ship is not None:
                effect.remove(ship, context or {})
        self._active_effects.clear()

    # ------------------------------------------------------------------
    # Typed getters — used by RunLevelView
    # ------------------------------------------------------------------

    def get_active_behavior(self) -> BehaviorEffect | None:
        """Active firing behavior override, or None."""
        for e in self._active_effects:
            if isinstance(e, BehaviorEffect):
                return e
        return None

    def get_active_overlay(self) -> OverlayEffect | None:
        """Active overlay effect (e.g. shield), or None."""
        for e in self._active_effects:
            if isinstance(e, OverlayEffect):
                return e
        return None

    def get_active_constraint(self) -> ConstraintEffect | None:
        """Active constraint modifier, or None."""
        for e in self._active_effects:
            if isinstance(e, ConstraintEffect):
                return e
        return None

    def get_active_effects(self) -> list[PowerUpEffect]:
        """All active effects. Used by HUD for display."""
        return list(self._active_effects)

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def to_snapshot(self) -> dict:
        """Serialise spawner timer state for 2P switching.
        Active effects are NOT preserved across player switches."""
        return {
            "spawner_timer": self._spawner.timer,
            "spawner_interval": self._spawner.current_interval,
        }

    @classmethod
    def from_snapshot(cls, snapshot: dict,
                      config: PowerUpConfigBase,
                      window_width: int, window_height: int,
                      sprite_scale: float = 1.0,
                      level_number: int = 1,
                      level_type: str = "standard") -> 'PowerUpManager':
        """Restore from snapshot. Subclasses call super() then
        pass their own config type."""
        manager = cls(config, window_width, window_height, sprite_scale)
        manager.setup(level_number, level_type)
        manager._spawner.timer = snapshot.get("spawner_timer", 0.0)
        manager._spawner._interval = snapshot.get(
            "spawner_interval",
            manager._spawner.current_interval
        )
        return manager

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pick_spawn_x(self,
                      enemy_positions: list[float]) -> float:
        """Spawn beneath a random living enemy if any, else random x."""
        if enemy_positions:
            return random.choice(enemy_positions)
        margin = 40
        return random.uniform(margin, self._window_width - margin)
```

---

## BaseLevel additions

Add to `src/agf/levels/base_level.py`:

```python
@abstractmethod
def get_powerup_manager(self) -> 'PowerUpManager | None':
    """Returns level's PowerUpManager, or None if this level
    type has no power-ups. RunLevelView uses this for effect
    category queries."""
    ...

def get_enemy_x_positions(self) -> list[float]:
    """x positions of living enemies for spawn position selection.
    Default returns empty list. Override in levels with enemy grids."""
    return []
```

---

## Unit tests required (agf)

All tests must run without a display.

### effect_categories.py

**StatModifierEffect:**
- apply() sets attribute to original * multiplier
- apply() preserves int type when original is int
- update() returns True before duration expires
- update() returns False after duration expires
- remove() restores original value exactly
- additive parameter adds to value after multiplying

**BehaviorEffect:**
- update() returns False after duration
- is_instant returns False
- remaining_duration decreases each update

**ConstraintEffect:**
- apply() calls apply_constraints() with correct window dimensions
- remove() calls restore_constraints()
- update() returns False after duration

**OverlayEffect:**
- apply() calls create_overlay_sprite() with scale from context
- update() calls update_overlay_sprite() with ship position
- remove() sets _overlay_sprite to None
- get_overlay_sprite() returns sprite while active, None after remove

**InstantEffect:**
- is_instant returns True
- update() always returns False
- remove() does nothing

### PowerUpSpawner
- setup() resets timer to 0
- update() returns None before interval expires
- update() returns type string from weight table when interval expires
- update() returns None when weight table is empty
- _compute_interval() decreases with level number
- _compute_interval() floors at spawn_interval_min
- timer resets after spawn

### PowerUpSprite
- Moves downward by fall_speed * delta_time each frame
- Removes itself when center_y < -height
- effect_type attribute accessible after init

### PowerUpManager
- _add_effect() with BehaviorEffect removes existing BehaviorEffect
- _add_effect() with ConstraintEffect removes existing ConstraintEffect
- _add_effect() with OverlayEffect removes existing OverlayEffect
- Multiple StatModifierEffects can be active simultaneously
- InstantEffect is applied but not added to _active_effects
- remove_effect() calls effect.remove() on ship if provided
- clear_all() empties sprites and calls remove() on all effects
- get_active_behavior() returns None when no behavior effect active
- get_active_overlay() returns None when no overlay effect active
- to_snapshot() captures timer and interval
- from_snapshot() restores timer and interval

---

## Implementation notes

- All effect category classes must be importable without arcade
  being initialised — use TYPE_CHECKING guards for arcade type hints
- PowerUpManager.create_effect() raises NotImplementedError by design —
  this is a deliberate contract that forces games to implement it.
  Do not provide a default implementation.
- StatModifierEffect stores the original attribute value at apply()
  time, not at construction time — this handles cases where another
  effect already modified the attribute before this one is applied.
  Stacking two StatModifiers on the same attribute will compound
  correctly as long as both store their own original values.
- PowerUpSprite uses effect_type string not an enum — this keeps agf
  decoupled from game-specific enum definitions. Games define their
  own PowerUpType enum and pass the .value string.
- The one-per-category enforcement in _add_effect() handles the case
  where a player collects a second BehaviorEffect while one is already
  active — the old one is cleanly removed before the new one applies.
  This is the correct UX behaviour (collecting a laser beam while
  triple shot is active replaces it rather than stacking).
- StatModifiers are intentionally exempt from the one-per-category rule
  since stacking rapid fire + damage boost + speed boost simultaneously
  is valid and fun gameplay.
