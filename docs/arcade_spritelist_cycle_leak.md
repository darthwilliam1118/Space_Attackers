# Arcade 3.x Performance Pitfall: The SpriteList Cycle Leak

## The Symptom

During development of Space Attackers, a severe progressive performance degradation
appeared at runtime:

- `Grid[move+shoot]` timing grew from **<1 ms to 30+ ms** over ~60 seconds at level 1
  with only 28 sprites on screen, no bullets, no kills.
- Memory usage grew at roughly **1 MB every few seconds** continuously.
- The sprite count stayed constant (28 the whole time), ruling out sprite accumulation.
- The slowdown was *progressive* — proportional to elapsed time, not to game complexity.

## Root Cause

### Part 1 — The Cycle

In Arcade 3.x, every `Sprite` tracks every `SpriteList` it has been added to via
`Sprite.sprite_lists` (a list on the sprite instance). Whenever a positional attribute
like `center_x` is written, the property setter dispatches `_update_position()` to
**every list in `sprite.sprite_lists`**:

```python
# arcade/sprite/base.py (conceptual)
@center_x.setter
def center_x(self, value):
    self._position = (value, self._position[1])
    for sprite_list in self.sprite_lists:   # <-- dispatches to ALL lists
        sprite_list._update_position(self)
```

This is intentional: it keeps GPU buffers in sync. The problem arises when you
construct a **temporary `arcade.SpriteList`** per frame and append sprites that are
already members of a permanent list:

```python
# BAD — do not do this in a hot path
def get_all_enemy_sprites(self) -> arcade.SpriteList:
    combined = arcade.SpriteList()       # new list every frame
    for s in self._grid.get_sprite_list():
        combined.append(s)               # registers s with combined
    for s in self._dive.get_all_sprites():
        combined.append(s)
    return combined                      # caller uses it briefly, then drops ref
```

Each `combined.append(s)` adds `combined` to `s.sprite_lists`. When the caller
discards `combined`, the Python *reference count* for `combined` drops to zero — but
`s.sprite_lists` still holds a reference to it, and `combined` still holds references
to all sprites. This is a **reference cycle**: sprite → list → sprite.

### Part 2 — Why `gc.disable()` Makes It Fatal

Space Attackers disables the cyclic garbage collector during gameplay to eliminate
GC-pause stutters (a common Arcade performance technique):

```python
import gc
gc.disable()   # called once before gameplay starts
```

CPython's reference-counting collector handles *acyclic* garbage instantly and for
free. Cyclic garbage — objects that keep each other alive through a reference loop —
is only collected by the **periodic cyclic GC**, which `gc.disable()` turns off.

With `gc.disable()` active, every temporary `SpriteList` created per frame is
**permanently orphaned**: it can never be collected, and every sprite forever retains a
reference to it in `sprite.sprite_lists`.

### Part 3 — Linear Slowdown

After `N` frames, every grid sprite has accumulated `N` dead `SpriteList` references.
The grid moves all 28 sprites every frame via `sprite.center_x +=`. Each write
dispatches `_update_position()` to all `N + 1` entries in `sprite.sprite_lists`. Work
per frame scales as `O(N_sprites × N_frames)` — exactly the observed linear growth.

### Diagnostic confirmation

A one-line diagnostic was added inside `EnemyGrid.update()`:

```python
if frame_count == 0 and self._sprite_list:
    sample = next(iter(self._sprite_list))
    print(f"[DIAG] sprite.sprite_lists len = {len(sample.sprite_lists)}")
```

Output confirmed the count grew by exactly 1 per frame:

```
[DIAG] sprite.sprite_lists len = 16
[DIAG] sprite.sprite_lists len = 32
[DIAG] sprite.sprite_lists len = 48
...
[DIAG] sprite.sprite_lists len = 144
```

(Increments of 16 because the diagnostic fires every 16 frames on a `frame_count % 16 == 0` cycle.)

## The Fix

Return a **plain Python `list`** instead of an `arcade.SpriteList` from any method
that combines sprites from multiple permanent lists:

```python
# GOOD — plain list has no two-way Sprite registration
def get_all_enemy_sprites(self) -> list[arcade.Sprite]:
    return list(self._grid.get_sprite_list()) + list(self._dive.get_all_sprites())

def get_enemy_bullet_sprite_list(self) -> list[arcade.Sprite]:
    return list(self._grid.get_bullet_sprite_list()) + list(self._dive.get_all_bullets())
```

`list(spritelist)` iterates and copies references into a plain Python list. It does
**not** call `SpriteList.append()`, so no sprite's `sprite_lists` is modified. The
resulting list is ordinary garbage the reference counter reclaims immediately after
the caller is done with it.

Call sites that previously used the returned `SpriteList` for iteration or collision
work identically with a plain list.

## General Rules

### Rule 1 — Never construct a per-frame `SpriteList` containing sprites that already live in another `SpriteList`

This is the core rule. It appears in the project's `CLAUDE.md` and in the `BaseLevel`
docstring:

> While `gc.disable()` is active during gameplay, never construct an
> `arcade.SpriteList()` per frame containing sprites that already live in another
> SpriteList — it creates an unbreakable cycle.

This applies to **any** helper method called per-frame that aggregates or filters
sprites: HP bar queries, collision target lists, draw helpers, etc.

### Rule 2 — Use plain Python lists for per-frame sprite aggregation

Anywhere you need to combine or project a subset of sprites for a single frame's use:

```python
# Return type: list[arcade.Sprite], not arcade.SpriteList
all_targets = list(self._grid.get_sprite_list()) + list(self._divers.get_all_sprites())
```

The only `arcade.SpriteList` instances that should contain a given sprite are its
**permanent, long-lived owners** — the ones that exist for the lifetime of the level
and call `sprite_list.draw()` / `sprite_list.update()` directly.

### Rule 3 — Keep an eye on Optional SpriteList arguments that create a new list as a default

This anti-pattern silently constructs a `SpriteList` whenever the caller omits the
argument:

```python
# BAD — every call site that omits player_bullets creates an empty SpriteList
def update(self, delta_time, player_ship, player_bullets: Optional[arcade.SpriteList] = None):
    bullets = player_bullets if player_bullets is not None else arcade.SpriteList()
    ...
```

Even an empty `SpriteList` is a registration target: if any sprite is later appended
to it, the cycle applies. And the pattern invites callers to silently omit the
argument, meaning no real list is ever passed. Prefer making the argument required, or
use a cached empty instance if a sentinel is genuinely needed.

### Rule 4 — A cached reusable empty `SpriteList` is safe

If you need to pass an "empty bullets" list to an `update()` call (e.g., during a
death animation where you want motion but no collision), cache one instance rather than
constructing it per frame:

```python
# In __init__:
self._empty_bullets: arcade.SpriteList = arcade.SpriteList()  # reusable sentinel

# In the death-sequence branch:
self._dive_ctrl.update(delta_time, None, None, self._empty_bullets)
```

Since no sprites are ever appended to `self._empty_bullets`, no sprite's `sprite_lists`
is modified and no cycle is created.

### Rule 5 — `gc.enable()` is not the fix

Re-enabling the cyclic GC would mask the leak — cycles would eventually be collected —
but would reintroduce the GC-pause stutters that prompted `gc.disable()` in the first
place. Fix the cause: don't construct shared-sprite SpriteLists in hot paths.

## Quick Decision Guide

| You want to…                              | Do this                                      |
|-------------------------------------------|----------------------------------------------|
| Draw a fixed set of sprites every frame   | Permanent `arcade.SpriteList`; call `.draw()` |
| Return a combined set for one-frame use   | `list(sl_a) + list(sl_b)` — plain Python list |
| Pass "no bullets" as a sentinel           | Cache one empty `SpriteList` in `__init__`   |
| Aggregate for collision with `arcade.check_for_collision_with_list` | Plain list is accepted |
| Profile suspicion of this leak            | Check `len(some_sprite.sprite_lists)` — if it grows over time, a temp SpriteList is being created per frame somewhere |

## Affected Files in Space Attackers

The fix touched these files (commit `9650618`):

| File | Change |
|---|---|
| `src/levels/standard_level.py` | `get_all_enemy_sprites` / `get_enemy_bullet_sprite_list` changed from `arcade.SpriteList` to `list[arcade.Sprite]`; `Optional[SpriteList] = None` default removed |
| `src/levels/boss_level.py` | Same return-type fix; `_empty_bullets` cached sentinel added |
| `src/levels/meteor_level.py` | Same return-type fix |
| `agf/levels/base_level.py` | Abstract method signatures updated; cycle-leak rationale added to docstring |
| `src/views/run_level.py` | Redundant `list()` wraps removed; missing `player_bullets` argument added to death-animation call path |
