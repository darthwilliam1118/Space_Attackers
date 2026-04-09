"""Unit tests for DivingShip — no display required (mock textures)."""

from __future__ import annotations

import arcade
import pytest

from src.diving_config import DivingConfig
from src.sprites.diving_ship import DivingShip, DiveState
from src.sprites.enemy_sprite import EnemySprite

W, H = 800, 1000
_SPEED = 200.0  # default dive speed for tests
_CFG = DivingConfig()  # default config (dive_speed not used directly on DivingConfig)


def _tex(name: str = "t") -> arcade.Texture:
    return arcade.Texture.create_empty(name, (48, 32))


def _bullet_tex() -> arcade.Texture:
    return arcade.Texture.create_empty("bt", (9, 54))


def _source(col: int = 2, row: int = 1) -> EnemySprite:
    s = EnemySprite("Blue", 2, col, row, texture=_tex())
    s.center_x = 400.0
    s.center_y = 800.0
    s.home_x = 400.0
    s.home_y = 800.0
    return s


def _ship(
    source: EnemySprite | None = None,
    speed: float = _SPEED,
    delay: float = 0.0,
    bullet_tex: arcade.Texture | None = None,
    waypoints: list[tuple[float, float]] | None = None,
) -> DivingShip:
    if source is None:
        source = _source()
    if waypoints is None:
        waypoints = _simple_waypoints()
    return DivingShip(
        source_sprite=source,
        waypoints=waypoints,
        config=_CFG,
        window_height=H,
        dive_speed=speed,
        launch_delay=delay,
        bullet_texture=bullet_tex,
    )


def _simple_waypoints(n: int = 120) -> list[tuple[float, float]]:
    """Straight down and back up, crossing well below midscreen (0.55*H)."""
    mid = H * 0.4  # below threshold (0.55 * H = 550)
    halfway = n // 2
    waypoints = []
    for i in range(halfway):
        t = i / (halfway - 1)
        y = 800.0 - (800.0 - mid) * t
        waypoints.append((400.0, y))
    for i in range(n - halfway):
        t = i / (n - halfway - 1) if n - halfway > 1 else 1.0
        y = mid + (800.0 - mid) * t
        waypoints.append((400.0, y))
    return waypoints


class TestDivingShipInit:
    def test_correct_grid_position(self) -> None:
        s = _ship(source=_source(col=3, row=2))
        assert s.grid_position == (3, 2)

    def test_starts_at_source_position(self) -> None:
        s = _ship()
        assert s.center_x == pytest.approx(400.0)
        assert s.center_y == pytest.approx(800.0)

    def test_no_launch_delay_starts_diving(self) -> None:
        s = _ship(delay=0.0)
        assert s._state == DiveState.DIVING

    def test_launch_delay_starts_waiting(self) -> None:
        s = _ship(delay=0.3)
        assert s._state == DiveState.WAITING

    def test_is_done_false_initially(self) -> None:
        s = _ship()
        assert not s.is_done


class TestDivingShipLaunchDelay:
    def test_does_not_move_during_delay(self) -> None:
        s = _ship(delay=1.0)
        initial_y = s.center_y
        s.update(0.1, player_x=400.0)
        assert s.center_y == pytest.approx(initial_y)

    def test_starts_moving_after_delay_expires(self) -> None:
        s = _ship(delay=0.1)
        s.update(0.15, player_x=400.0)
        assert s._state == DiveState.DIVING


class TestDivingShipBombing:
    def test_fires_bomb_when_crossing_threshold(self) -> None:
        s = _ship(bullet_tex=_bullet_tex())
        bomb_fired = False
        for _ in range(200):
            s.update(1 / 60, player_x=400.0)
            b = s.get_bomb()
            if b is not None:
                bomb_fired = True
                break
        assert bomb_fired

    def test_fires_exactly_one_bomb_per_dive(self) -> None:
        s = _ship(bullet_tex=_bullet_tex())
        bombs: list = []
        for _ in range(400):
            s.update(1 / 60, player_x=400.0)
            b = s.get_bomb()
            if b is not None:
                bombs.append(b)
        assert len(bombs) == 1

    def test_no_bomb_fired_on_return_path(self) -> None:
        s = _ship(bullet_tex=_bullet_tex())
        # Drive to RETURNING state
        for _ in range(400):
            s.update(1 / 60, player_x=400.0)
            s.get_bomb()  # consume any bomb
            if s._state == DiveState.RETURNING:
                break

        # Return phase — no new bombs
        for _ in range(200):
            s.update(1 / 60, player_x=400.0)
            assert s.get_bomb() is None


class TestDivingShipReturning:
    def test_transitions_to_returning_after_path_complete(self) -> None:
        s = _ship()
        for _ in range(500):
            s.update(1 / 60, player_x=400.0)
            if s._state == DiveState.RETURNING:
                break
        assert s._state == DiveState.RETURNING

    def test_is_done_after_reaching_home(self) -> None:
        s = _ship()
        for _ in range(2000):
            s.update(1 / 60, player_x=400.0)
            if s.is_done:
                break
        assert s.is_done


class TestDivingShipRotation:
    def test_angle_nonzero_while_diving_on_diagonal_path(self) -> None:
        """Right-and-down movement should tilt the ship right (negative angle)."""
        source = _source()
        diagonal = [(400.0 + i * 5, 800.0 - i * 5) for i in range(120)]
        s = DivingShip(source, diagonal, _CFG, H, dive_speed=_SPEED)
        s.update(1 / 60, player_x=400.0)
        # Moving right → tilts right → Arcade CCW-positive means negative angle
        assert s.angle < 0.0

    def test_angle_zero_on_vertical_downward_path(self) -> None:
        """Straight downward movement → angle should be 0° (sprite already faces down)."""
        source = _source()
        vertical = [(400.0, 800.0 - i * 5) for i in range(120)]
        s = DivingShip(source, vertical, _CFG, H, dive_speed=_SPEED)
        s.update(1 / 60, player_x=400.0)
        assert s.angle == pytest.approx(0.0, abs=1.0)

    def test_angle_moves_toward_zero_during_returning(self) -> None:
        """During RETURNING, angle should decrease toward 0 each tick."""
        source = _source()
        s = DivingShip(source, _simple_waypoints(), _CFG, H, dive_speed=_SPEED)
        # Manually put ship in RETURNING state with a non-zero angle
        s._state = DiveState.RETURNING
        s.angle = 90.0
        s.update(1 / 60, player_x=400.0)
        assert abs(s.angle) < 90.0

    def test_angle_zero_on_done(self) -> None:
        """After completing the full arc, angle must be exactly 0."""
        s = _ship()
        for _ in range(2000):
            s.update(1 / 60, player_x=400.0)
            if s.is_done:
                break
        assert s.angle == pytest.approx(0.0)
