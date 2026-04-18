"""SA power-up type identifiers."""

from __future__ import annotations

from enum import Enum


class SAPowerUpType(Enum):
    HEALTH = "health"
    SHIELD = "shield"
    RAPID_FIRE = "rapid_fire"
    BIG_GUN = "big_gun"
    SPEED_BOOST = "speed_boost"
    TRIPLE_SHOT = "triple_shot"
    SPREAD_SHOT = "spread_shot"
    FREE_MOVE = "free_move"
