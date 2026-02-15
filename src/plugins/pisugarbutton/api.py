"""API routes for PiSugar Button plugin – refresh current display hook for PiSugar button."""

import logging
from flask import Blueprint, jsonify, current_app
from refresh_task import PlaylistRefresh

logger = logging.getLogger(__name__)

pisugarbutton_bp = Blueprint("pisugarbutton_api", __name__)


def _device_config():
    return current_app.config["DEVICE_CONFIG"]


def _refresh_task():
    return current_app.config["REFRESH_TASK"]


@pisugarbutton_bp.route("/pisugarbutton-api/refresh-current", methods=["POST", "GET"])
def refresh_current():
    """Refresh and redisplay the currently shown playlist instance.

    Uses the last refresh info to determine which playlist and plugin instance is on
    display, then forces a refresh of that instance (regenerates the image and updates
    the display). Intended to be called by the PiSugar button script.

    Returns 400 if the current display is not from a playlist (e.g. was a manual update).
    """
    device_config = _device_config()
    refresh_task = _refresh_task()
    refresh_info = device_config.get_refresh_info()

    if not refresh_info or getattr(refresh_info, "refresh_type", None) != "Playlist":
        return jsonify({
            "success": False,
            "error": "Current display is not from a playlist. Refresh only works when the shown content is a playlist item.",
        }), 400

    playlist_name = getattr(refresh_info, "playlist", None)
    plugin_id = getattr(refresh_info, "plugin_id", None)
    instance_name = getattr(refresh_info, "plugin_instance", None)

    if not playlist_name or not plugin_id or not instance_name:
        return jsonify({
            "success": False,
            "error": "Could not determine current playlist instance.",
        }), 400

    playlist_manager = device_config.get_playlist_manager()
    playlist = playlist_manager.get_playlist(playlist_name)
    if not playlist:
        return jsonify({"success": False, "error": f"Playlist '{playlist_name}' not found"}), 404

    plugin_instance = playlist.find_plugin(plugin_id, instance_name)
    if not plugin_instance:
        return jsonify({
            "success": False,
            "error": f"Plugin instance '{instance_name}' not found in playlist.",
        }), 404

    try:
        refresh_task.manual_update(PlaylistRefresh(playlist, plugin_instance, force=True))
    except Exception as e:
        logger.exception("PiSugar refresh-current failed")
        return jsonify({"success": False, "error": str(e)}), 500

    return jsonify({
        "success": True,
        "message": "Display refreshed",
        "playlist": playlist_name,
        "plugin_id": plugin_id,
        "instance": instance_name,
    })
