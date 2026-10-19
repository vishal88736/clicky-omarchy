# System audit — 2026-10-19

Read-only inspection completed before project creation. No packages, settings, services, capture, microphone recording, or credentials were changed during the audit. Only this new project and its documents were then created.

## Detected environment

| Component | Observed result |
|---|---|
| OS / package manager | Omarchy 4.0.0.r7083.g81fd2d2-1, Arch family, pacman 7.1; yay available |
| Kernel / architecture | 7.2.8-9-omarchy, x86_64 |
| Desktop | Hyprland 0.56.2, commit efb50993780079460b0cbed1363e2166a2de1d9f; Wayland session, XWayland 24.1.14 installed |
| Display | One currently connected 1920×1080 panel, 144 Hz, scale 1.25. These are audit observations, never application constants. |
| Hyprland IPC | Live version, monitors, clients, binds and configerrors succeeded outside the agent sandbox; no config errors. 248 bindings. SUPER+CTRL+SEMICOLON has no conflict. |
| Configuration | Lua: ~/.config/hypr/hyprland.lua imports default.hypr.omarchy and personal bindings, input, monitors, looknfeel, autostart. Personal bindings/autostart contain comments only. Packaged files under /usr/share/omarchy are read-only. |
| Audio / portals | PipeWire 1.6.9, WirePlumber 0.5.18, Pulse compatibility; live sources and sinks. Hyprland, GTK and core desktop portals active. GNOME Keyring exposes org.freedesktop.secrets. |
| Capture / OCR | grim 1.5.0, slurp 1.5.0, wl-clipboard 2.3.0, omasnap 1.21, ffmpeg 9.0.2, Tesseract 5.5.3 with English data. Capture itself was not run during the read-only audit. |
| Voice | voxtype 1.1.1 user service active; local ggml-base.en.bin exists. CLI supports transcribe of 16kHz mono WAV, allowing isolated transcription without touching daemon output or clipboard. pw-record/pw-play available. No espeak, piper or speech-dispatcher CLI detected; Qt6 speech installed, engine/voice availability still needs runtime testing. |
| Development | qmake6, make, GCC 16.2, Qt 6.12 Core/Quick/Controls/DBus/SQL/Multimedia/Speech/Wayland, GTK4 4.24, libadwaita 1.10. System /usr/bin/python 3.14.8; PATH Python is mise 3.15.0. Node 26.12.0, npm 11.20, uv 0.13.0. Rust/cargo absent. |
| Hardware | Intel i7-13620H, 10 physical / 16 logical cores; 15 GiB RAM, ~4.1 GiB available at inspection. RTX 4050 Laptop GPU, 6141 MiB VRAM, 5852 MiB free, NVIDIA 615.78.08 verified outside sandbox. |
| Local inference | A modest quantized model is plausible; no throughput measured. No ollama/llama-server, compatible local endpoint, or common LLM cache found. User explicitly chose to leave local model setup for later. |
| AI / MCP | Codex and Claude wrappers, OpenCode installed. Codex metadata lists its managed node_repl MCP; it depends on Codex-specific trusted runtime configuration and is not imported into this app. SDK absent from default Python. PyPI reports official mcp 2.3.0, httpx 0.28.1, jsonschema 4.26.0. |
| Integrations | git 2.56, gh 2.102, Chromium 154, Brave, foot, xdg-open. wtype 0.4 present; no ydotool/dotool/xdotool. Installed wtype alone does not prove compositor input protocol support. |
| Lifecycle | UWSM graphical-session services, user systemd, .desktop launcher conventions; personal autostart.lua is empty apart from comments. No clicky project was present. |

## Constraints and reuse decisions

Agent sandbox initially denied Hyprland, audio and GPU access. Repeating read-only probes with authorized host access succeeded. Do not diagnose these sandbox errors as broken drivers or desktop services. Do not use PATH Python 3.15 for SDK installation when the installed stable system Python 3.14 is available. No full environment, window titles, clipboard contents, credentials, cookies, SSH keys or authentication stores were dumped. Existing AI auth files were checked for existence only. MCP config was inspected as names, transport and environment-variable names, never values.

Reuse Qt Quick and qmake for native Wayland UI, Python in a project virtual environment for the official MCP SDK, SQLite from Python, GNOME Keyring via secret-tool, grim/slurp for deliberate capture, supported Hyprland IPC for window actions, and PipeWire plus local Voxtype for voice input. Keep typed text isolated from desktop input unless an explicitly reviewed action targets a stable window. No raw input-device permissions, sudo, udev changes, unrestricted shell, or X11 automation are needed.

## Exact implementation steps

1. Record source/license review and architecture; initialize this new project without committing or pushing.
2. Create a Qt Quick shell and a private JSON-lines Python worker; isolate persistence, provider, context, MCP, desktop broker and voice modules.
3. Implement OpenAI-compatible local provider configuration, cancellation, SSE/non-streaming responses, explicit capability probes and a SQLite message/restart path. Local model acceptance is blocked by the user-deferred endpoint; use an explicitly labeled HTTP fixture for protocol tests.
4. Add persistent drafts, searchable history, per-message/per-conversation opt-in context, removal, clear, exact request preview and conservative byte-based context budgeting with response/tool reserves.
5. Install only project virtual-environment dependencies; integrate the maintained MCP SDK stdio and HTTP clients, real safe local servers, tool schema validation, per-server/per-tool toggles and per-action approvals.
6. Add narrow local filesystem/Git/approved-command MCP tools; constrain roots and reject symlink escapes. Keep external servers disabled until registered and reviewed. Treat stdio servers as trusted executable code, not sandboxes.
7. Add native single-instance show/hide/focus/stop commands, checked Hyprland keybinding/window rules, launcher, reversible user service and installer manifest. Preserve existing config and refuse file collisions.
8. Add explicit screenshot preview/attachment, local OCR, optional active-window context, capture cleanup and verified-only vision submission.
9. Add bounded push-to-talk capture, separate local Voxtype transcription, mute/cancel and Qt speech engine detection with clear unavailable errors.
10. Run unit, real SDK stdio/HTTP multi-server, failure/cancellation, offscreen UI and host desktop checks; record exact evidence and remaining blocked tests. Provide installation, security, troubleshooting and uninstall procedures.
