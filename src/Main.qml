import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: win
    property bool libraryOpen: false
    property bool detailOpen: false
    property bool autoSend: false
    property bool hasMessages: (backend.state.messages || []).length>0
    property bool canStop: backend.busy || backend.voiceState!=="idle"
    width: libraryOpen || detailOpen ? Math.min(940,Screen.width-40) : Math.min(560,Screen.width-40)
    height: libraryOpen || detailOpen ? Math.min(680,Screen.height-60) : Math.min(hasMessages?550:(backend.state.attachment || backend.state.window)?480:420,Screen.height-60)
    visible: false
    flags: Qt.Window | Qt.FramelessWindowHint
    title: "Clicky"
    color: "transparent"
    Material.theme: Material.Dark
    Material.accent: theme.accent
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
    property var selectedIds: (backend.state.selections || []).map(function(m){return m.id})
    property var toolRows: {
        let rows=[]
        for(let s of backend.servers) for(let t of s.tools) rows.push({server:s.id,name:t.name,schema:t.schema,enabled:t.enabled,label:s.id+" / "+t.name})
        return rows
    }
    function flushDraft(){draftTimer.stop();if(currentCid)backend.send({cmd:"draft",conversation:currentCid,text:input.text})}
    function switchConversation(id){flushDraft();backend.send({cmd:"switch",id:id})}
    function newConversation(){flushDraft();backend.send({cmd:"new"})}
    function inspectRequest(){autoSend=false;flushDraft();backend.send({cmd:"prepare",text:input.text})}
    function submit(){autoSend=!backend.state.attachment;flushDraft();backend.send({cmd:"prepare",text:input.text})}
    function closeOverlay(){flushDraft();win.hide()}
    onClosing:function(event){event.accepted=false;closeOverlay()}
    onVisibleChanged:if(visible)input.forceActiveFocus()
    Shortcut {sequence:"Escape";context:Qt.ApplicationShortcut;onActivated:{if(approvalDialog.opened)backend.send({cmd:"approve",id:approval.id,allow:false});else if(previewDialog.opened)previewDialog.close();else closeOverlay()}}
    Shortcut {sequence:"Ctrl+Return";context:Qt.ApplicationShortcut;onActivated:if(!backend.busy)inspectRequest()}
    Shortcut {sequence:"Ctrl+N";context:Qt.ApplicationShortcut;onActivated:if(!backend.busy)newConversation()}
    Shortcut {sequence:"Ctrl+K";context:Qt.ApplicationShortcut;onActivated:{libraryOpen=true;search.forceActiveFocus()}}
    Shortcut {sequence:"Ctrl+.";context:Qt.ApplicationShortcut;onActivated:{companion.clear();backend.send({cmd:"cancel"})}}
    Shortcut {sequence:"Ctrl+Shift+Q";context:Qt.ApplicationShortcut;onActivated:backend.quit()}
    Timer {id:draftTimer;interval:200;onTriggered:if(win.currentCid)backend.send({cmd:"draft",conversation:win.currentCid,text:input.text})}
    Connections {
        target:backend
        function onWorkerEvent(v){
            if(v.event==="state"){
                win.providerForm=v.provider
                if(v.conversation!==win.currentCid){win.currentCid=v.conversation;input.text=v.draft || "";search.text="";win.trace=[]}
            }
            if(v.event==="history"){win.historyMessages=v.messages;historyDialog.open()}
            if(v.event==="preview"){
                win.requestPreview=v.request;win.previewId=v.id
                if(win.autoSend){win.autoSend=false;backend.send({cmd:"send",id:v.id})}else previewDialog.open()
            }
            if(v.event==="approval"){win.approval=v;approvalDialog.open();win.show();win.raise();win.requestActivate()}
            if(v.event==="approval_closed" && v.id===win.approval.id)approvalDialog.close()
            if(v.event==="activity"){let a=win.trace.slice();a.push(v);win.trace=a}
            if(v.event==="transcript"){input.text+=(input.text?"\n":"")+v.text;input.forceActiveFocus()}
            if(v.event==="request_started" && v.conversation===win.currentCid)input.text=""
            if(v.event==="models"){win.foundModels=v.models;win.notice=qsTr("Models: %1").arg(v.models.join(", "))}
            if(v.event==="search" && v.query===search.text)win.searchResults=v.conversations
            if(v.event==="notice")win.notice=v.message
            if(v.event==="usage")win.notice=qsTr("Usage: %1").arg(JSON.stringify(v.usage))
        }
    }
    component SmallButton: Button {
        font.pixelSize:11;topInset:0;bottomInset:0;implicitHeight:30;leftPadding:10;rightPadding:10
        background:Rectangle{color:parent.down?"#38443a":parent.hovered?"#2c362e":"transparent";radius:7;border.color:parent.highlighted?theme.accent:"#343e36"}
        contentItem:Text{text:parent.text;font:parent.font;color:parent.enabled?(parent.highlighted?theme.accent:"#b5c1b7"):"#657167";horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter}
        ToolTip.visible:hovered && text.length===1;ToolTip.text:Accessible.name
    }
    component PanelDialog: Dialog {
        id:panel
        Material.theme:Material.Dark;Material.accent:theme.accent
        Material.background:"#1b231e"
        onAboutToShow:win.detailOpen=true
        onClosed:win.detailOpen=false
        header:Label{text:panel.title;color:"#edf1e8";font.pixelSize:20;padding:20;bottomPadding:8}
        footer:DialogButtonBox {
            visible:panel.standardButtons!==Dialog.NoButton
            standardButtons:panel.standardButtons
            background:Rectangle{color:"#1b231e";radius:10}
            onAccepted:panel.accept()
            onRejected:panel.reject()
        }
        background:Rectangle{color:"#1b231e";radius:Math.max(10,theme.radius);border.color:"#414f43"}
        Overlay.modal:Rectangle{color:"#bb0c110e"}
    }
    Rectangle {
        anchors.fill:parent;radius:Math.max(14,theme.radius);color:"#171e19";border.color:"#414e41";border.width:1
        RowLayout {
            anchors.fill:parent;spacing:0
            Rectangle {
                visible:win.libraryOpen;Layout.preferredWidth:290;Layout.fillHeight:true;color:"#121914";radius:Math.max(14,theme.radius)
                ColumnLayout {
                    anchors.fill:parent;anchors.margins:18;spacing:10
                    RowLayout {
                        Label{text:qsTr("Conversations");font.pixelSize:17;font.weight:Font.DemiBold;Layout.fillWidth:true}
                        SmallButton{text:"+";Accessible.name:qsTr("New conversation");enabled:!backend.busy;onClicked:newConversation()}
                    }
                    TextField{id:search;objectName:"historySearch";Layout.fillWidth:true;placeholderText:qsTr("Search history…");font.pixelSize:12;onTextChanged:backend.send({cmd:"search",text:text})}
                    Label{text:qsTr("Open to continue · + Context to attach");font.pixelSize:10;color:"#859889"}
                    ListView {
                        id:historyList;objectName:"historyList";Layout.fillWidth:true;Layout.fillHeight:true;clip:true;spacing:6
                        model:search.text.length?win.searchResults:(backend.state.conversations || [])
                        delegate:Rectangle {
                            required property var modelData
                            width:historyList.width;height:94;radius:8;color:modelData.id===win.currentCid?"#27352b":"#1c261f"
                            ColumnLayout {
                                anchors.fill:parent;anchors.margins:10;spacing:3
                                Label{text:modelData.title;textFormat:Text.PlainText;elide:Text.ElideRight;Layout.fillWidth:true;font.pixelSize:12}
                                Label{text:Qt.formatDateTime(new Date(modelData.updated),"MMM d · hh:mm");font.pixelSize:10;color:"#859889"}
                                RowLayout {
                                    SmallButton{text:qsTr("Open");enabled:!backend.busy;onClicked:switchConversation(modelData.id)}
                                    SmallButton{objectName:"addContext_"+modelData.id;text:qsTr("+ Context");visible:modelData.id!==win.currentCid;onClicked:backend.send({cmd:"history",id:modelData.id})}
                                }
                            }
                        }
                    }
                    Label{text:qsTr("SELECTED CONTEXT");color:"#859889";font.pixelSize:10;font.letterSpacing:1.2}
                    ListView {
                        id:selectionsList
                        Layout.fillWidth:true;Layout.preferredHeight:Math.min(150,count*34);clip:true;spacing:4
                        model:backend.state.selections || []
                        delegate:RowLayout {
                            required property var modelData
                            width:selectionsList.width;height:30
                            Label{text:modelData.content;textFormat:Text.PlainText;elide:Text.ElideRight;Layout.fillWidth:true;font.pixelSize:11}
                            SmallButton{objectName:"removeContext_"+modelData.id;text:"×";Accessible.name:qsTr("Remove context");onClicked:backend.send({cmd:"select",message:modelData.id,enabled:false})}
                        }
                    }
                    RowLayout {
                        SmallButton{text:qsTr("Fresh context");onClicked:backend.send({cmd:"fresh_context"})}
                        SmallButton{text:qsTr("Clear chat");onClicked:clearDialog.open()}
                    }
                }
            }
            ColumnLayout {
                Layout.fillWidth:true;Layout.fillHeight:true;Layout.margins:20;spacing:10
                RowLayout {
                    Layout.fillWidth:true
                    Layout.minimumHeight:46;Layout.maximumHeight:46
                    BuddyAvatar{Layout.preferredWidth:38;Layout.preferredHeight:46;scale:0.82;thinking:backend.busy;recording:backend.voiceState==="recording"}
                    ColumnLayout {
                        spacing:2;Layout.fillWidth:true
                        Label{text:"clicky";Layout.fillWidth:true;font.pixelSize:21;font.weight:Font.DemiBold;font.letterSpacing:-0.7;color:"#edf1e8"}
                        Label{text:backend.voiceState==="recording"?qsTr("Listening · local transcription"):backend.voiceState==="transcribing"?qsTr("Transcribing locally…"):backend.busy?qsTr("Working with you…"):qsTr("A little buddy for your desktop");Layout.fillWidth:true;elide:Text.ElideRight;font.pixelSize:10;color:"#9bab9a"}
                    }
                    SmallButton{objectName:"historyToggle";text:"≡";Accessible.name:qsTr("Conversation history");checkable:true;checked:win.libraryOpen;onClicked:win.libraryOpen=!win.libraryOpen}
                    SmallButton{text:"⚙";Accessible.name:qsTr("Settings");onClicked:settingsDialog.open()}
                    SmallButton{text:"×";Accessible.name:qsTr("Hide Clicky");onClicked:closeOverlay()}
                    MouseArea{Layout.preferredWidth:8;Layout.fillHeight:true;onPressed:win.startSystemMove()}
                }
                Rectangle{Layout.fillWidth:true;height:1;color:"#2e3a30"}
                Rectangle {
                    visible:backend.error.length>0;Layout.fillWidth:true;implicitHeight:errorLabel.implicitHeight+18;radius:8;color:"#412c28"
                    Label{id:errorLabel;anchors.fill:parent;anchors.margins:9;text:backend.error;textFormat:Text.PlainText;color:"#f4c8b7";wrapMode:Text.Wrap;font.pixelSize:11;TapHandler{onTapped:backend.dismissError()}}
                }
                ColumnLayout {
                    visible:!win.hasMessages && !backend.error.length;Layout.fillWidth:true;Layout.fillHeight:true;spacing:5
                    Label{text:qsTr("What are we working on?");font.pixelSize:22;font.weight:Font.Medium;Layout.fillWidth:true;color:"#e7ecdf"}
                    Label{text:(backend.state.provider || {}).model?qsTr("Ask, talk, or bring a piece of your screen."):qsTr("Your buddy is ready. Connect a model in Settings to chat.");wrapMode:Text.Wrap;Layout.fillWidth:true;font.pixelSize:12;color:"#95a591"}
                    RowLayout {
                        SmallButton{text:qsTr("Connected tools");onClicked:toolsDialog.open()}
                        SmallButton{text:qsTr("Connect model");visible:!(backend.state.provider || {}).model;onClicked:settingsDialog.open()}
                    }
                    Item{Layout.fillHeight:true}
                }
                ListView {
                    id:messages;objectName:"messageList";visible:win.hasMessages;Layout.fillWidth:true;Layout.fillHeight:true;clip:true;spacing:16
                    model:backend.state.messages || [];onCountChanged:Qt.callLater(positionViewAtEnd)
                    delegate:ColumnLayout {
                        required property var modelData
                        width:messages.width;spacing:5
                        RowLayout {
                            Label{text:modelData.role==="user"?qsTr("YOU"):"CLICKY";font.pixelSize:9;font.letterSpacing:1;color:modelData.role==="user"?"#91a08e":theme.accent;Layout.fillWidth:true}
                            SmallButton{text:qsTr("Speak");visible:modelData.role==="assistant";onClicked:backend.speak(modelData.content)}
                        }
                        TextArea{text:modelData.content;readOnly:true;selectByMouse:true;textFormat:TextEdit.PlainText;wrapMode:TextEdit.Wrap;Layout.fillWidth:true;font.pixelSize:13;color:"#e7ecdf";padding:0;background:null}
                        Label{text:modelData.status==="complete"?"":modelData.status;font.pixelSize:9;color:"#91a08e";visible:text.length>0}
                    }
                }
                RowLayout {
                    visible:!!backend.state.attachment || !!backend.state.window;Layout.fillWidth:true
                    Image{visible:!!backend.state.attachment;source:backend.state.attachment?"file://"+backend.state.attachment.path:"";Layout.preferredWidth:76;Layout.preferredHeight:45;fillMode:Image.PreserveAspectFit;TapHandler{onTapped:imageDialog.open()}}
                    Label{text:backend.state.attachment?qsTr("Screen attached · review before sending"):JSON.stringify(backend.state.window || {});textFormat:Text.PlainText;wrapMode:Text.Wrap;Layout.fillWidth:true;font.pixelSize:10;color:theme.accent}
                    SmallButton{text:qsTr("OCR");visible:!!backend.state.attachment;onClicked:backend.send({cmd:"ocr"})}
                    SmallButton{text:"×";Accessible.name:qsTr("Remove attachment");onClicked:{backend.send({cmd:"remove_attachment"});backend.send({cmd:"remove_window"})}}
                }
                Rectangle {
                    Layout.fillWidth:true;Layout.preferredHeight:90;radius:10;color:"#222d24";border.color:input.activeFocus?"#64735c":"#3b493b"
                    ScrollView {
                        anchors.fill:parent;anchors.margins:8;clip:true
                        TextArea {
                            id:input;objectName:"messageInput";wrapMode:TextEdit.Wrap;selectByMouse:true;textFormat:TextEdit.PlainText;font.pixelSize:14;color:"#edf1e8";background:null
                            onTextChanged:draftTimer.restart()
                            Keys.onReturnPressed:function(e){if(e.modifiers===Qt.NoModifier){e.accepted=true;if(text.trim().length && !backend.busy)win.submit()}else e.accepted=false}
                        }
                    }
                    Text{anchors.left:parent.left;anchors.top:parent.top;anchors.margins:14;text:qsTr("Ask anything…");color:"#84927c";font.pixelSize:14;visible:input.text.length===0}
                }
                RowLayout {
                    SmallButton{objectName:"captureButton";text:qsTr("Screen");enabled:!backend.busy;onClicked:backend.capture(false)}
                    SmallButton{text:qsTr("Region");enabled:!backend.busy;onClicked:backend.capture(true)}
                    SmallButton{objectName:"voiceButton";text:backend.voiceState==="recording"?qsTr("■ Finish"):qsTr("● Talk");enabled:!backend.busy && backend.voiceState!=="transcribing";highlighted:backend.voiceState==="recording";onClicked:backend.send({cmd:backend.voiceState==="recording"?"record_stop":"record_start"})}
                    SmallButton{text:qsTr("Inspect");enabled:!backend.busy && input.text.trim().length>0;onClicked:inspectRequest()}
                    Item{Layout.fillWidth:true}
                    SmallButton{objectName:"reviewButton";text:win.canStop?qsTr("Stop"):qsTr("Ask ↵");highlighted:true;enabled:win.canStop || input.text.trim().length>0;onClicked:{if(win.canStop){companion.clear();backend.send({cmd:"cancel"})}else submit()}}
                }
                RowLayout {
                    Rectangle{width:5;height:5;radius:3;color:(backend.state.provider || {}).model?theme.accent:"#6c786a"}
                    Label{text:(backend.state.provider || {}).model || qsTr("No model connected");textFormat:Text.PlainText;elide:Text.ElideRight;Layout.fillWidth:true;font.pixelSize:9;color:"#91a08e"}
                    SmallButton{text:backend.servers.filter(function(s){return s.state==="connected"}).length+" MCP";onClicked:toolsDialog.open()}
                    SmallButton{text:qsTr("Activity");onClicked:activityDialog.open()}
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
        id:settingsDialog;objectName:"settingsDialog";title:qsTr("Model & voice settings");modal:true;anchors.centerIn:parent;width:Math.min(660,win.width-40);height:Math.min(600,win.height-40);standardButtons:Dialog.Close
        ScrollView {
            anchors.fill:parent;clip:true;contentWidth:availableWidth
        ColumnLayout {
            width:settingsDialog.availableWidth;spacing:10
            Label { text:qsTr("OpenAI-compatible endpoint · local or HTTPS hosted. No silent fallback.");wrapMode:Text.Wrap;Layout.fillWidth:true }
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
            RowLayout {
                Switch {text:qsTr("Visual guides · on demand");checked:companion?companion.enabled:false;onToggled:if(companion)companion.enabled=checked}
                SmallButton {text:qsTr("Try guide");enabled:companion && companion.enabled;onClicked:companion.tour()}
                SmallButton {text:qsTr("Mute");onClicked:backend.mute()}
                SmallButton {text:qsTr("Window info");onClicked:backend.windowContext()}
            }
            Label {text:companion && companion.available?qsTr("Optional hints only · no cursor tracking or follower"):qsTr("Visual hints unavailable in this session");font.pixelSize:10;wrapMode:Text.Wrap;Layout.fillWidth:true;color:theme.accent}
            SmallButton {text:qsTr("Quit Clicky");onClicked:backend.quit()}
            Item { Layout.fillHeight:true }
        }
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
        id:invokeDialog;title:qsTr("Invoke a discovered tool");modal:true;anchors.centerIn:parent;width:Math.min(650,win.width-40);height:Math.min(550,win.height-40);standardButtons:Dialog.Close
        ColumnLayout {
            anchors.fill:parent
            ComboBox { id:toolChoice;Layout.fillWidth:true;model:win.toolRows;textRole:"label" }
            ScrollView { Layout.fillWidth:true;Layout.fillHeight:true;TextArea{text:JSON.stringify((win.toolRows[toolChoice.currentIndex] || {}).schema || {},null,2);readOnly:true;wrapMode:TextEdit.Wrap;textFormat:TextEdit.PlainText;font.pixelSize:11} }
            TextArea { id:toolArgs;Layout.fillWidth:true;Layout.preferredHeight:100;text:"{}";wrapMode:TextEdit.Wrap;textFormat:TextEdit.PlainText;placeholderText:qsTr("JSON arguments") }
            Button { text:qsTr("Review action");enabled:!backend.busy;onClicked:{try{let t=win.toolRows[toolChoice.currentIndex];backend.send({cmd:"tool_call",server:t.server,tool:t.name,arguments:JSON.parse(toolArgs.text)});invokeDialog.close()}catch(e){win.notice=qsTr("Invalid JSON arguments")}} }
        }
    }
    PanelDialog {
        id:registerDialog;title:qsTr("Register a trusted MCP server");modal:true;anchors.centerIn:parent;width:Math.min(680,win.width-40);height:Math.min(500,win.height-40);standardButtons:Dialog.Close
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
