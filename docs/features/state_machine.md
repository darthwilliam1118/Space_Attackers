# Feature: Game State Machine

## Overview
Space Attackers uses an explicit state machine to manage all major game
screens and transitions. All state transitions are driven by either user
input (key presses) or game events (level cleared, player killed, etc.).

## States

### SPLASH
- Entry point on launch
- Loads all assets and game config file in background
- Transitions to MAIN automatically when assets finish loading, or after 5
  seconds, whichever comes first

### MAIN
- Cycles automatically through three pages: leaderboard, instructions, demo game
- Awaits key input to branch:
  - `1` → GAME_INIT (1 player)
  - `2` → GAME_INIT (2 players)
  - `C` → GAME_CONFIG
  - `X` → EXIT

### GAME_CONFIG
- Displays editable game parameters loaded from config file
- Saves changes back to config file on exit
- Returns to MAIN on back/escape

### GAME_INIT
- Receives player count (1 or 2)
- Creates a `PlayerState` object for each player
- Sets level = starting_level (from config, default: 1)
- Initialises game params from config defaults (num_lives, etc.)
- Transitions to SET_ACTIVE_PLAYER

### SET_ACTIVE_PLAYER
- Called at game start and on every player switch
- If the incoming player has a `level_snapshot`, restores enemy positions
  and layout from that snapshot, then transitions to START_LEVEL
- If no snapshot exists, transitions to START_LEVEL (fresh level)

### START_LEVEL
- If restoring from snapshot: rebuilds level from saved state, then applies
  spawn safety adjustment (see Spawn Safety below)
- If new level: creates fresh enemy layout for player's current_level
- Transitions to RUN_LEVEL

### RUN_LEVEL
- Main game loop: input handling, physics update, collision detection, rendering
- For temporary use, since we have no enemy logic, just display a message with a countdown timer for 5 seconds. if the W key is pressed, LEVEL_COMPLETE, if the L key is pressed, PLAYER_KILLED.
- Transitions:
  - All aliens cleared → LEVEL_COMPLETE
  - Player ship destroyed → PLAYER_KILLED

### LEVEL_COMPLETE
- Awards level bonus to active player's score
- Displays remaining lives for ALL players still alive
- Increments active player's current_level
- Clears active player's level_snapshot (next level is always fresh)
- Transitions to SET_ACTIVE_PLAYER (same player continues)

### PLAYER_KILLED
- Decrements active player's lives
- Evaluates next action (see 2-Player Logic below)

### SAVE_SNAPSHOT_AND_SWITCH
- Serialises current level state (enemy positions, projectiles, layout)
  into active player's `level_snapshot`
- Clears all active projectiles from the snapshot (missiles mid-air are
  discarded; enemy positions are preserved)
- Sets other player as active
- Transitions to SET_ACTIVE_PLAYER

### DROP_TO_1P
- Sets dead player's `is_alive = False`
- Continues with surviving player as sole active player
- Game proceeds as 1P from this point
- Transitions to SET_ACTIVE_PLAYER

### GAME_OVER
- Displays final score (both players if 2P game)
- If either score qualifies for top 10 leaderboard → SCORE_ENTRY
- Otherwise → MAIN

### SCORE_ENTRY (stub)
- Accepts player initials / name entry
- Saves score to leaderboard data
- Transitions to MAIN
- Temporary: display the screen with HIGH SCORES message for 5 seconds before transition to MAIN
- **Note: implement as stub initially, full implementation later**

### EXIT
- Clean shutdown, end process

---

## Player State

Each player maintains an independent `PlayerState` object throughout the game:
```python
@dataclass
class PlayerState:
    player_num: int        # 1 or 2
    lives: int             # remaining lives
    score: int             # current score
    current_level: int     # level this player is on
    level_snapshot: dict   # frozen level state; None if fresh level
    is_alive: bool         # False once lives reach 0
```

---

## 2-Player Game Flow

In a 2-player game, players take turns. A player plays until their ship
is destroyed, then control passes to the other player. Each player
maintains their own level progress independently — they may be on
different levels at any time.

### Player killed — decision table

After decrementing active player's lives, evaluate:

| Condition | Action |
|-----------|--------|
| Lives > 0, 1P mode | Resume RUN_LEVEL (same level, same player) |
| Lives > 0, 2P mode | → SAVE_SNAPSHOT_AND_SWITCH |
| Lives = 0, other player still alive | → DROP_TO_1P |
| Lives = 0, both players dead | → GAME_OVER |

---

## Spawn Safety

When a player resumes a snapshotted level (i.e. returning from a player
switch or resuming after losing a life in 1P mode), the ship must not
spawn into an unsafe position.

### Rules
1. **Projectiles discarded**: all in-flight missiles and bombs are removed
   from the snapshot before the level is restored. This is done in
   SAVE_SNAPSHOT_AND_SWITCH and before any resume from snapshot.
2. **Enemy clearance zone**: on spawn, check a defined safe radius around
   the ship's starting position. Any enemy unit within that radius is
   nudged to the nearest safe position outside it, maintaining their
   relative formation spacing as much as possible.
3. **Minimum safe gap**: the clearance radius should be defined in
   `game_config.toml` as `spawn_safe_radius` (default: 80px) so it can
   be tuned without code changes.
4. **Diving enemies**: any enemy currently in a dive animation is snapped
   back to its formation position before the level resumes.

### Implementation note
Spawn safety logic lives in `START_LEVEL` when restoring from a snapshot.
It must run before the first frame is rendered. It should be a standalone
function `apply_spawn_safety(snapshot, ship_spawn_pos)` so it is unit
testable without a display.

---

## Key Bindings (Main Screen)

| Key | Action |
|-----|--------|
| `1` | Start 1-player game |
| `2` | Start 2-player game |
| `C` | Open game config |
| `X` | Exit game |

---

## Game Config File

- Human-editable TOML file (`game_config.toml`), consistent with pyproject.toml
- Loaded at splash screen, reloaded if changed via GAME_CONFIG screen
- Parameters include:
```toml
[game]
starting_level = 1
num_lives = 3
spawn_safe_radius = 80
```

---

## Implementation Notes

- Implement state machine as a `GameStateManager` class with an explicit
  state enum (`GameState.SPLASH`, `GameState.MAIN`, etc.)
- State transitions must be logged for debugging
- Each state should be a separate method or class to keep logic isolated
- No rendering calls inside state transition logic
- All logic classes must be unit testable without a display
- `apply_spawn_safety()` must be covered by unit tests with edge cases:
  - No enemies in radius (no-op)
  - All enemies in radius (push all out)
  - Diving enemy mid-animation (snap to formation)
