# Desktop buddy rebuild — 21 October 2026

## Read-only re-audit

The existing checkout was clean at `8bef5ed` on `main`, tracking the public
`vishal88736/clicky-omarchy` repository. The installed user service was running.
Its manifest owns five integration files and one marked bindings block. Existing
history, provider configuration and Keyring entries must survive this rebuild.

Current machine: Omarchy **4.0.0.r7195.g3ac4365**, kernel **7.2.8-9-omarchy**,
Hyprland **0.56.2-4** (Lua configuration), Qt **6.12**, layer-shell-qt **6.8**.
`grim`, `slurp`, `pw-record`, `voxtype`, `wtype`, `secret-tool` and qmake6 are
available. Live Hyprland IPC and cursor coordinates work. The current panel has
fractional scaling; screen geometry must come from IPC/QScreen, never constants.
Hyprland reports no configuration errors. The earlier full hardware/tool audit
remains in [system-audit.md](system-audit.md); version changes above supersede it.

## Reference review

Inspected [Jason Kneen's OpenClicky](https://github.com/jasonkneen/openclicky)
at **e9eb06a29ff5cd82033d032238f51a936168b05a**, including its MIT license,
`OverlayWindow.swift`, `CompanionResponseOverlay.swift` and
`OpenClickyVisualGuidanceOverlayModels.swift`.

The important interaction is an animated companion following the pointer, with
temporary captions and visual pointing. Its macOS implementation uses a
transparent, non-key, mouse-ignoring NSWindow per screen. AppKit, SwiftUI,
ScreenCaptureKit and macOS permissions cannot run on Omarchy. Its local HTTP
control bridge advertises MCP-style descriptors; that alone is not a replacement
for negotiated MCP. We retain the existing official MCP SDK client.

No Swift code, third-party artwork, bundled model prompts or credentials are
copied. The new Qt implementation is original, inspired by that interaction.
Attribution links are retained in the README. Existing verified Python storage,
provider, MCP and approval modules are retained; the previous large chat shell
and its screenshots are superseded.

## Architecture and implementation sequence

1. Native Qt companion controller: one transparent input-passthrough layer-shell
   surface per QScreen; keyboard interactivity disabled; bounded asynchronous
   Hyprland cursor IPC, with reconnect and display hotplug handling.
2. Animated QML buddy, captions and temporary guidance without moving the real
   pointer. Separate interactive compact HUD, expandable history and settings.
3. Keep explicit historical message selection, exact request inspection, local
   screenshot review, genuine MCP discovery and one-use tool approvals.
4. Add screenshot-relative guidance parsing with bounds checks and map capture
   pixels back to logical desktop coordinates. Guidance is visual only.
5. Test cursor tracking, actual input passthrough, native UI, persistence,
   context isolation, MCP, cancellation, hotkey integration and clean shutdown.
6. Replace only manifest-owned installation files, validate Hyprland reload,
   publish real application screenshots and update setup/validation documents.

Provider setup remains deferred as requested. No new LLM download or credential
reuse is authorized by that earlier choice. Live inference must be marked
blocked until an endpoint and model are configured; fixtures are labeled as such.
