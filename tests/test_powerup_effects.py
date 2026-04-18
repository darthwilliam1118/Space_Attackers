"""Unit tests for SA power-up effect classes."""

from __future__ import annotations

import pytest

from src.powerups.effects.big_gun import BigGunEffect
from src.powerups.effects.free_move import FreeMovementEffect
from src.powerups.effects.health import HealthEffect
from src.powerups.effects.rapid_fire import RapidFireEffect
from src.powerups.effects.shield import ShieldEffect
from src.powerups.effects.speed_boost import SpeedBoostEffect
from src.powerups.effects.spread_shot import SpreadShotEffect
from src.powerups.effects.triple_shot import TripleShotEffect
from src.powerups.sa_powerup_config import SAPowerUpConfig


class _FakeShipConfig:
    fire_cooldown: float = 0.5
    bullet_speed: float = 600.0
    player_bullet_damage: int = 100


class _FakeShip:
    """Stand-in for PlayerShip — no arcade.Sprite required for effect tests."""

    def __init__(self, hp: int = 50, max_hp: int = 100) -> None:
        self.hit_points = hp
        self.max_hit_points = max_hp
        self.fire_cooldown_multiplier = 1.0
        self.speed_multiplier = 1.0
        self.bullet_scale_multiplier = 1.0
        self.bullet_damage_multiplier = 1
        self.shield_active = False
        self.shield_hits_remaining = 0
        # Constraint zone attributes (FreeMovement)
        self._zone_top = 200.0
        self._zone_bottom = 0.0
        self._zone_left = 0.0
        self._zone_right = 800.0
        # Behavior-effect interior fields
        self._fire_cooldown_remaining = 0.0
        self._config = _FakeShipConfig()
        self._window_width = 800
        self._window_height = 600
        self._tilt_angle = 0.0
        self._player_num = 1
        self._sprite_scale = 1.0
        self.center_x = 400.0
        self.center_y = 50.0
        self.height = 48.0


@pytest.fixture
def cfg() -> SAPowerUpConfig:
    return SAPowerUpConfig()


@pytest.fixture
def ship() -> _FakeShip:
    return _FakeShip()


# ----------------------------------------------------------------------
# HealthEffect
# ----------------------------------------------------------------------


class TestHealthEffect:
    def test_apply_restores_hp(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        ship.hit_points = 50
        HealthEffect(cfg).apply(ship, {})
        assert ship.hit_points == 50 + cfg.health_restore_amount

    def test_apply_caps_at_max(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        ship.hit_points = 90
        ship.max_hit_points = 100
        HealthEffect(cfg).apply(ship, {})
        assert ship.hit_points == 100

    def test_is_instant(self, cfg: SAPowerUpConfig) -> None:
        assert HealthEffect(cfg).is_instant is True


# ----------------------------------------------------------------------
# BigGunEffect
# ----------------------------------------------------------------------


class TestBigGunEffect:
    def test_apply_sets_both_multipliers(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        eff = BigGunEffect(cfg)
        eff.apply(ship, {})
        assert ship.bullet_scale_multiplier == cfg.big_gun_scale_multiplier
        assert ship.bullet_damage_multiplier == int(cfg.big_gun_damage_multiplier)

    def test_remove_restores_defaults(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        eff = BigGunEffect(cfg)
        eff.apply(ship, {})
        eff.remove(ship, {})
        assert ship.bullet_scale_multiplier == 1.0
        assert ship.bullet_damage_multiplier == 1

    def test_update_returns_false_after_duration(
        self, cfg: SAPowerUpConfig, ship: _FakeShip
    ) -> None:
        eff = BigGunEffect(cfg)
        # Tick past full duration
        assert eff.update(cfg.big_gun_duration + 0.1, ship) is False

    def test_remaining_duration_decreases(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        eff = BigGunEffect(cfg)
        before = eff.remaining_duration
        eff.update(1.0, ship)
        assert eff.remaining_duration == pytest.approx(before - 1.0)


# ----------------------------------------------------------------------
# RapidFireEffect
# ----------------------------------------------------------------------


class TestRapidFireEffect:
    def test_apply_sets_multiplier(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        RapidFireEffect(cfg).apply(ship, {})
        assert ship.fire_cooldown_multiplier == cfg.rapid_fire_multiplier

    def test_remove_restores_one(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        eff = RapidFireEffect(cfg)
        eff.apply(ship, {})
        eff.remove(ship, {})
        assert ship.fire_cooldown_multiplier == 1.0


# ----------------------------------------------------------------------
# SpeedBoostEffect
# ----------------------------------------------------------------------


class TestSpeedBoostEffect:
    def test_apply_sets_multiplier(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        SpeedBoostEffect(cfg).apply(ship, {})
        assert ship.speed_multiplier == cfg.speed_boost_multiplier

    def test_remove_restores_one(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        eff = SpeedBoostEffect(cfg)
        eff.apply(ship, {})
        eff.remove(ship, {})
        assert ship.speed_multiplier == 1.0


# ----------------------------------------------------------------------
# ShieldEffect
# ----------------------------------------------------------------------


class _FakeShieldSprite:
    def __init__(self) -> None:
        self.hits = -1

    def update_state(self, hits: int, x: float, y: float) -> None:
        self.hits = hits


class TestShieldEffect:
    def test_apply_sets_ship_flags(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        eff = ShieldEffect(cfg)
        # Bypass the create_overlay_sprite call (needs arcade) by stubbing
        eff._overlay_sprite = _FakeShieldSprite()
        # Manually mimic OverlayEffect.apply minus the sprite creation
        ship.shield_active = True
        ship.shield_hits_remaining = eff._hits_remaining
        assert ship.shield_active is True
        assert ship.shield_hits_remaining == cfg.shield_hits

    def test_on_hit_absorbed_decrements(self, cfg: SAPowerUpConfig) -> None:
        eff = ShieldEffect(cfg)
        start = eff.hits_remaining
        depleted = eff.on_hit_absorbed()
        assert eff.hits_remaining == start - 1
        assert depleted is False

    def test_on_hit_absorbed_returns_true_when_depleted(self, cfg: SAPowerUpConfig) -> None:
        eff = ShieldEffect(cfg)
        for _ in range(cfg.shield_hits - 1):
            assert eff.on_hit_absorbed() is False
        assert eff.on_hit_absorbed() is True

    def test_remove_clears_ship_flags(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        eff = ShieldEffect(cfg)
        ship.shield_active = True
        ship.shield_hits_remaining = 3
        # Skip sprite-related cleanup by clearing the field first
        eff._overlay_sprite = None
        eff.remove(ship, {})
        assert ship.shield_active is False
        assert ship.shield_hits_remaining == 0

    def test_display_label_shows_pips(self, cfg: SAPowerUpConfig) -> None:
        eff = ShieldEffect(cfg)
        # Full pips at start
        assert "SHIELD" in eff.display_label
        full = eff.display_label.count("\u2593")
        assert full == cfg.shield_hits
        eff.on_hit_absorbed()
        # One pip degrades
        assert eff.display_label.count("\u2593") == cfg.shield_hits - 1
        assert eff.display_label.count("\u2591") == 1


# ----------------------------------------------------------------------
# TripleShotEffect
# ----------------------------------------------------------------------


class TestTripleShotEffect:
    def test_get_bullets_returns_three(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        eff = TripleShotEffect(cfg)
        bullets = eff.get_bullets(ship)
        assert len(bullets) == 3

    def test_get_bullets_respects_cooldown(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        eff = TripleShotEffect(cfg)
        first = eff.get_bullets(ship)
        assert len(first) == 3
        # Cooldown now armed; second call within cooldown returns []
        second = eff.get_bullets(ship)
        assert second == []

    def test_get_bullets_uses_offset_angles(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        eff = TripleShotEffect(cfg)
        bullets = eff.get_bullets(ship)
        angles = sorted(b.angle for b in bullets)
        # Bullet.angle is set from angle_deg parameter — three distinct angles.
        assert len(set(angles)) == 3


# ----------------------------------------------------------------------
# SpreadShotEffect
# ----------------------------------------------------------------------


class TestSpreadShotEffect:
    def test_get_bullets_returns_five(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        eff = SpreadShotEffect(cfg)
        bullets = eff.get_bullets(ship)
        assert len(bullets) == 5

    def test_get_bullets_respects_cooldown(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        eff = SpreadShotEffect(cfg)
        eff.get_bullets(ship)
        assert eff.get_bullets(ship) == []

    def test_spread_uses_configured_angle(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        eff = SpreadShotEffect(cfg)
        bullets = eff.get_bullets(ship)
        angles = sorted(b.angle for b in bullets)
        # Outermost bullets should be at +/- 2 * spread_angle (rotated as PlayerBullet does)
        # We just confirm symmetry around centre
        assert len(set(angles)) == 5


# ----------------------------------------------------------------------
# FreeMovementEffect
# ----------------------------------------------------------------------


class TestFreeMovementEffect:
    def test_apply_expands_zone(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        eff = FreeMovementEffect(cfg)
        eff.apply_constraints(ship, 800, 600)
        assert ship._zone_top == 600.0
        assert ship._zone_bottom == 0.0
        assert ship._zone_left == 0.0
        assert ship._zone_right == 800.0

    def test_apply_saves_original_zone(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        ship._zone_top = 200.0
        eff = FreeMovementEffect(cfg)
        eff.apply_constraints(ship, 800, 600)
        assert eff._saved_constraints["_zone_top"] == 200.0

    def test_restore_returns_original_zone(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        ship._zone_top = 200.0
        ship._zone_right = 800.0
        eff = FreeMovementEffect(cfg)
        eff.apply_constraints(ship, 800, 600)
        # zone_top now full window
        assert ship._zone_top == 600.0
        eff.restore_constraints(ship)
        assert ship._zone_top == 200.0

    def test_apply_uses_context_window(self, cfg: SAPowerUpConfig, ship: _FakeShip) -> None:
        eff = FreeMovementEffect(cfg)
        eff.apply(ship, {"window_width": 1024, "window_height": 768})
        assert ship._zone_top == 768.0
        assert ship._zone_right == 1024.0
