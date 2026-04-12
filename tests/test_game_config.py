"""Tests for GameConfig loader and saver."""

import sys
import tomllib
from pathlib import Path

import pytest

from src.game_config import GameConfig, _apply_argv_overrides


def test_load_defaults(tmp_path: Path) -> None:
    cfg_file = tmp_path / "game_config.toml"
    cfg_file.write_text("[game]\nstarting_level = 1\nnum_lives = 3\nspawn_safe_radius = 80\n")
    cfg = GameConfig.load(cfg_file)
    assert cfg.starting_level == 1
    assert cfg.num_lives == 3
    assert cfg.spawn_safe_radius == 80


def test_load_custom_values(tmp_path: Path) -> None:
    cfg_file = tmp_path / "game_config.toml"
    cfg_file.write_text("[game]\nstarting_level = 5\nnum_lives = 5\nspawn_safe_radius = 120\n")
    cfg = GameConfig.load(cfg_file)
    assert cfg.starting_level == 5
    assert cfg.num_lives == 5
    assert cfg.spawn_safe_radius == 120


def test_load_missing_keys_use_defaults(tmp_path: Path) -> None:
    cfg_file = tmp_path / "game_config.toml"
    cfg_file.write_text("[game]\n")  # all keys absent
    cfg = GameConfig.load(cfg_file)
    assert cfg.starting_level == 1
    assert cfg.num_lives == 3
    assert cfg.spawn_safe_radius == 80


def test_save_roundtrip(tmp_path: Path) -> None:
    cfg_file = tmp_path / "game_config.toml"
    original = GameConfig(starting_level=3, num_lives=5, spawn_safe_radius=100)
    original.save(cfg_file)
    reloaded = GameConfig.load(cfg_file)
    assert reloaded.starting_level == 3
    assert reloaded.num_lives == 5
    assert reloaded.spawn_safe_radius == 100


def test_save_produces_valid_toml(tmp_path: Path) -> None:
    cfg_file = tmp_path / "game_config.toml"
    GameConfig(starting_level=2, num_lives=4, spawn_safe_radius=60).save(cfg_file)
    with open(cfg_file, "rb") as fh:
        data = tomllib.load(fh)
    assert data["game"]["starting_level"] == 2


# ---------------------------------------------------------------------------
# argv override tests
# ---------------------------------------------------------------------------


class TestArgvOverrides:
    def test_int_field_overridden(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "-num_lives", "7"])
        cfg = GameConfig()
        _apply_argv_overrides(cfg)
        assert cfg.num_lives == 7

    def test_float_field_overridden(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "-sprite_scale", "2.0"])
        cfg = GameConfig()
        _apply_argv_overrides(cfg)
        assert cfg.sprite_scale == 2.0

    def test_bool_field_with_value_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "-debug", "true"])
        cfg = GameConfig()
        _apply_argv_overrides(cfg)
        assert cfg.debug is True

    def test_bool_field_with_value_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "-god_mode", "false"])
        cfg = GameConfig(god_mode=True)
        _apply_argv_overrides(cfg)
        assert cfg.god_mode is False

    def test_bool_flag_no_value_sets_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "-debug"])
        cfg = GameConfig()
        _apply_argv_overrides(cfg)
        assert cfg.debug is True

    def test_sub_config_field_overridden(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "-ship_speed", "999.0"])
        cfg = GameConfig()
        _apply_argv_overrides(cfg)
        assert cfg.ship.ship_speed == 999.0

    def test_unknown_arg_prints_warning(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "-not_a_real_key", "5"])
        cfg = GameConfig()
        _apply_argv_overrides(cfg)
        out = capsys.readouterr().out
        assert "Unknown argument -not_a_real_key, ignored" in out

    def test_double_dash_prefix_also_works(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "--num_lives", "9"])
        cfg = GameConfig()
        _apply_argv_overrides(cfg)
        assert cfg.num_lives == 9

    def test_multiple_overrides_applied(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "-num_lives", "2", "-starting_level", "5"])
        cfg = GameConfig()
        _apply_argv_overrides(cfg)
        assert cfg.num_lives == 2
        assert cfg.starting_level == 5

    def test_toml_not_modified(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        cfg_file = tmp_path / "game_config.toml"
        cfg_file.write_text("[game]\nnum_lives = 3\n")
        monkeypatch.setattr(sys, "argv", ["prog", "-num_lives", "99"])
        cfg = GameConfig.load(cfg_file)
        assert cfg.num_lives == 99  # override applied in memory
        with open(cfg_file) as fh:
            assert "99" not in fh.read()  # file unchanged

    def test_empty_argv_leaves_config_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "argv", ["prog"])
        cfg = GameConfig(num_lives=5)
        _apply_argv_overrides(cfg)
        assert cfg.num_lives == 5
