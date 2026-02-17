"""Discover available button actions for the hardwarebuttons plugin.

This plugin intentionally exposes only built-in actions (Core/System), plus its own
"external script" and "call URL" actions. It does not load/merge actions from other
plugins.
"""

import logging

logger = logging.getLogger(__name__)

# Built-in action IDs and labels (grouped as Core / System)
BUILTIN_ACTIONS = [
    {"id": "core_trigger_refresh", "label": "Trigger refresh (next in playlist)", "group": "Core"},
    {"id": "core_force_refresh", "label": "Force refresh (re-show current)", "group": "Core"},
    {"id": "core_next_playlist", "label": "Next playlist item", "group": "Core"},
    {"id": "core_prev_playlist", "label": "Previous playlist item", "group": "Core"},
    {"id": "system_shutdown", "label": "Shutdown", "group": "System"},
    {"id": "system_reboot", "label": "Reboot", "group": "System"},
    {"id": "system_restart_inkypi", "label": "Restart InkyPi service", "group": "System"},
    {"id": "external_script", "label": "Run external bash script", "group": "System"},
    {"id": "call_url", "label": "Call URL", "group": "System"},
]
# No-action option for dropdowns
NO_ACTION_ID = ""


def get_available_actions(device_config):
    """Build list of actions for dropdowns.

    Args:
        device_config: Config instance (unused; kept for backward compatibility with callers).

    Returns:
        List of dicts: id, label, group ("Core" | "System").
    """
    logger.debug("get_available_actions called")
    out = []
    # No-action first
    out.append({"id": NO_ACTION_ID, "label": "(No action)", "group": "Core"})

    for a in BUILTIN_ACTIONS:
        out.append(dict(a))
    logger.debug("get_available_actions: added %d built-in actions", len(BUILTIN_ACTIONS))
    logger.debug("get_available_actions: total %d actions", len(out))
    return out
