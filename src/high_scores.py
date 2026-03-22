"""HighScoreTable — persistent top-10 leaderboard stored as JSON."""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


def scores_path() -> Path:
    """Return the path to highscores.json.

    When running as a PyInstaller bundle, writes next to the exe so the file
    persists between runs.  In development, writes to the project root.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "highscores.json"
    return Path(__file__).parent.parent / "highscores.json"


@dataclass
class HighScoreEntry:
    name: str
    score: int
    date: str  # ISO-8601 "YYYY-MM-DD"


class HighScoreTable:
    """Sorted (descending) list of up to MAX_ENTRIES high scores."""

    MAX_ENTRIES: int = 10
    MAX_NAME_LEN: int = 10

    def __init__(self, path: Path) -> None:
        self._path = path
        self._entries: list[HighScoreEntry] = []

    # ------------------------------------------------------------------
    # Class methods
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path) -> "HighScoreTable":
        """Load from *path*.  Returns an empty table on any read/parse error."""
        table = cls(path)
        if not path.exists():
            return table
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            table._entries = [
                HighScoreEntry(
                    name=str(e["name"]),
                    score=int(e["score"]),
                    date=str(e.get("date", "")),
                )
                for e in raw
            ]
            table._entries.sort(key=lambda e: e.score, reverse=True)
            table._entries = table._entries[: cls.MAX_ENTRIES]
        except Exception as exc:
            log.warning("Could not load high scores from %s: %s", path, exc)
            table._entries = []
        return table

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def qualifies(self, score: int) -> bool:
        """True if *score* would enter the top MAX_ENTRIES."""
        if len(self._entries) < self.MAX_ENTRIES:
            return True
        return score > self._entries[-1].score

    def add(self, name: str, score: int) -> int:
        """Insert entry, keep sorted descending, trim to MAX_ENTRIES.

        Returns the 1-based rank of the new entry.
        """
        entry = HighScoreEntry(
            name=name[: self.MAX_NAME_LEN],
            score=score,
            date=date.today().isoformat(),
        )
        self._entries.append(entry)
        self._entries.sort(key=lambda e: e.score, reverse=True)
        self._entries = self._entries[: self.MAX_ENTRIES]
        return self._entries.index(entry) + 1

    def save(self) -> Optional[str]:
        """Write table to disk.

        Returns None on success, or an error message string on failure.
        """
        try:
            data = json.dumps(
                [asdict(e) for e in self._entries],
                indent=2,
                ensure_ascii=False,
            )
            self._path.write_text(data, encoding="utf-8")
            return None
        except Exception as exc:
            return str(exc)

    @property
    def entries(self) -> list[HighScoreEntry]:
        return list(self._entries)
