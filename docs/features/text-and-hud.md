# Feature: Text and HUD

## Overview
All in-game text uses arcade.Text objects (never arcade.draw_text()) to
avoid per-frame texture allocation. The HUD displays score, lives, and
level during RUN_LEVEL. Other views (MAIN, GAME_OVER, LEVEL_COMPLETE,
SPLASH) have their own text layouts. All text uses the Kenvector Future
font from the Kenney Space Shooter Redux pack for visual consistency
with the sprites.

## Files
- src/ui/hud.py       — HUD class for RUN_LEVEL
- src/ui/text_utils.py — shared helpers

## Fonts

Two TTF fonts ship with Kenney Space Shooter Redux:

| File | Internal name | Use |
|------|--------------|-----|
| kenvector_future.ttf | "KenVector Future" | Headings, scores, HUD |
| kenvector_future_thin.ttf | "KenVector Future Thin" | Body text, instructions |

Load both once at application startup in SpaceAttackersWindow.__init__(),
before any View is shown:

```python
arcade.load_font(resource_path("assets/fonts/kenvector_future.ttf"))
arcade.load_font(resource_path("assets/fonts/kenvector_future_thin.ttf"))
```

Font name is the internal name shown in the font preview, NOT the
filename. If the wrong name is used Arcade silently falls back to the
system default — verify by checking the rendered output looks correct.

## Rule: never use arcade.draw_text() inside on_draw()

arcade.draw_text() allocates a new OpenGL texture every call. At 60fps
this causes the Arcade performance warning and degrades frame time.

Always:
1. Create arcade.Text objects once in on_show_view() or __init__()
2. Update .text property only when the displayed value changes
3. Call .draw() inside on_draw()

## HUD layout (RUN_LEVEL)

```
+--------------------------------------------------+
| SCORE: 12400          LEVEL: 3      LIVES: ♥♥♥  |
+--------------------------------------------------+
```

- HUD rendered at top of window, y = window_height - 24
- Score: left-aligned, x = 16
- Level: center-aligned, x = window_width / 2
- Lives: right-aligned, x = window_width - 16

In 2P mode display both players:

```
+--------------------------------------------------+
| P1: 12400    LEVEL: 3    P2: 8200               |
| LIVES: ♥♥♥              LIVES: ♥♥               |
+--------------------------------------------------+
```

Active player's score and lives are rendered in WHITE.
Inactive player's score and lives are rendered in a muted color
(128, 128, 128, 255) to indicate they are not currently playing.

### HUD class

```python
class HUD:
    def __init__(self, window_width: int, window_height: int,
                 num_players: int):
        """Create all arcade.Text objects. Font must already be loaded."""

    def update(self, player_states: list[PlayerState],
               active_player: int, level: int) -> None:
        """Update text content if values have changed since last call.
        Uses cached last-known values to avoid unnecessary texture
        rebuilds — only update .text when value actually differs."""

    def draw(self) -> None:
        """Call .draw() on all Text objects."""
```

## arcade.Text reference

```python
arcade.Text(
    text="SCORE: 0",
    x=16,
    y=window_height - 24,
    color=arcade.color.WHITE,        # or RGBA tuple
    font_size=16,
    font_name="Kenvector Future",
    anchor_x="left",                 # "left", "center", "right"
    anchor_y="center",               # "top", "center", "baseline", "bottom"
    bold=False,
    italic=False,
    multiline=False,
    width=None,                      # required if multiline=True
    align="left",                    # "left", "center", "right" for multiline
    rotation=0.0
)
```

## Text layouts per view

### SPLASH
- Centered "LOADING..." text, font_size=24, anchor_x="center"
- Optional: asset loading progress (update .text as assets load)

### MAIN
- "SPACE ATTACKERS" title: centered, font_size=48, y=75% window height
- Cycling subtitle (leaderboard / instructions / demo): centered,
  font_size=18, Kenvector Future Thin
- "PRESS 1 OR 2 TO START": centered, font_size=16, animated alpha
  (pulse using sin — see Animated text below)
- "C — CONFIG    X — EXIT": centered, font_size=14, muted color

### LEVEL_COMPLETE
- "LEVEL COMPLETE": centered, font_size=48
- "LEVEL N": centered, font_size=24, below title
- Per-player lives display: centered, font_size=18
- "GET READY...": centered, font_size=16, appears after 1 second delay

### GAME_OVER
- "GAME OVER": centered, font_size=48, arcade.color.RED
- Final score(s): centered, font_size=24
- "NEW HIGH SCORE!" if applicable: centered, font_size=18,
  arcade.color.YELLOW
- "PRESS ANY KEY": centered, font_size=14, animated alpha

### SCORE_ENTRY (stub)
- "ENTER YOUR NAME": centered, font_size=24
- Player initial entry field: centered, font_size=32
- Score value: centered, font_size=18

## Animated text

For pulsing or flashing prompts, animate the alpha channel of the
color tuple in on_update():

```python
# Pulsing prompt — smooth sine wave
self.prompt_elapsed += delta_time
alpha = int(abs(math.sin(self.prompt_elapsed * 3.0)) * 255)
self.start_prompt.color = (255, 255, 255, alpha)

# Flashing prompt — binary on/off
self.flash_elapsed += delta_time
visible = int(self.flash_elapsed / 0.5) % 2 == 0
self.press_key_text.color = (255, 255, 255, 255 if visible else 0)
```

## Centering helpers

```python
# text_utils.py

def centered_text(text: str, window_width: int, y: int,
                  font_size: int = 16,
                  color=arcade.color.WHITE,
                  font_name: str = "Kenvector Future") -> arcade.Text:
    """Returns an arcade.Text centered horizontally on screen."""
    return arcade.Text(
        text=text,
        x=window_width / 2,
        y=y,
        color=color,
        font_size=font_size,
        font_name=font_name,
        anchor_x="center",
        anchor_y="center"
    )
```

## game_config.toml additions

No new config keys required — font paths are fixed assets.
Font sizes could be made configurable if needed for different resolutions
but hardcoded values are acceptable for initial implementation.

## Unit tests required

All tests must run without a display. Because arcade.Text requires an
OpenGL context, unit tests for HUD should use dependency injection:

- HUD.update() correctly detects changed score and updates text content
- HUD.update() does NOT update text content when value is unchanged
  (verify by checking a mock or subclassed Text that tracks assignments)
- HUD renders active player text in WHITE and inactive in muted color
- centered_text() returns Text with anchor_x="center" and x=window_width/2
- Animated alpha produces values in range 0-255

## Implementation notes

- arcade.Text objects require an active OpenGL context to instantiate.
  Create them in on_show_view(), not in __init__(), to ensure the context
  is ready.
- Exception: HUD is created by RUN_LEVEL in on_show_view() — acceptable.
- Font loading in SpaceAttackersWindow.__init__() must happen before any
  view is shown. If a View tries to create a Text object with a font
  that has not been loaded yet, Arcade silently uses the system default.
- For tests that need to verify text content without a display, extract
  the value-tracking logic (last_score, last_lives, etc.) into a separate
  method that can be tested independently of arcade.Text.
- All text in the game should use one of the two Kenvector fonts. Do not
  introduce system fonts or other TTF files without updating this spec.
