"""Particle effects — burst particles and shockwave ring for destruction events."""

from __future__ import annotations

import math
import random

import arcade

from src.particles_config import ParticlesConfig

# Colours sampled randomly per particle
_PARTICLE_COLORS: list[tuple[int, int, int, int]] = [
    (255, 200, 50, 255),   # yellow
    (255, 120, 20, 255),   # orange
    (255, 60,  10, 255),   # red-orange
    (200, 200, 200, 255),  # grey (debris)
]


class Particle(arcade.Sprite):
    """A single debris or spark particle spawned on destruction.

    Textures are injected so __init__ never touches the disk or GPU directly.
    """

    def __init__(
        self,
        x: float,
        y: float,
        textures: list[arcade.Texture],
        config: ParticlesConfig,
        vx_momentum: float = 0.0,
        vy_momentum: float = 0.0,
    ) -> None:
        super().__init__()
        self.texture = random.choice(textures)

        self.center_x = x
        self.center_y = y

        angle = random.uniform(0.0, 2.0 * math.pi)
        speed = random.uniform(config.particle_speed_min, config.particle_speed_max)
        self.change_x = math.cos(angle) * speed + vx_momentum
        self.change_y = math.sin(angle) * speed + vy_momentum
        self.change_angle = random.uniform(-180.0, 180.0)

        self._lifetime: float = random.uniform(
            config.particle_lifetime_min, config.particle_lifetime_max
        )
        self._elapsed: float = 0.0
        self._initial_scale: float = random.uniform(0.3, 0.8)
        self._gravity: float = config.particle_gravity

        self.scale = self._initial_scale
        self.color = random.choice(_PARTICLE_COLORS)

    def update(self, delta_time: float = 1 / 60) -> None:  # type: ignore[override]
        self._elapsed += delta_time
        if self._elapsed >= self._lifetime:
            self.remove_from_sprite_lists()
            return

        t = self._elapsed / self._lifetime

        self.alpha = int(255 * (1.0 - t))
        self.scale = self._initial_scale * (1.0 - t * 0.8)

        self.change_y -= self._gravity * delta_time

        self.center_x += self.change_x * delta_time
        self.center_y += self.change_y * delta_time
        self.angle += self.change_angle * delta_time


class ParticleEmitter:
    """Manages a SpriteList of Particle objects.

    Instantiate once and reuse across all explosions.  Pass optional
    *textures* in tests to avoid requiring an OpenGL context.
    """

    def __init__(
        self,
        config: ParticlesConfig,
        textures: list[arcade.Texture] | None = None,
    ) -> None:
        self._config = config
        if textures is not None:
            self._textures = textures
        else:
            spark = arcade.make_soft_circle_texture(16, (255, 200, 80, 255))
            debris = arcade.make_circle_texture(6, (180, 180, 180, 255))
            self._textures = [spark, debris, spark]  # weight sparks higher

        self.particles: arcade.SpriteList = arcade.SpriteList()

    def explode(
        self,
        x: float,
        y: float,
        vx: float = 0.0,
        vy: float = 0.0,
        count: int | None = None,
    ) -> None:
        """Spawn particles at *(x, y)* with optional momentum *(vx, vy)*."""
        n = count if count is not None else self._config.particle_count
        for _ in range(n):
            p = Particle(x, y, self._textures, self._config, vx, vy)
            self.particles.append(p)

    def update(self, delta_time: float) -> None:
        """Tick all live particles (each self-removes on expiry)."""
        for p in list(self.particles):
            p.update(delta_time)

    def draw(self) -> None:
        """Draw all live particles."""
        self.particles.draw()

    @property
    def active_count(self) -> int:
        """Number of currently live particles."""
        return len(self.particles)


class ShockwaveSprite(arcade.Sprite):
    """Expanding translucent ring that fades out over *duration* seconds.

    Pass *texture* in tests to avoid requiring an OpenGL context.
    """

    def __init__(
        self,
        x: float,
        y: float,
        config: ParticlesConfig,
        vx: float = 0.0,
        vy: float = 0.0,
        texture: arcade.Texture | None = None,
    ) -> None:
        if texture is None:
            texture = arcade.make_circle_texture(64, arcade.color.WHITE)
        super().__init__()
        self.texture = texture

        self.center_x = x
        self.center_y = y
        self._vx = vx
        self._vy = vy
        self._duration = config.shockwave_duration
        self._max_scale = config.shockwave_max_scale
        self._elapsed = 0.0

        self.scale = 0.1
        self.alpha = 180

    def update(self, delta_time: float = 1 / 60) -> None:  # type: ignore[override]
        self._elapsed += delta_time
        if self._elapsed >= self._duration:
            self.remove_from_sprite_lists()
            return

        t = self._elapsed / self._duration
        self.scale = 0.1 + t * self._max_scale
        self.alpha = int(180 * (1.0 - t))
        self.center_x += self._vx * delta_time
        self.center_y += self._vy * delta_time

    @property
    def is_complete(self) -> bool:
        return self._elapsed >= self._duration
