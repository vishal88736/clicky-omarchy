# MCP server configuration

Clicky uses the official Python MCP **2.3** SDK. The client initializes sessions, negotiates protocol capabilities, follows paginated tool discovery, validates JSON schemas and routes calls to their owning server. The bundled servers use the SDK's `MCPServer`; this is not a custom protocol shim.

## Included connections

`workspace` exposes capabilities, bounded visible-directory listing, UTF-8 file reads/writes and fixed read-only Git operations. Initial roots contain only the project's `docs/`. File operations reject traversal, hidden paths, non-regular files and symlink components using directory descriptors and `O_NOFOLLOW`. Writes are atomic and bounded to 32 KiB. There is no recursive delete or arbitrary shell.

`desktop` exposes capabilities, explicit active-window/window-list reads, supported Lua focus/close actions, allowlisted application/URL launching, fixed command aliases, pointer movement and restricted single-line text input. All calls require approval. Screen capture is a separate local UI action with preview, not a silent MCP upload. Keyboard injection is disabled by default; `input_classes` must explicitly allow a nonterminal application. Arbitrary clicking, drag and unrestricted key injection are not provided.

## Enable, inspect and invoke

Open **Tools** to inspect the actual negotiated protocol and discovered schemas. Enable or disable a server or individual tool; these settings persist. **Invoke a tool** selects a discovered schema and accepts JSON arguments. The review dialog displays its server, tool, arguments and effects; **Approve once** runs exactly that proposal. **Activity** shows its result. Persistent activity stores event names/status/times; detailed payloads remain limited to the current session.

Disabling a tool during an approval wait prevents its execution. Disconnection, malformed arguments, excessive results and deadlines fail closed. A cancelled call closes its connection so a hidden action is not left running; use **Reconnect** afterward. Stdio/HTTP tests exercise real SDK sessions, including unavailable servers and permission failures.

## Register another server

Use **Register server**, review its trust warning, and paste one specification. New registrations start disabled. Configuration is `~/.config/clicky/config.json`; see `config.example.json` for placeholders. Secrets belong in GNOME Keyring or environment references.

```json
{
  "id": "my_local_server",
  "transport": "stdio",
  "command": "/absolute/path/to/trusted-server",
  "args": [],
  "env_refs": {"SERVICE_TOKEN": "env:MY_MCP_TOKEN"},
  "enabled": false,
  "disabled_tools": []
}
```

For Streamable HTTP, use `"transport": "streamable_http"`, `"url": "http://127.0.0.1:9000/mcp"` and optional `"header_refs": {"Authorization": "my-server-auth"}`. For older HTTP+SSE servers use `"transport": "sse"` and the server's `/sse` URL. These transports were all tested locally with real SDK servers. Remote HTTP is rejected; use HTTPS.

A Keyring header reference stores the entire intended header value, including any required `Bearer ` prefix. Create it without exposing the value in argv:

```sh
secret-tool store --label='Clicky MCP authorization' application clicky entry my-server-auth
```

Enter the secret at the prompt. The JSON contains only `my-server-auth`. Never include actual tokens in command arguments, `env`/`headers` dictionaries, tool descriptions or committed examples.

Stdio servers execute trusted code with your OS account's privileges. Clicky restricts **its bundled tools**; it cannot sandbox an arbitrary external executable. Browser automation can be connected as another trusted MCP server, but no browser-control server was installed or verified in this run. Submission, messaging and publishing tools still require one-use approval. Existing Codex/Claude MCP/auth configuration is not imported automatically.

To change filesystem roots, stop Clicky, edit `roots` to existing absolute directories you explicitly permit, then restart; do not broaden to `/` or credential directories. Reconnect bundled servers after changing roots. Configure command aliases only as trusted absolute executable/argv arrays. Never use a shell interpreter as an alias.
