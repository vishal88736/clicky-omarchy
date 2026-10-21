# Existing implementation review — 2026-10-19

Actual public repository source, package definitions and license files were inspected read-only; neither upstream installer nor AppImage was executed.

| Area | HeyClicky Linux | OpenClicky Linux | Clicky decision |
|---|---|---|---|
| License | No LICENSE file in recursive repository tree; GitHub license metadata is null | Actual LICENSE is MIT with contributor copyright and macOS derivation notice | No upstream implementation code copied; preserve Omarchy template attribution |
| UI | Python GTK3/Cairo fullscreen overlay, optional GtkLayerShell, XWayland fallback | Python GTK3 pointer and companion windows | Use installed Qt Quick, proper Wayland app ID and app-specific floating rule |
| Capture | capture.py selects grim, portal or desktop-specific helpers; predictable /tmp screenshot path | screen.py uses Gdk X root-window capture and X monitor geometry | Use grim/slurp with private runtime files and explicit preview |
| Voice | brain.py uploads audio to AssemblyAI, calls providers through curl, streams ElevenLabs to mpv | recorder.py subprocess capture; optional sherpa-onnx offline STT/TTS, backend/provider paths | Reuse installed local Voxtype model and PipeWire; detect actual local Qt speech support |
| Providers | brain.py has OpenAI/Anthropic/Gemini request branches, screenshot encoding and coordinate tags | ask.py has OpenAI/Anthropic/OpenRouter/backend request adapters | Separate compatible provider, capability probes, deadlines, streaming and explicit image submission |
| Input | overlay.py evdev listeners; setup.sh attempts input-group membership and ACL changes | x11.py Xlib XTest/record/shape, explicitly detects Wayland; pyproject depends on python-xlib | No evdev permissions or X11 automation. Narrow supported Hyprland IPC; optional wtype remains restricted |
| MCP | No general MCP manager found in inspected brain/overlay/capture files | Repository agent lane uses Codex; inspected Linux modules do not provide a general MCP connection manager | Official MCP 2.3 SDK client with real stdio/HTTP/SSE sessions and per-call approval |
| Secrets / permissions | curl arguments include authorization headers; setup installs optional packages and changes input permissions | config.py can load/save provider keys as JSON shell settings | Keyring/environment references; no keys in process argv or config; external server trust explicit |
| Maintenance | Last push reported June 2026 at audit time; no releases observed | Recent October 2026 changes; Linux package 0.9.1, README explicitly says X11 only | Neither port was assumed to work on this Wayland machine |

Sources: [HeyClicky repository](https://github.com/asemfateen/Heyclicky_linux), [brain.py](https://github.com/asemfateen/Heyclicky_linux/blob/main/src/brain.py), [overlay.py](https://github.com/asemfateen/Heyclicky_linux/blob/main/src/overlay.py), [capture.py](https://github.com/asemfateen/Heyclicky_linux/blob/main/src/capture.py), [setup.sh](https://github.com/asemfateen/Heyclicky_linux/blob/main/src/setup.sh); [OpenClicky](https://github.com/prasanthsasikumar/openclicky), [license](https://github.com/prasanthsasikumar/openclicky/blob/main/LICENSE), [Linux package](https://github.com/prasanthsasikumar/openclicky/blob/main/linux/pyproject.toml), [X11 integration](https://github.com/prasanthsasikumar/openclicky/blob/main/linux/openclicky_linux/x11.py), [screen capture](https://github.com/prasanthsasikumar/openclicky/blob/main/linux/openclicky_linux/screen.py), [provider adapter](https://github.com/prasanthsasikumar/openclicky/blob/main/linux/openclicky_linux/ask.py), [configuration](https://github.com/prasanthsasikumar/openclicky/blob/main/linux/openclicky_linux/config.py). These are inspection findings, not upstream end-to-end test results.

SDK source and installed signatures were checked against the [official Python SDK](https://github.com/modelcontextprotocol/python-sdk). The installed 2.3 API uses MCPServer, snake_case model attributes and httpx2 for its HTTP client. Window-rule documentation was consulted at the [official Hyprland wiki](https://wiki.hypr.land/Configuring/Basics/Window-Rules/); installed Omarchy Lua helpers are the authoritative syntax for this system.

## Jason Kneen OpenClicky — 21 October 2026

The newly supplied reference is a different repository from the Linux projects
above: [jasonkneen/openclicky](https://github.com/jasonkneen/openclicky), inspected
at `e9eb06a29ff5cd82033d032238f51a936168b05a`. Its MIT license, actual overlay,
response caption and visual guidance source were reviewed. The companion uses
mouse-ignoring, non-key AppKit windows per display. SwiftUI, ScreenCaptureKit and
macOS TCC are platform-specific; they cannot be reused as a Linux desktop backend.

The cursor companion, temporary pointing and compact HUD interaction informed the
new original Qt/layer-shell implementation. No Swift source, art or prompts were
copied. Genuine official-SDK MCP, secure provider configuration, SQLite context
and the Linux voice pipeline are retained from the tested local implementation.
The reference's local HTTP bridge advertises MCP-style tools, which does not itself
prove negotiated MCP transport support. See [the rebuild audit](buddy-rebuild.md)
and [third-party notices](../THIRD_PARTY_NOTICES.md).
