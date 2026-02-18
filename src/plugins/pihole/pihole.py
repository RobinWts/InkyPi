from plugins.base_plugin.base_plugin import BasePlugin
import logging
import requests

logger = logging.getLogger(__name__)

class Pihole(BasePlugin):
    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params['style_settings'] = True
        return template_params

    def generate_image(self, settings, device_config):
        pihole_url = settings.get('piholeUrl', '').strip()
        if not pihole_url:
            raise RuntimeError("Pi-hole URL is required.")

        # Get SSL verification setting from plugin settings (not device config)
        allow_insecure_ssl = settings.get('allowInsecureSSL', 'false').lower() == 'true'

        try:
            # Fetch Pi-hole statistics
            stats_data = self.get_pihole_stats(pihole_url, device_config, allow_insecure_ssl)
        except Exception as e:
            logger.error(f"Failed to fetch Pi-hole data: {str(e)}")
            raise RuntimeError("Failed to fetch Pi-hole data. Please check your URL and Pi-hole authentication settings.")

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

    def get_pihole_stats(self, pihole_url: str, device_config, allow_insecure_ssl: bool) -> dict:
        """Fetch statistics from Pi-hole API.

        Requires Pi-hole v6+ with REST API at /api/*.
        Uses session-based authentication if password is set, otherwise accesses endpoints without auth.
        """
        base_url = pihole_url.rstrip("/")
        stats = self._get_stats(base_url, device_config, allow_insecure_ssl)
        if stats is not None:
            return stats

        raise RuntimeError("Failed to fetch Pi-hole stats. Ensure you're using Pi-hole v6+ and check your URL and authentication settings.")

    def _get_stats(self, base_url: str, device_config, allow_insecure_ssl: bool) -> dict | None:
        """Fetch statistics from Pi-hole v6+ REST API."""
        url = f"{base_url}/api/stats/summary"
        try:
            resp = requests.get(url, timeout=10, verify=not allow_insecure_ssl)
            if resp.status_code == 401:
                # If the API requires auth, try to login if PIHOLE_PASSWORD is configured.
                password = (device_config.load_env_key("PIHOLE_PASSWORD") or "").strip()
                if not password:
                    logger.warning("Pi-hole API requires authentication but PIHOLE_PASSWORD is not configured")
                    return None

                sid = self._authenticate_sid(base_url, password, allow_insecure_ssl)
                resp = requests.get(url, headers={"X-FTL-SID": sid}, timeout=10, verify=not allow_insecure_ssl)

            if not 200 <= resp.status_code < 300:
                logger.warning(f"Pi-hole API returned status {resp.status_code}")
                return None

            data = resp.json()
            return self._normalize_stats(data)
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL error connecting to Pi-hole: {e}. Try enabling 'Allow insecure HTTPS' if using a self-signed certificate.")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Pi-hole API: {e}")
            return None
        except Exception as e:
            logger.error(f"Pi-hole API request failed: {e}")
            return None

    def _authenticate_sid(self, base_url: str, password: str, allow_insecure_ssl: bool) -> str:
        auth_url = f"{base_url}/api/auth"
        try:
            resp = requests.post(auth_url, json={"password": password}, timeout=10, verify=not allow_insecure_ssl)
            if not 200 <= resp.status_code < 300:
                raise RuntimeError("Authentication failed.")
            data = resp.json()
            sid = (((data or {}).get("session") or {}).get("sid") or "").strip()
            if not sid:
                raise RuntimeError("Authentication did not return a session id.")
            return sid
        except Exception as e:
            logger.error(f"Pi-hole authentication failed: {e}")
            raise RuntimeError("Pi-hole authentication failed. Check PIHOLE_PASSWORD or configure an application password.")

    def _normalize_stats(self, data: dict) -> dict:
        """Normalize Pi-hole v6+ API stats into a common shape for the template."""
        if not isinstance(data, dict):
            return {}

        # If the API already returns data in the expected format, use it directly.
        if all(k in data for k in ("dns_queries_today", "ads_blocked_today", "ads_percentage_today")):
            return data

        # Map modern API response fields to expected template format.
        # Field names may differ between Pi-hole v6 versions; keep this defensive.
        queries_total = (
            (data.get("queries") or {}).get("total")
            or (data.get("dns") or {}).get("queries")
            or data.get("dns_queries_today")
            or 0
        )
        blocked_total = (
            (data.get("queries") or {}).get("blocked")
            or (data.get("blocked") or {}).get("queries")
            or data.get("ads_blocked_today")
            or 0
        )

        try:
            pct_blocked = float(
                (data.get("queries") or {}).get("percent_blocked")
                or (data.get("blocked") or {}).get("percent")
                or data.get("ads_percentage_today")
                or 0
            )
        except Exception:
            pct_blocked = 0.0

        domains_blocked = (
            (data.get("gravity") or {}).get("domains_being_blocked")
            or (data.get("domains") or {}).get("blocked")
            or data.get("domains_being_blocked")
            or 0
        )

        # Status field differs; try a few known variants.
        status = data.get("status") or data.get("blocking") or data.get("enabled")
        if isinstance(status, bool):
            status = "enabled" if status else "disabled"

        return {
            "status": status,
            "dns_queries_today": queries_total,
            "ads_blocked_today": blocked_total,
            "ads_percentage_today": pct_blocked,
            "domains_being_blocked": domains_blocked,
            "queries_forwarded": (data.get("queries") or {}).get("forwarded") or data.get("queries_forwarded") or 0,
            "queries_cached": (data.get("queries") or {}).get("cached") or data.get("queries_cached") or 0,
        }
