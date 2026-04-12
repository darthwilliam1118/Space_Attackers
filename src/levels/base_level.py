"""BaseLevel — abstract interface for all level types.

RunLevelView and GameStateManager interact with levels exclusively
through this interface. Concrete level classes implement the details.

No arcade imports at module level so tests importing BaseLevel do not
trigger arcade initialisation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

from src.game_event import GameEvent

if TYPE_CHECKING:
    import arcade


class BaseLevel(ABC):
    """Abstract interface for all level types."""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    def setup(self, level_number: int) -> None:
        """Initialise all entities for this level from scratch.
        Not called when restoring from snapshot."""

    # ------------------------------------------------------------------
    # Per-frame
    # ------------------------------------------------------------------

    @abstractmethod
    def update(
        self,
        delta_time: float,
        player_ship: Any,
        player_bullets: Optional[Any] = None,
    ) -> list[GameEvent]:
        """Update all level entities.

        player_ship is None during the death sequence and 2P wait.
        Implementations must handle None safely (no collision checks).

        player_bullets is the RunLevelView SpriteList of active player
        projectiles. StandardLevel passes this to DiveController so it
        can handle bullet vs diving-ship collision internally (as before).
        Pass None or omit to skip that collision check.

        Returns list of GameEvents that occurred this frame.
        """

    @abstractmethod
    def draw(self) -> None:
        """Draw all level entities.
        Called from RunLevelView.on_draw() between background and
        player ship layers."""

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    @abstractmethod
    def is_cleared(self) -> bool:
        """True when the win condition for this level type is met.

        StandardLevel: grid empty AND no airborne dive ships.
        BossLevel: boss destroyed.
        BonusLevel: timer expired or all targets collected.
        """

    @property
    @abstractmethod
    def level_type(self) -> str:
        """String identifier e.g. 'standard', 'boss', 'meteor', 'bonus'."""

    # ------------------------------------------------------------------
    # Bullet collision — called from RunLevelView bullet loop
    # ------------------------------------------------------------------

    @abstractmethod
    def apply_player_bullet(self, bullet: Any) -> Any:
        """Check bullet against all level enemies.
        Returns a hit result object if hit, None otherwise.
        Caller removes the bullet sprite on hit."""

    # ------------------------------------------------------------------
    # Hit reporting
    # ------------------------------------------------------------------

    @abstractmethod
    def consume_pending_hits(self) -> list[tuple[float, float, int]]:
        """Return and clear all lethal hits this frame.
        Each entry is (x, y, points). RunLevelView spawns explosions
        and score popups for each entry."""

    @abstractmethod
    def consume_pending_non_lethal_hits(self) -> list[tuple[float, float]]:
        """Return and clear all non-lethal hits (HP damage without kill).
        Each entry is (x, y). RunLevelView spawns a hit ring for each."""

    # ------------------------------------------------------------------
    # Sprite lists — for draw only
    # ------------------------------------------------------------------

    @abstractmethod
    def get_all_enemy_sprites(self) -> "arcade.SpriteList":
        """All active enemy sprites (grid + airborne) for draw and HP bars."""

    @abstractmethod
    def get_enemy_bullet_sprite_list(self) -> "arcade.SpriteList":
        """All active enemy projectiles for draw."""

    # ------------------------------------------------------------------
    # Snapshot / restore
    # ------------------------------------------------------------------

    @abstractmethod
    def to_snapshot(self) -> dict:
        """Serialise complete level state.
        Must include a 'level_type' key matching self.level_type."""

    @classmethod
    @abstractmethod
    def from_snapshot(
        cls,
        snapshot: dict,
        config: Any,
        window_width: int,
        window_height: int,
    ) -> "BaseLevel":
        """Restore a level from a snapshot dict."""

    # ------------------------------------------------------------------
    # 2P dive wait — optional overrides
    # ------------------------------------------------------------------

    def has_any_airborne(self) -> bool:
        """True if any entities are mid-animation that should complete
        before a 2P snapshot is taken. Default False."""
        return False

    def block_new_launches(self) -> None:
        """Prevent new enemy launches during 2P death wait.
        Default is a no-op."""

    # ------------------------------------------------------------------
    # Velocity — for explosion drift
    # ------------------------------------------------------------------

    @property
    def velocity(self) -> tuple[float, float]:
        """Current (vx, vy) of the primary enemy formation.
        Used to match explosion drift to enemy movement. Default (0, 0)."""
        return (0.0, 0.0)

    # ------------------------------------------------------------------
    # Optional debug hook
    # ------------------------------------------------------------------

    def debug_force_dive(self, player_x: float) -> None:
        """Force a dive group for debug purposes (Shift+D).
        No-op by default. StandardLevel overrides."""
