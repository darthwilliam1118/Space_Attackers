"""GameConfig — loads and saves game_config.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_PATH = Path(__file__).parent.parent / "game_config.toml"


@dataclass
class GameConfig:
    starting_level: int = 1
    num_lives: int = 3
    spawn_safe_radius: int = 80

    @classmethod
    def load(cls, path: Path = _DEFAULT_PATH) -> "GameConfig":
        """Load config from *path*. Missing keys fall back to dataclass defaults."""
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        game = data.get("game", {})
        return cls(
            starting_level=int(game.get("starting_level", cls.starting_level)),
            num_lives=int(game.get("num_lives", cls.num_lives)),
            spawn_safe_radius=int(game.get("spawn_safe_radius", cls.spawn_safe_radius)),
        )

    def save(self, path: Path = _DEFAULT_PATH) -> None:
        """Persist current values back to *path* as TOML."""
        lines = [
            "[game]\n",
            f"starting_level = {self.starting_level}\n",
            f"num_lives = {self.num_lives}\n",
            f"spawn_safe_radius = {self.spawn_safe_radius}\n",
        ]
        path.write_text("".join(lines), encoding="utf-8")
