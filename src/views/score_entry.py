"""SCORE_ENTRY view — keyboard name entry and persistent leaderboard display."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

from src.high_scores import HighScoreTable, scores_path
from src.ui.text_utils import FONT_MAIN, FONT_THIN, centered_text

_DONE_DURATION = 3.0
_CURSOR_BLINK = 0.5  # seconds per half-cycle


class ScoreEntryView(arcade.View):
    """Keyboard name entry + leaderboard display.

    State machine:
      entering   — active player is typing their name
      save_error — save failed; waiting for any key to acknowledge
      done       — all entries saved; 3-second countdown then → MAIN
    """

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__()
        self._manager = manager
        self._table: Optional[HighScoreTable] = None
        self._pending: list = []
        self._name: str = ""
        self._state: str = "entering"
        self._done_timer: float = 0.0
        self._cursor_timer: float = 0.0
        self._new_rank: Optional[int] = None
        self._save_error: Optional[str] = None

        self._title_text: Optional[arcade.Text] = None
        self._entry_rows: list[arcade.Text] = []
        self._prompt_text: Optional[arcade.Text] = None
        self._name_text: Optional[arcade.Text] = None
        self._cursor_text: Optional[arcade.Text] = None
        self._status_text: Optional[arcade.Text] = None
        self._error_line1: Optional[arcade.Text] = None
        self._error_line2: Optional[arcade.Text] = None

    # ------------------------------------------------------------------
    # Arcade callbacks
    # ------------------------------------------------------------------

    def on_show_view(self) -> None:
        self.window.music.play("ending")  # type: ignore[attr-defined]

        # Use pre-loaded table from GameOverView, or load fresh from disk
        self._table = (
            self._manager.context.get("high_score_table")
            or HighScoreTable.load(scores_path())
        )

        players = self._manager.context.get("players", [])
        self._pending = [p for p in players if self._table.qualifies(p.score)]

        self._name = ""
        self._state = "entering" if self._pending else "done"
        self._done_timer = 0.0
        self._cursor_timer = 0.0
        self._new_rank = None

        self._build_layout()

    def on_update(self, delta_time: float) -> None:
        self.window.star_field.update(delta_time)  # type: ignore[attr-defined]
        self._cursor_timer += delta_time

        if self._state == "done":
            self._done_timer += delta_time
            if self._done_timer >= _DONE_DURATION:
                from src.state import GameState
                self._manager.transition(GameState.MAIN)

    def on_draw(self) -> None:
        self.clear()
        self.window.background.draw()  # type: ignore[attr-defined]
        self.window.star_field.draw()  # type: ignore[attr-defined]

        if self._title_text:
            self._title_text.draw()
        for row in self._entry_rows:
            row.draw()

        if self._state == "save_error":
            if self._error_line1:
                self._error_line1.draw()
            if self._error_line2:
                self._error_line2.draw()
            return

        if self._prompt_text:
            self._prompt_text.draw()
        if self._status_text:
            self._status_text.draw()

        if self._state == "entering" and self._name_text and self._cursor_text:
            self._name_text.text = self._name
            self._name_text.draw()
            # Position cursor at the right edge of the centered name
            cursor_x = self.window.width / 2 + self._name_text.content_width / 2
            self._cursor_text.x = cursor_x
            show_cursor = int(self._cursor_timer / _CURSOR_BLINK) % 2 == 0
            r, g, b = arcade.color.GOLD[:3]
            self._cursor_text.color = (r, g, b, 255 if show_cursor else 0)
            self._cursor_text.draw()

    def on_key_press(self, key: int, modifiers: int) -> None:
        if self._state == "save_error":
            self._state = "done"
            self._done_timer = 0.0
            self._refresh_prompt()
            return

        if self._state == "entering":
            self._handle_entry_key(key)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        w, h = self.window.width, self.window.height

        self._title_text = centered_text(
            "HIGH SCORES", w, h - 60,
            font_size=36, color=arcade.color.GOLD, font_name=FONT_MAIN, bold=True,
        )

        top_y = h - 110
        row_h = 28
        self._entry_rows = [
            centered_text(
                "", w, top_y - i * row_h,
                font_size=18, color=arcade.color.WHITE, font_name=FONT_THIN,
            )
            for i in range(HighScoreTable.MAX_ENTRIES)
        ]

        prompt_y = top_y - HighScoreTable.MAX_ENTRIES * row_h - 24
        self._prompt_text = centered_text(
            "", w, prompt_y,
            font_size=16, color=arcade.color.WHITE, font_name=FONT_THIN,
        )
        self._name_text = centered_text(
            "", w, prompt_y - 38,
            font_size=28, color=arcade.color.GOLD, font_name=FONT_MAIN,
        )
        # Cursor drawn separately so centering of the name is unaffected
        self._cursor_text = arcade.Text(
            "_", 0, prompt_y - 38,
            arcade.color.GOLD, 28,
            font_name=FONT_MAIN,
            anchor_x="left",
            anchor_y="center",
        )
        self._status_text = centered_text(
            "", w, prompt_y - 80,
            font_size=13, color=(140, 140, 140, 255), font_name=FONT_THIN,
        )

        mid = h // 2
        self._error_line1 = centered_text(
            "", w, mid + 20,
            font_size=18, color=arcade.color.RED, font_name=FONT_THIN,
        )
        self._error_line2 = centered_text(
            "", w, mid - 20,
            font_size=14, color=arcade.color.WHITE, font_name=FONT_THIN,
        )

        self._refresh_rows()
        self._refresh_prompt()

    def _refresh_rows(self) -> None:
        entries = self._table.entries if self._table else []
        for i, text_obj in enumerate(self._entry_rows):
            rank = i + 1
            if i < len(entries):
                e = entries[i]
                text_obj.text = f"#{rank:<2}  {e.name:<10}  {e.score:>6}"
                text_obj.color = (
                    arcade.color.YELLOW if rank == self._new_rank else arcade.color.WHITE
                )
            else:
                text_obj.text = f"#{rank:<2}  {'---':<10}"
                text_obj.color = (80, 80, 80, 255)

    def _refresh_prompt(self) -> None:
        if self._state == "done":
            if self._prompt_text:
                self._prompt_text.text = ""
            if self._name_text:
                self._name_text.text = ""
            if self._status_text:
                self._status_text.text = "RETURNING TO MENU\u2026"
            return

        if self._state == "entering" and self._pending:
            player = self._pending[0]
            num_players = len(self._manager.context.get("players", []))
            if num_players > 1:
                label = f"PLAYER {player.player_num} \u2014 ENTER YOUR NAME:"
            else:
                label = "ENTER YOUR NAME:"
            if self._prompt_text:
                self._prompt_text.text = label
            if self._status_text:
                self._status_text.text = (
                    "A\u2013Z  0\u20139  SPACE  |  BACKSPACE = delete  |  ENTER = confirm"
                )

    def _handle_entry_key(self, key: int) -> None:
        assert self._table is not None

        if key == arcade.key.BACKSPACE:
            self._name = self._name[:-1]
            return

        if key in (arcade.key.ENTER, arcade.key.RETURN, arcade.key.NUM_ENTER):
            name = self._name.strip()
            if not name:
                return
            player = self._pending.pop(0)
            self._new_rank = self._table.add(name, player.score)
            self._name = ""
            self._refresh_rows()
            if self._pending:
                self._refresh_prompt()
            else:
                err = self._table.save()
                self._manager.context["high_score_table"] = self._table
                if err is None:
                    self._state = "done"
                    self._done_timer = 0.0
                    self._refresh_prompt()
                else:
                    self._state = "save_error"
                    if self._error_line1:
                        self._error_line1.text = f"Could not save scores: {err}"
                    if self._error_line2:
                        self._error_line2.text = "Press any key to continue"
            return

        # Printable characters — always uppercase
        if len(self._name) >= HighScoreTable.MAX_NAME_LEN:
            return

        ch: Optional[str] = None
        if arcade.key.A <= key <= arcade.key.Z:
            ch = chr(key).upper()
        elif ord("0") <= key <= ord("9"):
            ch = chr(key)
        elif key == arcade.key.SPACE:
            ch = " "

        if ch is not None:
            self._name += ch
