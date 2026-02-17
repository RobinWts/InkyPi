# Hardware Buttons Reg Test

A **test plugin** for validating the action registration system of the Hardware Buttons plugin.

## Purpose

This plugin exists to verify that:

- Plugins can register **anytime actions** and **display actions** with the Hardware Buttons plugin
- Actions are correctly discovered and shown in the button binding dropdown
- Action callbacks execute when buttons are pressed
- Actions can trigger display refreshes and modify displayed content

It is intended for development and testing only, not for regular use on a display.

## How It Works

- **Settings:** Single headline text input (default: "Instance Display")
- **Display:** Renders the headline plus "The buttons actions 1-4 are now available!"
- **Registered actions:**
  - **RegTest: Force Display** (anytime) – Sets headline to "Forced display" and forces this plugin to display
  - **Display Action 1–4** (display) – Change the headline to "action No 1 pressed" through "action No 4 pressed" and refresh

## Testing Steps

1. Add this plugin to a playlist
2. Open Hardware Buttons settings and bind a button to **RegTest: Force Display** or to **Display Action 1/2/3/4**
3. Display an instance of this plugin (via playlist or Update now)
4. Press the bound buttons and confirm the headline updates and the display refreshes

## See Also

- [PLUGIN_ACTION_REGISTRATION.md](../hardwarebuttons/PLUGIN_ACTION_REGISTRATION.md) – Guide for plugin authors
- [ACTION_REGISTRATION_PLAN.md](../hardwarebuttons/ACTION_REGISTRATION_PLAN.md) – Design document
