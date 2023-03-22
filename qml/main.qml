import QtLocation 5.6
import QtPositioning 5.6
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15
import QtQuick.Shapes 1.15
import QtQuick.Window 2.15

Window {
    id: window

    width: 800
    height: 600
    flags: Qt.Window
    title: qsTr("WayDroid Helper")
    minimumWidth: 800
    minimumHeight: 600
    Component.onCompleted: {
        Status.get_state();
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        TabBar {
            id: bar

            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            z: 1
            contentHeight: 30

            TabButton {
                // Material.theme: Material.Light

                // text: qsTr("Config")
                font.pointSize: 12
                font.family: "sans"

                Text {
                    text: qsTr("Config")
                    color: "black"
                    anchors.centerIn: parent
                }

                background: Rectangle {
                    color: bar.currentIndex == 0 ? "#d8d8d8" : "#ebebeb"
                }

            }

            TabButton {
                font.pointSize: 12
                font.family: "sans"

                Text {
                    text: qsTr("Application")
                    color: "black"
                    anchors.centerIn: parent
                }

                background: Rectangle {
                    color: bar.currentIndex == 1 ? "#d8d8d8" : "#ebebeb"
                }

            }

            TabButton {
                font.pointSize: 12
                font.family: "sans"

                Text {
                    text: qsTr("Shell")
                    color: "black"
                    anchors.centerIn: parent
                }

                background: Rectangle {
                    color: bar.currentIndex == 2 ? "#d8d8d8" : "#ebebeb"
                }

            }

            background: Rectangle {
                color: "#ebebeb"
            }

        }

        StackLayout {
            id: layout

            clip: true
            Layout.fillHeight: true
            currentIndex: bar.currentIndex

            Rectangle {
                id: rect1

                ScrollView {
                    id: scrollView

                    anchors.fill: parent
                    leftPadding: 15
                    rightPadding: 15
                    bottomPadding: 10
                    topPadding: 10

                    Column {
                        spacing: 10
                        width: scrollView.width - 30

                        Text {
                            font.weight: Font.Medium
                            text: "WayDroid Props"
                        }

                        GeneralConfig {
                            model: GeneralCfgModel
                        }

                        Text {
                            font.weight: Font.Medium
                            text: "WayDroid Base Props"
                        }

                        GeneralConfig {
                            model: BasePropModel
                        }

                    }

                }

            }

            Rectangle {
                id: rect2

                WaydroidApp {
                }

            }

            Rectangle {
                id: rect3

                WaydroidShell {
                    anchors.fill: parent
                }

            }

        }

        Rectangle {
            Layout.fillWidth: true
            height: 30
            color: "#fafafa"
            clip: true // clip the children

            Text {
                id: statusText

                leftPadding: 10
                width: 20
                anchors.verticalCenter: parent.verticalCenter
                text: " Stopped"
                color: "#756f5c"

                Connections {
                    function onSessionStatusChanged(status) {
                        if (status === 0) {
                            statusText.text = " Stopped";
                            statusText.color = "#756f5c";
                        } else if (status === 1) {
                            statusText.text = " Starting";
                            statusText.color = "#b9a43e";
                        } else if (status === 2) {
                            statusText.text = " Running";
                            statusText.color = "#107c10";
                        }
                    }

                    target: Status
                }

            }

        }

    }

}
