# Context Index

Entry point for all background/context docs in this workspace. `CLAUDE.md` stays intentionally
short and points here; the detail lives in these files.

## Read me first
- [history.md](history.md) — running log of notable work and decisions (newest first). **Read this
  to catch up on what recently changed and why.**

## Reference
- [architecture.md](architecture.md) — how InkyPi is put together: directory map, plugin system,
  config & data models, refresh task, web/API endpoints, display abstraction, key file formats.
- [development.md](development.md) — running it locally: dev setup, commands, tests, the headless-Chrome
  rendering requirement, and operational gotchas (dev mode, persistence, threading, caching).
- [plugin-development.md](plugin-development.md) — building/maintaining plugins: workflow, common
  patterns, and **the plugin-repo / "never commit plugins from the fork" rule**.
- [plugin-blueprints.md](plugin-blueprints.md) — how a plugin adds its own Flask API routes and
  startup/background work: `get_blueprint()`, the core blueprint-registration patch, `record_once` /
  `before_request`, capturing core refs, and the inter-plugin action-registry pattern.

## Per-plugin context
- [seniorDashboard_allDay.md](seniorDashboard_allDay.md) — the senior dashboard plugin: what it is,
  how it's structured, its offline/auto-reboot behavior, and where its real repo lives.
- [hardwarebuttons.md](hardwarebuttons.md) — GPIO button-binding plugin; the reference example for
  plugin blueprints, a background worker thread, and the cross-plugin action registry.

## Maintaining this folder
- When you add a new context file, **link it here** under the right heading.
- Keep `CLAUDE.md` lean — new background detail belongs in a notes file referenced from this index,
  not inlined into `CLAUDE.md`.
