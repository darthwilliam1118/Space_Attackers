"""PlayerShip — player-controlled sprite with movement, firing, and invincibility."""

from __future__ import annotations

from typing import Optional

import arcade

from src.paths import resource_path
from src.ship_config import ShipConfig
from src.sprites.explosion import ExplosionSprite
from src.sprites.player_bullet import PlayerBullet, bullet_path_for

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
    ) -> None:
        if texture is not None:
            super().__init__(texture)
        else:
            super().__init__(resource_path(_SHIP_PATHS.get(player_num, _SHIP_PATHS[1])))

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

        # Fire cooldown
        self._fire_cooldown_remaining: float = 0.0

        # Invincibility
        self._invincible_remaining: float = 0.0
        self._flash_timer: float = 0.0
        self.start_invincibility()  # active from spawn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply_movement(self, keys_held: set[int], delta_time: float) -> None:
        """Move ship based on *keys_held*, clamped to the movement zone."""
        speed = self._config.ship_speed * delta_time
        if arcade.key.LEFT in keys_held or arcade.key.A in keys_held:
            self.center_x -= speed
        if arcade.key.RIGHT in keys_held or arcade.key.D in keys_held:
            self.center_x += speed
        if arcade.key.UP in keys_held or arcade.key.W in keys_held:
            self.center_y += speed
        if arcade.key.DOWN in keys_held or arcade.key.S in keys_held:
            self.center_y -= speed

        # Clamp to zone.
        half_w = self.width / 2.0
        half_h = self.height / 2.0
        self.center_x = max(self._zone_left + half_w, min(self._zone_right - half_w, self.center_x))
        self.center_y = max(self._zone_bottom + half_h, min(self._zone_top - half_h, self.center_y))

    def try_fire(self, window_height: int) -> Optional[PlayerBullet]:
        """Return a PlayerBullet if the cooldown has expired, else None."""
        if self._fire_cooldown_remaining > 0.0:
            return None
        self._fire_cooldown_remaining = self._config.fire_cooldown
        return PlayerBullet(
            x=self.center_x,
            y=self.center_y + self.height / 2.0,
            speed=self._config.bullet_speed,
            window_height=window_height,
            player_num=self._player_num,
        )

    def start_invincibility(self) -> None:
        """Begin invincibility timer and flash effect."""
        self._invincible_remaining = self._config.spawn_invincible_duration
        self._flash_timer = 0.0
        self.visible = True

    def is_invincible(self) -> bool:
        """True while invincibility frames are active."""
        return self._invincible_remaining > 0.0

    def kill(self) -> ExplosionSprite:  # type: ignore[override]
        """Remove ship and return an ExplosionSprite at this position."""
        explosion = ExplosionSprite(
            x=self.center_x,
            y=self.center_y,
            frame_duration=self._config.explosion_frame_duration,
        )
        self.remove_from_sprite_lists()
        return explosion

    def update(self, delta_time: float = 1 / 60) -> None:  # type: ignore[override]
        """Tick cooldown and invincibility timers."""
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
