"""Unit tests for PlayerShip — no display required."""

from __future__ import annotations

import arcade
import pytest

from src.ship_config import ShipConfig
from src.sprites.player_ship import PlayerShip
from src.sprites.explosion import ExplosionSprite


W, H = 800, 600


def _texture() -> arcade.Texture:
    return arcade.Texture.create_empty("ship", (60, 48))


def _ship(player_num: int = 1, **cfg_kwargs) -> PlayerShip:
    cfg = ShipConfig(**cfg_kwargs)
    return PlayerShip(player_num=player_num, config=cfg, window_width=W, window_height=H, texture=_texture())


class TestSpawnPosition:
    def test_spawns_at_horizontal_centre(self) -> None:
        s = _ship()
        assert s.center_x == pytest.approx(W / 2.0)

    def test_spawns_in_bottom_zone(self) -> None:
        s = _ship(ship_zone_height_pct=0.20)
        zone_top = H * 0.20
        assert s.center_y <= zone_top

    def test_spawn_position_changes_with_zone_pct(self) -> None:
        s1 = _ship(ship_zone_height_pct=0.20)
        s2 = _ship(ship_zone_height_pct=0.30)
        assert s2.center_y > s1.center_y


class TestMovementClamping:
    def test_clamp_left_boundary(self) -> None:
        s = _ship()
        s.center_x = 0.0
        s.apply_movement({arcade.key.LEFT}, delta_time=1.0)
        assert s.center_x >= 0

    def test_clamp_right_boundary(self) -> None:
        s = _ship()
        s.center_x = W
        s.apply_movement({arcade.key.RIGHT}, delta_time=1.0)
        assert s.center_x <= W

    def test_clamp_top_boundary(self) -> None:
        s = _ship(ship_zone_height_pct=0.20)
        s.center_y = H * 0.20
        s.apply_movement({arcade.key.UP}, delta_time=1.0)
        assert s.center_y <= H * 0.20

    def test_clamp_bottom_boundary(self) -> None:
        s = _ship()
        s.center_y = 0.0
        s.apply_movement({arcade.key.DOWN}, delta_time=1.0)
        assert s.center_y >= 0

    def test_movement_delta_time_scaled(self) -> None:
        s1 = _ship(ship_speed=200)
        s2 = _ship(ship_speed=200)
        s1.center_x = W / 2
        s2.center_x = W / 2
        s1.apply_movement({arcade.key.RIGHT}, delta_time=0.1)
        s2.apply_movement({arcade.key.RIGHT}, delta_time=0.2)
        assert s2.center_x - W / 2 == pytest.approx(2 * (s1.center_x - W / 2))

    def test_wasd_keys_move_ship(self) -> None:
        s = _ship(ship_speed=200)
        start_x = s.center_x
        s.apply_movement({arcade.key.D}, delta_time=0.1)
        assert s.center_x > start_x


class TestFiring:
    def test_fire_returns_bullet_when_ready(self) -> None:
        s = _ship(fire_cooldown=0.3, spawn_invincible_duration=0.0)
        # Drain cooldown from spawn invincibility period (none here).
        s._fire_cooldown_remaining = 0.0
        bullet = s.try_fire(H)
        assert bullet is not None

    def test_fire_returns_none_during_cooldown(self) -> None:
        s = _ship(fire_cooldown=0.3)
        s._fire_cooldown_remaining = 0.0
        s.try_fire(H)  # first shot — starts cooldown
        bullet = s.try_fire(H)  # immediate second — should be None
        assert bullet is None

    def test_fire_returns_bullet_after_cooldown_expires(self) -> None:
        s = _ship(fire_cooldown=0.3)
        s._fire_cooldown_remaining = 0.0
        s.try_fire(H)
        s.update(0.31)
        bullet = s.try_fire(H)
        assert bullet is not None

    def test_p1_bullet_uses_blue_laser(self) -> None:
        from src.sprites.player_bullet import bullet_path_for
        assert "Blue" in bullet_path_for(1)

    def test_p2_bullet_uses_red_laser(self) -> None:
        from src.sprites.player_bullet import bullet_path_for
        assert "Red" in bullet_path_for(2)


class TestInvincibility:
    def test_invincible_at_spawn(self) -> None:
        s = _ship(spawn_invincible_duration=2.0)
        assert s.is_invincible()

    def test_not_invincible_after_duration(self) -> None:
        s = _ship(spawn_invincible_duration=1.0)
        s.update(1.01)
        assert not s.is_invincible()

    def test_start_invincibility_resets_timer(self) -> None:
        s = _ship(spawn_invincible_duration=2.0)
        s.update(2.1)  # expire it
        assert not s.is_invincible()
        s.start_invincibility()
        assert s.is_invincible()

    def test_flash_toggles_visibility(self) -> None:
        s = _ship(spawn_invincible_duration=2.0)
        initial = s.visible
        s.update(0.11)  # one flash interval (0.1s)
        assert s.visible != initial

    def test_visible_after_invincibility_ends(self) -> None:
        s = _ship(spawn_invincible_duration=0.5)
        for _ in range(20):
            s.update(0.05)
        assert s.visible


class TestKill:
    def test_kill_returns_explosion_at_ship_position(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Prevent disk/display access inside ExplosionSprite by injecting frames.
        dummy_frames = [arcade.Texture.create_empty(f"ex{i}", (64, 64)) for i in range(4)]
        monkeypatch.setattr(
            "src.sprites.explosion.ExplosionSprite._load_frames",
            staticmethod(lambda: dummy_frames),
        )
        s = _ship()
        x, y = s.center_x, s.center_y
        explosion = s.kill()
        assert isinstance(explosion, ExplosionSprite)
        assert explosion.center_x == pytest.approx(x)
        assert explosion.center_y == pytest.approx(y)
