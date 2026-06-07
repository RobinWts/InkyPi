# Plugin: hardwarebuttons

Lets you bind **physical GPIO buttons** on the Raspberry Pi to actions (refresh, playlist nav,
shutdown/reboot, restart service, run a bash script, call a URL) with short / double / long-press
gestures. It's also the reference example for **plugin blueprints** and an **inter-plugin action
registry**.

> Read [plugin-blueprints.md](plugin-blueprints.md) alongside this — the general blueprint mechanics
> were extracted from here. And mind the **"never commit plugins from this fork"** rule in
> [plugin-development.md](plugin-development.md).

## Standalone repo

- Real repo: `https://github.com/RobinWts/InkyPi-Plugin-hardwarebuttons` (from `plugin-info.json`).
- **No local clone present** under `random_code/` (unlike the senior plugin). To commit changes,
  clone that repo first, then copy the changed files from `src/plugins/hardwarebuttons/` into it —
  never commit from this fork.
- Related demo repo (action-registration example for other plugin devs):
  `https://github.com/RobinWts/InkyPi-Plugin-HWButtonRegTest`.

## Key idea: it's a UI + service plugin, not a display plugin

`generate_image()` just returns a **blank placeholder** — nothing is drawn to the panel. The real work
is: (1) a settings UI to configure buttons, (2) a Flask blueprint API, and (3) a background GPIO worker
thread. So almost everything interesting is *outside* `generate_image()`.

## File map

| File | Role |
|---|---|
| `hardwarebuttons.py` | Plugin class. `get_blueprint()`; `generate_settings_template()` (runs patch check, auto-starts core patch if needed, loads timings/buttons/available actions for the form); `generate_image()` placeholder. |
| `api.py` | Blueprint `hardwarebuttons_api`. Routes `/hardwarebuttons-api/{save,available-actions,execute,restart-service}`. `record_once` + `before_request` capture `DEVICE_CONFIG`/`REFRESH_TASK` refs and start the button manager. Heavy input validation in `save`. |
| `button_manager.py` | GPIO worker thread (`gpiozero`). Builds buttons from config, runs the short/double/long-press state machine, reloads on config change. `gpiozero` is optional → on dev/non-Pi the plugin loads but buttons are disabled. |
| `actions.py` | Executes a triggered action. Built-in Core/System actions + dispatch to plugin-registered actions. One action at a time (`_action_lock`). Security: `external_script` restricted to the home dir; `call_url` must be http(s). |
| `discovery.py` | Builds the action dropdown list: built-ins + plugin "anytime" actions + generic "Display Action N" entries. |
| `action_registry.py` | Thread-safe registry letting **other plugins** contribute button actions (anytime + display). |
| `patch_core.py` / `patch-core.sh` | The blueprint-registration core patch (see [plugin-blueprints.md](plugin-blueprints.md)). |
| `settings.html` | Button configuration UI. |
| `demo_*.sh` + `DEMO_SCRIPTS.md` | Example external scripts (LED off/restore, system status, button logger). |
| `PLUGIN_ACTION_REGISTRATION.md` | Guide for other plugin authors to register actions. |
| `CORE_CHANGES.md` | Documents the required core patch. |
| `requirements.txt` | `gpiozero>=2.0` (optional — only needed on the Pi). |

## How it runs (lifecycle)

1. At app startup, `register_plugin_blueprints(app)` registers `hardwarebuttons_bp`.
2. `@bp.record_once` captures core refs (`device_config`, `refresh_task`, `app`, `port`) and calls
   `button_manager.start_if_needed(refs)` → background thread starts **without needing the settings
   page to be opened**.
3. The worker reads config from `device_config.get_config("hardwarebuttons")` and wires up gpiozero
   `Button`s with the configured `short/double/long` actions and timing thresholds.
4. A press → state machine in `button_manager._setup_button` → `actions.execute_action(refs, ...)`,
   which runs in the **GPIO thread (no Flask request context)**.
5. Saving in the UI → `POST /hardwarebuttons-api/save` validates + `update_value("hardwarebuttons", …)`
   + `button_manager.request_reload()` to re-wire buttons live.

## Config shape (device.json, top-level `hardwarebuttons` key)

```json
{
  "timings": { "short_press_ms": 500, "double_click_interval_ms": 500, "long_press_ms": 1000 },
  "buttons": [
    { "id": "btn_0", "gpio_pin": 17,
      "short_action": "core_trigger_refresh", "double_action": "system_reboot", "long_action": "external_script",
      "script_path_long": "/home/pi/foo.sh", "url_short": null }
  ]
}
```
Built-in action ids: `core_trigger_refresh`, `core_force_refresh`, `core_next_playlist`,
`core_prev_playlist`, `system_shutdown`, `system_reboot`, `system_restart_inkypi`, `external_script`,
`call_url`. Plugin-registered actions add `<plugin>_<name>` (anytime) and `display_action_N` (display).

## Action registry (inter-plugin extension)

Other plugins can expose button-bindable actions from their own blueprint `record_once`:
`action_registry.register_actions(plugin_id, anytime_actions={...}, display_actions=[...])`.
- **Anytime** actions run regardless of what's on screen (e.g. "Reload Weather"); shown under "Other
  Plugins".
- **Display** actions (max 6) only fire when that plugin is the one currently displayed (resolved from
  `refresh_info`); shown as generic "Display Action N" under "Current Plugin".
This registry pattern is the reusable bit worth copying for other "any plugin can contribute X" features.

## Dev notes

- On macOS/dev there's no `gpiozero` → buttons are disabled, but the plugin, settings page, and API all
  still load/work. You can exercise actions via `POST /hardwarebuttons-api/execute` with `{"action_id": ...}`.
- Several actions shell out with `sudo` (`reboot`, `shutdown`, `systemctl restart`) — they only do
  something real on the Pi with passwordless sudo configured.
