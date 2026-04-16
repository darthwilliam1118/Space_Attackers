"""GameState enum and GameStateManager — drives all screen transitions."""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

from agf.state import BaseGameStateManager

if TYPE_CHECKING:
    import arcade


class GameState(Enum):
    SPLASH = auto()
    MAIN = auto()
    GAME_CONFIG = auto()
    GAME_INIT = auto()
    SET_ACTIVE_PLAYER = auto()
    START_LEVEL = auto()
    RUN_LEVEL = auto()
    LEVEL_COMPLETE = auto()
    PLAYER_KILLED = auto()
    SAVE_SNAPSHOT_AND_SWITCH = auto()
    DROP_TO_1P = auto()
    GAME_OVER = auto()
    SCORE_ENTRY = auto()
    EXIT = auto()


class GameStateManager(BaseGameStateManager):
    """Owns the current GameState and drives Arcade view swaps.

    No rendering happens here — only state bookkeeping and view swaps.
    """

    def __init__(self, window: "arcade.Window") -> None:
        super().__init__(window, GameState.SPLASH)

    # ------------------------------------------------------------------
    # Private — one handler per state
    # ------------------------------------------------------------------

    def _enter_state(self, state: Enum) -> None:
        # Import views here to keep arcade out of the module-level import
        # (tests that import GameState/GameStateManager won't trigger arcade).
        from src.views.game_config_view import GameConfigView
        from src.views.game_over import GameOverView
        from src.views.level_complete import LevelCompleteView
        from src.views.main_menu import MainMenuView
        from src.views.player_killed import PlayerKilledView
        from src.views.run_level import RunLevelView
        from src.views.score_entry import ScoreEntryView
        from src.views.splash import SplashView

        match state:
            case GameState.SPLASH:
                self.window.show_view(SplashView(self))

            case GameState.MAIN:
                self.window.show_view(MainMenuView(self))

            case GameState.GAME_CONFIG:
                self.window.show_view(GameConfigView(self))

            case GameState.GAME_INIT:
                self._handle_game_init()

            case GameState.SET_ACTIVE_PLAYER:
                self._handle_set_active_player()

            case GameState.START_LEVEL:
                self._handle_start_level()

            case GameState.RUN_LEVEL:
                self.window.show_view(RunLevelView(self))

            case GameState.LEVEL_COMPLETE:
                self.window.show_view(LevelCompleteView(self))

            case GameState.PLAYER_KILLED:
                self._save_grid_snapshot()
                self.window.show_view(PlayerKilledView(self))

            case GameState.SAVE_SNAPSHOT_AND_SWITCH:
                self._handle_save_snapshot_and_switch()

            case GameState.DROP_TO_1P:
                self._handle_drop_to_1p()

            case GameState.GAME_OVER:
                self.window.show_view(GameOverView(self))

            case GameState.SCORE_ENTRY:
                self.window.show_view(ScoreEntryView(self))

            case GameState.EXIT:
                import arcade

                arcade.exit()

    # ------------------------------------------------------------------
    # Logic-only state handlers (no view swap)
    # ------------------------------------------------------------------

    def _handle_game_init(self) -> None:
        from agf.player_state import PlayerState

        from src.game_config import GameConfig

        cfg: GameConfig = self.context.get("config") or GameConfig.load()
        num_players: int = self.context.get("num_players", 1)

        self.context["config"] = cfg
        self.context["players"] = [
            PlayerState(player_num=i + 1, lives=cfg.num_lives, current_level=cfg.starting_level)
            for i in range(num_players)
        ]
        self.context["active_player_index"] = 0
        self.transition(GameState.SET_ACTIVE_PLAYER)

    def _handle_set_active_player(self) -> None:
        self.transition(GameState.START_LEVEL)

    def _handle_start_level(self) -> None:
        from agf.spawn_safety import apply_spawn_safety

        from src.levels.level_factory import create_level
        from src.ship_config import ShipConfig

        players: list = self.context.get("players", [])
        idx: int = self.context.get("active_player_index", 0)
        cfg = self.context.get("config")
        w: int = self.window.width
        h: int = self.window.height

        level_number: int = 1
        snapshot: Optional[dict] = None

        if players:
            player = players[idx]
            level_number = player.current_level
            if player.level_snapshot is not None:
                snapshot = player.level_snapshot
                # Apply spawn safety before handing snapshot to factory
                ship_cfg: ShipConfig = cfg.ship if cfg else ShipConfig()
                spawn_y = h * ship_cfg.ship_zone_height_pct / 2.0
                apply_spawn_safety(
                    snapshot,
                    (w / 2.0, spawn_y),
                    cfg.spawn_safe_radius if cfg else 80,
                )

        level = create_level(
            level_number=level_number,
            config=cfg,
            window_width=w,
            window_height=h,
            snapshot=snapshot,
        )

        self.context["current_level"] = level
        self.context.pop("enemy_grid", None)
        self.context.pop("dive_controller", None)
        self.transition(GameState.RUN_LEVEL)

    def _save_grid_snapshot(self) -> None:
        """Snapshot the current level into the active player's level_snapshot.

        Called before PLAYER_KILLED so the level state is preserved across respawns.
        In-flight enemy bullets are discarded — same policy as SAVE_SNAPSHOT_AND_SWITCH.
        """
        from agf.levels.base_level import BaseLevel

        players: list = self.context.get("players", [])
        idx: int = self.context.get("active_player_index", 0)
        level: Optional[BaseLevel] = self.context.get("current_level")

        if players and level is not None:
            snapshot = level.to_snapshot()
            snapshot.pop("projectiles", None)
            players[idx].level_snapshot = snapshot

    def _handle_save_snapshot_and_switch(self) -> None:
        """Serialise level state for the active player, then switch."""
        from agf.levels.base_level import BaseLevel

        players: list = self.context.get("players", [])
        idx: int = self.context.get("active_player_index", 0)
        level: Optional[BaseLevel] = self.context.get("current_level")

        if players and level is not None:
            snapshot = level.to_snapshot()
            snapshot.pop("projectiles", None)  # discard in-flight projectiles
            players[idx].level_snapshot = snapshot

        # Switch to the other player
        other_idx = 1 - idx
        self.context["active_player_index"] = other_idx
        self.transition(GameState.SET_ACTIVE_PLAYER)

    def _handle_drop_to_1p(self) -> None:
        players: list = self.context.get("players", [])
        idx: int = self.context.get("active_player_index", 0)
        if players:
            players[idx].is_alive = False
        other_idx = 1 - idx
        self.context["active_player_index"] = other_idx
        self.transition(GameState.SET_ACTIVE_PLAYER)
