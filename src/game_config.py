"""GameConfig — loads and saves game_config.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from src.background_config import BackgroundConfig
from src.enemy_config import EnemyConfig
from src.ship_config import ShipConfig

_DEFAULT_PATH = Path(__file__).parent.parent / "game_config.toml"


@dataclass
class GameConfig:
    starting_level: int = 1
    num_lives: int = 3
    spawn_safe_radius: int = 80
    debug: bool = False
    ship: ShipConfig = None  # type: ignore[assignment]
    enemies: EnemyConfig = None  # type: ignore[assignment]
    background: BackgroundConfig = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.ship is None:
            self.ship = ShipConfig()
        if self.enemies is None:
            self.enemies = EnemyConfig()
        if self.background is None:
            self.background = BackgroundConfig()

    @classmethod
    def load(cls, path: Path = _DEFAULT_PATH) -> "GameConfig":
        """Load config from *path*. Missing keys fall back to dataclass defaults."""
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        game = data.get("game", {})
        ship = data.get("ship", {})
        sc = ShipConfig(
            ship_speed=float(ship.get("ship_speed", ShipConfig.ship_speed)),
            ship_accel=float(ship.get("ship_accel", ShipConfig.ship_accel)),
            ship_decel=float(ship.get("ship_decel", ShipConfig.ship_decel)),
            ship_tilt_rate=float(ship.get("ship_tilt_rate", ShipConfig.ship_tilt_rate)),
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
        ec_raw = data.get("enemies", {})
        ec = EnemyConfig(
            enemy_cols=int(ec_raw.get("enemy_cols", EnemyConfig.enemy_cols)),
            enemy_rows=int(ec_raw.get("enemy_rows", EnemyConfig.enemy_rows)),
            enemy_col_width_factor=float(ec_raw.get("enemy_col_width_factor", EnemyConfig.enemy_col_width_factor)),
            enemy_speed_initial=float(ec_raw.get("enemy_speed_initial", EnemyConfig.enemy_speed_initial)),
            enemy_speed_max_bonus=float(ec_raw.get("enemy_speed_max_bonus", EnemyConfig.enemy_speed_max_bonus)),
            enemy_speed_level_bonus=float(ec_raw.get("enemy_speed_level_bonus", EnemyConfig.enemy_speed_level_bonus)),
            enemy_side_margin=float(ec_raw.get("enemy_side_margin", EnemyConfig.enemy_side_margin)),
            enemy_drop_distance=float(ec_raw.get("enemy_drop_distance", EnemyConfig.enemy_drop_distance)),
            enemy_fire_interval_min=float(ec_raw.get("enemy_fire_interval_min", EnemyConfig.enemy_fire_interval_min)),
            enemy_fire_interval_max=float(ec_raw.get("enemy_fire_interval_max", EnemyConfig.enemy_fire_interval_max)),
            enemy_bullet_speed=float(ec_raw.get("enemy_bullet_speed", EnemyConfig.enemy_bullet_speed)),
        )
        bg_raw = data.get("background", {})
        bc = BackgroundConfig(
            background_image=str(bg_raw.get("background_image", BackgroundConfig.background_image)),
            star_count=int(bg_raw.get("star_count", BackgroundConfig.star_count)),
            star_speed_min=float(bg_raw.get("star_speed_min", BackgroundConfig.star_speed_min)),
            star_speed_max=float(bg_raw.get("star_speed_max", BackgroundConfig.star_speed_max)),
        )
        return cls(
            starting_level=int(game.get("starting_level", cls.starting_level)),
            num_lives=int(game.get("num_lives", cls.num_lives)),
            spawn_safe_radius=int(game.get("spawn_safe_radius", cls.spawn_safe_radius)),
            debug=bool(game.get("debug", cls.debug)),
            ship=sc,
            enemies=ec,
            background=bc,
        )

    def save(self, path: Path = _DEFAULT_PATH) -> None:
        """Persist current values back to *path* as TOML."""
        sc = self.ship
        lines = [
            "[game]\n",
            f"starting_level = {self.starting_level}\n",
            f"num_lives = {self.num_lives}\n",
            f"spawn_safe_radius = {self.spawn_safe_radius}\n",
            f"debug = {'true' if self.debug else 'false'}\n",
            "\n[ship]\n",
            f"ship_speed = {sc.ship_speed}\n",
            f"ship_accel = {sc.ship_accel}\n",
            f"ship_decel = {sc.ship_decel}\n",
            f"ship_tilt_rate = {sc.ship_tilt_rate}\n",
            f"fire_cooldown = {sc.fire_cooldown}\n",
            f"bullet_speed = {sc.bullet_speed}\n",
            f"spawn_invincible_duration = {sc.spawn_invincible_duration}\n",
            f"ship_zone_height_pct = {sc.ship_zone_height_pct}\n",
            f"explosion_frame_duration = {sc.explosion_frame_duration}\n",
        ]
        bg = self.background
        lines += [
            "\n[background]\n",
            f'background_image = "{bg.background_image}"\n',
            f"star_count = {bg.star_count}\n",
            f"star_speed_min = {bg.star_speed_min}\n",
            f"star_speed_max = {bg.star_speed_max}\n",
        ]
        ec = self.enemies
        lines += [
            "\n[enemies]\n",
            f"enemy_cols = {ec.enemy_cols}\n",
            f"enemy_rows = {ec.enemy_rows}\n",
            f"enemy_col_width_factor = {ec.enemy_col_width_factor}\n",
            f"enemy_speed_initial = {ec.enemy_speed_initial}\n",
            f"enemy_speed_max_bonus = {ec.enemy_speed_max_bonus}\n",
            f"enemy_speed_level_bonus = {ec.enemy_speed_level_bonus}\n",
            f"enemy_side_margin = {ec.enemy_side_margin}\n",
            f"enemy_drop_distance = {ec.enemy_drop_distance}\n",
            f"enemy_fire_interval_min = {ec.enemy_fire_interval_min}\n",
            f"enemy_fire_interval_max = {ec.enemy_fire_interval_max}\n",
            f"enemy_bullet_speed = {ec.enemy_bullet_speed}\n",
        ]
        path.write_text("".join(lines), encoding="utf-8")
