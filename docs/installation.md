# Installation and local model setup

The audited machine already had the Qt toolchain, capture tools, audio tools, OCR and Voxtype model. Only project `.venv` dependencies were installed. No system packages or GPU settings were changed. The app is installed per user, without root or modifications to `/usr/share/omarchy`.

## Build

```sh
git clone https://github.com/vishal88736/clicky-omarchy.git
cd clicky-omarchy
bin/build
bin/test
bin/test-ui
bin/clicky open
```

The build uses the installed `/usr/bin/python` 3.14, uv, qmake6 and make. Qt modules: Core, Gui, Qml, Quick, QuickControls2, Network, TextToSpeech and Wayland; layer-shell-qt is required for the companion; Qt Test is used by the native harness. Targeted runtime: Omarchy 4, Qt 6.12, Hyprland 0.56 Lua configuration. GTK is not required by Clicky. Runtime helpers: `hyprctl`, `grim`, `slurp`, `tesseract`, `pw-record`, `voxtype`, and `secret-tool`. Capture, OCR and voice failures are surfaced in the interface when their optional helpers are absent.

`bin/build` links in `build/native/` and publishes the finished executable atomically to `build/clicky`, keeping the installed launch path available during compilation. Restart the user service after an update to run the new code. Clean exit flushes the current draft before stopping the worker, including text typed before its debounce timer fired.

## Install the launcher, shortcut and service

```sh
bin/install
```

Default shortcut: **Super+Ctrl+Semicolon**. The installer checks live bindings, refuses collisions and existing destination files, saves a private backup, then appends one marked `dofile` block to `~/.config/hypr/bindings.lua`. Its own Lua file floats only the `clicky` app ID. It validates `hyprctl reload` and `hyprctl configerrors` and enables `clicky.service` under `graphical-session.target`.

Alternative fresh-install options:

```sh
bin/install --hotkey 'SUPER + CTRL + F12' --no-autostart
```

Do not run this second command over an existing installation. To change the integration, uninstall it first; history and settings remain. The project checkout must stay in place because the user-local launcher points to it. Build again after moving or updating the checkout, then reinstall the integration if the path changed. No release binary or Arch package is claimed.

```sh
clicky open
clicky toggle
clicky hide
clicky status
clicky check --json
systemctl --user stop clicky.service
systemctl --user start clicky.service
systemctl --user disable --now clicky.service
```

`clicky stop` stops a directly launched instance. For the service-managed instance, use `systemctl --user stop clicky.service` so systemd knows the intended stopped state. A shortcut can launch Clicky again even when autostart is disabled.

## Connect a local model

No LLM is bundled or downloaded. Local model setup was explicitly deferred during implementation. Start an OpenAI-compatible server separately, then in **Settings**:

1. Enter its base URL including `/v1`, exact model ID, actual context-window size, and response budget; save.
2. Use **Discover models** to confirm connectivity. Model discovery alone does not verify capabilities.
3. Run **text**, then optionally **stream**, **tools** and **vision** probes. The probes use synthetic content; the vision probe contains a generated blue square. A tool probe never executes a desktop action.
4. Type a question, use **Inspect / Ctrl+Enter** to review the exact request, then explicitly send it. Enter/Ask submits ordinary typed messages; screen attachments always force review.

The compatible adapter supports SSE or ordinary responses, tool-call loops, image_url content, usage reports and cancellation. Each capability stays disabled/unverified until its own probe passes. A model that can answer text is not assumed to understand images or call tools. Provider/model changes invalidate prior probe results. Tool schemas consume context: disable unused tools if the conservative request budget is exceeded. The UTF-8 byte estimate is not a model-specific tokenizer measurement; image and response reserves are additional allowances.

Optional authentication goes through the masked key field to GNOME Keyring. Local endpoints without authentication need no key. Environment references such as `env:CLICKY_LOCAL_KEY` are supported in configuration; do not put credentials in JSON, argv, Git, or this example file. HTTP is accepted only on loopback; a hosted endpoint must use HTTPS, with no credentials embedded in its URL. There is no automatic remote fallback.

## Local speech

**Talk** records at 16 kHz mono, **Finish recording** invokes the installed local Voxtype Whisper model and puts text in the draft. This does not alter the existing Voxtype daemon or clipboard. Stop cancels recording/transcription; the recording limit is 60 seconds. The public JFK speech sample was recognized using the existing model; microphone format was separately verified.

Qt speech plugins were present but their real engines were missing (`libflite.so.1`, `libspeechd.so.2`). Playback therefore remains unavailable on the audited installation. If desired, install a local engine with `omarchy pkg add flite`, restart Clicky, and confirm Settings reports a real speech engine before testing **Speak**. The Qt mock plugin is explicitly excluded from audible playback. No paid voice service is required.

## Assistant controls

`clicky open` shows the prompt, `clicky hide` dismisses it, and `clicky info` reports
non-secret UI flags. Use the gear for settings and ≡ for history. The prompt is
pinned across workspaces by its own user rule. There is no cursor follower or
background pointer polling. Visual guides are disabled by default and can be
explicitly enabled in Settings; they display a short-lived target only.
