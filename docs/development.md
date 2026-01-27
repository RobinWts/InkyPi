# InkyPi Development Quick Start

## Development Without Hardware

The `--dev` flag enables complete development without requiring:

- Raspberry Pi hardware
- Physical e-ink displays (Inky pHAT/wHAT or Waveshare)
- Root privileges or GPIO access
- Linux-specific features (systemd)

Works on **macOS** - no hardware needed!

## Setup

```bash
# 1. Clone and setup
git clone https://github.com/fatihak/InkyPi.git
cd InkyPi

# 2. Create conda environment
conda create -n inkypi python=3.11
conda activate inkypi

# 3. Install Python dependencies and run
pip install -r install/requirements-dev.txt
bash install/update_vendors.sh
python src/inkypi.py --dev
```

**That's it!** Open http://localhost:8080 and start developing.

## What You Can Do

- **Develop plugins** - Create new plugins without hardware (no Raspberry Pi, nor physical displays)
- **Test UI changes** - Instant feedback on web interface modifications  
- **Debug issues** - Full error messages in terminal
- **Verify rendering** - Check output in `mock_display_output/latest.png`
- **macOS development** - Works on macOS

## Essential Commands

```bash
conda activate inkypi                # Activate conda environment
python src/inkypi.py --dev           # Start development server
conda deactivate                     # Exit conda environment
```

## Development Tips

1. **Check rendered output**: Images are saved to `mock_display_output/`
2. **Plugin development**: Copy an existing plugin as template (e.g., `clock/`)
3. **Configuration**: Edit `src/config/device_dev.json` for display settings
4. **Hot reload**: Restart server to see code changes

## Testing Your Changes

1. Configure a plugin through the web UI
2. Click "Display" button
3. Check `mock_display_output/latest.png` for result
4. Iterate quickly without deployment

## Other Requirements

### Chromium or Google Chrome browser

InkyPi uses `--headless` mode to render HTML templates to PNG images using a Chrome-like browser.  

On macOS, Google Chrome is recommended and must be installed at its default location:

`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`

InkyPi will search for a Chrome-like browser in your system's PATH. 
