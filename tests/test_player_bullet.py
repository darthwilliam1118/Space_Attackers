"""Unit tests for PlayerBullet — no display required."""

from __future__ import annotations

import arcade
import pytest

from src.sprites.player_bullet import PlayerBullet, bullet_path_for


def _texture() -> arcade.Texture:
    return arcade.Texture.create_empty("bullet", (10, 30))


class TestBulletPaths:
    def test_player1_path(self) -> None:
        assert "laserBlue01" in bullet_path_for(1)

    def test_player2_path(self) -> None:
        assert "laserRed01" in bullet_path_for(2)

    def test_unknown_player_falls_back_to_p1(self) -> None:
        assert "laserBlue01" in bullet_path_for(99)


class TestBulletMovement:
    def test_moves_upward(self) -> None:
        b = PlayerBullet(100, 50, speed=500, window_height=600, texture=_texture())
        b.update(0.1)
        assert b.center_y == pytest.approx(50 + 500 * 0.1)

    def test_delta_time_scaled(self) -> None:
        b1 = PlayerBullet(0, 0, speed=500, window_height=600, texture=_texture())
        b2 = PlayerBullet(0, 0, speed=500, window_height=600, texture=_texture())
        b1.update(0.05)
        b2.update(0.10)
        assert b2.center_y == pytest.approx(2 * b1.center_y)

    def test_removes_when_off_screen(self) -> None:
        b = PlayerBullet(100, 590, speed=500, window_height=600, texture=_texture())
        sprite_list = arcade.SpriteList()
        sprite_list.append(b)
        b.update(1.0)  # will travel far past window_height
        assert b not in sprite_list
