"""Unit tests for BaseLevel, StandardLevel, and LevelFactory — no display required."""

from __future__ import annotations

from unittest.mock import MagicMock

import arcade
import pytest

from src.dive_controller import DiveController
from src.diving_config import DivingConfig
from src.enemy_config import EnemyConfig
from src.enemy_grid import EnemyGrid
from src.levels.level_factory import _create_fresh, _get_level_type, create_level
from src.levels.standard_level import StandardLevel

W, H = 800, 600


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _enemy_tex() -> arcade.Texture:
    return arcade.Texture.create_empty("enemy_t", (48, 32))


def _bullet_tex() -> arcade.Texture:
    return arcade.Texture.create_empty("bullet_t", (9, 54))


def _make_grid(cols: int = 3, rows: int = 2, level: int = 1) -> EnemyGrid:
    ec = EnemyConfig(
        enemy_cols_start=cols,
        enemy_cols_max=cols,
        enemy_rows_start=rows,
        enemy_rows_max=rows,
    )
    g = EnemyGrid(ec, W, H, enemy_texture=_enemy_tex(), bullet_texture=_bullet_tex())
    g.setup(level=level)
    return g


def _make_ctrl(level: int = 1, grid: EnemyGrid | None = None) -> DiveController:
    cfg = DivingConfig()
    ctrl = DiveController(cfg, W, H)
    ctrl.setup(level, enemy_grid=grid)
    return ctrl


def _make_standard(cols: int = 3, rows: int = 2, level: int = 1) -> StandardLevel:
    grid = _make_grid(cols=cols, rows=rows, level=level)
    ctrl = _make_ctrl(level=level, grid=grid)
    return StandardLevel(grid, ctrl)


# ---------------------------------------------------------------------------
# _get_level_type
# ---------------------------------------------------------------------------


class TestGetLevelType:
    # _get_level_type always returns "standard" — boss/meteor are inserted
    # between standard levels via pending_boss / pending_meteor_storm context
    # flags set in LevelCompleteView, not by routing on level number.
    def test_always_returns_standard(self) -> None:
        for n in [1, 2, 3, 4, 5, 6, 9, 10, 15, 20, 21, 25, 30]:
            assert _get_level_type(n) == "standard", f"level {n} should be standard"


# ---------------------------------------------------------------------------
# _create_fresh
# ---------------------------------------------------------------------------


class TestCreateFresh:
    def test_unknown_level_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown level type"):
            _create_fresh("unknown_xyz", 1, None, W, H)

    def test_boss_level_type_returns_boss_level(self) -> None:
        from src.levels.boss_level import BossLevel

        result = _create_fresh("boss", 5, None, W, H)
        assert isinstance(result, BossLevel)

    def test_standard_returns_standard_level(self) -> None:
        result = _create_fresh("standard", 1, None, W, H)
        assert isinstance(result, StandardLevel)

    def test_standard_level_not_cleared_after_setup(self) -> None:
        # A fresh standard level has enemies — not cleared
        result = _create_fresh("standard", 1, None, W, H)
        assert not result.is_cleared()


# ---------------------------------------------------------------------------
# create_level (factory entry point)
# ---------------------------------------------------------------------------


class TestCreateLevel:
    def test_no_snapshot_returns_standard_level(self) -> None:
        result = create_level(1, None, W, H)
        assert isinstance(result, StandardLevel)

    def test_no_snapshot_level_has_enemies(self) -> None:
        result = create_level(1, None, W, H)
        assert not result.is_cleared()

    def test_with_snapshot_calls_restore_path(self) -> None:
        # Build a snapshot from a fresh level
        fresh = _make_standard()
        snap = fresh.to_snapshot()
        # Restore from that snapshot
        restored = create_level(1, None, W, H, snapshot=snap)
        assert isinstance(restored, StandardLevel)

    def test_with_snapshot_level_type_key_present(self) -> None:
        fresh = _make_standard()
        snap = fresh.to_snapshot()
        assert snap["level_type"] == "standard"

    def test_unknown_snapshot_type_raises(self) -> None:
        snap = {"level_type": "unknown_xyz"}
        with pytest.raises(ValueError, match="Cannot restore unknown level type"):
            create_level(1, None, W, H, snapshot=snap)

    def test_boss_snapshot_returns_boss_level(self) -> None:
        from src.levels.boss_level import BossLevel

        snap = {"level_type": "boss", "boss": {"encounter": 1}}
        result = create_level(1, None, W, H, snapshot=snap)
        assert isinstance(result, BossLevel)


# ---------------------------------------------------------------------------
# StandardLevel.to_snapshot / from_snapshot
# ---------------------------------------------------------------------------


class TestStandardLevelSnapshot:
    def test_to_snapshot_includes_level_type(self) -> None:
        level = _make_standard()
        snap = level.to_snapshot()
        assert snap["level_type"] == "standard"

    def test_to_snapshot_includes_diving_key(self) -> None:
        level = _make_standard()
        snap = level.to_snapshot()
        assert "diving" in snap

    def test_from_snapshot_returns_standard_level(self) -> None:
        original = _make_standard()
        snap = original.to_snapshot()
        restored = StandardLevel.from_snapshot(snap, None, W, H)
        assert isinstance(restored, StandardLevel)

    def test_from_snapshot_level_type_standard(self) -> None:
        original = _make_standard()
        snap = original.to_snapshot()
        restored = StandardLevel.from_snapshot(snap, None, W, H)
        assert restored.level_type == "standard"


# ---------------------------------------------------------------------------
# StandardLevel.is_cleared
# ---------------------------------------------------------------------------


class TestStandardLevelIsCleared:
    def test_not_cleared_when_grid_has_enemies(self) -> None:
        level = _make_standard(cols=3, rows=2)
        assert not level.is_cleared()

    def test_cleared_when_grid_empty_and_no_airborne(self) -> None:
        # Mock both grid and dive controller
        grid = MagicMock()
        grid.is_cleared.return_value = True
        grid.velocity = (0.0, 0.0)
        grid.get_sprite_list.return_value = arcade.SpriteList()
        grid.get_bullet_sprite_list.return_value = arcade.SpriteList()

        dive = MagicMock()
        dive.has_any_airborne.return_value = False

        level = StandardLevel(grid, dive)
        assert level.is_cleared()

    def test_not_cleared_when_dives_airborne(self) -> None:
        grid = MagicMock()
        grid.is_cleared.return_value = True
        grid.velocity = (0.0, 0.0)

        dive = MagicMock()
        dive.has_any_airborne.return_value = True

        level = StandardLevel(grid, dive)
        assert not level.is_cleared()

    def test_not_cleared_when_grid_not_cleared(self) -> None:
        grid = MagicMock()
        grid.is_cleared.return_value = False

        dive = MagicMock()
        dive.has_any_airborne.return_value = False

        level = StandardLevel(grid, dive)
        assert not level.is_cleared()


# ---------------------------------------------------------------------------
# StandardLevel.has_any_airborne
# ---------------------------------------------------------------------------


class TestStandardLevelAirborne:
    def test_delegates_to_dive_controller(self) -> None:
        grid = MagicMock()
        dive = MagicMock()
        dive.has_any_airborne.return_value = True

        level = StandardLevel(grid, dive)
        assert level.has_any_airborne() is True
        dive.has_any_airborne.assert_called_once()

    def test_false_when_no_airborne(self) -> None:
        grid = MagicMock()
        dive = MagicMock()
        dive.has_any_airborne.return_value = False

        level = StandardLevel(grid, dive)
        assert level.has_any_airborne() is False


# ---------------------------------------------------------------------------
# StandardLevel.velocity
# ---------------------------------------------------------------------------


class TestStandardLevelVelocity:
    def test_returns_grid_velocity(self) -> None:
        grid = MagicMock()
        grid.velocity = (42.5, 0.0)

        dive = MagicMock()
        level = StandardLevel(grid, dive)
        assert level.velocity == (42.5, 0.0)


# ---------------------------------------------------------------------------
# StandardLevel.block_new_launches
# ---------------------------------------------------------------------------


class TestStandardLevelBlockLaunches:
    def test_sets_dive_controller_flag(self) -> None:
        grid = MagicMock()
        dive = MagicMock()
        dive.new_dive_launches_blocked = False

        level = StandardLevel(grid, dive)
        level.block_new_launches()

        assert dive.new_dive_launches_blocked is True


# ---------------------------------------------------------------------------
# StandardLevel.debug_force_dive
# ---------------------------------------------------------------------------


class TestStandardLevelDebugForceDive:
    def test_calls_launch_group_on_dive_ctrl(self) -> None:
        grid = MagicMock()
        dive = MagicMock()

        level = StandardLevel(grid, dive)
        level.debug_force_dive(400.0)

        dive.launch_group.assert_called_once_with(grid, 400.0)
