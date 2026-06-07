# Architecture

InkyPi is an E-Ink display system on a Raspberry Pi: a Flask web UI for configuration, a plugin
architecture for content, and a background refresh task that drives scheduled display updates.

## Key directories

- **`src/inkypi.py`** — Main Flask application entry point
- **`src/plugins/`** — All plugin implementations
- **`src/blueprints/`** — Flask blueprints for web routes (main, settings, plugin, playlist, apikeys)
- **`src/config.py`** — Configuration management (reads/writes device.json)
- **`src/model.py`** — Core data models (PlaylistManager, Playlist, PluginInstance, RefreshInfo)
- **`src/refresh_task.py`** — Background thread that handles scheduled display updates
- **`src/display/`** — Display abstraction layer (Inky, Waveshare, mock displays)
- **`src/utils/`** — Utilities for image processing, fonts, helpers
- **`install/`** — Installation scripts and base configuration
- **`mock_display_output/`** — Where dev mode saves rendered images (`latest.png`)

## Plugin system

Registry pattern with dynamic loading:

1. **Discovery & loading** (`src/plugins/plugin_registry.py`): `load_plugins()` scans plugin dirs for
   `plugin-info.json`, dynamically imports the class named in the manifest, stores instances in
   `PLUGIN_CLASSES` keyed by plugin ID. Plugins can be disabled via `"disabled": true` in device.json.
2. **Base class** (`src/plugins/base_plugin/base_plugin.py`): all plugins inherit `BasePlugin`.
   - Required: `generate_image(settings, device_config)` → `PIL.Image`.
   - Optional: `generate_settings_template()`, `cleanup(settings)`,
     `render_image(dimensions, html_file, css_file, template_params)`.
   - Provides plugin dir access and a Jinja2 env for template rendering.
3. **Registration**: auto-discovered — `config.py`'s `read_plugins_list()` scans subdirs of
   `src/plugins/` for `plugin-info.json` (no manual device.json editing). Each plugin dir needs
   `{plugin_id}.py` (class matching the manifest `class`), `plugin-info.json`, `icon.png`, and
   optional `settings.html`. `plugin_order` in device.json controls UI ordering; new plugins are
   appended automatically.
4. **Blueprints**: plugins may expose Flask blueprints via a `get_blueprint()` classmethod;
   `register_plugin_blueprints(app)` registers them at startup, letting plugins add custom endpoints.
   Mechanics and patterns: [plugin-blueprints.md](plugin-blueprints.md).

## Configuration & state

**Device config** (`src/config.py`): reads `device.json` from `src/config/` (or `device_dev.json` in
dev mode). Manages plugins, playlists, refresh info, device settings (resolution, orientation,
display_type, timezone, API keys). `update_value(key, value, write=True)` persists changes.

**Data models** (`src/model.py`):
- **PlaylistManager** — manages multiple time-based playlists; picks the active one by current time.
- **Playlist** — holds plugin instances; active between start/end (supports windows wrapping past
  midnight, e.g. 21:00–03:00); cycles instances sequentially.
- **PluginInstance** — one plugin config: plugin_id, name, settings dict, refresh config. Refresh is
  interval-based or scheduled (daily HH:MM); tracks `latest_refresh_time`.

## Refresh task (`src/refresh_task.py`)

Background daemon thread, two modes: scheduled playback (cycles active playlist) and manual refresh
(web UI "Display" button). Loop: wait `plugin_cycle_interval_seconds` (default 60 min) → check for
manual requests → pick active playlist → next instance → call `generate_image()` → compare image hash
(skip if unchanged) → display via DisplayManager → update RefreshInfo. Thread-safe via
`threading.Lock`/`Condition`. Manual refresh types: **ManualRefresh** (from settings page) and
**PlaylistRefresh** (specific instance, with force flag).

## Web interface & API

- **Main** (`blueprints/main.py`): `/`, `/api/current_image`, `/api/plugin_order` (POST reorder).
- **Plugin** (`blueprints/plugin.py`): `/plugin/<plugin_id>` (settings form),
  `/images/<plugin_id>/<filename>`, `/plugin_instance_image/<playlist>/<plugin_id>/<instance>`,
  `/update_now` (POST manual update), `/display_plugin_instance` (POST), `/update_plugin_instance/<name>`
  (PUT), `/delete_plugin_instance` (POST, runs cleanup).
- **Playlist** (`blueprints/playlist.py`): `/playlist`, `/add_plugin`, `/create_playlist`,
  `/update_playlist/<name>` (PUT), `/delete_playlist/<name>` (DELETE).
- **Settings** (`blueprints/settings.py`): device config endpoints; also `/shutdown` (POST,
  `{"reboot": true}` runs `sudo reboot`, else `sudo shutdown -h now`).
- **API keys** (`blueprints/apikeys.py`): manage keys in `.env`.

## Display abstraction

**DisplayManager** (`src/display/display_manager.py`): factory by `display_type`; applies orientation,
resize, inversion, enhancement; delegates to InkyDisplay / WaveshareDisplay / MockDisplay. In dev mode
MockDisplay writes `mock_display_output/latest.png`.

## Key file formats

**device.json**
```json
{
  "name": "InkyPi",
  "display_type": "inky|waveshare|mock",
  "resolution": [width, height],
  "orientation": "horizontal|vertical",
  "timezone": "US/Eastern",
  "inverted_image": false,
  "plugin_cycle_interval_seconds": 3600,
  "startup": true,
  "playlist_config": { "playlists": [], "active_playlist": null },
  "refresh_info": { "refresh_time": "...", "image_hash": "...": },
  "plugin_order": ["plugin_id1", "plugin_id2"]
}
```

**plugin-info.json**
```json
{
  "id": "plugin_id",
  "display_name": "Display Name",
  "class": "ClassName",
  "repository": "https://github.com/..."
}
```
