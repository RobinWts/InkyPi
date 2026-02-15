"""PiSugar Button plugin – exposes an API hook to refresh the current display, for use with PiSugar button mapping."""

from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class PiSugarButton(BasePlugin):
    """Plugin that exposes a refresh-current-display endpoint for the PiSugar hardware button.

    When the PiSugar button is mapped to run the provided script, pressing it triggers
    a refresh of the currently displayed playlist instance (regenerates and redisplayes).
    """

    @classmethod
    def get_blueprint(cls):
        from . import api
        return api.pisugarbutton_bp

    def generate_image(self, settings, device_config):
        # This plugin is API-only; return a placeholder if ever used in a playlist
        w, h = device_config.get_resolution()
        return Image.new("RGB", (w, h), color=(248, 248, 248))
