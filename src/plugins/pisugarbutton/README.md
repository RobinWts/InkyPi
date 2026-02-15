# PiSugar Button plugin

This plugin exposes an HTTP hook that **refreshes and redisplayes the currently shown playlist item**. When the PiSugar hardware button is configured to run the provided script, pressing the button triggers a display update: the same plugin instance is regenerated and shown again (e.g. to fetch fresh data or redraw the slide).

## Requirements

- **InkyPi core** must have [plugin blueprint registration](https://github.com/fatihak/InkyPi/blob/main/docs/plugin_core_interface_proposal.md) enabled (i.e. `register_plugin_blueprints(app)` and plugins implementing `get_blueprint()`). Without it, the plugin’s API route will not be registered.
- **PiSugar** hardware (e.g. PiSugar 2, 3, or S) with the [PiSugar Power Manager](https://docs.pisugar.com/docs/product-wiki/battery/pisugar-power-manager) installed so you can assign a script to the button.

## What it does

- **Endpoint:** `POST` or `GET` `/pisugarbutton-api/refresh-current`
- **Behaviour:** Reads the last refresh info (current playlist and plugin instance on display), then runs a forced refresh of that instance and updates the display. If the current display came from a manual “Update now” (not a playlist), the endpoint returns 400 and does nothing.

## PiSugar button setup

### 1. Install the plugin

Ensure the `pisugarbutton` plugin is in `src/plugins/` and listed in your device config (it will be if you use the default plugin discovery). Restart InkyPi so the blueprint is registered:

```bash
sudo systemctl restart inkypi.service
```

### 2. Make the script executable

On the Raspberry Pi:

```bash
chmod +x /home/pi/InkyPi/src/plugins/pisugarbutton/scripts/refresh-display.sh
```

Use the path that matches your InkyPi install (e.g. `/home/pi/InkyPi` or your project root).

### 3. Configure the PiSugar Power Manager

1. Open the **PiSugar Power Manager** in a browser: `http://<your-pi-ip>:8421`
2. Find the **button / gesture** settings (exact name depends on your PiSugar model and Power Manager version). You may see options like:
   - **Single click**, **Double click**, **Long press** – each can run a custom script or command.
3. Set the action you want (e.g. **Single click**) to run the InkyPi refresh script:
   - **Script path:**  
     `/home/pi/InkyPi/src/plugins/pisugarbutton/scripts/refresh-display.sh`  
     (adjust if your InkyPi install is elsewhere.)
   - Some versions let you choose “Run script” and then pick or type the path; others use a config file. See [PiSugar scripts documentation](https://docs.pisugar.com/docs/product-wiki/battery/pisugar-scripts-example) and your Power Manager UI for details.
4. Save and, if needed, restart the PiSugar service so the new action is applied.

### 4. Optional: change InkyPi URL

By default the script calls `http://127.0.0.1` (InkyPi on port 80). For **development** (InkyPi on port 8080), either:

- Set the environment variable before running the script, e.g. in the PiSugar config or in a wrapper script:
  ```bash
  export INKYPI_URL="http://127.0.0.1:8080"
  /home/pi/InkyPi/src/plugins/pisugarbutton/scripts/refresh-display.sh
  ```
- Or edit `scripts/refresh-display.sh` and set `INKYPI_URL` there (e.g. `INKYPI_URL=http://127.0.0.1:8080`).

## Testing without PiSugar

You can trigger the same behaviour from the command line or another machine:

```bash
# On the Pi (production, port 80)
curl -X POST http://127.0.0.1/pisugarbutton-api/refresh-current

# Development (port 8080)
curl -X POST http://127.0.0.1:8080/pisugarbutton-api/refresh-current
```

A successful response is JSON like:

```json
{"success": true, "message": "Display refreshed", "playlist": "Default", "plugin_id": "clock", "instance": "My Clock"}
```

If the current display is not from a playlist, you’ll get `400` and a message that refresh only works for playlist items.

## Icon

Add an `icon.png` in the `pisugarbutton` plugin folder if you want a custom icon in the InkyPi plugin list; otherwise the UI may show a default or placeholder.
