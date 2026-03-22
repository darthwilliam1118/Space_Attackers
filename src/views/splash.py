"""Splash screen — title card shown on launch."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Optional

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

from src.ui.text_utils import FONT_MAIN, FONT_THIN, centered_text


class SplashView(arcade.View):
    """Displays the game title and waits for any key to proceed to MAIN.

    Level music tracks are loaded in a background thread while the splash
    animates.  "Press any key" and the auto-advance timer are suppressed
    until that background load completes.
    """

    TITLE = "Space Attackers!"
    PROMPT = "Press any key to continue..."

    _AUTO_ADVANCE = 5.0

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__()
        self._manager = manager
        self._elapsed: float = 0.0
        self._ending_ready: bool = False   # "ending" track loaded; safe to play
        self._music_started: bool = False  # play() already called (main thread only)
        self._assets_ready: bool = False   # all tracks loaded; show prompt
        self._title_text: Optional[arcade.Text] = None
        self._prompt_text: Optional[arcade.Text] = None

    def on_show_view(self) -> None:
        w, h = self.window.width, self.window.height
        self._title_text = centered_text(
            self.TITLE, w, h // 2 + 40,
            font_size=64, color=arcade.color.YELLOW, font_name=FONT_MAIN, bold=True,
        )
        self._prompt_text = centered_text(
            self.PROMPT, w, 40,
            font_size=18, color=arcade.color.WHITE, font_name=FONT_THIN,
        )
        # Load all music in the background; splash appears with no audio delay.
        # arcade.load_sound() is audio-only (no OpenGL) and safe from a worker thread.
        threading.Thread(target=self._preload_tracks, daemon=True).start()

    def _preload_tracks(self) -> None:
        """Worker: load ending first, then level tracks."""
        self.window.music.load_track("ending")  # type: ignore[attr-defined]
        self._ending_ready = True  # signal main thread to start music
        for key in ("level_1", "level_2", "level_3"):
            self.window.music.load_track(key)  # type: ignore[attr-defined]
        self._assets_ready = True

    def on_update(self, delta_time: float) -> None:
        self.window.star_field.update(delta_time)  # type: ignore[attr-defined]
        if self._ending_ready and not self._music_started:
            self.window.music.play("ending")  # type: ignore[attr-defined]
            self._music_started = True
        if not self._assets_ready:
            return  # hold timer and prompt until all tracks are loaded
        self._elapsed += delta_time
        if self._elapsed >= self._AUTO_ADVANCE:
            self._go_to_main()

    def _go_to_main(self) -> None:
        from src.state import GameState
        self._manager.transition(GameState.MAIN)

    def on_draw(self) -> None:
        self.clear()
        self.window.background.draw()  # type: ignore[attr-defined]
        self.window.star_field.draw()  # type: ignore[attr-defined]
        if self._title_text:
            self._title_text.draw()
        if self._assets_ready and self._prompt_text:
            self._prompt_text.draw()

    def on_key_press(self, key: int, modifiers: int) -> None:
        if not self._assets_ready:
            return
        self._go_to_main()
