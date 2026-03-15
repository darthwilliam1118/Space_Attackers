"""Spawn safety — adjusts enemy positions before a player respawns."""

from __future__ import annotations

import math
from typing import Any


def apply_spawn_safety(
    snapshot: dict[str, Any],
    ship_spawn_pos: tuple[float, float],
    safe_radius: float = 80.0,
) -> None:
    """Mutate *snapshot* so no enemy overlaps the ship spawn zone.

    Rules applied in order:
    1. Enemies in a dive animation are snapped back to formation position.
    2. Any enemy within *safe_radius* of *ship_spawn_pos* is nudged to the
       nearest point just outside the radius, preserving direction.

    The snapshot dict is expected to contain:
        enemies: list of dicts with keys:
            "pos"      — [x, y] current position
            "formation_pos" — [x, y] home formation position
            "diving"   — bool, True if mid-dive animation
    Projectiles are NOT present (they are stripped before this is called).
    """
    enemies: list[dict[str, Any]] = snapshot.get("enemies", [])
    sx, sy = ship_spawn_pos

    for enemy in enemies:
        # Rule 1 — snap diving enemies back to formation
        if enemy.get("diving", False):
            fp = enemy.get("formation_pos")
            if fp is not None:
                enemy["pos"] = list(fp)
            enemy["diving"] = False

        # Rule 2 — push enemies outside the safe radius
        ex, ey = enemy["pos"]
        dx = ex - sx
        dy = ey - sy
        dist = math.hypot(dx, dy)

        if dist < safe_radius:
            if dist == 0.0:
                # Enemy is exactly on spawn point — push straight up
                dx, dy, dist = 0.0, 1.0, 1.0
            scale = safe_radius / dist
            enemy["pos"] = [sx + dx * scale, sy + dy * scale]
