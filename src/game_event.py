"""GameEvent — events returned by EnemyGrid.update() to decouple grid from state machine."""

from __future__ import annotations

from enum import Enum, auto


class GameEvent(Enum):
    PLAYER_KILLED = auto()
    LEVEL_COMPLETE = auto()
    ENEMY_DESTROYED = auto()
