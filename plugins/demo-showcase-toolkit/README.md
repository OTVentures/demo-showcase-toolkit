# Demo Showcase Toolkit

Describe a showcase and select existing demos. This plugin uses the Demo Match MCP connection to create an unlisted client page with separate copies, keeping the originals unchanged.

Use Codex desktop with your own approved Demo Match account, Python 3.9+ and curl. After installation, start a new task and ask:

> Use Demo Showcase to create a showcase called “Conference Demos”. Copy these demos: [paste their links]. Include all videos and captions, keep the originals unchanged, verify the result and give me the published link.

Private means unlisted and accessible by link. This package does not grant account permissions. Hosted-video copying is live validated; PDF imports and external players require per-showcase checks. Copies with missing publication requirements remain in draft.

The default connector is the OTVentures Demo Match service at `https://demos.otventures.vc/mcp`. This release is designed for authorized users of that service; it is not a generic CMS connector. Forking for another deployment requires updating both connector configuration and the media origin in the planner, and revalidating the workflow against that server's schemas.

- [Installation and updates](https://github.com/OTVentures/demo-showcase-toolkit/blob/main/docs/INSTALL.md)
- [Validation and limits](https://github.com/OTVentures/demo-showcase-toolkit/blob/main/docs/VALIDATION.md)
- [Full project guide](https://github.com/OTVentures/demo-showcase-toolkit)
- [Workflow](skills/demo-showcase/SKILL.md)

MIT licensed. The license applies to toolkit code and documentation; connected services and demo assets retain their own access requirements and rights.
