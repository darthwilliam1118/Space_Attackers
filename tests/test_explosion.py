"""Unit tests for ExplosionSprite — no display required."""

from __future__ import annotations

import arcade
import pytest

from src.sprites.explosion import ExplosionSprite


def _make_texture(name: str) -> arcade.Texture:
    return arcade.Texture.create_empty(name, (64, 64))


def _frames(n: int) -> list[arcade.Texture]:
    return [_make_texture(f"f{i}") for i in range(n)]


class TestExplosionFrameOrder:
    def test_single_frame_sequence(self) -> None:
        frames = _frames(1)
        exp = ExplosionSprite(0, 0, frames=frames)
        # Only one frame, no ping-pong extension.
        assert len(exp._frames) == 1

    def test_ping_pong_sequence_length(self) -> None:
        # 4 base frames → reversed → ping-pong = 2n-1 = 7
        frames = _frames(4)
        exp = ExplosionSprite(0, 0, frames=frames)
        assert len(exp._frames) == 7

    def test_ping_pong_starts_at_first_reversed_frame(self) -> None:
        # Frames passed in as [f0,f1,f2,f3]. ExplosionSprite reverses them so
        # index-0 = f3 (smallest per spec: bottom-right = smallest, reversed).
        frames = _frames(4)
        exp = ExplosionSprite(0, 0, frames=frames)
        assert exp._frames[0] == frames[3]

    def test_ping_pong_ends_at_smallest_frame(self) -> None:
        # Full ping-pong returns to smallest: last frame == first frame == f3.
        frames = _frames(4)
        exp = ExplosionSprite(0, 0, frames=frames)
        assert exp._frames[-1] == frames[3]


class TestExplosionLifecycle:
    def test_not_complete_at_start(self) -> None:
        exp = ExplosionSprite(0, 0, frames=_frames(3))
        assert not exp.is_complete

    def test_complete_after_full_cycle(self) -> None:
        exp = ExplosionSprite(0, 0, frame_duration=0.1, frames=_frames(3))
        total_frames = len(exp._frames)
        for _ in range(total_frames):
            exp.update(0.1)
        assert exp.is_complete

    def test_not_complete_mid_animation(self) -> None:
        exp = ExplosionSprite(0, 0, frame_duration=0.1, frames=_frames(4))
        # Advance only half the frames.
        for _ in range(len(exp._frames) // 2):
            exp.update(0.1)
        assert not exp.is_complete

    def test_position_set_correctly(self) -> None:
        exp = ExplosionSprite(123.0, 456.0, frames=_frames(2))
        assert exp.center_x == pytest.approx(123.0)
        assert exp.center_y == pytest.approx(456.0)
