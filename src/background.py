"""Background rendering: static nebula layer and procedural scrolling star field."""

from __future__ import annotations

import random
from typing import Any, Optional

import arcade
import arcade.shape_list as _shape_module

from src.paths import resource_path


class StaticBackground:
    """Single arcade.Sprite scaled to fill the window exactly — no scrolling."""

    def __init__(
        self,
        texture_path: str,
        window_width: int,
        window_height: int,
        _sprite: Optional[arcade.Sprite] = None,
    ) -> None:
        sprite = _sprite if _sprite is not None else arcade.Sprite(resource_path(texture_path))
        if _sprite is None:
            sprite.width = window_width
            sprite.height = window_height
            sprite.center_x = window_width / 2
            sprite.center_y = window_height / 2
        self._sprite_list = arcade.SpriteList()
        self._sprite_list.append(sprite)

    def draw(self) -> None:
        self._sprite_list.draw()


class ProceduralStarField:
    """Procedural scrolling star field rendered via arcade.ShapeElementList.

    Stars scroll downward at independent speeds (parallax). Stars that exit the
    bottom wrap to the top with a new random x position. The ShapeElementList is
    rebuilt only when at least one star wraps — not every frame.

    Pass *_shape_list* to skip OpenGL initialisation in tests.
    """

    def __init__(
        self,
        window_width: int,
        window_height: int,
        star_count: int = 300,
        speed_min: float = 20.0,
        speed_max: float = 120.0,
        _shape_list: Optional[Any] = None,
    ) -> None:
        self._width = window_width
        self._height = window_height
        self._count = star_count
        self._speed_min = speed_min
        self._speed_max = speed_max

        self._x: list[float] = [random.uniform(0, window_width) for _ in range(star_count)]
        self._y: list[float] = [random.uniform(0, window_height) for _ in range(star_count)]
        self._speed_list: list[float] = [random.uniform(speed_min, speed_max) for _ in range(star_count)]
        self._size: list[float] = [random.uniform(1.0, 3.0) for _ in range(star_count)]
        self._brightness: list[int] = [random.randint(120, 255) for _ in range(star_count)]

        # _rebuild_enabled=False when a test sentinel is injected to avoid GL calls.
        self._rebuild_enabled: bool = _shape_list is None
        self._shape_list: Any = _shape_list
        if self._rebuild_enabled:
            self._rebuild()

    def _rebuild(self) -> None:
        """Rebuild ShapeElementList from current star positions."""
        if not self._rebuild_enabled:
            return
        sl: _shape_module.ShapeElementList = _shape_module.ShapeElementList()
        for x, y, size, b in zip(self._x, self._y, self._size, self._brightness):
            shape = _shape_module.create_ellipse_filled(x, y, size, size, (b, b, b, 255))
            sl.append(shape)
        self._shape_list = sl

    def update(self, delta_time: float) -> None:
        """Scroll all stars downward; wrap any that exit the bottom."""
        wrapped = False
        for i in range(self._count):
            self._y[i] -= self._speed_list[i] * delta_time
            if self._y[i] < 0:
                self._y[i] = float(self._height)
                self._x[i] = random.uniform(0, self._width)
                wrapped = True
        if wrapped:
            self._rebuild()

    def draw(self) -> None:
        """Draw the star field — single GPU call."""
        if self._shape_list is not None:
            self._shape_list.draw()
