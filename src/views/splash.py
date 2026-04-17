"""Splash screen — title card shown on launch."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agf.views.splash import SplashView as _SplashViewBase

if TYPE_CHECKING:
    from src.state import GameStateManager


class SplashView(_SplashViewBase):
    """Space Attackers splash: preloads ending + level music tracks."""

    TITLE_LINE1 = "Space"
    TITLE_LINE2 = "Attackers!"
    AUTO_ADVANCE = 5.0

    def __init__(self, manager: "GameStateManager") -> None:
        self._manager = manager
        self._ending_ready: bool = False
        self._music_started: bool = False
        super().__init__(on_complete=self._go_to_main)

    def _preload_tracks(self) -> None:
        self.window.music.load_track("ending")  # type: ignore[attr-defined]
        self._ending_ready = True
        for key in ("level_1", "level_2", "level_3"):
            self.window.music.load_track(key)  # type: ignore[attr-defined]
        self._assets_ready = True

    def on_update(self, delta_time: float) -> None:
        if self._ending_ready and not self._music_started:
            self.window.music.play("ending")  # type: ignore[attr-defined]
            self._music_started = True
        super().on_update(delta_time)

    def _go_to_main(self) -> None:
        from src.state import GameState

        self._manager.transition(GameState.MAIN)
