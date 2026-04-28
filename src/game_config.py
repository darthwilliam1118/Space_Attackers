"""GameConfig - loads and saves game_config.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from agf.background import BackgroundConfig
from agf.config import BaseGameConfig, apply_argv_overrides, config_path

from src.boss_config import BossConfig
from src.diving_config import DivingConfig
from src.enemy_config import EnemyConfig
from src.meteor_config import MeteorConfig
from src.particles_config import ParticlesConfig
from src.powerups.sa_powerup_config import SAPowerUpConfig
from src.ship_config import ShipConfig
from src.ui_config import UIConfig

# Re-exported so existing tests importing ``_apply_argv_overrides`` keep working.
_apply_argv_overrides = apply_argv_overrides


def _config_path() -> Path:
    """Return the path to game_config.toml for Space Attackers."""
    return config_path(Path(__file__).parent.parent)


@dataclass
class GameConfig(BaseGameConfig):
    spawn_safe_radius: int = 80
    force_level_type: str = ""
    debug_show_collision_timing: bool = False
    ship: ShipConfig = field(default_factory=ShipConfig)
    enemies: EnemyConfig = field(default_factory=EnemyConfig)
    background: BackgroundConfig = field(default_factory=BackgroundConfig)
    particles: ParticlesConfig = field(default_factory=ParticlesConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    diving: DivingConfig = field(default_factory=DivingConfig)
    powerups: SAPowerUpConfig = field(default_factory=SAPowerUpConfig)
    meteors: MeteorConfig = field(default_factory=MeteorConfig)
    boss: BossConfig = field(default_factory=BossConfig)

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
            apply_argv_overrides(result)
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
        pu_raw = data.get("powerups", {})
        pu = SAPowerUpConfig(
            spawn_interval_base=float(
                pu_raw.get("spawn_interval_base", SAPowerUpConfig.spawn_interval_base)
            ),
            spawn_interval_min=float(
                pu_raw.get("spawn_interval_min", SAPowerUpConfig.spawn_interval_min)
            ),
            spawn_interval_jitter=float(
                pu_raw.get("spawn_interval_jitter", SAPowerUpConfig.spawn_interval_jitter)
            ),
            spawn_interval_decay=float(
                pu_raw.get("spawn_interval_decay", SAPowerUpConfig.spawn_interval_decay)
            ),
            powerups_scale=float(pu_raw.get("powerups_scale", SAPowerUpConfig.powerups_scale)),
            fall_speed_min=float(pu_raw.get("fall_speed_min", SAPowerUpConfig.fall_speed_min)),
            fall_speed_max=float(pu_raw.get("fall_speed_max", SAPowerUpConfig.fall_speed_max)),
            fall_angle_max=float(pu_raw.get("fall_angle_max", SAPowerUpConfig.fall_angle_max)),
            spin_rpm=float(pu_raw.get("spin_rpm", SAPowerUpConfig.spin_rpm)),
            spawn_height_offset=float(
                pu_raw.get("spawn_height_offset", SAPowerUpConfig.spawn_height_offset)
            ),
            meteor_spawn_interval_factor=float(
                pu_raw.get(
                    "meteor_spawn_interval_factor", SAPowerUpConfig.meteor_spawn_interval_factor
                )
            ),
            shield_duration=float(pu_raw.get("shield_duration", SAPowerUpConfig.shield_duration)),
            shield_hits=int(pu_raw.get("shield_hits", SAPowerUpConfig.shield_hits)),
            health_restore_amount=int(
                pu_raw.get("health_restore_amount", SAPowerUpConfig.health_restore_amount)
            ),
            rapid_fire_duration=float(
                pu_raw.get("rapid_fire_duration", SAPowerUpConfig.rapid_fire_duration)
            ),
            rapid_fire_multiplier=float(
                pu_raw.get("rapid_fire_multiplier", SAPowerUpConfig.rapid_fire_multiplier)
            ),
            big_gun_duration=float(
                pu_raw.get("big_gun_duration", SAPowerUpConfig.big_gun_duration)
            ),
            big_gun_damage_multiplier=float(
                pu_raw.get("big_gun_damage_multiplier", SAPowerUpConfig.big_gun_damage_multiplier)
            ),
            big_gun_scale_multiplier=float(
                pu_raw.get("big_gun_scale_multiplier", SAPowerUpConfig.big_gun_scale_multiplier)
            ),
            speed_boost_duration=float(
                pu_raw.get("speed_boost_duration", SAPowerUpConfig.speed_boost_duration)
            ),
            speed_boost_multiplier=float(
                pu_raw.get("speed_boost_multiplier", SAPowerUpConfig.speed_boost_multiplier)
            ),
            triple_shot_duration=float(
                pu_raw.get("triple_shot_duration", SAPowerUpConfig.triple_shot_duration)
            ),
            spread_shot_duration=float(
                pu_raw.get("spread_shot_duration", SAPowerUpConfig.spread_shot_duration)
            ),
            spread_shot_angle=float(
                pu_raw.get("spread_shot_angle", SAPowerUpConfig.spread_shot_angle)
            ),
            free_move_duration=float(
                pu_raw.get("free_move_duration", SAPowerUpConfig.free_move_duration)
            ),
            weight_health=float(pu_raw.get("weight_health", SAPowerUpConfig.weight_health)),
            weight_shield=float(pu_raw.get("weight_shield", SAPowerUpConfig.weight_shield)),
            weight_rapid_fire=float(
                pu_raw.get("weight_rapid_fire", SAPowerUpConfig.weight_rapid_fire)
            ),
            weight_big_gun=float(pu_raw.get("weight_big_gun", SAPowerUpConfig.weight_big_gun)),
            weight_speed_boost=float(
                pu_raw.get("weight_speed_boost", SAPowerUpConfig.weight_speed_boost)
            ),
            weight_triple_shot=float(
                pu_raw.get("weight_triple_shot", SAPowerUpConfig.weight_triple_shot)
            ),
            weight_spread_shot=float(
                pu_raw.get("weight_spread_shot", SAPowerUpConfig.weight_spread_shot)
            ),
            weight_free_move=float(
                pu_raw.get("weight_free_move", SAPowerUpConfig.weight_free_move)
            ),
        )
        me_raw = data.get("meteors", {})
        mc = MeteorConfig(
            storm_duration=float(me_raw.get("storm_duration", MeteorConfig.storm_duration)),
            spawn_rate_base=float(me_raw.get("spawn_rate_base", MeteorConfig.spawn_rate_base)),
            spawn_rate_scale_pct=float(
                me_raw.get("spawn_rate_scale_pct", MeteorConfig.spawn_rate_scale_pct)
            ),
            spawn_rate_max=float(me_raw.get("spawn_rate_max", MeteorConfig.spawn_rate_max)),
            fall_speed_min=float(me_raw.get("fall_speed_min", MeteorConfig.fall_speed_min)),
            fall_speed_max=float(me_raw.get("fall_speed_max", MeteorConfig.fall_speed_max)),
            fall_angle_max=float(me_raw.get("fall_angle_max", MeteorConfig.fall_angle_max)),
            spin_rpm_min=float(me_raw.get("spin_rpm_min", MeteorConfig.spin_rpm_min)),
            spin_rpm_max=float(me_raw.get("spin_rpm_max", MeteorConfig.spin_rpm_max)),
            spawn_height_offset=float(
                me_raw.get("spawn_height_offset", MeteorConfig.spawn_height_offset)
            ),
            hp_bar_duration=float(me_raw.get("hp_bar_duration", MeteorConfig.hp_bar_duration)),
            prob_large=float(me_raw.get("prob_large", MeteorConfig.prob_large)),
            prob_med=float(me_raw.get("prob_med", MeteorConfig.prob_med)),
            prob_small=float(me_raw.get("prob_small", MeteorConfig.prob_small)),
            prob_tiny=float(me_raw.get("prob_tiny", MeteorConfig.prob_tiny)),
            hp_large=int(me_raw.get("hp_large", MeteorConfig.hp_large)),
            hp_med=int(me_raw.get("hp_med", MeteorConfig.hp_med)),
            hp_small=int(me_raw.get("hp_small", MeteorConfig.hp_small)),
            hp_tiny=int(me_raw.get("hp_tiny", MeteorConfig.hp_tiny)),
            points_large=int(me_raw.get("points_large", MeteorConfig.points_large)),
            points_med=int(me_raw.get("points_med", MeteorConfig.points_med)),
            points_small=int(me_raw.get("points_small", MeteorConfig.points_small)),
            points_tiny=int(me_raw.get("points_tiny", MeteorConfig.points_tiny)),
        )
        bo_raw = data.get("boss", {})
        bo = BossConfig(
            boss_sprite=str(bo_raw.get("boss_sprite", BossConfig.boss_sprite)),
            boss_scale_base=float(bo_raw.get("boss_scale_base", BossConfig.boss_scale_base)),
            boss_scale_per_boss=float(
                bo_raw.get("boss_scale_per_boss", BossConfig.boss_scale_per_boss)
            ),
            boss_hp_base=int(bo_raw.get("boss_hp_base", BossConfig.boss_hp_base)),
            boss_hp_per_boss=int(bo_raw.get("boss_hp_per_boss", BossConfig.boss_hp_per_boss)),
            boss_speed_base=float(bo_raw.get("boss_speed_base", BossConfig.boss_speed_base)),
            boss_speed_per_boss=float(
                bo_raw.get("boss_speed_per_boss", BossConfig.boss_speed_per_boss)
            ),
            boss_speed_max=float(bo_raw.get("boss_speed_max", BossConfig.boss_speed_max)),
            boss_side_margin=float(bo_raw.get("boss_side_margin", BossConfig.boss_side_margin)),
            boss_drop_distance=float(
                bo_raw.get("boss_drop_distance", BossConfig.boss_drop_distance)
            ),
            boss_fire_interval_base=float(
                bo_raw.get("boss_fire_interval_base", BossConfig.boss_fire_interval_base)
            ),
            boss_fire_interval_per_boss=float(
                bo_raw.get("boss_fire_interval_per_boss", BossConfig.boss_fire_interval_per_boss)
            ),
            boss_fire_interval_min=float(
                bo_raw.get("boss_fire_interval_min", BossConfig.boss_fire_interval_min)
            ),
            boss_bullet_speed=float(bo_raw.get("boss_bullet_speed", BossConfig.boss_bullet_speed)),
            boss_bullet_damage=int(bo_raw.get("boss_bullet_damage", BossConfig.boss_bullet_damage)),
            boss_spread_chance=float(
                bo_raw.get("boss_spread_chance", BossConfig.boss_spread_chance)
            ),
            boss_spread_count=int(bo_raw.get("boss_spread_count", BossConfig.boss_spread_count)),
            boss_spread_angle=float(bo_raw.get("boss_spread_angle", BossConfig.boss_spread_angle)),
            boss_points_base=int(bo_raw.get("boss_points_base", BossConfig.boss_points_base)),
            boss_points_per_boss=int(
                bo_raw.get("boss_points_per_boss", BossConfig.boss_points_per_boss)
            ),
            boss_death_duration=float(
                bo_raw.get("boss_death_duration", BossConfig.boss_death_duration)
            ),
            boss_death_explosion_count=int(
                bo_raw.get("boss_death_explosion_count", BossConfig.boss_death_explosion_count)
            ),
            boss_death_particle_count=int(
                bo_raw.get("boss_death_particle_count", BossConfig.boss_death_particle_count)
            ),
            boss_dive_group_size_max=int(
                bo_raw.get("boss_dive_group_size_max", BossConfig.boss_dive_group_size_max)
            ),
            boss_dive_interval_base=float(
                bo_raw.get("boss_dive_interval_base", BossConfig.boss_dive_interval_base)
            ),
            boss_dive_interval_min=float(
                bo_raw.get("boss_dive_interval_min", BossConfig.boss_dive_interval_min)
            ),
            boss_diver_loop_count=int(
                bo_raw.get("boss_diver_loop_count", BossConfig.boss_diver_loop_count)
            ),
            boss_pu_weight_shield=float(
                bo_raw.get("boss_pu_weight_shield", BossConfig.boss_pu_weight_shield)
            ),
            boss_pu_weight_big_gun=float(
                bo_raw.get("boss_pu_weight_big_gun", BossConfig.boss_pu_weight_big_gun)
            ),
            boss_pu_weight_spread_shot=float(
                bo_raw.get("boss_pu_weight_spread_shot", BossConfig.boss_pu_weight_spread_shot)
            ),
        )
        result = cls(
            starting_level=int(game.get("starting_level", cls.starting_level)),
            num_lives=int(game.get("num_lives", cls.num_lives)),
            spawn_safe_radius=int(game.get("spawn_safe_radius", cls.spawn_safe_radius)),
            force_level_type=str(game.get("force_level_type", "")),
            music_volume=int(game.get("music_volume", cls.music_volume)),
            effects_volume=int(game.get("effects_volume", cls.effects_volume)),
            debug=bool(game.get("debug", cls.debug)),
            god_mode=bool(game.get("god_mode", cls.god_mode)),
            debug_show_collision_timing=bool(
                game.get("debug_show_collision_timing", cls.debug_show_collision_timing)
            ),
            max_window_height=int(game.get("max_window_height", 0)),
            sprite_scale=float(game.get("sprite_scale", cls.sprite_scale)),
            ship=sc,
            enemies=ec,
            background=bc,
            particles=pc,
            ui=uc,
            diving=dc,
            powerups=pu,
            meteors=mc,
            boss=bo,
        )
        apply_argv_overrides(result)
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
            f"debug_show_collision_timing = "
            f"{'true' if self.debug_show_collision_timing else 'false'}\n",
            f"max_window_height = {self.max_window_height}\n",
            f"sprite_scale = {self.sprite_scale}\n",
            f'force_level_type = "{self.force_level_type}"\n',
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
        pu = self.powerups
        lines += [
            "\n[powerups]\n",
            f"spawn_interval_base = {pu.spawn_interval_base}\n",
            f"spawn_interval_min = {pu.spawn_interval_min}\n",
            f"spawn_interval_jitter = {pu.spawn_interval_jitter}\n",
            f"spawn_interval_decay = {pu.spawn_interval_decay}\n",
            f"meteor_spawn_interval_factor = {pu.meteor_spawn_interval_factor}\n",
            f"powerups_scale = {pu.powerups_scale}\n",
            f"fall_speed_min = {pu.fall_speed_min}\n",
            f"fall_speed_max = {pu.fall_speed_max}\n",
            f"fall_angle_max = {pu.fall_angle_max}\n",
            f"spin_rpm = {pu.spin_rpm}\n",
            f"spawn_height_offset = {pu.spawn_height_offset}\n",
            f"shield_duration = {pu.shield_duration}\n",
            f"shield_hits = {pu.shield_hits}\n",
            f"health_restore_amount = {pu.health_restore_amount}\n",
            f"rapid_fire_duration = {pu.rapid_fire_duration}\n",
            f"rapid_fire_multiplier = {pu.rapid_fire_multiplier}\n",
            f"big_gun_duration = {pu.big_gun_duration}\n",
            f"big_gun_damage_multiplier = {pu.big_gun_damage_multiplier}\n",
            f"big_gun_scale_multiplier = {pu.big_gun_scale_multiplier}\n",
            f"speed_boost_duration = {pu.speed_boost_duration}\n",
            f"speed_boost_multiplier = {pu.speed_boost_multiplier}\n",
            f"triple_shot_duration = {pu.triple_shot_duration}\n",
            f"spread_shot_duration = {pu.spread_shot_duration}\n",
            f"spread_shot_angle = {pu.spread_shot_angle}\n",
            f"free_move_duration = {pu.free_move_duration}\n",
            f"weight_health = {pu.weight_health}\n",
            f"weight_shield = {pu.weight_shield}\n",
            f"weight_rapid_fire = {pu.weight_rapid_fire}\n",
            f"weight_big_gun = {pu.weight_big_gun}\n",
            f"weight_speed_boost = {pu.weight_speed_boost}\n",
            f"weight_triple_shot = {pu.weight_triple_shot}\n",
            f"weight_spread_shot = {pu.weight_spread_shot}\n",
            f"weight_free_move = {pu.weight_free_move}\n",
        ]
        me = self.meteors
        lines += [
            "\n[meteors]\n",
            f"storm_duration = {me.storm_duration}\n",
            f"spawn_rate_base = {me.spawn_rate_base}\n",
            f"spawn_rate_scale_pct = {me.spawn_rate_scale_pct}\n",
            f"spawn_rate_max = {me.spawn_rate_max}\n",
            f"fall_speed_min = {me.fall_speed_min}\n",
            f"fall_speed_max = {me.fall_speed_max}\n",
            f"fall_angle_max = {me.fall_angle_max}\n",
            f"spin_rpm_min = {me.spin_rpm_min}\n",
            f"spin_rpm_max = {me.spin_rpm_max}\n",
            f"spawn_height_offset = {me.spawn_height_offset}\n",
            f"hp_bar_duration = {me.hp_bar_duration}\n",
            f"prob_large = {me.prob_large}\n",
            f"prob_med = {me.prob_med}\n",
            f"prob_small = {me.prob_small}\n",
            f"prob_tiny = {me.prob_tiny}\n",
            f"hp_large = {me.hp_large}\n",
            f"hp_med = {me.hp_med}\n",
            f"hp_small = {me.hp_small}\n",
            f"hp_tiny = {me.hp_tiny}\n",
            f"points_large = {me.points_large}\n",
            f"points_med = {me.points_med}\n",
            f"points_small = {me.points_small}\n",
            f"points_tiny = {me.points_tiny}\n",
        ]
        bo = self.boss
        lines += [
            "\n[boss]\n",
            f'boss_sprite = "{bo.boss_sprite}"\n',
            f"boss_scale_base = {bo.boss_scale_base}\n",
            f"boss_scale_per_boss = {bo.boss_scale_per_boss}\n",
            f"boss_hp_base = {bo.boss_hp_base}\n",
            f"boss_hp_per_boss = {bo.boss_hp_per_boss}\n",
            f"boss_speed_base = {bo.boss_speed_base}\n",
            f"boss_speed_per_boss = {bo.boss_speed_per_boss}\n",
            f"boss_speed_max = {bo.boss_speed_max}\n",
            f"boss_side_margin = {bo.boss_side_margin}\n",
            f"boss_drop_distance = {bo.boss_drop_distance}\n",
            f"boss_fire_interval_base = {bo.boss_fire_interval_base}\n",
            f"boss_fire_interval_per_boss = {bo.boss_fire_interval_per_boss}\n",
            f"boss_fire_interval_min = {bo.boss_fire_interval_min}\n",
            f"boss_bullet_speed = {bo.boss_bullet_speed}\n",
            f"boss_bullet_damage = {bo.boss_bullet_damage}\n",
            f"boss_spread_chance = {bo.boss_spread_chance}\n",
            f"boss_spread_count = {bo.boss_spread_count}\n",
            f"boss_spread_angle = {bo.boss_spread_angle}\n",
            f"boss_points_base = {bo.boss_points_base}\n",
            f"boss_points_per_boss = {bo.boss_points_per_boss}\n",
            f"boss_death_duration = {bo.boss_death_duration}\n",
            f"boss_death_explosion_count = {bo.boss_death_explosion_count}\n",
            f"boss_death_particle_count = {bo.boss_death_particle_count}\n",
            f"boss_dive_group_size_max = {bo.boss_dive_group_size_max}\n",
            f"boss_dive_interval_base = {bo.boss_dive_interval_base}\n",
            f"boss_dive_interval_min = {bo.boss_dive_interval_min}\n",
            f"boss_diver_loop_count = {bo.boss_diver_loop_count}\n",
            f"boss_pu_weight_shield = {bo.boss_pu_weight_shield}\n",
            f"boss_pu_weight_big_gun = {bo.boss_pu_weight_big_gun}\n",
            f"boss_pu_weight_spread_shot = {bo.boss_pu_weight_spread_shot}\n",
        ]
        path.write_text("".join(lines), encoding="utf-8")
