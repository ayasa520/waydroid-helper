import QtQuick 2.15
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

ListView {
    // call the function when the root item is completed

    id: generalConfig

    width: parent.width
    height: contentItem.childrenRect.height
    interactive: false

    Connections {
        function onSessionStatusChanged(status) {
            if (status == 0)
                generalConfig.model.disable(status);
            else if (status == 2)
                generalConfig.model.enable(status);
        }

        target: Status
    }

    Rectangle {
        width: generalConfig.width
        height: generalConfig.height
        border.color: "#e6e6e6"
        color: "#00000000"
        border.width: 1
        radius: 10 // 设置圆角半径
    }

    delegate: Item {
        id: item

        width: generalConfig.width
        height: 60
        Component.onCompleted: {
            if (edit.toLowerCase() === "true" || edit.toLowerCase() === "false") {
                var component = buttonComponent;
                var object = component.createObject(item);
                layout.children.push(object);
            } else {
                var component = textComponent;
                var object = component.createObject(item);
                layout.children.push(object);
            }
        }

        // define a component for Text type
        Component {
            id: textComponent

            TextField {
                id: generalTextFiled

                Layout.alignment: Qt.AlignRight
                text: edit
                enabled: isEnabled
                Layout.rightMargin: 10
                height: 40
                horizontalAlignment: Text.AlignRight
                onAccepted: {
                    // modify the edit role of the current item using setData function
                    // model.setData(model.index, text, Qt.EditRole);
                    if (model.edit != text)
                        model.edit = text;

                }
                onActiveFocusChanged: {
                    if (!activeFocus && (model.edit != text))
                        model.edit = text;

                }

                background: Rectangle {
                    Layout.alignment: Qt.AlignRight
                    implicitWidth: 100
                    // set the color to #ebebeb
                    color: "#ebebeb"
                    // set the border color and width
                    border.width: 0
                    // set the radius to make rounded corners
                    radius: 10
                }

            }

        }

        // define a component for Item type
        Component {
            id: buttonComponent

            DashSwitch {
                id: dashSwitch

                property string str: edit

                Layout.alignment: Qt.AlignRight
                enabled: isEnabled
                checkedColor: "#3584e4"
                checked: edit.toLowerCase() === "true" ? true : false
                onClicked: {
                    if (str === "True")
                        edit = "False";
                    else if (str === "true")
                        edit = "false";
                    else if (str === "False")
                        edit = "True";
                    else if (str === "false")
                        edit = "true";
                }
            }

        }

        Rectangle {
            anchors.fill: parent

            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                onPressed: {
                    parent.color = "#efefef";
                }
                onReleased: {
                    parent.color = "#f9f9f9";
                }
                onEntered: {
                    parent.color = "#f9f9f9";
                }
                onExited: {
                    parent.color = "white";
                }
            }

            RowLayout {
                id: layout

                anchors.fill: parent
                spacing: 2

                Column {
                    Layout.alignment: Qt.AlignLeft
                    Layout.leftMargin: 10
                    Layout.fillWidth: true

                    Text {
                        text: display
                        horizontalAlignment: Text.AlignLeft

                        font {
                            pointSize: 13
                            letterSpacing: 0.8
                        }

                    }

                    Text {
                        width: parent.width
                        text: toolTip
                        horizontalAlignment: Text.AlignLeft
                        color: "#9b9b9b"
                        elide: Text.ElideRight

                        font {
                            pointSize: 11
                            letterSpacing: 0.2
                        }

                    }

                }

            }

        }

        Rectangle {
            width: parent.width
            height: (index === model.count - 1 || index === 0) ? 0 : 1 // omit the line for the last item
            color: "#EDEDED"
        }

    }

}
