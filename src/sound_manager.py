from __future__ import annotations

import arcade


class SoundManager:
    """Throttles simultaneous playbacks of one sound to reduce audio thread load.

    Tracks active pyglet Players; when the cap is reached the oldest is stopped
    before a new one starts.  Use a separate instance per sound type.
    """

    def __init__(self, max_simultaneous: int = 4) -> None:
        self._max = max_simultaneous
        self._active: list[arcade.pyglet.media.Player] = []

    def play(self, sound: arcade.Sound, volume: float = 1.0) -> None:
        self._active = [p for p in self._active if p.playing]
        if len(self._active) >= self._max:
            oldest = self._active.pop(0)
            arcade.stop_sound(oldest)
        player = arcade.play_sound(sound, volume=volume)
        if player is not None:
            self._active.append(player)
