"""Unit tests for MeteorLevel — no display required."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from agf.events import GameEvent

from src.meteor_config import MeteorConfig

# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #


def _make_config(**overrides) -> MeteorConfig:
    defaults = dict(
        storm_duration=10.0,
        spawn_rate_base=2.0,
        spawn_rate_scale_pct=0.10,
        spawn_rate_max=10.0,
        fall_speed_min=100.0,
        fall_speed_max=200.0,
        fall_angle_max=20.0,
        spin_rpm_min=10.0,
        spin_rpm_max=60.0,
        spawn_height_offset=40.0,
        hp_bar_duration=1.0,
        prob_large=0.30,
        prob_med=0.40,
        prob_small=0.20,
        prob_tiny=0.10,
        hp_large=1000,
        hp_med=500,
        hp_small=100,
        hp_tiny=25,
        points_large=200,
        points_med=100,
        points_small=50,
        points_tiny=25,
    )
    defaults.update(overrides)
    return MeteorConfig(**defaults)


def _fake_meteor(
    size: str = "small",
    hit_points: int = 100,
    vx: float = 0.0,
    vy: float = -100.0,
    spin: float = 0.0,
) -> MagicMock:
    """Plain MagicMock that quacks like a MeteorSprite — no OpenGL needed."""
    m = MagicMock()
    m.hit_points = hit_points
    m.max_hit_points = hit_points
    m.hp_bar_timer = 0.0
    m.center_x = 400.0
    m.center_y = 400.0
    m.width = 40.0
    m.height = 40.0
    return m


def _make_level(cfg: MeteorConfig | None = None):
    """Return a MeteorLevel using a plain list for _meteor_list so MagicMock
    sprites can be appended without requiring an arcade display context."""
    from src.levels.meteor_level import MeteorLevel

    config = cfg or _make_config()
    level = MeteorLevel(config, 800, 600, _meteor_factory=_fake_meteor)
    level.setup(4)  # level 4 → last regular = 3
    # Replace arcade.SpriteList with a plain list — tests don't need GPU collision
    level._meteor_list = []  # type: ignore[assignment]
    return level


# --------------------------------------------------------------------------- #
# is_cleared                                                                   #
# --------------------------------------------------------------------------- #


class TestIsCleared:
    def test_not_cleared_before_timer_expires(self) -> None:
        level = _make_level()
        assert not level.is_cleared()

    def test_not_cleared_when_timer_done_but_meteors_present(self) -> None:
        level = _make_level()
        level._storm_timer = level._config.storm_duration + 1.0
        level._meteor_list.append(_fake_meteor())
        assert not level.is_cleared()

    def test_cleared_when_timer_done_and_list_empty(self) -> None:
        level = _make_level()
        level._storm_timer = level._config.storm_duration + 1.0
        assert level.is_cleared()


# --------------------------------------------------------------------------- #
# apply_player_bullet                                                          #
# --------------------------------------------------------------------------- #


class TestApplyPlayerBullet:
    def _bullet(self, damage: int = 200) -> MagicMock:
        b = MagicMock()
        b.damage = damage
        return b

    def test_miss_returns_none(self) -> None:
        level = _make_level()
        with patch("arcade.check_for_collision_with_list", return_value=[]):
            result = level.apply_player_bullet(self._bullet())
        assert result is None

    def test_hit_kill_returns_killed_true(self) -> None:
        level = _make_level()
        meteor = _fake_meteor("small", hit_points=100)
        level._meteor_list.append(meteor)
        with patch("arcade.check_for_collision_with_list", return_value=[meteor]):
            result = level.apply_player_bullet(self._bullet(damage=200))
        assert result is not None
        assert result.killed is True
        assert result.points == level._config.points_small

    def test_hit_survive_returns_killed_false(self) -> None:
        level = _make_level()
        meteor = _fake_meteor("large", hit_points=1000)
        level._meteor_list.append(meteor)
        with patch("arcade.check_for_collision_with_list", return_value=[meteor]):
            result = level.apply_player_bullet(self._bullet(damage=100))
        assert result is not None
        assert result.killed is False
        assert meteor.hit_points == 900
        assert meteor.hp_bar_timer == level._config.hp_bar_duration

    def test_hit_survive_sets_hp_bar_timer(self) -> None:
        level = _make_level()
        meteor = _fake_meteor("large", hit_points=1000)
        level._meteor_list.append(meteor)
        with patch("arcade.check_for_collision_with_list", return_value=[meteor]):
            level.apply_player_bullet(self._bullet(damage=100))
        assert meteor.hp_bar_timer == level._config.hp_bar_duration

    def test_killed_meteor_hp_reduced_to_zero(self) -> None:
        level = _make_level()
        meteor = _fake_meteor("small", hit_points=50)
        level._meteor_list.append(meteor)
        with patch("arcade.check_for_collision_with_list", return_value=[meteor]):
            level.apply_player_bullet(self._bullet(damage=50))
        assert meteor.hit_points <= 0


# --------------------------------------------------------------------------- #
# consume_pending_hits                                                         #
# --------------------------------------------------------------------------- #


class TestConsumeHits:
    def test_consume_drains_pending_list(self) -> None:
        level = _make_level()
        level._pending_hits = [(100.0, 200.0, 50)]
        result = level.consume_pending_hits()
        assert result == [(100.0, 200.0, 50)]
        assert level.consume_pending_hits() == []

    def test_consume_non_lethal_always_empty(self) -> None:
        level = _make_level()
        assert level.consume_pending_non_lethal_hits() == []


# --------------------------------------------------------------------------- #
# Enemy bullet sprite list                                                     #
# --------------------------------------------------------------------------- #


class TestGetEnemyBullets:
    def test_returns_empty_sprite_list(self) -> None:
        import arcade

        level = _make_level()
        result = level.get_enemy_bullet_sprite_list()
        assert isinstance(result, arcade.SpriteList)
        assert len(result) == 0


# --------------------------------------------------------------------------- #
# Player collision → PLAYER_KILLED                                            #
# --------------------------------------------------------------------------- #


class TestPlayerCollision:
    def test_player_collision_returns_player_killed(self) -> None:
        level = _make_level()
        meteor = _fake_meteor("small", hit_points=100)
        level._meteor_list.append(meteor)
        ship = MagicMock()
        with patch("arcade.check_for_collision_with_list", return_value=[meteor]):
            events = level.update(0.016, ship, None)
        assert GameEvent.PLAYER_KILLED in events

    def test_player_collision_adds_pending_hit_for_explosion(self) -> None:
        level = _make_level()
        meteor = _fake_meteor("large", hit_points=1000)
        meteor.center_x = 400.0
        meteor.center_y = 400.0
        level._meteor_list.append(meteor)
        ship = MagicMock()
        with patch("arcade.check_for_collision_with_list", return_value=[meteor]):
            level.update(0.016, ship, None)
        hits = level.consume_pending_hits()
        assert len(hits) == 1
        assert hits[0][2] == 0  # no points for player death collision


# --------------------------------------------------------------------------- #
# Spawn rate formula                                                           #
# --------------------------------------------------------------------------- #


class TestSpawnRate:
    def test_rate_scales_with_level(self) -> None:
        from src.levels.meteor_level import MeteorLevel

        cfg = _make_config(spawn_rate_base=3.0, spawn_rate_scale_pct=0.10)
        level = MeteorLevel(cfg, 800, 600, _meteor_factory=_fake_meteor)

        level.setup(4)  # last_regular = 3
        interval_low = level._spawn_interval()

        level.setup(7)  # last_regular = 6
        interval_high = level._spawn_interval()

        assert interval_high < interval_low  # higher level → shorter interval

    def test_rate_capped_at_max(self) -> None:
        from src.levels.meteor_level import MeteorLevel

        cfg = _make_config(spawn_rate_base=3.0, spawn_rate_scale_pct=1.0, spawn_rate_max=5.0)
        level = MeteorLevel(cfg, 800, 600, _meteor_factory=_fake_meteor)
        level.setup(100)
        assert level._spawn_interval() == pytest.approx(1.0 / cfg.spawn_rate_max)


# --------------------------------------------------------------------------- #
# get_all_enemy_sprites                                                        #
# --------------------------------------------------------------------------- #


class TestGetAllEnemySprites:
    def test_returns_meteor_list(self) -> None:
        level = _make_level()
        meteor = _fake_meteor()
        level._meteor_list.append(meteor)
        sprites = level.get_all_enemy_sprites()
        assert meteor in sprites
