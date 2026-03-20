# Feature: Score Popup

## Overview
When an enemy is destroyed, a small score value floats upward from the
kill position and fades out over ~0.8 seconds. This gives immediate
visual feedback for every kill and reinforces the scoring system. Score
popups are managed as a list in RUN_LEVEL and are self-contained objects
that signal completion via an is_done property.

## Files
- src/space_attackers/ui/score_popup.py — ScorePopup class

## Behaviour

- Appears at the center position of the destroyed enemy
- Displays the point value as "+10" (or whatever the score value is)
- Floats upward at `popup_rise_speed` pixels/second (default: 60)
- Fades out linearly over `popup_duration` seconds (default: 0.8)
- Uses arcade.Text object internally — not a sprite
- Marks itself as done when duration expires
- Caller removes done popups from the list each frame

## Class design

```python
class ScorePopup:
    def __init__(self, x: float, y: float, value: int,
                 duration: float = 0.8,
                 rise_speed: float = 60.0):
        """
        Create arcade.Text object at (x, y) displaying "+{value}".
        Font: "Kenvector Future", font_size=14, anchor_x="center".
        Color: arcade.color.YELLOW initially.
        duration: total seconds before popup is done.
        rise_speed: pixels per second the text floats upward.

        Note: arcade.Text requires an active OpenGL context.
        For testability, accept an optional pre-built text object
        via constructor parameter in tests.
        """
        self.elapsed = 0.0
        self.duration = duration
        self.rise_speed = rise_speed
        self.done = False

    def update(self, delta_time: float) -> None:
        """
        Each frame:
        - elapsed += delta_time
        - If elapsed >= duration: self.done = True, return
        - t = elapsed / duration  (0.0 -> 1.0)
        - Move upward: label.y += rise_speed * delta_time
        - Fade out: label.color = (255, 220, 50, int(255 * (1.0 - t)))
        """

    def draw(self) -> None:
        """Draw the text label if not done."""

    @property
    def is_done(self) -> bool:
        return self.done
```

## Integration in RUN_LEVEL

```python
# In RUN_LEVEL:
self.score_popups: list[ScorePopup] = []

# On enemy destroyed (in event handling):
popup = ScorePopup(enemy.center_x, enemy.center_y, points)
self.score_popups.append(popup)

# In on_update():
for popup in self.score_popups:
    popup.update(delta_time)
self.score_popups = [p for p in self.score_popups if not p.is_done]

# In on_draw() — after scene, before HUD:
for popup in self.score_popups:
    popup.draw()
```

## Visual spec

- Text: "+{value}" e.g. "+10"
- Font: "Kenvector Future", size 14
- Starting color: (255, 220, 50, 255) — warm yellow
- Ending color: (255, 220, 50, 0) — same yellow, fully transparent
- Starting position: center_x and center_y of destroyed enemy
- anchor_x: "center" — popup centered on kill position horizontally

## Multiple simultaneous popups

Multiple popups can be active simultaneously — one per enemy destroyed.
Each is independent with its own elapsed timer and position. No maximum
cap required for a standard game since the player can only fire one
bullet at a time making rapid simultaneous kills impossible.

## game_config.toml additions

```toml
[ui]
popup_duration = 0.8
popup_rise_speed = 60.0
```

## Unit tests required

All tests must run without a display. Inject a mock or stub text object
via the optional constructor parameter to avoid needing an OpenGL context.

- ScorePopup.update() moves text upward by rise_speed * delta_time
- ScorePopup.update() reduces alpha linearly from 255 to 0 over duration
- ScorePopup.is_done returns False before duration expires
- ScorePopup.is_done returns True when elapsed >= duration
- ScorePopup.draw() does not raise when is_done is True
- Multiple ScorePopup instances are independent (different positions,
  different elapsed timers)
- Text displays correct "+{value}" format for various score values

## Implementation notes

- arcade.Text requires an active OpenGL context — create the Text object
  in ScorePopup.__init__() which is called from RUN_LEVEL's on_update()
  handler, at which point the context is guaranteed to be active
- For unit tests, accept an optional `_text_obj` parameter in __init__()
  that replaces the arcade.Text with a test double:
    def __init__(self, x, y, value, duration=0.8, rise_speed=60.0,
                 _text_obj=None):
- ScorePopup has no knowledge of the score system — it receives the
  numeric value from the caller and displays it. Score accumulation is
  handled by RUN_LEVEL and PlayerState.
- Keep ScorePopup focused on display only. Do not add sound, particle
  effects, or other side effects — those belong in RUN_LEVEL's destruction
  handler.
