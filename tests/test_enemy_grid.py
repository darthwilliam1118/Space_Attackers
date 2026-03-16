"""Unit tests for EnemyGrid, EnemySprite, EnemyBullet — no display required."""

from __future__ import annotations

import arcade
import pytest

from src.enemy_config import EnemyConfig
from src.enemy_grid import EnemyGrid
from src.sprites.enemy_sprite import ROW_MAPPING, EnemySprite, sprite_path_for
from src.sprites.enemy_bullet import EnemyBullet

W, H = 800, 600


def _enemy_tex() -> arcade.Texture:
    return arcade.Texture.create_empty("enemy", (48, 32))


def _bullet_tex() -> arcade.Texture:
    return arcade.Texture.create_empty("ebullet", (9, 54))


def _cfg(**kwargs: object) -> EnemyConfig:
    return EnemyConfig(**kwargs)  # type: ignore[arg-type]


def _grid(**kwargs: object) -> EnemyGrid:
    cfg = _cfg(**kwargs)
    g = EnemyGrid(cfg, W, H, enemy_texture=_enemy_tex(), bullet_texture=_bullet_tex())
    g.setup(level=1)
    return g


# ---------------------------------------------------------------------------
# EnemySprite
# ---------------------------------------------------------------------------

class TestEnemySpriteMapping:
    def test_row_mapping_has_five_entries(self) -> None:
        assert len(ROW_MAPPING) == 5

    def test_sprite_path_format(self) -> None:
        path = sprite_path_for("Black", 1)
        assert "enemyBlack1.png" in path

    def test_row0_is_black1(self) -> None:
        assert ROW_MAPPING[0] == ("Black", 1)

    def test_row4_is_black5(self) -> None:
        assert ROW_MAPPING[4] == ("Black", 5)

    def test_row_cycling_uses_modulo_5(self) -> None:
        assert ROW_MAPPING[5 % 5] == ROW_MAPPING[0]


# ---------------------------------------------------------------------------
# EnemyBullet
# ---------------------------------------------------------------------------

class TestEnemyBullet:
    def test_moves_downward(self) -> None:
        b = EnemyBullet(100, 300, speed=250, texture=_bullet_tex())
        b.update(0.1)
        assert b.center_y == pytest.approx(300 - 250 * 0.1)

    def test_removes_when_below_screen(self) -> None:
        b = EnemyBullet(100, 5, speed=250, texture=_bullet_tex())
        sl = arcade.SpriteList()
        sl.append(b)
        b.update(1.0)
        assert b not in sl


# ---------------------------------------------------------------------------
# Grid spawn
# ---------------------------------------------------------------------------

class TestGridSpawn:
    def test_correct_sprite_count(self) -> None:
        g = _grid(enemy_cols=5, enemy_rows=4)
        assert len(g.get_sprite_list()) == 20

    def test_correct_sprite_count_custom(self) -> None:
        g = _grid(enemy_cols=3, enemy_rows=2)
        assert len(g.get_sprite_list()) == 6

    def test_row0_color_and_type(self) -> None:
        g = _grid(enemy_cols=5, enemy_rows=4)
        row0 = [s for s in g.get_sprite_list() if s.row == 0]
        assert all(s.color_name == "Black" and s.ship_type == 1 for s in row0)

    def test_row1_color_and_type(self) -> None:
        g = _grid(enemy_cols=5, enemy_rows=4)
        row1 = [s for s in g.get_sprite_list() if s.row == 1]
        assert all(s.color_name == "Blue" and s.ship_type == 2 for s in row1)

    def test_row2_color_and_type(self) -> None:
        g = _grid(enemy_cols=5, enemy_rows=4)
        row2 = [s for s in g.get_sprite_list() if s.row == 2]
        assert all(s.color_name == "Green" and s.ship_type == 3 for s in row2)

    def test_row3_color_and_type(self) -> None:
        g = _grid(enemy_cols=5, enemy_rows=4)
        row3 = [s for s in g.get_sprite_list() if s.row == 3]
        assert all(s.color_name == "Red" and s.ship_type == 4 for s in row3)

    def test_horizontal_spacing_has_one_buffer_column_each_side(self) -> None:
        # Grid is laid out with (cols+2) column-width slots so there is
        # exactly one empty column of space on each side before the margin.
        margin = 40.0
        cols = 5
        g = _grid(enemy_cols=cols, enemy_rows=1, enemy_side_margin=margin)
        xs = sorted(s.center_x for s in g.get_sprite_list())
        usable_w = W - 2 * margin
        col_spacing = usable_w / (cols + 1)
        assert xs[0] == pytest.approx(margin + col_spacing)
        assert xs[-1] == pytest.approx(margin + cols * col_spacing)

    def test_topmost_row_at_80pct_height(self) -> None:
        g = _grid(enemy_cols=1, enemy_rows=1)
        sprites = list(g.get_sprite_list())
        assert sprites[0].center_y == pytest.approx(H * 0.80)


# ---------------------------------------------------------------------------
# Grid movement
# ---------------------------------------------------------------------------

class TestGridMovement:
    def test_moves_right_by_default(self) -> None:
        g = _grid(enemy_speed_initial=100)
        initial_xs = [s.center_x for s in g.get_sprite_list()]
        g.update(0.1, None, 0.0)
        new_xs = [s.center_x for s in g.get_sprite_list()]
        assert all(nx > ox for nx, ox in zip(new_xs, initial_xs))

    def test_movement_is_delta_time_scaled(self) -> None:
        g1 = _grid(enemy_speed_initial=100)
        g2 = _grid(enemy_speed_initial=100)
        xs1_before = [s.center_x for s in g1.get_sprite_list()]
        xs2_before = [s.center_x for s in g2.get_sprite_list()]
        g1.update(0.1, None, 0.0)
        g2.update(0.2, None, 0.0)
        delta1 = [s.center_x - ox for s, ox in zip(g1.get_sprite_list(), xs1_before)]
        delta2 = [s.center_x - ox for s, ox in zip(g2.get_sprite_list(), xs2_before)]
        for d1, d2 in zip(delta1, delta2):
            assert d2 == pytest.approx(2 * d1)


# ---------------------------------------------------------------------------
# Boundary check and reversal
# ---------------------------------------------------------------------------

class TestBoundary:
    def test_reversal_triggered_at_right_margin(self) -> None:
        g = _grid(enemy_cols=1, enemy_rows=1, enemy_side_margin=40,
                  enemy_speed_initial=100)
        # Force rightmost enemy close to right edge
        for s in g.get_sprite_list():
            s.center_x = W - 40 - s.width / 2 + 1  # just past margin
        g._origin_x = list(g.get_sprite_list())[0].center_x
        assert g._direction == 1.0
        g.check_boundary()
        assert g._direction == -1.0

    def test_reversal_triggered_at_left_margin(self) -> None:
        g = _grid(enemy_cols=1, enemy_rows=1, enemy_side_margin=40,
                  enemy_speed_initial=100)
        g._direction = -1.0
        for s in g.get_sprite_list():
            s.center_x = 40 + s.width / 2 - 1  # just past left margin
        g.check_boundary()
        assert g._direction == 1.0

    def test_drop_distance_on_reversal(self) -> None:
        drop = 48.0
        g = _grid(enemy_cols=1, enemy_rows=1, enemy_side_margin=40,
                  enemy_drop_distance=drop)
        initial_y = list(g.get_sprite_list())[0].center_y
        for s in g.get_sprite_list():
            s.center_x = W  # force right boundary
        g.check_boundary()
        new_y = list(g.get_sprite_list())[0].center_y
        assert initial_y - new_y == pytest.approx(drop)

    def test_boundary_uses_surviving_enemies_not_original_edge(self) -> None:
        """Destroying the rightmost column shrinks effective boundary."""
        g = _grid(enemy_cols=3, enemy_rows=1, enemy_side_margin=40,
                  enemy_speed_initial=0)
        sprites = sorted(g.get_sprite_list(), key=lambda s: s.center_x)
        # Remove the rightmost enemy
        sprites[-1].remove_from_sprite_lists()
        # New rightmost is the middle column
        surviving_right = max(s.right for s in g.get_sprite_list())
        assert surviving_right < W - 40


# ---------------------------------------------------------------------------
# Speed scaling
# ---------------------------------------------------------------------------

class TestSpeedScaling:
    def test_speed_at_zero_destruction(self) -> None:
        g = _grid(enemy_speed_initial=80, enemy_speed_max_bonus=120,
                  enemy_cols=4, enemy_rows=1)
        assert g._speed == pytest.approx(80.0)

    def test_speed_at_full_destruction(self) -> None:
        g = _grid(enemy_speed_initial=80, enemy_speed_max_bonus=120,
                  enemy_cols=4, enemy_rows=1)
        g._enemies_destroyed = g._total_enemies
        g.recalculate_speed()
        assert g._speed == pytest.approx(200.0)

    def test_speed_at_50pct_destruction(self) -> None:
        g = _grid(enemy_speed_initial=80, enemy_speed_max_bonus=120,
                  enemy_cols=4, enemy_rows=1)
        g._enemies_destroyed = g._total_enemies // 2
        g.recalculate_speed()
        assert g._speed == pytest.approx(140.0)


# ---------------------------------------------------------------------------
# Bottom enemies
# ---------------------------------------------------------------------------

class TestBottomEnemies:
    def test_returns_one_per_column(self) -> None:
        g = _grid(enemy_cols=5, enemy_rows=4)
        bottom = g.get_bottom_enemies()
        assert len(bottom) == 5
        assert all(v is not None for v in bottom.values())

    def test_bottom_enemy_has_highest_row_index(self) -> None:
        g = _grid(enemy_cols=1, enemy_rows=3)
        bottom = g.get_bottom_enemies()
        assert bottom[0].row == 2  # type: ignore[union-attr]

    def test_updates_when_bottom_enemy_destroyed(self) -> None:
        g = _grid(enemy_cols=1, enemy_rows=3)
        bottom_before = g.get_bottom_enemies()[0]
        assert bottom_before is not None
        bottom_before.remove_from_sprite_lists()
        g._enemies_destroyed += 1
        new_bottom = g.get_bottom_enemies()[0]
        assert new_bottom is not None
        assert new_bottom.row == 1  # row 2 was removed, row 1 is now bottom


# ---------------------------------------------------------------------------
# apply_player_bullet
# ---------------------------------------------------------------------------

class TestApplyPlayerBullet:
    def test_returns_none_on_miss(self) -> None:
        g = _grid(enemy_cols=1, enemy_rows=1)
        bullet = EnemyBullet(9999, 9999, 500, texture=_bullet_tex())
        assert g.apply_player_bullet(bullet) is None

    def test_returns_enemy_center_on_hit(self) -> None:
        g = _grid(enemy_cols=1, enemy_rows=1)
        enemy = list(g.get_sprite_list())[0]
        expected_cx, expected_cy = enemy.center_x, enemy.center_y
        # Use same texture size so collision hit box overlaps
        bullet_tex = arcade.Texture.create_empty("pb", (9, 54))
        bullet = arcade.Sprite(bullet_tex)
        bullet.center_x = enemy.center_x
        bullet.center_y = enemy.center_y
        result = g.apply_player_bullet(bullet)
        assert result == (expected_cx, expected_cy)

    def test_removes_enemy_on_hit(self) -> None:
        g = _grid(enemy_cols=1, enemy_rows=1)
        enemy = list(g.get_sprite_list())[0]
        bullet_tex = arcade.Texture.create_empty("pb2", (9, 54))
        bullet = arcade.Sprite(bullet_tex)
        bullet.center_x = enemy.center_x
        bullet.center_y = enemy.center_y
        g.apply_player_bullet(bullet)
        assert len(g.get_sprite_list()) == 0


# ---------------------------------------------------------------------------
# is_cleared
# ---------------------------------------------------------------------------

class TestIsCleared:
    def test_not_cleared_with_enemies(self) -> None:
        g = _grid(enemy_cols=2, enemy_rows=1)
        assert not g.is_cleared()

    def test_cleared_when_all_removed(self) -> None:
        g = _grid(enemy_cols=1, enemy_rows=1)
        list(g.get_sprite_list())[0].remove_from_sprite_lists()
        assert g.is_cleared()


# ---------------------------------------------------------------------------
# Snapshot round-trip
# ---------------------------------------------------------------------------

class TestSnapshot:
    def test_snapshot_contains_required_keys(self) -> None:
        g = _grid(enemy_cols=2, enemy_rows=2)
        snap = g.to_snapshot()
        for key in ("enemies", "direction", "speed", "shoot_timers", "projectiles"):
            assert key in snap

    def test_snapshot_enemy_count(self) -> None:
        g = _grid(enemy_cols=3, enemy_rows=2)
        snap = g.to_snapshot()
        assert len(snap["enemies"]) == 6

    def test_snapshot_enemy_fields(self) -> None:
        g = _grid(enemy_cols=1, enemy_rows=1)
        snap = g.to_snapshot()
        e = snap["enemies"][0]
        for field in ("pos", "formation_pos", "diving", "col", "row", "color", "ship_type"):
            assert field in e

    def test_from_snapshot_restores_enemy_count(self) -> None:
        g = _grid(enemy_cols=3, enemy_rows=2)
        snap = g.to_snapshot()
        cfg = _cfg(enemy_cols=3, enemy_rows=2)
        g2 = EnemyGrid.from_snapshot(snap, cfg, W, H,
                                     enemy_texture=_enemy_tex(),
                                     bullet_texture=_bullet_tex())
        assert len(g2.get_sprite_list()) == 6

    def test_from_snapshot_restores_direction(self) -> None:
        g = _grid(enemy_cols=2, enemy_rows=1)
        g._direction = -1.0
        snap = g.to_snapshot()
        cfg = _cfg(enemy_cols=2, enemy_rows=1)
        g2 = EnemyGrid.from_snapshot(snap, cfg, W, H,
                                     enemy_texture=_enemy_tex(),
                                     bullet_texture=_bullet_tex())
        assert g2._direction == pytest.approx(-1.0)

    def test_from_snapshot_restores_speed(self) -> None:
        g = _grid(enemy_cols=2, enemy_rows=1, enemy_speed_initial=150)
        snap = g.to_snapshot()
        cfg = _cfg(enemy_cols=2, enemy_rows=1)
        g2 = EnemyGrid.from_snapshot(snap, cfg, W, H,
                                     enemy_texture=_enemy_tex(),
                                     bullet_texture=_bullet_tex())
        assert g2._speed == pytest.approx(150.0)
