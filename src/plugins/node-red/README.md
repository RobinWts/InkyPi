# Node-RED Plugin

This plugin integrates with Node-RED to display data on InkyPi devices.

## Status

🚧 **Work in Progress** - Basic structure created, functionality not yet implemented.

## Files

- `node_red.py` - Main plugin class (inherits from BasePlugin)
- `plugin-info.json` - Plugin manifest/registration file
- `settings.html` - Settings template for the web UI
- `render/` - Directory for HTML/CSS templates (if using render_image)
- `icon.png` - **TODO: Add plugin icon** (should match style of other plugin icons)

## Next Steps

1. Add `icon.png` to the plugin directory
2. Implement `generate_image` method in `node_red.py`
3. Define settings in `settings.html`
4. Add any required HTML/CSS templates in `render/` if needed
