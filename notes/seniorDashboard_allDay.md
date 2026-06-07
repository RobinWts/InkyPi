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

## Offline handling & auto-reboot (added 2026-06-07)

Solves silent failure when Pi/router power-save kills the WLAN. Flow in `generate_image()`, before
the normal work:

1. `_check_connectivity(calendar_urls)` — lightweight `requests.get(timeout=5, stream=True)` per URL.
   Offline **only** when *all* URLs fail with a connection-level error (`ConnectionError`/`Timeout`).
   Any HTTP response (even 404/500) ⇒ online (a reboot wouldn't fix a broken feed).
2. **Online** → `reboot_manager.cancel_reboot()` (cancels any pending reboot), then normal render.
3. **Offline** → `reboot_manager.schedule_reboot(...)` for `now + 10 min`, then
   `_render_offline_image()` shows a localized screen with today's date, a "no internet" notice, and
   the auto-restart time. At that time `reboot_manager._do_reboot()` runs `os.system("sudo reboot")`.

Design choices (confirmed with user): network-failure-only trigger; **self-contained** (no core files
changed, no blueprint — same `sudo reboot` mechanism as core `settings.py`, relies on InkyPi's
passwordless sudo); cancel-on-reconnect; 10-min delay to avoid boot-loops; displayed time stays stable
across refreshes in one outage; one reboot per process (lock-guarded, idempotent scheduler in
`reboot_manager.py`). Offline strings are `offlineTitle` / `offlineMessage` / `offlineClock` /
`offlineReassure` in `LABELS`, and time respects the device 12h/24h format.

## Dev-testing the offline path (without unplugging)

1. Temporarily stub `reboot_manager._do_reboot()` to log instead of `os.system("sudo reboot")` — **keep
   this in the fork only, never copy to the plugin repo** (otherwise you could reboot your dev Mac).
2. Make the calendar unreachable: set the plugin's calendar URL to a dead address
   (`http://127.0.0.1:1/x.ics` → refused; `https://10.255.255.1/x.ics` → timeout), or block the real
   host via `/etc/hosts`.
3. Trigger a manual update in the web UI; inspect `mock_display_output/latest.png` and the server log
   (`reboot scheduled` / `reboot canceled`).
4. To prove no false reboot on a bad feed, point at a reachable-but-404 URL and confirm it does **not**
   show the offline screen.
