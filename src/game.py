import ctypes
import ctypes.wintypes

import pyglet
import arcade
from src.background import ProceduralStarField, StaticBackground
from src.game_config import GameConfig
from src.music import MusicPlayer
from src.paths import resource_path
from src.state import GameState, GameStateManager

SCREEN_TITLE = "Space Attackers"


def _work_area() -> tuple[int, int]:
    """Return (width, height) of the primary monitor work area (excludes taskbar)."""
    try:
        r = ctypes.wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(r), 0)  # SPI_GETWORKAREA
        return r.right - r.left, r.bottom - r.top
    except Exception:
        screen = pyglet.display.Display().get_default_screen()
        return screen.width, screen.height


def _window_size(max_window_height: int = 0) -> tuple[int, int]:
    """Return (width, height) for a 4:3 window fitting the usable display area.

    Uses the OS work area (taskbar excluded) so the window is never taller than
    what's actually available.  *max_window_height* caps the height when non-zero
    (useful for testing smaller screen sizes).
    """
    work_w, work_h = _work_area()
    usable_h = int(work_h * 0.97)   # small gap only; work area already excludes taskbar
    usable_w = int(usable_h * 4 / 3)
    if usable_w > work_w:
        usable_w = int(work_w * 0.97)
        usable_h = int(usable_w * 3 / 4)
    if max_window_height > 0:
        usable_h = min(usable_h, max_window_height)
        usable_w = int(usable_h * 4 / 3)
    return usable_w, usable_h


class GameWindow(arcade.Window):
    """Main game window. Owns the Arcade window and manages view transitions."""

    def __init__(self) -> None:
        cfg = GameConfig.load()          # load before sizing so max_window_height is available
        w, h = _window_size(cfg.max_window_height)
        super().__init__(w, h, SCREEN_TITLE, center_window=True)
        # Ensure the title bar is not above the top of the screen after centering
        x, y = self.get_location()
        if y < 0:
            self.set_location(x, 0)
        arcade.set_background_color(arcade.color.BLACK)
        arcade.load_font(resource_path("assets/fonts/kenvector_future2.ttf"))
        arcade.load_font(resource_path("assets/fonts/kenvector_future_thin2.ttf"))
        bg = cfg.background
        self.background = StaticBackground(bg.background_image, w, h)
        self.star_field = ProceduralStarField(w, h, bg.star_count, bg.star_speed_min, bg.star_speed_max)
        self.music = MusicPlayer()
        self._manager = GameStateManager(self)
        self._manager.transition(GameState.SPLASH)


def main() -> None:
    GameWindow()
    arcade.run()
