"""Whole-app flows driven through the keyboard, against the real Stockfish when it is installed."""

import asyncio
import shutil

import chess
import pytest

from hyprchess.app import ChessApp
from hyprchess.game import Game, TimeControl
from hyprchess.game_screen import GameScreen
from hyprchess.screens import FormScreen, HelpScreen, HostScreen, JoinScreen, MenuScreen, TitleScreen
from textual.widgets import OptionList

needs_engine = pytest.mark.skipif(not shutil.which("stockfish"), reason="stockfish not installed")


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    for var in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
        monkeypatch.setenv(var, str(tmp_path / var))
    return tmp_path


async def until(pilot, condition, timeout=15.0):
    for _ in range(int(timeout / 0.05)):
        if condition():
            return
        await pilot.pause(0.05)
    raise AssertionError("timed out waiting for the app")


async def choose(pilot, app, option_id):
    """Highlight a title/menu option by id and press enter."""
    menu = app.screen.query_one(OptionList)
    menu.highlighted = menu.get_option_index(option_id)
    await pilot.press("enter")
    await pilot.pause()


def move(screen, uci):
    m = chess.Move.from_uci(uci[:4])
    screen.cursor = m.from_square
    screen.action_select()
    screen.cursor = m.to_square
    screen.action_select()


def run(coro):
    asyncio.run(coro)


def test_title_menu_skin_cycle_and_help():
    async def main():
        app = ChessApp()
        async with app.run_test(size=(100, 40)) as pilot:
            assert isinstance(app.screen, TitleScreen)
            menu = app.screen.query_one(OptionList)
            assert menu.get_option("resume").disabled
            first = app.skin.name
            menu.highlighted = menu.get_option_index("skin")
            await pilot.press("right")
            assert app.skin.name != first and app.skin.name in str(menu.get_option("skin").prompt)
            assert ChessApp().skin.name == app.skin.name  # remembered across launches
            await pilot.press("question_mark")
            assert isinstance(app.screen, HelpScreen)
            await pilot.press("x")
            assert isinstance(app.screen, TitleScreen)

    run(main())


def test_local_game_with_clock_promotion_picker_resume_and_save(isolated_home):
    async def main():
        app = ChessApp()
        async with app.run_test(size=(120, 44)) as pilot:
            await choose(pilot, app, "local")
            form = app.screen
            assert isinstance(form, FormScreen)
            while form.rows[0].options[form.rows[0].index] != "Custom":
                await pilot.press("right")
            assert len(form.visible()) == 3  # custom rows appear
            await pilot.press("down", "right", "down", "right", "enter")  # 2 min, 1 sec
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, GameScreen) and screen.game.tc == TimeControl(120, 1)
            for uci in ("e2e4", "d7d5", "e4d5", "c7c6", "d5c6", "a7a6", "c6b7", "a6a5"):
                move(screen, uci)
            assert screen.game.clock[chess.WHITE] > 120  # increments added
            move(screen, "b7a8")
            await pilot.pause()
            assert isinstance(app.screen, MenuScreen)  # promotion picker
            await choose(pilot, app, "n")
            assert screen.game.board.piece_at(chess.A8) == chess.Piece(chess.KNIGHT, chess.WHITE)
            _, lost = screen.game.history()
            assert lost[chess.BLACK] == [chess.ROOK, chess.PAWN, chess.PAWN, chess.PAWN]
            await pilot.press("s")
            await until(pilot, lambda: list((isolated_home / "XDG_DATA_HOME" / "hyprchess").glob("*.pgn")))
            await pilot.press("b")
            await pilot.pause()
            assert isinstance(app.screen, TitleScreen)
            assert not app.screen.query_one(OptionList).get_option("resume").disabled
            await choose(pilot, app, "resume")
            resumed = app.screen
            assert isinstance(resumed, GameScreen) and resumed is not screen
            assert resumed.game.board.fen() == screen.game.board.fen() and resumed.game.clock is not None
            # saved game opens in the viewer and cannot be changed
            await pilot.press("b")
            await pilot.pause()
            await choose(pilot, app, "pgn")
            await pilot.press("enter")
            await pilot.pause()
            viewer = app.screen
            assert isinstance(viewer, GameScreen) and viewer.mode == "viewer" and viewer.view == 0
            await pilot.press("full_stop", "full_stop")
            assert viewer.view == 2 and viewer.shown.fen() == viewer.game.at(2).fen()
            move(viewer, "a8b6")
            assert len(viewer.game.board.move_stack) == 9

    run(main())


def test_flag_fall_ends_game_and_offers_rematch():
    async def main():
        app = ChessApp()
        async with app.run_test(size=(100, 40)) as pilot:
            app.start_game(Game(TimeControl(60)), "local")
            await pilot.pause()
            screen = app.screen
            move(screen, "e2e4")
            screen.game.clock[chess.BLACK] = 0.1
            await until(pilot, lambda: isinstance(app.screen, MenuScreen))
            assert screen.game.outcome() == ("1-0", "on time") and app.load_state() is None
            await choose(pilot, app, "rematch")
            assert isinstance(app.screen, GameScreen) and not app.screen.game.board.move_stack
            assert app.screen.game.clock[chess.BLACK] == 60

    run(main())


@needs_engine
def test_engine_game_undo_redo_hint_and_level():
    async def main():
        app = ChessApp()
        async with app.run_test(size=(120, 44)) as pilot:
            await choose(pilot, app, "engine")
            await until(pilot, lambda: isinstance(app.screen, FormScreen))  # Stockfish starts first
            await pilot.press("right")  # play as Black
            await pilot.press("enter")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, GameScreen) and screen.human == chess.BLACK and screen.flipped
            await until(pilot, lambda: len(screen.game.board.move_stack) == 1 and not screen.thinking)
            move(screen, "e7e5")
            await until(pilot, lambda: len(screen.game.board.move_stack) == 3 and not screen.thinking)
            await pilot.press("i")
            await until(pilot, lambda: len(screen.hint) == 2 and not screen.thinking)
            await pilot.press("u")
            await pilot.pause()
            assert len(screen.game.board.move_stack) == 1
            await pilot.press("r")
            assert len(screen.game.board.move_stack) == 3
            await pilot.press("right_square_bracket")
            assert screen.preset == 3 and "Strong" in screen.names[chess.WHITE]
            assert app.load_state()["preset"] == 3

    run(main())


def test_online_game_between_two_apps_including_illegal_move_and_disconnect():
    async def main():
        host_app, guest_app = ChessApp(), ChessApp()
        async with host_app.run_test(size=(100, 40)) as hp, guest_app.run_test(size=(100, 40)) as gp:
            await choose(hp, host_app, "host")
            await hp.press("enter")  # White, default time
            await until(hp, lambda: isinstance(host_app.screen, HostScreen) and host_app.screen.server)
            await choose(gp, guest_app, "join")
            assert isinstance(guest_app.screen, JoinScreen)
            for ch in "127.0.0.1":
                await gp.press("full_stop" if ch == "." else ch)
            await gp.press("enter")
            await until(gp, lambda: isinstance(guest_app.screen, GameScreen))
            await until(hp, lambda: isinstance(host_app.screen, GameScreen))
            host, guest = host_app.screen, guest_app.screen
            assert (host.human, guest.human) == (chess.WHITE, chess.BLACK) and guest.game.tc == host.game.tc
            assert not guest.can_move and not host.check_action("undo", ())
            move(guest, "e7e5")  # not their turn: ignored
            assert not guest.game.board.move_stack
            move(host, "e2e4")
            await until(gp, lambda: len(guest.game.board.move_stack) == 1)
            move(guest, "e7e5")
            await until(hp, lambda: len(host.game.board.move_stack) == 2)
            assert host.game.board.fen() == guest.game.board.fen()
            # a peer that sends an illegal move is cut off rather than obeyed
            await guest.peer.send(t="move", uci="e5e4")
            await until(hp, lambda: host.game.outcome() is not None)
            assert host.game.outcome()[0] == "*" and len(host.game.board.move_stack) == 2
            await until(gp, lambda: guest.game.outcome() == ("*", "opponent disconnected"))

    run(main())


def test_online_resign_reaches_the_other_side():
    async def main():
        host_app, guest_app = ChessApp(), ChessApp()
        async with host_app.run_test(size=(100, 40)) as hp, guest_app.run_test(size=(100, 40)) as gp:
            await choose(hp, host_app, "host")
            await hp.press("right", "enter")  # host plays Black
            await until(hp, lambda: isinstance(host_app.screen, HostScreen) and host_app.screen.server)
            guest_app.config["join"] = "127.0.0.1"
            await choose(gp, guest_app, "join")
            await gp.press("enter")
            await until(gp, lambda: isinstance(guest_app.screen, GameScreen))
            await until(hp, lambda: isinstance(host_app.screen, GameScreen))
            host, guest = host_app.screen, guest_app.screen
            assert guest.human == chess.WHITE
            move(guest, "d2d4")
            await until(hp, lambda: len(host.game.board.move_stack) == 1)
            await hp.press("x")
            await hp.pause()
            await choose(hp, host_app, "yes")
            await until(gp, lambda: guest.game.outcome() == ("1-0", "resignation"))
            assert host.game.outcome() == ("1-0", "resignation")

    run(main())
