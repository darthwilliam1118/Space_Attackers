# Feature: Player Ship

## Overview
The player ship is the primary player-controlled entity in RUN_LEVEL. It
moves in a constrained zone at the bottom of the screen, fires bullets
upward, and is destroyed on collision with an enemy projectile or enemy
ship. In 2P mode only one ship is visible at a time — the active player's
ship.

## Ship movement

- Moves left/right and limited forward/back within a constrained zone at
  the bottom of the screen
- Movement zone: full screen width horizontally, bottom 20% of screen
  vertically (configurable as `ship_zone_height_pct` in game_config.toml)
- Hard stops at all four edges of the movement zone — no wrapping
- Movement is frame-rate independent, driven by delta_time
- Ship speed configurable in game_config.toml as `ship_speed` (default: 300
  pixels/second)
- Controls:
  - Left arrow or A — move left
  - Right arrow or D — move right
  - Up arrow or W — move forward (up, constrained to zone)
  - Down arrow or S — move backward (down, constrained to zone)
  - Spacebar — fire

## Shooting

- Single bullet on screen at a time
- After a bullet is fired, a cooldown must expire before firing again
- Cooldown configurable in game_config.toml as `fire_cooldown` (default:
  0.3 seconds)
- Bullet travels straight up at a fixed speed configurable as
  `bullet_speed` (default: 500 pixels/second)
- Bullet is removed when it exits the top of the screen or hits an enemy
- If a bullet is already on screen, spacebar input is ignored until the
  cooldown expires — do NOT wait for the bullet to leave the screen, just
  enforce the time-based cooldown

## Asset paths

All assets loaded via resource_path() helper for PyInstaller compatibility.

### Ship sprites
- Player 1: `assets/images/PNG/playerShip1_blue.png`
- Player 2: `assets/images/PNG/playerShip2_red.png`

### Laser sprites
- Player 1 bullet: `assets/images/PNG/Lasers/laserBlue01.png`
- Player 2 bullet: `assets/images/PNG/Lasers/laserRed01.png`

### Explosion sprite sheet
- Path: `assets/images/exp2_0.png`
- Frame size: 64x64 pixels
- Layout: frames arranged in a grid; bottom-right frame is the smallest
  explosion, frames increase in size toward the top-left
- Animation sequence: run all frames from smallest to largest, then back
  down to smallest (ping-pong), then remove the sprite
- Load via arcade.load_spritesheet() slicing into 64x64 frames

## Spawn and respawn

- On level start, ship spawns at horizontal center, bottom of movement zone
- On respawn (after losing a life), ship returns to same default spawn
  position
- Spawn safety: invincibility frames active for `spawn_invincible_duration`
  seconds after spawn/respawn (default: 2.0, configurable in
  game_config.toml)
- During invincibility, ship flashes (alternate visible/invisible every
  0.1s) to signal to the player it is protected
- Invincibility does NOT affect the ability to move or fire

## Collision and death

- Ship is destroyed on collision with:
  - Any enemy projectile
  - Any enemy sprite (diving or formation)
- No collision during invincibility frames
- On destruction, trigger an ExplosionSprite at ship position
- Fire PLAYER_KILLED transition on the GameStateManager after explosion
  completes (do not transition mid-explosion)
- Explosion duration before transition: determined by full ping-pong
  animation cycle completing

## Explosion animation

- ExplosionSprite is a self-contained arcade.Sprite subclass
- On init, load all frames from exp2_0.png via arcade.load_spritesheet()
  with frame size 64x64
- Determine frame order: sheet is laid out so bottom-right is smallest —
  slice the sheet and reverse the frame list so index 0 = smallest frame
- Animation plays ping-pong: forward through all frames (small to large),
  then backward (large to small)
- On completion of the full ping-pong cycle, call remove_from_sprite_lists()
- Frame timing: configurable as `explosion_frame_duration` (default: 0.05
  seconds per frame)
- ExplosionSprite must determine the grid dimensions from the sheet
  dimensions divided by 64 — do not hardcode row/column counts so the sheet
  can be swapped without code changes

## Debug / test UI (retain existing behaviour)

The following keyboard shortcuts must remain active in RUN_LEVEL for
testing purposes until enemy logic is implemented:

- `W` key — simulate level complete (WIN), triggers LEVEL_COMPLETE
  transition
- `L` key — simulate player killed, triggers PLAYER_KILLED sequence
  including explosion animation and lives decrement

These shortcuts must be clearly marked in code with a `# DEBUG` comment
and should not interfere with ship movement (W is also move-forward —
resolve by only treating W as win when a debug modifier such as Shift is
held, i.e. Shift+W = win, plain W = move forward).

## 2P mode

- Only the active player's ship is instantiated and visible during
  RUN_LEVEL
- Ship sprite is selected based on player_num from PlayerState:
  player_num == 1 uses playerShip1_blue, player_num == 2 uses
  playerShip2_red. Same logic applies to bullet sprite selection.
- When player switch occurs (SAVE_SNAPSHOT_AND_SWITCH), the current ship
  is removed and the incoming player's ship is spawned fresh at default
  position with invincibility frames active
- Each player's ship state (position at time of death) is NOT saved to
  level_snapshot — ship always respawns at default position

## game_config.toml additions
```toml
[ship]
ship_speed = 300
fire_cooldown = 0.3
bullet_speed = 500
spawn_invincible_duration = 2.0
ship_zone_height_pct = 0.20
explosion_frame_duration = 0.05
```

## Class design
```python
class PlayerShip(arcade.Sprite):
    def __init__(self, player_num: int, config: ShipConfig,
                 window_width: int, window_height: int):
        ...

    def update(self, delta_time: float) -> None:
        """Apply movement, update cooldown timer, update invincibility
        flash."""

    def try_fire(self) -> PlayerBullet | None:
        """Returns a PlayerBullet if cooldown has expired, else None."""

    def apply_movement(self, keys_held: set, delta_time: float) -> None:
        """Move ship based on held keys, clamp to movement zone."""

    def start_invincibility(self) -> None:
        """Begin invincibility timer and flash effect."""

    def is_invincible(self) -> bool:
        """Returns True if invincibility frames are still active."""

    def kill(self) -> ExplosionSprite:
        """Remove ship, return an ExplosionSprite at this position."""
```
```python
class PlayerBullet(arcade.Sprite):
    def __init__(self, x: float, y: float, speed: float,
                 texture_path: str):
        ...

    def update(self, delta_time: float) -> None:
        """Move bullet upward, remove if off screen."""
```
```python
class ExplosionSprite(arcade.Sprite):
    def __init__(self, x: float, y: float,
                 frame_duration: float = 0.05):
        """Load exp2_0.png, build ping-pong frame sequence, begin
        animation."""

    def update(self, delta_time: float) -> None:
        """Advance frame, handle ping-pong reversal, remove on
        completion."""

    @property
    def is_complete(self) -> bool:
        """True after full ping-pong cycle has played."""
```

## Unit tests required

All tests must run without a display. Cover:

- Ship initialises at correct spawn position for given window dimensions
- Movement clamps correctly at all four zone boundaries
- Movement is delta_time scaled (not frame-dependent)
- try_fire() returns None during cooldown, returns bullet after cooldown
  expires
- try_fire() returns None when called within cooldown window
- Bullet sprite path is correct for player 1 and player 2
- start_invincibility() sets correct timer
- is_invincible() returns False after duration expires
- Flash state toggles correctly during invincibility at 0.1s intervals
- kill() returns an ExplosionSprite at the correct position
- PlayerBullet removes itself when y position exceeds screen height
- ExplosionSprite ping-pong sequence is correctly ordered (small to large
  to small)
- ExplosionSprite calls remove_from_sprite_lists() after full cycle
- is_complete returns False mid-animation, True after full cycle
- Shift+W triggers LEVEL_COMPLETE in RUN_LEVEL (debug shortcut)
- L triggers PLAYER_KILLED sequence in RUN_LEVEL (debug shortcut)
- Plain W moves ship forward (not treated as win trigger)

## Implementation notes

- PlayerShip must be instantiatable without a display (no asset loading in
  __init__ — use lazy loading or inject textures)
- ExplosionSprite must also be instantiatable without a display for testing
  — accept a pre-loaded frame list as optional constructor parameter; load
  from disk only if not provided
- ShipConfig is a dataclass populated from game_config.toml at startup
- Keys held state is tracked in RUN_LEVEL view (on_key_press /
  on_key_release) and passed into apply_movement() each frame — ship does
  not read keyboard directly
- GameStateManager reference passed into RUN_LEVEL, not into PlayerShip
  directly — ship signals death via kill(), view handles the state
  transition after explosion is_complete
- ExplosionSprite defined in src/space_attackers/sprites/explosion.py —
  shared module, not inside ship module
- Laser file for player 2 is likely a typo in assets:
  check for both laserRed01.png and lasterRed01.png at runtime and use
  whichever exists, log a warning if falling back