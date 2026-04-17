"""Main menu — cycles leaderboard and instructions pages."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from agf.views.main_menu import MainMenuViewBase

if TYPE_CHECKING:
    from src.state import GameStateManager

_PROJECT_ROOT = Path(__file__).parent.parent.parent


class MainMenuView(MainMenuViewBase):
    """Space Attackers main menu — routes key presses through the state machine.

    Keys:
        1 → 1-player game
        2 → 2-player game
        C → game config
        X → exit
    """

    TITLE = "Space Attackers!"
    FALLBACK_INSTRUCTIONS = [
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

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__(
            readme_path=_PROJECT_ROOT / "README.md",
            license_path=_PROJECT_ROOT / "LICENSE",
        )
        self._manager = manager

    def on_start_1p(self) -> None:
        from src.state import GameState

        cfg = self._manager.context.get("config")
        self._manager.transition(GameState.GAME_INIT, num_players=1, config=cfg)

    def on_start_2p(self) -> None:
        from src.state import GameState

        cfg = self._manager.context.get("config")
        self._manager.transition(GameState.GAME_INIT, num_players=2, config=cfg)

    def on_config(self) -> None:
        from src.state import GameState

        self._manager.transition(GameState.GAME_CONFIG)

    def on_exit(self) -> None:
        from src.state import GameState

        self._manager.transition(GameState.EXIT)
