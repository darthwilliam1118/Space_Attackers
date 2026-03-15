"""Tests for apply_spawn_safety() — no display required."""

import math

import pytest

from src.spawn_safety import apply_spawn_safety

SPAWN = (400.0, 60.0)
RADIUS = 80.0


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _enemy(x: float, y: float, *, diving: bool = False) -> dict:
    return {
        "pos": [x, y],
        "formation_pos": [x, y + 100],  # formation is 100px above current
        "diving": diving,
    }


def _dist(enemy: dict, spawn: tuple[float, float]) -> float:
    ex, ey = enemy["pos"]
    return math.hypot(ex - spawn[0], ey - spawn[1])


# ---------------------------------------------------------------------------
# Edge case: no enemies
# ---------------------------------------------------------------------------

def test_no_enemies_is_noop() -> None:
    snapshot: dict = {"enemies": []}
    apply_spawn_safety(snapshot, SPAWN, RADIUS)
    assert snapshot["enemies"] == []


# ---------------------------------------------------------------------------
# Rule 2: enemies outside radius are untouched
# ---------------------------------------------------------------------------

def test_enemy_outside_radius_unchanged() -> None:
    e = _enemy(SPAWN[0] + RADIUS + 10, SPAWN[1])
    snapshot = {"enemies": [e]}
    original_pos = list(e["pos"])
    apply_spawn_safety(snapshot, SPAWN, RADIUS)
    assert e["pos"] == original_pos


# ---------------------------------------------------------------------------
# Rule 2: enemies inside radius are nudged out
# ---------------------------------------------------------------------------

def test_enemy_inside_radius_pushed_out() -> None:
    e = _enemy(SPAWN[0] + 10, SPAWN[1] + 10)
    snapshot = {"enemies": [e]}
    apply_spawn_safety(snapshot, SPAWN, RADIUS)
    assert _dist(e, SPAWN) >= RADIUS - 1e-9


def test_all_enemies_inside_radius_pushed_out() -> None:
    enemies = [
        _enemy(SPAWN[0] + d, SPAWN[1]) for d in [5, 15, 30, 50, 70]
    ]
    snapshot = {"enemies": enemies}
    apply_spawn_safety(snapshot, SPAWN, RADIUS)
    for e in enemies:
        assert _dist(e, SPAWN) >= RADIUS - 1e-9


def test_enemy_exactly_on_spawn_pushed_up() -> None:
    e = _enemy(SPAWN[0], SPAWN[1])
    snapshot = {"enemies": [e]}
    apply_spawn_safety(snapshot, SPAWN, RADIUS)
    assert _dist(e, SPAWN) >= RADIUS - 1e-9
    # Should be pushed straight up (dy positive)
    assert e["pos"][1] > SPAWN[1]


# ---------------------------------------------------------------------------
# Rule 1: diving enemy snapped to formation before distance check
# ---------------------------------------------------------------------------

def test_diving_enemy_snapped_to_formation() -> None:
    # Enemy is close to spawn while diving; formation_pos is safe
    e = _enemy(SPAWN[0] + 5, SPAWN[1] + 5, diving=True)
    e["formation_pos"] = [SPAWN[0] + 200, SPAWN[1] + 200]  # safely outside
    snapshot = {"enemies": [e]}
    apply_spawn_safety(snapshot, SPAWN, RADIUS)
    assert e["diving"] is False
    assert e["pos"] == [SPAWN[0] + 200, SPAWN[1] + 200]


def test_diving_enemy_snapped_then_still_pushed_if_formation_inside_radius() -> None:
    # Formation position is also inside radius — must be pushed out further
    e = _enemy(SPAWN[0] + 5, SPAWN[1] + 5, diving=True)
    e["formation_pos"] = [SPAWN[0] + 10, SPAWN[1]]  # inside radius
    snapshot = {"enemies": [e]}
    apply_spawn_safety(snapshot, SPAWN, RADIUS)
    assert e["diving"] is False
    assert _dist(e, SPAWN) >= RADIUS - 1e-9


# ---------------------------------------------------------------------------
# Projectiles are NOT in snapshot (stripped before call) — no interference
# ---------------------------------------------------------------------------

def test_snapshot_without_projectiles_key() -> None:
    e = _enemy(SPAWN[0] + 200, SPAWN[1] + 200)
    snapshot = {"enemies": [e]}  # no "projectiles" key
    apply_spawn_safety(snapshot, SPAWN, RADIUS)  # must not raise
