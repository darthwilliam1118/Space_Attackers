"""Unit tests for BossConfig, BossSprite, BossLevel, and LevelFactory boss routing."""

from __future__ import annotations

import arcade
from agf.events import GameEvent

from src.boss_config import BossConfig
from src.diving_config import DivingConfig
from src.levels.boss_level import BossLevel
from src.levels.level_factory import create_level

W, H = 800, 600


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _boss_tex() -> arcade.Texture:
    return arcade.Texture.create_empty("boss_t", (96, 96))


def _make_boss_config(**overrides) -> BossConfig:
    defaults: dict = dict(
        boss_hp_base=300,
        boss_hp_per_boss=100,
        boss_speed_base=60.0,
        boss_speed_per_boss=0.0,
        boss_speed_max=180.0,
        boss_side_margin=40.0,
        boss_drop_distance=24.0,
        boss_fire_interval_base=999.0,  # very long — no auto-fire in tests
        boss_fire_interval_per_boss=0.0,
        boss_fire_interval_min=999.0,
        boss_bullet_speed=280.0,
        boss_bullet_damage=1,
        boss_spread_chance=0.0,  # no spread in tests by default
        boss_spread_count=5,
        boss_spread_angle=30.0,
        boss_points_base=1000,
        boss_points_per_boss=500,
        boss_death_duration=0.1,
        boss_death_explosion_count=2,
        boss_death_particle_count=10,
        boss_dive_group_size_max=1,
        boss_dive_interval_base=9999.0,
        boss_dive_interval_min=9999.0,
        boss_diver_loop_count=1,
        boss_pu_weight_shield=1.0,
        boss_pu_weight_big_gun=1.0,
        boss_pu_weight_spread_shot=1.0,
    )
    defaults.update(overrides)
    return BossConfig(**defaults)


def _make_level(
    cfg: BossConfig | None = None,
    encounter: int = 1,
) -> BossLevel:
    """Create a BossLevel without a display (no power-up managers, no diving)."""
    if cfg is None:
        cfg = _make_boss_config()
    level = BossLevel(cfg, DivingConfig(), W, H)
    level.setup(5 * encounter)
    return level


# ---------------------------------------------------------------------------
# BossConfig
# ---------------------------------------------------------------------------


class TestBossConfig:
    def test_defaults_are_valid(self) -> None:
        cfg = BossConfig()
        assert cfg.boss_hp_base > 0
        assert cfg.boss_speed_base > 0
        assert cfg.boss_death_duration > 0

    def test_custom_values_override_defaults(self) -> None:
        cfg = BossConfig(boss_hp_base=999)
        assert cfg.boss_hp_base == 999


# ---------------------------------------------------------------------------
# BossSprite
# ---------------------------------------------------------------------------


class TestBossSprite:
    def _make_sprite(self, cfg: BossConfig | None = None, encounter: int = 1) -> arcade.Sprite:
        from src.sprites.boss_sprite import BossSprite

        if cfg is None:
            cfg = _make_boss_config()
        return BossSprite(cfg, encounter, W, H, scale=1.0, texture=_boss_tex())

    def test_hp_scales_by_encounter(self) -> None:
        cfg = _make_boss_config(boss_hp_base=300, boss_hp_per_boss=100)
        s1 = self._make_sprite(cfg, encounter=1)
        s2 = self._make_sprite(cfg, encounter=2)
        assert s1.hit_points == 300
        assert s2.hit_points == 400

    def test_speed_capped_at_max(self) -> None:
        cfg = _make_boss_config(
            boss_speed_base=9000.0, boss_speed_per_boss=0.0, boss_speed_max=200.0
        )
        sprite = self._make_sprite(cfg, encounter=1)
        assert sprite._vx == 200.0

    def test_spawns_at_top_centre(self) -> None:
        sprite = self._make_sprite()
        assert abs(sprite.center_x - W / 2) < 1.0
        assert sprite.center_y > H * 0.5

    def test_bounces_right_on_left_margin(self) -> None:
        cfg = _make_boss_config(boss_side_margin=40.0, boss_drop_distance=24.0)
        sprite = self._make_sprite(cfg)
        sprite._vx = -200.0
        start_y = sprite.center_y
        # Force sprite to left margin
        sprite.center_x = cfg.boss_side_margin + sprite.width / 2.0 + 0.1
        sprite._move(1 / 60)
        assert sprite._vx > 0  # reversed direction
        assert sprite.center_y < start_y  # dropped

    def test_bounces_left_on_right_margin(self) -> None:
        cfg = _make_boss_config(boss_side_margin=40.0, boss_drop_distance=24.0)
        sprite = self._make_sprite(cfg)
        sprite._vx = 200.0
        start_y = sprite.center_y
        sprite.center_x = W - cfg.boss_side_margin - sprite.width / 2.0 - 0.1
        sprite._move(1 / 60)
        assert sprite._vx < 0
        assert sprite.center_y < start_y

    def test_take_damage_reduces_hp(self) -> None:
        sprite = self._make_sprite(_make_boss_config(boss_hp_base=300))
        sprite.take_damage(100)
        assert sprite.hit_points == 200

    def test_take_damage_returns_true_on_death(self) -> None:
        sprite = self._make_sprite(_make_boss_config(boss_hp_base=100))
        result = sprite.take_damage(100)
        assert result is True
        assert sprite.hit_points == 0

    def test_take_damage_returns_false_when_alive(self) -> None:
        sprite = self._make_sprite(_make_boss_config(boss_hp_base=200))
        result = sprite.take_damage(100)
        assert result is False

    def test_is_invincible_returns_false(self) -> None:
        sprite = self._make_sprite()
        assert sprite.is_invincible() is False

    def test_generate_bullets_single_shot(self) -> None:
        cfg = _make_boss_config(boss_spread_chance=0.0, boss_fire_interval_base=0.01)
        sprite = self._make_sprite(cfg)
        sprite._generate_bullets()
        bullets = sprite.consume_pending_bullets()
        assert len(bullets) == 1

    def test_generate_bullets_spread(self) -> None:
        cfg = _make_boss_config(
            boss_spread_chance=1.0, boss_spread_count=5, boss_fire_interval_base=0.01
        )
        sprite = self._make_sprite(cfg)
        sprite._generate_bullets()
        bullets = sprite.consume_pending_bullets()
        assert len(bullets) == 5

    def test_consume_pending_bullets_clears_list(self) -> None:
        sprite = self._make_sprite()
        sprite._generate_bullets()
        sprite.consume_pending_bullets()
        assert sprite.consume_pending_bullets() == []

    def test_spread_chance_override_forces_spread(self) -> None:
        cfg = _make_boss_config(boss_spread_chance=0.0, boss_spread_count=3)
        sprite = self._make_sprite(cfg)
        sprite._spread_chance_override = 1.0
        sprite._generate_bullets()
        bullets = sprite.consume_pending_bullets()
        assert len(bullets) == 3

    def test_reaches_bottom_true_when_below_zone(self) -> None:
        sprite = self._make_sprite()
        sprite.center_y = sprite.height / 2.0  # near bottom
        assert sprite.reaches_bottom(sprite.height) is True

    def test_reaches_bottom_false_when_high(self) -> None:
        sprite = self._make_sprite()
        sprite.center_y = H * 0.9
        assert sprite.reaches_bottom(H * 0.3) is False


# ---------------------------------------------------------------------------
# BossLevel
# ---------------------------------------------------------------------------


class TestBossLevel:
    def test_level_type_is_boss(self) -> None:
        level = _make_level()
        assert level.level_type == "boss"

    def test_not_cleared_after_setup(self) -> None:
        level = _make_level()
        assert not level.is_cleared()

    def test_get_boss_hp_bar_data_returns_tuple_after_setup(self) -> None:
        level = _make_level()
        data = level.get_boss_hp_bar_data()
        assert data is not None
        cx, bar_y, bar_width, hp, max_hp = data
        assert hp == max_hp  # full health at start
        assert bar_width > 0

    def test_get_boss_hp_bar_data_width_matches_boss_width(self) -> None:
        level = _make_level()
        data = level.get_boss_hp_bar_data()
        assert data is not None
        _, _, bar_width, _, _ = data
        assert abs(bar_width - level._boss.width) < 0.1

    def test_get_boss_hp_bar_data_returns_none_during_death(self) -> None:
        level = _make_level()
        level._start_death_sequence()
        assert level.get_boss_hp_bar_data() is None

    def test_boss_death_center_stored_on_death(self) -> None:
        level = _make_level()
        cx = level._boss.center_x
        cy = level._boss.center_y
        level._start_death_sequence()
        death_center = level.get_boss_death_center()
        assert death_center is not None
        assert abs(death_center[0] - cx) < 0.1
        assert abs(death_center[1] - cy) < 0.1

    def test_cleared_after_death_duration_elapses(self) -> None:
        cfg = _make_boss_config(
            boss_hp_base=1,
            boss_death_duration=0.05,
            boss_death_explosion_count=1,
        )
        level = BossLevel(cfg, DivingConfig(), W, H)
        level.setup(5)
        level._start_death_sequence()
        events = level._update_death_sequence(0.1)
        assert level.is_cleared()
        assert GameEvent.LEVEL_COMPLETE in events

    def test_apply_player_bullet_returns_none(self) -> None:
        from unittest.mock import MagicMock

        level = _make_level()
        bullet = MagicMock()
        result = level.apply_player_bullet(bullet)
        assert result is None

    def test_consume_pending_hits_returns_boss_hits(self) -> None:
        level = _make_level()
        assert level._boss is not None
        level._boss.record_hit(lethal=True)
        hits = level.consume_pending_hits()
        assert len(hits) == 1
        x, y, pts = hits[0]
        assert pts == level._boss.points

    def test_consume_pending_hits_clears_list(self) -> None:
        level = _make_level()
        level._boss.record_hit(lethal=True)
        level.consume_pending_hits()
        assert level.consume_pending_hits() == []

    def test_has_any_airborne_false_with_no_divers(self) -> None:
        level = _make_level()
        assert level.has_any_airborne() is False

    def test_get_all_enemy_sprites_does_not_contain_boss(self) -> None:
        # Boss has its own dedicated HP bar; it must not appear in the generic list.
        level = _make_level()
        sprites = level.get_all_enemy_sprites()
        assert level._boss not in sprites

    def test_velocity_returns_boss_vx(self) -> None:
        level = _make_level()
        vx, vy = level.velocity
        assert vx != 0.0  # boss is moving
        assert vy == 0.0

    def test_to_snapshot_includes_level_type(self) -> None:
        level = _make_level()
        snap = level.to_snapshot()
        assert snap["level_type"] == "boss"

    def test_to_snapshot_includes_boss_hp(self) -> None:
        level = _make_level()
        snap = level.to_snapshot()
        assert snap["boss"]["hp"] == level._boss.hit_points


# ---------------------------------------------------------------------------
# LevelFactory boss routing
# ---------------------------------------------------------------------------


class TestLevelFactoryBoss:
    # Boss levels are created via force_level_type, not by level number routing.
    def test_force_boss_returns_boss_level(self) -> None:
        from src.levels.boss_level import BossLevel

        result = create_level(5, None, W, H, force_level_type="boss")
        assert isinstance(result, BossLevel)

    def test_force_boss_at_any_level_number(self) -> None:
        from src.levels.boss_level import BossLevel

        for n in [5, 10, 15]:
            result = create_level(n, None, W, H, force_level_type="boss")
            assert isinstance(result, BossLevel)

    def test_level_5_without_force_returns_standard(self) -> None:
        from src.levels.standard_level import StandardLevel

        result = create_level(5, None, W, H)
        assert isinstance(result, StandardLevel)

    def test_level_3_without_force_returns_standard(self) -> None:
        from src.levels.standard_level import StandardLevel

        result = create_level(3, None, W, H)
        assert isinstance(result, StandardLevel)

    def test_create_level_1_returns_standard_level(self) -> None:
        from src.levels.standard_level import StandardLevel

        result = create_level(1, None, W, H)
        assert isinstance(result, StandardLevel)

    def test_from_snapshot_boss_returns_boss_level(self) -> None:
        from src.levels.boss_level import BossLevel

        level = create_level(5, None, W, H, force_level_type="boss")
        snap = level.to_snapshot()
        restored = create_level(5, None, W, H, snapshot=snap)
        assert isinstance(restored, BossLevel)

    def test_restored_boss_hp_matches_snapshot(self) -> None:
        level = create_level(5, None, W, H, force_level_type="boss")
        level._boss.hit_points = 123
        snap = level.to_snapshot()
        restored = create_level(5, None, W, H, snapshot=snap)
        assert restored._boss.hit_points == 123
