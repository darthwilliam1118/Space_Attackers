"""Unit tests for ProceduralStarField — no display required."""

from __future__ import annotations

import pytest

from src.background import ProceduralStarField

W, H = 800, 600
_SENTINEL = object()  # passed as _sprites to skip OpenGL init


def _make(star_count: int = 20, speed_min: float = 20.0, speed_max: float = 120.0) -> ProceduralStarField:
    return ProceduralStarField(W, H, star_count=star_count, speed_min=speed_min,
                               speed_max=speed_max, _sprites=_SENTINEL)


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
        for i in range(5):
            sf._speed_list[i] = 100.0
            sf._y[i] = 300.0

        sf.update(0.1)

        for y in sf._y:
            assert y == pytest.approx(300.0 - 100.0 * 0.1)

    def test_stars_wrap_at_bottom(self) -> None:
        sf = _make(star_count=3)
        sf._y[0] = 1.0
        sf._speed_list[0] = 500.0

        sf.update(0.1)  # moves to 1 - 50 = -49 → wraps

        assert sf._y[0] == pytest.approx(float(H))

    def test_wrapped_star_gets_new_x(self) -> None:
        sf = _make(star_count=3)
        new_xs: set[float] = set()
        for _ in range(20):
            sf._y[0] = 1.0
            sf.update(0.1)
            new_xs.add(sf._x[0])
        # Randomness means we should see more than one distinct x value
        assert len(new_xs) > 1

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

    def test_non_wrapping_stars_unaffected_by_others(self) -> None:
        sf = _make(star_count=2)
        sf._y[0] = 1.0
        sf._speed_list[0] = 500.0  # will wrap
        sf._y[1] = 400.0
        sf._speed_list[1] = 10.0   # will not wrap

        sf.update(0.1)

        assert sf._y[0] == pytest.approx(float(H))  # wrapped
        assert sf._y[1] == pytest.approx(400.0 - 10.0 * 0.1)  # just moved
