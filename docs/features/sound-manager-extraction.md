# Refactor: Extract SoundManager to agf

## Overview
Move `SoundManager` from `src/sound_manager.py` in Space Attackers into
the arcade-game-framework package at `src/agf/sound_manager.py`. Update
all import sites in Space Attackers. No behaviour changes — this is a
pure mechanical extraction.

## Why agf
SoundManager has zero game-specific dependencies — it only uses
`arcade.Sound`, `arcade.play_sound()`, and `arcade.stop_sound()`.
Every Arcade game benefits from throttled sound playback and no game
should reimplement this pattern.

---

## Step 1 — Create agf/sound_manager.py

Create this file verbatim in the agf repo at `src/agf/sound_manager.py`:

```python
"""SoundManager — throttles simultaneous playbacks of one sound.

Tracks active pyglet Players; when the cap is reached the oldest is
stopped before a new one starts. Use a separate instance per sound type.

Example:
    self._sm_explosion = SoundManager(max_simultaneous=2)
    self._sm_explosion.play(self._snd_explosion, volume=0.8)
"""

from __future__ import annotations

import arcade


class SoundManager:
    """Throttles simultaneous playbacks of one sound to reduce audio thread load.

    Tracks active pyglet Players; when the cap is reached the oldest is
    stopped before a new one starts. Use a separate instance per sound type.
    """

    def __init__(self, max_simultaneous: int = 4) -> None:
        self._max = max_simultaneous
        self._active: list[arcade.pyglet.media.Player] = []

    def play(self, sound: arcade.Sound, volume: float = 1.0) -> None:
        """Play *sound* at *volume*, stopping the oldest playback if at cap."""
        self._active = [p for p in self._active if p.playing]
        if len(self._active) >= self._max:
            oldest = self._active.pop(0)
            arcade.stop_sound(oldest)
        player = arcade.play_sound(sound, volume=volume)
        if player is not None:
            self._active.append(player)

    @property
    def active_count(self) -> int:
        """Number of currently playing instances. Useful for debug display."""
        self._active = [p for p in self._active if p.playing]
        return len(self._active)
```

The only addition vs the original is the `active_count` property and
the module docstring — behaviour is identical.

---

## Step 2 — Add to agf __init__.py (optional convenience re-export)

If `src/agf/__init__.py` re-exports commonly used classes, add:

```python
from agf.sound_manager import SoundManager
```

If `__init__.py` is intentionally minimal (just a version string), skip
this — callers import from the module directly.

---

## Step 3 — Add unit test in agf

Create `tests/test_sound_manager.py` in the agf repo. All tests must
run without a display or audio device.

```python
"""Tests for SoundManager — no display or audio device required."""
from __future__ import annotations
from unittest.mock import MagicMock, patch
from agf.sound_manager import SoundManager


def _make_player(playing: bool = True):
    p = MagicMock()
    p.playing = playing
    return p


def test_play_adds_to_active() -> None:
    sm = SoundManager(max_simultaneous=3)
    mock_player = _make_player()
    with patch("agf.sound_manager.arcade.play_sound", return_value=mock_player):
        with patch("agf.sound_manager.arcade.stop_sound"):
            sm.play(MagicMock())
    assert len(sm._active) == 1


def test_play_stops_oldest_when_at_cap() -> None:
    sm = SoundManager(max_simultaneous=2)
    oldest = _make_player(playing=True)
    sm._active = [oldest, _make_player(playing=True)]
    new_player = _make_player()
    with patch("agf.sound_manager.arcade.play_sound", return_value=new_player):
        with patch("agf.sound_manager.arcade.stop_sound") as mock_stop:
            sm.play(MagicMock())
    mock_stop.assert_called_once_with(oldest)
    assert new_player in sm._active


def test_play_cleans_up_finished_players() -> None:
    sm = SoundManager(max_simultaneous=3)
    finished = _make_player(playing=False)
    sm._active = [finished]
    new_player = _make_player()
    with patch("agf.sound_manager.arcade.play_sound", return_value=new_player):
        with patch("agf.sound_manager.arcade.stop_sound"):
            sm.play(MagicMock())
    assert finished not in sm._active
    assert new_player in sm._active


def test_active_count_excludes_finished() -> None:
    sm = SoundManager(max_simultaneous=4)
    sm._active = [_make_player(True), _make_player(False), _make_player(True)]
    assert sm.active_count == 2


def test_play_returns_without_error_when_play_sound_returns_none() -> None:
    sm = SoundManager(max_simultaneous=2)
    with patch("agf.sound_manager.arcade.play_sound", return_value=None):
        with patch("agf.sound_manager.arcade.stop_sound"):
            sm.play(MagicMock())  # must not raise
    assert len(sm._active) == 0
```

---

## Step 4 — Commit and tag agf

```bash
# In arcade-game-framework repo
git add src/agf/sound_manager.py tests/test_sound_manager.py
git commit -m "feat: add SoundManager for throttled sound playback"
git tag -a v0.2.0 -m "Add SoundManager"
git push origin main --tags
```

---

## Step 5 — Update Space Attackers dependency pin

In `Space_Attackers/pyproject.toml`, bump the agf version pin:

```toml
"arcade-game-framework @ git+https://github.com/darthwilliam1118/arcade-game-framework@v0.2.0",
```

Then reinstall:

```bash
pip install -e ".[dev]"
```

Verify agf installed correctly:

```bash
python -c "from agf.sound_manager import SoundManager; print('OK')"
```

---

## Step 6 — Update imports in Space Attackers

### src/views/run_level.py
```python
# Remove:
from src.sound_manager import SoundManager

# Add:
from agf.sound_manager import SoundManager
```

### src/views/level_complete.py
```python
# Remove:
from src.sound_manager import SoundManager

# Add:
from agf.sound_manager import SoundManager
```

These are the only two files that import SoundManager. Verify with:

```bash
grep -r "from src.sound_manager" src/
```

Output must be empty after the change.

---

## Step 7 — Delete src/sound_manager.py from Space Attackers

```bash
git rm src/sound_manager.py
```

---

## Step 8 — Run tests and verify

```bash
pytest --cov=src
```

All existing tests must pass. Run the game manually and confirm:
- Explosion sounds still throttle correctly during heavy combat
- No ImportError on startup
- No regression in sound behaviour

---

## Step 9 — Commit Space Attackers changes

```bash
git add -A
git commit -m "refactor: move SoundManager to agf v0.2.0"
git push
```

---

## Checklist for Claude Code

Work in this exact order — each step is independently verifiable:

1. Create `src/agf/sound_manager.py` in agf repo (copy from brief above)
2. Create `tests/test_sound_manager.py` in agf repo
3. Run agf tests — all pass
4. Commit and tag agf v0.2.0, push with tags
5. Update pyproject.toml in Space Attackers to @v0.2.0
6. `pip install -e ".[dev]"` in Space Attackers
7. Update import in `src/views/run_level.py`
8. Update import in `src/views/level_complete.py`
9. `grep -r "from src.sound_manager" src/` — must return empty
10. `git rm src/sound_manager.py`
11. `pytest --cov=src` — all pass
12. Commit Space Attackers, push

## Implementation notes

- The `arcade.pyglet.media.Player` type hint in `_active` list is correct
  for Arcade 3.3.x — do not change it to a generic `Any`
- `arcade.stop_sound()` expects the Player object returned by
  `arcade.play_sound()`, not the Sound object — this is already correct
  in the existing implementation
- Do not add `max_concurrent` as a per-call parameter at this stage —
  keep the API minimal. Per-call limits can be added later if needed.
- The `active_count` property is the only addition beyond the original —
  it's useful for debug display and costs nothing
- Both import sites (`run_level.py` and `level_complete.py`) use
  `SoundManager` identically — no call-site changes needed, only the
  import line
