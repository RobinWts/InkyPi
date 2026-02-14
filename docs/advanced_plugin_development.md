# Advanced Plugin Development

This guide covers how to build plugins that go beyond the basics: plugins that expose their own API routes and interact with InkyPi core to trigger refreshes, push images to the display, and read playlist and refresh status. It assumes you have read [Building InkyPi Plugins](building_plugins.md) and know how to create a plugin, implement `generate_image`, and add a settings template.

**Core requirements:** Everything in this guide works with **only** the [plugin blueprint registration](plugin_core_interface_proposal.md) in core (i.e. `register_plugin_blueprints(app)` in the plugin registry and plugins implementing `get_blueprint()`). No other core changes are required. Core already provides `app.config['DEVICE_CONFIG']`, `['DISPLAY_MANAGER']`, and `['REFRESH_TASK']`, plus the documented APIs (`RefreshTask.manual_update`, `PlaylistRefresh`, `ManualRefresh`, `DisplayManager.display_image`, `Config` methods, `PlaylistManager`, `RefreshInfo`, etc.).

**Contents:**

1. [Prerequisites: Plugin with a Blueprint](#1-prerequisites-plugin-with-a-blueprint)
2. [Core Services in Request Context](#2-core-services-in-request-context)
3. [Triggering a Display Refresh from Your Plugin](#3-triggering-a-display-refresh-from-your-plugin)
4. [Pushing an Image to the Display](#4-pushing-an-image-to-the-display)
5. [Reading Playlist and Refresh Status](#5-reading-playlist-and-refresh-status)
6. [Storing Persistent Plugin Data](#6-storing-persistent-plugin-data)
7. [Complete Example: Remote Control Plugin](#7-complete-example-remote-control-plugin)

---

## 1. Prerequisites: Plugin with a Blueprint

To use the features in this guide, your plugin must expose API routes via a Flask Blueprint and implement `get_blueprint()`. If you have not done that yet:

1. Create an `api.py` in your plugin directory and define a Blueprint with routes (e.g. under `/<plugin_id>-api/...`).
2. In your plugin class, add:
   ```python
   @classmethod
   def get_blueprint(cls):
       from . import api
       return api.your_bp
   ```

See [Adding API routes (optional)](building_plugins.md#adding-api-routes-optional) in the main plugin guide. Once your blueprint is registered, your route handlers run inside a Flask request context and can access core services as described below.

---

## 2. Core Services in Request Context

Inside any Flask request—including your plugin’s API routes—InkyPi stores three core objects in the app config. You can use them to drive the display and refresh behaviour from your plugin.

### What Is Available

| Key | Type | Purpose |
|-----|------|--------|
| `DEVICE_CONFIG` | `Config` | Device config, playlists, plugins list, env keys, resolution, refresh info. |
| `DISPLAY_MANAGER` | `DisplayManager` | Push a PIL image to the display. |
| `REFRESH_TASK` | `RefreshTask` | Trigger a manual refresh (playlist item or single plugin with settings). |

### How to Access Them

In any route handler (including your plugin’s blueprint routes), use Flask’s `current_app`:

```python
from flask import current_app

def my_route():
    device_config = current_app.config["DEVICE_CONFIG"]
    display_manager = current_app.config["DISPLAY_MANAGER"]
    refresh_task = current_app.config["REFRESH_TASK"]
    # ...
```

**Important:** These are only available when your code runs during an HTTP request (e.g. in a blueprint route). They are not available in `generate_image()` or during import; there, you only have the arguments passed by core (e.g. `device_config` in `generate_image`).

### What Config (device_config) Exposes

When you have `device_config` (from `generate_image` or from `current_app.config["DEVICE_CONFIG"]`), you can use:

| Method or attribute | Description |
|---------------------|-------------|
| `get_config(key=None, default={})` | Get a device config value, or the full config dict if `key` is None. |
| `get_resolution()` | Returns `(width, height)` for the display. |
| `get_plugins()` | List of plugin config dicts (from plugin-info.json and order). |
| `get_plugin(plugin_id)` | Get the config dict for one plugin by id. |
| `load_env_key(key)` | Load a secret from the environment (e.g. API keys). |
| `get_playlist_manager()` | Returns the `PlaylistManager` (playlists, active playlist, find plugin, etc.). |
| `get_refresh_info()` | Returns the last `RefreshInfo` (refresh time, plugin_id, playlist, instance). |
| `plugin_image_dir` | Path where plugin instance images are stored. |
| `write_config()` | Persist config to disk (use after changing playlists or plugin data). |

Use these in both `generate_image` and in your API routes (via `current_app.config["DEVICE_CONFIG"]`) to build status APIs, trigger the right playlist item, or resolve image settings for display.

---

## 3. Triggering a Display Refresh from Your Plugin

You can request “refresh now” from your own API (e.g. a “Next slide” button, a webhook, or an automation tool). Core provides two refresh actions; both are triggered via `RefreshTask.manual_update(...)`.

### Option A: Refresh a Specific Playlist Item (Show This Instance Now)

Use this when you want to show a specific plugin instance that is already in a playlist (same as “Display” on the playlist page).

1. Get the playlist and plugin instance from the playlist manager.
2. Call `refresh_task.manual_update(PlaylistRefresh(playlist, plugin_instance, force=True))`.

**Example: “Show this plugin instance now” by playlist name and instance name**

```python
from flask import Blueprint, request, jsonify, current_app
from refresh_task import PlaylistRefresh

my_plugin_bp = Blueprint("my_plugin_api", __name__)

@my_plugin_bp.route("/my_plugin-api/show-instance", methods=["POST"])
def show_instance():
    """Display a specific playlist plugin instance now (e.g. from automation)."""
    data = request.get_json() or {}
    playlist_name = data.get("playlist_name")
    plugin_id = data.get("plugin_id")
    instance_name = data.get("instance_name")

    if not all([playlist_name, plugin_id, instance_name]):
        return jsonify({"success": False, "error": "playlist_name, plugin_id, instance_name required"}), 400

    device_config = current_app.config["DEVICE_CONFIG"]
    refresh_task = current_app.config["REFRESH_TASK"]
    playlist_manager = device_config.get_playlist_manager()

    playlist = playlist_manager.get_playlist(playlist_name)
    if not playlist:
        return jsonify({"success": False, "error": f"Playlist '{playlist_name}' not found"}), 404

    plugin_instance = playlist.find_plugin(plugin_id, instance_name)
    if not plugin_instance:
        return jsonify({"success": False, "error": f"Instance '{instance_name}' not found"}), 404

    try:
        refresh_task.manual_update(PlaylistRefresh(playlist, plugin_instance, force=True))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    return jsonify({"success": True, "message": "Display updated"})
```

**Example: “Next slide” in the active playlist**

Advance the active playlist to the next plugin instance and show it:

```python
import pytz
from datetime import datetime
from refresh_task import PlaylistRefresh

@my_plugin_bp.route("/my_plugin-api/next-slide", methods=["POST"])
def next_slide():
    """Show the next plugin instance in the currently active playlist."""
    device_config = current_app.config["DEVICE_CONFIG"]
    refresh_task = current_app.config["REFRESH_TASK"]
    playlist_manager = device_config.get_playlist_manager()

    active_name = playlist_manager.active_playlist
    if not active_name:
        # No active playlist; determine one from current time
        tz = pytz.timezone(device_config.get_config("timezone", default="UTC"))
        now = datetime.now(tz)
        playlist = playlist_manager.determine_active_playlist(now)
        if not playlist or not playlist.plugins:
            return jsonify({"success": False, "error": "No active playlist or no plugins"}), 400
    else:
        playlist = playlist_manager.get_playlist(active_name)
        if not playlist or not playlist.plugins:
            return jsonify({"success": False, "error": "Active playlist has no plugins"}), 400

    # Get the next plugin in rotation (this advances the internal index)
    plugin_instance = playlist.get_next_plugin()

    try:
        refresh_task.manual_update(PlaylistRefresh(playlist, plugin_instance, force=True))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    return jsonify({
        "success": True,
        "playlist": playlist.name,
        "plugin_id": plugin_instance.plugin_id,
        "instance": plugin_instance.name,
    })
```

### Option B: Refresh a Single Plugin with Given Settings (Manual “Update Now”)

Use this when you want to run a plugin’s `generate_image` with specific settings and show the result (same as “Update now” on the plugin settings page). The plugin does not have to be in a playlist.

1. Build a `plugin_settings` dict (same keys as the plugin’s settings form).
2. Call `refresh_task.manual_update(ManualRefresh(plugin_id, plugin_settings))`.

**Example: Trigger a manual refresh for a plugin by ID with custom settings**

```python
from refresh_task import ManualRefresh

@my_plugin_bp.route("/my_plugin-api/refresh-plugin", methods=["POST"])
def refresh_plugin():
    """Trigger a manual refresh for a plugin with the given settings (like Update now)."""
    data = request.get_json() or {}
    plugin_id = data.get("plugin_id")
    plugin_settings = data.get("plugin_settings", {})

    if not plugin_id:
        return jsonify({"success": False, "error": "plugin_id required"}), 400

    device_config = current_app.config["DEVICE_CONFIG"]
    refresh_task = current_app.config["REFRESH_TASK"]

    if not device_config.get_plugin(plugin_id):
        return jsonify({"success": False, "error": f"Plugin '{plugin_id}' not found"}), 404

    try:
        refresh_task.manual_update(ManualRefresh(plugin_id, plugin_settings))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    return jsonify({"success": True, "message": "Display updated"})
```

**Note:** `manual_update()` blocks until the refresh completes. If the plugin’s `generate_image` raises, that exception is re-raised from `manual_update()`; handle it in your route (e.g. return 500 with the error message).

---

## 4. Pushing an Image to the Display

Sometimes you want to show a one-off image without going through the playlist or a plugin instance (e.g. a notification, or content from a webhook). You can generate a PIL image in your route and send it to the display manager.

### Steps

1. Get `display_manager = current_app.config["DISPLAY_MANAGER"]` and `device_config = current_app.config["DEVICE_CONFIG"]`.
2. Build a PIL `Image` (e.g. with your plugin’s logic or a simple placeholder).
3. Optionally get `image_settings` from the plugin config so the display applies the same enhancements (orientation, resize, etc. are applied by the display manager using device config).
4. Call `display_manager.display_image(image, image_settings=image_settings)`.

**Example: Webhook that shows a simple text image on the display**

```python
from PIL import Image, ImageDraw, ImageFont
from flask import current_app

@my_plugin_bp.route("/my_plugin-api/webhook", methods=["POST"])
def webhook():
    """Accept a webhook and show a short message on the display."""
    data = request.get_json() or {}
    message = data.get("message", "No message")
    # Optional: which plugin's image_settings to use (e.g. for consistent framing)
    plugin_id = data.get("plugin_id", "my_plugin")

    device_config = current_app.config["DEVICE_CONFIG"]
    display_manager = current_app.config["DISPLAY_MANAGER"]

    width, height = device_config.get_resolution()
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Use a default font; in production you might use get_fonts() or a path from static/fonts
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except OSError:
        font = ImageFont.load_default()
    draw.text((20, 20), str(message)[:200], fill=(0, 0, 0), font=font)

    plugin_config = device_config.get_plugin(plugin_id)
    image_settings = (plugin_config.get("image_settings", []) if plugin_config else [])

    display_manager.display_image(img, image_settings=image_settings)
    return jsonify({"success": True, "message": "Display updated"})
```

**Example: Reuse your plugin’s generate_image in a route**

If your plugin class has a `generate_image(settings, device_config)` that returns a PIL image, you can call it from a route and then push the result to the display:

```python
from plugins.plugin_registry import get_plugin_instance

@my_plugin_bp.route("/my_plugin-api/show-custom", methods=["POST"])
def show_custom():
    """Generate an image with our plugin and current settings, then show it."""
    data = request.get_json() or {}
    settings = data.get("settings", {})

    device_config = current_app.config["DEVICE_CONFIG"]
    display_manager = current_app.config["DISPLAY_MANAGER"]
    plugin_config = device_config.get_plugin("my_plugin")
    if not plugin_config:
        return jsonify({"success": False, "error": "Plugin not found"}), 404

    plugin = get_plugin_instance(plugin_config)
    image = plugin.generate_image(settings, device_config)
    image_settings = plugin_config.get("image_settings", [])

    display_manager.display_image(image, image_settings=image_settings)
    return jsonify({"success": True})
```

---

## 5. Reading Playlist and Refresh Status

Plugins can build status APIs or adapt behaviour based on “what is on display now” and “when did we last refresh.” All of this is read-only and comes from `device_config`.

### RefreshInfo (Last Refresh)

`device_config.get_refresh_info()` returns a `RefreshInfo` object with:

| Attribute | Description |
|-----------|-------------|
| `refresh_time` | ISO-formatted string of the last refresh time. |
| `image_hash` | Hash of the last displayed image. |
| `refresh_type` | `"Manual Update"` or `"Playlist"`. |
| `plugin_id` | Plugin that was shown. |
| `playlist` | Playlist name (if refresh_type is Playlist). |
| `plugin_instance` | Plugin instance name (if refresh_type is Playlist). |
| `get_refresh_datetime()` | Returns the refresh time as a `datetime` or `None`. |

### PlaylistManager and Playlists

- `device_config.get_playlist_manager()` returns the `PlaylistManager`.
- `playlist_manager.active_playlist` is the name of the currently active playlist (set by the refresh task).
- `playlist_manager.get_playlist_names()` → list of playlist names.
- `playlist_manager.get_playlist(name)` → `Playlist` or `None`.
- `playlist_manager.determine_active_playlist(current_datetime)` → the playlist that would be active at that time (by time windows).
- A `Playlist` has: `name`, `start_time`, `end_time`, `plugins` (list of `PluginInstance`), `current_plugin_index`, `find_plugin(plugin_id, name)`, `get_next_plugin()`.
- A `PluginInstance` has: `plugin_id`, `name`, `settings`, `refresh`, `latest_refresh_time`, `get_image_path()`.

**Example: Status API that returns current slide and last refresh**

```python
@my_plugin_bp.route("/my_plugin-api/status", methods=["GET"])
def status():
    """Return current display and playlist status (for dashboards or automation)."""
    device_config = current_app.config["DEVICE_CONFIG"]
    refresh_info = device_config.get_refresh_info()
    playlist_manager = device_config.get_playlist_manager()

    last_refresh_dt = refresh_info.get_refresh_datetime() if refresh_info else None
    last_refresh_str = last_refresh_dt.isoformat() if last_refresh_dt else None

    active_playlist = playlist_manager.active_playlist
    current_plugin_id = getattr(refresh_info, "plugin_id", None)
    current_instance = getattr(refresh_info, "plugin_instance", None)
    current_playlist_name = getattr(refresh_info, "playlist", None)

    return jsonify({
        "success": True,
        "last_refresh": last_refresh_str,
        "refresh_type": getattr(refresh_info, "refresh_type", None),
        "active_playlist": active_playlist,
        "current_plugin_id": current_plugin_id,
        "current_plugin_instance": current_instance,
        "current_playlist": current_playlist_name,
        "playlist_names": playlist_manager.get_playlist_names(),
    })
```

**Example: “Who is next?” in the active playlist**

Without advancing the index, you can compute which instance would be shown next by copying the playlist’s logic (or by advancing and then reverting if you prefer not to modify state). Here we only read:

```python
@my_plugin_bp.route("/my_plugin-api/next-preview", methods=["GET"])
def next_preview():
    """Return which plugin instance would be shown next (read-only)."""
    device_config = current_app.config["DEVICE_CONFIG"]
    playlist_manager = device_config.get_playlist_manager()
    active_name = playlist_manager.active_playlist

    if not active_name:
        import pytz
        from datetime import datetime
        tz = pytz.timezone(device_config.get_config("timezone", default="UTC"))
        playlist = playlist_manager.determine_active_playlist(datetime.now(tz))
    else:
        playlist = playlist_manager.get_playlist(active_name)

    if not playlist or not playlist.plugins:
        return jsonify({"success": True, "next": None, "playlist": None})

    # Next index without permanently changing the playlist state
    idx = playlist.current_plugin_index
    if idx is None:
        next_idx = 0
    else:
        next_idx = (idx + 1) % len(playlist.plugins)
    next_instance = playlist.plugins[next_idx]

    return jsonify({
        "success": True,
        "playlist": playlist.name,
        "next_plugin_id": next_instance.plugin_id,
        "next_instance_name": next_instance.name,
    })
```

---

## 6. Storing Persistent Plugin Data

Plugins sometimes need to store small state (e.g. OAuth tokens, feature flags, or counters) that survives restarts. Core does not yet provide a dedicated `get_plugin_data` / `set_plugin_data` API; the recommended approach for now is to store data in your plugin directory.

### File-Based Storage in Your Plugin Directory

Store a JSON (or other) file under your plugin’s directory so it travels with the plugin and is easy to back up.

```python
import os
import json
from flask import current_app

def _plugin_data_path():
    """Path to a JSON file in our plugin directory for persistent data."""
    device_config = current_app.config["DEVICE_CONFIG"]
    # Resolve plugin dir: same pattern as BasePlugin.get_plugin_dir
    from utils.app_utils import resolve_path
    plugins_dir = resolve_path("plugins")
    plugin_dir = os.path.join(plugins_dir, "my_plugin")
    return os.path.join(plugin_dir, "plugin_data.json")

def get_plugin_data(key, default=None):
    """Read a value from our plugin data file (call from request context)."""
    path = _plugin_data_path()
    if not os.path.isfile(path):
        return default
    try:
        with open(path) as f:
            data = json.load(f)
        return data.get(key, default)
    except (json.JSONDecodeError, IOError):
        return default

def set_plugin_data(key, value):
    """Write a value to our plugin data file (call from request context)."""
    path = _plugin_data_path()
    data = {}
    if os.path.isfile(path):
        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    data[key] = value
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
```

Use these only from within a request (where `current_app` is available), or pass a resolved path into non-request code. If core later adds `device_config.get_plugin_data(plugin_id, key)` / `set_plugin_data(...)`, you can switch to that for storage that is backed up with device config.

---

## 7. Complete Example: Remote Control Plugin

The following is a minimal but complete plugin that exposes:

- **GET /remote-api/status** – current slide and last refresh.
- **POST /remote-api/next** – show the next slide in the active playlist.
- **POST /remote-api/show** – show a specific playlist instance by name.

It assumes the plugin `id` is `remote`; routes are under `/remote-api/` (recommended naming: `/<plugin_id>-api/...`).

**Directory structure:**

```
plugins/remote/
    ├── remote.py
    ├── api.py
    ├── plugin-info.json
    ├── icon.png
    └── settings.html   (optional; can be minimal)
```

**remote.py**

```python
from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image

class Remote(BasePlugin):
    """Remote control plugin: API only, no display content of its own."""

    @classmethod
    def get_blueprint(cls):
        from . import api
        return api.remote_bp

    def generate_image(self, settings, device_config):
        # This plugin is API-only; return a placeholder if ever used in a playlist
        w, h = device_config.get_resolution()
        return Image.new("RGB", (w, h), color=(240, 240, 240))
```

**api.py**

```python
import pytz
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from refresh_task import PlaylistRefresh

remote_bp = Blueprint("remote_api", __name__)


def _device_config():
    return current_app.config["DEVICE_CONFIG"]


def _refresh_task():
    return current_app.config["REFRESH_TASK"]


def _playlist_manager():
    return _device_config().get_playlist_manager()


@remote_bp.route("/remote-api/status", methods=["GET"])
def status():
    """Return current display and last refresh info."""
    device_config = _device_config()
    refresh_info = device_config.get_refresh_info()
    pm = _playlist_manager()

    last_dt = refresh_info.get_refresh_datetime() if refresh_info else None
    return jsonify({
        "success": True,
        "last_refresh": last_dt.isoformat() if last_dt else None,
        "refresh_type": getattr(refresh_info, "refresh_type", None),
        "active_playlist": pm.active_playlist,
        "plugin_id": getattr(refresh_info, "plugin_id", None),
        "plugin_instance": getattr(refresh_info, "plugin_instance", None),
        "playlist": getattr(refresh_info, "playlist", None),
        "playlist_names": pm.get_playlist_names(),
    })


@remote_bp.route("/remote-api/next", methods=["POST"])
def next_slide():
    """Show the next plugin instance in the active playlist."""
    pm = _playlist_manager()
    active_name = pm.active_playlist
    if not active_name:
        tz = pytz.timezone(_device_config().get_config("timezone", default="UTC"))
        playlist = pm.determine_active_playlist(datetime.now(tz))
    else:
        playlist = pm.get_playlist(active_name)

    if not playlist or not playlist.plugins:
        return jsonify({"success": False, "error": "No active playlist or no plugins"}), 400

    plugin_instance = playlist.get_next_plugin()
    try:
        _refresh_task().manual_update(PlaylistRefresh(playlist, plugin_instance, force=True))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    return jsonify({
        "success": True,
        "playlist": playlist.name,
        "plugin_id": plugin_instance.plugin_id,
        "instance": plugin_instance.name,
    })


@remote_bp.route("/remote-api/show", methods=["POST"])
def show_instance():
    """Show a specific playlist instance. Body: playlist_name, plugin_id, instance_name."""
    data = request.get_json() or {}
    playlist_name = data.get("playlist_name")
    plugin_id = data.get("plugin_id")
    instance_name = data.get("instance_name")
    if not all([playlist_name, plugin_id, instance_name]):
        return jsonify({"success": False, "error": "playlist_name, plugin_id, instance_name required"}), 400

    pm = _playlist_manager()
    playlist = pm.get_playlist(playlist_name)
    if not playlist:
        return jsonify({"success": False, "error": "Playlist not found"}), 404
    plugin_instance = playlist.find_plugin(plugin_id, instance_name)
    if not plugin_instance:
        return jsonify({"success": False, "error": "Instance not found"}), 404

    try:
        _refresh_task().manual_update(PlaylistRefresh(playlist, plugin_instance, force=True))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    return jsonify({"success": True, "message": "Display updated"})
```

**plugin-info.json**

```json
{
    "display_name": "Remote",
    "id": "remote",
    "class": "Remote",
    "repository": ""
}
```

### Testing the Remote plugin

After adding the `remote` plugin to `src/plugins/` and restarting InkyPi:

- **Status:** `curl http://your-pi/remote-api/status`
- **Next slide:** `curl -X POST http://your-pi/remote-api/next`
- **Show instance:** `curl -X POST http://your-pi/remote-api/show -H "Content-Type: application/json" -d '{"playlist_name":"Default","plugin_id":"clock","instance_name":"My Clock"}'`

Use your device's hostname or IP and the correct port (e.g. 8080 in dev mode).

---

## See also

- [Building InkyPi Plugins](building_plugins.md) – plugin basics, settings, rendering, publishing.
- [Plugin–Core Interface Proposal](plugin_core_interface_proposal.md) – design rationale for exposing core services to plugins.

