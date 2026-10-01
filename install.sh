#!/bin/bash

# Install hyprchess as an app: the `hyprchess` command plus an entry in the app launcher.
# Run it again after pulling to update. Remove with ./install.sh --remove.

set -e

DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
DESKTOP="$HOME/.local/share/applications/hyprchess.desktop"
ICON="$HOME/.local/share/icons/hicolor/scalable/apps/hyprchess.svg"

if uv --version &>/dev/null; then
  UV=(uv)
elif command -v mise &>/dev/null && mise x uv -- uv --version &>/dev/null; then
  UV=(mise x uv -- uv)
else
  echo "hyprchess needs uv (https://docs.astral.sh/uv/). On Omarchy: mise use -g uv" >&2
  exit 1
fi

if [[ ${1:-} == --remove ]]; then
  "${UV[@]}" tool uninstall hyprchess || true
  rm -f "$DESKTOP" "$ICON"
  echo "Removed hyprchess. Saved games and skins are still in ~/.local/share/hyprchess and ~/.config/hyprchess."
  exit 0
fi

"${UV[@]}" tool install --force --quiet "$DIR"
BIN="$(realpath -s "$("${UV[@]}" tool dir --bin)/hyprchess")"

mkdir -p "$(dirname "$DESKTOP")" "$(dirname "$ICON")"
cp "$DIR/icon.svg" "$ICON"
gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" &>/dev/null || true

# One window: launching again focuses the game that is already open (same id the bar widget uses).
if command -v omarchy-launch-or-focus-tui &>/dev/null; then
  EXEC="omarchy-launch-or-focus-tui --app-id=org.omarchy.hyprchess $BIN"
else
  EXEC="xdg-terminal-exec --app-id=org.omarchy.hyprchess -e $BIN"
fi

cat >"$DESKTOP" <<DESKTOP_ENTRY
[Desktop Entry]
Version=1.0
Type=Application
Name=hyprchess
GenericName=Chess
Comment=Terminal chess: Stockfish, online play, clocks and custom skins
Exec=$EXEC
Icon=hyprchess
Terminal=false
Categories=Game;BoardGame;
StartupWMClass=org.omarchy.hyprchess
DESKTOP_ENTRY

echo "Installed. Open hyprchess from the app launcher, or run: hyprchess"
command -v stockfish &>/dev/null || echo "Note: stockfish is not on your PATH; install it to play against the computer."
