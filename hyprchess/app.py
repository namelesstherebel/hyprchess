"""The application: config, skins, the shared Stockfish process, and screen routing."""

import json
import os
import shutil
from pathlib import Path

import chess
import chess.engine
from textual.app import App
from textual.theme import Theme

from .game import Game, TimeControl
from .game_screen import GameScreen
from .screens import TitleScreen
from .skins import blend, load_skins, omarchy_colors


def _xdg(variable: str, default: str) -> Path:
    return Path(os.environ.get(variable) or default).expanduser() / "hyprchess"


class ChessApp(App):
    TITLE = "hyprchess"
    ENABLE_COMMAND_PALETTE = False  # keeps the footer for game keys

    def __init__(self, engine_path: str | None = None, skin: str | None = None) -> None:
        super().__init__()
        self.config_dir = _xdg("XDG_CONFIG_HOME", "~/.config")
        self.data_dir = _xdg("XDG_DATA_HOME", "~/.local/share")  # saved PGNs
        self.state_file = _xdg("XDG_STATE_HOME", "~/.local/state") / "resume.json"
        self.config = {"setup": {}}
        try:
            loaded = json.loads((self.config_dir / "config.json").read_text())
            if isinstance(loaded, dict) and isinstance(loaded.get("setup", {}), dict):
                self.config = {"setup": {}, **loaded}
        except (OSError, ValueError):
            pass
        self.skins, self.skin_errors = load_skins(self.config_dir / "skins")
        wanted = skin or self.config.get("skin")
        self.skin_index = next((i for i, s in enumerate(self.skins) if s.name.lower() == str(wanted).lower()), 0)
        if c := omarchy_colors():  # menus and dialogs follow the Omarchy theme too
            bg, fg = c["background"], c["foreground"]
            self.register_theme(
                Theme(
                    name="omarchy",
                    primary=c["accent"],
                    accent=c["accent"],
                    foreground=blend(fg, "#ffffff", 0.35),
                    background=bg,
                    surface=blend(bg, fg, 0.07),
                    panel=blend(bg, fg, 0.14),
                    dark=int(bg[1:3], 16) + int(bg[3:5], 16) + int(bg[5:7], 16) < 384,
                )
            )
            self.theme = "omarchy"
        self.engine_path = engine_path or self.config.get("engine") or shutil.which("stockfish")
        self.engine: chess.engine.UciProtocol | None = None
        self.engine_error = ""

    @property
    def skin(self):
        return self.skins[self.skin_index]

    def cycle_skin(self, delta: int) -> None:
        self.skin_index = (self.skin_index + delta) % len(self.skins)
        self.config["skin"] = self.skin.name
        self.save_config()

    def save_config(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        (self.config_dir / "config.json").write_text(json.dumps(self.config, indent=2) + "\n")

    def remember(self, values: dict) -> None:
        """Keep setup-form choices as the defaults for next time."""
        self.config["setup"].update(values)
        self.save_config()

    async def get_engine(self) -> chess.engine.UciProtocol | None:
        """The running Stockfish, started on first use. None (with engine_error set) if unavailable."""
        if self.engine:
            return self.engine
        if not self.engine_path:
            self.engine_error = "Stockfish was not found. Install it (for example: yay -S stockfish) or pass --engine PATH."
            return None
        try:
            _, self.engine = await chess.engine.popen_uci(self.engine_path)
        except (OSError, chess.engine.EngineError) as e:
            self.engine_error = f"Could not start {self.engine_path}: {e}"
        return self.engine

    # ---- resume file

    def save_state(self, state: dict) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state))

    def clear_state(self) -> None:
        self.state_file.unlink(missing_ok=True)

    def load_state(self) -> dict | None:
        """The unfinished game on disk, rebuilt and checked, or None."""
        try:
            s = json.loads(self.state_file.read_text())
            game = Game(TimeControl(s["base"], s["inc"]))
            for uci in s["moves"]:
                game.board.push_uci(uci)
            if game.clock:
                game.clock = {chess.WHITE: float(s["clock"][0]), chess.BLACK: float(s["clock"][1])}
            if s["mode"] not in ("engine", "local") or game.outcome():
                return None
            human = bool(s["human"]) if s["mode"] == "engine" else None
            return {"game": game, "mode": s["mode"], "human": human, "preset": int(s["preset"]) % 6}
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            return None

    # ---- screens

    def on_mount(self) -> None:
        self.push_screen(TitleScreen())
        for error in self.skin_errors:
            self.notify(error, title="Skin skipped", severity="warning", timeout=10)

    def start_game(self, game: Game, mode: str, **kwargs) -> None:
        self.push_screen(GameScreen(game, mode, **kwargs))

    def resume_game(self) -> None:
        if state := self.load_state():
            self.start_game(state.pop("game"), state.pop("mode"), **state)

    async def on_unmount(self) -> None:
        if self.engine:
            await self.engine.quit()
