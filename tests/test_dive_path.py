"""Unit tests for dive_path.py — no display required (pure math)."""

from __future__ import annotations

import pytest

from src.dive_path import bezier_point, make_dive_path

W, H = 800, 1000


class TestBezierPoint:
    def test_returns_p0_at_t0(self) -> None:
        p0, p1, p2, p3 = (0.0, 0.0), (100.0, 200.0), (300.0, 400.0), (500.0, 0.0)
        result = bezier_point(p0, p1, p2, p3, 0.0)
        assert result == pytest.approx(p0)

    def test_returns_p3_at_t1(self) -> None:
        p0, p1, p2, p3 = (0.0, 0.0), (100.0, 200.0), (300.0, 400.0), (500.0, 0.0)
        result = bezier_point(p0, p1, p2, p3, 1.0)
        assert result == pytest.approx(p3)

    def test_midpoint_between_p0_and_p3(self) -> None:
        p0 = (0.0, 0.0)
        p3 = (100.0, 0.0)
        # With all points collinear, midpoint should be between p0 and p3
        p1 = (33.0, 0.0)
        p2 = (66.0, 0.0)
        result = bezier_point(p0, p1, p2, p3, 0.5)
        # x must be between 0 and 100
        assert 0.0 < result[0] < 100.0


class TestMakeDivePath:
    def test_returns_correct_length(self) -> None:
        path = make_dive_path(
            start=(400.0, 800.0),
            player_x=400.0,
            window_height=H,
            window_width=W,
            num_waypoints=120,
        )
        assert len(path) == 120

    def test_first_waypoint_equals_start(self) -> None:
        start = (400.0, 800.0)
        path = make_dive_path(start, player_x=400.0, window_height=H, window_width=W)
        assert path[0] == pytest.approx(start, abs=1e-6)

    def test_last_waypoint_equals_start(self) -> None:
        start = (400.0, 800.0)
        path = make_dive_path(start, player_x=400.0, window_height=H, window_width=W)
        assert path[-1] == pytest.approx(start, abs=1e-6)

    def test_waypoints_reach_below_midscreen(self) -> None:
        start = (400.0, 800.0)
        path = make_dive_path(start, player_x=400.0, window_height=H, window_width=W)
        min_y = min(pt[1] for pt in path)
        # The path must dip below window_height * 0.55 to trigger bomb
        assert min_y < H * 0.55

    def test_custom_num_waypoints(self) -> None:
        path = make_dive_path(
            start=(200.0, 700.0),
            player_x=300.0,
            window_height=H,
            window_width=W,
            num_waypoints=60,
        )
        assert len(path) == 60

    def test_curve_sign_affects_horizontal_offset(self) -> None:
        """Positive and negative curve_sign should produce mirrored arcs."""
        start = (400.0, 800.0)
        import random
        rng_state = random.getstate()

        random.seed(42)
        path_pos = make_dive_path(start, 400.0, H, W, curve_sign=1)
        random.seed(42)
        path_neg = make_dive_path(start, 400.0, H, W, curve_sign=-1)

        random.setstate(rng_state)

        # Peak x deviation should be on opposite sides
        deviations_pos = [pt[0] - start[0] for pt in path_pos]
        deviations_neg = [pt[0] - start[0] for pt in path_neg]
        assert max(deviations_pos) > 0
        assert min(deviations_neg) < 0
