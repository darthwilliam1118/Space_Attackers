"""Point agf at the game's project root so resource_path() finds assets."""

from __future__ import annotations

from pathlib import Path

from agf.paths import set_project_root

set_project_root(Path(__file__).resolve().parent.parent)
