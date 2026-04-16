"""PlayerShip — player-controlled sprite with movement, firing, and invincibility."""

from __future__ import annotations

import math
from typing import Optional

import arcade
from agf.paths import resource_path

from src.ship_config import ShipConfig
from src.sprites.explosion import ExplosionSprite
from src.sprites.player_bullet import PlayerBullet

_SHIP_PATHS: dict[int, str] = {
    1: "assets/images/PNG/playerShip1_blue.png",
    2: "assets/images/PNG/playerShip2_red.png",
}

_FLASH_INTERVAL = 0.1  # seconds between visibility toggles during invincibility


class PlayerShip(arcade.Sprite):
    """Player-controlled ship sprite.

    Pass *texture* to inject a pre-loaded texture (tests, no display needed).
    The ship does NOT read the keyboard directly — the view tracks held keys
    and passes them to apply_movement() each frame.
    """

    def __init__(
        self,
        player_num: int,
        config: ShipConfig,
        window_width: int,
        window_height: int,
        texture: Optional[arcade.Texture] = None,
        scale: float = 1.0,
    ) -> None:
        if texture is not None:
            super().__init__(texture)
        else:
            tex = arcade.load_texture(
                resource_path(_SHIP_PATHS.get(player_num, _SHIP_PATHS[1])),
                hit_box_algorithm=arcade.hitbox.algo_simple,
            )
            super().__init__(tex)
        self.scale = scale
        self._sprite_scale = scale

        self._player_num = player_num
        self._config = config
        self._window_width = window_width
        self._window_height = window_height

        # Movement zone: full width, bottom ship_zone_height_pct of screen.
        zone_height = window_height * config.ship_zone_height_pct
        self._zone_bottom: float = 0.0
        self._zone_top: float = zone_height
        self._zone_left: float = 0.0
        self._zone_right: float = float(window_width)

        # Spawn at horizontal centre, bottom of zone.
        self.center_x = window_width / 2.0
        self.center_y = zone_height / 2.0

        # Momentum
        self._vx: float = 0.0
        self._vy: float = 0.0

        # Tilt animation (degrees; negative = clockwise = lean right)
        self._tilt_angle: float = 0.0

        # Fire cooldown
        self._fire_cooldown_remaining: float = 0.0

        # Hit points
        self.hit_points: int = config.player_max_hp
        self.max_hit_points: int = config.player_max_hp

        # Invincibility
        self._invincible_remaining: float = 0.0
        self._flash_timer: float = 0.0
        self.start_invincibility()  # active from spawn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply_movement(self, keys_held: set[int], delta_time: float) -> None:
        """Update velocity with momentum, then move and clamp to zone."""
        cfg = self._config
        max_speed = cfg.ship_speed * 2.0
        accel = cfg.ship_accel * delta_time
        decel = cfg.ship_decel * delta_time

        moving_left = arcade.key.LEFT in keys_held or arcade.key.A in keys_held
        moving_right = arcade.key.RIGHT in keys_held or arcade.key.D in keys_held
        moving_up = arcade.key.UP in keys_held or arcade.key.W in keys_held
        moving_down = arcade.key.DOWN in keys_held or arcade.key.S in keys_held

        # --- horizontal ---
        if moving_left and not moving_right:
            self._vx = max(self._vx - accel, -max_speed)
        elif moving_right and not moving_left:
            self._vx = min(self._vx + accel, max_speed)
        else:
            # decelerate toward zero
            if self._vx > 0:
                self._vx = max(0.0, self._vx - decel)
            elif self._vx < 0:
                self._vx = min(0.0, self._vx + decel)

        # --- vertical ---
        if moving_down and not moving_up:
            self._vy = max(self._vy - accel, -max_speed)
        elif moving_up and not moving_down:
            self._vy = min(self._vy + accel, max_speed)
        else:
            if self._vy > 0:
                self._vy = max(0.0, self._vy - decel)
            elif self._vy < 0:
                self._vy = min(0.0, self._vy + decel)

        self.center_x += self._vx * delta_time
        self.center_y += self._vy * delta_time

        # Clamp to zone.
        half_w = self.width / 2.0
        half_h = self.height / 2.0
        self.center_x = max(self._zone_left + half_w, min(self._zone_right - half_w, self.center_x))
        self.center_y = max(self._zone_bottom + half_h, min(self._zone_top - half_h, self.center_y))

    def try_fire(self) -> Optional[PlayerBullet]:
        """Return a PlayerBullet fired at the ship's current tilt angle, or None."""
        if self._fire_cooldown_remaining > 0.0:
            return None
        self._fire_cooldown_remaining = self._config.fire_cooldown
        return PlayerBullet(
            x=self.center_x,
            y=self.center_y + self.height / 2.0,
            speed=self._config.bullet_speed,
            window_width=self._window_width,
            window_height=self._window_height,
            angle_deg=self._tilt_angle,
            player_num=self._player_num,
            scale=self._sprite_scale,
            damage=self._config.player_bullet_damage,
        )

    def take_damage(self, amount: int) -> bool:
        """Reduce HP by *amount*. Returns True if HP reaches zero (player dies)."""
        self.hit_points = max(0, self.hit_points - amount)
        return self.hit_points <= 0

    def start_invincibility(self) -> None:
        """Begin invincibility timer and flash effect."""
        self._invincible_remaining = self._config.spawn_invincible_duration
        self._flash_timer = 0.0
        self.visible = True

    @property
    def velocity(self) -> tuple[float, float]:
        """Current velocity for momentum transfer to destruction effects."""
        return (self._vx, self._vy)

    def is_invincible(self) -> bool:
        """True while invincibility frames are active."""
        return self._invincible_remaining > 0.0

    def kill(self, vx: float = 0.0, vy: float = 0.0) -> ExplosionSprite:  # type: ignore[override]
        """Remove ship and return an ExplosionSprite at this position."""
        explosion = ExplosionSprite(
            x=self.center_x,
            y=self.center_y,
            frame_duration=self._config.explosion_frame_duration,
            vx=vx,
            vy=vy,
            scale=self._sprite_scale,
        )
        self.remove_from_sprite_lists()
        return explosion

    def update(self, delta_time: float = 1 / 60) -> None:  # type: ignore[override]
        """Tick cooldown, invincibility timers, and tilt animation."""
        if self._fire_cooldown_remaining > 0.0:
            self._fire_cooldown_remaining = max(0.0, self._fire_cooldown_remaining - delta_time)

        if self._invincible_remaining > 0.0:
            self._invincible_remaining = max(0.0, self._invincible_remaining - delta_time)
            self._flash_timer += delta_time
            if self._flash_timer >= _FLASH_INTERVAL:
                self._flash_timer -= _FLASH_INTERVAL
                self.visible = not self.visible
            if self._invincible_remaining <= 0.0:
                self.visible = True

        self._update_tilt(delta_time)

    def _update_tilt(self, delta_time: float) -> None:
        """Step _tilt_angle toward the target derived from horizontal velocity."""
        max_speed = self._config.ship_speed * 2.0
        # Moving right → negative angle (clockwise lean); left → positive (CCW lean).
        target = (self._vx / max_speed) * 45.0 if max_speed > 0 else 0.0
        max_step = self._config.ship_tilt_rate * delta_time
        diff = target - self._tilt_angle
        if abs(diff) <= max_step:
            self._tilt_angle = target
        else:
            self._tilt_angle += math.copysign(max_step, diff)
        self.angle = self._tilt_angle
