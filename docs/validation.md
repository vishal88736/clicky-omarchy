# Validation record

Audit began on 19 October 2026; implementation and local checks continued into 20 October in Asia/Kolkata. Source existence, protocol fixtures, real transport tests and live desktop checks are distinguished below.

## Executed checks

| Check | Actual result |
|---|---|
| `bin/build` | qmake6/GCC build succeeded with installed Qt 6.12 and project-local Python dependencies |
| `bin/test` | **21 passed** locally in 7.34 seconds after the credential-isolation regression was added |
| `bin/test-ui` | Both native interaction scenarios passed: mouse-driven historical context selection/removal and exact preview isolation; draft/restart, Ctrl+Enter, dialogs and real safe MCP approval/execution. QtTest reports 4 passed entries including init/cleanup. |
| Actual MCP stdio | Two safe SDK subprocess servers connected, negotiated protocol, discovered schemas and returned real tool results |
| Actual MCP HTTP | SDK Streamable HTTP and SSE servers started on temporary loopback ports; both initialized and executed tools |
| Failure/permission paths | Unavailable server, invalid arguments, forbidden path, disabled tool, denied/approved real file writes, disabling during approval and cancellation passed |
| Provider protocol fixture | Text, streaming, synthetic vision/tool probes, usage, error, cancellation, context isolation and full tool/result/answer loop passed against a clearly labeled HTTP fixture; this is not a neural model |
| Native lifecycle | Both visible-window IPC stop and SIGTERM exited 0 with isolated temporary data |
| Immediate draft retention | Native UI test typed a new draft, immediately flushed/closed the worker, restarted it, and restored the exact draft without waiting for the debounce timer |
| GitHub CI | [Run 39306936290](https://github.com/vishal88736/clicky-omarchy/actions/runs/39306936290) succeeded at commit `2e91c9d`: **19 passed, 2 skipped**. Only the two native-binary lifecycle cases were skipped; native build/UI are tested locally. |
| Real Wayland launch | `clicky` app ID, floating=true, xwayland=false; actual compositor-reported size 1120×780 on the audited display |
| Show/hide | Installed launcher and single-instance IPC produced hidden → visible → hidden states |
| Shortcut registration | Non-conflicting Super+Ctrl+Semicolon registered as a live Hyprland Lua binding. Synthetic wtype keys did not prove activation; physical-key check remains manual. |
| Desktop broker | Corrected supported Lua focus and pointer dispatches passed real readback checks. Pointer was moved only to its current location; focus targeted Clicky's own window. |
| Screenshot | Actual grim PNG captured locally: 1920×1080, 1,029,962 bytes for that test frame; no upload, temporary image deleted |
| OCR | Actual Tesseract recognized Clicky from the non-private rendered app screenshot |
| Microphone | Actual PipeWire capture: mono, 16 kHz, 14,309 frames; no upload, temporary recording deleted |
| Local STT | Installed local Voxtype model transcribed whisper.cpp's public JFK sample, exit 0, expected phrase recognized; no private audio used |
| TTS | Real Qt engines unavailable: flite/speechd plugins lacked their libraries. Mock engine excluded. Audible playback not verified. |
| Keyring | A temporary non-credential sentinel was stored/read successfully, compared without printing its value, then removed |
| Credential isolation | Same-endpoint model changes retain the reference; endpoint URL changes clear it; endpoint-derived references differ and normalize trailing slashes. Regression passed. |
| Reversal | Live uninstall removed only app integration, original bindings SHA-256 restored exactly, no Hyprland config errors, then clean reinstall |
| Shutdown hardening | First reversal exposed a close-to-hide/quit defect. After the fix, the visible service stopped in **0.39 seconds**, `Result=success`, `ExecMainStatus=0`, then restarted. |
| Visual review | Real offscreen main/tools screenshots inspected; transparent dialog content was fixed and re-rendered. Partial Hindi catalog reviewed using a temporary language file, without changing desktop language. |

The native Qt harness reports init/cleanup as passed entries in addition to its interaction cases; these are not counted as additional product features. All test history, fixture servers and provider fixtures are separate from user data. No private screenshot/audio or authentication data was committed.

## Acceptance matrix

| Requirement | State |
|---|---|
| Start without breaking session | Passed in actual Wayland session |
| Show/hide through configured hotkey | Registration and lifecycle path passed; physical chord activation still needs manual confirmation |
| Text assistant with configured provider | Compatible protocol path passed; real LLM blocked because local model setup was explicitly deferred |
| Persist conversations across restart | Passed in SQLite/worker fixture and native draft/restart tests |
| Sidebar explicit context selection/removal | Passed in both backend tests and the actual sidebar/checkbox/remove-button mouse interaction scenario |
| Send only intended context | Exact request assertions passed against recorded provider-fixture requests; no unselected historical text |
| Real MCP connection | Passed for multiple stdio, Streamable HTTP and SSE sessions |
| Real MCP invocation | Passed, including native UI approval/execution and real safe file operations |
| Unavailable/failing tools | Passed |
| Compatible screen capture | Passed for focused-monitor grim capture; interactive region selection remains manual |
| Sensitive approval | Passed, including denied write and disable-during-review race |
| Clean stop | Passed after correcting the defect found by live testing |
| Reversible installation | Passed; original binding bytes restored, user data preserved |
| Accurate status documentation | Implemented/fixture/live/blocked features explicitly separated |

## Precise remaining manual checks

1. **Local LLM:** start an OpenAI-compatible endpoint; set its URL/model/actual context limit; run text, streaming, tools and synthetic vision probes. Send a question, stop generation mid-stream, restart Clicky and verify its saved answer. This was not run against an actual model because installation was deferred.
2. **Model-driven MCP:** enable only `workspace / capabilities`, run the tools probe, ask the model to call it, inspect and approve the proposed arguments, then verify the returned result and assistant answer. Manual MCP execution already works without an LLM.
3. **Vision:** run the synthetic image probe first; use Screen/Region, inspect the image, preview the request and explicitly send a question about it. Remove/cancel and confirm no provider request occurs. No neural visual-understanding result is claimed yet.
4. **Physical shortcut and region picker:** physically press Super+Ctrl+Semicolon twice. Use Region to select a small non-sensitive area, then cancel a second selection with Escape. Confirm correct preview and overlay restoration.
5. **Voice end to end:** speak a known sentence into Talk, finish, review the draft, send it to the verified model. Install a real speech engine if desired, restart, confirm Settings lists it, test Speak, Mute and Stop. Component microphone/STT checks passed, but audible playback and the full spoken model loop remain blocked.
6. **Browser automation:** register a trusted browser MCP server disabled, inspect schemas, enable selected tools, and test a read operation followed by a denied form/message/publish action. No third-party browser server was installed in this run.

Unsupported first-version actions: arbitrary shell, recursive delete, unrestricted keyboard injection, mouse clicking/dragging and automatic provider-specific tokenizer calibration. These are not disguised as working features.
