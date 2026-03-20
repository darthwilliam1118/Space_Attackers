"""Unit tests for ProceduralStarField — no display required."""

from __future__ import annotations

import pytest

from src.background import ProceduralStarField

W, H = 800, 600
_SENTINEL = object()  # passed as _shape_list to skip OpenGL init


def _make(star_count: int = 20, speed_min: float = 20.0, speed_max: float = 120.0) -> ProceduralStarField:
    return ProceduralStarField(W, H, star_count=star_count, speed_min=speed_min,
                               speed_max=speed_max, _shape_list=_SENTINEL)


class TestInit:
    def test_star_count_correct(self) -> None:
        sf = _make(star_count=50)
        assert len(sf._x) == 50
        assert len(sf._y) == 50
        assert len(sf._speed_list) == 50

    def test_all_speeds_in_range(self) -> None:
        sf = _make(star_count=100, speed_min=30.0, speed_max=90.0)
        assert all(30.0 <= s <= 90.0 for s in sf._speed_list)

    def test_all_positions_within_window(self) -> None:
        sf = _make(star_count=100)
        assert all(0 <= x <= W for x in sf._x)
        assert all(0 <= y <= H for y in sf._y)


class TestUpdate:
    def test_moves_stars_downward(self) -> None:
        sf = _make(star_count=5)
        # Pin all speeds to a known value and all y far from edges
        for i in range(5):
            sf._speed_list[i] = 100.0
            sf._y[i] = 300.0

        sf.update(0.1)

        for y in sf._y:
            assert y == pytest.approx(300.0 - 100.0 * 0.1)

    def test_stars_wrap_at_bottom(self) -> None:
        sf = _make(star_count=3)
        # Place one star just above zero, fast enough to cross in one step
        sf._y[0] = 1.0
        sf._speed_list[0] = 500.0

        sf.update(0.1)  # moves to 1 - 50 = -49 → wraps

        assert sf._y[0] == pytest.approx(float(H))

    def test_wrapped_star_gets_new_x(self) -> None:
        sf = _make(star_count=3)
        sf._y[0] = 1.0
        sf._speed_list[0] = 500.0
        # Run many times; x should not be stuck at the original value every time
        original_x = sf._x[0]
        new_xs: set[float] = set()
        for _ in range(20):
            sf._y[0] = 1.0  # force wrap every iteration
            sf.update(0.1)
            new_xs.add(sf._x[0])
        # At least one new x should differ from the original
        assert any(x != pytest.approx(original_x) for x in new_xs)

    def test_wrapped_x_stays_within_window(self) -> None:
        sf = _make(star_count=1)
        for _ in range(30):
            sf._y[0] = 1.0
            sf.update(0.1)
            assert 0 <= sf._x[0] <= W

    def test_delta_time_scaled(self) -> None:
        sf1 = _make(star_count=1)
        sf2 = _make(star_count=1)
        sf1._speed_list[0] = 100.0
        sf2._speed_list[0] = 100.0
        sf1._y[0] = 500.0
        sf2._y[0] = 500.0

        sf1.update(0.05)
        sf2.update(0.10)

        drop1 = 500.0 - sf1._y[0]
        drop2 = 500.0 - sf2._y[0]
        assert drop2 == pytest.approx(2 * drop1)


class TestRebuild:
    def test_rebuild_called_on_wrap(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sf = _make(star_count=3)
        sf._y[0] = 1.0
        sf._speed_list[0] = 500.0

        calls: list[int] = []
        monkeypatch.setattr(sf, "_rebuild", lambda: calls.append(1))

        sf.update(0.1)  # star 0 wraps

        assert calls, "_rebuild should have been called on wrap"

    def test_rebuild_not_called_without_wrap(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sf = _make(star_count=5)
        # Push all stars safely away from the bottom
        for i in range(5):
            sf._y[i] = 400.0
            sf._speed_list[i] = 10.0  # slow — won't reach 0 in 0.01s

        calls: list[int] = []
        monkeypatch.setattr(sf, "_rebuild", lambda: calls.append(1))

        sf.update(0.01)

        assert not calls, "_rebuild should not be called when no star wraps"
