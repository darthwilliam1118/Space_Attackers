"""Resource path helper — works in both dev and PyInstaller bundles."""

import os
import sys


def resource_path(relative: str) -> str:
    """Return absolute path to *relative*, compatible with PyInstaller bundles.

    In a frozen bundle sys._MEIPASS is the temp extraction directory.
    In dev, fall back to the project root (two levels up from this file).
    """
    base: str = getattr(
        sys,
        "_MEIPASS",
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    return os.path.join(base, relative)
