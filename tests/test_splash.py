from src.views.splash import SplashView


def test_splash_view_constants() -> None:
    """SplashView class-level constants have the correct values."""
    assert SplashView.TITLE_LINE1 == "Space"
    assert SplashView.TITLE_LINE2 == "Attackers!"
    assert SplashView.PROMPT == "Press any key to continue..."
