"""dive_path.py — Bézier path generation for diving ships.

Pure math module: no Arcade dependencies, fully unit-testable without a display.
"""

from __future__ import annotations

import random


def bezier_point(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    """Evaluate a cubic Bézier curve at parameter *t* (0.0 → 1.0).

    Uses the standard formula:
        B(t) = (1-t)³·P0 + 3(1-t)²t·P1 + 3(1-t)t²·P2 + t³·P3
    """
    u = 1.0 - t
    x = (u ** 3) * p0[0] + 3 * (u ** 2) * t * p1[0] + 3 * u * (t ** 2) * p2[0] + (t ** 3) * p3[0]
    y = (u ** 3) * p0[1] + 3 * (u ** 2) * t * p1[1] + 3 * u * (t ** 2) * p2[1] + (t ** 3) * p3[1]
    return (x, y)


def make_dive_path(
    start: tuple[float, float],
    player_x: float,
    window_height: int,
    window_width: int,
    num_waypoints: int = 120,
    curve_sign: int = 1,
) -> list[tuple[float, float]]:
    """Generate a cubic Bézier arc as a list of (x, y) waypoints.

    The path leaves *start*, swoops down toward the player at the bottom of
    the screen, then arcs back up to *start* — a full loop.

    Control points:
      P0 = start
      P1 = (start_x + curve_sign * offset, start_y - window_height * 0.3)
           pulls the curve sideways early in the descent
      P2 = (player_x, window_height * 0.25)
           aims toward the player in the lower portion of the screen
      P3 = start  (path returns to origin)

    Args:
        start:          Grid position of the ship (its home position).
        player_x:       Player's current x coordinate at launch time.
        window_height:  Window height in pixels.
        window_width:   Window width in pixels (unused currently, kept for API consistency).
        num_waypoints:  Number of evenly-spaced t samples (default 120 ≈ 2 s at 60 fps).
        curve_sign:     +1 curves right, -1 curves left. Pass the same sign for all
                        ships in a group so they fan together visually.

    Returns:
        List of ``num_waypoints`` (x, y) tuples from P0 to P3.
    """
    offset = random.uniform(120.0, 200.0)

    p0 = start
    p1 = (start[0] + curve_sign * offset, start[1] - window_height * 0.3)
    p2 = (player_x, window_height * 0.25)
    p3 = start

    waypoints: list[tuple[float, float]] = []
    for i in range(num_waypoints):
        t = i / (num_waypoints - 1)
        waypoints.append(bezier_point(p0, p1, p2, p3, t))

    return waypoints
