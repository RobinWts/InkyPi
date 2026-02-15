"""Hardware Buttons plugin - configures hardware button bindings (UI/settings only)."""

from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image
import logging
import os
import subprocess

logger = logging.getLogger(__name__)


class HardwareButtons(BasePlugin):
    """Plugin for configuring hardware button actions (UI/settings only)."""

    def generate_settings_template(self):
        """Add patch-check and autopatch template parameters."""
        template_params = super().generate_settings_template()
        try:
            from flask import current_app

            # Check if core files need patching first
            core_needs_patch = False
            core_patch_missing = []
            try:
                from .patch_core import check_core_patched
                is_patched, missing = check_core_patched()
                core_needs_patch = not is_patched
                core_patch_missing = missing
            except Exception as e:
                logger.warning(f"Could not check patch status: {e}")

            template_params['core_needs_patch'] = core_needs_patch
            template_params['core_patch_missing'] = core_patch_missing

            if core_needs_patch:
                patch_script = os.path.join(os.path.dirname(__file__), "patch-core.sh")
                if os.path.isfile(patch_script):
                    try:
                        subprocess.Popen(
                            ["bash", patch_script],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        template_params['auto_patch_started'] = True
                    except Exception as e:
                        logger.warning(f"Could not start auto core patch: {e}")
                        template_params['auto_patch_started'] = False
                else:
                    logger.warning("patch-core.sh not found for hardwarebuttons")
                    template_params['auto_patch_started'] = False
            else:
                template_params['auto_patch_started'] = False
        except (RuntimeError, ImportError):
            template_params['core_needs_patch'] = False
            template_params['core_patch_missing'] = []
            template_params['auto_patch_started'] = False
        return template_params

    def generate_image(self, settings, device_config):
        """Return a placeholder image - this plugin is UI-only."""
        width, height = device_config.get_resolution()
        img = Image.new('RGB', (width, height), color='white')
        return img
