# Plugin: seniorDashboard_allDay

At-a-glance dashboard for an elderly person whose calendar is maintained by a family member/carer.
Runs on a landscape Waveshare 7.2" e-ink display. Shows **today + the next two days** as a calendar
list plus a small weather block. In real use it is the user's mother-in-law's daily display in a
senior residence — she relies on it for the date and appointments, so silent failure is a real
problem (this drove the offline feature below).

> First read [plugin-development.md](plugin-development.md) — especially the **"never commit plugins
> from this fork"** rule. It applies to this plugin.

## Standalone repo & copy mapping

- Real repo (where commits happen): **`/Users/robinglave/random_code/InkyPi-Plugin-seniorDashboard_allDay/`**
  (GitHub: `https://github.com/RobinWts/InkyPi-Plugin-seniorDashboard_allDay`).
- Dev/test location in this fork: `src/plugins/seniorDashboard_allDay/`.
- The standalone repo nests the plugin one level down, so copy with this mapping:
  `src/plugins/seniorDashboard_allDay/<path>` → `<repo>/seniorDashboard_allDay/<path>`
  (README, example.png, settings.png live at the repo root). Verify byte-identical, then commit there.

## Layout

```
seniorDashboard_allDay/
├── seniorDashboard_allDay.py   # main plugin class (SeniorDashboardAllDay)
├── constants.py                # FONT_SIZES, LOCALE_MAP, LABELS (localized strings), WEATHER_ICONS
├── reboot_manager.py           # offline auto-reboot scheduler (see below)
├── plugin-info.json
├── settings.html               # config form (calendars, colors, language, location, font size)
├── render/
│   ├── seniorDashboard_allDay.html / .css   # normal dashboard (uses FullCalendar.js + Intl)
│   └── offline.html / .css                  # offline / "no connection" screen
└── icon.png
```

## How the normal render works

`generate_image()`: reads `calendarURLs[]` / `calendarColors[]` from settings; fetches each ICS via
`fetch_calendar()` (`requests` + `icalendar` + `recurring_ical_events`); filters out ended events;
injects placeholders for empty today/tomorrow/day-after; fetches weather from Open-Meteo DWD API
(no key needed); then renders `render/seniorDashboard_allDay.html` via `self.render_image()`.

**Localization**: language (`de`/`en`/`es`/`fr`) selected in settings → `LABELS` dict in
`constants.py` for UI strings, and the same locale code is passed to FullCalendar and
`Intl.DateTimeFormat` so weekday/month names and date order are correct without extra work. Add a
language by extending `LOCALE_MAP` + `LABELS` with the correct international code.

## Never-silently-fail + auto-reboot (added 2026-06-07, hardened later same day)

The core guarantee: **`generate_image()` always returns an image** — the dashboard when all is well,
otherwise a localized status/error screen showing the current date — and it auto-reboots to recover,
**bounded by a consecutive-reboot cap** so a persistent problem can't loop forever.

`generate_image()` wraps the whole update in a `try/except` and routes every failure through
`_handle_failure(reason)`:

1. **`config`** — no calendar URL configured → error screen (`errorTitle` + `configMessage`), **no
   reboot** (a reboot can't add a URL).
2. **`offline`** — `_check_connectivity()` finds *all* URLs unreachable at the connection level
   (`ConnectionError`/`Timeout`; any HTTP response, even 404/500, counts as online) → offline screen +
   reboot.
3. **`error`** — anything else throws (calendar HTTP/parse error, malformed ICS, `recurring_ical_events`
   raising, render returning None / Chromium crash). The handler **re-checks connectivity**: if the
   network actually dropped mid-update it's treated as `offline`; otherwise it shows the generic error
   screen. Reboots per the cap.

**Reboot cap (loop protection).** A consecutive-reboot counter is persisted in device.json under
`seniorDashboard_allDay_reboot_count`. Each new reboot episode increments it; after
`MAX_CONSECUTIVE_REBOOTS` (3, in `reboot_manager.py`) it **stops rebooting** and just keeps showing the
screen (with `noRebootNote` instead of the reboot line). A **successful** normal render calls
`cancel_reboot()` and **resets the counter to 0**. Within one process the scheduler is idempotent so
the displayed reboot time stays stable.

**Belt-and-suspenders rendering.** `_render_status_image()` renders the screen via HTML
(`render/offline.html` — a generic title/message/reboot-line/note template). If Chromium itself fails,
it falls back to `_render_status_pil()` — a pure-PIL screen (numeric date + localized strings, no
browser) — and ultimately a blank image. So even a broken renderer can't cause a silent failure.

**Weather is already safe**: `fetch_weather_data()` catches everything and returns an empty block; the
dashboard still renders without weather. Calendar fetch happens *before* weather, so weather can't break
calendar handling.

Self-contained (no core files, no blueprint; reboot via `os.system("sudo reboot")` from a
`threading.Timer`, same mechanism as core `settings.py`, relies on passwordless sudo). Localized strings
live in `LABELS` (`offlineTitle/offlineMessage/offlineClock/offlineReassure`, `errorTitle/errorMessage`,
`rebootPrefix`, `configMessage`, `noRebootNote`); times respect the device 12h/24h format.

## Dev-testing the failure paths (without unplugging)

1. Temporarily stub `reboot_manager._do_reboot()` to log instead of `os.system("sudo reboot")` — **keep
   this in the fork only, never copy to the plugin repo** (otherwise you could reboot your dev Mac).
2. **Offline**: set the calendar URL to a dead address (`http://127.0.0.1:1/x.ics` → refused;
   `https://10.255.255.1/x.ics` → timeout), or block the real host via `/etc/hosts`.
3. **Error (network up)**: point at a reachable-but-404 URL, or feed malformed ICS → expect the *error*
   screen (not offline), still + reboot.
4. **Cap**: set `seniorDashboard_allDay_reboot_count` to 3 in device.json → next failure shows the screen
   with the persistent-problem note and **no** reboot.
5. **PIL fallback**: monkeypatch `render_image` to raise → still get a Chromium-free image.
6. Trigger a manual update; inspect `mock_display_output/latest.png` and the server log
   (`Reboot scheduled` / `reboot canceled` / `reboot cap (3) reached`).
