"""Main menu — cycles leaderboard and instructions pages."""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

from agf.high_scores import HighScoreTable, scores_path

from src.ui.text_utils import FONT_MAIN, FONT_THIN, centered_text, measure_text_width

_PAGES = ["LEADERBOARD", "INSTRUCTIONS"]
_CYCLE_INTERVAL = 15.0  # seconds per page
_SCROLL_SPEED = 28.0  # px/s for instruction autoscroll
_LINE_HEIGHT = 26  # px between instruction lines


# ---------------------------------------------------------------------------
# README parser
# ---------------------------------------------------------------------------


def _word_wrap(text: str, max_chars: int = 58) -> list[str]:
    """Break *text* at word boundaries so no line exceeds *max_chars*."""
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = (current + " " + word).lstrip()
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _parse_how_to_play() -> list[str]:
    """Return plain-text lines from README How to Play + Credits sections."""
    root = Path(__file__).parent.parent.parent
    try:
        raw = (root / "README.md").read_text(encoding="utf-8")
    except Exception:
        return _FALLBACK_LINES

    result: list[str] = []
    assets: list[str] = []
    in_howto = False
    in_assets = False

    for line in raw.splitlines():
        s = line.rstrip()

        if s == "## How to Play":
            in_howto = True
            continue
        if s == "## Assets":
            in_howto = False
            in_assets = True
            continue
        if s.startswith("## "):
            in_howto = False
            in_assets = False
            continue

        if in_howto:
            if not s:
                result.append("")
                continue
            if s.startswith("---"):
                continue
            if s.startswith("### "):
                result.append(s[4:].upper())
                continue
            # Table separator  |---|---|
            if s.startswith("|") and all(c in "-|: " for c in s):
                continue
            # Table data row — "\tleft\tright" for two-column rendering
            if s.startswith("|") and s.endswith("|"):
                cells = [c.strip() for c in s.strip("|").split("|")]
                if len(cells) >= 2 and cells[0].lower() == "action":
                    continue
                if len(cells) >= 2:
                    result.append(f"\t{cells[0]}\t{cells[1]}")
                continue
            # Bullet point
            if s.startswith("- "):
                for wrapped in _word_wrap(s[2:], max_chars=75):
                    result.append(f"    {wrapped}")
                continue
            # Plain paragraph
            for wrapped in _word_wrap(s):
                result.append(f"  {wrapped}")

        elif in_assets:
            if not s:
                continue
            # Strip any leading "- " or " - "
            clean = s.lstrip().lstrip("- ").lstrip()
            for wrapped in _word_wrap(clean, max_chars=70):
                assets.append(f"  {wrapped}")

    # Append CREDITS block
    license_lines: list[str] = []
    try:
        first3 = (root / "LICENSE").read_text(encoding="utf-8").splitlines()[:3]
        license_lines = [line.rstrip() for line in first3 if line.strip()]
    except Exception:
        pass

    if license_lines or assets:
        # Strip any trailing blank from the previous section before adding ours
        while result and not result[-1]:
            result.pop()
        result.extend(["", "CREDITS"])
        for line in license_lines:
            result.append(f"  {line}")
        if assets:
            result.append("")
            result.extend(assets)

    # Strip leading/trailing blank lines
    while result and not result[0]:
        result.pop(0)
    while result and not result[-1]:
        result.pop()
    return result


_FALLBACK_LINES = [
    "CONTROLS",
    "\tMove left\tArrow Left / A",
    "\tMove right\tArrow Right / D",
    "\tMove up\tArrow Up / W",
    "\tMove down\tArrow Down / S",
    "\tFire\tSpace",
    "\tPause / Resume\tP",
    "",
    "OBJECTIVE",
    "  Destroy all enemies before they hit your ship.",
    "  Clear each wave to advance to the next level.",
    "",
    "TIPS",
    "    Ship tilts as it moves \u2014 aim your shots!",
    "    Brief invincibility window after spawning.",
    "    Enemies speed up as their numbers thin.",
    "",
    "CREDITS",
    "  MIT License",
    "  Copyright (c) 2026 darthwilliam1118",
    "",
    "  Sprites: Kenney (kenney.nl) \u2014 CC0 Public Domain",
    "  Fonts: KenPixel & KenVector by Kenney Vleugels",
    "  Sound effects: OpenGameArt.org \u2014 CC0 Public Domain",
]


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------


class MainMenuView(arcade.View):
    """Cycles LEADERBOARD / INSTRUCTIONS pages.

    Keys:
        1 → 1-player game
        2 → 2-player game
        C → game config
        X → exit
    """

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__()
        self._manager = manager
        self._page_index: int = 0
        self._elapsed: float = 0.0
        self._prompt_elapsed: float = 0.0
        self._scroll_offset: float = 0.0

        # Always-visible chrome
        self._title_text: Optional[arcade.Text] = None
        self._page_indicator: Optional[arcade.Text] = None
        self._start_prompt: Optional[arcade.Text] = None
        self._hints_text: Optional[arcade.Text] = None

        # Leaderboard panel
        self._lb_rows: list[tuple[arcade.Text, arcade.Text, arcade.Text]] = []

        # Instructions panel — each entry is (primary_text, right_col_text | None)
        self._instr_texts: list[tuple[arcade.Text, arcade.Text | None]] = []
        self._instr_needs_scroll: bool = False
        self._instr_max_scroll: float = 0.0
        self._content_top: float = 0.0
        self._content_bottom: float = 0.0
        self._scroll_delay: float = 0.0

    # ------------------------------------------------------------------
    # Arcade callbacks
    # ------------------------------------------------------------------

    def on_show_view(self) -> None:
        self.window.music.play("ending")  # type: ignore[attr-defined]
        self._elapsed = 0.0
        self._scroll_offset = 0.0
        self._scroll_delay = 5.0 if _PAGES[self._page_index] == "INSTRUCTIONS" else 0.0

        w, h = self.window.width, self.window.height
        self._content_top = float(h - 145)
        self._content_bottom = 80.0

        self._title_text = centered_text(
            "Space Attackers!",
            w,
            h - 50,
            font_size=42,
            color=arcade.color.YELLOW,
            font_name=FONT_MAIN,
        )
        self._page_indicator = centered_text(
            self._page_label(),
            w,
            h - 95,
            font_size=22,
            color=arcade.color.CYAN,
            font_name=FONT_THIN,
        )
        self._start_prompt = centered_text(
            "PRESS 1 OR 2 TO START",
            w,
            56,
            font_size=16,
            color=arcade.color.WHITE,
            font_name=FONT_MAIN,
        )
        self._hints_text = centered_text(
            "C \u2014 CONFIG    X \u2014 EXIT",
            w,
            24,
            font_size=14,
            color=(160, 160, 160, 255),
            font_name=FONT_THIN,
        )

        self._build_leaderboard(w)
        self._build_instructions(w)

    def on_update(self, delta_time: float) -> None:
        self.window.star_field.update(delta_time)  # type: ignore[attr-defined]

        self._elapsed += delta_time
        if self._elapsed >= _CYCLE_INTERVAL:
            self._elapsed = 0.0
            self._scroll_offset = 0.0
            self._page_index = (self._page_index + 1) % len(_PAGES)
            if self._page_indicator:
                self._page_indicator.text = self._page_label()
            if _PAGES[self._page_index] == "INSTRUCTIONS":
                self._scroll_delay = 5.0

        if _PAGES[self._page_index] == "INSTRUCTIONS" and self._instr_needs_scroll:
            if self._scroll_delay > 0:
                self._scroll_delay -= delta_time
            else:
                self._scroll_offset = min(
                    self._scroll_offset + _SCROLL_SPEED * delta_time,
                    self._instr_max_scroll,
                )

        self._prompt_elapsed += delta_time
        if self._start_prompt is not None:
            alpha = int(abs(math.sin(self._prompt_elapsed * 3.0)) * 255)
            self._start_prompt.color = (255, 255, 255, alpha)

    def on_draw(self) -> None:
        self.clear()
        self.window.background.draw()  # type: ignore[attr-defined]
        self.window.star_field.draw()  # type: ignore[attr-defined]

        if self._title_text:
            self._title_text.draw()
        if self._page_indicator:
            self._page_indicator.draw()
        if self._start_prompt:
            self._start_prompt.draw()
        if self._hints_text:
            self._hints_text.draw()

        if _PAGES[self._page_index] == "LEADERBOARD":
            for rank_t, name_t, score_t in self._lb_rows:
                rank_t.draw()
                name_t.draw()
                score_t.draw()
        else:
            for i, (text_a, text_b) in enumerate(self._instr_texts):
                y = self._content_top - i * _LINE_HEIGHT + self._scroll_offset
                text_a.y = y
                if self._content_bottom <= y <= self._content_top + _LINE_HEIGHT:
                    text_a.draw()
                    if text_b is not None:
                        text_b.y = y
                        text_b.draw()

    def on_key_press(self, key: int, modifiers: int) -> None:
        from src.state import GameState

        match key:
            case arcade.key.KEY_1:
                cfg = self._manager.context.get("config")
                self._manager.transition(GameState.GAME_INIT, num_players=1, config=cfg)
            case arcade.key.KEY_2:
                cfg = self._manager.context.get("config")
                self._manager.transition(GameState.GAME_INIT, num_players=2, config=cfg)
            case arcade.key.C:
                self._manager.transition(GameState.GAME_CONFIG)
            case arcade.key.X:
                self._manager.transition(GameState.EXIT)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _page_label(self) -> str:
        labels = {"LEADERBOARD": "HIGH SCORES", "INSTRUCTIONS": "HOW TO PLAY"}
        return f"[ {labels[_PAGES[self._page_index]]} ]"

    def _build_leaderboard(self, w: int) -> None:
        table = HighScoreTable.load(scores_path())
        entries = table.entries
        row_h = 28
        top_y = int(self._content_top)
        _col_font_size = 18
        _col_gap = 16
        name_col_w = measure_text_width(
            "W" * HighScoreTable.MAX_NAME_LEN, _col_font_size, FONT_THIN
        )
        name_x = w / 2 - name_col_w / 2
        name_x_end = w / 2 + name_col_w / 2
        rank_x = name_x - _col_gap
        score_x = name_x_end + _col_gap
        self._lb_rows = []
        for i in range(HighScoreTable.MAX_ENTRIES):
            rank = i + 1
            y = top_y - i * row_h
            if i < len(entries):
                e = entries[i]
                color: tuple[int, int, int, int] = arcade.color.WHITE
                rank_str, name_str, score_str = f"#{rank}", e.name, str(e.score)
            else:
                color = (80, 80, 80, 255)
                rank_str, name_str, score_str = f"#{rank}", "---", ""
            rank_t = arcade.Text(
                rank_str,
                rank_x,
                y,
                color,
                _col_font_size,
                font_name=FONT_THIN,
                anchor_x="right",
                anchor_y="center",
            )
            name_t = arcade.Text(
                name_str,
                name_x,
                y,
                color,
                _col_font_size,
                font_name=FONT_THIN,
                anchor_x="left",
                anchor_y="center",
            )
            score_t = arcade.Text(
                score_str,
                score_x,
                y,
                color,
                _col_font_size,
                font_name=FONT_THIN,
                anchor_x="left",
                anchor_y="center",
            )
            self._lb_rows.append((rank_t, name_t, score_t))

    def _build_instructions(self, w: int) -> None:
        lines = _parse_how_to_play()
        self._instr_texts = []
        # Two-column rows are anchored either side of centre with a fixed gap.
        col_gap = 20
        col_r = w // 2 - col_gap // 2  # right edge of left column
        col_l = w // 2 + col_gap // 2  # left edge of right column
        for line in lines:
            if line.startswith("\t"):
                parts = line.split("\t")  # ["", left_text, right_text]
                left_t = arcade.Text(
                    parts[1],
                    col_r,
                    0,
                    arcade.color.WHITE,
                    16,
                    font_name=FONT_THIN,
                    anchor_x="right",
                    anchor_y="center",
                )
                right_t = arcade.Text(
                    parts[2],
                    col_l,
                    0,
                    arcade.color.WHITE,
                    16,
                    font_name=FONT_THIN,
                    anchor_x="left",
                    anchor_y="center",
                )
                self._instr_texts.append((left_t, right_t))
            else:
                is_header = bool(line) and not line.startswith(" ") and line == line.upper()
                t = centered_text(
                    line,
                    w,
                    0,  # y set dynamically in on_draw
                    font_size=16,
                    color=arcade.color.CYAN if is_header else arcade.color.WHITE,
                    font_name=FONT_THIN,
                )
                self._instr_texts.append((t, None))
        total_h = len(lines) * _LINE_HEIGHT
        panel_h = self._content_top - self._content_bottom
        self._instr_needs_scroll = total_h > panel_h
        self._instr_max_scroll = max(0.0, total_h - panel_h + _LINE_HEIGHT)
