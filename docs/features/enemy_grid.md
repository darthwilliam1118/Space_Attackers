# Feature: Enemy Grid

## Overview
Each level spawns a grid of enemy ships that moves as a unit back and
forth across the screen, dropping down each time it bounces off a side
margin. Enemies fire downward at the player. The player destroys enemies
with bullets. If the grid reaches the bottom of the screen or an enemy
collides with the player ship, the player is killed. Destroying all
enemies advances the level.

## Asset paths

Enemy sprites follow this naming pattern:
  assets/images/PNG/Enemies/enemy<Color><N>.png

Where Color is one of: Black, Blue, Green, Red
And N is the ship type digit: 1 through 5

Examples:
  assets/images/PNG/Enemies/enemyBlack1.png
  assets/images/PNG/Enemies/enemyGreen3.png
  assets/images/PNG/Enemies/enemyRed5.png

All assets loaded via resource_path() helper.

## Grid layout

- Grid dimensions configurable in game_config.toml:
    enemy_cols = 5
    enemy_rows = 4
- Grid is horizontally centered in the window on spawn
- Grid occupies the top half of the window vertically, with the topmost
  row starting at 80% of window height and rows spaced evenly downward
- Horizontal spacing: enemies are evenly distributed across window width
  minus a 40px margin on each side, so outermost enemies have 40px
  clearance on spawn
- Each row uses a single ship type and single color, fixed mapping:
    Row 0 (top):    enemyBlack1.png
    Row 1:          enemyBlue2.png
    Row 2:          enemyGreen3.png
    Row 3 (bottom): enemyRed4.png
  (Additional rows if enemy_rows > 4 cycle back through this mapping)
- All enemy positions are stored relative to a grid origin point so the
  entire grid can be moved by updating the origin only
- Destroyed enemies leave an empty space — the grid does NOT compress

## Grid movement

- The entire grid moves as a unit, driven by a single velocity applied to
  the grid origin each frame
- Movement is frame-rate independent, driven by delta_time
- Horizontal speed configurable as `enemy_speed_initial` (default: 80
  pixels/second). Speed increases as enemies are destroyed (see Speed
  Scaling below)
- Reversal trigger: when the outermost surviving enemy in the direction of
  travel reaches within 40px of the window edge (configurable as
  `enemy_side_margin`, default: 40), the grid:
    1. Drops down by `enemy_drop_distance` pixels (default: one ship
       height, ~48px — configurable)
    2. Reverses horizontal direction
- Drop occurs once per bounce throughout the level
- If the bottom edge of any enemy sprite reaches below
  `ship_zone_top` (top of player movement zone), trigger PLAYER_KILLED
  for the active player

## Speed scaling

- As enemies are destroyed, the grid speeds up to maintain tension
- Speed formula:
    current_speed = enemy_speed_initial + (enemies_destroyed /
    total_enemies) * enemy_speed_max_bonus
- `enemy_speed_max_bonus` configurable (default: 120 pixels/second) so
  at full clear speed = 80 + 120 = 200 pixels/second
- Speed is recalculated each time an enemy is destroyed

## Enemy shooting

- Only the bottom-most surviving enemy in each column can fire
- Each active bottom-row enemy fires independently on a random timer
- Fire interval per enemy: random value between `enemy_fire_interval_min`
  and `enemy_fire_interval_max` seconds, re-randomised after each shot
    enemy_fire_interval_min = 1.5
    enemy_fire_interval_max = 4.0
- Enemy bullet travels straight down at `enemy_bullet_speed` (default:
  250 pixels/second)
- Only one bullet per column active at a time — a column cannot fire
  again until its current bullet leaves the screen or hits the player
- Enemy bullet removed when it exits the bottom of the screen
- Enemy bullet collision with player ship: triggers PLAYER_KILLED sequence
  (respects player invincibility frames)
- Enemy bullet sprite: assets/images/PNG/Lasers/laserRed01.png for all
  enemies regardless of color (reuses player 2 laser asset)

## Collision detection

- Player bullet vs enemy grid:
    - Use arcade.check_for_collision_with_list(bullet, enemy_sprite_list)
    - On hit: remove bullet, remove enemy sprite, spawn ExplosionSprite
      at enemy position, add 10 to active player score
    - Check after all movement updates in on_update()
- Enemy sprite vs player ship:
    - Use arcade.check_for_collision_with_list(player_ship, enemy_sprite_list)
    - On hit: trigger PLAYER_KILLED sequence (respects invincibility frames)
- Enemy bullet vs player ship:
    - Use arcade.check_for_collision_with_list(player_ship, enemy_bullets)
    - On hit: trigger PLAYER_KILLED sequence (respects invincibility frames)
- All collision checks skipped during player invincibility frames
- use_spatial_hash=True on enemy_sprite_list (enemies move as a unit so
  spatial hash is rebuilt each frame — test performance, disable if slow)

## Level completion

- After each enemy is destroyed, check if enemy_sprite_list is empty
- If empty: trigger LEVEL_COMPLETE transition
- LEVEL_COMPLETE is triggered immediately when last enemy is destroyed,
  do not wait for explosion to complete (explosion can finish playing
  during the level complete screen)

## Class design
```python
class EnemyGrid:
    """Manages the enemy formation, movement, shooting, and state."""

    def __init__(self, config: EnemyConfig, window_width: int,
                 window_height: int):
        ...

    def setup(self, level: int) -> None:
        """Spawn enemy sprites at correct positions for this level."""

    def update(self, delta_time: float, player_ship: PlayerShip) -> list[GameEvent]:
        """Move grid, update shoot timers, return list of events that
        occurred this frame (EnemyDestroyed, PlayerKilled, LevelComplete).
        No direct state machine calls — events returned to RUN_LEVEL."""

    def apply_player_bullet(self, bullet: PlayerBullet) -> bool:
        """Check bullet against grid. Returns True if hit occurred.
        Caller responsible for removing bullet."""

    def get_bottom_enemies(self) -> list[EnemySprite]:
        """Returns the lowest surviving enemy in each column."""

    def recalculate_speed(self) -> None:
        """Update grid speed based on enemies remaining."""

    def check_boundary(self) -> None:
        """Check if grid should bounce and drop."""

    def is_cleared(self) -> bool:
        """Returns True if no enemies remain."""

    def get_sprite_list(self) -> arcade.SpriteList:
        """Returns the SpriteList for rendering and collision detection."""

    def get_bullet_sprite_list(self) -> arcade.SpriteList:
        """Returns active enemy bullet SpriteList."""

    def to_snapshot(self) -> dict:
        """Serialise full grid state for level_snapshot."""

    @classmethod
    def from_snapshot(cls, snapshot: dict, config: EnemyConfig,
                      window_width: int, window_height: int) -> 'EnemyGrid':
        """Restore EnemyGrid from a saved snapshot."""
```
```python
class EnemySprite(arcade.Sprite):
    def __init__(self, color: str, ship_type: int, col: int, row: int):
        ...
    col: int        # column index in grid
    row: int        # row index in grid
    color: str      # "Black", "Blue", "Green", "Red"
    ship_type: int  # 1-5
```
```python
class EnemyBullet(arcade.Sprite):
    def __init__(self, x: float, y: float, speed: float):
        ...

    def update(self, delta_time: float) -> None:
        """Move bullet downward, remove if off screen."""
```

## game_config.toml additions
```toml
[enemies]
enemy_cols = 5
enemy_rows = 4
enemy_speed_initial = 80
enemy_speed_max_bonus = 120
enemy_side_margin = 40
enemy_drop_distance = 48
enemy_fire_interval_min = 1.5
enemy_fire_interval_max = 4.0
enemy_bullet_speed = 250
```

## Snapshot serialisation

to_snapshot() must capture enough state to fully restore the grid:
- Surviving enemy positions (absolute x, y), col, row, color, ship_type
- Current grid direction (1 or -1)
- Current grid speed
- Current shoot timer state for each column
- Active enemy bullet positions

from_snapshot() must restore all of the above and apply spawn safety
(see state-machine.md) before returning.

## Debug / test UI (retain existing behaviour)

Retain Shift+W and L debug shortcuts from the player ship feature.
Add the following additional debug shortcut in RUN_LEVEL:

- Shift+E — instantly destroy all enemies (triggers LEVEL_COMPLETE),
  useful for testing level advance without playing through

Mark with # DEBUG comment.

## Unit tests required

All tests must run without a display. Cover:

- Grid spawns correct number of sprites (enemy_cols * enemy_rows)
- Each row uses correct color and ship type per mapping table
- Sprites are evenly horizontally spaced within window minus margins
- Grid origin moves correctly each frame scaled by delta_time
- Boundary check triggers drop + direction reversal at correct x threshold
- Drop distance matches enemy_drop_distance config value
- Reversal uses outermost SURVIVING enemy, not original grid edge
  (i.e. destroyed enemies on the edge don't extend the boundary)
- Speed formula produces correct value at 0%, 50%, 100% destruction
- get_bottom_enemies() returns correct sprite per column, updates when
  bottom enemy is destroyed
- apply_player_bullet() returns True on hit, False on miss
- apply_player_bullet() removes correct enemy on hit
- is_cleared() returns False with enemies remaining, True when empty
- to_snapshot() captures all required fields
- from_snapshot() restores grid to equivalent state
- EnemyBullet removes itself when y < 0

## Implementation notes

- EnemyGrid does NOT call the state machine directly — it returns a list
  of GameEvent objects from update(). RUN_LEVEL processes these events
  and makes state machine calls. This keeps EnemyGrid unit testable
  without a display or state machine
- GameEvent is a simple enum or dataclass:
    class GameEvent(Enum):
        PLAYER_KILLED = auto()
        LEVEL_COMPLETE = auto()
        ENEMY_DESTROYED = auto()
- EnemyGrid instantiatable without a display — inject pre-loaded textures
  in tests via optional constructor parameter
- Boundary check uses outermost SURVIVING enemy position, not original
  grid edge — as enemies are destroyed from the sides, the effective
  grid width shrinks and reversal point shifts inward
- to_snapshot() / from_snapshot() used by state machine's
  SAVE_SNAPSHOT_AND_SWITCH and SET_ACTIVE_PLAYER states
