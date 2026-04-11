# Feature Brief: Hit Point System with Health Bars

## Overview
Replace the current one-hit-kill system with a hit-point-based damage model for both players and enemies, with animated health bars displayed above damaged enemies.

## Constants (add to constants.py)
```python
PLAYER_MAX_HP = 100
PLAYER_BULLET_DAMAGE = 100

ENEMY_BULLET_DAMAGE = 20

# HP per enemy type, keyed by sprite/type identifier
ENEMY_BASE_HP = {
    "enemy_type_a": 100,   # level 1 dies in one hit
    "enemy_type_b": 150,
    "enemy_type_c": 200,
}

# HP scaling per level
ENEMY_HP_LEVEL_MULTIPLIER = 1.25  # each level enemies get 25% more HP

# Health bar display
HP_BAR_DURATION = 1.0        # seconds bar is visible after a hit
HP_BAR_HEIGHT = 6
HP_BAR_Y_OFFSET = 10         # pixels above sprite center
HP_BAR_COLOR_HIGH = arcade.color.GREEN    # > 75%
HP_BAR_COLOR_MID = arcade.color.YELLOW   # 25–75%
HP_BAR_COLOR_LOW = arcade.color.RED      # < 25%
HP_BAR_OUTLINE_COLOR = arcade.color.WHITE
HP_BAR_OUTLINE_WIDTH = 2
```

## Data Model Changes

### EnemyState dataclass
Add fields:
```python
hit_points: int
max_hit_points: int
hp_bar_timer: float = 0.0   # counts down after a hit, bar hidden when 0
```

### PlayerState dataclass
Add fields:
```python
hit_points: int = PLAYER_MAX_HP
max_hit_points: int = PLAYER_MAX_HP
```

### Bullet
Add field:
```python
damage: int   # set at spawn time based on who fired it
```

## Enemy Factory
When spawning enemies, set HP based on type and current level:
```python
base_hp = ENEMY_BASE_HP[enemy_type]
scaled_hp = int(base_hp * (ENEMY_HP_LEVEL_MULTIPLIER ** (level - 1)))
enemy.hit_points = scaled_hp
enemy.max_hit_points = scaled_hp
```

## Collision / Damage Logic
Replace existing one-hit-kill collision handling with:

```python
def handle_bullet_enemy_collision(bullet, enemy):
    enemy.hit_points -= bullet.damage
    if enemy.hit_points <= 0:
        # existing destroy + explosion logic
        destroy_enemy(enemy)
        show_explosion(enemy.center_x, enemy.center_y)
    else:
        enemy.hp_bar_timer = HP_BAR_DURATION

def handle_enemy_bullet_player_collision(bullet, player):
    player.hit_points -= bullet.damage
    if player.hit_points <= 0:
        # existing player death logic
        handle_player_death()
    # player HP bar is always visible in HUD, no timer needed
```

## Update Loop
Each frame, tick down hp_bar_timer on all enemies:
```python
for enemy in enemy_list:
    if enemy.hp_bar_timer > 0:
        enemy.hp_bar_timer -= delta_time
```

## Health Bar Rendering
Add a `draw_enemy_hp_bars()` method called in `on_draw()` after drawing sprites:

```python
def draw_enemy_hp_bars():
    for enemy in enemy_list:
        if enemy.hp_bar_timer <= 0:
            continue

        hp_percent = enemy.hit_points / enemy.max_hit_points
        bar_width = enemy.width  # scales with sprite

        # color based on HP percent
        if hp_percent > 0.75:
            fill_color = HP_BAR_COLOR_HIGH
        elif hp_percent > 0.25:
            fill_color = HP_BAR_COLOR_MID
        else:
            fill_color = HP_BAR_COLOR_LOW

        bar_x = enemy.center_x
        bar_y = enemy.center_y + enemy.height / 2 + HP_BAR_Y_OFFSET

        # outline rectangle
        arcade.draw_rectangle_outline(
            bar_x, bar_y,
            bar_width, HP_BAR_HEIGHT,
            HP_BAR_OUTLINE_COLOR, HP_BAR_OUTLINE_WIDTH
        )

        # filled portion — left-aligned within the bar
        filled_width = bar_width * hp_percent
        arcade.draw_rectangle_filled(
            bar_x - (bar_width - filled_width) / 2, bar_y,
            filled_width, HP_BAR_HEIGHT,
            fill_color
        )
```

## Player HP in HUD
The player's HP bar should be permanently visible in the HUD (not timer-based). Add a bar to the existing HUD draw method:

- Position: bottom-center of screen, or wherever health is conventionally shown
- Label: "HP" or a heart icon
- Same color logic as enemy bars (green/yellow/red thresholds)
- Width: fixed (e.g. 200px), not scaled to sprite

## Two-Player Considerations
- Each `PlayerState` tracks its own `hit_points` independently
- Each player's HP bar is drawn in their respective HUD area
- Friendly fire: if not implemented, only enemy bullets damage players (no change needed)
- Snapshot serialization: ensure `hit_points` is included in the two-player state snapshot so the remote player sees accurate HP

## What NOT to Change
- Explosion animation logic — trigger it exactly as before, just on `hp <= 0` instead of on any hit
- Bullet spawn logic — only add the `damage` field at spawn time
- Enemy movement patterns — no change
- Existing sprite/type structure — add fields, don't redesign

## Testing Checklist
- [ ] Level 1 enemies die in one player bullet hit
- [ ] Level 2+ enemies require multiple hits
- [ ] Health bar appears on hit and disappears after 1 second if enemy survives
- [ ] Health bar color changes correctly at 75% and 25% thresholds
- [ ] Bar width correctly scales with sprite width
- [ ] Bar depletes from right to left as HP decreases
- [ ] Enemy at 1 HP still shows bar briefly before dying on next hit
- [ ] Player HP decreases correctly on enemy bullet hit
- [ ] Player death triggers at 0 HP
- [ ] Two-player HP states are independent
- [ ] State snapshots include hit point data
