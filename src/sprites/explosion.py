"""ExplosionSprite — self-contained ping-pong explosion animation."""

from __future__ import annotations

from typing import Optional

import arcade

from src.paths import resource_path

_SHEET_PATH = "assets/images/exp2_0.png"
_FRAME_SIZE = 64


class ExplosionSprite(arcade.Sprite):
    """Plays a ping-pong explosion animation then removes itself.

    For unit tests, pass a pre-built *frames* list so no display/disk access
    occurs. In production, leave *frames* as None and the sheet is loaded
    via resource_path().
    """

    def __init__(
        self,
        x: float,
        y: float,
        frame_duration: float = 0.05,
        frames: Optional[list[arcade.Texture]] = None,
        vx: float = 0.0,
        vy: float = 0.0,
    ) -> None:
        super().__init__()
        self.center_x = x
        self.center_y = y
        self._vx = vx
        self._vy = vy
        self._frame_duration = frame_duration
        self._elapsed: float = 0.0
        self._complete: bool = False

        if frames is not None:
            base_frames = frames
        else:
            base_frames = self._load_frames()

        # The sheet is laid out so bottom-right = smallest, so after
        # load_spritesheet the last element is smallest → reverse to get
        # index-0 = smallest.
        base_frames = list(reversed(base_frames))
        # Ping-pong: small→large→small.  Total length = 2n-1.
        # e.g. [D,C,B,A] → [D,C,B,A,B,C,D]
        if len(base_frames) > 1:
            self._frames: list[arcade.Texture] = (
                base_frames + list(reversed(base_frames[:-1]))
            )
        else:
            self._frames = base_frames

        self._frame_index: int = 0
        if self._frames:
            self.texture = self._frames[0]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _load_frames() -> list[arcade.Texture]:
        path = resource_path(_SHEET_PATH)
        sheet = arcade.load_spritesheet(path)
        img = sheet.image
        cols = img.width // _FRAME_SIZE
        rows = img.height // _FRAME_SIZE
        return sheet.get_texture_grid(
            size=(_FRAME_SIZE, _FRAME_SIZE),
            columns=cols,
            count=rows * cols,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_complete(self) -> bool:
        """True after the full ping-pong cycle has finished."""
        return self._complete

    def update(self, delta_time: float = 1 / 60) -> None:  # type: ignore[override]
        if self._complete:
            return
        self.center_x += self._vx * delta_time
        self.center_y += self._vy * delta_time
        self._elapsed += delta_time
        if self._elapsed >= self._frame_duration:
            self._elapsed -= self._frame_duration
            self._frame_index += 1
            if self._frame_index >= len(self._frames):
                self._complete = True
                self.remove_from_sprite_lists()
                return
            self.texture = self._frames[self._frame_index]
