"""Menus and dialogs: title screen, setup form, pop-up menus, help, online host/join."""

import asyncio
import random
from dataclasses import dataclass
from typing import Callable

import chess
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Footer, Input, OptionList, Static
from textual.widgets.option_list import Option

from . import net
from .board import sprite_rows
from .game import CUSTOM_INCREMENTS, CUSTOM_MINUTES, PRESETS, TIME_PRESETS, Game, TimeControl
from .skins import PIECES

HELP = """\
[b]Moving[/b]
  arrows / hjkl   move the cursor
  enter / space   pick up a piece, then drop it       esc  put it back
  mouse click     same as cursor + enter
  Blue squares are the legal moves for the piece you picked up.

[b]Game[/b]
  u  undo your last move      r  redo it        i  hint from Stockfish
  \\[  easier    ]  harder      x  resign         b  back to the menu
  Undo, redo, hints and difficulty are off in online games.

[b]View[/b]
  ,  step back    .  step forward    Home  start    End  live
  f  flip the board     c  next skin     t  show or hide the side panel
  s  save the game as PGN
  You cannot move pieces while reviewing an earlier position.

[b]Clocks[/b]
  Both clocks start once White has moved. The increment, if any, is
  added after each move. A clock at zero loses the game.

[b]Castling[/b]  (written O-O kingside, O-O-O queenside)
  Pick up the king and drop it two squares toward a rook; the rook
  jumps over to the king's other side. Allowed only if:
    - neither the king nor that rook has moved yet
    - every square between them is empty
    - the king is not in check, and does not cross or land on
      a square an enemy piece attacks

[b]En passant[/b]
  When an enemy pawn moves two squares from its start and lands
  right beside your pawn, you may capture it as if it had moved
  only one: your pawn goes diagonally to the empty square behind
  it and the enemy pawn is removed. Only on the very next move.

[b]Promotion[/b]
  A pawn reaching the last rank asks which piece it becomes.

[dim]Arrows scroll, any other key closes[/dim]"""

DIALOG_CSS = """
    {name} {{ align: center middle; }}
    {name} > Vertical, {name} > VerticalScroll {{
        width: {width}; max-width: 100%; height: auto; max-height: 100%;
        padding: 1 2; border: round $accent; background: $surface;
    }}
    {name} OptionList, {name} OptionList:focus {{
        height: auto; max-height: 16; border: none; background: $surface; padding: 0;
    }}
    {name} .title {{ text-style: bold; margin-bottom: 1; }}
    {name} .body {{ margin-bottom: 1; }}
"""


class HelpScreen(ModalScreen):
    DEFAULT_CSS = DIALOG_CSS.format(name="HelpScreen", width=76)

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(HELP)

    def on_key(self, event) -> None:
        if event.key in ("up", "down", "pageup", "pagedown"):
            return  # left to the scroll container
        event.stop()
        self.dismiss()

    def on_click(self) -> None:
        self.dismiss()


class MenuScreen(ModalScreen[str | None]):
    """A titled pop-up list. Dismisses with the chosen option id, or None on Esc."""

    DEFAULT_CSS = DIALOG_CSS.format(name="MenuScreen", width=46)
    BINDINGS = [Binding("j", "move(1)", show=False), Binding("k", "move(-1)", show=False)]

    def __init__(self, title: str, options: list[tuple[str, str]], body: str = "", escape: bool = True) -> None:
        super().__init__()
        self.heading, self.options, self.body, self.escape = title, options, body, escape

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self.heading, classes="title")
            if self.body:
                yield Static(self.body, classes="body")
            yield OptionList(*(Option(label, id=key) for key, label in self.options))

    def action_move(self, delta: int) -> None:
        menu = self.query_one(OptionList)
        menu.action_cursor_down() if delta > 0 else menu.action_cursor_up()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)

    def on_key(self, event) -> None:
        if event.key == "escape" and self.escape:
            event.stop()
            self.dismiss(None)


@dataclass
class Row:
    key: str
    label: str
    options: list[str]
    index: int = 0
    show: Callable[[dict], bool] | None = None  # given the current values, is this row visible?


class FormScreen(ModalScreen[dict | None]):
    """Setup form: up/down picks a row, left/right changes it. Dismisses with {key: option index}."""

    DEFAULT_CSS = DIALOG_CSS.format(name="FormScreen", width=52)
    BINDINGS = [
        Binding("up,k", "row(-1)", show=False),
        Binding("down,j", "row(1)", show=False),
        Binding("left,h", "change(-1)", show=False),
        Binding("right,l", "change(1)", show=False),
        Binding("enter", "submit", show=False),
        Binding("escape", "cancel", show=False),
    ]

    def __init__(self, title: str, rows: list[Row], submit: str = "start") -> None:
        super().__init__()
        self.heading, self.rows, self.submit, self.cursor = title, rows, submit, 0

    def values(self) -> dict[str, int]:
        return {r.key: r.index for r in self.rows}

    def visible(self) -> list[Row]:
        values = self.values()
        return [r for r in self.rows if r.show is None or r.show(values)]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self.heading, classes="title")
            yield Static(id="rows")

    def on_mount(self) -> None:
        self._draw()

    def _draw(self) -> None:
        out = Text()
        rows = self.visible()
        self.cursor = min(self.cursor, len(rows) - 1)
        for i, row in enumerate(rows):
            active = i == self.cursor
            out.append("▸ " if active else "  ", "bold")
            out.append(f"{row.label:<12}", "bold" if active else "")
            out.append(f"‹ {row.options[row.index]} ›\n", "reverse" if active else "")
        out.append(f"\n←/→ change · Enter {self.submit} · Esc back", "dim")
        self.query_one("#rows", Static).update(out)

    def action_row(self, delta: int) -> None:
        self.cursor = (self.cursor + delta) % len(self.visible())
        self._draw()

    def action_change(self, delta: int) -> None:
        row = self.visible()[self.cursor]
        row.index = (row.index + delta) % len(row.options)
        self._draw()

    def action_submit(self) -> None:
        self.dismiss(self.values())

    def action_cancel(self) -> None:
        self.dismiss(None)


def time_rows(saved: dict) -> list[Row]:
    def custom(values: dict) -> bool:
        return values["time"] == len(TIME_PRESETS)

    def at(key: str, options: list) -> int:
        return saved.get(key, 0) if isinstance(saved.get(key), int) and 0 <= saved[key] < len(options) else 0

    names = [name for name, _ in TIME_PRESETS] + ["Custom"]
    minutes, incs = [f"{m} min" for m in CUSTOM_MINUTES], [f"{s} sec" for s in CUSTOM_INCREMENTS]
    return [
        Row("time", "Time", names, at("time", names)),
        Row("minutes", "Per side", minutes, at("minutes", minutes), custom),
        Row("inc", "Increment", incs, at("inc", incs), custom),
    ]


def time_control(values: dict) -> TimeControl:
    if values["time"] < len(TIME_PRESETS):
        return TIME_PRESETS[values["time"]][1]
    return TimeControl(CUSTOM_MINUTES[values["minutes"]] * 60, CUSTOM_INCREMENTS[values["inc"]])


def pick_side(index: int) -> chess.Color:
    return [chess.WHITE, chess.BLACK, random.choice([chess.WHITE, chess.BLACK])][index]


SIDES = ["White", "Black", "Random"]


class JoinScreen(ModalScreen[str | None]):
    DEFAULT_CSS = DIALOG_CSS.format(name="JoinScreen", width=52)

    def __init__(self, last: str) -> None:
        super().__init__()
        self.last = last

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Join an online game", classes="title")
            yield Static("Address your opponent's Host screen shows:", classes="body")
            yield Input(value=self.last, placeholder=f"192.168.1.20 or host:{net.PORT}")
            yield Static("\n[dim]Enter connect · Esc back[/dim]")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            event.stop()
            self.dismiss(None)


class HostScreen(ModalScreen["net.Peer | None"]):
    """Listens for one opponent. Dismisses with the connected Peer, or None on Esc."""

    DEFAULT_CSS = DIALOG_CSS.format(name="HostScreen", width=56)

    def __init__(self, port: int = net.PORT) -> None:
        super().__init__()
        self.port, self.server = port, None

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Hosting an online game", classes="title")
            yield Static("Starting…", id="status")
            yield Static("\n[dim]Esc cancel[/dim]")

    async def on_mount(self) -> None:
        status = self.query_one("#status", Static)
        try:
            self.server = await net.host(self.port, self._connected)
        except OSError as e:
            status.update(f"Could not listen on port {self.port}: {e.strerror or e}")
            return
        addresses = "\n".join(f"  {a}:{self.port}" for a in net.local_addresses())
        status.update(
            f"Waiting for an opponent. Tell them to choose Join and enter:\n\n{addresses}\n\n"
            "Works on the same network or over a VPN such as Tailscale.\n"
            f"Across the internet, forward TCP port {self.port} to this machine."
        )

    def _connected(self, peer: net.Peer) -> None:
        if self.server is None:  # second connection, or we already left
            peer.close()
            return
        self._stop()
        self.dismiss(peer)

    def _stop(self) -> None:
        if self.server:
            self.server.close()
            self.server = None

    def on_key(self, event) -> None:
        if event.key == "escape":
            event.stop()
            self._stop()
            self.dismiss(None)


class TitleScreen(Screen):
    DEFAULT_CSS = """
    TitleScreen { align: center middle; }
    TitleScreen Center { height: auto; }
    TitleScreen #art { width: auto; height: auto; }
    TitleScreen #name { width: auto; text-style: bold; margin-top: 1; }
    TitleScreen #tag { width: auto; color: $text-muted; margin-bottom: 1; }
    TitleScreen OptionList, TitleScreen OptionList:focus {
        width: 44; max-width: 100%; height: auto; border: round $accent; padding: 0 1; background: $surface;
    }
    """
    BINDINGS = [
        Binding("j", "move(1)", show=False),
        Binding("k", "move(-1)", show=False),
        Binding("left,h", "skin(-1)", show=False),
        Binding("right,l", "skin(1)", show=False),
        Binding("question_mark", "help", "Help"),
        Binding("q", "app.quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Center(Static(id="art"))
        yield Center(Static("H Y P R C H E S S", id="name"))
        yield Center(Static("Chess for Omarchy", id="tag"))
        yield Center(self._menu())
        yield Footer()

    def _menu(self) -> OptionList:
        return OptionList(
            Option("Play Stockfish", id="engine"),
            Option("Two players, this keyboard", id="local"),
            Option("Online: host a game", id="host"),
            Option("Online: join a game", id="join"),
            Option("Resume last game", id="resume"),
            Option("Open a saved game", id="pgn"),
            Option("", id="skin"),
            Option("Help", id="help"),
            Option("Quit", id="quit"),
        )

    def on_mount(self) -> None:
        self._sync()

    def on_screen_resume(self) -> None:
        self._sync()

    def on_resize(self) -> None:
        self._sync()

    def _sync(self) -> None:
        """Redraw everything that depends on the skin, the window size or saved state."""
        app, menu = self.app, self.query_one(OptionList)
        w, h = self.size
        size = 12 if (w >= 84 and h >= 28) else 8 if (w >= 58 and h >= 22) else 0
        art = self.query_one("#art", Static)
        art.display = bool(size)
        if size:
            pieces = [sprite_rows(app.skin, pt, chess.WHITE, size) for pt in PIECES]
            art.update(Text("\n").join(Text(" ").join(rows) for rows in zip(*pieces)))
        self.query_one("#tag").display = h >= 16
        menu.replace_option_prompt("skin", f"Skin: ‹ {app.skin.name} ›")
        menu.enable_option("resume") if app.load_state() else menu.disable_option("resume")

    def action_move(self, delta: int) -> None:
        menu = self.query_one(OptionList)
        menu.action_cursor_down() if delta > 0 else menu.action_cursor_up()

    def action_skin(self, delta: int) -> None:
        menu = self.query_one(OptionList)
        if menu.highlighted is not None and menu.get_option_at_index(menu.highlighted).id == "skin":
            self.app.cycle_skin(delta)
            self._sync()

    def action_help(self) -> None:
        self.app.push_screen(HelpScreen())

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        choice = event.option.id
        if choice == "skin":
            self.app.cycle_skin(1)
            self._sync()
        elif choice == "help":
            self.action_help()
        elif choice == "quit":
            self.app.exit()
        else:
            getattr(self, f"flow_{choice}")()

    # Each flow runs as a worker so it can wait on dialogs one after another.

    @work
    async def flow_engine(self) -> None:
        app = self.app
        if not await app.get_engine():
            app.notify(app.engine_error, title="Stockfish unavailable", severity="error", timeout=10)
            return
        saved = app.config["setup"]
        levels = [name for name, _, _ in PRESETS]
        rows = [
            Row("side", "Play as", SIDES, saved.get("side", 0) % 3),
            Row("level", "Difficulty", levels, saved.get("level", 2) % len(levels)),
            *time_rows(saved),
        ]
        if (values := await app.push_screen_wait(FormScreen("Play Stockfish", rows))) is None:
            return
        app.remember(values)
        app.start_game(Game(time_control(values)), "engine", human=pick_side(values["side"]), preset=values["level"])

    @work
    async def flow_local(self) -> None:
        app = self.app
        if (values := await app.push_screen_wait(FormScreen("Two players", time_rows(app.config["setup"])))) is None:
            return
        app.remember(values)
        app.start_game(Game(time_control(values)), "local")

    @work
    async def flow_host(self) -> None:
        app = self.app
        rows = [Row("side", "Play as", SIDES, app.config["setup"].get("side", 0) % 3), *time_rows(app.config["setup"])]
        if (values := await app.push_screen_wait(FormScreen("Host an online game", rows, submit="host"))) is None:
            return
        app.remember(values)
        if (peer := await app.push_screen_wait(HostScreen())) is None:
            return
        me, tc = pick_side(values["side"]), time_control(values)
        await peer.send(t="hello", v=net.VERSION, host_color="white" if me else "black", base=tc.base, inc=tc.inc)
        app.start_game(Game(tc), "online", human=me, peer=peer)

    @work
    async def flow_join(self) -> None:
        app = self.app
        if (address := await app.push_screen_wait(JoinScreen(app.config.get("join", "")))) is None:
            return
        app.config["join"] = address
        app.save_config()
        try:
            peer = await net.join(address)
            hello = await asyncio.wait_for(peer.recv(), 8)
        except (OSError, ValueError, TimeoutError) as e:
            app.notify(f"Could not connect to {address}: {e or 'timed out'}", severity="error", timeout=8)
            return
        if not net.valid_hello(hello):
            peer.close()
            app.notify("That host is not running a compatible hyprchess.", severity="error", timeout=8)
            return
        me = chess.BLACK if hello["host_color"] == "white" else chess.WHITE
        app.start_game(Game(TimeControl(hello["base"], hello["inc"])), "online", human=me, peer=peer)

    @work
    async def flow_resume(self) -> None:
        self.app.resume_game()

    @work
    async def flow_pgn(self) -> None:
        app = self.app
        files = sorted(app.data_dir.glob("*.pgn"), reverse=True)[:30]
        if not files:
            app.notify(f"No saved games yet. Press s during a game to save one to {app.data_dir}")
            return
        options = [(f.name, f.stem) for f in files]
        if (name := await app.push_screen_wait(MenuScreen("Open a saved game", options))) is None:
            return
        try:
            game, headers = Game.from_pgn((app.data_dir / name).read_text())
        except (OSError, ValueError) as e:
            app.notify(f"Could not open {name}: {e}", severity="error")
            return
        names = {chess.WHITE: headers.get("White", "White"), chess.BLACK: headers.get("Black", "Black")}
        app.start_game(game, "viewer", names=names)
