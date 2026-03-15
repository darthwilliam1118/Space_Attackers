"""Tests for GameConfig loader and saver."""

import tomllib
from pathlib import Path

import pytest

from src.game_config import GameConfig


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
