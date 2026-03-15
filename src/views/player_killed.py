"""PLAYER_KILLED — decrements lives and applies the 2-player decision table."""

from __future__ import annotations

from typing import TYPE_CHECKING

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

_DISPLAY_DURATION = 2.0


class PlayerKilledView(arcade.View):
    """Decrements the active player's lives, then routes per the decision table."""

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__()
        self._manager = manager
        self._elapsed: float = 0.0
        self._next_state, self._next_ctx = self._resolve_next()

    def _resolve_next(self):  # type: ignore[return]
        from src.state import GameState

        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        num_players = len(players)

        if not players:
            return GameState.GAME_OVER, {}

        player = players[idx]
        player.lives -= 1

        other_alive = any(p.is_alive for p in players if p.player_num != player.player_num)

        if player.lives > 0 and num_players == 1:
            return GameState.SET_ACTIVE_PLAYER, {}

        if player.lives > 0 and num_players > 1:
            return GameState.SAVE_SNAPSHOT_AND_SWITCH, {}

        if player.lives <= 0 and other_alive:
            player.is_alive = False
            return GameState.DROP_TO_1P, {}

        # lives <= 0, both dead
        player.is_alive = False
        return GameState.GAME_OVER, {}

    def on_update(self, delta_time: float) -> None:
        self._elapsed += delta_time
        if self._elapsed >= _DISPLAY_DURATION:
            self._manager.transition(self._next_state, **self._manager.context)

    def on_draw(self) -> None:
        self.clear()
        width = self.window.width
        height = self.window.height

        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        label = f"Player {players[idx].player_num}" if players else "Player"

        arcade.draw_text(
            f"{label} DESTROYED!",
            width / 2,
            height / 2 + 40,
            arcade.color.RED,
            font_size=42,
            anchor_x="center",
            bold=True,
        )

        if players:
            player = players[idx]
            arcade.draw_text(
                f"Lives remaining: {player.lives}",
                width / 2,
                height / 2 - 20,
                arcade.color.WHITE,
                font_size=22,
                anchor_x="center",
            )
