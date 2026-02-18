from plugins.base_plugin.base_plugin import BasePlugin
import logging
import requests

logger = logging.getLogger(__name__)

class Pihole(BasePlugin):
    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params['api_key'] = {
            "required": True,
            "service": "Pi-hole",
            "expected_key": "PIHOLE_API_TOKEN"
        }
        template_params['style_settings'] = True
        return template_params

    def generate_image(self, settings, device_config):
        pihole_url = settings.get('piholeUrl', '').strip()
        if not pihole_url:
            raise RuntimeError("Pi-hole URL is required.")

        api_token = device_config.load_env_key("PIHOLE_API_TOKEN")
        if not api_token:
            raise RuntimeError("Pi-hole API token not configured. Please set PIHOLE_API_TOKEN in .env or via the API Keys page in the web UI.")

        try:
            # Fetch Pi-hole statistics
            stats_data = self.get_pihole_stats(pihole_url, api_token)
        except Exception as e:
            logger.error(f"Failed to fetch Pi-hole data: {str(e)}")
            raise RuntimeError("Failed to fetch Pi-hole data. Please check your URL and API token.")

        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        template_params = {
            "stats": stats_data,
            "plugin_settings": settings
        }

        image = self.render_image(dimensions, "pihole.html", "pihole.css", template_params)

        if not image:
            raise RuntimeError("Failed to render Pi-hole image, please check logs.")

        return image

    def get_pihole_stats(self, pihole_url, api_token):
        """Fetch statistics from Pi-hole API"""
        # Remove trailing slash if present
        pihole_url = pihole_url.rstrip('/')
        
        # Pi-hole API endpoint for summary
        api_url = f"{pihole_url}/admin/api.php?summary&auth={api_token}"
        
        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Pi-hole API request failed: {str(e)}")
            raise RuntimeError(f"Failed to connect to Pi-hole: {str(e)}")
