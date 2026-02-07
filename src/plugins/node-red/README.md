# Node-RED Plugin

This plugin integrates with Node-RED to display data on InkyPi devices.

## Features

✅ **Two Display Modes:**
- **JSON Parsing Mode** - Configure layouts via web UI, extract data from JSON responses
- **HTML Mode** - Node-RED sends complete HTML, rendered directly

✅ **JSON Parsing Mode Features:**
- Configurable divisions (side-by-side in landscape, stacked in portrait)
- Output lines: Title, Divider, or Data Output
- Format strings with placeholders for flexible data display
- Font, size, color, and alignment options for each output
- Support for nested JSON keys (dot notation)
- Shows "??" when data not found

✅ **HTML Mode Features:**
- Direct HTML rendering from Node-RED
- Complete control over layout and styling
- No configuration needed - just send HTML

## Files

- `node_red.py` - Main plugin class (inherits from BasePlugin)
- `plugin-info.json` - Plugin manifest/registration file
- `settings.html` - Settings template for the web UI
- `render/` - Directory for HTML/CSS templates (JSON mode)
- `preview.html` - Generated preview file for debugging
- `DATA_INTEGRATION.md` - Documentation on integrating with Node-RED
- `LAYOUT_CONFIGURATION_PLAN.md` - Layout configuration details
- `icon.png` - Plugin icon

## Usage

See [DATA_INTEGRATION.md](./DATA_INTEGRATION.md) for detailed integration instructions.
