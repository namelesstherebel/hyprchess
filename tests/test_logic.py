"""Game rules, clocks, skins and the network handshake, with no UI."""

import asyncio

import chess
import pytest

from hyprchess import net
from hyprchess.game import Game, TimeControl, format_clock
from hyprchess.skins import build_skin, load_skins, parse_sprites

WALNUT = {"board": {"light": "#b89b72", "dark": "#7d5a3c"}, "white": {"body": "#ffffff", "detail": "#999999"},
          "black": {"body": "#000000", "detail": "#666666"}}


def play(game: Game, *ucis: str) -> None:
    for uci in ucis:
        game.push(chess.Move.from_uci(uci))


def test_captures_and_material_include_en_passant_and_promotion():
    game = Game()
    play(game, "e2e4", "a7a6", "e4e5", "d7d5", "e5d6", "a6a5", "d6c7", "a5a4", "c7b8q")  # ep, then promotes with capture
    sans, lost = game.history()
    assert sans[4] == "exd6" and sans[-1] == "cxb8=Q"
    assert lost[chess.BLACK] == [chess.KNIGHT, chess.PAWN, chess.PAWN] and lost[chess.WHITE] == []
    assert Game.material(game.board) == 5 + 8  # two pawns and a knight up, plus pawn became queen


def test_clock_runs_only_after_first_move_adds_increment_and_flags():
    game = Game(TimeControl(60, 2))
    game.tick(5)
    assert game.clock[chess.WHITE] == 60  # not started
    play(game, "e2e4")
    assert game.clock[chess.WHITE] == 62
    game.tick(10)
    assert game.clock[chess.BLACK] == 50 and game.outcome() is None
    game.tick(60)
    assert game.clock[chess.BLACK] == 0 and game.outcome() == ("1-0", "on time")
    game.tick(60)
    assert game.outcome() == ("1-0", "on time")


def test_online_tick_never_flags_the_other_side():
    game = Game(TimeControl(60))
    play(game, "e2e4")
    game.tick(999, only=chess.WHITE)  # it is Black's clock running; White's client must wait for Black's word
    assert game.clock[chess.BLACK] == 0 and game.outcome() is None


def test_undo_redo_and_new_move_clears_redo():
    game = Game()
    play(game, "e2e4", "e7e5")
    game.undo(2)
    assert not game.board.move_stack and game.redo_one() and len(game.board.move_stack) == 2
    game.undo(1)
    play(game, "d7d5")
    assert not game.redo_one()


def test_pgn_round_trip_keeps_moves_and_resignation():
    game = Game(TimeControl(300, 3))
    play(game, "e2e4", "e7e5", "g1f3")
    game.resign(chess.BLACK)
    text = game.pgn("Ann", "Bob")
    assert '[TimeControl "300+3"]' in text and '[Result "1-0"]' in text
    loaded, headers = Game.from_pgn(text)
    assert loaded.board.move_stack == game.board.move_stack and headers["White"] == "Ann"
    assert loaded.outcome() == ("1-0", "resignation")
    with pytest.raises(ValueError):
        Game.from_pgn('[FEN "8/8/8/8/8/8/8/K6k w - - 0 1"]\n[SetUp "1"]\n\n1. Ka2 *')


def test_format_clock():
    assert [format_clock(s) for s in (3725, 600, 61, 9.44, 0)] == ["1:02:05", "10:00", "1:01", "0:09.4", "0:00.0"]


def test_skin_defaults_and_rejections(tmp_path):
    skin = build_skin(WALNUT, "file-name")
    assert skin.name == "file-name" and skin.cursor.startswith("#") and 12 in skin.sprites
    for broken in (
        {**WALNUT, "board": {"light": "red", "dark": "#000000"}},
        {**WALNUT, "white": {"body": "#ffffff"}},
        {**WALNUT, "glyphs": {"king": "KK"}},
        {**WALNUT, "glyphs": {"wizard": "W"}},
        {**WALNUT, "sprites": {"8": "XX\nXX"}},
        {**WALNUT, "sprites": {"9": "X"}},
        {**WALNUT, "board": "nope"},
    ):
        with pytest.raises(ValueError):
            build_skin(broken, "x")
    with pytest.raises(ValueError):
        parse_sprites("")


def test_user_skin_files_load_override_and_report_errors(tmp_path):
    (tmp_path / "ocean.toml").write_text('name = "Ocean"\n[board]\nlight="#9cc4d9"\ndark="#3d6f8a"\n'
                                         '[white]\nbody="#ffffff"\ndetail="#8fa3ad"\n[black]\nbody="#101820"\ndetail="#5f7f91"\n')
    (tmp_path / "walnut2.toml").write_text('name = "Walnut"\n[board]\nlight="#111111"\ndark="#222222"\n'
                                           '[white]\nbody="#ffffff"\ndetail="#8fa3ad"\n[black]\nbody="#101820"\ndetail="#5f7f91"\n')
    (tmp_path / "bad.toml").write_text("this is not toml = = =")
    (tmp_path / "half.toml").write_text('[board]\nlight="#9cc4d9"\n')
    skins, errors = load_skins(tmp_path)
    names = [s.name for s in skins]
    assert "Ocean" in names and names.count("Walnut") == 1
    assert next(s for s in skins if s.name == "Walnut").square[True] == "#111111"
    assert len(errors) == 2 and any("bad.toml" in e for e in errors) and any("half.toml" in e for e in errors)


def test_hello_validation():
    good = {"t": "hello", "v": net.VERSION, "host_color": "white", "base": 300, "inc": 2}
    assert net.valid_hello(good) and net.valid_hello({**good, "base": None})
    for bad in (None, {}, {**good, "v": 99}, {**good, "host_color": "green"}, {**good, "base": 10**9},
                {**good, "base": "300"}, {**good, "inc": -1}, {**good, "inc": True}, {**good, "base": True}):
        assert not net.valid_hello(bad), bad


def test_host_join_exchange_and_garbage_is_dropped():
    async def main():
        peers = []
        server = await net.host(0, peers.append)
        port = server.sockets[0].getsockname()[1]
        guest = await net.join(f"127.0.0.1:{port}")
        await guest.send(t="move", uci="e2e4")
        await asyncio.sleep(0.05)
        assert await peers[0].recv() == {"t": "move", "uci": "e2e4"}
        guest.writer.write(b"not json\n")
        await guest.writer.drain()
        assert await peers[0].recv() is None
        guest.close()
        server.close()
        with pytest.raises(ValueError):
            await net.join("")
        with pytest.raises(OSError):
            await net.join(f"127.0.0.1:{port}", timeout=2)

    asyncio.run(main())
