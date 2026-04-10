"""ScorePopup — floating score indicator shown on enemy kill."""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class _TextLike(Protocol):
    """Minimal interface used by ScorePopup so tests can inject a stub."""

    x: float
    y: float
    color: tuple[int, int, int, int]

    def draw(self) -> None: ...


class ScorePopup:
    """Floating "+N" label that rises and fades after an enemy is destroyed.

    Uses arcade.Text internally.  For unit tests, pass a stub via *_text_obj*
    to avoid requiring an active OpenGL context.
    """

    def __init__(
        self,
        x: float,
        y: float,
        value: int,
        duration: float = 0.8,
        rise_speed: float = 60.0,
        _text_obj: Optional[_TextLike] = None,
    ) -> None:
        self.elapsed: float = 0.0
        self.duration: float = duration
        self.rise_speed: float = rise_speed
        self.done: bool = False

        if _text_obj is not None:
            self._label: _TextLike = _text_obj
            self._label.x = x
            self._label.y = y
            self._label.color = (255, 220, 50, 255)
        else:
            import arcade

            self._label = arcade.Text(  # type: ignore[assignment]
                f"+{value}",
                x,
                y,
                color=(255, 220, 50, 255),
                font_size=14,
                font_name="KenVector Future2 Thin",
                anchor_x="center",
            )

    def update(self, delta_time: float) -> None:
        """Advance animation: rise upward and fade alpha linearly to zero."""
        if self.done:
            return
        self.elapsed += delta_time
        if self.elapsed >= self.duration:
            self.done = True
            return
        t = self.elapsed / self.duration
        self._label.y += self.rise_speed * delta_time
        self._label.color = (255, 220, 50, int(255 * (1.0 - t)))

    def draw(self) -> None:
        """Draw the label if the popup has not yet expired."""
        if not self.done:
            self._label.draw()

    @property
    def is_done(self) -> bool:
        return self.done
