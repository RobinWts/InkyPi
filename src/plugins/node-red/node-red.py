"""
Node-RED Plugin for InkyPi
This plugin fetches JSON data from a Node-RED HTTP endpoint and displays it on the e-ink display.
"""

from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image
import logging
import requests
import json

logger = logging.getLogger(__name__)


class NodeRed(BasePlugin):
    """Plugin for displaying Node-RED data on InkyPi."""
    
    def generate_image(self, settings, device_config):
        """
        Generate an image from Node-RED data.
        
        Args:
            settings: A dictionary of plugin configuration values
            device_config: An instance of the Config class
            
        Returns:
            PIL.Image: The generated image
        """
        # Get settings with defaults
        node_red_url = settings.get('nodeRedUrl', 'http://localhost:1880').strip().rstrip('/')
        endpoint_path = settings.get('endpointPath', '/inkypi/data').strip()
        timeout = int(settings.get('timeout', 10))
        
        # Validate settings
        if not node_red_url:
            logger.error("Node-RED URL is required")
            raise RuntimeError("Node-RED URL is required.")
        
        if not endpoint_path:
            logger.error("Endpoint path is required")
            raise RuntimeError("Endpoint path is required.")
        
        # Construct full URL
        full_url = f"{node_red_url}{endpoint_path}"
        logger.info(f"Fetching data from Node-RED: {full_url}")
        
        try:
            # Make HTTP GET request
            logger.debug(f"Making HTTP GET request to {full_url} with timeout {timeout}s")
            response = requests.get(full_url, timeout=timeout)
            
            # Log response details
            logger.info(f"HTTP Status Code: {response.status_code}")
            logger.debug(f"Response Headers: {dict(response.headers)}")
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse JSON response
            try:
                data = response.json()
                logger.info(f"Successfully fetched JSON data from Node-RED")
                logger.debug(f"JSON Data: {json.dumps(data, indent=2)}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response: {e}")
                logger.debug(f"Response content: {response.text[:500]}")
                raise RuntimeError("Node-RED returned invalid JSON data.")
            
            # Get display dimensions
            dimensions = device_config.get_resolution()
            if device_config.get_config("orientation") == "vertical":
                dimensions = dimensions[::-1]
            
            # Format JSON for display
            json_string = json.dumps(data, indent=2, ensure_ascii=False)
            
            # Render the data
            template_params = {
                "json_string": json_string,
                "endpoint_url": full_url,
                "plugin_settings": settings
            }
            
            image = self.render_image(
                dimensions,
                "node_red.html",
                "node_red.css",
                template_params
            )
            
            logger.info("Successfully generated image from Node-RED data")
            return image
            
        except requests.exceptions.Timeout:
            logger.error(f"Request to {full_url} timed out after {timeout}s")
            raise RuntimeError(f"Request to Node-RED timed out after {timeout} seconds.")
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Node-RED at {full_url}: {e}")
            raise RuntimeError(f"Failed to connect to Node-RED. Check the URL and ensure Node-RED is running.")
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error from Node-RED: {e}")
            status_code = response.status_code if 'response' in locals() else 'unknown'
            raise RuntimeError(f"Node-RED returned HTTP error {status_code}.")
        
        except RuntimeError:
            # Re-raise RuntimeErrors as-is (they already have user-friendly messages)
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error fetching Node-RED data: {e}", exc_info=True)
            raise RuntimeError(f"Failed to fetch data from Node-RED: {str(e)}")
