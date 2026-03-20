"""Shared text helpers — thin wrappers around arcade.Text for common patterns."""

from __future__ import annotations

import arcade

FONT_MAIN = "KenVector Future"
FONT_THIN = "Kenvector Future"

_MUTED: tuple[int, int, int, int] = (128, 128, 128, 255)


def centered_text(
    text: str,
    window_width: int,
    y: int,
    font_size: int = 16,
    color: tuple[int, int, int, int] = arcade.color.WHITE,
    font_name: str = FONT_MAIN,
    bold: bool = False,
) -> arcade.Text:
    """Return an arcade.Text centered horizontally on screen."""
    return arcade.Text(
        text=text,
        x=window_width / 2,
        y=y,
        color=color,
        font_size=font_size,
        font_name=font_name,
        anchor_x="center",
        anchor_y="center",
        bold=bold,
    )
