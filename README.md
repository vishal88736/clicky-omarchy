# Clicky for Omarchy

A native Qt Quick desktop assistant for Hyprland, with persistent conversations, explicit context selection, and genuine MCP connections. Built on this machine's installed Qt, Wayland capture tools, PipeWire and Voxtype.

**Work in progress:** the user deferred local model installation. No live LLM endpoint is configured. Protocol fixture tests do not prove model quality, vision understanding or model-driven tool use. See [the system audit](docs/system-audit.md) and [architecture](docs/architecture.md).

## Build and launch

Requires Omarchy's Qt 6 toolchain, Python 3.14 and uv. Dependencies are isolated in `.venv`; no system Python packages are modified.

```sh
git clone https://github.com/vishal88736/clicky-omarchy.git
cd clicky-omarchy
sh bin/build
sh bin/clicky open
```

The local model endpoint and model name are configured in **Settings**. Save settings, discover models, and run the text capability probe. Streaming, tool calling and vision each have separate synthetic probes; capabilities are never inferred from a model name. Optional keys go to GNOME Keyring.

## Daily use

- **Ctrl+Enter** previews the exact request before sending it.
- **Ctrl+N** creates a conversation; **Ctrl+K** searches history.
- **Context** beside an older conversation selects individual historical messages. Browsing history alone adds no context.
- **Screen / Region** captures and previews locally. A verified vision endpoint is required before submission. **OCR** runs locally.
- **Talk** starts local recording; finish to transcribe into the draft for review. The microphone stops after 60 seconds.
- **Tools** lists real MCP servers, discovered schemas, per-tool toggles and manual invocation. Every invocation requires approval.
- **Ctrl+.** cancels work; **Escape** hides; **Ctrl+Shift+Q** quits.

```sh
sh bin/test
sh bin/clicky status
sh bin/clicky hide
sh bin/clicky toggle
sh bin/clicky stop
```

## Safety and data

No continuous recording, clipboard scraping, automatic screen upload, imported AI credentials, unrestricted shell, or new input-device permissions. Bundled filesystem tools operate only inside explicitly permitted roots and reject hidden files and symlink escapes. Initially the permitted root is this project's `docs/`. External stdio MCP servers are trusted programs with your account's OS privileges; Clicky cannot sandbox arbitrary server code.

History and drafts live in a private SQLite database in `~/.local/share/clicky/`. Settings in `~/.config/clicky/` contain secret references. Screenshots and microphone audio are temporary. Local history is not encrypted by the app; clearing is logical deletion, not forensic erasure.

## Implementation status

Source is being built and tested incrementally. Test evidence and installation/uninstall documentation will be added as checks run. No feature is declared complete from source alone.

## License

MIT. This is an independent project, unaffiliated with HeyClicky or OpenClicky. No code from the unlicensed HeyClicky Linux repository is included. Native theme behavior follows Omarchy's MIT app templates; see [LICENSE](LICENSE) and [source review](docs/source-review.md).
