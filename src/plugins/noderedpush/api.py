"""
API routes for Node Red Push plugin – POST HTML payload to update the display.
"""
import logging

from flask import Blueprint, request, jsonify, current_app

from utils.image_utils import take_screenshot_html

logger = logging.getLogger(__name__)

# Max HTML payload size (bytes) to avoid abuse and timeouts
MAX_HTML_PAYLOAD_BYTES = 500 * 1024

noderedpush_bp = Blueprint("noderedpush_api", __name__)


def _wrap_html_for_screenshot(html_fragment: str, width: int, height: int) -> str:
    """Wrap a fragment in a full HTML document with viewport so screenshot matches dimensions."""
    # Basic sanitization: escape </script> and similar to avoid breaking the wrapper
    escaped = html_fragment.replace("</script>", r"<\/script>")
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width={width}, height={height}, initial-scale=1">
<style>
  html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; box-sizing: border-box; }}
  body {{ overflow: hidden; }}
</style>
</head>
<body>
{escaped}
</body>
</html>"""


def _validate_html_payload(payload: str) -> tuple[bool, str]:
    """Check payload is a non-empty string that looks like HTML. Returns (ok, error_message)."""
    if not isinstance(payload, str):
        return False, "Payload must be a string"
    if not payload.strip():
        return False, "HTML payload cannot be empty"
    if len(payload.encode("utf-8")) > MAX_HTML_PAYLOAD_BYTES:
        return False, f"HTML payload must be at most {MAX_HTML_PAYLOAD_BYTES // 1024} KB"
    if "<" not in payload or ">" not in payload:
        return False, "Payload must contain HTML (e.g. tags like <div>, <p>)"
    return True, ""


@noderedpush_bp.route("/noderedpush-api/push", methods=["POST"])
def push():
    """
    Accept a JSON body with an "html" key, render it to an image, and push to the display.
    Content-Type: application/json
    Body: { "html": "<div>Your content</div>" }
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"success": False, "error": "Request body must be JSON"}), 400

    html_payload = data.get("html")
    ok, err = _validate_html_payload(html_payload)
    if not ok:
        return jsonify({"success": False, "error": err}), 400

    device_config = current_app.config["DEVICE_CONFIG"]
    display_manager = current_app.config["DISPLAY_MANAGER"]

    dimensions = device_config.get_resolution()
    if device_config.get_config("orientation") == "vertical":
        dimensions = dimensions[::-1]

    full_html = _wrap_html_for_screenshot(html_payload, dimensions[0], dimensions[1])

    try:
        image = take_screenshot_html(full_html, dimensions)
    except Exception as e:
        logger.exception("Failed to render HTML for Node Red Push")
        return jsonify({"success": False, "error": f"Rendering failed: {str(e)}"}), 500

    if image is None:
        return jsonify({"success": False, "error": "Failed to render HTML to image"}), 500

    plugin_config = device_config.get_plugin("noderedpush")
    image_settings = (plugin_config.get("image_settings", []) if plugin_config else [])

    try:
        display_manager.display_image(image, image_settings=image_settings)
    except Exception as e:
        logger.exception("Failed to push image to display")
        return jsonify({"success": False, "error": f"Display update failed: {str(e)}"}), 500

    return jsonify({"success": True, "message": "Display updated"})
