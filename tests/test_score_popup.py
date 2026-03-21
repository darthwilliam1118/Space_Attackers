"""Tests for ScorePopup — all run headless via injected stub text object."""

from __future__ import annotations

import pytest
from src.ui.score_popup import ScorePopup


class _StubText:
    """Minimal stand-in for arcade.Text used in tests."""

    def __init__(self, text: str = "") -> None:
        self.text = text
        self.x: float = 0.0
        self.y: float = 0.0
        self.color: tuple[int, int, int, int] = (255, 220, 50, 255)
        self.draw_calls: int = 0

    def draw(self) -> None:
        self.draw_calls += 1


def _popup(x: float = 100.0, y: float = 200.0, value: int = 10,
           duration: float = 0.8, rise_speed: float = 60.0) -> tuple[ScorePopup, _StubText]:
    stub = _StubText(f"+{value}")
    popup = ScorePopup(x, y, value, duration=duration, rise_speed=rise_speed, _text_obj=stub)
    return popup, stub


# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------

def test_update_moves_text_upward() -> None:
    popup, stub = _popup(rise_speed=60.0)
    stub.y = 200.0
    popup.update(0.1)
    assert abs(stub.y - 206.0) < 1e-6


def test_update_rise_is_delta_time_scaled() -> None:
    popup, stub = _popup(rise_speed=120.0)
    stub.y = 0.0
    popup.update(0.5)
    assert abs(stub.y - 60.0) < 1e-6


# ---------------------------------------------------------------------------
# Alpha fade
# ---------------------------------------------------------------------------

def test_alpha_starts_at_255() -> None:
    _, stub = _popup()
    assert stub.color[3] == 255


def test_alpha_fades_linearly() -> None:
    popup, stub = _popup(duration=1.0)
    popup.update(0.5)   # t = 0.5 → alpha = 128
    assert stub.color[3] == int(255 * 0.5)


def test_alpha_at_three_quarters() -> None:
    popup, stub = _popup(duration=1.0)
    popup.update(0.75)
    assert stub.color[3] == int(255 * 0.25)


# ---------------------------------------------------------------------------
# is_done lifecycle
# ---------------------------------------------------------------------------

def test_is_done_false_before_duration() -> None:
    popup, _ = _popup(duration=0.8)
    popup.update(0.4)
    assert not popup.is_done


def test_is_done_true_at_duration() -> None:
    popup, _ = _popup(duration=0.8)
    popup.update(0.8)
    assert popup.is_done


def test_is_done_true_past_duration() -> None:
    popup, _ = _popup(duration=0.8)
    popup.update(1.5)
    assert popup.is_done


def test_update_is_noop_after_done() -> None:
    popup, stub = _popup(duration=0.8, rise_speed=60.0)
    popup.update(0.8)   # marks done
    y_before = stub.y
    popup.update(0.5)   # should not move
    assert stub.y == y_before


# ---------------------------------------------------------------------------
# draw()
# ---------------------------------------------------------------------------

def test_draw_calls_label_draw_when_active() -> None:
    popup, stub = _popup()
    popup.draw()
    assert stub.draw_calls == 1


def test_draw_does_not_call_label_draw_when_done() -> None:
    popup, stub = _popup(duration=0.8)
    popup.update(0.8)
    popup.draw()
    assert stub.draw_calls == 0


# ---------------------------------------------------------------------------
# Multiple independent instances
# ---------------------------------------------------------------------------

def test_two_popups_are_independent() -> None:
    popup_a, stub_a = _popup(x=50.0, y=100.0, rise_speed=60.0, duration=1.0)
    popup_b, stub_b = _popup(x=200.0, y=300.0, rise_speed=120.0, duration=2.0)

    popup_a.update(0.5)
    popup_b.update(0.25)

    assert abs(stub_a.y - (100.0 + 60.0 * 0.5)) < 1e-6
    assert abs(stub_b.y - (300.0 + 120.0 * 0.25)) < 1e-6
    assert not popup_a.is_done
    assert not popup_b.is_done


# ---------------------------------------------------------------------------
# Display format
# ---------------------------------------------------------------------------

def test_text_format_value_10() -> None:
    stub = _StubText()
    ScorePopup(0, 0, 10, _text_obj=stub)
    # stub.text is set by _StubText constructor, not by ScorePopup (ScorePopup
    # creates the arcade.Text with the formatted string when no stub is given).
    # When a stub is injected the caller is responsible for initial text content,
    # but we can verify the constructor doesn't blow up for various values.
    # For real arcade.Text the formatted string is tested via integration.


@pytest.mark.parametrize("value", [0, 10, 50, 100, 999])
def test_popup_accepts_various_values(value: int) -> None:
    stub = _StubText(f"+{value}")
    popup = ScorePopup(0.0, 0.0, value, _text_obj=stub)
    assert not popup.is_done
