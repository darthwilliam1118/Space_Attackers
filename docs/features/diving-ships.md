# Feature: Diving Ships

## Overview
Starting from level 2, groups of enemy ships periodically break from the
formation and execute a swooping dive toward the player, dropping bombs
during the pass, then looping back to their original grid position.
The number of diving ships and frequency of dives scale with level
progression. Diving ships are worth double points if destroyed mid-dive.

## Files
- src/space_attackers/enemies/dive_controller.py  — DiveController class
- src/space_attackers/enemies/diving_ship.py      — DivingShip class
- src/space_attackers/enemies/dive_path.py        — path generation helpers

## Level scaling

Dive behaviour is determined entirely by level number. All parameters
computed from level in DiveController, not stored in game_config.toml
as fixed values — they are functions of level.

### Ships per dive group
```
dive_group_size = min(level - 1, dive_group_size_max)
```
- Level 1: 0 (no diving)
- Level 2: 1 ship per group
- Level 3: 2 ships per group
- Level 4+: increases by 1 per level up to `dive_group_size_max`
- dive_group_size_max configurable (default: 4)

### Interval between dive groups
```
dive_interval = max(
    dive_interval_min,
    dive_interval_base - (level - 2) * dive_interval_step
)
```
- dive_interval_base: starting interval in seconds (default: 12.0)
- dive_interval_step: seconds subtracted per level (default: 1.0)
- dive_interval_min: floor interval (default: 4.0)
- Level 2: 12s between groups
- Level 6: 8s between groups
- Level 10+: 4s between groups (floor)

### Dive speed
```
dive_speed = dive_speed_base + (level - 2) * dive_speed_step
dive_speed = min(dive_speed, dive_speed_max)
```
- dive_speed_base: pixels/second at level 2 (default: 200)
- dive_speed_step: added per level (default: 15)
- dive_speed_max: ceiling (default: 380)

## game_config.toml additions

```toml
[diving]
dive_group_size_max = 4
dive_interval_base = 12.0
dive_interval_step = 1.0
dive_interval_min = 4.0
dive_speed_base = 200.0
dive_speed_step = 15.0
dive_speed_max = 380.0
dive_bomb_speed = 220.0
dive_bonus_points = 20
dive_return_speed = 160.0
```

## Dive group selection

- DiveController selects `dive_group_size` ships randomly from all
  currently alive grid ships that are NOT already diving
- Selection is uniformly random across the entire grid — no row weighting
- If fewer eligible ships exist than dive_group_size, dive all eligible
  ships (no minimum required)
- Selected ships are removed from the EnemyGrid's SpriteList and handed
  to DiveController as DivingShip instances
- Their grid slots become visually empty during the dive (same as a
  destroyed ship)
- On successful return, ships are re-inserted into EnemyGrid's SpriteList
  at their original grid position

## Dive path — Bézier curve arc

Each diving ship follows a cubic Bézier curve from its grid position
down toward the player and back up to its grid start position. This
produces the classic Galaga swooping arc.

### Path definition

```python
def make_dive_path(start: tuple[float, float],
                   player_x: float,
                   window_height: int,
                   window_width: int) -> list[tuple[float, float]]:
    """
    Generate a cubic Bézier curve as a list of (x, y) waypoints.

    Control points:
      P0 = start (ship's grid position)
      P1 = (start_x + curve_offset, start_y - window_height * 0.3)
           — pulls the curve sideways early in the descent
      P2 = (player_x, window_height * 0.25)
           — aims toward player in the lower portion of screen
      P3 = start (returns to grid position)

    curve_offset: random choice of +/- 120 to 200 pixels so each ship
    arcs from a different side, adding visual variety.

    Evaluate the curve at N evenly spaced t values (0.0 to 1.0),
    returning a list of (x, y) waypoints. N = 120 gives smooth motion
    at 60fps for a ~2 second dive.
    """
```

### Waypoint following

DivingShip follows the precomputed waypoint list in order each frame,
advancing by `dive_speed * delta_time` pixels along the path. When the
ship reaches the final waypoint it transitions to RETURNING state.

Using precomputed waypoints rather than evaluating Bézier per frame:
- Simplifies state management
- Makes path length calculation straightforward
- Easier to unit test

## DivingShip state machine

Each DivingShip has its own internal state:

```
DIVING → (reaches bottom half of screen) → BOMBING → (continues path) →
RETURNING → (reaches grid position) → DONE
```

States:
- **DIVING**: following waypoint path downward, no bombs yet
- **BOMBING**: fires one bomb at player's current x position, then
  continues following path — transition back to DIVING until path complete
- **RETURNING**: path is complete, ship moves directly back to grid
  position at `dive_return_speed` (slower than dive speed — more relaxed
  return arc)
- **DONE**: ship has returned to grid position, signals DiveController
  to re-insert it into EnemyGrid

Bombing trigger: when ship's center_y drops below window_height * 0.55
(just below midscreen), fire one bomb and transition to BOMBING. Only
one bomb per dive pass — do not fire again on the return path.

## Group formation timing

When a group of N ships dives together:
- Ships launch with a stagger delay of 0.3 seconds between each
- First ship launches immediately, second after 0.3s, third after 0.6s
- Each ship generates its own independent Bézier path with different
  curve_offset so they fan out visually rather than overlapping
- Ships are otherwise fully independent — each has its own state,
  position, and bomb

## Bomb behaviour

- DivingShip bomb is a separate sprite (reuse EnemyBullet from enemy
  grid feature — same asset, same downward movement)
- Fired at player's current x position at moment of firing (snapshot,
  not tracking)
- Bomb travels straight down at `dive_bomb_speed` pixels/second
- Removed when it exits the bottom of screen or hits player
- Bomb collision with player follows same rules as grid enemy bullets
  (respects invincibility frames)
- Only one bomb per ship per dive — if the ship is destroyed mid-dive
  its bomb continues independently until it exits or hits

## Collision and scoring

- DivingShip collision with player bullet:
  - Ship destroyed (gone permanently — does NOT return to grid)
  - Award `dive_bonus_points` (default: 20) to active player score
  - Spawn ScorePopup showing "+20"
  - Spawn destruction effect (ExplosionSprite + particles + shockwave)
  - If this was the last enemy (grid + diving combined), trigger
    LEVEL_COMPLETE
- DivingShip collision with player ship:
  - Trigger PLAYER_KILLED (respects invincibility frames)
  - DivingShip is also destroyed — gone permanently
  - Award dive_bonus_points to score (player still gets credit)
- No collision with other diving ships or grid ships

## Interaction with EnemyGrid

DiveController and EnemyGrid must stay loosely coupled:

- DiveController calls `enemy_grid.remove_for_dive(ship)` to extract a
  ship from the grid before diving
- DiveController calls `enemy_grid.return_from_dive(ship)` when ship
  returns to re-insert at grid position
- EnemyGrid.is_cleared() must check both grid sprites AND active diving
  ships — level is not complete while ships are still in flight
- EnemyGrid.get_sprite_list() excludes currently diving ships (already
  removed during dive)
- EnemyGrid boundary check (side margin reversal) uses surviving
  non-diving ships to determine outermost position

## Class design

```python
class DiveController:
    def __init__(self, config: DivingConfig, window_width: int,
                 window_height: int):
        ...

    def setup(self, level: int, enemy_grid: 'EnemyGrid') -> None:
        """Compute level-scaled parameters. Reset dive timer."""

    def update(self, delta_time: float,
               enemy_grid: 'EnemyGrid',
               player_ship: 'PlayerShip',
               bullet_sprite_list: arcade.SpriteList) -> list[GameEvent]:
        """
        - Advance dive timer
        - On timer expiry: select ships, launch group, reset timer
        - Update all active DivingShips
        - Check bullet collisions with diving ships
        - Collect and return GameEvents from this frame
        """

    def launch_group(self, enemy_grid: 'EnemyGrid',
                     player_x: float) -> None:
        """Select random eligible ships, create DivingShip instances
        with staggered launch timers, extract from grid."""

    def get_all_sprites(self) -> arcade.SpriteList:
        """Returns SpriteList of all currently airborne diving ships
        for rendering and collision detection."""

    def get_all_bullets(self) -> arcade.SpriteList:
        """Returns SpriteList of all active dive bombs."""

    def active_count(self) -> int:
        """Number of ships currently in flight."""

    def has_any_airborne(self) -> bool:
        """True if any ships are currently diving or returning."""
```

```python
class DivingShip(arcade.Sprite):
    def __init__(self, source_sprite: EnemySprite,
                 waypoints: list[tuple[float, float]],
                 config: DivingConfig,
                 launch_delay: float = 0.0):
        """
        source_sprite: the EnemySprite being extracted from the grid.
        Copies texture, color, col, row from source.
        waypoints: precomputed Bézier path.
        launch_delay: seconds to wait before starting movement (stagger).
        """

    def update(self, delta_time: float,
               player_x: float) -> list[GameEvent]:
        """Advance state machine, move along path, fire bomb if ready."""

    @property
    def is_done(self) -> bool:
        """True when ship has returned to grid position."""

    @property
    def grid_position(self) -> tuple[int, int]:
        """(col, row) for re-insertion into EnemyGrid."""

    def get_bomb(self) -> 'EnemyBullet | None':
        """Returns active bomb sprite if one has been fired, else None."""
```

```python
# dive_path.py

def make_dive_path(start: tuple[float, float],
                   player_x: float,
                   window_height: int,
                   window_width: int,
                   num_waypoints: int = 120) -> list[tuple[float, float]]:
    """Generate Bézier waypoint list for a dive arc."""

def bezier_point(p0, p1, p2, p3,
                 t: float) -> tuple[float, float]:
    """Evaluate cubic Bézier at parameter t (0.0 to 1.0)."""
```

## Integration in RUN_LEVEL

```python
# Initialise alongside EnemyGrid in on_show_view():
self.dive_controller = DiveController(config.diving,
                                      self.window.width,
                                      self.window.height)
self.dive_controller.setup(level, self.enemy_grid)

# In on_update():
events += self.dive_controller.update(
    delta_time,
    self.enemy_grid,
    self.player_ship,
    self.player_bullet_list
)

# In on_draw() — diving ships draw above grid, below HUD:
self.dive_controller.get_all_sprites().draw()
self.dive_controller.get_all_bullets().draw()

# Level complete check must include diving ships:
def is_level_cleared(self) -> bool:
    return (self.enemy_grid.is_cleared() and
            not self.dive_controller.has_any_airborne())
```

## 2P player switching — dive completion before snapshot

In a 2P game, a player switch (SAVE_SNAPSHOT_AND_SWITCH) must NOT occur
while ships are airborne. This eliminates snapshot complexity for diving
ships entirely — the snapshot is always taken with a clean DiveController
state.

### Waiting for dives to complete

When a PLAYER_KILLED event occurs in 2P mode and lives > 0, RUN_LEVEL
enters a WAITING_FOR_DIVES sub-state before proceeding to
SAVE_SNAPSHOT_AND_SWITCH:

```python
# In RUN_LEVEL event handling (2P, lives > 0):
if game_event == GameEvent.PLAYER_KILLED and num_players == 2:
    self.player_ship.kill()          # remove ship, start explosion
    self.waiting_for_dives = True    # enter waiting sub-state
    self.new_dive_launches_blocked = True  # prevent new groups launching

# In on_update(), while waiting_for_dives:
if self.waiting_for_dives:
    if not self.dive_controller.has_any_airborne():
        self.waiting_for_dives = False
        self.state_manager.transition(SAVE_SNAPSHOT_AND_SWITCH)
```

### Behaviour during wait

- Player ship is already destroyed — no ship on screen
- Enemy grid continues moving and shooting normally
- Dive timer is paused — no new dive groups are launched
- Existing airborne ships complete their current dive and return to grid
  at normal speed
- Active dive bombs continue flying and are removed when they exit the
  screen (no player to hit — skip collision checks while waiting)
- Wait is typically very short (1-3 seconds at most since ships are
  already mid-arc and return quickly)
- No visual indicator shown to the player — the brief pause feels natural

### Snapshot content (simplified)

Because the snapshot is always taken after all dives complete, the
DiveController snapshot only needs to capture:

- dive_timer: seconds elapsed since last group launch (so interval
  resumes correctly for the returning player)
- Dive timer is NOT reset on restore — the returning player resumes
  from where their timer was when they left

```python
# In DiveController:
def to_snapshot(self) -> dict:
    """Returns minimal state — no airborne ships guaranteed."""
    return {
        'dive_timer': self.dive_timer,
        'level': self.current_level,
    }

@classmethod
def from_snapshot(cls, snapshot: dict, config: DivingConfig,
                  window_width: int,
                  window_height: int) -> 'DiveController':
    """Restore DiveController from snapshot. No airborne ships
    to restore."""
    controller = cls(config, window_width, window_height)
    controller.setup(snapshot['level'], enemy_grid=None)
    controller.dive_timer = snapshot['dive_timer']
    return controller
```

### 1P mode — no change

In 1P mode, PLAYER_KILLED proceeds immediately to the respawn sequence
regardless of dive state. Airborne ships continue their dive during the
explosion animation and invincibility frames — this is intentional and
adds tension during respawn.

## Debug shortcuts (retain existing, add new)

Add to existing RUN_LEVEL debug shortcuts (marked # DEBUG):

- Shift+D — immediately trigger a dive group regardless of timer,
  useful for testing dive behaviour without waiting

## Unit tests required

All tests must run without a display.

### dive_path.py
- bezier_point() returns P0 at t=0.0
- bezier_point() returns P3 at t=1.0
- bezier_point() returns a point between P0 and P3 for 0 < t < 1
- make_dive_path() returns list of length num_waypoints
- make_dive_path() first waypoint equals start position
- make_dive_path() last waypoint equals start position (path returns)
- make_dive_path() waypoints reach below midscreen (dive goes deep enough)

### DivingShip
- Initialises with DIVING state and correct grid_position
- Does not move during launch_delay period
- Transitions to BOMBING state when center_y crosses trigger threshold
- Fires exactly one bomb per dive pass
- Does not fire bomb on return path
- Transitions to RETURNING after final waypoint reached
- is_done returns True only after reaching grid position in RETURNING
- Advancing waypoints is delta_time scaled

### DiveController
- Level 1: dive_group_size == 0, no dives launched
- Level 2: dive_group_size == 1
- dive_interval decreases with level, floors at dive_interval_min
- dive_speed increases with level, caps at dive_speed_max
- launch_group() selects only from non-diving alive ships
- launch_group() handles fewer eligible ships than group size
- Stagger delay: second ship launches 0.3s after first
- Ships returned to grid on is_done (return_from_dive called)
- has_any_airborne() returns False when no ships in flight
- GameEvent.LEVEL_COMPLETE not emitted while has_any_airborne() is True
- to_snapshot() returns dict with dive_timer and level keys only
- to_snapshot() does not include airborne ship data
- from_snapshot() restores dive_timer correctly
- No new groups launched when new_dive_launches_blocked is True

### RUN_LEVEL 2P waiting behaviour
- PLAYER_KILLED in 2P with lives > 0 sets waiting_for_dives = True
- SAVE_SNAPSHOT_AND_SWITCH not triggered while has_any_airborne() is True
- SAVE_SNAPSHOT_AND_SWITCH triggered immediately when has_any_airborne()
  returns False
- New dive launches blocked during waiting_for_dives
- Dive bombs skip player collision checks during waiting_for_dives
- 1P PLAYER_KILLED proceeds immediately regardless of dive state

## Implementation notes

- DivingShip copies its texture from the source EnemySprite — do not
  reload from disk. Textures are shared references in Arcade, copy is free.
- DiveController returns GameEvents list from update() same pattern as
  EnemyGrid — no direct state machine calls
- dive_path.py has zero Arcade dependencies — pure math, fully testable
  without display or game context
- curve_offset sign (left vs right arc) should be random per ship but
  consistent within a group launch — if the group curves left, all ships
  in that group curve left with varying magnitude. This looks more
  intentional than each ship randomly picking a direction.
- During a dive, the diving ship's grid slot in EnemyGrid shows as empty.
  The boundary check for grid reversal should not count empty dive slots
  as the outermost ship — same logic as destroyed ships.
- Bomb inherits from EnemyBullet — no new class needed. Pass the dive
  bomb into the same enemy_bullets SpriteList used by EnemyGrid for
  unified collision detection with the player ship in RUN_LEVEL.
```
