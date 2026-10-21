import QtQuick
import QtQuick.Shapes

Item {
    id: avatar
    property color tint: theme.accent
    property bool thinking: false
    property bool recording: false
    property bool animate: true
    width: 42; height: 48
    Shape {
        anchors.fill: parent
        ShapePath {
            strokeWidth: 1.4; strokeColor: Qt.lighter(avatar.tint, 1.35); fillColor: avatar.tint
            startX: 7; startY: 7
            PathQuad { x: 11; y: 5; controlX: 6; controlY: 1 }
            PathLine { x: 37; y: 27 }
            PathQuad { x: 35; y: 34; controlX: 43; controlY: 33 }
            PathLine { x: 24; y: 34 }
            PathLine { x: 17; y: 43 }
            PathQuad { x: 11; y: 41; controlX: 12; controlY: 48 }
            PathLine { x: 7; y: 7 }
        }
    }
    Row {
        x: 15; y: 22; spacing: 5
        Rectangle { width: 3.4; height: avatar.recording?7:4.5; radius: 2; color: "#18211c" }
        Rectangle { width: 3.4; height: avatar.recording?7:4.5; radius: 2; color: "#18211c" }
        SequentialAnimation on opacity {
            running: avatar.animate; loops: Animation.Infinite
            PauseAnimation { duration: 4200 }
            NumberAnimation { to: 0.1; duration: 80 }
            NumberAnimation { to: 1; duration: 110 }
        }
    }
    SequentialAnimation on rotation {
        running: avatar.thinking && avatar.animate; loops: Animation.Infinite
        NumberAnimation { to: -8; duration: 600; easing.type: Easing.InOutSine }
        NumberAnimation { to: 6; duration: 600; easing.type: Easing.InOutSine }
    }
}
