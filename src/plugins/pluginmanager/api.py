"""API routes for pluginmanager plugin - handles install/uninstall/update of third-party plugins."""

import os
import subprocess
from urllib.parse import urlparse

from flask import Blueprint, request, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

plugin_manage_bp = Blueprint("pluginmanager_api", __name__)

# Import patch functionality
try:
    from .patch_core import check_core_patched, patch_core_files
except ImportError:
    # Fallback if relative import fails
    import sys
    plugin_dir = os.path.dirname(__file__)
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)
    from patch_core import check_core_patched, patch_core_files


def _project_dir():
    """Project root (parent of src/)."""
    # Get BASE_DIR from config, go up one level
    try:
        from config import Config
        return os.path.dirname(Config.BASE_DIR)
    except ImportError:
        # Fallback: assume we're in src/plugins/pluginmanager, go up 3 levels
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def _cli_script():
    """Path to the inkypi-plugin CLI script in the pluginmanager plugin."""
    plugin_dir = os.path.dirname(__file__)
    return os.path.join(plugin_dir, "inkypi-plugin")


def _third_party_plugins():
    """Plugins that have a repository (third-party)."""
    device_config = current_app.config["DEVICE_CONFIG"]
    return [p for p in device_config.get_plugins() if p.get("repository")]


def _validate_install_url(url):
    """Validate URL for install: HTTPS and GitHub.com only. Returns (ok, error_message)."""
    if not url or not isinstance(url, str):
        return False, "URL is required"
    url = url.strip()
    if not url:
        return False, "URL is required"
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL"
    if parsed.scheme != "https":
        return False, "Only HTTPS URLs are allowed"
    if not parsed.netloc:
        return False, "Invalid URL host"
    host = parsed.netloc.lower().split(":")[0]  # strip port if present
    if host not in ("github.com", "www.github.com"):
        return False, "Only GitHub.com repository URLs are accepted"
    return True, None


@plugin_manage_bp.route("/pluginmanager-api/install", methods=["POST"])
def install_plugin():
    """Install a plugin from a Git repository URL. Uses CLI install-from-url."""
    data = request.get_json() or {}
    url = data.get("url", "")

    ok, err = _validate_install_url(url)
    if not ok:
        return jsonify({"success": False, "error": err}), 400

    cli = _cli_script()
    if not os.path.isfile(cli):
        return jsonify({"success": False, "error": "Plugin CLI not found"}), 500

    project_dir = _project_dir()
    env = {**os.environ, "PROJECT_DIR": project_dir}

    try:
        result = subprocess.run(
            ["bash", cli, "install-from-url", url.strip()],
            env=env,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Install timed out"}), 500
    except Exception as e:
        logger.exception("Plugin install subprocess failed")
        return jsonify({"success": False, "error": str(e)}), 500

    # Check if install succeeded by looking for "[INFO] Done" in output
    # This handles cases where restart fails but plugin was installed
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    install_succeeded = "[INFO] Done" in output or result.returncode == 0
    
    if not install_succeeded:
        err_msg = result.stderr.strip() or result.stdout.strip() or "Install failed"
        logger.warning("Plugin install failed: %s", err_msg)
        return jsonify({"success": False, "error": err_msg}), 400
    
    # Log any warnings but still return success if plugin was installed
    if result.returncode != 0:
        logger.warning("Plugin install completed but CLI exited with code %d: %s", 
                      result.returncode, output.strip())
    
    return jsonify({"success": True})


@plugin_manage_bp.route("/pluginmanager-api/uninstall", methods=["POST"])
def uninstall_plugin():
    """Uninstall a third-party plugin by id. Only allows plugins with repository set."""
    data = request.get_json() or {}
    plugin_id = (data.get("plugin_id") or "").strip()

    if not plugin_id:
        return jsonify({"success": False, "error": "plugin_id is required"}), 400

    third_party = _third_party_plugins()
    allowed_ids = {p["id"] for p in third_party}
    if plugin_id not in allowed_ids:
        return jsonify({"success": False, "error": "Plugin not found or cannot be uninstalled"}), 400

    cli = _cli_script()
    if not os.path.isfile(cli):
        return jsonify({"success": False, "error": "Plugin CLI not found"}), 500

    project_dir = _project_dir()
    env = {**os.environ, "PROJECT_DIR": project_dir}

    try:
        result = subprocess.run(
            ["bash", cli, "uninstall", plugin_id],
            env=env,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Uninstall timed out"}), 500
    except Exception as e:
        logger.exception("Plugin uninstall subprocess failed")
        return jsonify({"success": False, "error": str(e)}), 500

    # Check if uninstall succeeded by looking for success message in output
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    uninstall_succeeded = "Plugin successfully uninstalled" in output or result.returncode == 0
    
    if not uninstall_succeeded:
        err_msg = result.stderr.strip() or result.stdout.strip() or "Uninstall failed"
        logger.warning("Plugin uninstall failed: %s", err_msg)
        return jsonify({"success": False, "error": err_msg}), 400
    
    # Log any warnings but still return success if plugin was uninstalled
    if result.returncode != 0:
        logger.warning("Plugin uninstall completed but CLI exited with code %d: %s", 
                      result.returncode, output.strip())
    
    return jsonify({"success": True})


@plugin_manage_bp.route("/pluginmanager-api/update", methods=["POST"])
def update_plugin():
    """Update a third-party plugin by reinstalling from its repository. Only allows plugins with repository set."""
    data = request.get_json() or {}
    plugin_id = (data.get("plugin_id") or "").strip()

    if not plugin_id:
        return jsonify({"success": False, "error": "plugin_id is required"}), 400

    third_party = _third_party_plugins()
    plugin_info = next((p for p in third_party if p["id"] == plugin_id), None)
    if not plugin_info:
        return jsonify({"success": False, "error": "Plugin not found or cannot be updated"}), 400

    repo_url = plugin_info.get("repository", "").strip()
    if not repo_url:
        return jsonify({"success": False, "error": "Plugin repository URL not found"}), 400

    cli = _cli_script()
    if not os.path.isfile(cli):
        return jsonify({"success": False, "error": "Plugin CLI not found"}), 500

    project_dir = _project_dir()
    env = {**os.environ, "PROJECT_DIR": project_dir}

    try:
        result = subprocess.run(
            ["bash", cli, "install", plugin_id, repo_url],
            env=env,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Update timed out"}), 500
    except Exception as e:
        logger.exception("Plugin update subprocess failed")
        return jsonify({"success": False, "error": str(e)}), 500

    # Check if update succeeded by looking for "[INFO] Done" in output
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    update_succeeded = "[INFO] Done" in output or result.returncode == 0
    
    if not update_succeeded:
        err_msg = result.stderr.strip() or result.stdout.strip() or "Update failed"
        logger.warning("Plugin update failed: %s", err_msg)
        return jsonify({"success": False, "error": err_msg}), 400
    
    # Log any warnings but still return success if plugin was updated
    if result.returncode != 0:
        logger.warning("Plugin update completed but CLI exited with code %d: %s", 
                      result.returncode, output.strip())
    
    return jsonify({"success": True})


@plugin_manage_bp.route("/pluginmanager-api/core-changes", methods=["GET"])
def serve_core_changes():
    """Serve the CORE_CHANGES.md file."""
    try:
        import os
        md_path = os.path.join(os.path.dirname(__file__), "CORE_CHANGES.md")
        if os.path.exists(md_path):
            from flask import send_file
            return send_file(md_path, mimetype='text/markdown', as_attachment=False)
        else:
            return jsonify({"error": "CORE_CHANGES.md not found"}), 404
    except Exception as e:
        logger.exception("Failed to serve CORE_CHANGES.md")
        return jsonify({"error": str(e)}), 500


@plugin_manage_bp.route("/pluginmanager-api/check-patch", methods=["GET"])
def check_patch():
    """Check if core files need patching."""
    try:
        is_patched, missing = check_core_patched()
        return jsonify({
            "success": True,
            "is_patched": is_patched,
            "missing_parts": missing
        })
    except Exception as e:
        logger.exception("Failed to check patch status")
        return jsonify({"success": False, "error": str(e)}), 500


@plugin_manage_bp.route("/pluginmanager-api/patch-core", methods=["POST"])
def patch_core():
    """Patch core files to add blueprint registration support."""
    try:
        # Use the patch script (similar to install/uninstall using CLI script)
        patch_script = os.path.join(os.path.dirname(__file__), "patch-core.sh")
        if not os.path.isfile(patch_script):
            # Fallback to direct Python call if script doesn't exist
            success, error = patch_core_files()
            if not success:
                return jsonify({"success": False, "error": error}), 500
            
            # Restart service
            appname = os.environ.get("APPNAME")
            if appname:
                import subprocess
                project_dir = _project_dir()
                env = {**os.environ, "PROJECT_DIR": project_dir}
                try:
                    subprocess.run(
                        ["sudo", "systemctl", "restart", f"{appname}.service"],
                        env=env,
                        cwd=project_dir,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                except Exception as e:
                    logger.warning(f"Could not restart service: {e}")
            
            return jsonify({"success": True, "message": "Core files patched successfully"})
        
        # Use patch script (preferred method)
        project_dir = _project_dir()
        env = {**os.environ, "PROJECT_DIR": project_dir}
        
        result = subprocess.run(
            ["bash", patch_script],
            env=env,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        patch_succeeded = "[INFO] Done" in output or result.returncode == 0
        
        if not patch_succeeded:
            err_msg = result.stderr.strip() or result.stdout.strip() or "Patch failed"
            logger.warning("Core patch failed: %s", err_msg)
            return jsonify({"success": False, "error": err_msg}), 400
        
        if result.returncode != 0:
            logger.warning("Core patch completed but script exited with code %d: %s", 
                          result.returncode, output.strip())
        
        return jsonify({"success": True, "message": "Core files patched successfully"})
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Patch timed out"}), 500
    except Exception as e:
        logger.exception("Failed to patch core files")
        return jsonify({"success": False, "error": str(e)}), 500
