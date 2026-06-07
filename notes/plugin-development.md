# Plugin Development

This fork exists to develop and maintain InkyPi **plugins**. This is the most important file to read
before touching anything under `src/plugins/`.

## ⚠️ Plugins live in their own repos — never commit them from this fork

Each maintained plugin has its **own standalone Git repository** (referenced by the `repository`
field in its `plugin-info.json`). In a normal InkyPi install, plugin repos are **flattened** into
`src/plugins/<id>/` when cloned/installed, so the nested `.git` and original repo layout are lost.

Consequences — follow these strictly:

- **Never commit plugin changes from `src/plugins/<id>/` in this fork.** Committing here would not
  reach the plugin's real repo and can break the flattened layout.
- **Develop and test here**, then **copy the changed files into the plugin's standalone repo** and
  commit from there. Verify the copies are byte-identical before committing.
- The standalone repo usually nests the plugin under a folder named after the plugin id, e.g.
  `<plugin-repo>/<plugin_id>/...` — mirror the same relative paths (`render/`, etc.) when copying.
- Keep dev-only tweaks (e.g. temporarily stubbing a reboot for testing) **in this fork only** — do
  not copy them back to the plugin repo.

See per-plugin notes for the exact repo path and copy mapping, e.g.
[seniorDashboard_allDay.md](seniorDashboard_allDay.md).

## New-plugin workflow

1. `src/plugins/{plugin_id}/` directory.
2. `{plugin_id}.py` with a class inheriting `BasePlugin`.
3. Implement `generate_image(settings, device_config)`:
   - resolution via `device_config.get_resolution()`,
   - settings (form inputs) as a dict,
   - return a `PIL.Image` or `raise RuntimeError("message")`.
4. `plugin-info.json` (id, display_name, class, optional repository).
5. Optional `settings.html` form template.
6. `icon.png`.
7. Restart the dev server to load it; it then appears in the web UI and can be added to playlists.

For HTML-based rendering: put templates in `render/` (HTML + optional CSS), call
`self.render_image(dimensions, "template.html", "style.css", template_params)`. BasePlugin's
`plugin.html` base template provides fonts and style options (frame, background, text color, margins —
passed via `plugin_settings`).

## Common patterns

**Settings template params**
```python
def generate_settings_template(self):
    template_params = super().generate_settings_template()
    template_params['options'] = [...]          # data for settings.html
    template_params['style_settings'] = True    # text/background color options
    return template_params
```

**Secrets from .env**
```python
api_key = device_config.load_env_key('OPENAI_API_KEY')
if not api_key:
    raise RuntimeError("API key not configured")
```

**Persist state between refreshes** (settings act as per-instance key-value storage, saved by refresh_task)
```python
current_index = int(settings.get("current_index", 0))
settings["current_index"] = (current_index + 1) % total_items
```

**Cleanup on deletion** (override when a plugin stores external files)
```python
def cleanup(self, settings):
    file_path = settings.get("uploaded_file")
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
```

## Custom API routes / background work

To add Flask endpoints, startup hooks, or a background worker (not just a rendered image), give the
plugin a blueprint. See [plugin-blueprints.md](plugin-blueprints.md) for the full mechanics
(`get_blueprint()`, the core blueprint-registration patch, `record_once`/`before_request`, capturing
core refs, dev-vs-prod port) — worked example: [hardwarebuttons.md](hardwarebuttons.md).

## Error handling at the refresh boundary

`generate_image()` raising `RuntimeError` is caught and logged by `refresh_task`; on a scheduled
(interval) refresh the display simply isn't updated (no error image), while a manual refresh re-raises
to the web endpoint and returns a JSON error. There is no retry. A plugin that wants graceful
degradation must handle it internally and still return an image (see the senior dashboard's offline
screen).
