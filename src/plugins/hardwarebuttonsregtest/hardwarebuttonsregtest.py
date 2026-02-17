"""Hardware Buttons Registration Test plugin.

Tests the action registration system with the hardwarebuttons plugin.
Displays a headline and registers 1 anytime action + 4 display actions.
"""

import json
import logging
import os

from plugins.base_plugin.base_plugin import BasePlugin
from utils.app_utils import resolve_path

logger = logging.getLogger(__name__)

PLUGIN_ID = "hardwarebuttonsregtest"
DEFAULT_HEADLINE = "Instance Display"
DATA_FILE = "plugin_data.json"


def _get_data_path():
    """Path to plugin data file for override headline storage."""
    return os.path.join(resolve_path("plugins"), PLUGIN_ID, DATA_FILE)


def _get_override_headline():
    """Read override headline from plugin data (if set). Callable from any context."""
    path = _get_data_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("override_headline")
    except (json.JSONDecodeError, OSError):
        return None


def _set_override_headline(headline):
    """Write override headline to plugin data. Callable from any context."""
    path = _get_data_path()
    plugin_dir = os.path.dirname(path)
    os.makedirs(plugin_dir, exist_ok=True)
    data = {}
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    data["override_headline"] = headline
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _clear_override_headline():
    """Remove override headline from plugin data."""
    path = _get_data_path()
    if not os.path.isfile(path):
        return
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if "override_headline" in data:
            del data["override_headline"]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
    except (json.JSONDecodeError, OSError):
        pass


class HardwareButtonsRegTest(BasePlugin):
    """Test plugin for hardware button action registration."""

    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params["style_settings"] = True
        return template_params

    @classmethod
    def get_blueprint(cls):
        from . import api
        return api.hardwarebuttonsregtest_bp

    def generate_image(self, settings, device_config):
        # Use override headline if set (from button actions), else use settings
        override = _get_override_headline()
        if override is not None:
            headline = override
            _clear_override_headline()
        else:
            headline = settings.get("headline", DEFAULT_HEADLINE) or DEFAULT_HEADLINE

        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        template_params = {
            "headline": headline,
            "plugin_settings": settings,
        }
        return self.render_image(
            dimensions,
            "hardwarebuttonsregtest.html",
            "hardwarebuttonsregtest.css",
            template_params,
        )
