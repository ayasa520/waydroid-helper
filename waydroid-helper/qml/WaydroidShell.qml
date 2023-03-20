import QMLTermWidget 1.0
import QtQuick 2.15
import QtQuick.Controls 2.15
import Tcp 1.0

Rectangle {
    Action {
        onTriggered: terminal.copyClipboard()
        shortcut: "Ctrl+Shift+C"
    }

    Action {
        onTriggered: terminal.pasteClipboard()
        shortcut: "Ctrl+Shift+V"
    }

    Action {
        onTriggered: searchButton.visible = !searchButton.visible
        shortcut: "Ctrl+F"
    }

    Action {
        onTriggered: {
            console.log('open new terminal window in:' + mainsession.currentDir);
        }
        shortcut: "Ctrl+Shift+T"
    }

    QMLTermWidget {
        id: terminal

        focus: bar.currentIndex === 2
        anchors.fill: parent
        font.family: "monospace"
        font.pointSize: 12
        colorScheme: "cool-retro-term"
        onTerminalUsesMouseChanged: console.log(terminalUsesMouse)
        onTerminalSizeChanged: console.log(terminalSize)
        onActiveFocusChanged: {
            if (activeFocus)
                socket.reconnect_if_need();

        }
        Component.onCompleted: {
            terminal.startTerminalTeletype();
            terminal.sendData2.connect(function(data) {
                socket.on_write(data);
            });
            // socket.readyReadLine.connect(function(data) {
            //     socket.os_write(terminal.getPtySlaveFd(), data);
            // });
            socket.readyRead.connect(function(){
                socket.os_write(terminal.getPtySlaveFd())
            })
        }

        Connections {
            function onClosing() {
                socket.closeEvent();
            }

            target: window
        }

        Tcp {
            // Component.onCompleted: socket.init()

            id: socket
        }

        QMLTermScrollbar {
            terminal: terminal
            width: 20

            Rectangle {
                opacity: 0.4
                anchors.margins: 5
                radius: width * 0.5
                anchors.fill: parent
            }

        }

        session: QMLTermSession {
            id: mainsession

            // initialWorkingDirectory: "$HOME"
            onMatchFound: {
                console.log("found at: %1 %2 %3 %4".arg(startColumn).arg(startLine).arg(endColumn).arg(endLine));
            }
            onNoMatchFound: {
                console.log("not found");
            }
        }

    }

    Button {
        id: searchButton

        text: "Find version"
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        visible: false
        onClicked: mainsession.search("version")
    }
    // Component.onCompleted: terminal.forceActiveFocus();

}
