"""MusicPlayer — loads and manages background music tracks."""

from __future__ import annotations

from typing import Optional

import arcade

from src.paths import resource_path

_TRACKS: dict[str, str] = {
    "ending": "assets/music/Juhani Junkala [Retro Game Music Pack] Ending.ogg",
    "level_1": "assets/music/Juhani Junkala [Retro Game Music Pack] Level 1.ogg",
    "level_2": "assets/music/Juhani Junkala [Retro Game Music Pack] Level 2.ogg",
    "level_3": "assets/music/Juhani Junkala [Retro Game Music Pack] Level 3.ogg",
    "level_4": "assets/music/awake10_megawall.mp3",
    "level_5": "assets/music/Cyberpunk Moonlight Sonata.mp3",
    "level_6": "assets/music/fight.ogg",
}

# Number of distinct level tracks available
LEVEL_TRACK_COUNT = 6


def track_key_for_level(level: int) -> str:
    """Return the music track key for *level*, cycling through the 6 level tracks."""
    idx = ((level - 1) % LEVEL_TRACK_COUNT) + 1
    return f"level_{idx}"


class MusicPlayer:
    """Owns all music tracks and keeps at most one playing at a time.

    Call play(key) from each view's on_show_view().  If the requested track
    is already playing it continues uninterrupted (no restart on re-entry).
    """

    def __init__(self) -> None:
        self._sounds: dict[str, arcade.Sound] = {}
        self._current_key: Optional[str] = None
        self._player: Optional[object] = (
            None  # pyglet.media.player.Player returned by arcade.play_sound
        )
        self._volume: float = 0.8  # 0.0-1.0
        # All tracks are lazy-loaded: load_track() / play() on demand

    def load_track(self, key: str) -> None:
        """Load *key* into _sounds if not already loaded (idempotent)."""
        if key not in self._sounds:
            self._sounds[key] = arcade.load_sound(resource_path(_TRACKS[key]))

    def play(self, key: str) -> None:
        """Start playing *key* looped.  No-op if *key* is already playing."""
        if key == self._current_key:
            return
        self.stop()
        self.load_track(key)  # lazy fallback in case preload was skipped
        self._current_key = key
        self._player = arcade.play_sound(self._sounds[key], volume=self._volume, loop=True)

    def set_volume(self, volume_0_100: int) -> None:
        """Set music volume (0-100).  Applies immediately to any playing track."""
        self._volume = max(0, min(100, volume_0_100)) / 100.0
        if self._player is not None:
            self._player.volume = self._volume  # type: ignore[union-attr]

    def pause(self) -> None:
        """Pause playback without losing the current track."""
        if self._player is not None:
            self._player.pause()  # type: ignore[union-attr]

    def resume(self) -> None:
        """Resume a paused track."""
        if self._player is not None:
            self._player.play()  # type: ignore[union-attr]

    def stop(self) -> None:
        """Stop whatever is currently playing."""
        if self._player is not None:
            self._player.pause()
            self._player = None
        self._current_key = None
