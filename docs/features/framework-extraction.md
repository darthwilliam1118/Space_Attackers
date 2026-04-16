# Refactor: Extract Arcade Game Framework (agf)

## Overview
Extract reusable game infrastructure from Space Attackers into a standalone
Python package (`agf` — Arcade Game Framework) hosted in a separate GitHub
repository. Space Attackers then declares `agf` as a dependency and imports
from it. No gameplay changes. All existing tests must pass after migration.

This extraction is a prerequisite for implementing power-ups and building
future games (side-scrollers, platformers) on the same foundation.

## Two repositories

```
arcade-game-framework/          ← NEW repo: https://github.com/darthwilliam1118/arcade-game-framework
Space_Attackers/                ← EXISTING repo: updated to depend on agf
```

---

## Phase 0 — Create the framework repo first

Before touching Space Attackers, create and publish the framework repo
so that `pip install` works before any Space Attackers imports are changed.

### arcade-game-framework repo structure

```
arcade-game-framework/
├── .github/
│   └── workflows/
│       └── ci.yml              ← lint + test only (no PyInstaller)
├── .gitattributes
├── .gitignore
├── .pre-commit-config.yml      ← same Black + Ruff setup
├── pyproject.toml
├── README.md
├── src/
│   └── agf/
│       ├── __init__.py         ← version string only
│       ├── paths.py
│       ├── events.py           ← GameEvent base enum
│       ├── high_scores.py
│       ├── music.py
│       ├── player_state.py
│       ├── spawn_safety.py
│       ├── state.py            ← GameStateManager base class
│       ├── background/
│       │   ├── __init__.py
│       │   ├── background_config.py
│       │   ├── static_background.py
│       │   └── star_field.py
│       ├── sprites/
│       │   ├── __init__.py
│       │   ├── explosion.py
│       │   └── particles.py
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── hud_base.py
│       │   ├── score_popup.py
│       │   └── text_utils.py
│       ├── levels/
│       │   ├── __init__.py
│       │   └── base_level.py
│       ├── config/
│       │   ├── __init__.py
│       │   └── base_config.py  ← config loading pattern
│       └── views/
│           ├── __init__.py
│           ├── splash.py
│           ├── main_menu.py
│           ├── game_over.py
│           ├── score_entry.py
│           └── level_complete.py
└── tests/
    └── (migrated framework tests)
```

### Framework pyproject.toml

```toml
[project]
name = "arcade-game-framework"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "arcade>=3.3.3,<4.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov",
    "ruff",
    "black",
]
```

---

## What moves to agf — file by file

### agf/paths.py
Copy `src/paths.py` verbatim. Zero game-specific content.
Update internal import if any: none needed.

### agf/events.py
```python
# Base GameEvent enum — games extend this
from enum import Enum, auto

class GameEvent(Enum):
    PLAYER_KILLED = auto()
    LEVEL_COMPLETE = auto()
    ENEMY_DESTROYED = auto()
    POWERUP_COLLECTED = auto()
    # Games add their own values by subclassing or extending
```

Note: Python enums cannot be subclassed if they have members. Games that
need additional events should either import and re-export agf events in
their own enum, or simply define their own complete enum that includes
the agf values. Space Attackers re-exports these values from its own
`src/game_event.py` which becomes a thin re-export file:

```python
# src/game_event.py (Space Attackers — after migration)
from agf.events import GameEvent  # re-export, no changes to callers
__all__ = ["GameEvent"]
```

### agf/high_scores.py
Copy `src/high_scores.py` verbatim. No game-specific content.

### agf/music.py
Copy `src/music.py`. The track keys ("ending", "level_1" etc.) are
passed in by the game — the MusicPlayer itself is generic.

### agf/player_state.py
Copy `src/player_state.py` verbatim.

### agf/spawn_safety.py
Copy `src/spawn_safety.py` verbatim.

### agf/background/
Copy `src/background.py` split into:
- `agf/background/static_background.py` — StaticBackground class
- `agf/background/star_field.py` — ProceduralStarField class
- `agf/background/background_config.py` — BackgroundConfig dataclass
  (copy from `src/background_config.py`)
- `agf/background/__init__.py` — re-exports all three for convenience:
  ```python
  from agf.background.static_background import StaticBackground
  from agf.background.star_field import ProceduralStarField
  from agf.background.background_config import BackgroundConfig
  ```

### agf/sprites/explosion.py
Copy `src/sprites/explosion.py`. Check for any Space Attackers-specific
imports — there should be none beyond arcade and agf.paths.

### agf/sprites/particles.py
Copy `src/sprites/particles.py`. Check for game-specific imports.

### agf/ui/text_utils.py
Copy `src/ui/text_utils.py` verbatim.

### agf/ui/score_popup.py
Copy `src/ui/score_popup.py`. No game-specific content.

### agf/ui/hud_base.py
Do NOT copy `src/ui/hud.py` directly — it references Space Attackers-
specific HP bar logic and player ship references. Instead extract a
minimal `HUDBase` class that handles common patterns (font loading,
text object management, draw ordering) and leave game-specific HUD
logic in `src/ui/hud.py` which subclasses it:

```python
# agf/ui/hud_base.py
class HUDBase:
    """Base class for game HUDs. Manages text object lifecycle.
    Subclass and implement draw() for game-specific layouts."""

    def __init__(self, window_width: int, window_height: int):
        self.window_width = window_width
        self.window_height = window_height
        self._texts: list[arcade.Text] = []

    def draw(self) -> None:
        for t in self._texts:
            t.draw()
```

Space Attackers' `src/ui/hud.py` subclasses `HUDBase`:
```python
from agf.ui.hud_base import HUDBase

class HUD(HUDBase):
    # existing implementation unchanged
```

### agf/levels/base_level.py
Copy `src/levels/base_level.py` verbatim. It has no Space Attackers
imports — it was designed to be generic.

### agf/config/base_config.py
This is the most important design decision in the extraction.

`GameConfig` in Space Attackers is a monolithic dataclass that knows
about ShipConfig, EnemyConfig, DivingConfig. The reusable parts are:
- The TOML loading pattern
- The PyInstaller-aware path resolution (_config_path())
- The argv override system (_apply_argv_overrides())
- The save() pattern

Extract these as a base class. Each game subclasses it and adds its
own sections:

```python
# agf/config/base_config.py
from __future__ import annotations
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def config_path(filename: str = "game_config.toml") -> Path:
    """PyInstaller-aware config file path resolution.
    When frozen: next to the .exe (user-editable).
    In dev: project root (two levels above agf package).
    Games pass their own filename if needed.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / filename
    # Walk up from this file to find project root
    return Path(__file__).parent.parent.parent.parent / filename


@dataclass
class BaseGameConfig:
    """Base config with common fields all games share.

    Subclass this in your game and add game-specific sections.
    Override load() to parse your additional TOML sections.
    Override save() to write them back.
    """
    starting_level: int = 1
    num_lives: int = 3
    music_volume: int = 80
    effects_volume: int = 80
    debug: bool = False
    god_mode: bool = False
    max_window_height: int = 1024
    sprite_scale: float = 1.0

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "BaseGameConfig":
        """Load from TOML. Subclasses call super().load() then
        parse their own sections."""
        raise NotImplementedError

    def save(self, path: Optional[Path] = None) -> None:
        """Write config to TOML. Subclasses override to include
        their own sections."""
        raise NotImplementedError
```

Space Attackers' `src/game_config.py` retains all its existing logic
but imports and subclasses BaseGameConfig:

```python
# src/game_config.py (after migration) — abbreviated
from agf.config.base_config import BaseGameConfig, config_path
from src.ship_config import ShipConfig
from src.enemy_config import EnemyConfig
# ... etc

@dataclass
class GameConfig(BaseGameConfig):
    ship: ShipConfig = None
    enemies: EnemyConfig = None
    # ... all existing fields and methods unchanged
    # _config_path() replaced by agf.config_path()
    # load() and save() remain in full
```

### agf/state.py — GameStateManager base

The `GameStateManager` pattern is reusable but the specific states and
view imports are not. Extract the base pattern:

```python
# agf/state.py
from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    import arcade

log = logging.getLogger(__name__)


class BaseGameStateManager:
    """Base state manager. Subclass and implement _enter_state()."""

    def __init__(self, window: "arcade.Window") -> None:
        self.window = window
        self.context: dict[str, Any] = {}
        self.state: Any = None

    def transition(self, new_state: Any, **context: Any) -> None:
        log.debug("State: %s → %s  ctx=%s",
                  getattr(self.state, 'name', self.state),
                  getattr(new_state, 'name', new_state),
                  context)
        self.state = new_state
        self.context.update(context)
        self._enter_state(new_state)

    def _enter_state(self, state: Any) -> None:
        raise NotImplementedError
```

Space Attackers' `src/state.py` retains all its logic but subclasses:

```python
# src/state.py (after migration)
from agf.state import BaseGameStateManager

class GameStateManager(BaseGameStateManager):
    def _enter_state(self, state: GameState) -> None:
        # all existing match/case logic unchanged
```

### agf/views/

Each view is extracted with Space Attackers-specific strings made into
overridable class attributes or constructor parameters.

#### agf/views/splash.py
`SplashView` from Space Attackers is almost generic. Changes needed:
- `TITLE = "Space Attackers!"` → overridable class attribute
- `PROMPT = "Press any key to continue..."` → overridable class attribute
- `_AUTO_ADVANCE = 5.0` → overridable class attribute
- Music track preloading is game-specific — extract to an overridable
  `_preload_tracks()` method that games override
- `_go_to_main()` calls `GameState.MAIN` — make this call
  `self._on_complete()` which games override

```python
# agf/views/splash.py
class SplashView(arcade.View):
    TITLE: str = "My Game"
    PROMPT: str = "Press any key to continue..."
    AUTO_ADVANCE: float = 5.0

    def __init__(self, on_complete) -> None:
        """on_complete: callable called when splash ends."""
        super().__init__()
        self._on_complete = on_complete
        # ... rest of init unchanged

    def _preload_tracks(self) -> None:
        """Override to preload game-specific audio tracks."""
        self._assets_ready = True  # default: no preloading needed
```

Space Attackers subclasses:
```python
# src/views/splash.py (after migration)
from agf.views.splash import SplashView as _SplashBase
from src.state import GameState

class SplashView(_SplashBase):
    TITLE = "Space Attackers!"
    AUTO_ADVANCE = 5.0

    def __init__(self, manager) -> None:
        self._manager = manager
        super().__init__(on_complete=self._go_to_main)

    def _preload_tracks(self) -> None:
        self.window.music.load_track("ending")
        self._ending_ready = True
        for key in ("level_1", "level_2", "level_3"):
            self.window.music.load_track(key)
        self._assets_ready = True

    def _go_to_main(self) -> None:
        self._manager.transition(GameState.MAIN)
```

#### agf/views/main_menu.py
`MainMenuView` is the most complex view to extract. It has:
- Page cycling logic (generic)
- Leaderboard rendering (generic — uses HighScoreTable)
- Instructions rendering from README (generic — great pattern to keep)
- Hard-coded key bindings (game-specific)
- Hard-coded music track "ending" (game-specific)
- Hard-coded `GameState.GAME_INIT` transition (game-specific)

Approach: keep all the rendering logic in `agf`, make key handling and
transitions overridable:

```python
# agf/views/main_menu.py
class MainMenuViewBase(arcade.View):
    """Generic cycling main menu with leaderboard + instructions.

    Subclass and implement:
      on_start_1p() — called when 1P start key pressed
      on_start_2p() — called when 2P start key pressed
      on_config()   — called when config key pressed
      on_exit()     — called when exit key pressed
      music_track() → str — track key to play on show
    """
    PAGES = ["LEADERBOARD", "INSTRUCTIONS"]
    CYCLE_INTERVAL = 15.0

    def on_start_1p(self) -> None: pass
    def on_start_2p(self) -> None: pass
    def on_config(self) -> None: pass
    def on_exit(self) -> None: pass

    def music_track(self) -> str:
        return "ending"

    # All rendering logic from current MainMenuView goes here unchanged
    # on_key_press() calls the above hooks instead of direct transitions
```

Space Attackers subclasses:
```python
# src/views/main_menu.py (after migration)
from agf.views.main_menu import MainMenuViewBase
from src.state import GameState

class MainMenuView(MainMenuViewBase):
    def __init__(self, manager) -> None:
        super().__init__()
        self._manager = manager

    def on_start_1p(self) -> None:
        cfg = self._manager.context.get("config")
        self._manager.transition(GameState.GAME_INIT, num_players=1, config=cfg)

    def on_start_2p(self) -> None:
        cfg = self._manager.context.get("config")
        self._manager.transition(GameState.GAME_INIT, num_players=2, config=cfg)

    def on_config(self) -> None:
        self._manager.transition(GameState.GAME_CONFIG)

    def on_exit(self) -> None:
        self._manager.transition(GameState.EXIT)
```

#### agf/views/game_over.py
Copy `src/views/game_over.py`. Make title string and transition target
overridable class attributes or callbacks. Same pattern as splash.

#### agf/views/score_entry.py
Copy `src/views/score_entry.py`. Make transition target overridable.

#### agf/views/level_complete.py
Copy `src/views/level_complete.py`. Make transition target overridable.

### agf/window.py — GameWindow base

Extract the common window setup pattern:

```python
# agf/window.py
class GameWindowBase(arcade.Window):
    """Base game window. Subclass and implement create_state_manager()."""

    TITLE: str = "My Game"
    ASPECT_RATIO: float = 1.25  # width = height * ratio

    def __init__(self, config: BaseGameConfig) -> None:
        h = config.max_window_height
        w = int(h * self.ASPECT_RATIO)
        super().__init__(w, h, self.TITLE, center_window=True)
        arcade.set_background_color(arcade.color.BLACK)

        self._load_fonts(config)
        bg = config.background if hasattr(config, 'background') else None
        if bg is not None:
            self.background = StaticBackground(bg.background_image, w, h)
            self.star_field = ProceduralStarField(
                w, h, bg.star_count, bg.star_speed_min, bg.star_speed_max
            )
        self.music = MusicPlayer()
        self.music.set_volume(config.music_volume)

    def _load_fonts(self, config) -> None:
        """Override to load game-specific fonts."""
        pass

    def start(self) -> None:
        """Call after __init__ to begin the game."""
        raise NotImplementedError
```

Space Attackers' `src/game.py` subclasses:
```python
# src/game.py (after migration)
from agf.window import GameWindowBase
from src.game_config import GameConfig
from src.state import GameState, GameStateManager

class GameWindow(GameWindowBase):
    TITLE = "Space Attackers"

    def __init__(self) -> None:
        cfg = GameConfig.load()
        super().__init__(cfg)
        arcade.load_font(resource_path("assets/fonts/kenvector_future2.ttf"))
        arcade.load_font(resource_path("assets/fonts/kenvector_future_thin2.ttf"))
        self._manager = GameStateManager(self)
        self._manager.transition(GameState.SPLASH)
```

---

## Space Attackers import migration map

After the framework is published, update every import in Space Attackers:

| Old import | New import |
|-----------|-----------|
| `from src.paths import resource_path` | `from agf.paths import resource_path` |
| `from src.high_scores import ...` | `from agf.high_scores import ...` |
| `from src.music import MusicPlayer` | `from agf.music import MusicPlayer` |
| `from src.player_state import PlayerState` | `from agf.player_state import PlayerState` |
| `from src.spawn_safety import ...` | `from agf.spawn_safety import ...` |
| `from src.background import ...` | `from agf.background import ...` |
| `from src.background_config import ...` | `from agf.background import BackgroundConfig` |
| `from src.sprites.explosion import ...` | `from agf.sprites.explosion import ...` |
| `from src.sprites.particles import ...` | `from agf.sprites.particles import ...` |
| `from src.ui.text_utils import ...` | `from agf.ui.text_utils import ...` |
| `from src.ui.score_popup import ...` | `from agf.ui.score_popup import ...` |
| `from src.levels.base_level import ...` | `from agf.levels.base_level import ...` |
| `from src.game_event import GameEvent` | unchanged (thin re-export) |
| `from src.state import GameStateManager` | unchanged (subclass stays in src) |
| `from src.views.splash import SplashView` | unchanged (subclass stays in src) |
| `from src.views.main_menu import ...` | unchanged (subclass stays in src) |

Files DELETED from Space Attackers after migration:
```
src/paths.py           → moved to agf
src/high_scores.py     → moved to agf
src/music.py           → moved to agf
src/player_state.py    → moved to agf
src/spawn_safety.py    → moved to agf
src/background.py      → moved to agf
src/background_config.py → moved to agf
src/sprites/explosion.py → moved to agf
src/sprites/particles.py → moved to agf
src/ui/text_utils.py   → moved to agf
src/ui/score_popup.py  → moved to agf
src/levels/base_level.py → moved to agf
```

Files MODIFIED in Space Attackers (not deleted):
```
src/game_config.py     → subclasses BaseGameConfig
src/game_event.py      → re-exports agf.events.GameEvent
src/state.py           → subclasses BaseGameStateManager
src/game.py            → subclasses GameWindowBase
src/ui/hud.py          → subclasses HUDBase
src/views/splash.py    → subclasses agf SplashView
src/views/main_menu.py → subclasses agf MainMenuViewBase
src/views/game_over.py → subclasses agf GameOverView
src/views/score_entry.py → subclasses agf ScoreEntryView
src/views/level_complete.py → subclasses agf LevelCompleteView
```

---

## Space Attackers pyproject.toml — add agf dependency

```toml
[project]
dependencies = [
    "arcade>=3.3.3,<4.0",
    "arcade-game-framework @ git+https://github.com/darthwilliam1118/arcade-game-framework@main",
]
```

This uses a direct git dependency — no PyPI publishing required. CI
will install it automatically. PyInstaller bundles it with the exe
since pip resolves and installs the package to site-packages.

---

## CLAUDE.md additions for both repos

### arcade-game-framework CLAUDE.md
```markdown
# Arcade Game Framework (agf)

## Purpose
Reusable infrastructure for Arcade-based games. Contains no game-specific
logic — ships, enemies, levels, power-ups etc. all live in the game repos.

## Package name
agf — import as `from agf.paths import resource_path` etc.

## What belongs here
- State machine base classes
- Generic views (splash, menu, game over, score entry, level complete)
- Background rendering (static + procedural star field)
- Visual effects (explosion, particles, shockwave)
- UI utilities (text_utils, score_popup, hud base)
- High score persistence
- Music player
- Config base class and loading pattern
- BaseLevel abstraction
- PlayerState, spawn_safety

## What does NOT belong here
- Game-specific sprites (ships, enemies, bullets)
- Game-specific state transitions
- Game-specific config sections
- Game-specific level implementations
```

### Space Attackers CLAUDE.md addition
```markdown
## Framework dependency
Shared infrastructure is in the agf package (arcade-game-framework repo).
Import framework classes from agf:
  from agf.paths import resource_path
  from agf.high_scores import HighScoreTable
  from agf.background import StaticBackground, ProceduralStarField
  etc.

Do NOT re-implement anything already in agf. Check agf first.
Game-specific classes (ship, enemies, levels, power-ups) stay in src/.
```

---

## Migration order — do these in sequence

### Step 1 — Create arcade-game-framework repo
- The repo is been created at https://github.com/darthwilliam1118/arcade-game-framework
- The repo is cloned locally at C:\Users\darth\Code\arcade-game-framework
- The repo is empty except for a python .gitignore and README.md and LICENSE
- Set up pyproject.toml, .gitattributes, .pre-commit-config.yml,
  CI workflow (lint + test, no PyInstaller)
- Create empty src/agf/__init__.py with version = "0.1.0"
- Initial commit and push

### Step 2 — Migrate zero-dependency files first
These have no imports from other src/ files — safest to move first:

Copy verbatim to agf (no changes):
- `src/paths.py` → `src/agf/paths.py`
- `src/high_scores.py` → `src/agf/high_scores.py`
- `src/music.py` → `src/agf/music.py`
- `src/player_state.py` → `src/agf/player_state.py`
- `src/spawn_safety.py` → `src/agf/spawn_safety.py`
- `src/background_config.py` → `src/agf/background/background_config.py`
- `src/ui/text_utils.py` → `src/agf/ui/text_utils.py`
- `src/ui/score_popup.py` → `src/agf/ui/score_popup.py`
- `src/levels/base_level.py` → `src/agf/levels/base_level.py`

Commit to agf repo.

### Step 3 — Add agf as dependency to Space Attackers
```
pip install "arcade-game-framework @ git+https://github.com/darthwilliam1118/arcade-game-framework@main"
```
Update Space Attackers pyproject.toml.
Run tests — they should still pass (nothing changed yet).

### Step 4 — Migrate each file in Space Attackers
For each file in the migration map above, in this order:
1. Update Space Attackers imports to use agf
2. Delete the old src/ file
3. Run tests — must pass before moving to next file

Order within Step 4:
```
paths.py           (update ~20 import sites)
high_scores.py     (update ~3 import sites)
music.py           (update ~4 import sites)
player_state.py    (update ~5 import sites)
spawn_safety.py    (update ~2 import sites)
background files   (update ~4 import sites)
text_utils.py      (update ~8 import sites)
score_popup.py     (update ~3 import sites)
base_level.py      (update ~4 import sites)
```

### Step 5 — Migrate files requiring modification
These need refactoring (base class extraction) before moving:

```
game_config.py     → extract BaseGameConfig to agf, subclass in Space Attackers
state.py           → extract BaseGameStateManager to agf
game.py            → extract GameWindowBase to agf
ui/hud.py          → extract HUDBase to agf
sprites/explosion  → copy to agf, update Space Attackers import
sprites/particles  → copy to agf, update Space Attackers import
```

### Step 6 — Migrate views
Each view gets an agf base class + Space Attackers subclass:
```
views/splash.py
views/main_menu.py
views/game_over.py
views/score_entry.py
views/level_complete.py
```

### Step 7 — Final verification
- Run full test suite in Space Attackers — all pass
- Run full test suite in arcade-game-framework — all pass
- Manual smoke test: launch game, play a level, complete it, game over,
  high score entry, config screen, exit
- Build exe via PyInstaller — confirm agf is bundled correctly
- Push both repos, confirm CI passes on both

---

## Unit tests

### In arcade-game-framework
Migrate any existing tests that test framework-level code:
- test_high_scores.py → moves to agf repo
- test_spawn_safety.py → moves to agf repo
- test_player_state.py → moves to agf (if exists)
- test_background.py → moves to agf (if exists)
- test_base_level.py → moves to agf

All tests in agf must run without a display and without game-specific
imports.

### In Space Attackers
All remaining tests stay — they test game-specific behaviour.
After migration, add smoke test that `import agf` succeeds and the
version string is accessible:
```python
def test_agf_importable():
    import agf
    assert hasattr(agf, '__version__')
```

---

## Implementation notes

- Do Step 4 one file at a time with a test run between each — do not
  batch multiple file migrations in one commit. If something breaks,
  the diff is small and the cause is obvious.
- The git dependency syntax in pyproject.toml pins to @main branch.
  Once agf is stable, pin to a specific tag instead:
  `@ git+https://...@v0.1.0` — this prevents surprise breakage if
  agf changes.
- PyInstaller bundles git-installed packages correctly because pip
  installs them to site-packages — the spec file needs no changes.
- The `_config_path()` function in game_config.py uses
  `Path(__file__).parent.parent` to find the project root. After
  migration to subclassing BaseGameConfig, verify the path resolution
  still points to the correct location — the agf package will be in
  site-packages, not the project tree, so `Path(__file__)` inside
  agf will be wrong for project-root resolution. The `config_path()`
  helper in agf uses `sys.executable` when frozen (correct) and
  a walk-up approach in dev — test this explicitly.
- `main_menu.py` reads `README.md` from the project root using
  `Path(__file__).parent.parent.parent`. After migration this path
  calculation must be updated in the agf base class — it should walk
  up from the calling game's package, not from agf's location.
  Pass the readme path as a constructor argument or class attribute
  to avoid fragile path arithmetic.
- Do not add `particles_config.py` to agf — it is currently
  Space Attackers-specific (tied to the game's particle tuning values).
  ParticlesConfig stays in `src/particles_config.py`. Only the
  particle sprite classes (ParticleEmitter, ShockwaveSprite) move to agf.
```
