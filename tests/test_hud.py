"""Unit tests for HUD and text_utils — no display required."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agf.player_state import PlayerState

from src.ui.hud import _MUTED, _WHITE, HUD

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeText:
    """Minimal arcade.Text stand-in for testing — no OpenGL required."""

    def __init__(self, text: str = "", color: tuple = _WHITE, **kwargs) -> None:
        self.text = text
        self.color = color

    def draw(self) -> None:
        pass


def _fake_factory(**kwargs) -> FakeText:
    return FakeText(**kwargs)


def _hud1p() -> HUD:
    return HUD(800, 600, num_players=1, _text_factory=_fake_factory)


def _hud2p() -> HUD:
    return HUD(800, 600, num_players=2, _text_factory=_fake_factory)


def _player(num: int = 1, score: int = 0, lives: int = 3, level: int = 1) -> PlayerState:
    p = PlayerState(player_num=num, lives=lives, score=score, current_level=level)
    return p


# ---------------------------------------------------------------------------
# 1-player HUD
# ---------------------------------------------------------------------------


class TestHUD1P:
    def test_update_writes_score_on_change(self) -> None:
        hud = _hud1p()
        p = _player(score=0)
        p.score = 500
        hud.update([p], 0, 1)
        assert "500" in hud._score.text

    def test_update_skips_score_when_unchanged(self) -> None:
        hud = _hud1p()
        p = _player(score=100)
        hud.update([p], 0, 1)
        hud._score.text = "TAMPERED"  # simulate external write
        hud.update([p], 0, 1)  # same score — should NOT overwrite
        assert hud._score.text == "TAMPERED"

    def test_update_writes_level_on_change(self) -> None:
        hud = _hud1p()
        p = _player()
        hud.update([p], 0, 3)
        assert "3" in hud._level.text

    def test_update_skips_level_when_unchanged(self) -> None:
        hud = _hud1p()
        p = _player()
        hud.update([p], 0, 2)
        hud._level.text = "TAMPERED"
        hud.update([p], 0, 2)
        assert hud._level.text == "TAMPERED"

    def test_update_tracks_lives_on_change(self) -> None:
        hud = _hud1p()
        p = _player(lives=2)
        hud.update([p], 0, 1)
        assert hud._last_lives[0] == 2

    def test_update_skips_lives_cache_when_unchanged(self) -> None:
        hud = _hud1p()
        p = _player(lives=3)
        hud.update([p], 0, 1)
        assert hud._last_lives[0] == 3
        hud.update([p], 0, 1)  # same lives — cache stays at 3
        assert hud._last_lives[0] == 3

    def test_lives_floor_at_zero(self) -> None:
        hud = _hud1p()
        p = _player(lives=0)
        hud.update([p], 0, 1)
        assert hud._last_lives[0] == 0

    def test_draw_calls_all_text_objects(self) -> None:
        hud = _hud1p()
        for t in hud._texts:
            t.draw = MagicMock()  # type: ignore[method-assign]
        hud.draw()
        for t in hud._texts:
            t.draw.assert_called_once()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# 2-player HUD
# ---------------------------------------------------------------------------


class TestHUD2P:
    def test_active_player_is_white(self) -> None:
        hud = _hud2p()
        p1 = _player(num=1, score=100, lives=3)
        p2 = _player(num=2, score=200, lives=2)
        hud.update([p1, p2], active_player_idx=0, level=1)
        assert hud._p1_score.color == _WHITE
        assert hud._p1_lives.color == _WHITE

    def test_inactive_player_is_muted(self) -> None:
        hud = _hud2p()
        p1 = _player(num=1, score=100, lives=3)
        p2 = _player(num=2, score=200, lives=2)
        hud.update([p1, p2], active_player_idx=0, level=1)
        assert hud._p2_score.color == _MUTED
        assert hud._p2_lives.color == _MUTED

    def test_switch_active_player_updates_colors(self) -> None:
        hud = _hud2p()
        p1 = _player(num=1, score=100, lives=3)
        p2 = _player(num=2, score=200, lives=2)
        hud.update([p1, p2], active_player_idx=0, level=1)
        # Switch to P2 active
        hud.update([p1, p2], active_player_idx=1, level=1)
        assert hud._p2_score.color == _WHITE
        assert hud._p1_score.color == _MUTED

    def test_score_text_contains_player_score(self) -> None:
        hud = _hud2p()
        p1 = _player(num=1, score=1234)
        p2 = _player(num=2, score=5678)
        hud.update([p1, p2], active_player_idx=0, level=1)
        assert "1234" in hud._p1_score.text
        assert "5678" in hud._p2_score.text


# ---------------------------------------------------------------------------
# centered_text helper
# ---------------------------------------------------------------------------


class TestCenteredText:
    def test_anchor_x_is_center(self) -> None:
        with patch("agf.ui.text_utils.arcade.Text") as MockText:
            from agf.ui.text_utils import centered_text

            centered_text("hello", 800, 300)
            _, kwargs = MockText.call_args
            assert kwargs.get("anchor_x") == "center"

    def test_x_is_half_window_width(self) -> None:
        with patch("agf.ui.text_utils.arcade.Text") as MockText:
            from agf.ui.text_utils import centered_text

            centered_text("hello", 800, 300)
            _, kwargs = MockText.call_args
            assert kwargs.get("x") == 400.0

    def test_text_content_passed_through(self) -> None:
        with patch("agf.ui.text_utils.arcade.Text") as MockText:
            from agf.ui.text_utils import centered_text

            centered_text("SPACE ATTACKERS", 800, 300)
            _, kwargs = MockText.call_args
            assert kwargs.get("text") == "SPACE ATTACKERS"
