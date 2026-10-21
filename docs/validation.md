# Validation record — 21 October 2026

The final app has no cursor follower or background pointer polling. Visual guides
are disabled by default and do not create an idle overlay. Live model setup remains
deferred. Protocol fixtures are distinguished from real model inference below.

## Executed on the final implementation

| Check | Actual result |
|---|---|
| Published CI | [Run 39575899124](https://github.com/vishal88736/clicky-omarchy/actions/runs/39575899124) succeeded at follower-removal commit `5fc99ef`; native UI/desktop acceptance is local |
| Native build | qmake6 / make succeeded with installed Qt 6.12 and layer-shell-qt 6.8 |
| Python suite | `bin/test`: 23 passed, including actual MCP servers, security, context, provider fixtures and native IPC/SIGTERM lifecycle |
| Native Qt suite | `bin/test-ui`: 6 passed, 0 failed (4 actual cases plus setup/cleanup) |
| Typed native text path | Actual keyboard input into the HUD → Enter → Python worker → streamed local HTTP fixture → saved reply → worker restart → restored reply; the fixture is not an LLM |
| Historical context UI | Actual sidebar/context checkbox/request inspector/remove-button interactions passed; intended text included, unselected text absent |
| Drafts and MCP UI | Typed draft, conversation switching, immediate flush/restart, dialogs and actual safe MCP approval/execution passed |
| Optional hint controller | Bounds validation, cancellation and disabled preference across reconstruction passed offscreen |
| Actual MCP transports | Multiple real SDK stdio sessions plus Streamable HTTP and SSE servers negotiated, discovered schemas and executed tools |
| Permission/failure paths | Forbidden paths, missing servers, malformed requests, denial/approval of actual writes, disabling during approval, cancellation and timeouts covered |
| Real Wayland session | `scripts/verify_desktop.py` passed: native app ID, floating=true, pinned=true, xwayland=false, clean config, no follower and no idle overlay |
| Restart without follower | Real service stop completed in 0.72 seconds, Result=success, ExecMainStatus=0; restart returned following=false, guides=false, guiding=false |
| Actual capture | grim produced a temporary 1920×1080 PNG; logical bounds 1536×864 matched scale 1.25. File removed with its temporary directory; no upload |
| Installation reversal | Old manifest-owned integration removed and new launcher/icon/pinned rule installed. Conversation/message/selection counts unchanged; config.json unchanged during uninstall; backups retained |
| Visual inspection | Actual HUD, history and settings QML screenshots rendered with isolated temporary data; inspected for layout and modal clipping. Superseded screenshot removed |

The provider HTTP fixture tests also cover discovery, synthetic text/stream/image/tool
probes, usage, error bodies, cancellation and a complete real-MCP tool/result loop.
They prove the wire/orchestration path, not neural language or vision capability.

Native Qt cases are: optional guidance bounds/preference; typed HTTP streaming and
restart; historical selection/inspection/removal; draft/restart/dialogs/MCP approval.
QtTest counts setup and cleanup separately. The offscreen plugin's unsupported
`raise()` warning is expected; actual Wayland focus/lifecycle is checked separately.

CI runs the Python suite in a headless Python 3.14 container. The two native-binary
cases skip when no native binary exists; Qt interaction and desktop checks run
locally. Follow [GitHub Actions](https://github.com/vishal88736/clicky-omarchy/actions)
for the status at each commit; CI is not desktop or model acceptance.

Earlier component checks on 19–20 October verified microphone format, installed
Voxtype transcription of a public speech sample, local OCR and a temporary Keyring
sentinel round trip. Those are not a full spoken-model conversation. Qt's real
speech-engine libraries were missing; the mock plugin is deliberately excluded.
No audible playback or live neural response is claimed.

## Remaining manual or blocked checks

| Feature | Status / next verification |
|---|---|
| Actual model text | Blocked until a local endpoint/model is supplied; setup was deferred by the user |
| Model-driven tool selection | Protocol and real MCP execution tested separately; actual model selecting tools remains blocked |
| Neural vision and target recognition | Requires a verified vision model; mapping and reviewed-attachment handling are tested |
| Speech playback/full voice loop | Local capture/STT components checked earlier; real TTS engine and model needed for complete spoken interaction |
| Physical global hotkey | Non-conflicting live Lua binding registered; physical Super+Ctrl+Semicolon activation remains manual |
| Interactive region picker | grim capture verified; physical region selection/cancellation remains manual |
| Optional hint on multiple displays | Controller is offscreen-tested; final optional Wayland hint, display hotplug and multi-monitor behavior need manual acceptance if desired |
| Third-party browser MCP | Registration/manager exist; an external browser server has not been configured or tested |

## Manual verification procedures

1. **Text model:** configure its exact `/v1` base URL/model/context limit, save,
   discover models, and run the text probe. Type a question and press Enter; stop
   a second generation; restart and confirm the first answer persists. Run the
   stream probe before claiming streaming support from that model.
2. **Tools:** enable only `workspace / capabilities`, run the tools probe, request
   that tool from the model, inspect/approve the proposed arguments, and verify
   the returned result and answer. Deny a second invocation and check Activity.
3. **Screen:** run the synthetic vision probe; click Screen/Region, inspect the
   local image, and explicitly send a question through the request preview.
   Capture another and cancel; no provider request should be made for that image.
4. **Shortcut/region:** physically press Super+Ctrl+Semicolon twice. Select a small
   non-sensitive region, then cancel another selection with Escape. Confirm prompt
   restoration and no idle overlay.
5. **Voice:** record a known sentence with Talk, finish, inspect the draft, send
   to the configured model. With a real local TTS engine installed, test Speak,
   Mute and Stop. Missing devices/services must produce a visible error.
6. **Optional hints:** leave disabled unless wanted. If enabled deliberately,
   use Try guide and confirm the marker expires in 6.5 seconds, passes input,
   and never follows/moves the real cursor. Disable afterward.
7. **Browser MCP:** register a trusted server disabled, inspect schemas, enable
   selected tools, test a read, then deny a proposed form/message/publish action.

Unsupported: unrestricted shell, arbitrary mouse clicking/dragging, recursive
filesystem deletion and silent screen/clipboard observation. Cursor following
was explicitly removed. These are not presented as implemented features.
