"""Plugin Manager plugin - manages installation and uninstallation of third-party plugins."""

from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class PluginManager(BasePlugin):
    """Plugin for managing third-party plugins installation/uninstallation."""
    
    @classmethod
    def get_blueprint(cls):
        """Return the Flask blueprint for this plugin's API routes."""
        from . import api
        return api.plugin_manage_bp
    
    def generate_settings_template(self):
        """Add third-party plugins list to template parameters."""
        template_params = super().generate_settings_template()
        # Access device_config via Flask's current_app
        try:
            from flask import current_app
            device_config = current_app.config.get('DEVICE_CONFIG')
            if device_config:
                third_party = [p for p in device_config.get_plugins() if p.get("repository")]
                template_params['third_party_plugins'] = third_party
            else:
                template_params['third_party_plugins'] = []
            
            # Check if core files need patching
            try:
                from .patch_core import check_core_patched
                is_patched, missing = check_core_patched()
                template_params['core_needs_patch'] = not is_patched
                template_params['core_patch_missing'] = missing
            except Exception as e:
                logger.warning(f"Could not check patch status: {e}")
                template_params['core_needs_patch'] = False
                template_params['core_patch_missing'] = []
        except (RuntimeError, ImportError):
            # Not in Flask context or Flask not available
            template_params['third_party_plugins'] = []
            template_params['core_needs_patch'] = False
            template_params['core_patch_missing'] = []
        return template_params
    
    def generate_image(self, settings, device_config):
        """Return a placeholder image - this plugin is UI-only."""
        # Create a simple placeholder image
        width, height = device_config.get_resolution()
        img = Image.new('RGB', (width, height), color='white')
        return img
