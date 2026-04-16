"""Thin re-export of agf.events.GameEvent.

Kept so existing call sites continue to work.  New code should import
``GameEvent`` from ``agf.events`` directly.
"""

from __future__ import annotations

from agf.events import GameEvent

__all__ = ["GameEvent"]
