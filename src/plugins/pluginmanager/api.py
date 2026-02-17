"""API routes for pluginmanager plugin - handles install/uninstall/update of third-party plugins."""

import os
import subprocess
from urllib.parse import urlparse

from flask import Blueprint, request, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

plugin_manage_bp = Blueprint("pluginmanager_api", __name__)


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


@plugin_manage_bp.route("/pluginmanager-api/check-updates", methods=["POST"])
def check_updates():
    """Check if a plugin has updates available by comparing local and remote commits."""
    data = request.get_json() or {}
    plugin_id = (data.get("plugin_id") or "").strip()

    if not plugin_id:
        return jsonify({"success": False, "error": "plugin_id is required"}), 400

    third_party = _third_party_plugins()
    plugin_info = next((p for p in third_party if p["id"] == plugin_id), None)
    if not plugin_info:
        return jsonify({"success": False, "error": "Plugin not found"}), 400

    repo_url = plugin_info.get("repository", "").strip()
    if not repo_url:
        return jsonify({"success": False, "error": "Plugin repository URL not found"}), 400

    try:
        from config import Config
        plugins_dir = os.path.join(Config.BASE_DIR, "plugins")
        plugin_dir = os.path.join(plugins_dir, plugin_id)
        git_dir = os.path.join(plugin_dir, ".git")
        
        if not os.path.isdir(git_dir):
            return jsonify({"success": False, "error": "Plugin is not a git repository"}), 400
        
        # Get current local commit hash
        local_commit_result = subprocess.run(
            ["git", "-C", plugin_dir, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        if local_commit_result.returncode != 0:
            logger.warning(f"Could not get local commit for {plugin_id}")
            return jsonify({"success": False, "error": "Could not determine current version"}), 500
        
        local_commit = local_commit_result.stdout.strip()
        
        # Get remote URL to query directly
        remote_url_result = subprocess.run(
            ["git", "-C", plugin_dir, "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        if remote_url_result.returncode != 0:
            logger.warning(f"Could not get remote URL for {plugin_id}")
            return jsonify({"success": False, "error": "Could not determine remote repository"}), 500
        
        remote_url = remote_url_result.stdout.strip()
        
        # Use ls-remote to get the remote HEAD commit without needing to fetch
        # This works even with shallow clones
        ls_remote_result = subprocess.run(
            ["git", "ls-remote", "--heads", remote_url],
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if ls_remote_result.returncode != 0:
            logger.warning(f"Could not query remote for {plugin_id}: {ls_remote_result.stderr}")
            return jsonify({"success": False, "error": "Failed to check remote repository"}), 500
        
        # Parse ls-remote output to find the default branch
        # Format: <commit_hash>    refs/heads/<branch_name>
        remote_refs = ls_remote_result.stdout.strip().split("\n")
        remote_commit = None
        default_branch = None
        
        # Try common branch names first
        for branch_name in ["main", "master", "develop"]:
            for ref_line in remote_refs:
                if f"refs/heads/{branch_name}" in ref_line:
                    parts = ref_line.split()
                    if len(parts) >= 1:
                        remote_commit = parts[0]
                        default_branch = branch_name
                        break
            if remote_commit:
                break
        
        # If no common branch found, use the first ref
        if not remote_commit and remote_refs:
            first_ref = remote_refs[0]
            parts = first_ref.split()
            if len(parts) >= 2:
                remote_commit = parts[0]
                # Extract branch name from refs/heads/branch_name
                ref_path = parts[1]
                if "refs/heads/" in ref_path:
                    default_branch = ref_path.replace("refs/heads/", "")
        
        if not remote_commit:
            logger.warning(f"Could not determine remote commit for {plugin_id}")
            return jsonify({"success": True, "has_updates": False, "commits_behind": 0})
        
        # Compare commits directly
        # With shallow clones, we can't reliably count commits behind, so we just check if they differ
        if local_commit == remote_commit:
            return jsonify({"success": True, "has_updates": False, "commits_behind": 0})
        else:
            # Commits differ - there are updates available
            # Note: With shallow clones, we can't reliably count commits behind,
            # but we know there's a difference, so updates are available
            return jsonify({"success": True, "has_updates": True, "commits_behind": 1})
            
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Check updates timed out"}), 500
    except Exception as e:
        logger.exception("Failed to check for plugin updates")
        return jsonify({"success": False, "error": str(e)}), 500


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


