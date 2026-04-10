"""Unit tests for PlayerBullet — no display required."""

from __future__ import annotations

import math

import arcade
import pytest

from src.sprites.player_bullet import PlayerBullet, bullet_path_for

W, H = 800, 600


def _texture() -> arcade.Texture:
    return arcade.Texture.create_empty("bullet", (10, 30))


def _bullet(
    x: float = 100, y: float = 50, speed: float = 500, angle_deg: float = 0.0
) -> PlayerBullet:
    return PlayerBullet(
        x, y, speed=speed, window_width=W, window_height=H, angle_deg=angle_deg, texture=_texture()
    )


class TestBulletPaths:
    def test_player1_path(self) -> None:
        assert "laserBlue01" in bullet_path_for(1)

    def test_player2_path(self) -> None:
        assert "laserRed01" in bullet_path_for(2)

    def test_unknown_player_falls_back_to_p1(self) -> None:
        assert "laserBlue01" in bullet_path_for(99)


class TestBulletMovement:
    def test_moves_straight_up_at_zero_angle(self) -> None:
        b = _bullet(angle_deg=0.0)
        b.update(0.1)
        assert b.center_y == pytest.approx(50 + 500 * 0.1)
        assert b.center_x == pytest.approx(100.0)

    def test_angled_right_has_positive_vx(self) -> None:
        b = _bullet(angle_deg=45.0)
        start_x = b.center_x
        b.update(0.1)
        assert b.center_x > start_x

    def test_angled_left_has_negative_vx(self) -> None:
        b = _bullet(angle_deg=-45.0)
        start_x = b.center_x
        b.update(0.1)
        assert b.center_x < start_x

    def test_45_degree_components_equal(self) -> None:
        speed = 500.0
        b = _bullet(speed=speed, angle_deg=45.0)
        b.update(1.0)
        expected = speed * math.sin(math.radians(45.0))
        assert b.center_x - 100 == pytest.approx(expected)
        assert b.center_y - 50 == pytest.approx(expected)

    def test_delta_time_scaled(self) -> None:
        start_y = 50.0
        b1 = _bullet()
        b2 = _bullet()
        b1.update(0.05)
        b2.update(0.10)
        assert b2.center_y - start_y == pytest.approx(2 * (b1.center_y - start_y))

    def test_sprite_angle_matches_tilt(self) -> None:
        b = _bullet(angle_deg=30.0)
        assert b.angle == pytest.approx(30.0)


class TestBulletRemoval:
    def _in_list(self, b: PlayerBullet) -> bool:
        sl = arcade.SpriteList()
        sl.append(b)
        b.update(1.0)
        return b in sl

    def test_removes_at_top(self) -> None:
        assert not self._in_list(_bullet(y=H - 1, speed=500))

    def test_removes_at_bottom(self) -> None:
        assert not self._in_list(_bullet(y=1, speed=-500))

    def test_removes_at_right(self) -> None:
        assert not self._in_list(_bullet(x=W - 1, angle_deg=89.0, speed=500))

    def test_removes_at_left(self) -> None:
        assert not self._in_list(_bullet(x=1, angle_deg=-89.0, speed=500))
