"""GameConfig — loads and saves game_config.toml."""

from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.background_config import BackgroundConfig
from src.enemy_config import EnemyConfig
from src.particles_config import ParticlesConfig
from src.ship_config import ShipConfig
from src.ui_config import UIConfig


def _config_path() -> Path:
    """Return the path to game_config.toml.

    When frozen by PyInstaller, look next to the .exe so users can edit it.
    In dev, look in the project root (two levels above src/).
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "game_config.toml"
    return Path(__file__).parent.parent / "game_config.toml"


@dataclass
class GameConfig:
    starting_level: int = 1
    num_lives: int = 3
    spawn_safe_radius: int = 80
    debug: bool = False
    max_window_height: int = 1024  # height in px; width = height * 0.75 (4:3)
    ship: ShipConfig = None  # type: ignore[assignment]
    enemies: EnemyConfig = None  # type: ignore[assignment]
    background: BackgroundConfig = None  # type: ignore[assignment]
    particles: ParticlesConfig = None  # type: ignore[assignment]
    ui: UIConfig = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.ship is None:
            self.ship = ShipConfig()
        if self.enemies is None:
            self.enemies = EnemyConfig()
        if self.background is None:
            self.background = BackgroundConfig()
        if self.particles is None:
            self.particles = ParticlesConfig()
        if self.ui is None:
            self.ui = UIConfig()

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "GameConfig":
        """Load config from *path*. Missing keys fall back to dataclass defaults.

        If *path* is None, uses the platform-appropriate default (next to the .exe
        when frozen, or the project root in dev). Returns default config on any error.
        """
        if path is None:
            path = _config_path()
        try:
            with open(path, "rb") as fh:
                data = tomllib.load(fh)
        except Exception:
            return cls()

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
            enemy_cols_start=int(ec_raw.get("enemy_cols_start", EnemyConfig.enemy_cols_start)),
            enemy_rows_start=int(ec_raw.get("enemy_rows_start", EnemyConfig.enemy_rows_start)),
            enemy_cols_max=int(ec_raw.get("enemy_cols_max", EnemyConfig.enemy_cols_max)),
            enemy_rows_max=int(ec_raw.get("enemy_rows_max", EnemyConfig.enemy_rows_max)),
            enemy_cols_per_level=int(ec_raw.get("enemy_cols_per_level", EnemyConfig.enemy_cols_per_level)),
            enemy_rows_per_level=int(ec_raw.get("enemy_rows_per_level", EnemyConfig.enemy_rows_per_level)),
            enemy_col_width_factor=float(ec_raw.get("enemy_col_width_factor", EnemyConfig.enemy_col_width_factor)),
            enemy_speed_initial=float(ec_raw.get("enemy_speed_initial", EnemyConfig.enemy_speed_initial)),
            enemy_speed_max_bonus=float(ec_raw.get("enemy_speed_max_bonus", EnemyConfig.enemy_speed_max_bonus)),
            enemy_speed_level_pct=float(ec_raw.get("enemy_speed_level_pct", EnemyConfig.enemy_speed_level_pct)),
            enemy_side_margin=float(ec_raw.get("enemy_side_margin", EnemyConfig.enemy_side_margin)),
            enemy_drop_distance=float(ec_raw.get("enemy_drop_distance", EnemyConfig.enemy_drop_distance)),
            enemy_fire_interval_min_l1=float(ec_raw.get("enemy_fire_interval_min_l1", EnemyConfig.enemy_fire_interval_min_l1)),
            enemy_fire_interval_max_l1=float(ec_raw.get("enemy_fire_interval_max_l1", EnemyConfig.enemy_fire_interval_max_l1)),
            enemy_fire_interval_scale=float(ec_raw.get("enemy_fire_interval_scale", EnemyConfig.enemy_fire_interval_scale)),
            enemy_fire_interval_min_cap=float(ec_raw.get("enemy_fire_interval_min_cap", EnemyConfig.enemy_fire_interval_min_cap)),
            enemy_fire_interval_max_cap=float(ec_raw.get("enemy_fire_interval_max_cap", EnemyConfig.enemy_fire_interval_max_cap)),
            enemy_bullet_speed=float(ec_raw.get("enemy_bullet_speed", EnemyConfig.enemy_bullet_speed)),
        )
        bg_raw = data.get("background", {})
        bc = BackgroundConfig(
            background_image=str(bg_raw.get("background_image", BackgroundConfig.background_image)),
            star_count=int(bg_raw.get("star_count", BackgroundConfig.star_count)),
            star_speed_min=float(bg_raw.get("star_speed_min", BackgroundConfig.star_speed_min)),
            star_speed_max=float(bg_raw.get("star_speed_max", BackgroundConfig.star_speed_max)),
        )
        pc_raw = data.get("particles", {})
        pc = ParticlesConfig(
            particle_count=int(pc_raw.get("particle_count", ParticlesConfig.particle_count)),
            particle_speed_min=float(pc_raw.get("particle_speed_min", ParticlesConfig.particle_speed_min)),
            particle_speed_max=float(pc_raw.get("particle_speed_max", ParticlesConfig.particle_speed_max)),
            particle_lifetime_min=float(pc_raw.get("particle_lifetime_min", ParticlesConfig.particle_lifetime_min)),
            particle_lifetime_max=float(pc_raw.get("particle_lifetime_max", ParticlesConfig.particle_lifetime_max)),
            particle_gravity=float(pc_raw.get("particle_gravity", ParticlesConfig.particle_gravity)),
            shockwave_duration=float(pc_raw.get("shockwave_duration", ParticlesConfig.shockwave_duration)),
            shockwave_max_scale=float(pc_raw.get("shockwave_max_scale", ParticlesConfig.shockwave_max_scale)),
        )
        ui_raw = data.get("ui", {})
        uc = UIConfig(
            popup_duration=float(ui_raw.get("popup_duration", UIConfig.popup_duration)),
            popup_rise_speed=float(ui_raw.get("popup_rise_speed", UIConfig.popup_rise_speed)),
        )
        return cls(
            starting_level=int(game.get("starting_level", cls.starting_level)),
            num_lives=int(game.get("num_lives", cls.num_lives)),
            spawn_safe_radius=int(game.get("spawn_safe_radius", cls.spawn_safe_radius)),
            debug=bool(game.get("debug", cls.debug)),
            max_window_height=int(game.get("max_window_height", 0)),
            ship=sc,
            enemies=ec,
            background=bc,
            particles=pc,
            ui=uc,
        )

    def save(self, path: Optional[Path] = None) -> None:
        """Persist current values back to *path* as TOML."""
        if path is None:
            path = _config_path()
        sc = self.ship
        lines = [
            "[game]\n",
            f"starting_level = {self.starting_level}\n",
            f"num_lives = {self.num_lives}\n",
            f"spawn_safe_radius = {self.spawn_safe_radius}\n",
            f"debug = {'true' if self.debug else 'false'}\n",
            f"max_window_height = {self.max_window_height}\n",
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
            f"enemy_cols_start = {ec.enemy_cols_start}\n",
            f"enemy_rows_start = {ec.enemy_rows_start}\n",
            f"enemy_cols_max = {ec.enemy_cols_max}\n",
            f"enemy_rows_max = {ec.enemy_rows_max}\n",
            f"enemy_cols_per_level = {ec.enemy_cols_per_level}\n",
            f"enemy_rows_per_level = {ec.enemy_rows_per_level}\n",
            f"enemy_col_width_factor = {ec.enemy_col_width_factor}\n",
            f"enemy_speed_initial = {ec.enemy_speed_initial}\n",
            f"enemy_speed_max_bonus = {ec.enemy_speed_max_bonus}\n",
            f"enemy_speed_level_pct = {ec.enemy_speed_level_pct}\n",
            f"enemy_side_margin = {ec.enemy_side_margin}\n",
            f"enemy_drop_distance = {ec.enemy_drop_distance}\n",
            f"enemy_fire_interval_min_l1 = {ec.enemy_fire_interval_min_l1}\n",
            f"enemy_fire_interval_max_l1 = {ec.enemy_fire_interval_max_l1}\n",
            f"enemy_fire_interval_scale = {ec.enemy_fire_interval_scale}\n",
            f"enemy_fire_interval_min_cap = {ec.enemy_fire_interval_min_cap}\n",
            f"enemy_fire_interval_max_cap = {ec.enemy_fire_interval_max_cap}\n",
            f"enemy_bullet_speed = {ec.enemy_bullet_speed}\n",
        ]
        uc = self.ui
        lines += [
            "\n[ui]\n",
            f"popup_duration = {uc.popup_duration}\n",
            f"popup_rise_speed = {uc.popup_rise_speed}\n",
        ]
        path.write_text("".join(lines), encoding="utf-8")
