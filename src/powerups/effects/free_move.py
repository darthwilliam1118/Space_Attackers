"""FreeMovementEffect — expands the ship movement zone to the full window."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agf.powerups.effect_categories import ConstraintEffect

if TYPE_CHECKING:
    from src.powerups.sa_powerup_config import SAPowerUpConfig


class FreeMovementEffect(ConstraintEffect):
    """Saves the ship's zone bounds and replaces them with the full window."""

    def __init__(self, config: "SAPowerUpConfig") -> None:
        super().__init__(duration=config.free_move_duration)

    @property
    def effect_type(self) -> str:
        return "free_move"

    @property
    def display_label(self) -> str:
        return "FREE MOVE"

    def apply_constraints(self, ship: Any, window_width: int, window_height: int) -> None:
        self._saved_constraints = {
            "_zone_top": ship._zone_top,
            "_zone_bottom": ship._zone_bottom,
            "_zone_left": ship._zone_left,
            "_zone_right": ship._zone_right,
        }
        ship._zone_top = float(window_height)
        ship._zone_bottom = 0.0
        ship._zone_left = 0.0
        ship._zone_right = float(window_width)
        ship.full_rotation = True

    def restore_constraints(self, ship: Any) -> None:
        for attr, val in self._saved_constraints.items():
            setattr(ship, attr, val)
        ship.full_rotation = False
        ship._tilt_angle = 0.0  # snap upright; normal tilt resumes from neutral
        # If ship is now outside the restored movement zone, grant spawn invincibility
        # so the player isn't immediately punished by enemies as they snap back in.
        if (
            ship.center_x < ship._zone_left
            or ship.center_x > ship._zone_right
            or ship.center_y < ship._zone_bottom
            or ship.center_y > ship._zone_top
        ):
            ship.start_invincibility()
