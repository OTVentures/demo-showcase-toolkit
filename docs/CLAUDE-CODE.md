# Demo Showcase Toolkit for Claude Code

Use this toolkit from a Claude Code terminal session or from a **local or SSH** session in the Claude Desktop app's Code tab. It is intended for marketers who have an approved Demo Match account. Claude Code plugins are not available in desktop cloud sessions. Cowork and claude.ai web support have not been tested for this toolkit.

## Install

In an interactive Claude Code session, add the marketplace once:

```
/plugin marketplace add OTVentures/demo-showcase-toolkit
```

Then install `demo-showcase-toolkit` from the `otventures-demo-showcase` marketplace. Review its components and choose the scope in the plugin panel:

```
/plugin install demo-showcase-toolkit@otventures-demo-showcase
```

The current release is `1.1.0`. If Claude Code asks to reload plugins, run `/reload-plugins`. Type `/` and select the namespaced skill to confirm it is available:

```
/demo-showcase-toolkit:demo-showcase
```

Claude Code's plugin instructions and naming format are documented in Anthropic's [plugin guide](https://code.claude.com/docs/en/plugins/install).

## Connect your Demo Match account

The plugin provides the Demo Match MCP connection at `https://demos.otventures.vc/mcp`; it does not provide credentials or account permissions. In Claude Code, run:

```
/mcp
```

Select the Demo Match server and complete the browser sign-in when prompted. `/mcp` is also where you can re-authenticate a server after a `401` or `403`. See Anthropic's [MCP authentication guide](https://code.claude.com/docs/en/mcp#authenticate-with-remote-mcp-servers).

If Claude itself reports an expired OAuth session before using any tools, sign back into Claude Code with `/login`. That account login is separate from the Demo Match connection. An already configured, authorized Demo Match connection can be reused; avoid adding another standalone connector for the same endpoint unnecessarily.

If the server connects but creating a client or copying a demo is denied, ask your Demo Match administrator for the needed account permission. “Manage public links” alone may not be sufficient. Installing the plugin never expands your Demo Match access.

## Give Claude this prompt

```
Use Demo Showcase to create a showcase called “Conference Demos”.
Copy these demos: [paste exact Demo Match links or IDs].
Include their approved videos and captions, keep the originals unchanged,
verify the copies, and give me the published showcase link.
```

Use exact links or IDs, a unique showcase title, and only demos you are authorized to copy. Claude should first resolve the source demos and readiness requirements, create draft copies, transfer approved media and captions, compare the originals with the copies, and publish only completed copies. It should retain the sources and make new copies rather than edit, move, unpublish, or delete the originals.

For media uploads, the local execution host must have Python 3.9+ and `curl`; the upload helper requires a POSIX terminal environment (macOS or Linux). Native Windows support is not claimed. Do not paste access tokens into prompts, source files, or tickets.

## Permissions and review

The toolkit does not bypass Claude Code permissions. Keep the normal approval prompts enabled and review the plugin's MCP tools during installation. In the Desktop Code tab, Manual mode asks before edits and commands; your selected permission mode and organization policy still apply. See Anthropic's [Desktop permission modes](https://code.claude.com/docs/en/desktop#choose-a-permission-mode).

This guide documents the supported setup and workflow. It does not claim that full end-to-end demo copying has been live-validated in Claude Code; verify each showcase's returned link, media, captions, and original demos before treating the run as complete.
