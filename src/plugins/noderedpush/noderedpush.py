"""
Node Red Push plugin – display HTML pushed from Node-RED or other clients.
"""
import logging
import os
import subprocess

from plugins.base_plugin.base_plugin import BasePlugin

logger = logging.getLogger(__name__)

# Path for the push API (shown in settings). Full URL = base URL + this path.
PUSH_API_PATH = "/noderedpush-api/push"

# Copy-paste snippet for Node-RED function node: escaped for JS (\\n, \\') so paste works directly
_FONT_HTML_SNIPPET = r'''msg.payload = {
  html: '<div style="padding: 20px; text-align: center; display: flex; flex-direction: column; gap: 12px; justify-content: center; height: 100%;">\n  <h1 style="font-family: \'Jost\', sans-serif; font-weight: bold; font-size: 2.5rem; margin: 0;">Title in Jost</h1>\n  <p style="font-family: \'Jost\', sans-serif; font-size: 1.2rem; margin: 0;">Body text in Jost</p>\n  <p style="font-family: \'Dogica\', monospace; font-size: 1rem; margin: 0;">Pixel style with Dogica</p>\n  <p style="font-family: \'DS-Digital\', monospace; font-size: 2rem; margin: 0;">12:34</p>\n  <p style="font-family: \'Napoli\', serif; font-size: 1.1rem; margin: 0;">Napoli for a classic look</p>\n</div>'
};
msg.headers = { 'Content-Type': 'application/json' };
return msg;'''


class NodeRedPush(BasePlugin):
    """Plugin that renders HTML from its template (playlist) or from the push API."""

    @classmethod
    def get_blueprint(cls):
        from . import api
        return api.noderedpush_bp

    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params["push_api_path"] = PUSH_API_PATH
        template_params["font_html_snippet"] = _FONT_HTML_SNIPPET

        # Check if core has blueprint registration (same as pluginmanager); offer autopatch
        try:
            from flask import current_app

            core_needs_patch = False
            core_patch_missing = []
            try:
                from .patch_core import check_core_patched
                is_patched, missing = check_core_patched()
                core_needs_patch = not is_patched
                core_patch_missing = missing
            except Exception as e:
                logger.warning(f"Could not check patch status: {e}")

            template_params["core_needs_patch"] = core_needs_patch
            template_params["core_patch_missing"] = core_patch_missing

            if core_needs_patch:
                patch_script = os.path.join(os.path.dirname(__file__), "patch-core.sh")
                if os.path.isfile(patch_script):
                    try:
                        subprocess.Popen(
                            ["bash", patch_script],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        template_params["auto_patch_started"] = True
                    except Exception as e:
                        logger.warning(f"Could not start auto core patch: {e}")
                        template_params["auto_patch_started"] = False
                else:
                    logger.warning("patch-core.sh not found for noderedpush")
                    template_params["auto_patch_started"] = False
        except (RuntimeError, ImportError):
            template_params["core_needs_patch"] = False
            template_params["core_patch_missing"] = []
            template_params["auto_patch_started"] = False

        return template_params

    def generate_image(self, settings, device_config):
        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        template_params = {
            "plugin_settings": settings,
        }
        return self.render_image(
            dimensions,
            "noderedpush.html",
            "noderedpush.css",
            template_params,
        )
