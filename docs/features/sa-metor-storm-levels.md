# Feature: Metor Storm Levels
## Overview
Implements the Space Attackers metor storm levels. Meteor storm levels are special levels that come in between regular game levels. They do not have an enemy grid and do not have level numbers or affect the level number count.
- implement in a new file called src\levels\meteor_level.py

# Level mechanics
- Meteor storm level happens after each 3 regular levels.
- Meteor storm level ends if player is destroyed - do not resume storm level, proceed to next regular level or end game if zero lives.
- all Metor configurable values should go in game_config.toml in [meteors] section
- Meteor storm ends after spawning meteors for some time (default 1 min, configurable) - AND after all spawned meteors have exited bottom of window
- Player surviving the level gets bonus equal to most recent regular level bonus.
- Meteor spawn rate should start low (3 per second, configurable) and increase with a percent function based on the regular level number most recently played (configurable)

# Meteor Features:
- Meteors spawn randomly off the top of the window. Use same logic as powerups use.
- Meteors move down the screen in a random direction, constrained to always hit the bottom of the window and not go off the side. use same math as powerups do for this calculation.
- Meteor sprites are found in assets\images\PNG\Meteors
- Use all the sprites in Meteors folder to make a variety of sizes and colors
- use 30% large, 40% medium, and 30% small probability to spawn
- Even mix of brown and grey color
- Meteors should have random speeds with a configurable range with sane defaults but be much faster than powerups.
- Meteor collision with player causes player death
- Meteors can be destroyed just like grid enemies, larger ones have more HP
- Large: 1000 HP
- Med: 500 HP
- Small: 100 HP
- Reuse damage bar and explosion effects from the regular levels when enemies are hit and are killed.
- Power ups can appear in meteor levels with same chance based on the most recent regular level.

