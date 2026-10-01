import argparse
import sys

from . import __version__
from .app import ChessApp


def main() -> None:
    parser = argparse.ArgumentParser(prog="hyprchess", description="Terminal chess for Omarchy.")
    parser.add_argument("-e", "--engine", metavar="PATH", help="UCI engine to play against (default: stockfish on PATH)")
    parser.add_argument("-s", "--skin", metavar="NAME", help="skin to start with")
    parser.add_argument("--skins-dir", action="store_true", help="print the folder custom skins go in, then exit")
    parser.add_argument("--version", action="version", version=f"hyprchess {__version__}")
    args = parser.parse_args()
    app = ChessApp(engine_path=args.engine, skin=args.skin)
    if args.skins_dir:
        print(app.config_dir / "skins")
        return
    sys.stdout.write("\x1b]2;hyprchess\x07")  # terminal window title
    sys.stdout.flush()
    app.run()


if __name__ == "__main__":
    main()
