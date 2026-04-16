"""Unit tests for GameState enum and player-killed decision logic.

GameStateManager itself requires an Arcade window, so we test the pure
decision logic by exercising PlayerKilledView._resolve_next() via a
lightweight fake manager.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from agf.player_state import PlayerState

from src.state import GameState

# ---------------------------------------------------------------------------
# GameState enum
# ---------------------------------------------------------------------------


def test_all_expected_states_exist() -> None:
    expected = {
        "SPLASH",
        "MAIN",
        "GAME_CONFIG",
        "GAME_INIT",
        "SET_ACTIVE_PLAYER",
        "START_LEVEL",
        "RUN_LEVEL",
        "LEVEL_COMPLETE",
        "PLAYER_KILLED",
        "SAVE_SNAPSHOT_AND_SWITCH",
        "DROP_TO_1P",
        "GAME_OVER",
        "SCORE_ENTRY",
        "EXIT",
    }
    actual = {s.name for s in GameState}
    assert expected == actual


# ---------------------------------------------------------------------------
# Player-killed decision table
# ---------------------------------------------------------------------------
# We test _resolve_next() in isolation by constructing a fake manager context
# and calling the method directly — no Arcade window needed.


def _fake_manager(players: list[PlayerState], active_index: int) -> MagicMock:
    manager = MagicMock()
    manager.context = {
        "players": players,
        "active_player_index": active_index,
    }
    return manager


def _resolve(players: list[PlayerState], active_index: int):
    from src.views.player_killed import PlayerKilledView

    manager = _fake_manager(players, active_index)
    view = PlayerKilledView.__new__(PlayerKilledView)
    view._manager = manager
    view._elapsed = 0.0
    next_state, _ = view._resolve_next()
    return next_state, players


# 1P, lives > 0 → resume same player
def test_1p_lives_remaining_resumes_level() -> None:
    players = [PlayerState(player_num=1, lives=3)]
    state, _ = _resolve(players, 0)
    assert state == GameState.SET_ACTIVE_PLAYER
    assert players[0].lives == 2


# 1P, lives = 0 → game over
def test_1p_no_lives_game_over() -> None:
    players = [PlayerState(player_num=1, lives=1)]
    state, updated = _resolve(players, 0)
    assert state == GameState.GAME_OVER
    assert updated[0].lives == 0
    assert updated[0].is_alive is False


# 2P, active lives > 0 → save snapshot and switch
def test_2p_active_lives_remaining_switches_player() -> None:
    players = [
        PlayerState(player_num=1, lives=3),
        PlayerState(player_num=2, lives=3),
    ]
    state, _ = _resolve(players, 0)
    assert state == GameState.SAVE_SNAPSHOT_AND_SWITCH
    assert players[0].lives == 2


# 2P, active dies, other still alive → drop to 1P
def test_2p_active_dies_other_alive_drops_to_1p() -> None:
    players = [
        PlayerState(player_num=1, lives=1),
        PlayerState(player_num=2, lives=3),
    ]
    state, updated = _resolve(players, 0)
    assert state == GameState.DROP_TO_1P
    assert updated[0].is_alive is False


# 2P, both dead → game over
def test_2p_both_dead_game_over() -> None:
    players = [
        PlayerState(player_num=1, lives=1),
        PlayerState(player_num=2, lives=0, is_alive=False),
    ]
    state, updated = _resolve(players, 0)
    assert state == GameState.GAME_OVER
    assert updated[0].is_alive is False
