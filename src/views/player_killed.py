"""PLAYER_KILLED — decrements lives and applies the 2-player decision table."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

from src.ui.text_utils import FONT_MAIN, FONT_THIN, centered_text

_DISPLAY_DURATION = 2.0


class PlayerKilledView(arcade.View):
    """Decrements the active player's lives, then routes per the decision table."""

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__()
        self._manager = manager
        self._elapsed: float = 0.0
        self._next_state, self._next_ctx = self._resolve_next()

        self._destroyed_text: Optional[arcade.Text] = None
        self._lives_text: Optional[arcade.Text] = None

    def _resolve_next(self):  # type: ignore[return]
        from src.state import GameState

        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        num_players = len(players)

        if not players:
            return GameState.GAME_OVER, {}

        player = players[idx]
        player.lives -= 1
        player.current_hp = None  # new life restores HP to max

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

    def on_show_view(self) -> None:
        self.window.music.play("ending")  # type: ignore[attr-defined]
        w, h = self.window.width, self.window.height
        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        label = f"Player {players[idx].player_num}" if players else "Player"

        self._destroyed_text = centered_text(
            f"{label} DESTROYED!",
            w,
            h // 2 + 40,
            font_size=42,
            color=arcade.color.RED,
            font_name=FONT_MAIN,
            bold=True,
        )

        lives_str = ""
        if players:
            player = players[idx]
            lives_str = f"Lives remaining: {player.lives}"
        self._lives_text = centered_text(
            lives_str,
            w,
            h // 2 - 20,
            font_size=22,
            color=arcade.color.WHITE,
            font_name=FONT_THIN,
        )

    def on_update(self, delta_time: float) -> None:
        from src.state import GameState

        self.window.star_field.update(delta_time)  # type: ignore[attr-defined]

        # Explosion already played in RunLevelView — go straight to GAME_OVER.
        if self._next_state == GameState.GAME_OVER:
            self._manager.transition(GameState.GAME_OVER)
            return

        self._elapsed += delta_time
        if self._elapsed >= _DISPLAY_DURATION:
            self._manager.transition(self._next_state, **self._manager.context)

    def on_draw(self) -> None:
        self.clear()
        self.window.background.draw()  # type: ignore[attr-defined]
        self.window.star_field.draw()  # type: ignore[attr-defined]
        if self._destroyed_text:
            self._destroyed_text.draw()
        if self._lives_text:
            self._lives_text.draw()
