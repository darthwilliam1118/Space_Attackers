"""Unit tests for Particle, ParticleEmitter, and ShockwaveSprite — no display required."""

from __future__ import annotations

import math

import arcade
import pytest

from src.particles_config import ParticlesConfig
from src.sprites.particles import Particle, ParticleEmitter, ShockwaveSprite


def _texture(name: str = "t") -> arcade.Texture:
    return arcade.Texture.create_empty(name, (8, 8))


def _textures() -> list[arcade.Texture]:
    return [_texture("t0"), _texture("t1"), _texture("t2")]


def _config(**overrides: object) -> ParticlesConfig:
    defaults = dict(
        particle_count=5,
        particle_speed_min=50.0,
        particle_speed_max=200.0,
        particle_lifetime_min=0.5,
        particle_lifetime_max=0.5,  # fixed lifetime for deterministic tests
        particle_gravity=100.0,
        shockwave_duration=1.0,
        shockwave_max_scale=2.0,
    )
    defaults.update(overrides)
    return ParticlesConfig(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Particle tests
# ---------------------------------------------------------------------------

class TestParticleMovement:
    def test_moves_by_velocity_times_delta(self) -> None:
        cfg = _config(particle_gravity=0.0)
        p = Particle(100.0, 200.0, _textures(), cfg)
        initial_x = p.center_x
        initial_y = p.center_y
        cx_before = p.change_x
        cy_before = p.change_y
        p.update(0.1)
        assert p.center_x == pytest.approx(initial_x + cx_before * 0.1, abs=1e-3)
        # change_y is modified by gravity first, so use the updated value
        expected_cy = cy_before - cfg.particle_gravity * 0.1
        assert p.center_y == pytest.approx(initial_y + expected_cy * 0.1, abs=1e-3)

    def test_alpha_decreases_over_lifetime(self) -> None:
        cfg = _config(particle_lifetime_min=1.0, particle_lifetime_max=1.0)
        p = Particle(0.0, 0.0, _textures(), cfg)
        p.update(0.5)
        assert p.alpha == pytest.approx(127, abs=2)
        p.update(0.5)
        # Should be removed; alpha irrelevant after expiry

    def test_alpha_starts_at_255(self) -> None:
        cfg = _config()
        p = Particle(0.0, 0.0, _textures(), cfg)
        assert p.alpha == 255

    def test_scale_decreases_over_lifetime(self) -> None:
        cfg = _config(particle_lifetime_min=1.0, particle_lifetime_max=1.0)
        p = Particle(0.0, 0.0, _textures(), cfg)
        initial_scale = p.scale
        p.update(0.5)
        assert p.scale < initial_scale

    def test_remove_when_elapsed_exceeds_lifetime(self) -> None:
        cfg = _config(particle_lifetime_min=0.1, particle_lifetime_max=0.1)
        particles = arcade.SpriteList()
        p = Particle(0.0, 0.0, _textures(), cfg)
        particles.append(p)
        assert len(particles) == 1
        p.update(0.2)
        assert len(particles) == 0

    def test_not_removed_before_lifetime(self) -> None:
        cfg = _config(particle_lifetime_min=1.0, particle_lifetime_max=1.0)
        particles = arcade.SpriteList()
        p = Particle(0.0, 0.0, _textures(), cfg)
        particles.append(p)
        p.update(0.5)
        assert len(particles) == 1

    def test_gravity_decreases_change_y(self) -> None:
        cfg = _config(particle_gravity=100.0, particle_lifetime_min=1.0, particle_lifetime_max=1.0)
        p = Particle(0.0, 0.0, _textures(), cfg)
        initial_change_y = p.change_y
        p.update(0.1)
        assert p.change_y == pytest.approx(initial_change_y - 100.0 * 0.1, abs=1e-3)

    def test_speed_within_configured_range(self) -> None:
        cfg = _config(particle_speed_min=80.0, particle_speed_max=120.0)
        # Run many particles to check range; gravity=0 so change_x/y are pure velocity
        for _ in range(50):
            p = Particle(0.0, 0.0, _textures(), cfg)
            speed = math.hypot(p.change_x, p.change_y)
            # momentum is 0 by default, so speed comes entirely from randomisation
            assert 80.0 <= speed <= 120.0 + 1e-9


class TestParticleMomentum:
    def test_momentum_added_to_change_x(self) -> None:
        cfg = _config(particle_speed_min=0.0, particle_speed_max=0.0)
        p = Particle(0.0, 0.0, _textures(), cfg, vx_momentum=50.0)
        # With speed=0 the random component is zero; only momentum remains
        assert p.change_x == pytest.approx(50.0, abs=1e-6)

    def test_momentum_added_to_change_y(self) -> None:
        cfg = _config(particle_speed_min=0.0, particle_speed_max=0.0)
        p = Particle(0.0, 0.0, _textures(), cfg, vy_momentum=30.0)
        assert p.change_y == pytest.approx(30.0, abs=1e-6)


# ---------------------------------------------------------------------------
# ParticleEmitter tests
# ---------------------------------------------------------------------------

class TestParticleEmitter:
    def test_explode_adds_correct_count(self) -> None:
        cfg = _config(particle_count=7)
        emitter = ParticleEmitter(cfg, textures=_textures())
        emitter.explode(0.0, 0.0)
        assert emitter.active_count == 7

    def test_explode_multiple_times_accumulates(self) -> None:
        cfg = _config(particle_count=3)
        emitter = ParticleEmitter(cfg, textures=_textures())
        emitter.explode(0.0, 0.0)
        emitter.explode(10.0, 10.0)
        assert emitter.active_count == 6

    def test_update_propagates_delta_time(self) -> None:
        cfg = _config(particle_count=1, particle_lifetime_min=0.1, particle_lifetime_max=0.1)
        emitter = ParticleEmitter(cfg, textures=_textures())
        emitter.explode(0.0, 0.0)
        assert emitter.active_count == 1
        emitter.update(0.2)  # > lifetime → particle self-removes
        assert emitter.active_count == 0

    def test_active_count_property(self) -> None:
        cfg = _config(particle_count=4)
        emitter = ParticleEmitter(cfg, textures=_textures())
        assert emitter.active_count == 0
        emitter.explode(0.0, 0.0)
        assert emitter.active_count == 4


# ---------------------------------------------------------------------------
# ShockwaveSprite tests
# ---------------------------------------------------------------------------

class TestShockwaveSprite:
    def test_scale_increases_over_duration(self) -> None:
        cfg = _config(shockwave_duration=1.0, shockwave_max_scale=2.0)
        sw = ShockwaveSprite(0.0, 0.0, cfg, texture=_texture())
        assert sw.scale_x == pytest.approx(0.1, abs=1e-6)
        sw.update(0.5)
        # t=0.5 → scale = 0.1 + 0.5 * 2.0 = 1.1
        assert sw.scale_x == pytest.approx(1.1, abs=1e-3)

    def test_alpha_decreases_over_duration(self) -> None:
        cfg = _config(shockwave_duration=1.0)
        sw = ShockwaveSprite(0.0, 0.0, cfg, texture=_texture())
        assert sw.alpha == 180
        sw.update(0.5)
        # t=0.5 → alpha = int(180 * 0.5) = 90
        assert sw.alpha == pytest.approx(90, abs=1)

    def test_removed_when_elapsed_exceeds_duration(self) -> None:
        cfg = _config(shockwave_duration=0.2)
        shockwaves = arcade.SpriteList()
        sw = ShockwaveSprite(0.0, 0.0, cfg, texture=_texture())
        shockwaves.append(sw)
        assert len(shockwaves) == 1
        sw.update(0.3)
        assert len(shockwaves) == 0

    def test_not_removed_mid_animation(self) -> None:
        cfg = _config(shockwave_duration=1.0)
        shockwaves = arcade.SpriteList()
        sw = ShockwaveSprite(0.0, 0.0, cfg, texture=_texture())
        shockwaves.append(sw)
        sw.update(0.5)
        assert len(shockwaves) == 1

    def test_is_complete_false_mid_animation(self) -> None:
        cfg = _config(shockwave_duration=1.0)
        sw = ShockwaveSprite(0.0, 0.0, cfg, texture=_texture())
        sw.update(0.5)
        assert not sw.is_complete

    def test_is_complete_true_after_duration(self) -> None:
        cfg = _config(shockwave_duration=0.2)
        sw = ShockwaveSprite(0.0, 0.0, cfg, texture=_texture())
        sw.update(0.3)
        assert sw.is_complete

    def test_accepts_pre_loaded_texture(self) -> None:
        cfg = _config()
        tex = _texture("shockwave_test")
        sw = ShockwaveSprite(0.0, 0.0, cfg, texture=tex)
        assert sw.texture == tex

    def test_position_set_correctly(self) -> None:
        cfg = _config()
        sw = ShockwaveSprite(123.0, 456.0, cfg, texture=_texture())
        assert sw.center_x == pytest.approx(123.0)
        assert sw.center_y == pytest.approx(456.0)

    def test_momentum_drifts_center(self) -> None:
        cfg = _config(shockwave_duration=1.0)
        sw = ShockwaveSprite(0.0, 0.0, cfg, vx=100.0, vy=50.0, texture=_texture())
        sw.update(0.1)
        assert sw.center_x == pytest.approx(100.0 * 0.1, abs=1e-3)
        assert sw.center_y == pytest.approx(50.0 * 0.1, abs=1e-3)
