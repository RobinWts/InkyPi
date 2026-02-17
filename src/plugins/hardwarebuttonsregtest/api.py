"""API and action registration for hardwarebuttonsregtest plugin."""

import logging

from flask import Blueprint

from . import hardwarebuttonsregtest as plugin_module

logger = logging.getLogger(__name__)

hardwarebuttonsregtest_bp = Blueprint("hardwarebuttonsregtest_api", __name__)


@hardwarebuttonsregtest_bp.record_once
def _register_actions(state):
    """Register 1 anytime action and 4 display actions with hardwarebuttons."""
    try:
        from plugins.hardwarebuttons import action_registry
    except ImportError:
        logger.debug("hardwarebuttons plugin not installed, skipping action registration")
        return

    def _trigger_refresh(refs, headline_override):
        """Set override headline and force display of this plugin."""
        plugin_module._set_override_headline(headline_override)

        device_config = refs.get("device_config")
        refresh_task = refs.get("refresh_task")
        playlist_manager = device_config.get_playlist_manager()

        # Try to find an instance in active or any playlist
        playlist = None
        instance = None
        active_name = playlist_manager.active_playlist
        if active_name:
            playlist = playlist_manager.get_playlist(active_name)
            if playlist:
                instance = playlist.find_plugin(plugin_module.PLUGIN_ID, None)
                if instance is None:
                    for pi in playlist.plugins:
                        if pi.plugin_id == plugin_module.PLUGIN_ID:
                            instance = pi
                            break

        if not playlist or not instance:
            # Search any playlist for our plugin
            for name in playlist_manager.get_playlist_names():
                pl = playlist_manager.get_playlist(name)
                if pl:
                    for pi in pl.plugins:
                        if pi.plugin_id == plugin_module.PLUGIN_ID:
                            playlist = pl
                            instance = pi
                            break
                if instance:
                    break

        if playlist and instance:
            from refresh_task import PlaylistRefresh
            refresh_task.manual_update(PlaylistRefresh(playlist, instance, force=True))
        else:
            from refresh_task import ManualRefresh
            refresh_task.manual_update(
                ManualRefresh(plugin_module.PLUGIN_ID, {"headline": plugin_module.DEFAULT_HEADLINE})
            )

    def anytime_force_display(refs):
        """Anytime action: set headline to 'Forced display' and force display."""
        _trigger_refresh(refs, "Forced display")

    def _make_display_action(action_num):
        """Create display action callback for action 1-4."""

        def callback(refs):
            current_instance = refs.get("current_plugin_instance")
            device_config = refs.get("device_config")
            refresh_task = refs.get("refresh_task")
            refresh_info = device_config.get_refresh_info()

            if not refresh_info or getattr(refresh_info, "plugin_id", None) != plugin_module.PLUGIN_ID:
                return

            plugin_module._set_override_headline(f"action No {action_num} pressed")

            playlist_name = getattr(refresh_info, "playlist", None)
            instance_name = getattr(refresh_info, "plugin_instance", None)

            if playlist_name and instance_name:
                playlist_manager = device_config.get_playlist_manager()
                playlist = playlist_manager.get_playlist(playlist_name)
                if playlist:
                    instance = playlist.find_plugin(plugin_module.PLUGIN_ID, instance_name)
                    if instance:
                        from refresh_task import PlaylistRefresh
                        refresh_task.manual_update(
                            PlaylistRefresh(playlist, instance, force=True)
                        )
                        return

            # Manual Update or no playlist context: use instance settings or defaults
            from refresh_task import ManualRefresh
            settings = dict(current_instance.settings) if current_instance else {}
            if not settings:
                settings = {"headline": plugin_module.DEFAULT_HEADLINE}
            refresh_task.manual_update(ManualRefresh(plugin_module.PLUGIN_ID, settings))

        return callback

    action_registry.register_actions(
        plugin_id=plugin_module.PLUGIN_ID,
        anytime_actions={
            "force_display": {
                "label": "RegTest: Force Display",
                "callback": anytime_force_display,
            }
        },
        display_actions=[
            _make_display_action(1),
            _make_display_action(2),
            _make_display_action(3),
            _make_display_action(4),
        ],
    )
    logger.info("hardwarebuttonsregtest: registered 1 anytime + 4 display actions")
