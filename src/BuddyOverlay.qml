import QtQuick
import QtQuick.Controls

Item {
    id: surface
    property real originX: 0
    property real originY: 0
    property point destination: companion.target
    property bool onScreen: destination.x>=originX && destination.x<originX+width && destination.y>=originY && destination.y<originY+height
    Item {
        id: buddy
        visible: surface.onScreen && companion.guiding
        x: Math.max(4,Math.min(surface.width-48,surface.destination.x-surface.originX))
        y: Math.max(4,Math.min(surface.height-54,surface.destination.y-surface.originY))
        width: 42; height: 48
        Behavior on x { NumberAnimation { duration: companion.guiding?650:120; easing.type: Easing.OutCubic } }
        Behavior on y { NumberAnimation { duration: companion.guiding?650:120; easing.type: Easing.OutCubic } }
        Rectangle { anchors.centerIn:parent; width:58;height:58;radius:29;color:theme.accent;opacity:0.08 }
        BuddyAvatar { thinking:backend.busy;recording:backend.voiceState==="recording" }
        Rectangle {
            visible: companion.guiding
            width: 64;height:64;radius:32;anchors.centerIn:parent;color:"transparent";border.width:1;border.color:theme.accent;opacity:0.6
            SequentialAnimation on scale { running:companion.guiding;loops:Animation.Infinite;NumberAnimation{to:1.25;duration:950}NumberAnimation{to:1;duration:950} }
        }
    }
    Rectangle {
        id: caption
        visible: surface.onScreen && companion.guiding && (companion.caption.length>0 || backend.voiceState!=="idle" || backend.busy)
        x: Math.max(12,Math.min(surface.width-width-12,buddy.x+52))
        y: Math.max(12,Math.min(surface.height-height-12,buddy.y+4))
        width: Math.min(310,label.implicitWidth+28);height:label.implicitHeight+22;radius:12
        color:"#f51a211e";border.color:"#485449";border.width:1
        Text {
            id:label;anchors.fill:parent;anchors.margins:11;color:"#edf1e9";font.pixelSize:12;wrapMode:Text.Wrap;maximumLineCount:5;elide:Text.ElideRight
            text: backend.voiceState==="recording"?qsTr("Listening · local microphone"):backend.voiceState==="transcribing"?qsTr("Transcribing locally…"):backend.busy?qsTr("Thinking…"):companion.caption
            textFormat:Text.PlainText
        }
    }
}
