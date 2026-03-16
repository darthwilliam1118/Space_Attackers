"""RUN_LEVEL view — player ship, bullets, explosions, and debug shortcuts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import arcade

if TYPE_CHECKING:
    from src.state import GameStateManager

from src.sprites.player_ship import PlayerShip
from src.sprites.explosion import ExplosionSprite
from src.sprites.player_bullet import PlayerBullet


class RunLevelView(arcade.View):
    """Active gameplay screen.

    Instantiates the player ship, handles input, and drives sprite updates.
    Transitions to LEVEL_COMPLETE or PLAYER_KILLED via GameStateManager.

    Debug shortcuts (marked # DEBUG):
      Shift+W  — simulate win (LEVEL_COMPLETE)
      L        — simulate player killed (triggers explosion then PLAYER_KILLED)
    """

    def __init__(self, manager: "GameStateManager") -> None:
        super().__init__()
        self._manager = manager
        self._keys_held: set[int] = set()

        # Sprites — all rendered via SpriteLists (Arcade 3.x has no Sprite.draw())
        self._ship: Optional[PlayerShip] = None
        self._ship_list = arcade.SpriteList()
        self._bullets = arcade.SpriteList()
        self._explosions = arcade.SpriteList()

        # State
        self._dying: bool = False  # True while death explosion plays
        self._explosion: Optional[ExplosionSprite] = None

        self._setup()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup(self) -> None:
        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        cfg = self._manager.context.get("config")

        ship_cfg = cfg.ship if cfg else None
        from src.ship_config import ShipConfig
        if ship_cfg is None:
            ship_cfg = ShipConfig()

        player_num = players[idx].player_num if players else 1

        self._ship = PlayerShip(
            player_num=player_num,
            config=ship_cfg,
            window_width=self.window.width,
            window_height=self.window.height,
        )
        self._ship_list.append(self._ship)

    # ------------------------------------------------------------------
    # Arcade callbacks
    # ------------------------------------------------------------------

    def on_show_view(self) -> None:
        arcade.set_background_color(arcade.color.BLACK)

    def on_update(self, delta_time: float) -> None:
        from src.state import GameState

        # If death explosion is playing, wait for it to complete.
        if self._dying:
            if self._explosion is not None:
                self._explosion.update(delta_time)
                if self._explosion.is_complete:
                    self._manager.transition(GameState.PLAYER_KILLED)
            return

        if self._ship is None:
            return

        self._ship.apply_movement(self._keys_held, delta_time)
        self._ship.update(delta_time)

        for bullet in list(self._bullets):
            bullet.update(delta_time)  # type: ignore[arg-type]

        for explosion in list(self._explosions):
            explosion.update(delta_time)  # type: ignore[arg-type]

    def on_draw(self) -> None:
        self.clear()
        width = self.window.width
        height = self.window.height

        players = self._manager.context.get("players", [])
        idx = self._manager.context.get("active_player_index", 0)
        if players:
            p = players[idx]
            hud_label = f"Player {p.player_num}  Level {p.current_level}  Lives {p.lives}"
        else:
            hud_label = "Player 1  Level 1"

        arcade.draw_text(
            hud_label,
            width / 2,
            height - 20,
            arcade.color.WHITE,
            font_size=14,
            anchor_x="center",
            anchor_y="center",
        )

        # Debug hint
        arcade.draw_text(
            "Shift+W = Win    L = Die",
            width / 2,
            height - 38,
            arcade.color.DARK_GRAY,
            font_size=11,
            anchor_x="center",
            anchor_y="center",
        )

        self._ship_list.draw()
        self._bullets.draw()
        self._explosions.draw()

    def on_key_press(self, key: int, modifiers: int) -> None:
        from src.state import GameState

        # DEBUG: Shift+W = win, L = die
        if key == arcade.key.W and (modifiers & arcade.key.MOD_SHIFT):  # DEBUG
            self._manager.transition(GameState.LEVEL_COMPLETE)  # DEBUG
            return  # DEBUG

        if key == arcade.key.L:  # DEBUG
            self._trigger_death()  # DEBUG
            return  # DEBUG

        self._keys_held.add(key)

        if key == arcade.key.SPACE and not self._dying:
            self._fire()

    def on_key_release(self, key: int, modifiers: int) -> None:
        self._keys_held.discard(key)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fire(self) -> None:
        if self._ship is None:
            return
        bullet = self._ship.try_fire(self.window.height)
        if bullet is not None:
            self._bullets.append(bullet)

    def _trigger_death(self) -> None:
        """Begin death sequence: show explosion, then transition."""
        if self._dying or self._ship is None:
            return
        self._dying = True
        explosion = self._ship.kill()
        self._explosion = explosion
        self._explosions.append(explosion)
        self._ship = None
