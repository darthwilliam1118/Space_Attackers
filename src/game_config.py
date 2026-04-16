"""GameConfig — loads and saves game_config.toml."""

from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Optional

from agf.background import BackgroundConfig

from src.diving_config import DivingConfig
from src.enemy_config import EnemyConfig
from src.particles_config import ParticlesConfig
from src.ship_config import ShipConfig
from src.ui_config import UIConfig


def _is_numeric(s: str) -> bool:
    """Return True if *s* looks like a number (handles negative values like -1)."""
    try:
        float(s)
        return True
    except ValueError:
        return False


_SUB_CONFIG_FIELDS = frozenset({"ship", "enemies", "background", "particles", "ui", "diving"})


def _apply_argv_overrides(cfg: "GameConfig") -> None:
    """Apply -key value overrides from sys.argv to *cfg* in place.

    Scans sys.argv for -key value pairs where key matches any field name in
    GameConfig or its nested sub-configs. Matching overrides are applied with
    correct type coercion. Unrecognised arguments print a warning and are skipped.
    The TOML file is never modified.
    """
    # Build flat registry: field_name -> (owner_obj, attr_name)
    registry: dict[str, tuple[object, str]] = {}

    for f in fields(cfg):
        if f.name not in _SUB_CONFIG_FIELDS:
            registry[f.name] = (cfg, f.name)

    for sub in (cfg.ship, cfg.enemies, cfg.background, cfg.particles, cfg.ui, cfg.diving):
        for f in fields(sub):
            existing = getattr(sub, f.name)
            if not isinstance(existing, dict):  # skip enemy_hp (dict[int, int])
                registry[f.name] = (sub, f.name)

    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        token = argv[i]
        if not token.startswith("-"):
            i += 1
            continue

        key = token.lstrip("-")
        if key not in registry:
            print(f"Unknown argument {token}, ignored")
            i += 1
            continue

        owner, attr = registry[key]
        existing = getattr(owner, attr)

        # Peek at the next token: is it a value or another flag?
        next_token = argv[i + 1] if i + 1 < len(argv) else None
        next_is_value = next_token is not None and (
            not next_token.startswith("-") or _is_numeric(next_token)
        )

        if isinstance(existing, bool) and not next_is_value:
            # Boolean flag with no explicit value: -debug alone means True
            setattr(owner, attr, True)
        elif next_is_value:
            assert next_token is not None
            i += 1
            try:
                if isinstance(existing, bool):
                    setattr(owner, attr, next_token.lower() not in ("false", "0", "no", "off"))
                elif isinstance(existing, int):
                    setattr(owner, attr, int(next_token))
                elif isinstance(existing, float):
                    setattr(owner, attr, float(next_token))
                else:
                    setattr(owner, attr, next_token)
            except ValueError:
                print(f"Invalid value for {token}: {next_token!r}, ignored")
        else:
            print(f"Missing value for {token}, ignored")

        i += 1


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
    music_volume: int = 80  # 0-100
    effects_volume: int = 80  # 0-100
    debug: bool = False
    god_mode: bool = False
    max_window_height: int = 1024  # height in px; width = height * 0.75 (4:3)
    sprite_scale: float = 1.0
    ship: ShipConfig = None  # type: ignore[assignment]
    enemies: EnemyConfig = None  # type: ignore[assignment]
    background: BackgroundConfig = None  # type: ignore[assignment]
    particles: ParticlesConfig = None  # type: ignore[assignment]
    ui: UIConfig = None  # type: ignore[assignment]
    diving: DivingConfig = None  # type: ignore[assignment]

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
        if self.diving is None:
            self.diving = DivingConfig()

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
            result = cls()
            _apply_argv_overrides(result)
            return result

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
            player_max_hp=int(ship.get("player_max_hp", ShipConfig.player_max_hp)),
            player_bullet_damage=int(
                ship.get("player_bullet_damage", ShipConfig.player_bullet_damage)
            ),
        )
        ec_raw = data.get("enemies", {})
        ec = EnemyConfig(
            enemy_cols_start=int(ec_raw.get("enemy_cols_start", EnemyConfig.enemy_cols_start)),
            enemy_rows_start=int(ec_raw.get("enemy_rows_start", EnemyConfig.enemy_rows_start)),
            enemy_cols_max=int(ec_raw.get("enemy_cols_max", EnemyConfig.enemy_cols_max)),
            enemy_rows_max=int(ec_raw.get("enemy_rows_max", EnemyConfig.enemy_rows_max)),
            enemy_cols_per_level=int(
                ec_raw.get("enemy_cols_per_level", EnemyConfig.enemy_cols_per_level)
            ),
            enemy_rows_per_level=int(
                ec_raw.get("enemy_rows_per_level", EnemyConfig.enemy_rows_per_level)
            ),
            enemy_col_width_factor=float(
                ec_raw.get("enemy_col_width_factor", EnemyConfig.enemy_col_width_factor)
            ),
            enemy_speed_initial=float(
                ec_raw.get("enemy_speed_initial", EnemyConfig.enemy_speed_initial)
            ),
            enemy_speed_max_bonus=float(
                ec_raw.get("enemy_speed_max_bonus", EnemyConfig.enemy_speed_max_bonus)
            ),
            enemy_speed_level_pct=float(
                ec_raw.get("enemy_speed_level_pct", EnemyConfig.enemy_speed_level_pct)
            ),
            enemy_side_margin=float(ec_raw.get("enemy_side_margin", EnemyConfig.enemy_side_margin)),
            enemy_drop_distance=float(
                ec_raw.get("enemy_drop_distance", EnemyConfig.enemy_drop_distance)
            ),
            enemy_bottom_margin=float(
                ec_raw.get("enemy_bottom_margin", EnemyConfig.enemy_bottom_margin)
            ),
            enemy_fire_interval_min_l1=float(
                ec_raw.get("enemy_fire_interval_min_l1", EnemyConfig.enemy_fire_interval_min_l1)
            ),
            enemy_fire_interval_max_l1=float(
                ec_raw.get("enemy_fire_interval_max_l1", EnemyConfig.enemy_fire_interval_max_l1)
            ),
            enemy_fire_interval_scale=float(
                ec_raw.get("enemy_fire_interval_scale", EnemyConfig.enemy_fire_interval_scale)
            ),
            enemy_fire_interval_min_cap=float(
                ec_raw.get("enemy_fire_interval_min_cap", EnemyConfig.enemy_fire_interval_min_cap)
            ),
            enemy_fire_interval_max_cap=float(
                ec_raw.get("enemy_fire_interval_max_cap", EnemyConfig.enemy_fire_interval_max_cap)
            ),
            enemy_bullet_speed=float(
                ec_raw.get("enemy_bullet_speed", EnemyConfig.enemy_bullet_speed)
            ),
            enemy_bullet_damage=int(
                ec_raw.get("enemy_bullet_damage", EnemyConfig.enemy_bullet_damage)
            ),
            enemy_hp={
                1: int(ec_raw.get("enemy_hp_type_1", 100)),
                2: int(ec_raw.get("enemy_hp_type_2", 100)),
                3: int(ec_raw.get("enemy_hp_type_3", 150)),
                4: int(ec_raw.get("enemy_hp_type_4", 150)),
                5: int(ec_raw.get("enemy_hp_type_5", 200)),
            },
            enemy_hp_level_factor=float(
                ec_raw.get("enemy_hp_level_factor", EnemyConfig.enemy_hp_level_factor)
            ),
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
            particle_speed_min=float(
                pc_raw.get("particle_speed_min", ParticlesConfig.particle_speed_min)
            ),
            particle_speed_max=float(
                pc_raw.get("particle_speed_max", ParticlesConfig.particle_speed_max)
            ),
            particle_lifetime_min=float(
                pc_raw.get("particle_lifetime_min", ParticlesConfig.particle_lifetime_min)
            ),
            particle_lifetime_max=float(
                pc_raw.get("particle_lifetime_max", ParticlesConfig.particle_lifetime_max)
            ),
            particle_gravity=float(
                pc_raw.get("particle_gravity", ParticlesConfig.particle_gravity)
            ),
            shockwave_duration=float(
                pc_raw.get("shockwave_duration", ParticlesConfig.shockwave_duration)
            ),
            shockwave_max_scale=float(
                pc_raw.get("shockwave_max_scale", ParticlesConfig.shockwave_max_scale)
            ),
        )
        ui_raw = data.get("ui", {})
        uc = UIConfig(
            popup_duration=float(ui_raw.get("popup_duration", UIConfig.popup_duration)),
            popup_rise_speed=float(ui_raw.get("popup_rise_speed", UIConfig.popup_rise_speed)),
            hp_bar_duration=float(ui_raw.get("hp_bar_duration", UIConfig.hp_bar_duration)),
            hp_bar_height=int(ui_raw.get("hp_bar_height", UIConfig.hp_bar_height)),
            hp_bar_y_offset=int(ui_raw.get("hp_bar_y_offset", UIConfig.hp_bar_y_offset)),
        )
        dc_raw = data.get("diving", {})
        dc = DivingConfig(
            dive_group_size_max=int(
                dc_raw.get("dive_group_size_max", DivingConfig.dive_group_size_max)
            ),
            dive_interval_base=float(
                dc_raw.get("dive_interval_base", DivingConfig.dive_interval_base)
            ),
            dive_interval_step=float(
                dc_raw.get("dive_interval_step", DivingConfig.dive_interval_step)
            ),
            dive_interval_min=float(
                dc_raw.get("dive_interval_min", DivingConfig.dive_interval_min)
            ),
            dive_speed_base=float(dc_raw.get("dive_speed_base", DivingConfig.dive_speed_base)),
            dive_speed_step=float(dc_raw.get("dive_speed_step", DivingConfig.dive_speed_step)),
            dive_speed_max=float(dc_raw.get("dive_speed_max", DivingConfig.dive_speed_max)),
            dive_bomb_speed=float(dc_raw.get("dive_bomb_speed", DivingConfig.dive_bomb_speed)),
            dive_bonus_points=int(dc_raw.get("dive_bonus_points", DivingConfig.dive_bonus_points)),
            dive_return_speed=float(
                dc_raw.get("dive_return_speed", DivingConfig.dive_return_speed)
            ),
        )
        result = cls(
            starting_level=int(game.get("starting_level", cls.starting_level)),
            num_lives=int(game.get("num_lives", cls.num_lives)),
            spawn_safe_radius=int(game.get("spawn_safe_radius", cls.spawn_safe_radius)),
            music_volume=int(game.get("music_volume", cls.music_volume)),
            effects_volume=int(game.get("effects_volume", cls.effects_volume)),
            debug=bool(game.get("debug", cls.debug)),
            god_mode=bool(game.get("god_mode", cls.god_mode)),
            max_window_height=int(game.get("max_window_height", 0)),
            sprite_scale=float(game.get("sprite_scale", cls.sprite_scale)),
            ship=sc,
            enemies=ec,
            background=bc,
            particles=pc,
            ui=uc,
            diving=dc,
        )
        _apply_argv_overrides(result)
        return result

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
            f"music_volume = {self.music_volume}\n",
            f"effects_volume = {self.effects_volume}\n",
            f"debug = {'true' if self.debug else 'false'}\n",
            f"god_mode = {'true' if self.god_mode else 'false'}\n",
            f"max_window_height = {self.max_window_height}\n",
            f"sprite_scale = {self.sprite_scale}\n",
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
            f"player_max_hp = {sc.player_max_hp}\n",
            f"player_bullet_damage = {sc.player_bullet_damage}\n",
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
            f"enemy_bullet_damage = {ec.enemy_bullet_damage}\n",
            f"enemy_hp_type_1 = {ec.enemy_hp.get(1, 100)}\n",
            f"enemy_hp_type_2 = {ec.enemy_hp.get(2, 100)}\n",
            f"enemy_hp_type_3 = {ec.enemy_hp.get(3, 150)}\n",
            f"enemy_hp_type_4 = {ec.enemy_hp.get(4, 150)}\n",
            f"enemy_hp_type_5 = {ec.enemy_hp.get(5, 200)}\n",
            f"enemy_hp_level_factor = {ec.enemy_hp_level_factor}\n",
        ]
        uc = self.ui
        lines += [
            "\n[ui]\n",
            f"popup_duration = {uc.popup_duration}\n",
            f"popup_rise_speed = {uc.popup_rise_speed}\n",
            f"hp_bar_duration = {uc.hp_bar_duration}\n",
            f"hp_bar_height = {uc.hp_bar_height}\n",
            f"hp_bar_y_offset = {uc.hp_bar_y_offset}\n",
        ]
        dv = self.diving
        lines += [
            "\n[diving]\n",
            f"dive_group_size_max = {dv.dive_group_size_max}\n",
            f"dive_interval_base = {dv.dive_interval_base}\n",
            f"dive_interval_step = {dv.dive_interval_step}\n",
            f"dive_interval_min = {dv.dive_interval_min}\n",
            f"dive_speed_base = {dv.dive_speed_base}\n",
            f"dive_speed_step = {dv.dive_speed_step}\n",
            f"dive_speed_max = {dv.dive_speed_max}\n",
            f"dive_bomb_speed = {dv.dive_bomb_speed}\n",
            f"dive_bonus_points = {dv.dive_bonus_points}\n",
            f"dive_return_speed = {dv.dive_return_speed}\n",
        ]
        path.write_text("".join(lines), encoding="utf-8")
