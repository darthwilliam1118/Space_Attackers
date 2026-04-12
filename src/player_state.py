"""PlayerState — per-player data carried across the entire game session."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlayerState:
    player_num: int  # 1 or 2
    lives: int  # remaining lives
    score: int = 0
    current_level: int = 1
    level_snapshot: Optional[dict] = field(default=None)  # None = fresh level
    is_alive: bool = True
    current_hp: Optional[int] = None  # None = restore to max on next spawn
