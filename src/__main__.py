import sys

import pyglet

if sys.platform == "win32":
    pyglet.options["win32_gdi_font"] = (
        True  # DirectWrite can't find fonts with weight names like "Thin"
    )

from src.game import main  # noqa: E402

if __name__ == "__main__":
    main()
