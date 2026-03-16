"""EnemySprite — a single enemy ship in the formation grid."""

from __future__ import annotations

from typing import Optional

import arcade

from src.paths import resource_path

# Row index → (color, ship_type).  Cycles via row % 5.
ROW_MAPPING: list[tuple[str, int]] = [
    ("Black", 1),
    ("Blue", 2),
    ("Green", 3),
    ("Red", 4),
    ("Black", 5),
]


def sprite_path_for(color: str, ship_type: int) -> str:
    return f"assets/images/PNG/Enemies/enemy{color}{ship_type}.png"


class EnemySprite(arcade.Sprite):
    """One cell in the enemy formation.

    Pass *texture* to inject a pre-loaded texture (tests, no display needed).
    """

    def __init__(
        self,
        color: str,
        ship_type: int,
        col: int,
        row: int,
        texture: Optional[arcade.Texture] = None,
    ) -> None:
        if texture is not None:
            super().__init__(texture)
        else:
            super().__init__(resource_path(sprite_path_for(color, ship_type)))
        self.color_name: str = color
        self.ship_type: int = ship_type
        self.col: int = col
        self.row: int = row
