"""Unit tests for SAPowerUpManager — effect-type mapping and spawner wiring."""

from __future__ import annotations

import pytest

from src.powerups.effects.big_gun import BigGunEffect
from src.powerups.effects.free_move import FreeMovementEffect
from src.powerups.effects.health import HealthEffect
from src.powerups.effects.rapid_fire import RapidFireEffect
from src.powerups.effects.shield import ShieldEffect
from src.powerups.effects.speed_boost import SpeedBoostEffect
from src.powerups.effects.spread_shot import SpreadShotEffect
from src.powerups.effects.triple_shot import TripleShotEffect
from src.powerups.sa_manager import SAPowerUpManager
from src.powerups.sa_powerup_config import SAPowerUpConfig
from src.powerups.sa_spawner import SAPowerUpSpawner


@pytest.fixture
def manager() -> SAPowerUpManager:
    return SAPowerUpManager(SAPowerUpConfig(), 800, 600)


class TestCreateSpawner:
    def test_returns_sa_subclass(self, manager: SAPowerUpManager) -> None:
        assert isinstance(manager._spawner, SAPowerUpSpawner)


class TestCreateEffect:
    @pytest.mark.parametrize(
        "effect_type, cls",
        [
            ("health", HealthEffect),
            ("shield", ShieldEffect),
            ("rapid_fire", RapidFireEffect),
            ("big_gun", BigGunEffect),
            ("speed_boost", SpeedBoostEffect),
            ("triple_shot", TripleShotEffect),
            ("spread_shot", SpreadShotEffect),
            ("free_move", FreeMovementEffect),
        ],
    )
    def test_returns_correct_class(
        self, manager: SAPowerUpManager, effect_type: str, cls: type
    ) -> None:
        eff = manager.create_effect(effect_type)
        assert isinstance(eff, cls)
        assert eff.effect_type == effect_type

    def test_unknown_type_raises(self, manager: SAPowerUpManager) -> None:
        with pytest.raises(ValueError, match="Unknown power-up type"):
            manager.create_effect("not_a_real_type")


class TestSnapshotRoundTrip:
    def test_snapshot_preserves_spawner_timer(self) -> None:
        cfg = SAPowerUpConfig()
        m = SAPowerUpManager(cfg, 800, 600)
        m.setup(5, "standard")
        m._spawner.timer = 3.5
        snap = m.to_snapshot()
        restored = SAPowerUpManager.from_snapshot(
            snap, cfg, 800, 600, sprite_scale=1.0, level_number=5, level_type="standard"
        )
        assert restored._spawner.timer == 3.5
