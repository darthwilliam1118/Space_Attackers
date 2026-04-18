"""Unit tests for SAPowerUpSpawner — unlock order and weight table."""

from __future__ import annotations

import pytest

from src.powerups.sa_powerup_config import SAPowerUpConfig
from src.powerups.sa_spawner import SAPowerUpSpawner


@pytest.fixture
def cfg() -> SAPowerUpConfig:
    return SAPowerUpConfig()


def _spawner_at(cfg: SAPowerUpConfig, level: int, level_type: str = "standard") -> SAPowerUpSpawner:
    s = SAPowerUpSpawner(cfg)
    s.setup(level, level_type)
    return s


class TestAvailableTypes:
    def test_level_1_unlocks_nothing(self, cfg: SAPowerUpConfig) -> None:
        s = _spawner_at(cfg, 1)
        assert s._available_types() == []

    def test_level_2_unlocks_health_only(self, cfg: SAPowerUpConfig) -> None:
        s = _spawner_at(cfg, 2)
        assert s._available_types() == ["health"]

    def test_level_3_unlocks_health_and_shield(self, cfg: SAPowerUpConfig) -> None:
        s = _spawner_at(cfg, 3)
        assert s._available_types() == ["health", "shield"]

    def test_level_9_unlocks_all_eight(self, cfg: SAPowerUpConfig) -> None:
        s = _spawner_at(cfg, 9)
        assert s._available_types() == SAPowerUpSpawner.UNLOCK_ORDER

    def test_level_50_does_not_grow_past_unlock_order(self, cfg: SAPowerUpConfig) -> None:
        s = _spawner_at(cfg, 50)
        assert s._available_types() == SAPowerUpSpawner.UNLOCK_ORDER


class TestWeightTable:
    def test_level_1_returns_empty(self, cfg: SAPowerUpConfig) -> None:
        s = _spawner_at(cfg, 1)
        assert s._build_weight_table() == {}

    def test_level_2_only_health_weight(self, cfg: SAPowerUpConfig) -> None:
        s = _spawner_at(cfg, 2)
        weights = s._build_weight_table()
        assert weights == {"health": cfg.weight_health}

    def test_level_4_includes_unlocked_subset(self, cfg: SAPowerUpConfig) -> None:
        s = _spawner_at(cfg, 4)
        weights = s._build_weight_table()
        assert set(weights.keys()) == {"health", "shield", "rapid_fire"}

    def test_boss_doubles_select_types(self, cfg: SAPowerUpConfig) -> None:
        # At level 9 all types unlocked; boss boosts triple_shot/shield/big_gun
        s = _spawner_at(cfg, 9, level_type="boss")
        weights = s._build_weight_table()
        assert weights["triple_shot"] == cfg.weight_triple_shot * 2.0
        assert weights["shield"] == cfg.weight_shield * 2.0
        assert weights["big_gun"] == cfg.weight_big_gun * 2.0
        # Untouched types keep base weight
        assert weights["health"] == cfg.weight_health

    def test_standard_does_not_double(self, cfg: SAPowerUpConfig) -> None:
        s = _spawner_at(cfg, 9, level_type="standard")
        weights = s._build_weight_table()
        assert weights["triple_shot"] == cfg.weight_triple_shot
        assert weights["shield"] == cfg.weight_shield
        assert weights["big_gun"] == cfg.weight_big_gun


class TestSpawnerUpdate:
    def test_update_returns_none_when_below_interval(self, cfg: SAPowerUpConfig) -> None:
        s = _spawner_at(cfg, 5)
        # First update with tiny dt — should not have hit interval
        assert s.update(0.001) is None

    def test_level_1_never_returns_a_type(self, cfg: SAPowerUpConfig) -> None:
        s = _spawner_at(cfg, 1)
        # Force interval to elapse
        for _ in range(10):
            result = s.update(cfg.spawn_interval_base + cfg.spawn_interval_jitter + 1.0)
            assert result is None
