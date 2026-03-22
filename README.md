# Space Attackers

A Space Invaders-style arcade game built in Python using the [Arcade](https://api.arcade.academy/) library. This project was created as a learning exercise for [Claude Code](https://claude.ai/claude-code).

## Download
👾 [Download Space Attackers for Windows](https://github.com/darthwilliam1118/Space_Attackers/releases/latest)
## How to Play

### Controls

| Action | Key |
|--------|-----|
| Move left | Arrow Left / A |
| Move right | Arrow Right / D |
| Move up | Arrow Up / W |
| Move down | Arrow Down / S |
| Fire | Space |

### Objective

Destroy all enemies in the grid before their bullets hit your ship. Clear each wave to advance to the next level. You start with 3 lives.

### Tips

- Your ship tilts as it moves — bullets fire in the direction of the tilt.
- After spawning you have a brief invincibility window (ship flashes).
- Enemies speed up as their numbers thin out
- Finish waves quickly.

## Running the Game

```bash
pip install -r requirements.txt
python main.py
```

Run tests:

```bash
pytest --cov=src
```

---

## Features

### Game Structure
- Full state machine: Splash → Main Menu → Config → Gameplay → Level Complete → Game Over → High Scores
- 5-second auto-advance on the splash screen
- Up to 2-player alternating-turn mode
- High score tracking across sessions
- Configurable starting level and number of lives via `game_config.toml`

### Player Ship
- Smooth momentum-based movement with configurable acceleration and deceleration
- Vertical movement restricted to the bottom third of the screen
- Ship tilts left/right proportional to horizontal velocity
- Bullets fire at the ship's current tilt angle
- Bullets removed instantly on hitting any screen edge
- Spawn invincibility with visible flashing effect
- Pixel-accurate collision detection (`algo_simple` hit boxes)

### Enemy Grid
- Configurable grid size (columns × rows) via `game_config.toml`
- Fixed column spacing based on enemy sprite width × a configurable factor
- Formation centered on screen regardless of column count
- Enemies march left/right and drop each time they reverse direction
- Each enemy returns to its spawn-position home when it reaches the bottom (no instant kill)
- Enemies fire bullets downward at random intervals
- Pixel-accurate collision detection on both enemy sprites and their bullets

### Progression
- Enemy speed increases as the grid is thinned — uses a √(killed%) curve for a natural ramp
- Speed floor rises each level via a configurable per-level bonus
- Enemy grid state preserved across player deaths; grid resets only on a new level or new game
- Explosion animation plays fully before level-complete or game-over transitions

### Technical
- All game logic separated from rendering — logic classes require no display
- Asset paths resolve correctly in both development and PyInstaller-bundled `.exe` builds
- GitHub Actions workflow: runs pytest and builds a self-contained Windows executable on every push to `main`
- Window centered on screen at startup

---

## Configuration (`game_config.toml`)

| Section | Key | Default | Description |
|---------|-----|---------|-------------|
| `[game]` | `starting_level` | `1` | Level to begin on |
| `[game]` | `num_lives` | `3` | Lives per player |
| `[game]` | `spawn_safe_radius` | `80` | Min enemy distance from player spawn after respawn |
| `[enemies]` | `enemy_cols` | `7` | Number of enemy columns |
| `[enemies]` | `enemy_rows` | `4` | Number of enemy rows |
| `[enemies]` | `enemy_col_width_factor` | `1.2` | Column spacing as a multiple of enemy sprite width |
| `[enemies]` | `enemy_speed_initial` | `30` | Base enemy speed (px/s) |
| `[enemies]` | `enemy_speed_max_bonus` | `150` | Max additional speed when grid is almost empty |
| `[enemies]` | `enemy_speed_level_bonus` | `15` | Extra base speed added per level |
| `[enemies]` | `enemy_side_margin` | `40` | Horizontal margin before reversing direction |
| `[enemies]` | `enemy_drop_distance` | `48` | Pixels dropped on each direction reversal |
| `[enemies]` | `enemy_fire_interval_min` | `1.5` | Min seconds between enemy shots |
| `[enemies]` | `enemy_fire_interval_max` | `4.0` | Max seconds between enemy shots |
| `[enemies]` | `enemy_bullet_speed` | `250` | Enemy bullet speed (px/s) |
| `[ship]` | `ship_speed` | `300` | Max ship speed (px/s) |
| `[ship]` | `ship_accel` | `1000` | Acceleration rate (px/s²) |
| `[ship]` | `ship_decel` | `1200` | Deceleration rate (px/s²) |
| `[ship]` | `ship_tilt_rate` | `90` | Max tilt change rate (°/s) |
| `[ship]` | `fire_cooldown` | `0.1` | Seconds between shots |
| `[ship]` | `bullet_speed` | `500` | Player bullet speed (px/s) |
| `[ship]` | `spawn_invincible_duration` | `2.0` | Invincibility seconds after spawn |
| `[ship]` | `ship_zone_height_pct` | `0.33` | Fraction of screen height the ship can move in |

## Assets
- Sprites: Kenney (kenney.nl) — CC0 Public Domain
 - Fonts: KenPixel & KenVector fonts by Kenney Vleugels (www.kenney.nl)
   Modified by MedicineStorm [OpenGameArt.org]
- Sound effects: [OpenGameArt.org] — CC0 Public Domain