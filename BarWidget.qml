import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui as Ui

// Bar button that opens hyprchess in a terminal, or focuses the window if it is already open.
Ui.BarWidget {
  id: root
  moduleName: "io.github.namelesstherebel.hyprchess"

  // bin/hyprchess runs the game straight from this plugin folder, so nothing else needs installing.
  readonly property string launcher: Qt.resolvedUrl("bin/hyprchess").toString().replace("file://", "")

  function open() {
    Quickshell.execDetached(["omarchy-launch-or-focus-tui", "--app-id=org.omarchy.hyprchess", root.launcher])
  }

  // Lets a keybinding or script open the game without the bar button.
  IpcHandler {
    target: "io.github.namelesstherebel.hyprchess"

    function open(): void {
      root.open()
    }
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  Ui.BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: ""
    tooltipText: "Chess"
    onPressed: root.open()
  }
}
