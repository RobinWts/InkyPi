# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

InkyPi is a Flask web app that drives an E-Ink display from a Raspberry Pi. A web UI configures
"plugins" (clock, weather, calendar, image feeds, etc.); a background thread periodically renders
the active plugin to a `PIL.Image` and pushes it to the physical display. The entire app can run
**without hardware** via `--dev` mode, which swaps the real display for a mock that writes PNGs to disk.

## Commands

```bash
# Run the dev server (mock display, port 8080, uses src/config/device_dev.json)
devbox run dev                  # preferred: devbox sets up venv + chromium + deps
# or, with a manual venv:
python src/inkypi.py --dev      # production mode (no --dev) binds port 80 and needs real hardware

# Tests
pytest                          # all tests (testpaths=tests, see pytest.ini)
pytest tests/test_model.py      # one file
pytest tests/test_model.py::TestPlaylist::test_is_active  # one test

# Vendored JS/CSS (select2, fullcalendar, chart.js) — required before first run
bash install/update_vendors.sh
```

Dev requirements are in `install/requirements-dev.txt` (no Pi-only packages like `inky`/`cysystemd`).
Open http://localhost:8080 after starting. Rendered output lands in `mock_display_output/` (latest run + timestamped history).

**Never run install/update/systemctl commands automatically** — provide them for the user to run.
Do not assume access to a physical e-ink display.

## Architecture

`src/inkypi.py` is the entrypoint. On startup it:
1. Builds `Config` (`src/config.py`) — loads `device.json` (or `device_dev.json` in `--dev`), reads every
   plugin's `plugin-info.json`, and hydrates the playlist/refresh model objects.
2. Creates a `DisplayManager` (`src/display/display_manager.py`) which picks a backend from `display_type`:
   `mock` → `MockDisplay`, `inky` → `InkyDisplay`, `epd*in*` (fnmatch) → `WaveshareDisplay`. Hardware
   display imports are wrapped in try/except so the app still runs on non-Pi machines.
3. Starts `RefreshTask` (`src/refresh_task.py`) — a daemon thread that is the heart of the app.
4. Registers Flask blueprints from `src/blueprints/` and, generically, from any plugin exposing `get_blueprint()`.

### The refresh loop (`refresh_task.py`)
A single background thread waits on a `threading.Condition` for `plugin_cycle_interval_seconds` or until
notified. Each cycle it either services a **manual update** (from the web UI, via `ManualRefresh`) or
picks the next plugin from the active playlist (`PlaylistRefresh`). It renders the plugin to an image,
hashes it (`compute_image_hash`), and **only pushes to the display if the hash changed** — this matters
because e-ink refreshes are slow/visible. `manual_update()` blocks the caller on `refresh_event` and
re-raises any exception the thread caught, so web requests surface plugin errors synchronously.

### Config & persistence (`config.py`, `model.py`)
There is no database. State lives in a single JSON file (`src/config/device.json` for prod,
`device_dev.json` for dev) that `Config.write_config()` rewrites in place. `model.py` defines the
domain objects serialized into it:
- `PlaylistManager` → `Playlist` → `PluginInstance`. A playlist is a time window (`start_time`–`end_time`,
  supports midnight wrap); the active playlist is the one whose window contains "now" with the **shortest**
  range winning (narrowest window = highest priority). `PluginInstance.should_refresh()` handles both
  `interval` and `scheduled` (HH:MM) refresh modes.
- `RefreshInfo` tracks the last displayed image's metadata (hash, time, plugin).
- Secrets are **not** in the JSON config — they go in `.env` and are read via `Config.load_env_key()`.

## Plugin system (`src/plugins/`) — this is where almost all work happens

Each plugin is a self-contained folder `src/plugins/{id}/` discovered at startup by the presence of
`plugin-info.json`. The folder name **is** the plugin `id` (lowercase, no spaces) and must match the
`.py` filename and the `id` field in the manifest.

```
plugins/{id}/
  {id}.py            # class inheriting BasePlugin (name set by "class" in manifest)
  plugin-info.json   # {"display_name","id","class","repository"}
  settings.html      # optional: web-UI form; input `name`s become keys in `settings`
  icon.png           # optional: shown in web UI
  render/            # optional: HTML/CSS templates for image rendering
```

`BasePlugin` (`src/plugins/base_plugin/base_plugin.py`) is the contract:
- Implement `generate_image(self, settings, device_config) -> PIL.Image`. `settings` is the dict of
  web-form values; `device_config` gives resolution and env secrets. **Raise `RuntimeError` with a clear
  message** on failure (missing key, API error) — it's shown in the web UI.
- Two ways to make an image: build it directly with Pillow, **or** call
  `self.render_image(dimensions, html_file, css_file, template_params)` which renders a Jinja template
  from the plugin's `render/` dir and screenshots it headlessly. `render/*.html` should `{% extends "plugin.html" %}`;
  passing `settings` as `template_params['plugin_settings']` enables the shared frame/color/margin styling.
- Override `generate_settings_template()` to inject extra template vars (set `style_settings=True` for the shared style block).
- Override `cleanup(settings)` to remove files when an instance is deleted.

**HTML→image rendering** (`src/utils/image_utils.py::take_screenshot_html`): uses Playwright if installed,
otherwise falls back to a headless **Chromium/Chrome subprocess**. A browser must be on PATH (devbox provides
chromium on Linux; macOS uses system Google Chrome). This is why `devbox.json` pins chromium and wires up Chrome on macOS.

### Plugin-provided Flask routes (`get_blueprint`)
Plugins that need their own HTTP endpoints (e.g. `pluginmanager`, `noderedpush`) define a Flask
`Blueprint` in an `api.py` and expose it via a `@classmethod get_blueprint(cls)`. `register_plugin_blueprints()`
in `inkypi.py` registers all of them at startup. Some such plugins ship a `patch-core.sh` / `patch_core.py`
that injects this hook into a stock InkyPi install — see `pluginmanager/CORE_CHANGES.md`. When working on a
plugin, prefer the `get_blueprint()` mechanism over editing core files.

## Working constraints (from `.cursorrules`)

- **Stay inside the plugin folder.** Treat core (`config.py`, `refresh_task.py`, `model.py`, `display/`,
  `blueprints/`, `inkypi.py`) as off-limits unless explicitly asked. Adapt the plugin to the existing
  interface rather than bending core to fit a plugin.
- All network calls **must** have explicit timeouts and degrade gracefully (show something useful on failure;
  never crash the refresh thread). Cache expensive/API results to respect rate limits and e-ink refresh costs.
- Prefer stdlib; justify any new dependency and add it to both `install/requirements.txt` and
  `requirements-dev.txt` (and `ws-requirements.txt` if Waveshare-specific). Per global rules, pin exact versions.
- Validate/sanitize user-supplied settings; never log secrets or hardcode keys.
- Settings forms must prepopulate when editing an existing instance — guard on the `loadPluginSettings`
  flag and read `pluginSettings` in `settings.html` (see `docs/building_plugins.md`).

## Key docs
- `docs/development.md` — dev-mode setup (devbox and venv paths), browser requirements per platform.
- `docs/building_plugins.md` — authoritative plugin-authoring guide; read before creating/changing a plugin.
