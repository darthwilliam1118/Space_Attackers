"""MeteorLevel — interstitial meteor storm level.

Meteors fall from the top of the window at random diagonal angles,
constrained to always reach the bottom. No enemy grid, no bullets.
Level ends when the spawn timer expires AND all meteors have exited
the bottom of the window or been destroyed.

Bullet hits are handled via apply_player_bullet() — RunLevelView drives
that loop and spawns explosions from the returned BulletHitResult.
Player-ship collisions are handled in update(); the killed meteor is
reported through consume_pending_hits() so RunLevelView can spawn an
explosion at the meteor's position before triggering the death sequence.
"""

from __future__ import annotations

import math
import random
from typing import Any, Callable, Optional

import arcade
from agf.events import GameEvent
from agf.levels.base_level import BaseLevel
from agf.paths import resource_path

from src.enemy_grid import BulletHitResult
from src.meteor_config import MeteorConfig
from src.sprites.meteor_sprite import MeteorSprite

# --------------------------------------------------------------------------- #
# Texture asset paths grouped by size tier                                    #
# --------------------------------------------------------------------------- #

_ASSET_ROOT = "assets/images/PNG/Meteors"

_TEXTURE_PATHS: dict[str, list[str]] = {
    "large": [
        f"{_ASSET_ROOT}/meteorBrown_big1.png",
        f"{_ASSET_ROOT}/meteorBrown_big2.png",
        f"{_ASSET_ROOT}/meteorBrown_big3.png",
        f"{_ASSET_ROOT}/meteorBrown_big4.png",
        f"{_ASSET_ROOT}/meteorGrey_big1.png",
        f"{_ASSET_ROOT}/meteorGrey_big2.png",
        f"{_ASSET_ROOT}/meteorGrey_big3.png",
        f"{_ASSET_ROOT}/meteorGrey_big4.png",
    ],
    "med": [
        f"{_ASSET_ROOT}/meteorBrown_med1.png",
        f"{_ASSET_ROOT}/meteorBrown_med3.png",
        f"{_ASSET_ROOT}/meteorGrey_med1.png",
        f"{_ASSET_ROOT}/meteorGrey_med2.png",
    ],
    "small": [
        f"{_ASSET_ROOT}/meteorBrown_small1.png",
        f"{_ASSET_ROOT}/meteorBrown_small2.png",
        f"{_ASSET_ROOT}/meteorGrey_small1.png",
        f"{_ASSET_ROOT}/meteorGrey_small2.png",
    ],
    "tiny": [
        f"{_ASSET_ROOT}/meteorBrown_tiny1.png",
        f"{_ASSET_ROOT}/meteorBrown_tiny2.png",
        f"{_ASSET_ROOT}/meteorGrey_tiny1.png",
        f"{_ASSET_ROOT}/meteorGrey_tiny2.png",
    ],
}

_SIZE_ORDER = ["large", "med", "small", "tiny"]


class MeteorLevel(BaseLevel):
    """Falling meteor storm — no enemy grid, no bullets, no level-number advance."""

    def __init__(
        self,
        config: MeteorConfig,
        window_width: int,
        window_height: int,
        powerup_manager: Any = None,
        _meteor_factory: Optional[Callable[..., MeteorSprite]] = None,
    ) -> None:
        self._config = config
        self._window_width = window_width
        self._window_height = window_height
        self._powerup_manager = powerup_manager
        self._meteor_factory = _meteor_factory

        self._meteor_list: arcade.SpriteList = arcade.SpriteList()
        self._empty_bullets: arcade.SpriteList = arcade.SpriteList()
        # Only populated by player-ship collisions (not bullet hits —
        # those are reported via BulletHitResult to RunLevelView directly).
        self._pending_hits: list[tuple[float, float, int]] = []

        self._textures: dict[str, list[arcade.Texture]] = {}
        self._textures_loaded: bool = False

        self._level_number: int = 1
        self._storm_timer: float = 0.0
        self._spawn_accumulator: float = 0.0

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def level_type(self) -> str:
        return "meteor"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def setup(self, level_number: int) -> None:
        self._level_number = level_number
        self._storm_timer = 0.0
        self._spawn_accumulator = 0.0
        self._meteor_list = arcade.SpriteList()
        self._pending_hits = []
        self._load_textures()
        if self._powerup_manager is not None:
            pu_level = max(1, level_number - 1)
            self._powerup_manager.setup(pu_level, "meteor")

    def _load_textures(self) -> None:
        if self._textures_loaded or self._meteor_factory is not None:
            return
        for size, paths in _TEXTURE_PATHS.items():
            self._textures[size] = [arcade.load_texture(resource_path(p)) for p in paths]
        self._textures_loaded = True

    # ------------------------------------------------------------------
    # Per-frame
    # ------------------------------------------------------------------

    def update(
        self,
        delta_time: float,
        player_ship: Any,
        player_bullets: Optional[arcade.SpriteList] = None,
        frame_count: int = 0,
    ) -> list[GameEvent]:
        events: list[GameEvent] = []

        # Power-ups
        if self._powerup_manager is not None:
            collected = self._powerup_manager.update(
                delta_time,
                player_ship,
                self._effect_context(),
                [],
            )
            for _ in collected:
                events.append(GameEvent.POWERUP_COLLECTED)

        # Advance storm clock and spawn new meteors
        if self._storm_timer < self._config.storm_duration:
            self._storm_timer += delta_time
            self._spawn_accumulator += delta_time
            interval = self._spawn_interval()
            while self._spawn_accumulator >= interval:
                self._spawn_meteor()
                self._spawn_accumulator -= interval

        # Update positions; remove meteors that exited the bottom
        for meteor in list(self._meteor_list):
            meteor.update(delta_time)
            if meteor.center_y < -100:
                meteor.remove_from_sprite_lists()

        # Player-ship vs meteor: destroy meteor, explosion at site.
        # Shield absorbs the collision; without shield the player is killed.
        if player_ship is not None:
            collisions = arcade.check_for_collision_with_list(player_ship, self._meteor_list)
            if collisions:
                meteor = collisions[0]
                self._pending_hits.append((meteor.center_x, meteor.center_y, 0))
                meteor.remove_from_sprite_lists()
                if player_ship.take_damage(player_ship.hit_points):
                    events.append(GameEvent.PLAYER_KILLED)

        return events

    def draw(self) -> None:
        self._meteor_list.draw()
        if self._powerup_manager is not None:
            self._powerup_manager.draw()

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def is_cleared(self) -> bool:
        return self._storm_timer >= self._config.storm_duration and len(self._meteor_list) == 0

    # ------------------------------------------------------------------
    # Bullet collision interface (called by RunLevelView's bullet loop)
    # ------------------------------------------------------------------

    def apply_player_bullet(self, bullet: Any) -> Optional[BulletHitResult]:
        hits = arcade.check_for_collision_with_list(bullet, self._meteor_list)
        if not hits:
            return None
        meteor = hits[0]
        cx, cy = meteor.center_x, meteor.center_y
        bullet_damage = getattr(bullet, "damage", 100)
        meteor.hit_points -= bullet_damage
        if meteor.hit_points <= 0:
            pts = self._points_for_meteor(meteor)
            meteor.remove_from_sprite_lists()
            return BulletHitResult(cx, cy, pts, killed=True)
        else:
            meteor.hp_bar_timer = self._config.hp_bar_duration
            return BulletHitResult(cx, cy, 0, killed=False)

    # ------------------------------------------------------------------
    # Hit reporting
    # ------------------------------------------------------------------

    def consume_pending_hits(self) -> list[tuple[float, float, int]]:
        result = list(self._pending_hits)
        self._pending_hits.clear()
        return result

    def consume_pending_non_lethal_hits(self) -> list[tuple[float, float]]:
        return []

    # ------------------------------------------------------------------
    # Sprite lists
    # ------------------------------------------------------------------

    def get_all_enemy_sprites(self) -> arcade.SpriteList:
        return self._meteor_list

    def get_enemy_bullet_sprite_list(self) -> arcade.SpriteList:
        return self._empty_bullets

    # ------------------------------------------------------------------
    # Power-ups
    # ------------------------------------------------------------------

    def get_powerup_manager(self) -> Any:
        return self._powerup_manager

    def get_enemy_x_positions(self) -> list[float]:
        return []

    # ------------------------------------------------------------------
    # Snapshot / restore
    # ------------------------------------------------------------------

    def to_snapshot(self) -> dict:
        return {"level_type": "meteor", "level_number": self._level_number}

    @classmethod
    def from_snapshot(
        cls,
        snapshot: dict,
        config: Any,
        window_width: int,
        window_height: int,
    ) -> "MeteorLevel":
        meteor_cfg = config.meteors if config is not None else MeteorConfig()
        scale = config.sprite_scale if config is not None else 1.0
        powerup_manager = None
        if config is not None and getattr(config, "powerups", None) is not None:
            from src.powerups.sa_manager import SAPowerUpManager

            powerup_manager = SAPowerUpManager(
                config.powerups, window_width, window_height, sprite_scale=scale
            )
        level = cls(meteor_cfg, window_width, window_height, powerup_manager)
        level.setup(snapshot.get("level_number", 1))
        return level

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _spawn_interval(self) -> float:
        last_regular = max(1, self._level_number - 1)
        rate = min(
            self._config.spawn_rate_base
            * (1.0 + self._config.spawn_rate_scale_pct * (last_regular - 1)),
            self._config.spawn_rate_max,
        )
        return 1.0 / rate

    def _safe_angle(self, spawn_x: float, spawn_y_dist: float) -> float:
        """Constrain fall angle so the meteor reaches the bottom within the window margins."""
        margin = 30.0
        w = float(self._window_width)
        a_min = math.degrees(math.atan((margin - spawn_x) / spawn_y_dist))
        a_max = math.degrees(math.atan((w - margin - spawn_x) / spawn_y_dist))
        a_min = max(a_min, -self._config.fall_angle_max)
        a_max = min(a_max, self._config.fall_angle_max)
        return random.uniform(a_min, a_max) if a_min < a_max else 0.0

    def _spawn_meteor(self) -> None:
        cfg = self._config
        size = random.choices(
            _SIZE_ORDER,
            weights=[cfg.prob_large, cfg.prob_med, cfg.prob_small, cfg.prob_tiny],
        )[0]
        hp_map = {
            "large": cfg.hp_large,
            "med": cfg.hp_med,
            "small": cfg.hp_small,
            "tiny": cfg.hp_tiny,
        }
        hp = hp_map[size]
        speed = random.uniform(cfg.fall_speed_min, cfg.fall_speed_max)
        spin = random.uniform(cfg.spin_rpm_min, cfg.spin_rpm_max) * random.choice((-1, 1))

        spawn_x = random.uniform(0.0, float(self._window_width))
        spawn_y = float(self._window_height) + cfg.spawn_height_offset
        angle = self._safe_angle(spawn_x, spawn_y)
        rad = math.radians(angle)
        vx = math.sin(rad) * speed
        vy = -math.cos(rad) * speed

        if self._meteor_factory is not None:
            meteor = self._meteor_factory(size=size, hit_points=hp, vx=vx, vy=vy, spin=spin)
        else:
            tex = random.choice(self._textures[size])
            meteor = MeteorSprite(tex, hit_points=hp, vx=vx, vy=vy, spin_deg_per_sec=spin)

        meteor.center_x = spawn_x
        meteor.center_y = spawn_y
        self._meteor_list.append(meteor)

    def _points_for_meteor(self, meteor: MeteorSprite) -> int:
        cfg = self._config
        hp = meteor.max_hit_points
        if hp >= cfg.hp_large:
            return cfg.points_large
        if hp >= cfg.hp_med:
            return cfg.points_med
        if hp >= cfg.hp_small:
            return cfg.points_small
        return cfg.points_tiny

    def _effect_context(self) -> dict:
        return {
            "window_width": self._window_width,
            "window_height": self._window_height,
            "sprite_scale": 1.0,
        }
