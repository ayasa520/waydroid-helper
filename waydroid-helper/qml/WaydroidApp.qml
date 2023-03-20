import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    anchors.fill: parent

    Control {
        width: 400
        height: 400
        padding: 10
        anchors.horizontalCenter: parent.horizontalCenter

        contentItem: DropArea {
            onDropped: {
                if (drop.hasUrls) {
                    for (var i = 0; i < drop.urls.length; i++) {
                        var path = drop.urls[i].slice(7);
                        App.install(path);
                    }
                }
            }

            Connections {
                function onInstallSuccess(app) {
                    console.log(app + " installed successfully");
                }

                target: App
            }

            Rectangle {
                anchors.fill: parent
                color: "#ebebeb"
                radius: 20

                Text {
                    text: "Drop apk here to install"
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.verticalCenter: parent.verticalCenter
                    font.pointSize: 20
                }

            }

        }

    }

}
