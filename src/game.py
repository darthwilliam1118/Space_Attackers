import pyglet
import arcade
from src.state import GameState, GameStateManager

SCREEN_TITLE = "Space Attackers"


def _window_size() -> tuple[int, int]:
    """Return (width, height) for a 4:3 window that fills the display height."""
    screen = pyglet.display.Display().get_default_screen()
    # Leave a small gap for the OS taskbar
    usable_h = int(screen.height * 0.92)
    usable_w = int(usable_h * 4 / 3)
    if usable_w > screen.width:
        usable_w = int(screen.width * 0.92)
        usable_h = int(usable_w * 3 / 4)
    return usable_w, usable_h


class GameWindow(arcade.Window):
    """Main game window. Owns the Arcade window and manages view transitions."""

    def __init__(self) -> None:
        w, h = _window_size()
        super().__init__(w, h, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.BLACK)
        self._manager = GameStateManager(self)
        self._manager.transition(GameState.SPLASH)


def main() -> None:
    GameWindow()
    arcade.run()
