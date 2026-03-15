import arcade
from src.state import GameState, GameStateManager

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Space Attackers"


class GameWindow(arcade.Window):
    """Main game window. Owns the Arcade window and manages view transitions."""

    def __init__(self) -> None:
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.BLACK)
        self._manager = GameStateManager(self)
        self._manager.transition(GameState.SPLASH)


def main() -> None:
    GameWindow()
    arcade.run()
