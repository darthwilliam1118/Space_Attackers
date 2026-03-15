import arcade


class SplashView(arcade.View):
    """Splash screen: displays title and waits for any key press to exit."""

    TITLE = "Space Attackers!"
    PROMPT = "Press any key to continue..."

    def on_draw(self) -> None:
        self.clear()
        width = self.window.width
        height = self.window.height

        arcade.draw_text(
            self.TITLE,
            width / 2,
            height / 2 + 40,
            arcade.color.YELLOW,
            font_size=64,
            anchor_x="center",
            anchor_y="center",
            bold=True,
        )

        arcade.draw_text(
            self.PROMPT,
            width / 2,
            40,
            arcade.color.WHITE,
            font_size=18,
            anchor_x="center",
            anchor_y="center",
        )

    def on_key_press(self, key: int, modifiers: int) -> None:
        arcade.exit()
