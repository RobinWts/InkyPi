# Generic Action Registration System for Hardware Buttons Plugin

## Overview

This document describes the design and implementation plan for a generic action registration system that allows any InkyPi plugin to register custom actions that can be bound to hardware buttons.

## Requirements

### Two Types of Actions

1. **Anytime Actions**
   - Can be triggered at any time regardless of what is currently displayed
   - Each action needs:
     - A unique action ID (scoped to the plugin, e.g., `pluginid_actionname`)
     - A descriptive label for the binding dropdown UI
     - A callback function to execute when triggered

2. **Display Actions** (context-dependent actions)
   - Can only be triggered when an instance of the registering plugin is currently displayed
   - Plugins register an array of 0-N display actions (e.g., `[action_0, action_1, action_2, ...]`)
   - The binding dropdown shows a generic list based on the **maximum** number of display actions registered by any plugin:
     - If plugin A registers 1 display action, plugin B registers 2, and plugin C registers 0, the dropdown will show:
       - "Display Action 1"
       - "Display Action 2"
   - When a "Display Action N" binding is triggered:
     1. Check which plugin is currently displayed (via `device_config.get_refresh_info().plugin_id`)
     2. Look up that plugin's registered display actions array
     3. If the plugin has an action at index N, call it
     4. Otherwise, log a warning and do nothing

### Registration Mechanism

- Plugins register actions by calling a registration function exposed by the hardwarebuttons plugin
- Registration happens during blueprint initialization (using `Blueprint.record_once`)
- The hardwarebuttons plugin maintains a central registry of all registered actions

### Execution

- When a button triggers an action:
  - For anytime actions: execute immediately
  - For display actions: check current display state, resolve the plugin's action, and execute if available
- Actions receive context about the current state (e.g., which plugin instance is displayed, playlist info)

## Detailed Design

### 1. Action Registry Structure

Create a new module `src/plugins/hardwarebuttons/action_registry.py`:

```python
# Global registry structure:
_action_registry = {
    "anytime": {
        # plugin_id_actionname: {
        #     "label": "Descriptive name",
        #     "plugin_id": "pluginid",
        #     "callback": callable
        # }
    },
    "display": {
        # plugin_id: [
        #     callable_for_action_0,
        #     callable_for_action_1,
        #     ...
        # ]
    }
}
```

**Key functions:**

- `register_anytime_action(plugin_id, action_name, label, callback)`
  - Validates inputs
  - Stores action with ID `f"{plugin_id}_{action_name}"`
  - Allows overwriting if the same plugin re-registers

- `register_display_actions(plugin_id, actions_array)`
  - Validates that `actions_array` is a list of callables
  - Stores the entire array for the plugin
  - Allows overwriting if the same plugin re-registers

- `get_all_anytime_actions()` → list of dicts with `{id, label, group, plugin_id}`

- `get_max_display_action_count()` → int (max length of any plugin's display actions array)

- `get_display_action(plugin_id, action_index)` → callable or None

- `execute_plugin_action(action_id, refs)` → execute an anytime action by ID

- `execute_display_action(action_index, refs)` → resolve current plugin, get its action at index, execute

### 2. Registration API for Plugins

Add a function in `src/plugins/hardwarebuttons/action_registry.py` that plugins can import:

```python
def register_actions(plugin_id, anytime_actions=None, display_actions=None):
    """
    Register actions for hardware button bindings.
    
    Args:
        plugin_id: str - unique plugin identifier
        anytime_actions: dict or None
            {
                "action_name": {
                    "label": "User-visible action label",
                    "callback": callable
                },
                ...
            }
        display_actions: list or None
            [
                callable_for_display_action_0,
                callable_for_display_action_1,
                ...
            ]
    """
```

### 3. Integration with Discovery

Update `src/plugins/hardwarebuttons/discovery.py`:

- `get_available_actions(device_config)` should:
  1. Start with builtin actions (Core, System) as before
  2. Call `action_registry.get_all_anytime_actions()` and add them to the list with group "Other Plugins"
  3. Call `action_registry.get_max_display_action_count()` and generate entries like:
     - `{"id": "display_action_0", "label": "Display Action 1", "group": "Current Plugin"}`
     - `{"id": "display_action_1", "label": "Display Action 2", "group": "Current Plugin"}`
     - etc. for N entries

### 4. Integration with Actions Executor

Update `src/plugins/hardwarebuttons/actions.py`:

In `_run_action_impl`:

1. Check if `action_id` starts with a registered plugin ID (lookup in anytime registry)
   - If yes, call `action_registry.execute_plugin_action(action_id, refs)`
   - Pass refs to the callback (so plugins can access device_config, refresh_task, etc.)

2. Check if `action_id` matches `"display_action_N"` pattern
   - Extract index N
   - Call `action_registry.execute_display_action(N, refs)`
   - This function will:
     - Get current plugin_id from `device_config.get_refresh_info().plugin_id`
     - Look up that plugin's display actions array
     - Call `actions_array[N]` if it exists, passing refs

### 5. Callback Signature

Plugin callbacks receive a single `refs` dict:

```python
def my_action_callback(refs):
    """
    Args:
        refs: dict with keys:
            - device_config: Config instance
            - refresh_task: RefreshTask instance
            - app: Flask app instance
            - (optional) current_plugin_instance: PluginInstance if display action
    """
```

### 6. Example Plugin Registration

A plugin wanting to register actions would do this in its `api.py`:

```python
from flask import Blueprint

my_bp = Blueprint("my_plugin_api", __name__)

@my_bp.record_once
def _register_my_actions(state):
    try:
        from plugins.hardwarebuttons import action_registry
    except ImportError:
        # Hardware buttons plugin not installed
        return
    
    # Anytime actions
    def my_action_1(refs):
        # Do something...
        pass
    
    def my_action_2(refs):
        # Do something else...
        pass
    
    # Display actions (can only be called when this plugin is displayed)
    def display_next_slide(refs):
        # Advance to next slide of this plugin instance
        pass
    
    def display_prev_slide(refs):
        # Go to previous slide
        pass
    
    action_registry.register_actions(
        plugin_id="my_plugin",
        anytime_actions={
            "reload": {
                "label": "Reload My Plugin Data",
                "callback": my_action_1
            },
            "toggle_mode": {
                "label": "Toggle Display Mode",
                "callback": my_action_2
            }
        },
        display_actions=[
            display_next_slide,  # Display Action 1
            display_prev_slide,  # Display Action 2
        ]
    )
```

### 7. Thread Safety

- Use a lock when accessing/modifying the registry (same pattern as `_action_lock` in `actions.py`)
- Registration happens once per plugin during blueprint setup (single-threaded)
- Execution can happen from GPIO thread or API routes (needs lock)

### 8. Error Handling

- Validate all inputs during registration (log warnings for invalid registrations)
- Gracefully handle:
  - Callback raises exception → log error, continue
  - Display action triggered but no plugin displayed → log warning, no-op
  - Display action triggered but current plugin doesn't have that action → log warning, no-op
  - Plugin tries to register after registry is in use → allow (support dynamic plugin loading)

### 9. Documentation for Plugin Authors

Create `src/plugins/hardwarebuttons/PLUGIN_ACTION_REGISTRATION.md`:

- Explain the two action types with use cases
- Show the registration pattern with complete examples
- Document the callback signature and what's available in `refs`
- Explain thread safety considerations (actions may be called from GPIO thread)
- Provide examples:
  - Weather plugin: "Update Weather Now" (anytime), "Next City" (display)
  - Calendar plugin: "Sync Calendar" (anytime), "Next Event" / "Previous Event" (display)
  - Image folder plugin: "Next Image" / "Previous Image" / "Random Image" (display)

## Implementation Steps

### Phase 1: Core Registry (Minimal Viable Implementation)

1. Create `action_registry.py` with:
   - Registry data structure
   - `register_actions()` function
   - `get_all_anytime_actions()`
   - `get_max_display_action_count()`
   - `get_display_action(plugin_id, action_index)`
   - Thread-safe access patterns

2. Update `discovery.py`:
   - Import action_registry
   - Add plugin anytime actions to available actions list
   - Add generic "Display Action 1", "Display Action 2", etc. based on max count

3. Update `actions.py`:
   - Import action_registry
   - Add handler for plugin anytime actions in `_run_action_impl`
   - Add handler for display actions in `_run_action_impl`

4. Test with hardcoded registration (temporarily add test registration in `api.py` blueprint record_once)

### Phase 2: Display Action Resolution

1. Implement display action resolution logic:
   - Get current plugin_id from refresh_info
   - Look up plugin's display actions array
   - Call action at the specified index

2. Handle edge cases:
   - No plugin currently displayed
   - Current plugin has no display actions registered
   - Action index out of bounds for current plugin

3. Add logging for debugging

### Phase 3: Documentation and Polish

1. Create `PLUGIN_ACTION_REGISTRATION.md` with:
   - Complete guide for plugin developers
   - Multiple examples covering common use cases
   - Best practices and gotchas

2. Update `README.md`:
   - Mention that other plugins can register custom actions
   - Link to the plugin action registration guide

3. Add inline code comments explaining the registry pattern

### Phase 4: Example Implementation

1. Create a simple example plugin (or update an existing one like `image_folder`) to demonstrate action registration
2. Show anytime action (e.g., "Reload Images")
3. Show display actions (e.g., "Next Image", "Previous Image", "Random Image")

### Phase 5: Settings UI Enhancement (Optional Future Work)

Enhance the settings page to show which plugins have registered actions:

- Add a collapsible section showing registered actions by plugin
- Visual feedback when hovering over actions in dropdown (show which plugin provides it)
- Help text explaining display actions vs anytime actions

## Open Questions / Clarifications Needed

### 1. Display Action Context

**Question:** Should display action callbacks receive information about the currently displayed plugin instance?

**Options:**
- A) Pass only generic refs (device_config, refresh_task)
- B) Also pass the current `PluginInstance` object (with its settings, name, etc.)

**Recommendation:** Option B - add `current_plugin_instance` to refs for display actions. This allows actions like "toggle setting X for this instance" or "navigate within this instance's data."
**Decision:** Option B

### 2. Display Action Naming

**Question:** Should we use generic labels ("Display Action 1", "Display Action 2") or try to show plugin-specific labels?

**Options:**
- A) Generic labels (simpler, works with current requirement)
- B) Dynamic labels that change based on which plugin is displayed (more complex, requires UI updates)

**Recommendation:** Option A for now (matches requirements). Option B could be a future enhancement if users request it.
**Decision:** Option A

### 3. Execution Context

**Question:** Should plugin actions have access to request context (e.g., for calling plugin instance's generate_image)?

**Recommendation:** Plugin actions run outside request context (triggered by GPIO). Provide the Flask app in refs so plugins can create an app context if needed:
**Decision:** Yes, provide the flask app

```python
def my_action(refs):
    app = refs.get("app")
    with app.app_context():
        # Now can access current_app, etc.
        pass
```

### 4. Action Documentation in Plugin-Info

**Question:** Should plugins declare their actions in `plugin-info.json` for documentation purposes?

**Options:**
- A) No, registration is code-only (simpler, more flexible)
- B) Add optional `"actions"` field to `plugin-info.json` for documentation

**Recommendation:** Option A for initial implementation. Option B could be added later if we want to build a "plugin capabilities" UI.
**Decision:** Option A

### 5. Maximum Display Actions Limit

**Question:** Should we enforce a reasonable maximum for display actions per plugin?

**Recommendation:** Yes, enforce a maximum of 10 display actions per plugin. This keeps the dropdown manageable and prevents abuse. Log a warning if a plugin tries to register more.
**Decision:** max 6 actions

## Testing Strategy

### Unit Tests

- Test action_registry functions in isolation:
  - Register and retrieve anytime actions
  - Register and retrieve display actions
  - Handle duplicate registrations (same plugin registers twice)
  - Handle invalid inputs (non-callable, missing labels, etc.)

### Integration Tests

1. **Mock Plugin Registration:**
   - Create mock plugin that registers 2 anytime actions and 3 display actions
   - Verify they appear in available_actions list
   - Verify dropdown shows "Display Action 1", "Display Action 2", "Display Action 3"

2. **Action Execution:**
   - Trigger anytime action → verify callback is called with correct refs
   - Set up mock refresh_info with plugin_id
   - Trigger display action → verify correct plugin's action is called
   - Trigger display action when different plugin displayed → verify no-op

3. **Edge Cases:**
   - Trigger display action when no plugin displayed → verify graceful handling
   - Trigger display action index that current plugin doesn't have → verify no-op
   - Plugin callback raises exception → verify error is logged and execution continues

### Manual Testing

1. Install hardware buttons plugin
2. Create a test plugin with action registration
3. Configure a button to trigger plugin's anytime action
4. Configure a button to trigger Display Action 1
5. Display an instance of the test plugin
6. Press buttons and verify actions execute correctly
7. Display a different plugin and press Display Action button → verify no-op

## Future Enhancements

### 1. Action Metadata

Allow plugins to provide metadata for their actions:

```python
{
    "icon": "path/to/icon.png",
    "description": "Detailed description for settings page",
    "category": "Navigation",  # For grouping in UI
}
```

### 2. Dynamic Display Action Labels

Show context-aware labels in the dropdown that update based on which plugin is currently displayed:
- When weather plugin is displayed: "Next City", "Previous City"
- When calendar plugin is displayed: "Next Event", "Previous Event"

### 3. Action Preview/Test Button

Add a "Test Action" button in the settings UI that triggers the action once for debugging.

### 4. Action Permissions

Some actions might need elevated permissions (e.g., system shutdown). Add a permission system where actions can declare their requirements and the UI shows warnings.

### 5. Multi-Instance Display Actions

Currently display actions are per plugin type. Consider supporting actions per plugin instance:
- Instance A of Weather plugin: "Show forecast for London"
- Instance B of Weather plugin: "Show forecast for New York"

This would require a more complex binding system (bind button to specific instance + action).

## Migration and Backward Compatibility

- Existing button configurations continue to work (builtin actions unchanged)
- Plugin action registration is opt-in (plugins without registration work as before)
- If a plugin registers actions and is later uninstalled, those actions simply won't be available (graceful degradation)
- Action IDs are scoped by plugin_id to avoid collisions

## Summary

This design provides a flexible, extensible action registration system that:

1. ✅ Allows plugins to register "anytime" and "display" actions
2. ✅ Uses descriptive labels for anytime actions
3. ✅ Uses generic labels for display actions (scalable to max registered)
4. ✅ Checks current display state for display actions
5. ✅ Is thread-safe and handles errors gracefully
6. ✅ Requires minimal changes to existing code
7. ✅ Provides clear API for plugin developers
8. ✅ Follows InkyPi plugin patterns (blueprint registration, no core changes)

## Next Steps

Please review this plan and provide feedback on:

1. ✅ Overall approach and architecture
2. ❓ Open questions that need decisions (see section above)
3. ❓ Any additional requirements or edge cases I should consider
4. ✅ Priority of implementation phases (should we skip Phase 4-5 for now?)

Once approved, I will proceed with implementation starting with Phase 1.
