## Collision Checks
We want to stagger collision checks across frames to reduce per-frame 
CPU cost. There can be many player bullets and many enemies on higher levels, so this collision check would take a long time.

Add a self._frame_count: int = 0 counter to RunLevelView that 
increments each on_update() call.

Stagger collision checks as follows:
- Player bullets vs dive ships: EVERY frame (keep responsive)  
- Player bullets vs enemy grid: EVERY 3 frames (frame_count % 3 == 0)
- Enemy sprites vs player ship (direct contact): EVERY 3 frames (frame_count % 3 == 1)
- Dive sprites vs player ship (direct contact): EVERY 3 frames (frame_count % 3 == 2)
- Enemy bullets vs player ship: EVERY 2 frames (frame_count % 2 == 0)
- Dive bullets vs player ship: EVERY 2 frames (frame_count % 2 == 1)

The offsets (== 0 vs == 1) ensure the two most expensive checks 
never run in the same frame.

# Important constraints:
- The frame_count should reset to 0 on level start/respawn to keep 
  behaviour deterministic or just bitwise "and" with 15 (1111b)
- During the _dying sequence and _waiting_for_dives, skip ALL 
  collision checks regardless of frame count (already done, preserve this)
- Add a config flag debug_show_collision_timing (default False) that 
  when True prints per-section timing each spike frame (see below), so we can 
  verify the improvement
# Proposed instrumentation:

_ta = time.perf_counter()
self._move(delta_time)
self.check_boundary()
_tb = time.perf_counter()
# ... per-enemy loop, bullet updates, shooting ...
_tc = time.perf_counter()
# collision: enemy bullets vs player
_td = time.perf_counter()
# collision: enemy sprites vs player
_te = time.perf_counter()
# store timings on self for standard_level to pick up and print

Then in standard_level.update() split _grid.update() vs _dive.update():

_t_grid_start = time.perf_counter()
events += self._grid.update(delta_time, player_ship)
_t_grid_end = time.perf_counter()
events += self._dive.update(...)
_t_dive_end = time.perf_counter()

And thread all that through standard_level.update() → back into run_level.py's spike print.

After implementing, user will play test that:
- Hitting enemies still feels responsive (no perceptible delay)
- Taking damage from enemy bullets still feels fair
- No bullets visually pass through sprites without registering