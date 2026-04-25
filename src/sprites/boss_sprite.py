"""BossSprite — single large enemy sprite for boss encounter levels."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional

import arcade
from agf.paths import resource_path

if TYPE_CHECKING:
    from src.boss_config import BossConfig
    from src.sprites.boss_bullet import BossBullet


class BossSprite(arcade.Sprite):
    """Large enemy sprite that moves side-to-side, firing bullets downward.

    Movement mirrors the standard EnemyGrid: horizontal travel that drops
    boss_drop_distance pixels on each wall bounce.  Boundary detection uses
    the sprite's actual scaled dimensions so margins are correct at any scale.

    Power-up compatibility attributes (ShieldEffect and BigGunEffect write
    these directly):
        shield_active, shield_hits_remaining — read by BossLevel damage logic
        bullet_scale_multiplier, bullet_damage_multiplier — read by _make_bullet
        _spread_chance_override — set by BossSpreadShotEffect to force spread bursts
    """

    def __init__(
        self,
        config: "BossConfig",
        encounter: int,
        window_width: int,
        window_height: int,
        scale: float = 1.0,
        texture: Optional[arcade.Texture] = None,
    ) -> None:
        if texture is not None:
            super().__init__(texture)
        else:
            super().__init__(arcade.load_texture(resource_path(config.boss_sprite)))

        boss_scale = config.boss_scale_base + config.boss_scale_per_boss * (encounter - 1)
        self.scale = boss_scale * scale
        self._sprite_scale = scale

        self._config = config
        self._encounter = encounter
        self._window_width = window_width
        self._window_height = window_height

        # HP
        self.hit_points: int = config.boss_hp_base + config.boss_hp_per_boss * (encounter - 1)
        self.max_hit_points: int = self.hit_points

        # Movement — start moving right, descending on each wall bounce
        speed = min(
            config.boss_speed_base + config.boss_speed_per_boss * (encounter - 1),
            config.boss_speed_max,
        )
        self._vx: float = speed
        self._vy: float = 0.0
        self._drop_direction: int = -1  # -1 = descending, +1 = ascending

        # Fire timer
        interval = max(
            config.boss_fire_interval_min,
            config.boss_fire_interval_base + config.boss_fire_interval_per_boss * (encounter - 1),
        )
        self._fire_timer: float = interval
        self._fire_interval: float = interval

        # Power-up state (written by effect classes)
        self.shield_active: bool = False
        self.shield_hits_remaining: int = 0
        self.bullet_scale_multiplier: float = 1.0
        self.bullet_damage_multiplier: int = 1
        self._spread_chance_override: Optional[float] = None

        # Pending bullets generated this frame
        self._pending_bullets: list["BossBullet"] = []

        # Pending hit reports consumed by BossLevel
        self._pending_hits: list[tuple[float, float, int]] = []
        self._pending_non_lethal: list[tuple[float, float]] = []

        # Points awarded on kill
        self._points: int = config.boss_points_base + config.boss_points_per_boss * (encounter - 1)

        # Spawn at top centre
        self.center_x = window_width / 2.0
        self.center_y = window_height - config.boss_side_margin - self.height / 2.0

    # ------------------------------------------------------------------
    # Per-frame
    # ------------------------------------------------------------------

    def update_boss(self, delta_time: float) -> None:
        """Move and tick fire timer. Called by BossLevel.update() each frame."""
        self._move(delta_time)
        self._tick_fire(delta_time)

    def _move(self, delta_time: float) -> None:
        cfg = self._config
        half_w = self.width / 2.0

        self.center_x += self._vx * delta_time

        left_limit = cfg.boss_side_margin + half_w
        right_limit = self._window_width - cfg.boss_side_margin - half_w

        if self._vx > 0 and self.center_x >= right_limit:
            self.center_x = right_limit
            self._vx = -self._vx
            self.center_y += cfg.boss_drop_distance * self._drop_direction
        elif self._vx < 0 and self.center_x <= left_limit:
            self.center_x = left_limit
            self._vx = -self._vx
            self.center_y += cfg.boss_drop_distance * self._drop_direction

    def _tick_fire(self, delta_time: float) -> None:
        self._fire_timer -= delta_time
        if self._fire_timer <= 0.0:
            self._fire_timer = self._fire_interval
            self._generate_bullets()

    def _generate_bullets(self) -> None:
        cfg = self._config
        spread_chance = (
            self._spread_chance_override
            if self._spread_chance_override is not None
            else cfg.boss_spread_chance
        )
        if random.random() < spread_chance:
            half_angle = cfg.boss_spread_angle / 2.0
            for _ in range(cfg.boss_spread_count):
                x_offset = random.uniform(-self.width / 2.0, self.width / 2.0)
                angle = random.uniform(-half_angle, half_angle)
                self._pending_bullets.append(
                    self._make_bullet(
                        self.center_x + x_offset, self.center_y - self.height / 2.0, angle
                    )
                )
        else:
            x_offset = random.uniform(-self.width / 2.0, self.width / 2.0)
            self._pending_bullets.append(
                self._make_bullet(self.center_x + x_offset, self.center_y - self.height / 2.0, 0.0)
            )

    def _make_bullet(self, x: float, y: float, angle_deg: float) -> "BossBullet":
        from src.sprites.boss_bullet import BossBullet

        damage = self._config.boss_bullet_damage * self.bullet_damage_multiplier
        return BossBullet(
            x=x,
            y=y,
            speed=self._config.boss_bullet_speed,
            angle_deg=angle_deg,
            scale=self._sprite_scale * self.bullet_scale_multiplier,
            damage=damage,
        )

    # ------------------------------------------------------------------
    # Damage / invincibility (SAPowerUpManager interface)
    # ------------------------------------------------------------------

    def take_damage(self, amount: int) -> bool:
        """Apply damage. Returns True if the boss is dead."""
        self.hit_points = max(0, self.hit_points - amount)
        return self.hit_points <= 0

    def is_invincible(self) -> bool:
        """Required by SAPowerUpManager interface — boss is never invincible."""
        return False

    # ------------------------------------------------------------------
    # Bullet / hit consumption
    # ------------------------------------------------------------------

    def consume_pending_bullets(self) -> list["BossBullet"]:
        bullets = list(self._pending_bullets)
        self._pending_bullets.clear()
        return bullets

    def consume_pending_hits(self) -> list[tuple[float, float, int]]:
        hits = list(self._pending_hits)
        self._pending_hits.clear()
        return hits

    def consume_pending_non_lethal_hits(self) -> list[tuple[float, float]]:
        hits = list(self._pending_non_lethal)
        self._pending_non_lethal.clear()
        return hits

    def record_hit(
        self, lethal: bool, hit_x: Optional[float] = None, hit_y: Optional[float] = None
    ) -> None:
        x = hit_x if hit_x is not None else self.center_x
        y = hit_y if hit_y is not None else self.center_y
        if lethal:
            self._pending_hits.append((self.center_x, self.center_y, self._points))
        else:
            self._pending_non_lethal.append((x, y))

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def points(self) -> int:
        return self._points

    def reaches_bottom(self, ship_zone_top: float) -> bool:
        """True if the boss bottom edge enters the player's movement zone."""
        return (self.center_y - self.height / 2.0) <= ship_zone_top

    def check_vertical_boundary(self, ship_zone_top: float) -> None:
        """Reverse vertical drop direction when the boss hits the bottom or top margin."""
        half_h = self.height / 2.0
        top_clamp = self._window_height - self._config.boss_side_margin - half_h
        if self._drop_direction < 0 and self.center_y - half_h <= ship_zone_top:
            self.center_y = ship_zone_top + half_h
            self._drop_direction = 1
        elif self._drop_direction > 0 and self.center_y >= top_clamp:
            self.center_y = top_clamp
            self._drop_direction = -1
