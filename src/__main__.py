import pyglet
pyglet.options['win32_gdi_font'] = True  # DirectWrite can't find fonts with weight names like "Thin"

from src.game import main

if __name__ == "__main__":
    main()
