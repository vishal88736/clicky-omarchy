# Troubleshooting and reversal

## The window does not appear

```sh
systemctl --user status clicky.service
clicky status
clicky open
clicky check --json
hyprctl configerrors
```

Run in the actual Wayland session. A restricted coding sandbox can deny Hyprland, PipeWire and GPU sockets even when the host desktop works. This occurred during the audit; host-access checks succeeded. Do not reinstall drivers from that sandbox symptom alone. `QT_QPA_PLATFORM=offscreen` is only for isolated tests. A missing `.venv` or moved checkout requires rebuilding from the correct path.

The default shortcut is **Super+Ctrl+Semicolon**. Live registration and launcher show/hide were checked; synthetic `wtype` global-hotkey events did not establish physical keyboard activation. Press the chord physically to complete that acceptance check. If your keyboard layout makes it inconvenient, uninstall and reinstall with `--hotkey 'SUPER + CTRL + F12'`, after checking conflicts. The installer never silently replaces an existing binding.

## The model cannot connect

No local LLM server was installed at the user's request. Start your own compatible server and supply its URL and model in Settings. Save first, discover models, then run the text probe. **Inspect / Ctrl+Enter** opens a request preview. **Ask / Enter** submits deliberate typed messages; an attached screenshot always requires preview confirmation. Unverified or unavailable providers report errors and retain the draft. Re-run probes after changing endpoint/model. A provider accepting text is not proof of vision/tool support.

If the context budget is exceeded, remove historical selections, disable unused tool schemas, reduce input, or set the model's actual supported context size. Do not increase the limit beyond what the server/model supports. Tool-result growth can stop a round before a second provider request; this is intentional.

## MCP connection or action failure

Inspect **Tools**, the actual schema and **Activity**. Missing stdio executables, expired header references, wrong transport URLs and SDK/server incompatibilities are visible connection errors. Use **Reconnect** after correcting configuration or cancelling an active call. Do not put secrets in argv to bypass a configuration problem. A file outside a permitted root, hidden file, symlink escape, unregistered command or unsupported input target is intentionally rejected.

Hyprland 0.56 dispatch uses Lua (`hl.dsp.focus`, `hl.dsp.window.close`, `hl.dsp.cursor.move`). Legacy flat dispatcher strings were rejected during testing and replaced. A tool returning `ok` is not sufficient evidence of the requested effect; the broker reads back focus/pointer state.

## Capture or microphone failure

Use the Wayland session and check `grim`, `slurp`, PipeWire and the default input source. Region selection can be cancelled with Escape; the assistant should return. OCR uses installed English Tesseract data. Voice capture/transcription remain local and do not type through the existing Voxtype daemon. Playback was unavailable because real Qt speech-engine libraries were missing; see [installation](installation.md). No audible success is inferred from the Qt mock plugin.

## Stop or disable autostart

```sh
systemctl --user stop clicky.service
systemctl --user disable --now clicky.service
```

For a direct launch, `clicky stop` or Ctrl+Shift+Q exits; Escape and the window close button only hide. A shutdown defect exposed by the first live uninstall test was fixed: explicit quit bypasses the close-to-hide handler, with regression tests for IPC stop and SIGTERM. Use the latest rebuilt binary when testing.

## Clean uninstall

From the checkout:

```sh
bin/uninstall
```

This stops/disables Clicky, removes only its verified owned launcher, icon, service and integration file, removes only the marked bindings block, reloads/validates Hyprland, and preserves history/settings and the private original-config backup. It refuses removal if an owned file/block was modified, so review those changes first. It never resets Omarchy configuration. Live reversal was tested against the original bindings hash, then the application was reinstalled.

Remaining data: `~/.config/clicky/config.json`, `~/.local/share/clicky/`, backups under `~/.local/state/clicky/backups/`, optional Keyring entries and the source checkout/`.venv`. They are deliberately retained. After reviewing/backing up your data, you can remove those app-specific paths yourself. No purge is performed automatically, and no unrelated file or credential is deleted.

## Confirm the cursor follower is removed

`clicky info` reports `following: false`. The application no longer polls cursor
coordinates or creates an idle overlay. `hyprctl layers -j` should show neither
`clicky-buddy` nor `clicky-guidance` during normal use. Visual guides are disabled
by default; an opted-in target marker expires automatically.

Run `.venv/bin/python scripts/verify_desktop.py` for read-only session verification.
Use the configured hotkey or launcher to open the assistant.
