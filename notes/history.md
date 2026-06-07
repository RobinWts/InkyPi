# History

Running log of notable work and decisions. **Read this to catch up on what changed and why.**

## How to use

- **Add new entries on top** (reverse-chronological — newest first).
- Group entries under a **daily tag** `## YYYY-MM-DD`. If today's tag already exists, add your
  bullet(s) under it; otherwise create a new tag above the previous day.
- Keep each bullet short: *what* changed and, when it matters, *why*. Link to the relevant doc or
  path for detail (`src/plugins/seniorDashboard_allDay/reboot_manager.py`, …).
- Log **decisions and direction changes**, not every keystroke. This is a memory aid for the next
  agent, not a git replacement.

## 2026-06-07

- **seniorDashboard_allDay: never-silently-fail hardening.** The first offline feature only caught a
  *fully* dead network; reachable-but-erroring calendars, flapping WLAN, malformed ICS, and render
  glitches still raised uncaught → silent failure. Now `generate_image()` wraps the whole update in
  try/except and routes every failure through `_handle_failure(reason)` → always returns a localized
  status/error screen (with current date). Reasons: `config` (no URL → no reboot), `offline` (network
  down → reboot), `error` (anything else → re-checks connectivity, reboots only if actually offline,
  else shows error screen). Added a **consecutive-reboot cap** (`MAX_CONSECUTIVE_REBOOTS=3`, persisted
  in device.json key `seniorDashboard_allDay_reboot_count`, reset on success) to stop endless reboot
  loops on a persistent problem (user-chosen policy). Added a **pure-PIL last-resort** screen so even a
  broken Chromium can't fail silently. Confirmed weather fetch was already safe (caught internally) and
  runs after the calendar fetch. New `LABELS`: `errorTitle/errorMessage/rebootPrefix/configMessage/noRebootNote`;
  `render/offline.html` generalized to title/message/reboot-line/note. Verified all 6 paths locally
  (reboot stubbed) incl. the German error/capped/PIL screens; `pytest` still 25 green. Files copied to
  the standalone plugin repo for commit.
- **Env + patch clarifications.** Noted that this workspace uses **conda** with a ready **`inkypi`**
  env for installed deps (in `development.md` + CLAUDE.md quick start). Also noted in
  [plugin-blueprints.md](plugin-blueprints.md) that **`pluginmanager`** is normally the first plugin to
  apply the core blueprint patch (same patch module as `hardwarebuttons`); the fork's `pluginmanager`
  may be outdated, which is harmless since the patch is idempotent.
- **Context housekeeping for hardwarebuttons.** Installed `src/plugins/hardwarebuttons` (GPIO
  button-binding plugin). Documented it in [hardwarebuttons.md](hardwarebuttons.md) and extracted the
  reusable blueprint-registration mechanics into [plugin-blueprints.md](plugin-blueprints.md)
  (`get_blueprint()`, the core patch, `record_once`/`before_request`, capturing `DEVICE_CONFIG`/`REFRESH_TASK`
  refs, dev-vs-prod port, the cross-plugin action registry). Linked both from the context index and
  cross-referenced from architecture/plugin-development notes. Confirmed this fork's core is **already
  patched** with `register_plugin_blueprints` (in `plugin_registry.py` + `inkypi.py`). No local clone of
  the plugin's standalone repo exists yet.
- **Context restructure.** Slimmed `CLAUDE.md` (326 → ~40 lines) to: fork purpose, the "never commit
  plugins from the fork" rule, and pointers. Moved the detail into `notes/` (`context-index.md`,
  `architecture.md`, `development.md`, `plugin-development.md`, per-plugin files), with
  `context-index.md` as the entry point.
- **seniorDashboard_allDay: offline handling + auto-reboot.** Added graceful handling for the
  recurring problem where the Pi/router power-save kills the WLAN and the display silently shows
  stale info. On each refresh the plugin now checks calendar reachability first; if offline it shows
  a localized "no connection — auto-restart at HH:MM" screen and reboots the device 10 min later to
  recover. Files: new `reboot_manager.py`, new `render/offline.{html,css}`, edits to
  `seniorDashboard_allDay.py` (connectivity gate + `_render_offline_image`) and `constants.py`
  (new localized `offline*` strings for de/en/es/fr). All under `src/plugins/seniorDashboard_allDay/`.
- **Decisions (confirmed with user):**
  - *Trigger only on true network failure* (timeout / connection refused / DNS) — **not** on HTTP
    errors (404/500) from a reachable server, since a reboot won't fix a broken feed.
  - *Self-contained in the plugin* — reboot via `os.system("sudo reboot")` from the plugin's own
    `threading.Timer` (same mechanism as core `settings.py`); **no** core files changed, **no**
    blueprint. Keeps the plugin independently installable.
  - *Cancel the pending reboot* if connectivity returns before the timer fires.
  - 10-min delay to avoid fast boot-loops; displayed reboot time stays stable across refreshes
    during one outage; one reboot per process (lock-guarded, idempotent scheduler).
- **Verified locally** (no real reboot fired — stubbed `os.system`): German + English offline screens
  render correctly via headless Chrome; connectivity classification (200→online,
  ConnErr/Timeout→offline, multi-URL one-ok→online); scheduler idempotency + cancel; existing
  `pytest` suite still green (25 passed).
- **Plugin lives in its own repo** at `/Users/robinglave/random_code/InkyPi-Plugin-seniorDashboard_allDay/`.
  Plugin folders are flattened in this dev clone, so commits happen from that standalone repo, **not**
  here. The 5 changed/new files were copied there (byte-identical) and its `README.md` was updated to
  document the new feature.
- **Dev-testing note:** to exercise the offline path without unplugging, stub `_do_reboot()` to log
  instead of reboot, then point the calendar URL at a dead address
  (`http://127.0.0.1:1/x.ics` → refused, `https://10.255.255.1/x.ics` → timeout) or block the real
  host via `/etc/hosts`. Output lands in `mock_display_output/latest.png`.
