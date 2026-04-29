"""LEVEL_COMPLETE screen — awards bonus, shows lives, advances level."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import arcade
from agf.paths import resource_path
from agf.views.level_complete import LevelCompleteView as _LevelCompleteViewBase

from src.sound_manager import SoundManager

if TYPE_CHECKING:
    from src.state import GameStateManager

_LEVEL_BONUS = 1000
_EXTRA_LIFE_INTERVAL = 10_000
_SND_EXTRA_LIFE = "assets/sounds/extraLife.wav"


class LevelCompleteView(_LevelCompleteViewBase):
    """Awards level bonus, displays remaining lives, then continues."""

    def __init__(self, manager: "GameStateManager") -> None:
        self._manager = manager
        self._snd_extra_life: Optional[arcade.Sound] = arcade.load_sound(
            resource_path(_SND_EXTRA_LIFE)
        )
        self._sm_extra_life = SoundManager(max_simultaneous=1)
        super().__init__(on_complete=self._advance)

    def apply_bonus(self) -> None:
        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        is_meteor = self._manager.context.get("current_level_is_meteor", False)
        is_boss = self._manager.context.get("current_level_is_boss", False)
        if players:
            player = players[idx]
            old_milestones = player.score // _EXTRA_LIFE_INTERVAL
            player.score += _LEVEL_BONUS
            earned = player.score // _EXTRA_LIFE_INTERVAL - old_milestones
            for _ in range(earned):
                player.lives += 1
                if self._snd_extra_life is not None:
                    self._sm_extra_life.play(self._snd_extra_life)
            if not is_meteor and not is_boss:
                old_level = player.current_level
                player.current_level += 1
                if old_level % 5 == 0:
                    # Boss beats meteor when both would fire (e.g. level 15)
                    self._manager.context["pending_boss"] = True
                elif old_level % 3 == 0:
                    self._manager.context["pending_meteor_storm"] = True
            player.level_snapshot = None
            player.current_hp = None  # next level always starts at full HP
        self._manager.context.pop("current_level_is_meteor", None)
        self._manager.context.pop("current_level_is_boss", None)

    def build_bonus_text(self) -> str:
        if self._manager.context.get("current_level_is_boss", False):
            return f"BOSS DEFEATED    Bonus: +{_LEVEL_BONUS}"
        if self._manager.context.get("current_level_is_meteor", False):
            return f"METEOR STORM    Bonus: +{_LEVEL_BONUS}"
        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        level = players[idx].current_level if players else 1
        return f"LEVEL {level}    Bonus: +{_LEVEL_BONUS}"

    def build_player_rows(self) -> list[str]:
        players = self._manager.context.get("players", [])
        return [
            f"Player {p.player_num}:  {p.lives} lives   Score: {p.score}"
            for p in players
            if p.is_alive
        ]

    def _advance(self) -> None:
        from src.state import GameState

        self._manager.transition(GameState.SET_ACTIVE_PLAYER)
