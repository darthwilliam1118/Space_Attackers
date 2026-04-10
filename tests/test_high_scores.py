"""Tests for HighScoreTable — all headless, no display required."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from src.high_scores import HighScoreTable


def _full_table(tmp_path: Path) -> HighScoreTable:
    """Return a table with MAX_ENTRIES entries, scores 100..1000 (step 100)."""
    t = HighScoreTable(tmp_path / "hs.json")
    for i in range(HighScoreTable.MAX_ENTRIES, 0, -1):
        t.add(f"P{i}", i * 100)
    return t


# ---------------------------------------------------------------------------
# qualifies()
# ---------------------------------------------------------------------------


def test_qualifies_true_when_empty(tmp_path: Path) -> None:
    t = HighScoreTable(tmp_path / "hs.json")
    assert t.qualifies(1)


def test_qualifies_true_when_table_not_full(tmp_path: Path) -> None:
    t = HighScoreTable(tmp_path / "hs.json")
    t.add("AAA", 500)
    assert t.qualifies(1)


def test_qualifies_true_when_beats_lowest(tmp_path: Path) -> None:
    t = _full_table(tmp_path)
    lowest = t.entries[-1].score
    assert t.qualifies(lowest + 1)


def test_qualifies_false_when_equal_to_lowest_and_full(tmp_path: Path) -> None:
    t = _full_table(tmp_path)
    lowest = t.entries[-1].score
    assert not t.qualifies(lowest)


def test_qualifies_false_when_below_lowest_and_full(tmp_path: Path) -> None:
    t = _full_table(tmp_path)
    lowest = t.entries[-1].score
    assert not t.qualifies(lowest - 1)


# ---------------------------------------------------------------------------
# add()
# ---------------------------------------------------------------------------


def test_add_returns_rank_1_for_highest(tmp_path: Path) -> None:
    t = HighScoreTable(tmp_path / "hs.json")
    t.add("LOW", 100)
    rank = t.add("TOP", 999)
    assert rank == 1


def test_add_returns_correct_rank(tmp_path: Path) -> None:
    t = HighScoreTable(tmp_path / "hs.json")
    t.add("A", 1000)
    t.add("B", 500)
    rank = t.add("C", 750)  # should be rank 2
    assert rank == 2


def test_add_sorted_descending(tmp_path: Path) -> None:
    t = HighScoreTable(tmp_path / "hs.json")
    t.add("C", 300)
    t.add("A", 100)
    t.add("B", 200)
    scores = [e.score for e in t.entries]
    assert scores == sorted(scores, reverse=True)


def test_add_trims_to_max_entries(tmp_path: Path) -> None:
    t = _full_table(tmp_path)
    t.add("NEW", 9999)
    assert len(t.entries) == HighScoreTable.MAX_ENTRIES


def test_add_drops_lowest_when_full(tmp_path: Path) -> None:
    t = _full_table(tmp_path)
    lowest_before = t.entries[-1].score
    t.add("NEW", lowest_before + 1)
    assert all(e.score > lowest_before for e in t.entries)


def test_add_truncates_name_to_max_len(tmp_path: Path) -> None:
    t = HighScoreTable(tmp_path / "hs.json")
    long_name = "A" * (HighScoreTable.MAX_NAME_LEN + 5)
    t.add(long_name, 100)
    assert len(t.entries[0].name) == HighScoreTable.MAX_NAME_LEN


# ---------------------------------------------------------------------------
# save() / load() round-trip
# ---------------------------------------------------------------------------


def test_save_returns_none_on_success(tmp_path: Path) -> None:
    t = HighScoreTable(tmp_path / "hs.json")
    t.add("AAA", 100)
    assert t.save() is None


def test_save_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "hs.json"
    t = HighScoreTable(path)
    t.add("DARTH", 1500)
    t.add("ACE", 800)
    t.save()

    t2 = HighScoreTable.load(path)
    assert len(t2.entries) == 2
    assert t2.entries[0].name == "DARTH"
    assert t2.entries[0].score == 1500
    assert t2.entries[1].name == "ACE"


def test_save_returns_error_string_on_failure(tmp_path: Path) -> None:
    t = HighScoreTable(tmp_path / "hs.json")
    t.add("AAA", 100)
    with patch.object(Path, "write_text", side_effect=OSError("disk full")):
        result = t.save()
    assert result is not None
    assert "disk full" in result


# ---------------------------------------------------------------------------
# load() error handling
# ---------------------------------------------------------------------------


def test_load_returns_empty_when_file_missing(tmp_path: Path) -> None:
    t = HighScoreTable.load(tmp_path / "nonexistent.json")
    assert t.entries == []


def test_load_returns_empty_on_corrupt_json(tmp_path: Path) -> None:
    path = tmp_path / "hs.json"
    path.write_text("not valid json {{{", encoding="utf-8")
    t = HighScoreTable.load(path)
    assert t.entries == []


def test_load_returns_empty_on_wrong_schema(tmp_path: Path) -> None:
    path = tmp_path / "hs.json"
    path.write_text('[{"bad": "field"}]', encoding="utf-8")
    t = HighScoreTable.load(path)
    assert t.entries == []
