# Refactor: Level Architecture

## Overview
Introduce a `BaseLevel` abstraction so that `RunLevelView` and
`GameStateManager` are decoupled from the specific types of enemies and
systems a level contains. The existing `EnemyGrid` + `DiveController`
behaviour is preserved exactly — wrapped inside a new `StandardLevel`
class. No gameplay changes. All existing tests must pass unchanged after
the refactor.

This refactor is a prerequisite for boss levels, meteor storm levels,
bonus levels, and any other future level type.

## Files to create

```
src/levels/__init__.py
src/levels/base_level.py        — abstract interface
src/levels/standard_level.py   — wraps existing EnemyGrid + DiveController
src/levels/level_factory.py    — maps level number to BaseLevel instance
```

## Files to modify

```
src/state.py          — _handle_start_level(), _save_grid_snapshot(),
                         _handle_save_snapshot_and_switch()
src/views/run_level.py — _setup(), on_update(), on_draw(),
                         _is_level_cleared(), death sequence
```

## Files NOT modified

```
src/enemy_grid.py      — no changes
src/dive_controller.py — no changes
src/sprites/           — no changes
src/ui/                — no changes
tests/                 — all existing tests pass unchanged
```

---

## BaseLevel interface

```python
# src/levels/base_level.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
import arcade
from src.game_event import GameEvent


class BaseLevel(ABC):
    """Abstract interface for all level types.

    RunLevelView and GameStateManager interact with levels exclusively
    through this interface. Concrete level classes implement the details.
    """

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    def setup(self, level_number: int) -> None:
        """Initialise all entities for this level from scratch.
        Not called when restoring from snapshot."""

    # ------------------------------------------------------------------
    # Per-frame
    # ------------------------------------------------------------------

    @abstractmethod
    def update(self, delta_time: float,
               player_ship: Any) -> list[GameEvent]:
        """Update all level entities.

        player_ship is None during the death sequence and 2P wait.
        Implementations must handle None safely (no collision checks).
        Returns list of GameEvents that occurred this frame.
        """

    @abstractmethod
    def draw(self) -> None:
        """Draw all level entities.
        Called from RunLevelView.on_draw() between background and
        player ship layers."""

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    @abstractmethod
    def is_cleared(self) -> bool:
        """True when the win condition for this level type is met.

        StandardLevel: grid empty AND no airborne dive ships.
        BossLevel: boss destroyed.
        BonusLevel: timer expired or all targets collected.
        """

    @property
    @abstractmethod
    def level_type(self) -> str:
        """String identifier e.g. 'standard', 'boss', 'meteor', 'bonus'."""

    # ------------------------------------------------------------------
    # Bullet collision — called from RunLevelView bullet loop
    # ------------------------------------------------------------------

    @abstractmethod
    def apply_player_bullet(self, bullet: Any) -> Any:
        """Check bullet against all level enemies.
        Returns a hit result object if hit, None otherwise.
        Caller removes the bullet sprite on hit."""

    # ------------------------------------------------------------------
    # Hit reporting
    # ------------------------------------------------------------------

    @abstractmethod
    def consume_pending_hits(self) -> list[tuple[float, float, int]]:
        """Return and clear all lethal hits this frame.
        Each entry is (x, y, points). RunLevelView spawns explosions
        and score popups for each entry."""

    @abstractmethod
    def consume_pending_non_lethal_hits(self) -> list[tuple[float, float]]:
        """Return and clear all non-lethal hits (HP damage without kill).
        Each entry is (x, y). RunLevelView spawns a hit ring for each."""

    # ------------------------------------------------------------------
    # Sprite lists — for draw only
    # ------------------------------------------------------------------

    @abstractmethod
    def get_all_enemy_sprites(self) -> arcade.SpriteList:
        """All active enemy sprites for draw."""

    @abstractmethod
    def get_enemy_bullet_sprite_list(self) -> arcade.SpriteList:
        """All active enemy projectiles for draw."""

    # ------------------------------------------------------------------
    # Snapshot / restore
    # ------------------------------------------------------------------

    @abstractmethod
    def to_snapshot(self) -> dict:
        """Serialise complete level state.
        Must include a 'level_type' key matching self.level_type."""

    @classmethod
    @abstractmethod
    def from_snapshot(cls, snapshot: dict, config: Any,
                      window_width: int,
                      window_height: int) -> 'BaseLevel':
        """Restore a level from a snapshot dict."""

    # ------------------------------------------------------------------
    # 2P dive wait — optional overrides
    # ------------------------------------------------------------------

    def has_any_airborne(self) -> bool:
        """True if any entities are mid-animation that should complete
        before a 2P snapshot is taken. Default False."""
        return False

    def block_new_launches(self) -> None:
        """Prevent new enemy launches during 2P death wait.
        Default is a no-op."""
        pass

    # ------------------------------------------------------------------
    # Velocity — for explosion drift
    # ------------------------------------------------------------------

    @property
    def velocity(self) -> tuple[float, float]:
        """Current (vx, vy) of the primary enemy formation.
        Used to match explosion drift to enemy movement. Default (0, 0)."""
        return (0.0, 0.0)

    # ------------------------------------------------------------------
    # Optional debug hook
    # ------------------------------------------------------------------

    def debug_force_dive(self, player_x: float) -> None:
        """Force a dive group for debug purposes (Shift+D).
        No-op by default. StandardLevel overrides."""
        pass
```

---

## StandardLevel implementation

Wraps EnemyGrid and DiveController exactly as they currently work.
No logic changes.

```python
# src/levels/standard_level.py
from __future__ import annotations
from typing import Any
import arcade
from src.levels.base_level import BaseLevel
from src.enemy_grid import EnemyGrid
from src.dive_controller import DiveController
from src.game_event import GameEvent


class StandardLevel(BaseLevel):

    def __init__(self, grid: EnemyGrid, dive_ctrl: DiveController):
        self._grid = grid
        self._dive = dive_ctrl

    @property
    def level_type(self) -> str:
        return "standard"

    def setup(self, level_number: int) -> None:
        self._grid.setup(level_number)
        self._dive.setup(level_number, self._grid)

    def update(self, delta_time: float,
               player_ship: Any) -> list[GameEvent]:
        events: list[GameEvent] = []
        events += self._grid.update(delta_time, player_ship)
        events += self._dive.update(
            delta_time, self._grid, player_ship, arcade.SpriteList()
        )
        return events

    def draw(self) -> None:
        self._grid.get_sprite_list().draw()
        self._grid.get_bullet_sprite_list().draw()
        self._dive.get_all_sprites().draw()
        self._dive.get_all_bullets().draw()

    def is_cleared(self) -> bool:
        return (self._grid.is_cleared()
                and not self._dive.has_any_airborne())

    def apply_player_bullet(self, bullet: Any) -> Any:
        hit = self._grid.apply_player_bullet(bullet)
        if hit is not None:
            return hit
        return self._dive.apply_player_bullet(bullet) \
            if hasattr(self._dive, 'apply_player_bullet') else None

    def consume_pending_hits(self) -> list[tuple[float, float, int]]:
        hits = list(self._grid.consume_pending_hits())
        hits += list(self._dive.consume_pending_hits())
        return hits

    def consume_pending_non_lethal_hits(self) -> list[tuple[float, float]]:
        hits: list[tuple[float, float]] = []
        if hasattr(self._grid, 'consume_pending_non_lethal_hits'):
            hits += list(self._grid.consume_pending_non_lethal_hits())
        hits += list(self._dive.consume_pending_non_lethal_hits())
        return hits

    def get_all_enemy_sprites(self) -> arcade.SpriteList:
        combined = arcade.SpriteList()
        for s in self._grid.get_sprite_list():
            combined.append(s)
        for s in self._dive.get_all_sprites():
            combined.append(s)
        return combined

    def get_enemy_bullet_sprite_list(self) -> arcade.SpriteList:
        combined = arcade.SpriteList()
        for s in self._grid.get_bullet_sprite_list():
            combined.append(s)
        for s in self._dive.get_all_bullets():
            combined.append(s)
        return combined

    def has_any_airborne(self) -> bool:
        return self._dive.has_any_airborne()

    def block_new_launches(self) -> None:
        self._dive.new_dive_launches_blocked = True

    def debug_force_dive(self, player_x: float) -> None:
        self._dive.launch_group(self._grid, player_x)

    @property
    def velocity(self) -> tuple[float, float]:
        return self._grid.velocity if self._grid is not None else (0.0, 0.0)

    def to_snapshot(self) -> dict:
        snapshot = self._grid.to_snapshot()
        snapshot["level_type"] = "standard"
        snapshot["diving"] = self._dive.to_snapshot()
        return snapshot

    @classmethod
    def from_snapshot(cls, snapshot: dict, config: Any,
                      window_width: int,
                      window_height: int) -> 'StandardLevel':
        from src.enemy_config import EnemyConfig
        from src.diving_config import DivingConfig

        enemy_cfg = config.enemies if config else EnemyConfig()
        diving_cfg = config.diving if config else DivingConfig()
        debug = config.debug if config else False
        scale = config.sprite_scale if config else 1.0
        hp_dur = config.ui.hp_bar_duration if config else 1.0

        grid = EnemyGrid.from_snapshot(
            snapshot, enemy_cfg, window_width, window_height,
            debug=debug, sprite_scale=scale, hp_bar_duration=hp_dur,
        )
        dive_ctrl = DiveController.from_snapshot(
            snapshot.get("diving", {}), diving_cfg,
            window_width, window_height,
            debug=debug, sprite_scale=scale, hp_bar_duration=hp_dur,
        )
        return cls(grid, dive_ctrl)
```

---

## LevelFactory

```python
# src/levels/level_factory.py
from __future__ import annotations
from typing import Any
from src.levels.base_level import BaseLevel


def create_level(level_number: int, config: Any,
                 window_width: int, window_height: int,
                 snapshot: dict | None = None) -> BaseLevel:
    """Create or restore the appropriate level for level_number.

    If snapshot is provided, restores from saved state.
    Otherwise creates a fresh level and calls setup().
    """
    if snapshot is not None:
        return _restore_from_snapshot(snapshot, config,
                                      window_width, window_height)
    level_type = _get_level_type(level_number)
    return _create_fresh(level_type, level_number, config,
                         window_width, window_height)


def _get_level_type(level_number: int) -> str:
    """Define the level sequence.

    All levels are standard for now. Extend here when new level
    types are added:
      if level_number % 10 == 0: return "boss"
      if level_number % 5 == 0: return "bonus"
    """
    return "standard"


def _create_fresh(level_type: str, level_number: int, config: Any,
                  window_width: int, window_height: int) -> BaseLevel:
    match level_type:
        case "standard":
            from src.levels.standard_level import StandardLevel
            from src.enemy_grid import EnemyGrid
            from src.dive_controller import DiveController
            from src.enemy_config import EnemyConfig
            from src.diving_config import DivingConfig

            cfg_e = config.enemies if config else EnemyConfig()
            cfg_d = config.diving if config else DivingConfig()
            debug = config.debug if config else False
            scale = config.sprite_scale if config else 1.0
            hp_dur = config.ui.hp_bar_duration if config else 1.0

            grid = EnemyGrid(cfg_e, window_width, window_height,
                             debug=debug, sprite_scale=scale,
                             hp_bar_duration=hp_dur)
            dive = DiveController(cfg_d, window_width, window_height,
                                  debug=debug, sprite_scale=scale,
                                  hp_bar_duration=hp_dur)
            level = StandardLevel(grid, dive)
            level.setup(level_number)
            return level
        case _:
            raise ValueError(f"Unknown level type: {level_type!r}")


def _restore_from_snapshot(snapshot: dict, config: Any,
                            window_width: int,
                            window_height: int) -> BaseLevel:
    level_type = snapshot.get("level_type", "standard")
    match level_type:
        case "standard":
            from src.levels.standard_level import StandardLevel
            return StandardLevel.from_snapshot(
                snapshot, config, window_width, window_height
            )
        case _:
            raise ValueError(
                f"Cannot restore unknown level type: {level_type!r}"
            )
```

---

## Changes to states.py

### _handle_start_level() — replace entirely

Remove all direct instantiation of EnemyGrid and DiveController.
spawn_safety is applied inside LevelFactory via from_snapshot().

```python
def _handle_start_level(self) -> None:
    from src.levels.level_factory import create_level
    from src.ship_config import ShipConfig

    players = self.context.get("players", [])
    idx = self.context.get("active_player_index", 0)
    cfg = self.context.get("config")
    w = self.window.width
    h = self.window.height

    level_number = 1
    snapshot = None

    if players:
        player = players[idx]
        level_number = player.current_level
        if player.level_snapshot is not None:
            snapshot = player.level_snapshot
            # Apply spawn safety before handing snapshot to factory
            from src.spawn_safety import apply_spawn_safety
            from src.ship_config import ShipConfig
            ship_cfg = cfg.ship if cfg else ShipConfig()
            spawn_y = h * ship_cfg.ship_zone_height_pct / 2.0
            apply_spawn_safety(snapshot, (w / 2.0, spawn_y),
                               cfg.spawn_safe_radius if cfg else 80)

    level = create_level(
        level_number=level_number,
        config=cfg,
        window_width=w,
        window_height=h,
        snapshot=snapshot,
    )

    self.context["current_level"] = level
    self.context.pop("enemy_grid", None)
    self.context.pop("dive_controller", None)
    self.transition(GameState.RUN_LEVEL)
```

### _save_grid_snapshot() — update to use BaseLevel

```python
def _save_grid_snapshot(self) -> None:
    from src.levels.base_level import BaseLevel

    players = self.context.get("players", [])
    idx = self.context.get("active_player_index", 0)
    level: Optional[BaseLevel] = self.context.get("current_level")

    if players and level is not None:
        snapshot = level.to_snapshot()
        snapshot.pop("projectiles", None)
        players[idx].level_snapshot = snapshot
```

### _handle_save_snapshot_and_switch() — update to use BaseLevel

```python
def _handle_save_snapshot_and_switch(self) -> None:
    from src.levels.base_level import BaseLevel

    players = self.context.get("players", [])
    idx = self.context.get("active_player_index", 0)
    level: Optional[BaseLevel] = self.context.get("current_level")

    if players and level is not None:
        snapshot = level.to_snapshot()
        snapshot.pop("projectiles", None)
        players[idx].level_snapshot = snapshot

    other_idx = 1 - idx
    self.context["active_player_index"] = other_idx
    self.transition(GameState.SET_ACTIVE_PLAYER)
```

---

## Changes to run_level.py

### Instance variables — remove grid and dive references

In __init__(), remove:
```python
self._grid: Optional[EnemyGrid] = None
self._dive_controller: Optional[DiveController] = None
self._waiting_for_dives: bool = False
```

Replace with:
```python
self._level: Optional[BaseLevel] = None
self._waiting_for_dives: bool = False  # keep — logic unchanged
```

Remove EnemyGrid and DiveController imports from the top of the file.
Add:
```python
from src.levels.base_level import BaseLevel
```

### _setup() — replace grid/dive with level

```python
# Remove:
self._grid = ctx.get("enemy_grid")
self._dive_controller = ctx.get("dive_controller")

# Replace with:
self._level = ctx.get("current_level")
```

### on_update() — consolidate update and event loops

Replace the two separate update blocks and their event loops with:

```python
# Single update call
events = self._level.update(delta_time, collision_target)

# Single hit processing block
vx, vy = self._level.velocity
cfg = self._manager.context.get("config")
for hit_x, hit_y, points in self._level.consume_pending_hits():
    self._update_score(points)
    ui_cfg = cfg.ui if cfg else UIConfig()
    self._score_popups.append(
        ScorePopup(hit_x, hit_y, points,
                   duration=ui_cfg.popup_duration,
                   rise_speed=ui_cfg.popup_rise_speed)
    )
    exp = ExplosionSprite(x=hit_x, y=hit_y, frame_duration=0.05,
                          vx=vx, vy=vy,
                          scale=cfg.sprite_scale if cfg else 1.0)
    self._explosions.append(exp)
    self.spawn_destruction_effect(hit_x, hit_y, vx, vy)
    if self._snd_enemy_killed:
        arcade.play_sound(self._snd_enemy_killed,
                          volume=self._sfx_volume())

for hit_x, hit_y in self._level.consume_pending_non_lethal_hits():
    self._spawn_hit_ring(hit_x, hit_y)

# Single event loop
god_mode = cfg.god_mode if cfg else False
for event in events:
    if event == GameEvent.PLAYER_KILLED:
        if not god_mode:
            self._trigger_death()
            return
    elif event in (GameEvent.LEVEL_COMPLETE, GameEvent.ENEMY_DESTROYED):
        if self._level.is_cleared():
            self._level_cleared = True
            return
```

### _is_level_cleared() inline closure — replace

```python
# Remove the closure definition entirely.
# Replace every call to _is_level_cleared() with:
self._level is not None and self._level.is_cleared()
```

### on_draw() — replace four draw calls

```python
# Remove:
if self._grid is not None:
    self._grid.get_sprite_list().draw()
    self._grid.get_bullet_sprite_list().draw()
if self._dive_controller is not None:
    self._dive_controller.get_all_sprites().draw()
    self._dive_controller.get_all_bullets().draw()

# Replace with:
if self._level is not None:
    self._level.draw()
```

### Death sequence — replace grid/dive references

```python
# In the _dying block, replace:
if self._grid is not None:
    self._grid.update(delta_time, None)
if self._dive_controller is not None:
    self._dive_controller.update(delta_time, self._grid, None,
                                 arcade.SpriteList())

# With:
if self._level is not None:
    self._level.update(delta_time, None)

# Replace airborne check:
if self._dive_controller is not None and \
        self._dive_controller.has_any_airborne():
    self._dying = False
    self._waiting_for_dives = True
    self._dive_controller.new_dive_launches_blocked = True

# With:
if self._level is not None and self._level.has_any_airborne():
    self._dying = False
    self._waiting_for_dives = True
    self._level.block_new_launches()
```

### 2P wait block — replace

```python
# Replace:
if self._dive_controller is not None:
    self._dive_controller.update(...)
    if not self._dive_controller.has_any_airborne():
        ...

# With:
if self._level is not None:
    self._level.update(delta_time, None)
    if not self._level.has_any_airborne():
        self._waiting_for_dives = False
        self._manager.transition(GameState.PLAYER_KILLED)
```

### Debug shortcut Shift+D — update

```python
# Replace:
self._dive_controller.launch_group(self._grid, self._ship.center_x)

# With:
if self._level is not None and self._ship is not None:
    self._level.debug_force_dive(self._ship.center_x)
```

### Bullet loop — update apply_player_bullet call

```python
# Replace:
hit = self._grid.apply_player_bullet(bullet)

# With:
hit = self._level.apply_player_bullet(bullet) \
      if self._level is not None else None
```

Also remove the guard `if self._grid is None: return` —
replace with `if self._level is None: return`.

---

## Unit tests required

All existing tests must pass unchanged.

New tests in tests/test_level_factory.py:

- create_level() with no snapshot returns StandardLevel
- create_level() with snapshot calls from_snapshot()
- to_snapshot() includes level_type == "standard"
- from_snapshot() with level_type "standard" returns StandardLevel
- from_snapshot() with unknown level_type raises ValueError
- _create_fresh() with unknown level_type raises ValueError
- _get_level_type() returns "standard" for levels 1 through 20
- StandardLevel.is_cleared() False when grid has enemies
- StandardLevel.is_cleared() False when dives airborne
- StandardLevel.is_cleared() True when grid empty and no airborne
- StandardLevel.has_any_airborne() delegates to DiveController
- StandardLevel.velocity returns grid velocity
- StandardLevel.block_new_launches() sets dive controller flag
- StandardLevel.debug_force_dive() calls launch_group on dive ctrl

---

## Migration checklist for Claude Code

Work in this order — each step is independently testable:

1. Create src/levels/__init__.py (empty)
2. Create src/levels/base_level.py — no arcade imports at module level
3. Create src/levels/standard_level.py — run existing tests, confirm pass
4. Create src/levels/level_factory.py
5. Update src/states.py — three methods only
6. Update src/views/run_level.py — work through in this order:
   a. __init__() instance variables
   b. imports at top of file
   c. _setup()
   d. on_draw()
   e. on_update() bullet loop
   f. on_update() main update + event loop
   g. on_update() death sequence
   h. on_update() 2P wait block
   i. on_key_press() Shift+D shortcut
7. Search entire file for any remaining self._grid or
   self._dive_controller references — there must be none
8. Run full test suite — all pass
9. Add new tests in tests/test_level_factory.py
10. Manual smoke test: 1P game, 2P game, level complete, game over

## Implementation notes

- base_level.py must have zero arcade imports at module level so tests
  importing BaseLevel do not trigger arcade initialisation. Use
  TYPE_CHECKING guard if arcade types are needed in annotations.
- After step 7, grep for "enemy_grid" and "dive_controller" across the
  entire src/ directory. Only EnemyGrid and DiveController source files
  themselves should contain these strings. Any occurrence in states.py
  or run_level.py is a missed replacement.
- The level_type key in snapshots defaults to "standard" in
  _restore_from_snapshot() for backwards compatibility with any snapshots
  that predate this refactor.
- StandardLevel.from_snapshot() does NOT call apply_spawn_safety() —
  that remains in _handle_start_level() in states.py so it runs exactly
  once regardless of level type.
- Player bullet collision loop stays in RunLevelView — only the
  apply_player_bullet() call changes to go through BaseLevel.
- HP bar drawing (_draw_enemy_hp_bars()) in RunLevelView currently reads
  from self._grid directly. After refactor it should call
  self._level.get_all_enemy_sprites() or a new get_hp_bar_data() method
  on BaseLevel. Add get_hp_bar_data() as an optional method returning
  an empty list by default if needed.
