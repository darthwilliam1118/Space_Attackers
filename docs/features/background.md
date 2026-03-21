# Feature: Background and Scrolling Star Field

## Overview
The game background consists of two layers rendered beneath all game
sprites: a static Kenney nebula bitmap for color and atmosphere, and a
procedural scrolling star field for depth and motion. No additional bitmap
assets are required for the star field. Both layers are active during
RUN_LEVEL and should also appear on MAIN, GAME_OVER, and LEVEL_COMPLETE
screens for visual continuity.

## Files
- src/space_attackers/background.py
  - ScrollingBackground class
  - ProceduralStarField class

## Layer stack (draw order in on_draw())

All views that show the background must draw in this order:
1. self.clear()                  — clears to black
2. self.bg.draw()                — static Kenney nebula bitmap
3. self.star_field.draw()        — procedural scrolling stars
4. self.scene.draw()             — game sprites
5. score popups                  — floating score text
6. HUD text objects              — always on top

## Layer 1 — Static nebula background

- Use one of the Kenney Space Shooter Redux background PNGs:
    assets/images/Backgrounds/darkPurple.png
  (or whichever dark variant is included — check assets/images/Backgrounds/)
- Implemented as a single arcade.Sprite scaled to fill the window exactly
- Does not scroll — static underneath the star field
- Loaded via resource_path() helper

```python
class StaticBackground:
    def __init__(self, texture_path: str, window_width: int,
                 window_height: int):
        self.sprite = arcade.Sprite(resource_path(texture_path))
        self.sprite.width = window_width
        self.sprite.height = window_height
        self.sprite.center_x = window_width / 2
        self.sprite.center_y = window_height / 2

    def draw(self) -> None:
        self.sprite.draw()
```

## Layer 2 — Procedural scrolling star field

- 300 stars generated at random positions on init (configurable as
  `star_count` in game_config.toml, default: 300)
- Each star has an independent random scroll speed creating natural
  parallax — slower stars appear further away
- Stars wrap from bottom back to top when they scroll off screen,
  randomising x position on wrap for variety
- Implemented using arcade.SpriteList for batched GPU rendering —
  NOT individual draw calls per star

### Star properties (randomised per star on init)
- x: random across window width
- y: random across window height
- speed: random between `star_speed_min` and `star_speed_max`
  (defaults: 20 and 120 pixels/second)
- size: random between 1.0 and 3.0 pixels radius
- brightness: random integer between 120 and 255 (greyscale white)

```python
class ProceduralStarField:
    def __init__(self, window_width: int, window_height: int,
                 star_count: int = 300,
                 speed_min: float = 20.0,
                 speed_max: float = 120.0):
        ...

    def _rebuild(self) -> None:
        """Rebuild ShapeElementList from current star positions.
        Called on init and whenever any star wraps."""

    def update(self, delta_time: float) -> None:
        """Scroll all stars downward by their individual speed * delta_time.
        Wrap stars that exit the bottom back to the top with new random x.
        Trigger _rebuild() if any star wrapped this frame."""

    def draw(self) -> None:
        """Draw the ShapeElementList — single GPU call."""
```

## game_config.toml additions

```toml
[background]
background_image = "assets/images/Backgrounds/darkPurple.png"
star_count = 300
star_speed_min = 20.0
star_speed_max = 120.0
```

## Sharing background across views

Background and star field instances are created once on the Window and
passed into each View that needs them, rather than recreated per View.
This avoids re-generating stars on every state transition and keeps
scrolling continuous across screen changes.

```python
# In arcade.Window subclass (main.py):
class SpaceAttackersWindow(arcade.Window):
    def __init__(self):
        super().__init__(800, 600, "Space Attackers")
        self.background = StaticBackground(config.background_image,
                                           self.width, self.height)
        self.star_field = ProceduralStarField(self.width, self.height,
                                              config.star_count,
                                              config.star_speed_min,
                                              config.star_speed_max)

# In each View:
def on_update(self, delta_time):
    self.window.star_field.update(delta_time)

def on_draw(self):
    self.clear()
    self.window.background.draw()
    self.window.star_field.draw()
    # ... rest of draw
```

## Unit tests required

All tests must run without a display.

- ProceduralStarField initialises with correct star count
- All star speeds are within configured min/max range
- update() moves stars downward by speed * delta_time
- Stars that reach y < 0 wrap to y = window_height
- Wrapped stars get a new random x position
- _rebuild() is called when a star wraps, not called when no wraps occur
- Star field is independent of frame rate (delta_time scaled)

## Implementation notes

- ShapeElementList cannot update individual element positions — a full
  rebuild is required when any star moves. This is acceptable because
  only 1-2 stars wrap per frame on average
- StaticBackground and ProceduralStarField are instantiatable without a
  display for testing — accept optional pre-built shape lists via
  constructor parameter in tests
- Background image path resolved via resource_path() for PyInstaller
  compatibility
- If the Kenney background PNG is not square, scale width and height
  independently to fill the window — do not maintain aspect ratio
