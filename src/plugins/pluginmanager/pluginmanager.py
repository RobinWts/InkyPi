"""Plugin Manager plugin - manages installation and uninstallation of third-party plugins."""

from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image
import logging
import os

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
            
            # Check if core files need patching FIRST
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
            
            # Only load plugins if core is patched (skip unnecessary work)
            if not core_needs_patch:
                device_config = current_app.config.get('DEVICE_CONFIG')
                if device_config:
                    third_party = [p for p in device_config.get_plugins() if p.get("repository")]
                    template_params['third_party_plugins'] = third_party
                else:
                    template_params['third_party_plugins'] = []
            else:
                # Skip loading plugins when unpatched
                template_params['third_party_plugins'] = []
                # Add project root path for patch command display
                try:
                    from config import Config
                    project_root = os.path.dirname(Config.BASE_DIR)
                    template_params['project_root'] = project_root
                except:
                    template_params['project_root'] = None
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
