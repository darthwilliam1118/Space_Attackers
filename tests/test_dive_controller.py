"""Unit tests for DiveController — no display required (mock textures)."""

from __future__ import annotations

import arcade
import pytest

from src.dive_controller import DiveController
from src.diving_config import DivingConfig
from src.enemy_config import EnemyConfig
from src.enemy_grid import EnemyGrid
from src.game_event import GameEvent

W, H = 800, 1000


def _enemy_tex() -> arcade.Texture:
    return arcade.Texture.create_empty("enemy", (48, 32))


def _bullet_tex() -> arcade.Texture:
    return arcade.Texture.create_empty("bt", (9, 54))


def _cfg(**kwargs) -> DivingConfig:
    return DivingConfig(**kwargs)


def _grid(cols: int = 5, rows: int = 3, level: int = 2) -> EnemyGrid:
    ec = EnemyConfig(
        enemy_cols_start=cols,
        enemy_cols_max=cols,
        enemy_rows_start=rows,
        enemy_rows_max=rows,
    )
    g = EnemyGrid(ec, W, H, enemy_texture=_enemy_tex(), bullet_texture=_bullet_tex())
    g.setup(level=level)
    return g


def _ctrl(level: int = 2, **kwargs) -> tuple[DiveController, EnemyGrid]:
    cfg = _cfg(**kwargs)
    ctrl = DiveController(cfg, W, H)
    grid = _grid(level=level)
    ctrl.setup(level, enemy_grid=grid)
    return ctrl, grid


class TestLevelScaling:
    def test_level1_dive_group_size_zero(self) -> None:
        cfg = _cfg()
        ctrl = DiveController(cfg, W, H)
        ctrl.setup(1, enemy_grid=None)
        assert ctrl._dive_group_size == 0

    def test_level2_dive_group_size_one(self) -> None:
        cfg = _cfg()
        ctrl = DiveController(cfg, W, H)
        ctrl.setup(2, enemy_grid=None)
        assert ctrl._dive_group_size == 1

    def test_dive_group_size_capped_at_max(self) -> None:
        cfg = _cfg(dive_group_size_max=4)
        ctrl = DiveController(cfg, W, H)
        ctrl.setup(100, enemy_grid=None)
        assert ctrl._dive_group_size == 4

    def test_dive_interval_decreases_with_level(self) -> None:
        cfg = _cfg(dive_interval_base=12.0, dive_interval_step=1.0, dive_interval_min=4.0)
        ctrl2 = DiveController(cfg, W, H)
        ctrl2.setup(2, enemy_grid=None)
        ctrl6 = DiveController(cfg, W, H)
        ctrl6.setup(6, enemy_grid=None)
        assert ctrl6._dive_interval < ctrl2._dive_interval

    def test_dive_interval_floors_at_min(self) -> None:
        cfg = _cfg(dive_interval_base=12.0, dive_interval_step=1.0, dive_interval_min=4.0)
        ctrl = DiveController(cfg, W, H)
        ctrl.setup(100, enemy_grid=None)
        assert ctrl._dive_interval == pytest.approx(4.0)

    def test_dive_speed_increases_with_level(self) -> None:
        cfg = _cfg(dive_speed_base=200.0, dive_speed_step=15.0, dive_speed_max=380.0)
        ctrl2 = DiveController(cfg, W, H)
        ctrl2.setup(2, enemy_grid=None)
        ctrl5 = DiveController(cfg, W, H)
        ctrl5.setup(5, enemy_grid=None)
        assert ctrl5._dive_speed > ctrl2._dive_speed

    def test_dive_speed_capped_at_max(self) -> None:
        cfg = _cfg(dive_speed_base=200.0, dive_speed_step=15.0, dive_speed_max=380.0)
        ctrl = DiveController(cfg, W, H)
        ctrl.setup(100, enemy_grid=None)
        assert ctrl._dive_speed == pytest.approx(380.0)


class TestLaunchGroup:
    def test_selects_only_non_diving_alive_ships(self) -> None:
        ctrl, grid = _ctrl(level=2)
        initial_count = len(grid.get_sprite_list())
        ctrl.launch_group(grid, player_x=400.0)
        # One ship extracted from grid (level 2 = 1 per group)
        assert len(grid.get_sprite_list()) == initial_count - 1
        assert ctrl.active_count() == 1

    def test_handles_fewer_eligible_ships_than_group_size(self) -> None:
        # Only 1 enemy in grid, group_size > 1
        ec = EnemyConfig(enemy_cols_start=1, enemy_cols_max=1, enemy_rows_start=1, enemy_rows_max=1)
        grid = EnemyGrid(ec, W, H, enemy_texture=_enemy_tex(), bullet_texture=_bullet_tex())
        grid.setup(level=2)
        cfg = _cfg(dive_group_size_max=4)
        ctrl = DiveController(cfg, W, H)
        ctrl.setup(level=5, enemy_grid=grid)  # level 5 → group_size 4
        ctrl.launch_group(grid, player_x=400.0)
        # Should have launched at most 1 (only 1 available)
        assert ctrl.active_count() == 1

    def test_stagger_delay_second_ship_is_0_3s(self) -> None:
        ctrl, grid = _ctrl(level=3)  # level 3 → group_size 2
        ctrl.launch_group(grid, player_x=400.0)
        assert ctrl.active_count() == 2
        delays = [ship._launch_delay for ship in ctrl._active_ships]
        assert sorted(delays) == pytest.approx([0.0, 0.3])


class TestUpdateBehaviour:
    def test_no_launch_at_level1(self) -> None:
        cfg = _cfg()
        ctrl = DiveController(cfg, W, H)
        grid = _grid(level=1)
        ctrl.setup(1, enemy_grid=grid)
        # Tick past any interval
        ctrl.update(100.0, grid, None, arcade.SpriteList())
        assert ctrl.active_count() == 0

    def test_launches_after_interval(self) -> None:
        cfg = _cfg(dive_interval_base=1.0, dive_interval_step=0.0, dive_interval_min=1.0)
        ctrl = DiveController(cfg, W, H)
        grid = _grid(level=2)
        ctrl.setup(2, enemy_grid=grid)
        ctrl.update(1.1, grid, None, arcade.SpriteList())
        assert ctrl.active_count() == 1

    def test_no_launch_when_blocked(self) -> None:
        cfg = _cfg(dive_interval_base=1.0, dive_interval_step=0.0, dive_interval_min=1.0)
        ctrl = DiveController(cfg, W, H)
        grid = _grid(level=2)
        ctrl.setup(2, enemy_grid=grid)
        ctrl.new_dive_launches_blocked = True
        ctrl.update(5.0, grid, None, arcade.SpriteList())
        assert ctrl.active_count() == 0

    def test_has_any_airborne_false_when_empty(self) -> None:
        ctrl, _ = _ctrl(level=2)
        assert not ctrl.has_any_airborne()

    def test_has_any_airborne_true_after_launch(self) -> None:
        ctrl, grid = _ctrl(level=2)
        ctrl.launch_group(grid, player_x=400.0)
        assert ctrl.has_any_airborne()


class TestSnapshot:
    def test_snapshot_keys(self) -> None:
        ctrl, _ = _ctrl(level=3)
        snap = ctrl.to_snapshot()
        assert set(snap.keys()) == {"dive_timer", "level"}

    def test_snapshot_no_airborne_data(self) -> None:
        ctrl, grid = _ctrl(level=3)
        ctrl.launch_group(grid, player_x=400.0)
        # Even with airborne ships, snapshot only has timer+level
        snap = ctrl.to_snapshot()
        assert set(snap.keys()) == {"dive_timer", "level"}

    def test_from_snapshot_restores_dive_timer(self) -> None:
        cfg = _cfg()
        ctrl = DiveController(cfg, W, H)
        ctrl.setup(3, enemy_grid=None)
        ctrl._dive_timer = 7.5
        snap = ctrl.to_snapshot()
        restored = DiveController.from_snapshot(snap, cfg, W, H)
        assert restored._dive_timer == pytest.approx(7.5)

    def test_from_snapshot_restores_level(self) -> None:
        cfg = _cfg()
        ctrl = DiveController(cfg, W, H)
        ctrl.setup(5, enemy_grid=None)
        snap = ctrl.to_snapshot()
        restored = DiveController.from_snapshot(snap, cfg, W, H)
        assert restored._level == 5


class TestLevelCompleteGuard:
    def test_enemy_destroyed_event_returned_on_bullet_hit(self) -> None:
        ctrl, grid = _ctrl(level=2)
        ctrl.launch_group(grid, player_x=400.0)
        assert ctrl.active_count() == 1

        ship = ctrl._active_ships[0]
        # Place a bullet directly on the ship
        bullet_tex = arcade.Texture.create_empty("pb", (9, 54))
        bullet = arcade.Sprite(bullet_tex)
        bullet.center_x = ship.center_x
        bullet.center_y = ship.center_y
        bullets = arcade.SpriteList()
        bullets.append(bullet)

        events = ctrl.update(0.0, grid, None, bullets)
        assert GameEvent.ENEMY_DESTROYED in events
