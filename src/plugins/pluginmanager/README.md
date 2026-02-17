# InkyPi-Plugin-PluginManager

![Example of InkyPi-Plugin-PluginManager](./example.png)

*InkyPi-Plugin-PluginManager* is a plugin for [InkyPi](https://github.com/fatihak/InkyPi) that provides a web-based interface for managing third-party plugins.

## What it does

The Plugin Manager enables you to install, update, and uninstall third-party InkyPi plugins directly from the web interface, without needing to use the command line.

### Features

- **Install Plugins**: Install third-party plugins directly from GitHub repositories by simply entering the repository URL
- **View Installed Plugins**: See all installed third-party plugins with their display names and version timestamps (last commit date)
- **Check for Updates**: Check if updates are available for installed plugins by comparing local and remote commit hashes
- **Update Plugins**: Update installed plugins to the latest version from their repository after checking for updates
- **Uninstall Plugins**: Remove plugins you no longer need with confirmation dialogs
- **Version Information**: Display the version timestamp (last commit date) for each installed plugin
- **Automatic Validation**: Validates that plugins are properly structured (require `plugin-info.json` with `id` matching folder name)
- **GitHub-Only**: Only accepts GitHub.com repository URLs for security
- **Service Management**: Automatically restarts the InkyPi service after plugin operations


### Requirements

- InkyPi must be installed and running
- Core files must be patched (one-time operation, see Installation section below)
- Plugins must be hosted on GitHub.com
- Plugins must have a `plugin-info.json` file with an `id` field that matches the folder name

## Installation

### Step 1: Install the Plugin Manager

Install the plugin using the InkyPi CLI, providing the plugin ID and GitHub repository URL:

```bash
inkypi plugin install pluginmanager https://github.com/RobinWts/InkyPi-Plugin-PluginManager
```

### Step 2: Patch Core Files

After successful installation, a patch of two core files is needed to enable the Plugin Manager functionality. This is a **one-time operation** that adds generic blueprint registration support to InkyPi's core. It will be appied automatically when you access the PluginManager the first time.

See [CORE_CHANGES.md](./pluginmanager/CORE_CHANGES.md) for detailed information about what the patch does and why it's needed.

## Usage

### Installing a Plugin

1. Open the Plugin Manager from the main InkyPi page
2. In the "Install from GitHub" section at the bottom, paste the GitHub repository URL
3. Click "Install"
4. Wait for the installation to complete (the service will restart automatically)
5. Click "Reload page" when prompted, give it a few seconds.

**Example:**
```
https://github.com/fatihak/InkyPi-Plugin-Template
```

### Viewing Installed Plugins

The "Installed third-party plugins" section displays:
- **Plugin Name**: The display name of the plugin (from `plugin-info.json`)
- **Version Timestamp**: Shows "Version timestamp:" followed by the complete commit timestamp (date, time, and timezone) of the last commit in the local repository
- **Check Updates Button**: Blue button labeled "check updates" to check for available updates
- **Delete Button**: Red button with "×" to uninstall the plugin

### Checking for Updates and Updating a Plugin

1. Find the plugin in the "Installed third-party plugins" list
2. Click the "check updates" button next to the plugin
3. The system will check the remote repository for new commits:
   - If no updates are available, you'll see a "No updates available!" message
   - If updates are available, you'll be prompted with an "Updates available!" dialog
4. If updates are available, click "OK" (or "Update") in the dialog to proceed with the update
5. Wait for the update to complete (the service will restart automatically)
6. Click "Reload page" when prompted, wait a few seconds to let the service restart completely.

**Note**: The update check compares the local commit hash with the remote repository's commit hash. If they differ, updates are available.

### Uninstalling a Plugin

1. Find the plugin in the "Installed third-party plugins" list
2. Click the delete button (×) next to the plugin
3. Confirm the uninstallation
4. Wait for the uninstallation to complete (the service will restart automatically)
5. Click "Reload page" when prompted

**Note**: Uninstalling a plugin will remove it from your system. Any plugin instances in playlists need be removed manually.

## Troubleshooting

### Plugin Manager shows "Core files need to be patched"

This means the core patch hasn't been applied yet or has been overwritten by a InkyPi-update. Follow the installation instructions above to run `patch-core.sh`.

### Installation fails with "No valid InkyPi plugin found"

Make sure:
- The repository URL is correct and accessible
- The repository contains a folder with a `plugin-info.json` file
- The `id` field in `plugin-info.json` matches the folder name
- The repository is hosted on GitHub.com (other Git hosts are not supported)

### Update check always shows "No updates available"

If the update check always reports no updates even when you know updates exist:
1. Ensure the plugin was installed via git clone (it should have a `.git` directory)
2. Check that the remote repository URL is correct and accessible
3. Verify network connectivity to GitHub.com

### Service doesn't restart after operations

If the service doesn't restart automatically:
1. Check that the `inkypi.service` exists: `systemctl list-unit-files | grep inkypi`
2. Manually restart: `sudo systemctl restart inkypi.service`

## Development Status

This plugin is actively maintained.

## License

This project is licensed under the GNU General Public License v3.0.
