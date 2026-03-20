# Feature: Particle Effects

## Overview
Enemy and player ship destruction triggers a three-layer visual effect:
a sprite sheet explosion (central flash), a particle burst (flying debris
and sparks), and an expanding shockwave ring. All three layers play
simultaneously. No additional bitmap assets are required beyond the
existing explosion sprite sheet — particles and the shockwave are
generated programmatically.

## Files
- src/space_attackers/sprites/particles.py
  - Particle class
  - ParticleEmitter class
  - ShockwaveSprite class

## Three-layer destruction effect

Triggered on both enemy destruction and player ship death:

```python
# In RUN_LEVEL on any destruction event:
def spawn_destruction_effect(self, x: float, y: float) -> None:
    explosion = ExplosionSprite(x, y)           # layer 1 — sprite sheet
    self.scene.add_sprite("explosions", explosion)
    self.particle_emitter.explode(x, y)         # layer 2 — particles
    shockwave = ShockwaveSprite(x, y)           # layer 3 — ring
    self.scene.add_sprite("shockwaves", shockwave)
```

Scene layer order (draw back to front):
  background → stars → enemies → player → bullets →
  shockwaves → explosions → particles → HUD

## Layer 1 — Sprite sheet explosion

Defined in src/space_attackers/sprites/explosion.py (existing feature —
see player-ship.md). Referenced here for draw order context only.

## Layer 2 — Particle burst

### Particle class

Each particle is an arcade.Sprite with randomised velocity, rotation,
lifetime, scale, and color. Particles remove themselves on expiry.

```python
class Particle(arcade.Sprite):
    def __init__(self, x: float, y: float,
                 textures: list[arcade.Texture]):
        """
        textures: pre-loaded list of particle textures passed in from
        ParticleEmitter — no disk loading in __init__ for testability.
        """

    def update(self, delta_time: float) -> None:
        """
        Each frame:
        - Advance elapsed time
        - If elapsed >= lifetime: remove_from_sprite_lists(), return
        - Compute t = elapsed / lifetime  (0.0 -> 1.0)
        - Fade out: self.alpha = int(255 * (1.0 - t))
        - Shrink: self.scale = initial_scale * (1.0 - t * 0.8)
        - Apply gravity: self.change_y -= gravity * delta_time
        - Apply velocity: self.center_x += self.change_x * delta_time
                          self.center_y += self.change_y * delta_time
        - Rotate: self.angle += self.change_angle * delta_time
        """
```

### Particle randomisation (per particle, set in __init__)

- angle: random 0 to 2π radians
- speed: random between `particle_speed_min` and `particle_speed_max`
- change_x: cos(angle) * speed
- change_y: sin(angle) * speed
- change_angle: random between -180 and 180 degrees/second
- lifetime: random between `particle_lifetime_min` and
  `particle_lifetime_max`
- initial_scale: random between 0.3 and 0.8
- color: randomly chosen from:
    (255, 200, 50)   — yellow
    (255, 120, 20)   — orange
    (255, 60,  10)   — red-orange
    (200, 200, 200)  — grey (debris)
- texture: randomly chosen from textures list

### Particle textures

Generated programmatically at startup — no asset files needed:

```python
# In ParticleEmitter.__init__():
self.spark_texture = arcade.make_soft_circle_texture(
    radius=8, color=(255, 200, 80, 255)
)
self.debris_texture = arcade.make_circle_texture(
    diameter=6, color=(180, 180, 180, 255)
)
self.textures = [self.spark_texture, self.debris_texture,
                 self.spark_texture]  # weight sparks higher
```

### ParticleEmitter class

```python
class ParticleEmitter:
    def __init__(self):
        self.particles = arcade.SpriteList()
        # Note: do NOT use use_spatial_hash — particles move every frame

    def explode(self, x: float, y: float,
                count: int = 20) -> None:
        """Spawn `count` particles at (x, y) with randomised properties."""

    def update(self, delta_time: float) -> None:
        """Call update(delta_time) on all particles."""

    def draw(self) -> None:
        """Draw all active particles."""

    @property
    def active_count(self) -> int:
        """Number of live particles — useful for debug display."""
```

### Gravity

Particles are subject to simulated gravity pulling them downward:
- `particle_gravity`: 150 pixels/second² (configurable)
- Applied as: `change_y -= particle_gravity * delta_time` each frame
- Creates a natural arc for debris rather than perfectly straight lines

## Layer 3 — Shockwave ring

An expanding translucent ring that fades out over ~0.3 seconds.

```python
class ShockwaveSprite(arcade.Sprite):
    def __init__(self, x: float, y: float,
                 duration: float = 0.3,
                 max_scale: float = 2.5,
                 texture: arcade.Texture | None = None):
        """
        texture: optional pre-loaded texture for testability.
        If None, generate via arcade.make_circle_texture(64,
        arcade.color.WHITE).
        """
        self.duration = duration
        self.max_scale = max_scale
        self.elapsed = 0.0
        self.center_x = x
        self.center_y = y
        self.scale = 0.1
        self.alpha = 180

    def update(self, delta_time: float) -> None:
        """
        Each frame:
        - elapsed += delta_time
        - If elapsed >= duration: remove_from_sprite_lists(), return
        - t = elapsed / duration
        - self.scale = 0.1 + t * max_scale
        - self.alpha = int(180 * (1.0 - t))
        """

    @property
    def is_complete(self) -> bool:
        return self.elapsed >= self.duration
```

## game_config.toml additions

```toml
[particles]
particle_count = 20
particle_speed_min = 50.0
particle_speed_max = 200.0
particle_lifetime_min = 0.3
particle_lifetime_max = 0.8
particle_gravity = 150.0
shockwave_duration = 0.3
shockwave_max_scale = 2.5
```

## Performance budget

- 20 particles per explosion is the default and well within 60fps budget
- Maximum simultaneous particles across all active explosions: ~300
  before potential frame drops on low-end hardware
- ParticleEmitter does not cap count — RUN_LEVEL should not spawn
  overlapping explosions faster than one per 0.1 seconds in practice
- If performance issues arise, reduce particle_count in config before
  changing code

## Unit tests required

All tests must run without a display.

- Particle moves by change_x * delta_time and change_y * delta_time
- Particle alpha decreases from 255 to 0 over lifetime
- Particle scale decreases over lifetime
- Particle calls remove_from_sprite_lists() when elapsed >= lifetime
- Particle change_y decreases each frame due to gravity
- ParticleEmitter.explode() adds correct count to particles SpriteList
- ParticleEmitter.update() propagates delta_time to all particles
- Particle speed is within configured min/max range
- ShockwaveSprite scale increases from 0.1 toward max_scale over duration
- ShockwaveSprite alpha decreases from 180 to 0 over duration
- ShockwaveSprite calls remove_from_sprite_lists() when elapsed >= duration
- ShockwaveSprite.is_complete returns False mid-animation, True after
- Shockwave accepts pre-loaded texture (no display needed in tests)

## Implementation notes

- Particle and ShockwaveSprite must be instantiatable without a display —
  accept pre-loaded textures as optional constructor parameters
- ParticleEmitter generates textures via arcade.make_soft_circle_texture()
  and arcade.make_circle_texture() — these require an active OpenGL
  context. Generate once in __init__ and reuse. In tests, inject textures
  via constructor.
- ParticleEmitter is instantiated once in RUN_LEVEL and reused across
  all explosions — do not create a new emitter per explosion
- ShockwaveSprite instances are created per explosion and self-manage
  via remove_from_sprite_lists()
- draw() for particles and shockwaves is called directly in on_draw(),
  not via Scene, so draw order is fully explicit
