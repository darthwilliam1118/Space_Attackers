import sys
from pathlib import Path

import pyglet
from agf.paths import set_project_root

set_project_root(Path(__file__).resolve().parent.parent)

if sys.platform == "win32":
    pyglet.options["win32_gdi_font"] = (
        True  # DirectWrite can't find fonts with weight names like "Thin"
    )
    pyglet.options["audio"] = ("xaudio2", "directsound", "openal", "silent")

from src.game import main  # noqa: E402

if __name__ == "__main__":
    main()
