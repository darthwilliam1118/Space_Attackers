"""Tests for PlayerState dataclass."""

from src.player_state import PlayerState


def test_defaults() -> None:
    p = PlayerState(player_num=1, lives=3)
    assert p.score == 0
    assert p.current_level == 1
    assert p.level_snapshot is None
    assert p.is_alive is True


def test_two_players_independent() -> None:
    p1 = PlayerState(player_num=1, lives=3)
    p2 = PlayerState(player_num=2, lives=3)
    p1.score = 500
    p1.current_level = 3
    assert p2.score == 0
    assert p2.current_level == 1


def test_snapshot_stored_and_cleared() -> None:
    p = PlayerState(player_num=1, lives=3)
    p.level_snapshot = {"enemies": [(10, 20), (30, 40)]}
    assert p.level_snapshot is not None
    p.level_snapshot = None
    assert p.level_snapshot is None


def test_is_alive_flag() -> None:
    p = PlayerState(player_num=1, lives=0)
    p.is_alive = False
    assert not p.is_alive
