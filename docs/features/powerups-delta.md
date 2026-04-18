# Power-Up Brief — Delta / Additions

Supplements agf-powerups.md and sa-powerups.md.
These changes take precedence over the original briefs where they conflict.

---

## 1. PowerUpSprite — diagonal movement and rotation (agf)

### Replace the current PowerUpSprite class entirely:

```python
# src/agf/powerups/powerup_sprite.py
from __future__ import annotations
import math
from typing import Optional
import arcade


class PowerUpSprite(arcade.Sprite):
    """Falling power-up pickup sprite.

    Spawns above the visible window and drifts downward at a
    configurable angle and speed, rotating slowly while falling.
    Removes itself when it scrolls off the bottom of the screen.

    Games pass a pre-loaded texture so the sprite has no knowledge
    of asset paths.
    """

    def __init__(self, x: float, y: float,
                 effect_type: str,
                 fall_speed: float = 80.0,
                 angle_deg: float = 0.0,
                 spin_rpm: float = 10.0,
                 scale: float = 1.0,
                 texture: Optional[arcade.Texture] = None):
        """
        x, y        — spawn position. y should be above window top
                      (e.g. window_height + sprite_height / 2)
        fall_speed  — pixels/second along the fall direction
        angle_deg   — drift angle in degrees. 0 = straight down.
                      Positive = drift right, negative = drift left.
                      Recommended range: -20 to +20 degrees.
        spin_rpm    — sprite rotation speed in RPM while falling.
                      10 RPM = one full rotation every 6 seconds.
        """
        if texture is not None:
            super().__init__(texture=texture)
        else:
            super().__init__()
        self.scale = scale
        self.effect_type = effect_type

        self._fall_speed = fall_speed
        self._spin_rpm = spin_rpm

        # Convert angle to velocity components
        # angle_deg=0 means straight down (negative y direction)
        rad = math.radians(angle_deg)
        self._vx = math.sin(rad) * fall_speed   # horizontal drift
        self._vy = -math.cos(rad) * fall_speed  # vertical (downward)

        # Spin: convert RPM to degrees/second
        self._spin_rate = spin_rpm * 6.0  # 1 RPM = 6 deg/s

        # Start above the window at the given position
        self.center_x = x
        self.center_y = y
        self.angle = 0.0

    def update(self, delta_time: float) -> None:  # type: ignore[override]
        self.center_x += self._vx * delta_time
        self.center_y += self._vy * delta_time
        self.angle += self._spin_rate * delta_time

        # Remove when fully below the bottom of the screen
        # Caller passes window_height via context at creation time —
        # use a generous negative threshold since we don't store window_height
        if self.center_y < -(self.height * 2):
            self.remove_from_sprite_lists()
```

### Add to PowerUpConfigBase (agf):

```python
# In src/agf/powerups/config.py — add these fields:
fall_speed_min: float = 60.0     # slowest fall speed (px/s)
fall_speed_max: float = 120.0    # fastest fall speed (px/s)
fall_angle_max: float = 20.0     # max drift angle degrees (+-) 
spin_rpm: float = 10.0           # rotation speed during fall
spawn_height_offset: float = 60.0  # pixels above window top to spawn
```

Remove the single `fall_speed: float = 80.0` field — replaced by
`fall_speed_min` and `fall_speed_max` for per-sprite randomisation.

### Update PowerUpManager.create_sprite() (agf):

```python
def create_sprite(self, effect_type: str, x: float,
                  y: float) -> PowerUpSprite:
    """y parameter is ignored — sprite always spawns above window."""
    import random
    cfg = self._config
    fall_speed = random.uniform(cfg.fall_speed_min, cfg.fall_speed_max)
    angle_deg = random.uniform(-cfg.fall_angle_max, cfg.fall_angle_max)
    spawn_y = self._window_height + cfg.spawn_height_offset
    texture = None  # subclasses override create_sprite() to load textures

    return PowerUpSprite(
        x=x,
        y=spawn_y,
        effect_type=effect_type,
        fall_speed=fall_speed,
        angle_deg=angle_deg,
        spin_rpm=cfg.spin_rpm,
        scale=self._scale,
        texture=texture,
    )
```

---

## 2. game_config.toml — replace fall_speed with range (SA)

```toml
[powerups]
# ... existing fields ...

# Replace: fall_speed = 80.0
# With:
fall_speed_min = 60.0
fall_speed_max = 120.0
fall_angle_max = 20.0
spin_rpm = 10.0
spawn_height_offset = 60.0
```

Update `SAP owerUpConfig` to inherit these from `PowerUpConfigBase`
(they're defined there now — no duplication needed in SA).

---

## 3. Gradual type introduction by level (SA)

### Replace SAP owerUpSpawner._build_weight_table() entirely:

The weight table must gate types by level number. Types unlock one
per level starting at level 2. The unlock order is defined as a
class-level constant so it's easy to adjust.

```python
# src/powerups/sa_spawner.py

class SAP owerUpSpawner(PowerUpSpawner):

    # Unlock order — index 0 unlocks at level 2, index 1 at level 3, etc.
    # Reorder this list to change which types appear first.
    UNLOCK_ORDER: list[str] = [
        "health",       # level 2 — most immediately useful
        "shield",       # level 3
        "rapid_fire",   # level 4
        "big_gun",      # level 5
        "triple_shot",  # level 6
        "speed_boost",  # level 7
        "spread_shot",  # level 8
        "free_move",    # level 9
    ]

    def _available_types(self) -> list[str]:
        """Returns types unlocked at the current level.
        Level 1: none. Level 2: first type. Level 3: first two. Etc."""
        unlocked_count = max(0, self._level_number - 1)
        return self.UNLOCK_ORDER[:unlocked_count]

    def _build_weight_table(self) -> dict[str, float]:
        available = self._available_types()
        if not available:
            return {}   # level 1 — no spawns

        cfg = self._config
        base_weights = {
            "health":      cfg.weight_health,
            "shield":      cfg.weight_shield,
            "rapid_fire":  cfg.weight_rapid_fire,
            "big_gun":     cfg.weight_big_gun,
            "triple_shot": cfg.weight_triple_shot,
            "speed_boost": cfg.weight_speed_boost,
            "spread_shot": cfg.weight_spread_shot,
            "free_move":   cfg.weight_free_move,
        }

        # Filter to only unlocked types
        weights = {t: base_weights[t] for t in available
                   if t in base_weights}

        # Boss levels: boost combat-useful types
        if self._level_type == "boss":
            for t in ("triple_shot", "shield", "big_gun"):
                if t in weights:
                    weights[t] *= 2.0

        return weights
```

---

## 4. Spawn rate curve (agf + SA)

### Replace PowerUpSpawner._compute_interval() in agf:

The current linear reduction is too gradual early on. Use a curve
that drops quickly in the first few levels then flattens:

```python
def _compute_interval(self) -> float:
    """Compute spawn interval using a curve that drops quickly
    in early levels then flattens toward the minimum.

    Uses exponential decay: interval = min + (base - min) * decay^level
    This gives a fast initial drop that gradually flattens, feeling
    more natural than a linear ramp.
    """
    import math
    cfg = self._config
    base = cfg.spawn_interval_base
    minimum = cfg.spawn_interval_min
    # decay_rate controls how fast the curve drops.
    # 0.85 means each level is 85% of the previous gap above minimum.
    decay_rate = getattr(cfg, 'spawn_interval_decay', 0.85)
    level_offset = max(0, self._level_number - 2)  # no spawns level 1
    interval = minimum + (base - minimum) * (decay_rate ** level_offset)
    jitter = random.uniform(
        -cfg.spawn_interval_jitter,
        cfg.spawn_interval_jitter
    )
    return max(minimum, interval + jitter)
```

### Add to PowerUpConfigBase (agf):

```python
spawn_interval_decay: float = 0.85  # exponential decay rate per level
```

Remove `spawn_interval_step` — replaced by `spawn_interval_decay`.
Update SA config and game_config.toml accordingly:

```toml
[powerups]
# Remove: spawn_interval_step = 0.5
# Add:
spawn_interval_decay = 0.85
```

The effect of decay = 0.85 with base = 20s and min = 6s:
```
Level 1:  no spawns (type table empty)
Level 2:  20.0s  (first unlock, full base interval)
Level 3:  17.9s
Level 4:  16.1s
Level 5:  14.6s
Level 6:  13.2s
Level 8:  10.9s
Level 10:  9.1s
Level 15:  7.3s
Level 20:  6.5s  (approaching minimum)
Level 25+: ~6.0s (at minimum)
```

---

## 5. Updated unit tests (additions)

### PowerUpSprite
- Sprite spawns at y = window_height + spawn_height_offset (above window)
- center_y decreases each frame (falls down)
- center_x drifts by vx * delta_time (angle drift)
- angle increases by spin_rate * delta_time each frame
- At angle_deg=0: vx is 0 (straight down)
- At angle_deg=20: vx is positive (drifts right)
- At angle_deg=-20: vx is negative (drifts left)
- Removes itself when center_y < -(height * 2)
- fall_speed, angle_deg, spin_rpm all configurable independently

### SAP owerUpSpawner
- _available_types() returns [] at level 1
- _available_types() returns ["health"] at level 2
- _available_types() returns ["health", "shield"] at level 3
- _available_types() returns all 8 types at level 9+
- _build_weight_table() returns {} at level 1 (no spawns)
- _build_weight_table() only includes unlocked types
- Boss level_type boosts combat type weights
- update() returns None at level 1 regardless of timer

### PowerUpSpawner (interval curve)
- Interval at level 2 equals spawn_interval_base (no reduction yet)
- Interval at level 3 < interval at level 2
- Interval never goes below spawn_interval_min
- Decay formula: min + (base - min) * decay^level_offset

---

## 6. CLAUDE.md additions

Add to Space Attackers CLAUDE.md:

```markdown
## Power-up spawn behaviour
- Level 1: no power-ups spawn at all (weight table is empty)
- Types unlock one per level starting level 2, in UNLOCK_ORDER sequence
- Unlock order defined in SAP owerUpSpawner.UNLOCK_ORDER — edit there
  to change which types appear first
- Spawn interval uses exponential decay curve (not linear) — see
  PowerUpSpawner._compute_interval()
- Sprites spawn above the window top and drift down at random angle
  (-fall_angle_max to +fall_angle_max degrees) and random speed
  (fall_speed_min to fall_speed_max px/s)
- All sprites rotate at spin_rpm (default 10 RPM) while falling
- fall_speed_min, fall_speed_max, fall_angle_max, spin_rpm all
  configurable in game_config.toml [powerups] section
```
