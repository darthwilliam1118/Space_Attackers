"""GameConfig — loads and saves game_config.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from src.ship_config import ShipConfig

_DEFAULT_PATH = Path(__file__).parent.parent / "game_config.toml"


@dataclass
class GameConfig:
    starting_level: int = 1
    num_lives: int = 3
    spawn_safe_radius: int = 80
    ship: ShipConfig = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.ship is None:
            self.ship = ShipConfig()

    @classmethod
    def load(cls, path: Path = _DEFAULT_PATH) -> "GameConfig":
        """Load config from *path*. Missing keys fall back to dataclass defaults."""
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        game = data.get("game", {})
        ship = data.get("ship", {})
        sc = ShipConfig(
            ship_speed=float(ship.get("ship_speed", ShipConfig.ship_speed)),
            fire_cooldown=float(ship.get("fire_cooldown", ShipConfig.fire_cooldown)),
            bullet_speed=float(ship.get("bullet_speed", ShipConfig.bullet_speed)),
            spawn_invincible_duration=float(
                ship.get("spawn_invincible_duration", ShipConfig.spawn_invincible_duration)
            ),
            ship_zone_height_pct=float(
                ship.get("ship_zone_height_pct", ShipConfig.ship_zone_height_pct)
            ),
            explosion_frame_duration=float(
                ship.get("explosion_frame_duration", ShipConfig.explosion_frame_duration)
            ),
        )
        return cls(
            starting_level=int(game.get("starting_level", cls.starting_level)),
            num_lives=int(game.get("num_lives", cls.num_lives)),
            spawn_safe_radius=int(game.get("spawn_safe_radius", cls.spawn_safe_radius)),
            ship=sc,
        )

    def save(self, path: Path = _DEFAULT_PATH) -> None:
        """Persist current values back to *path* as TOML."""
        sc = self.ship
        lines = [
            "[game]\n",
            f"starting_level = {self.starting_level}\n",
            f"num_lives = {self.num_lives}\n",
            f"spawn_safe_radius = {self.spawn_safe_radius}\n",
            "\n[ship]\n",
            f"ship_speed = {sc.ship_speed}\n",
            f"fire_cooldown = {sc.fire_cooldown}\n",
            f"bullet_speed = {sc.bullet_speed}\n",
            f"spawn_invincible_duration = {sc.spawn_invincible_duration}\n",
            f"ship_zone_height_pct = {sc.ship_zone_height_pct}\n",
            f"explosion_frame_duration = {sc.explosion_frame_duration}\n",
        ]
        path.write_text("".join(lines), encoding="utf-8")
