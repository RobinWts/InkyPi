# Plugin Blueprints — adding custom API routes & background work

How an InkyPi plugin exposes its own Flask routes (and runs startup/background logic). Extracted from
the `hardwarebuttons` plugin, which is the most complete worked example —
see [hardwarebuttons.md](hardwarebuttons.md) for the plugin itself.

## The core mechanism

1. A plugin class exposes a **`get_blueprint()` classmethod** returning a Flask `Blueprint`:
   ```python
   class HardwareButtons(BasePlugin):
       @classmethod
       def get_blueprint(cls):
           from . import api          # lazy import — avoid import-time side effects
           return api.hardwarebuttons_bp
   ```
2. At startup, **`register_plugin_blueprints(app)`** in `src/plugins/plugin_registry.py` iterates
   `PLUGIN_CLASSES`, calls `get_blueprint()` on any plugin that has it, and
   `app.register_blueprint(bp)`. `src/inkypi.py` imports and calls it after the built-in blueprints.
3. The blueprint itself lives in the plugin's `api.py`:
   ```python
   from flask import Blueprint, request, jsonify, current_app
   hardwarebuttons_bp = Blueprint("hardwarebuttons_api", __name__)

   @hardwarebuttons_bp.route("/hardwarebuttons-api/save", methods=["POST"])
   def save(): ...
   ```

**Conventions that matter:**
- **Namespace everything.** Give the blueprint a unique name (`"<plugin>_api"`) and prefix all routes
  with a plugin-specific path (`/hardwarebuttons-api/...`) so plugins never collide with core or each
  other. Routes are registered at the app root (no automatic prefix).
- **Lazy-import** the `api` module inside `get_blueprint()` so merely importing the plugin class has no
  Flask side effects.

## ⚠️ Requires a core patch (already applied in this fork)

`register_plugin_blueprints` is **not** in upstream InkyPi by default. It's a one-time **core patch**
that blueprint-using plugins (`pluginmanager`, `hardwarebuttons`) add to two files:
- `src/plugins/plugin_registry.py` — adds the `register_plugin_blueprints(app)` function.
- `src/inkypi.py` — imports it and calls `register_plugin_blueprints(app)` at startup.

The patch is idempotent, shared by all such plugins, and self-applied: `hardwarebuttons/patch_core.py`
(`check_core_patched()` / `patch_core_files()`) is driven by `patch-core.sh`, and the plugin's
settings page auto-runs it if missing. Undo with `git checkout src/plugins/plugin_registry.py src/inkypi.py`.

**Who applies it:** normally **`pluginmanager`** is the first plugin to patch the core — it ships the
**same patch module** as `hardwarebuttons`. (The `pluginmanager` copy in this fork may be out of date;
that's fine — the patch is idempotent and `hardwarebuttons` carries an equivalent copy, so whichever
runs first wins and the other no-ops.)

**In this fork the patch is already present** (`register_plugin_blueprints` exists in both files), so
local blueprint plugins work without action. On a fresh Pi install, installing `hardwarebuttons` (or
`pluginmanager`) applies it.

## Getting core refs & doing startup/background work

A plugin's routes and any background threads usually need the core objects, available on the Flask app:
`current_app.config["DEVICE_CONFIG"]` (the `Config`) and `current_app.config["REFRESH_TASK"]` (the
`RefreshTask`). Two hooks are the idiomatic way to grab them:

- **`@bp.record_once`** — runs once when the blueprint is registered (app startup). Best place to
  capture refs and kick off background work *without needing an HTTP request*:
  ```python
  @hardwarebuttons_bp.record_once
  def _on_blueprint_registered(state):
      app = state.app
      refs = {"device_config": app.config.get("DEVICE_CONFIG"),
              "refresh_task":  app.config.get("REFRESH_TASK"),
              "app": app, "port": 80}
      button_manager.start_if_needed(refs)     # start GPIO worker at boot
  ```
- **`@bp.before_request`** — a fallback to (re)capture refs on the first request and refine
  request-only data such as the port.

**Port differs by environment:** read it from `request.environ.get("SERVER_PORT", "80")` — dev mode
serves on **8080**, production on **80**. Don't hardcode if a route needs to call back into the app.

**Background threads run outside Flask request context.** A worker (e.g. the GPIO thread) must hold its
own captured `refs` and must not touch `current_app`/`request`. Persist what it needs at
registration/first-request time. Guard optional hardware deps so dev machines still load the plugin
(e.g. `gpiozero` import wrapped in try/except → button handling disabled, API still works).

## Persisting plugin-global config

For device-wide plugin config (not per-playlist-instance settings), write under a top-level key in
device.json:
```python
device_config.update_value("hardwarebuttons", {"timings": ..., "buttons": [...]}, write=True)
# read back: device_config.get_config("hardwarebuttons", default={})
```
This is distinct from per-instance `settings` passed to `generate_image()`. Validate untrusted UI
payloads in the route before persisting (the example clamps timings, checks GPIO pin ranges, whitelists
action ids, and validates URLs/script paths).

## Advanced: inter-plugin extension points

A blueprint can also host a **registry that other plugins call into**. `hardwarebuttons/action_registry.py`
lets any plugin register button-bindable actions from its own `record_once`
(`action_registry.register_actions(plugin_id, anytime_actions=..., display_actions=...)`), thread-safe
and executed later from the GPIO thread. This is a good template for "any plugin can contribute X"
features. Full guide ships in the plugin: `PLUGIN_ACTION_REGISTRATION.md`.
