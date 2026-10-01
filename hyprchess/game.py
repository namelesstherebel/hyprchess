"""Game state with no UI: board, clocks, undo/redo, captured material, PGN."""

import io
from dataclasses import dataclass
from datetime import datetime

import chess
import chess.pgn

VALUE = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}


@dataclass(frozen=True)
class TimeControl:
    base: int | None  # seconds per side, None = no clock
    inc: int = 0  # seconds added after each move

    @property
    def label(self) -> str:
        if self.base is None:
            return "No clock"
        minutes = self.base // 60 if self.base % 60 == 0 else round(self.base / 60, 1)
        return f"{minutes}+{self.inc}"


# (name, time control); the last entry is filled in from the custom rows of the setup form
TIME_PRESETS = [
    ("Bullet 1+0", TimeControl(60)),
    ("Blitz 3+2", TimeControl(180, 2)),
    ("Blitz 5+0", TimeControl(300)),
    ("Rapid 10+0", TimeControl(600)),
    ("Rapid 15+10", TimeControl(900, 10)),
    ("Classical 30+20", TimeControl(1800, 20)),
    ("No clock", TimeControl(None)),
]
CUSTOM_MINUTES = [1, 2, 3, 5, 10, 15, 20, 30, 45, 60, 90]
CUSTOM_INCREMENTS = [0, 1, 2, 3, 5, 10, 15, 30]


# (name, Stockfish options, search limit). Options apply only for that move.
PRESETS = [
    ("Beginner", {"Skill Level": 0}, {"depth": 1}),
    ("Casual", {"Skill Level": 3}, {"depth": 3}),
    ("Club 1500", {"UCI_LimitStrength": True, "UCI_Elo": 1500}, {"time": 0.3}),
    ("Strong 1900", {"UCI_LimitStrength": True, "UCI_Elo": 1900}, {"time": 0.5}),
    ("Expert 2300", {"UCI_LimitStrength": True, "UCI_Elo": 2300}, {"time": 0.8}),
    ("Maximum", {}, {"time": 1.5}),
]


def format_clock(seconds: float) -> str:
    if seconds < 10:
        return f"0:{seconds:04.1f}"
    seconds = int(seconds)
    hours, rest = divmod(seconds, 3600)
    return f"{hours}:{rest // 60:02}:{rest % 60:02}" if hours else f"{rest // 60}:{rest % 60:02}"


class Game:
    def __init__(self, tc: TimeControl = TimeControl(None)) -> None:
        self.board = chess.Board()
        self.tc = tc
        self.clock = None if tc.base is None else {chess.WHITE: float(tc.base), chess.BLACK: float(tc.base)}
        self.redo: list[list[chess.Move]] = []  # undone move groups; any new move clears it
        self.ended: tuple[str, str] | None = None  # (result, reason) for endings the board can't see

    def push(self, move: chess.Move) -> None:
        if self.clock:
            self.clock[self.board.turn] += self.tc.inc
        self.board.push(move)
        self.redo.clear()

    def undo(self, plies: int) -> None:
        undone = [self.board.pop() for _ in range(min(plies, len(self.board.move_stack)))]
        if undone:
            self.redo.append(undone)

    def redo_one(self) -> bool:
        if not self.redo:
            return False
        for move in reversed(self.redo.pop()):
            self.board.push(move)
        return True

    def tick(self, dt: float, only: chess.Color | None = None) -> None:
        """Run the clock of the side to move. Clocks start once White has moved.

        With `only` set (online play), just that side's flag can fall here; the
        other side reports its own flag over the network.
        """
        if not self.clock or self.outcome() or not self.board.move_stack:
            return
        side = self.board.turn
        self.clock[side] = max(self.clock[side] - dt, 0.0)
        if self.clock[side] == 0 and only in (None, side):
            self.end("0-1" if side == chess.WHITE else "1-0", "on time")

    def end(self, result: str, reason: str) -> None:
        if not self.outcome():
            self.ended = (result, reason)

    def resign(self, side: chess.Color) -> None:
        self.end("0-1" if side == chess.WHITE else "1-0", "resignation")

    def outcome(self) -> tuple[str, str] | None:
        """(result, reason) once the game is over, else None."""
        if self.ended:
            return self.ended
        if o := self.board.outcome(claim_draw=True):
            return o.result(), o.termination.name.replace("_", " ").lower()
        return None

    def history(self) -> tuple[list[str], dict[chess.Color, list[int]]]:
        """SAN for every move, and the piece types each colour has lost to captures."""
        replay, sans = chess.Board(), []
        lost: dict[chess.Color, list[int]] = {chess.WHITE: [], chess.BLACK: []}
        for move in self.board.move_stack:
            if replay.is_capture(move):
                victim = chess.PAWN if replay.is_en_passant(move) else replay.piece_type_at(move.to_square)
                lost[not replay.turn].append(victim)
            sans.append(replay.san(move))
            replay.push(move)
        for pieces in lost.values():
            pieces.sort(key=VALUE.get, reverse=True)
        return sans, lost

    def at(self, ply: int) -> chess.Board:
        """The position after `ply` moves."""
        board = chess.Board()
        for move in self.board.move_stack[:ply]:
            board.push(move)
        return board

    @staticmethod
    def material(board: chess.Board) -> int:
        """White's material minus Black's, in pawns."""
        return sum(VALUE[p.piece_type] * (1 if p.color else -1) for p in board.piece_map().values())

    def pgn(self, white: str, black: str) -> str:
        game = chess.pgn.Game.from_board(self.board)
        outcome = self.outcome()
        game.headers.update(
            Event="hyprchess",
            Date=f"{datetime.now():%Y.%m.%d}",
            White=white,
            Black=black,
            Result=outcome[0] if outcome else "*",
            TimeControl="-" if self.tc.base is None else f"{self.tc.base}+{self.tc.inc}",
        )
        if outcome:
            game.headers["Termination"] = outcome[1]
        return f"{game}\n"

    @classmethod
    def from_pgn(cls, text: str) -> tuple["Game", dict[str, str]]:
        """First game of a PGN text and its headers. Raises ValueError if it has no legal mainline."""
        parsed = chess.pgn.read_game(io.StringIO(text))
        if parsed is None or parsed.errors or parsed.board().fen() != chess.STARTING_FEN:
            raise ValueError("not a standard game from the starting position")
        game = cls()
        for move in parsed.mainline_moves():
            game.board.push(move)
        headers = dict(parsed.headers)
        if not game.board.outcome(claim_draw=True) and headers.get("Result") in ("1-0", "0-1", "1/2-1/2"):
            game.ended = (headers["Result"], headers.get("Termination", "game over"))
        return game, headers
