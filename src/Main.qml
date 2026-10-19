import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: win
    width: 1120; height: 780; minimumWidth: 850; minimumHeight: 600
    visible: false
    title: "Clicky"
    color: "#101316"
    Material.theme: Material.Dark
    Material.accent: theme.accent
    Material.roundedScale: theme.radius
    property string currentCid: ""
    property var historyMessages: []
    property var requestPreview: ({})
    property string previewId: ""
    property var approval: ({})
    property var trace: []
    property var foundModels: []
    property var searchResults: []
    property var providerForm: ({})
    property string notice: ""
    property bool helpVisible: false
    property var selectedIds: (backend.state.selections || []).map(function(m){ return m.id })
    property var toolRows: {
        let rows=[]
        for (let s of backend.servers) for(let t of s.tools) rows.push({server:s.id, name:t.name, schema:t.schema, enabled:t.enabled, label:s.id+" / "+t.name})
        return rows
    }
    function flushDraft() { draftTimer.stop(); backend.send({cmd:"draft", text:input.text}) }
    function switchConversation(id) { flushDraft(); backend.send({cmd:"switch",id:id}) }
    function newConversation() { flushDraft(); backend.send({cmd:"new"}) }
    function inspectRequest() { flushDraft(); backend.send({cmd:"prepare",text:input.text}) }
    function closeOverlay() { flushDraft(); win.hide() }
    onClosing: function(event) { event.accepted=false; closeOverlay() }
    onVisibleChanged: if(visible) input.forceActiveFocus()

    Shortcut { sequence:"Escape"; context:Qt.ApplicationShortcut; onActivated: {
        if(approvalDialog.opened) backend.send({cmd:"approve",id:approval.id,allow:false})
        else if(previewDialog.opened) previewDialog.close()
        else closeOverlay()
    } }
    Shortcut { sequence:"Ctrl+Return"; context:Qt.ApplicationShortcut; onActivated: if(!backend.busy) inspectRequest() }
    Shortcut { sequence:"Ctrl+N"; context:Qt.ApplicationShortcut; onActivated: if(!backend.busy) newConversation() }
    Shortcut { sequence:"Ctrl+K"; context:Qt.ApplicationShortcut; onActivated: search.forceActiveFocus() }
    Shortcut { sequence:"Ctrl+."; context:Qt.ApplicationShortcut; onActivated: backend.send({cmd:"cancel"}) }
    Shortcut { sequence:"Ctrl+Shift+Q"; context:Qt.ApplicationShortcut; onActivated: backend.quit() }
    Shortcut { sequence:"?"; enabled:!input.activeFocus && !search.activeFocus; context:Qt.ApplicationShortcut; onActivated: helpDialog.open() }
    Timer { id:draftTimer; interval:200; onTriggered: backend.send({cmd:"draft",text:input.text}) }

    Connections {
        target:backend
        function onWorkerEvent(v) {
            if(v.event==="state" && v.conversation!==win.currentCid) {
                win.currentCid=v.conversation; input.text=v.draft || ""; search.text=""; win.trace=[]
            }
            if(v.event==="history") { win.historyMessages=v.messages; historyDialog.open() }
            if(v.event==="preview") { win.requestPreview=v.request; win.previewId=v.id; previewDialog.open() }
            if(v.event==="approval") { win.approval=v; approvalDialog.open(); win.show(); win.raise(); win.requestActivate() }
            if(v.event==="approval_closed" && v.id===win.approval.id) approvalDialog.close()
            if(v.event==="activity") { let a=win.trace.slice(); a.push(v); win.trace=a }
            if(v.event==="transcript") { input.text+=(input.text?"\n":"")+v.text; input.forceActiveFocus() }
            if(v.event==="request_started" && v.conversation===win.currentCid) input.text=""
            if(v.event==="models") { win.foundModels=v.models; win.notice=qsTr("Discovered models: %1").arg(v.models.join(", ")) }
            if(v.event==="search" && v.query===search.text) win.searchResults=v.conversations
            if(v.event==="notice") win.notice=v.message
            if(v.event==="usage") win.notice=qsTr("Provider usage: %1").arg(JSON.stringify(v.usage))
        }
    }

    component SmallButton: Button { font.pixelSize:12; topInset:0; bottomInset:0; implicitHeight:34 }
    component SectionLabel: Label { color:"#87949d"; font.pixelSize:11; font.letterSpacing:1.2 }
    component PanelDialog: Dialog {
        Material.theme:Material.Dark
        Material.accent:theme.accent
        Material.roundedScale:theme.radius
        background:Rectangle { color:"#1b2227";radius:theme.radius;border.color:"#34414a" }
        Overlay.modal:Rectangle { color:"#b0000000" }
    }

    Item {
        anchors.fill:parent
        LayoutMirroring.enabled:Qt.application.layoutDirection===Qt.RightToLeft
        LayoutMirroring.childrenInherit:true
        RowLayout {
            anchors.fill:parent; spacing:0
            Rectangle {
                color:"#151a1e"; Layout.preferredWidth:250; Layout.fillHeight:true
                ColumnLayout {
                    anchors.fill:parent; anchors.margins:18; spacing:10
                    RowLayout {
                        Rectangle { width:10;height:10;radius:5;color:theme.accent }
                        Label { text:"Clicky"; font.pixelSize:24; font.weight:Font.DemiBold; Layout.fillWidth:true }
                        SmallButton { text:"+"; Accessible.name:qsTr("New conversation"); enabled:!backend.busy; onClicked:newConversation() }
                    }
                    Label { text:qsTr("Your desktop, with context."); color:"#87949d"; font.pixelSize:11 }
                    TextField { id:search; objectName:"historySearch"; Layout.fillWidth:true; placeholderText:qsTr("Search conversations"); font.pixelSize:12;onTextChanged:backend.send({cmd:"search",text:text}) }
                    SectionLabel { text:qsTr("CONVERSATIONS") }
                    ListView {
                        id:historyList; objectName:"historyList"; Layout.fillWidth:true; Layout.fillHeight:true; clip:true; spacing:5
                        model:search.text.length?win.searchResults:(backend.state.conversations || [])
                        delegate:Rectangle {
                            required property var modelData
                            width:historyList.width; height:74; radius:theme.radius
                            color:modelData.id===win.currentCid?"#263037":"#191f24"
                            ColumnLayout {
                                anchors.fill:parent; anchors.margins:9; spacing:2
                                Label { text:modelData.title; elide:Text.ElideRight; Layout.fillWidth:true; font.pixelSize:12 }
                                RowLayout {
                                    Label {
                                        text: { translator.language; return new Date(modelData.updated).toLocaleString(Qt.locale(),"dd MMM hh:mm") }
                                        color:"#87949d";font.pixelSize:10;Layout.fillWidth:true
                                    }
                                    SmallButton { objectName:"addContext_"+modelData.id;text:qsTr("Context"); flat:true; enabled:modelData.id!==win.currentCid && !backend.busy; onClicked: {flushDraft();backend.send({cmd:"history",id:modelData.id})} }
                                }
                            }
                            TapHandler { enabled:!backend.busy; onTapped:switchConversation(modelData.id) }
                        }
                    }
                    SectionLabel { text:qsTr("SELECTED CONTEXT") }
                    Label { visible:!(backend.state.selections || []).length; text:qsTr("Choose messages with Context.\nBrowsing history adds nothing.");font.pixelSize:11;color:"#87949d";wrapMode:Text.WordWrap;Layout.fillWidth:true }
                    ScrollView {
                        Layout.fillWidth:true;Layout.preferredHeight:Math.min(120,(backend.state.selections || []).length*43)
                        Column {
                            width:parent.width
                            Repeater {
                                model:backend.state.selections || []
                                RowLayout {
                                    required property var modelData
                                    width:parent.width
                                    Label { text:modelData.title+" · "+modelData.role;elide:Text.ElideRight;Layout.fillWidth:true;font.pixelSize:11 }
                                    SmallButton { objectName:"removeContext_"+modelData.id;text:"×"; Accessible.name:qsTr("Remove context selection"); onClicked:backend.send({cmd:"select",message:modelData.id,enabled:false}) }
                                }
                            }
                        }
                    }
                    SmallButton { text:qsTr("Reset selected context");Layout.fillWidth:true;enabled:!backend.busy;onClicked:backend.send({cmd:"fresh_context"}) }
                    RowLayout {
                        SmallButton { text:qsTr("Settings");Layout.fillWidth:true;onClicked:{win.providerForm=backend.state.provider || {};settingsDialog.open()} }
                        SmallButton { text:qsTr("Tools");Layout.fillWidth:true;onClicked:toolsDialog.open() }
                    }
                }
            }
            ColumnLayout {
                Layout.fillWidth:true;Layout.fillHeight:true;spacing:0
                Rectangle {
                    color:"#101316";Layout.fillWidth:true;Layout.preferredHeight:76
                    RowLayout {
                        anchors.fill:parent;anchors.margins:20;spacing:14
                        ColumnLayout {
                            Layout.fillWidth:true;spacing:5
                            Label { text:(backend.state.provider || {}).model || qsTr("Connect your local model");font.pixelSize:18;font.weight:Font.Medium;elide:Text.ElideRight;Layout.fillWidth:true }
                            Label { text:(backend.state.provider || {}).base_url || "";color:"#87949d";font.pixelSize:11 }
                        }
                        Label { text:qsTr("%1 MCP connected").arg(backend.servers.filter(function(s){return s.state==="connected"}).length);color:theme.accent;font.pixelSize:11 }
                        SmallButton { text:qsTr("Clear");enabled:!backend.busy;onClicked:clearDialog.open() }
                        SmallButton { text:qsTr("Hide");onClicked:closeOverlay() }
                    }
                }
                Rectangle { color:"#263037";Layout.fillWidth:true;Layout.preferredHeight:1 }
                Rectangle {
                    visible:!!backend.error;color:"#392324";Layout.fillWidth:true;Layout.preferredHeight:errorRow.implicitHeight+14
                    RowLayout {
                        id:errorRow;anchors.fill:parent;anchors.margins:8
                        Label { text:backend.error;wrapMode:Text.WordWrap;Layout.fillWidth:true;color:"#ffb6b2";font.pixelSize:12 }
                        SmallButton { text:"×";onClicked:backend.dismissError() }
                    }
                }
                Item {
                    Layout.fillWidth:true;Layout.fillHeight:true
                    ColumnLayout {
                        visible:!(backend.state.messages || []).length
                        anchors.centerIn:parent;width:Math.min(450,parent.width-60);spacing:16
                        Label { text:qsTr("A little space to think.");font.pixelSize:29;font.weight:Font.Light;Layout.fillWidth:true;wrapMode:Text.WordWrap }
                        Label { text:qsTr("Ask a question, bring a screen capture, or connect a tool. You choose what the assistant can see and do.");font.pixelSize:14;lineHeight:1.4;wrapMode:Text.WordWrap;color:"#a7b1b8";Layout.fillWidth:true }
                        Label { text:qsTr("Open Settings to connect your local model.");font.pixelSize:12;wrapMode:Text.WordWrap;color:theme.accent;Layout.fillWidth:true;visible:!(backend.state.provider || {}).model }
                    }
                    ListView {
                        id:messages;objectName:"messageList";anchors.fill:parent;anchors.margins:20;clip:true;spacing:18
                        model:backend.state.messages || []
                        onCountChanged:positionViewAtEnd()
                        delegate:ColumnLayout {
                            required property var modelData
                            width:messages.width;spacing:4
                            RowLayout {
                                Label { text:modelData.role==="user"?qsTr("YOU"):qsTr("CLICKY");font.pixelSize:10;font.letterSpacing:1;color:modelData.role==="user"?"#87949d":theme.accent }
                                Label { text:modelData.status==="complete"?"":modelData.status;color:"#87949d";font.pixelSize:10 }
                                Item { Layout.fillWidth:true }
                                SmallButton { text:qsTr("Speak");flat:true;visible:modelData.role==="assistant";onClicked:backend.speak(modelData.content) }
                            }
                            TextArea { text:modelData.content;readOnly:true;selectByMouse:true;textFormat:TextEdit.PlainText;wrapMode:TextEdit.Wrap;Layout.fillWidth:true;font.pixelSize:14;color:"#e5e9eb";padding:0;background:null }
                        }
                    }
                }
                Rectangle {
                    visible:!!backend.state.attachment || !!backend.state.window;color:"#1c252b";Layout.fillWidth:true;Layout.preferredHeight:100
                    RowLayout {
                        anchors.fill:parent;anchors.margins:12
                        Image { visible:!!backend.state.attachment;source:backend.state.attachment?"file://"+backend.state.attachment.path:"";Layout.preferredWidth:115;Layout.fillHeight:true;fillMode:Image.PreserveAspectFit;TapHandler{onTapped:imageDialog.open()} }
                        ColumnLayout {
                            Layout.fillWidth:true
                            Label { text:backend.state.attachment?qsTr("Screen capture · local preview"):qsTr("Active-window context");font.pixelSize:12 }
                            Label { text:backend.state.window?JSON.stringify(backend.state.window):qsTr("Nothing is uploaded until you review and send.");font.pixelSize:11;color:"#a7b1b8";wrapMode:Text.Wrap;Layout.fillWidth:true }
                        }
                        SmallButton { text:qsTr("OCR");visible:!!backend.state.attachment;onClicked:backend.send({cmd:"ocr"}) }
                        SmallButton { text:qsTr("Remove");onClicked:{backend.send({cmd:"remove_attachment"});backend.send({cmd:"remove_window"})} }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth:true;Layout.margins:18;spacing:8
                    RowLayout {
                        SmallButton { text:qsTr("Screen");enabled:!backend.busy;onClicked:backend.capture(false) }
                        SmallButton { text:qsTr("Region");enabled:!backend.busy;onClicked:backend.capture(true) }
                        SmallButton { text:qsTr("Window info");enabled:!backend.busy;onClicked:backend.windowContext() }
                        SmallButton { text:backend.voiceState==="recording"?qsTr("■ Finish recording"):backend.voiceState==="transcribing"?qsTr("Transcribing…"):qsTr("● Talk");enabled:!backend.busy && backend.voiceState!=="transcribing";onClicked:backend.send({cmd:backend.voiceState==="recording"?"record_stop":"record_start"}) }
                        SmallButton { text:qsTr("Mute");onClicked:backend.mute() }
                        Item { Layout.fillWidth:true }
                    }
                    ScrollView {
                        Layout.fillWidth:true;Layout.preferredHeight:100
                        TextArea { id:input;objectName:"messageInput";placeholderText:qsTr("Type a message. Ctrl+Enter to review.");wrapMode:TextEdit.Wrap;selectByMouse:true;textFormat:TextEdit.PlainText;font.pixelSize:14;onTextChanged:draftTimer.restart() }
                    }
                    RowLayout {
                        Label { text:backend.voiceState==="recording"?qsTr("Microphone on · local only · 60s limit"):backend.busy?qsTr("Working · actions require your approval"):win.notice || qsTr("Explicit context. Reviewed actions.");color:backend.voiceState==="recording"?"#ffb6b2":"#87949d";font.pixelSize:11;elide:Text.ElideRight;Layout.fillWidth:true }
                        SmallButton { text:qsTr("Activity");onClicked:activityDialog.open() }
                        SmallButton { text:qsTr("Stop");onClicked:backend.send({cmd:"cancel"}) }
                        Button { text:qsTr("Review & send");objectName:"reviewButton";highlighted:true;enabled:!backend.busy && input.text.trim().length>0;onClicked:inspectRequest() }
                    }
                }
            }
        }
    }

    PanelDialog {
        id:historyDialog;objectName:"contextDialog";title:qsTr("Choose historical messages");modal:true;anchors.centerIn:parent;width:Math.min(720,win.width-60);height:Math.min(580,win.height-70)
        standardButtons:Dialog.Close
        ColumnLayout {
            anchors.fill:parent
            Label { text:qsTr("Only checked messages enter this conversation's context.");wrapMode:Text.Wrap;Layout.fillWidth:true }
            SmallButton { text:qsTr("Select all complete messages");onClicked: {for(let m of win.historyMessages)if(m.status==="complete"&&(m.role==="user"||m.role==="assistant"))backend.send({cmd:"select",message:m.id,enabled:true})} }
            ListView {
                Layout.fillWidth:true;Layout.fillHeight:true;clip:true;model:win.historyMessages;spacing:10
                delegate:ColumnLayout {
                    required property var modelData
                    width:ListView.view.width
                    CheckBox { objectName:"contextSelect_"+modelData.id;text:modelData.role;checked:win.selectedIds.indexOf(modelData.id)>=0;enabled:modelData.status==="complete"&&(modelData.role==="user"||modelData.role==="assistant");onClicked:backend.send({cmd:"select",message:modelData.id,enabled:checked}) }
                    Label { text:modelData.content;textFormat:Text.PlainText;wrapMode:Text.Wrap;Layout.fillWidth:true;font.pixelSize:12 }
                }
            }
        }
    }
    PanelDialog {
        id:previewDialog;objectName:"requestDialog";title:qsTr("Inspect the exact request");modal:true;anchors.centerIn:parent;width:Math.min(800,win.width-50);height:Math.min(650,win.height-50)
        ColumnLayout {
            anchors.fill:parent
            Label { text:qsTr("Review messages, selected context, tool schemas and endpoint. Image bytes are represented by their local preview and SHA-256.");wrapMode:Text.Wrap;Layout.fillWidth:true;font.pixelSize:12 }
            ScrollView { Layout.fillWidth:true;Layout.fillHeight:true;TextArea{text:JSON.stringify(win.requestPreview,null,2);readOnly:true;selectByMouse:true;textFormat:TextEdit.PlainText;wrapMode:TextEdit.Wrap;font.family:"monospace";font.pixelSize:11} }
            RowLayout {
                Item { Layout.fillWidth:true }
                Button { text:qsTr("Cancel");onClicked:previewDialog.close() }
                Button { text:qsTr("Send this request");highlighted:true;onClicked:{backend.send({cmd:"send",id:win.previewId});previewDialog.close()} }
            }
        }
    }
    PanelDialog {
        id:approvalDialog;objectName:"approvalDialog";title:qsTr("Approve one tool action");modal:true;closePolicy:Popup.NoAutoClose;anchors.centerIn:parent;width:Math.min(740,win.width-70);height:480
        ColumnLayout {
            anchors.fill:parent
            Label { text:win.approval.tool || "";color:theme.accent;font.pixelSize:18;wrapMode:Text.Wrap;Layout.fillWidth:true }
            Label { text:win.approval.effect || "";wrapMode:Text.Wrap;Layout.fillWidth:true }
            ScrollView { Layout.fillWidth:true;Layout.fillHeight:true;TextArea{text:JSON.stringify(win.approval.arguments || {},null,2);readOnly:true;selectByMouse:true;wrapMode:TextEdit.Wrap;textFormat:TextEdit.PlainText;font.family:"monospace"} }
            Label { text:qsTr("Approval expires after two minutes. Review the arguments and effects.");font.pixelSize:11;color:"#a7b1b8";wrapMode:Text.Wrap;Layout.fillWidth:true }
            RowLayout {
                Item { Layout.fillWidth:true }
                Button { text:qsTr("Deny");onClicked:backend.send({cmd:"approve",id:win.approval.id,allow:false}) }
                Button { text:qsTr("Approve once");highlighted:true;onClicked:backend.send({cmd:"approve",id:win.approval.id,allow:true}) }
            }
        }
    }
    PanelDialog {
        id:settingsDialog;objectName:"settingsDialog";title:qsTr("Model & voice settings");modal:true;anchors.centerIn:parent;width:660;height:600;standardButtons:Dialog.Close
        ColumnLayout {
            anchors.fill:parent;spacing:10
            Label { text:qsTr("Local OpenAI-compatible endpoint. No remote fallback.");wrapMode:Text.Wrap;Layout.fillWidth:true }
            TextField { id:baseUrl;Layout.fillWidth:true;placeholderText:qsTr("Base URL (including /v1)");text:win.providerForm.base_url || "" }
            TextField { id:modelName;Layout.fillWidth:true;placeholderText:qsTr("Model identifier");text:win.providerForm.model || "" }
            TextField { id:providerKey;Layout.fillWidth:true;placeholderText:qsTr("Optional API key → GNOME Keyring");echoMode:TextInput.Password;onVisibleChanged:if(!visible)text="" }
            RowLayout {
                TextField { id:contextBudget;Layout.fillWidth:true;placeholderText:qsTr("Context tokens");text:String(win.providerForm.context_tokens || 8192);validator:IntValidator{bottom:2048;top:2000000} }
                TextField { id:responseBudget;Layout.fillWidth:true;placeholderText:qsTr("Response tokens");text:String(win.providerForm.response_tokens || 1024);validator:IntValidator{bottom:128;top:2000000} }
            }
            RowLayout {
                Button { text:qsTr("Save settings");onClicked:{backend.send({cmd:"provider_save",values:{base_url:baseUrl.text,model:modelName.text,context_tokens:Number(contextBudget.text),response_tokens:Number(responseBudget.text)},key:providerKey.text});providerKey.text=""} }
                Button { text:qsTr("Discover models");onClicked:backend.send({cmd:"models"}) }
            }
            Label { text:qsTr("Save first, then verify capabilities with synthetic non-private data.");wrapMode:Text.Wrap;Layout.fillWidth:true;color:"#a7b1b8";font.pixelSize:12 }
            RowLayout {
                Repeater { model:["text","stream","tools","vision"];Button{required property string modelData;text:modelData;onClicked:backend.send({cmd:"probe",kind:modelData})} }
            }
            Label { text:qsTr("Verified: %1").arg(Object.keys((backend.state.provider || {}).verified || {}).join(", ") || qsTr("none"));wrapMode:Text.Wrap;Layout.fillWidth:true;font.pixelSize:12 }
            Label { text:qsTr("Voice input: PipeWire → local Voxtype. Transcription fills the draft for review. No clipboard access.");wrapMode:Text.Wrap;Layout.fillWidth:true;font.pixelSize:12 }
            Label { text:backend.speechStatus;wrapMode:Text.Wrap;Layout.fillWidth:true;font.pixelSize:12;color:theme.accent }
            Label { text:win.notice;wrapMode:Text.Wrap;Layout.fillWidth:true;font.pixelSize:11 }
            Item { Layout.fillHeight:true }
        }
    }
    PanelDialog {
        id:toolsDialog;objectName:"toolsDialog";title:qsTr("MCP connections & tools");modal:true;anchors.centerIn:parent;width:Math.min(820,win.width-50);height:Math.min(650,win.height-50);standardButtons:Dialog.Close
        ColumnLayout {
            anchors.fill:parent
            Label { text:qsTr("Every invocation requires approval. Stdio servers run trusted code with your OS account permissions.");wrapMode:Text.Wrap;Layout.fillWidth:true;font.pixelSize:12 }
            ScrollView {
                Layout.fillWidth:true;Layout.fillHeight:true
                ColumnLayout {
                    width:parent.width
                    Repeater {
                        model:backend.servers
                        ColumnLayout {
                            required property var modelData
                            Layout.fillWidth:true
                            RowLayout {
                                CheckBox { text:modelData.id;checked:modelData.enabled;onClicked:backend.send({cmd:"server_toggle",id:modelData.id,enabled:checked}) }
                                Label { text:modelData.state+" · "+modelData.transport+" · "+modelData.protocol;color:theme.accent;font.pixelSize:11 }
                                SmallButton { text:qsTr("Reconnect");enabled:modelData.enabled;onClicked:backend.send({cmd:"mcp_connect",id:modelData.id}) }
                            }
                            Repeater {
                                model:parent.modelData.tools
                                RowLayout {
                                    required property var modelData
                                    property string sid:parent.modelData.id
                                    CheckBox { text:modelData.name;checked:modelData.enabled;onClicked:backend.send({cmd:"tool_toggle",server:parent.sid,tool:modelData.name,enabled:checked}) }
                                    Label { text:modelData.description;elide:Text.ElideRight;Layout.fillWidth:true;font.pixelSize:10;color:"#a7b1b8" }
                                }
                            }
                        }
                    }
                }
            }
            RowLayout {
                SmallButton { text:qsTr("Invoke a tool");onClicked:invokeDialog.open() }
                SmallButton { text:qsTr("Register server");onClicked:registerDialog.open() }
                Label { text:qsTr("Roots: %1").arg((backend.state.roots || []).join(", "));elide:Text.ElideLeft;Layout.fillWidth:true;font.pixelSize:10 }
            }
        }
    }
    PanelDialog {
        id:invokeDialog;title:qsTr("Invoke a discovered tool");modal:true;anchors.centerIn:parent;width:650;height:550;standardButtons:Dialog.Close
        ColumnLayout {
            anchors.fill:parent
            ComboBox { id:toolChoice;Layout.fillWidth:true;model:win.toolRows;textRole:"label" }
            ScrollView { Layout.fillWidth:true;Layout.fillHeight:true;TextArea{text:JSON.stringify((win.toolRows[toolChoice.currentIndex] || {}).schema || {},null,2);readOnly:true;wrapMode:TextEdit.Wrap;textFormat:TextEdit.PlainText;font.pixelSize:11} }
            TextArea { id:toolArgs;Layout.fillWidth:true;Layout.preferredHeight:100;text:"{}";wrapMode:TextEdit.Wrap;textFormat:TextEdit.PlainText;placeholderText:qsTr("JSON arguments") }
            Button { text:qsTr("Review action");enabled:!backend.busy;onClicked:{try{let t=win.toolRows[toolChoice.currentIndex];backend.send({cmd:"tool_call",server:t.server,tool:t.name,arguments:JSON.parse(toolArgs.text)});invokeDialog.close()}catch(e){win.notice=qsTr("Invalid JSON arguments")}} }
        }
    }
    PanelDialog {
        id:registerDialog;title:qsTr("Register a trusted MCP server");modal:true;anchors.centerIn:parent;width:680;height:500;standardButtons:Dialog.Close
        ColumnLayout {
            anchors.fill:parent
            Label { text:qsTr("Use env_refs/header_refs for Keyring or env:VARIABLE references. Never put credentials in arguments. New servers start disabled.");wrapMode:Text.Wrap;Layout.fillWidth:true }
            ScrollView { Layout.fillWidth:true;Layout.fillHeight:true;TextArea{id:serverSpec;text:JSON.stringify({id:"my_server",transport:"streamable_http",url:"http://127.0.0.1:9000/mcp",enabled:false,header_refs:{},disabled_tools:[]},null,2);wrapMode:TextEdit.Wrap;textFormat:TextEdit.PlainText} }
            CheckBox { id:trustServer;text:qsTr("I trust this server's code and understand its permissions.") }
            Button { text:qsTr("Register disabled server");enabled:trustServer.checked;onClicked:{try{let s=JSON.parse(serverSpec.text);s.enabled=false;backend.send({cmd:"server_register",spec:s,confirmed:true});registerDialog.close()}catch(e){win.notice=qsTr("Invalid JSON configuration")}} }
        }
    }
    PanelDialog {
        id:activityDialog;title:qsTr("Tool execution activity");modal:true;anchors.centerIn:parent;width:Math.min(800,win.width-50);height:Math.min(600,win.height-50);standardButtons:Dialog.Close
        ScrollView { anchors.fill:parent;TextArea{text:JSON.stringify({recent_persistent_events:backend.state.activity || [],session_details:win.trace},null,2);readOnly:true;wrapMode:TextEdit.Wrap;selectByMouse:true;textFormat:TextEdit.PlainText;font.pixelSize:11} }
    }
    PanelDialog { id:clearDialog;title:qsTr("Clear this conversation?");modal:true;anchors.centerIn:parent;standardButtons:Dialog.Cancel|Dialog.Ok;Label{text:qsTr("Messages, drafts, selections and action records will be removed.");wrapMode:Text.Wrap;width:400}onAccepted:{input.text="";backend.send({cmd:"clear",confirmed:true})} }
    PanelDialog { id:imageDialog;title:qsTr("Local screen preview");modal:true;anchors.centerIn:parent;width:win.width-80;height:win.height-80;standardButtons:Dialog.Close;Image{anchors.fill:parent;source:backend.state.attachment?"file://"+backend.state.attachment.path:"";fillMode:Image.PreserveAspectFit} }
    PanelDialog { id:helpDialog;title:qsTr("Keyboard shortcuts");modal:true;anchors.centerIn:parent;standardButtons:Dialog.Close;Label{text:qsTr("Ctrl+Enter  Review request\nCtrl+N  New conversation\nCtrl+K  Search history\nCtrl+.  Cancel operation\nEscape  Hide / dismiss\nCtrl+Shift+Q  Quit\n?  Shortcuts")} }
}
