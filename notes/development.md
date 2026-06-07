# Development

How to run, test, and render this project locally.

## Environment — this workspace uses conda

Env management here is **conda**, not a project `venv`. There is a ready **`inkypi` conda env** with the
dependencies already installed — activate it to get them:

```bash
conda activate inkypi
```

Use this instead of the upstream `python3 -m venv venv` flow below (that block is the generic InkyPi
setup, kept for reference). When running commands/tests in this repo, assume the `inkypi` env is the
source of installed deps.

## Setup (without hardware — recommended for dev)

```bash
git clone https://github.com/fatihak/InkyPi.git
cd InkyPi
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r install/requirements-dev.txt
bash install/update_vendors.sh
python src/inkypi.py --dev        # web UI at http://localhost:8080
```

### Devbox (macOS/Linux/WSL2)
```bash
devbox shell
python src/inkypi.py --dev
```

## Essential commands

```bash
python src/inkypi.py --dev                       # dev server (http://localhost:8080)
pytest tests/                                    # run tests
pytest tests/test_model.py::TestRefreshInfo -v   # run a specific test
pip install -r install/requirements.txt          # production deps
```

## Testing

pytest, configured in `pytest.ini` (testdir `tests/`, files `test_*.py`, classes `Test*`, functions
`test_*`). `tests/test_model.py` covers PlaylistManager (active playlist, midnight-wrapping windows),
Playlist (time-based activation, cycling), PluginInstance (interval vs scheduled refresh), and
RefreshInfo (serialize/deserialize). Run: `pytest tests/ -v`.

> Note: `tests/` import as `from src.model import ...` (repo root on path). Plugin code imports as
> `from plugins...` (i.e. `src/` on path) — match the right path when writing ad-hoc test harnesses.

## HTML rendering requirement

Plugins using `render_image()` (HTML/CSS → PNG via headless Chromium) need a Chrome-like browser:

| Platform | Required | Notes |
|---|---|---|
| macOS | Google Chrome | Must be at `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` |
| Raspbian/Debian | chromium-headless-shell | chromium or google-chrome also work if in PATH |
| Other Linux | chromium | devbox installs it automatically |
| Windows | Chromium or Chrome | devbox/WSL2 installs it; native Windows needs it in PATH |

## Operational notes / gotchas

- **Dev mode**: `--dev` runs without hardware on any OS; images saved to `mock_display_output/latest.png`.
- **Config persistence**: web UI changes are written immediately to device.json via `config.write_config()`.
- **Thread safety**: RefreshTask uses threading locks; manual updates signal the background thread via
  `threading.Condition`.
- **Plugin isolation**: each plugin instance is independent; settings stored per instance in playlist config.
- **Image caching**: RefreshTask compares image hashes to skip unchanged display updates — so a plugin
  whose output is identical won't re-render to the panel.
- **API keys**: stored in `.env` (one per plugin requirement); never committed.
