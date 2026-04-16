import arcade
from agf.paths import resource_path
from agf.window import GameWindowBase

from src.game_config import GameConfig
from src.state import GameState, GameStateManager

SCREEN_TITLE = "Space Attackers"


class GameWindow(GameWindowBase):
    """Main game window. Owns the Arcade window and manages view transitions."""

    def __init__(self) -> None:
        cfg = GameConfig.load()
        super().__init__(cfg, cfg.background, SCREEN_TITLE)
        self._manager = GameStateManager(self)
        self._manager.transition(GameState.SPLASH)

    def _load_fonts(self) -> None:
        arcade.load_font(resource_path("assets/fonts/kenvector_future2.ttf"))
        arcade.load_font(resource_path("assets/fonts/kenvector_future_thin2.ttf"))


def main() -> None:
    GameWindow()
    arcade.run()
