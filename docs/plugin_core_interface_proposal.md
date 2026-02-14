# Plugin–Core Interface Proposal

This document suggests what the InkyPi core should **expose** or **interface with** so that plugins can be powerful and innovative without adding complexity to the core. The goal: keep core small and stable, and move new behaviour into plugins that use a small, well-defined contract.

---

## Current State (What Plugins Have Today)

| Context | What plugins get |
|--------|--------------------|
| **`generate_image(settings, device_config)`** | `device_config` (Config instance), instance `settings`. No direct access to display or refresh task. |
| **`generate_settings_template()`** | Can use `current_app` (Flask) when called from a request; often used to read `DEVICE_CONFIG`. |
| **Plugin API routes (blueprints)** | Only what they put in their own routes; they can use `current_app.config` but this is not documented as a stable plugin API. |

**Config (device_config) already exposes:** `get_config()`, `get_resolution()`, `get_plugins()`, `get_plugin(id)`, `load_env_key()`, `write_config()`, `get_playlist_manager()`, `get_refresh_info()`, `plugin_image_dir`, etc. So plugins can read device config, resolution, orientation, playlists (via playlist_manager), and refresh info.

**What plugins do *not* have a documented, supported way to do:**

- Trigger a display refresh (playlist or single plugin) from their own API.
- Push an image to the display from their own code (e.g. webhook handler).
- Rely on a stable way to get core services (display, refresh task) inside plugin routes.

Below are concrete suggestions to fix that and to add one optional extra (persistent plugin data) without complicating the core.

---

## Principle: Expose Services, Don’t Add Plugin-Specific Logic

- Core should expose **generic** capabilities (e.g. “trigger a refresh”, “show this image”, “read playlists”).
- Core should **not** encode plugin-specific behaviour (e.g. “if plugin is webhook_plugin then…”).
- New behaviour (webhooks, automation, custom UIs) stays in plugins; core only provides the hooks and services.

---

## Suggestion 1: Document and Stabilise “Core Services” in Request Context

**Idea:** In any Flask request (including plugin blueprint routes), core already puts `DEVICE_CONFIG`, `DISPLAY_MANAGER`, and `REFRESH_TASK` in `app.config`. Treat this as the **official** way for plugins to reach core.

**Core change:** None. Only **document** that plugin API routes may use:

- `current_app.config['DEVICE_CONFIG']` → Config (device config, playlists, plugins, env keys, etc.).
- `current_app.config['DISPLAY_MANAGER']` → DisplayManager (display an image).
- `current_app.config['REFRESH_TASK']` → RefreshTask (trigger manual refresh).

**Optional, low-complexity addition:** A tiny helper module, e.g. `plugins/core_services.py`, that plugins can call so they don’t depend on raw Flask keys:

```python
# plugins/core_services.py (optional)
def get_device_config():
    from flask import current_app
    return current_app.config['DEVICE_CONFIG']

def get_display_manager():
    from flask import current_app
    return current_app.config['DISPLAY_MANAGER']

def get_refresh_task():
    from flask import current_app
    return current_app.config['REFRESH_TASK']
```

This keeps the “plugin contract” in one place and makes it easy to document and evolve (e.g. add a new key later without every plugin touching `current_app.config`).

**Why it helps:** Plugins with blueprints (webhooks, automation, Plugin Manager, etc.) can safely trigger refreshes and push images without reverse-engineering core.

---

## Suggestion 2: “Trigger Refresh” as a Supported Plugin Operation

**Idea:** Plugins should be able to request “refresh now” from their own API (e.g. webhook or “next slide” button). Core already supports this via `RefreshTask.manual_update(RefreshAction)`.

**Core change:** None. Only **document** that in a plugin route:

- To refresh a **specific playlist item** (same as “display this plugin instance now”):
  - Get `playlist` and `plugin_instance` from `device_config.get_playlist_manager()` (e.g. `get_playlist(name)`, `find_plugin(plugin_id, instance_name)`).
  - Call `refresh_task.manual_update(PlaylistRefresh(playlist, plugin_instance, force=True))`.
- To refresh a **single plugin with given settings** (same as “Update now” in the UI):
  - Call `refresh_task.manual_update(ManualRefresh(plugin_id, plugin_settings))`.

**Documentation:** Add a short “Plugin API and core services” section in `docs/building_plugins.md` that:
- Lists the three `current_app.config` entries (or the helper module).
- Shows a minimal example: “To trigger showing the next playlist item from your plugin’s API, get REFRESH_TASK and device_config, resolve playlist/plugin_instance, then call manual_update(PlaylistRefresh(...)).”

**Why it helps:** Enables “push-based” and “automation” plugins (webhooks, Home Assistant, Node-RED, custom buttons) that need to update the display on demand without adding any new core logic.

---

## Suggestion 3: “Display Image Now” from a Plugin

**Idea:** A plugin should be able to push a PIL image to the display from its own code (e.g. after receiving a webhook or generating content in an API handler).

**Core change:** None. **Document** that in a plugin route:

- Get `display_manager = current_app.config['DISPLAY_MANAGER']`.
- Generate a PIL image (e.g. via the same logic as `generate_image` or custom).
- Get `image_settings` from the plugin’s config if needed: `device_config.get_plugin(plugin_id).get("image_settings", [])`.
- Call `display_manager.display_image(image, image_settings=image_settings)`.

**Why it helps:** Plugins can implement “show this once” flows (notifications, one-off webhook content) without going through the playlist/refresh cycle.

---

## Suggestion 4: Read-Only Playlist and Refresh Info

**Idea:** Plugins may need to know “what is on display now”, “what’s the next plugin”, “when did we last refresh”. All of this is already available via `device_config`.

**Core change:** None. **Document** that:

- `device_config.get_playlist_manager()` gives playlists, active playlist, and per-playlist plugin instances.
- `device_config.get_refresh_info()` gives last refresh time, plugin_id, playlist name, plugin instance name, etc. (see `RefreshInfo` in `model.py`).

Plugins can use this in `generate_image` (they already have `device_config`) or in API routes (via `current_app.config['DEVICE_CONFIG']`).

**Why it helps:** Enables “status” APIs, dashboards, or plugins that adapt behaviour based on current slide or last refresh time, without new core APIs.

---

## Suggestion 5: Optional Persistent Plugin Data (Small Core Addition)

**Idea:** Plugins sometimes need to store small state (e.g. OAuth tokens, cache flags, user preferences) that should survive restarts and ideally live with device config (backup/restore).

**Current workaround:** Plugins can write files under their plugin directory or use env vars. That works but is not standardised and not clearly “backed up with config”.

**Proposal:** Add a minimal, generic API on Config, e.g.:

- `device_config.get_plugin_data(plugin_id, key, default=None)`  
- `device_config.set_plugin_data(plugin_id, key, value, write=True)`  

Storage could be a sidecar JSON key in `device.json` (e.g. `"plugin_data": { "plugin_id": { "key": value } }`) or a single `plugin_data.json` next to `device.json`. Core only stores and retrieves by plugin_id and key; it does not interpret values.

**Core change:** Small. Config gains a few lines to read/write a `plugin_data` structure and persist it with `write_config()`. No plugin-specific logic.

**Why it helps:** Enables plugins that need persistent state (tokens, toggles, counters) without each plugin inventing its own file format or location. Keeps complexity in plugins; core stays a generic key-value store per plugin.

---

## Suggestion 6: Do *Not* Add Complex Hooks Into the Refresh Loop (Yet)

**Idea:** One could add “plugin hooks” into the refresh loop (e.g. “before next plugin”, “after display”). That would increase core complexity (ordering, errors, lifecycle). A simpler approach is:

- Keep the refresh loop as it is.
- Let plugins that need to “inject” updates do it via **trigger refresh** (Suggestion 2) or **display image** (Suggestion 3) from their own API.

So: no new core hooks for now. Document trigger-refresh and display-image as the supported extension points. If later the project wants “run plugin code every N minutes” or “before/after refresh”, that can be a separate, careful design.

---

## Summary Table

| Suggestion | Core change | Enables |
|------------|-------------|--------|
| 1. Document (and optionally wrap) core services in request context | None / small helper module | Plugins can safely use DEVICE_CONFIG, DISPLAY_MANAGER, REFRESH_TASK in API routes |
| 2. Document “trigger refresh” from plugins | None | Webhooks, automation, “next slide”, “show this instance now” from plugin APIs |
| 3. Document “display image now” from plugins | None | One-off content, notifications, webhook-driven display from plugin APIs |
| 4. Document playlist and refresh_info access | None | Status APIs, “what’s on screen”, “when did we last refresh” |
| 5. Optional get/set_plugin_data on Config | Small addition to Config | Persistent plugin state (tokens, prefs) without ad-hoc files |
| 6. No refresh-loop hooks for now | None | Keeps core simple; use trigger/display as extension points |

---

## Example: What Becomes Possible With 1–4 Only

- **Webhook plugin:** Receives POST, generates image, calls `get_display_manager().display_image(image)` (Suggestion 3).
- **“Next slide” API:** Plugin route gets active playlist and current index, computes next, calls `get_refresh_task().manual_update(PlaylistRefresh(playlist, next_instance, force=True))` (Suggestion 2).
- **Status API:** Plugin route uses `get_device_config().get_refresh_info()` and `get_playlist_manager()` to return “current slide”, “last refresh”, “active playlist” (Suggestion 4).
- **Plugin Manager:** Already uses its blueprint; with documented core services it can reliably trigger a refresh after install/uninstall if desired (Suggestion 1–2).

All of the above use existing core behaviour; the only change is **documenting and optionally wrapping** the existing `app.config` and refresh/display APIs so plugins have a clear, supported contract.

---

## Suggested Next Steps

1. **Document** in `docs/building_plugins.md` (or a dedicated “Plugin API” page):
   - That plugin blueprint routes may use `current_app.config['DEVICE_CONFIG']`, `['DISPLAY_MANAGER']`, `['REFRESH_TASK']`.
   - Minimal examples for “trigger playlist refresh” and “display image now” and “read refresh/playlist info”.
2. **Optionally** add `plugins/core_services.py` with the three getters and point plugin authors there.
3. **Optionally** add `get_plugin_data` / `set_plugin_data` on Config and document them for plugins that need persistent state.

This keeps core complexity minimal while making it possible for plugins to implement powerful, new behaviour (webhooks, automation, status, one-off display) in a supported way.
