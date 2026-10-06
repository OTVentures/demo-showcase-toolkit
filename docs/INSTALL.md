# Installation

## Marketer setup

Ask Codex desktop to install the toolkit from this repository, then sign in to Demo Match with your own approved account if prompted. Start a new task to load the plugin. The assistant can check local prerequisites and explain any account permission gap; no coding is required from the marketer.

The plugin connects to `https://demos.otventures.vc/mcp`. Its configuration contains no credentials. Reuse an existing authorized Demo Match connector when available. Otherwise use the host's normal connection/sign-in flow. Do not paste tokens into chat, configuration files or GitHub issues.

Client creation requires settings authority; demo and media copying require appropriate publishing permissions. A user with only “Manage public links” may not have those permissions. Your Demo Match administrator handles account access. Plugin installation does not grant it.

## Assistant or administrator commands

With a recent Codex CLI installed:

```sh
codex plugin marketplace add OTVentures/demo-showcase-toolkit --ref v1.0.1
codex plugin add demo-showcase-toolkit@otventures-demo-showcase
```

The marketplace name is `otventures-demo-showcase`. Check existing marketplace sources first if it is already configured. Do not overwrite an unrelated source with the same name.

Start a new task after installation; restart the desktop app if the plugin is not visible. The instructions follow the official [OpenAI plugin packaging documentation](https://developers.openai.com/plugins/build/plugins); hosts and managed workspace policies can differ.

## ZIP installation

Download and extract the versioned archive from [GitHub Releases](https://github.com/OTVentures/demo-showcase-toolkit/releases). Preserve its hidden `.agents` and `.codex-plugin` folders. Select the extracted repository root in Codex and ask it to install the toolkit from that folder.

For the installing assistant:

```sh
codex plugin marketplace add /absolute/path/to/extracted/demo-showcase-toolkit-1.0.1
codex plugin add demo-showcase-toolkit@otventures-demo-showcase
```

The path must identify the folder containing `.agents/plugins/marketplace.json`, not the nested plugin folder. Keep that source folder available for future local updates.

## First run

Start with one or two demos you are authorized to copy. Give the assistant a unique showcase title and exact demo links or IDs. It resolves the selection, checks readiness requirements, creates draft copies, transfers media and captions, verifies the originals, then publishes the complete copies. The final response includes the actual showcase link and any incomplete checks.

If a run is interrupted, return to the same task and ask it to resume from the run record. Keep the task's working files until verification completes. A missing result must be reconciled before another create operation.

## Updates and existing local installs

Releases are pinned to a tag in the installation command so a working version remains reproducible. To move to a later release, ask the assistant to inspect the current source and update to the chosen published tag using supported marketplace commands. If following `main`, marketplace upgrade retrieves newer repository content; reinstall the plugin and start a new task to load it.

Earlier local builds may be installed as `demo-showcase-toolkit@personal`. Avoid enabling both that build and the GitHub version in the same task. Confirm the installed versions and finish any active showcase run before switching. Existing published showcases remain on Demo Match independently of plugin installation.

## Troubleshooting

| Symptom | Next step |
| --- | --- |
| Toolkit missing | Start a new task; restart the app; confirm installation and workspace policy. |
| Demo Match tools unavailable | Connect/sign in with your own approved account. |
| Client creation denied | Ask the Demo Match administrator for the required permission. |
| Ambiguous demo name | Supply its exact link or ID. |
| Missing captions | Supply approved tracks or choose a ready demo; do not bypass readiness. |
| Video PUT failed | Let the assistant inspect the existing destination and retry its upload, without creating another video. |
| PDF transfer failed | Keep the incomplete copy in draft and report the unsupported transfer. |
| Browser verification unavailable | Open the returned page manually; do not describe that check as passed. |

Python 3.9+ and curl must be available on the execution host. The terminal upload helper uses POSIX terminal controls on macOS/Linux; native Windows support is not claimed. The plugin does not provide a separate hosted agent or unattended server.
