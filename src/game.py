import arcade
from src.background import ProceduralStarField, StaticBackground
from src.game_config import GameConfig
from src.music import MusicPlayer
from src.paths import resource_path
from src.state import GameState, GameStateManager

SCREEN_TITLE = "Space Attackers"


class GameWindow(arcade.Window):
    """Main game window. Owns the Arcade window and manages view transitions."""

    def __init__(self) -> None:
        cfg = GameConfig.load()
        h = cfg.max_window_height
        w = int(h * 1.25)
        super().__init__(w, h, SCREEN_TITLE, center_window=True)
        arcade.set_background_color(arcade.color.BLACK)
        arcade.load_font(resource_path("assets/fonts/kenvector_future2.ttf"))
        arcade.load_font(resource_path("assets/fonts/kenvector_future_thin2.ttf"))
        bg = cfg.background
        self.background = StaticBackground(bg.background_image, w, h)
        self.star_field = ProceduralStarField(w, h, bg.star_count, bg.star_speed_min, bg.star_speed_max)
        self.music = MusicPlayer()
        self.music.set_volume(cfg.music_volume)
        self._manager = GameStateManager(self)
        self._manager.transition(GameState.SPLASH)


def main() -> None:
    GameWindow()
    arcade.run()
