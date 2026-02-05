# Node-RED Plugin Implementation Plan

## Overview
Simple plugin that fetches JSON data from a Node-RED HTTP endpoint and displays it on the e-ink display.

## Components

### 1. Settings (`settings.html`)
- **Node-RED URL**: Text input for base URL (e.g., `http://localhost:1880`)
- **Endpoint Path**: Text input for endpoint path (e.g., `/inkypi/data`)
- **Timeout**: Number input for HTTP timeout in seconds (default: 10)

### 2. Python Implementation (`node_red.py`)
- Fetch data from Node-RED endpoint via HTTP GET
- Parse JSON response
- Log data to console for debugging
- Handle errors gracefully
- Render data using HTML template

### 3. HTML Template (`render/node_red.html`)
- Display JSON data in readable format
- Show key-value pairs
- Handle nested objects/arrays
- Display error messages if fetch fails

### 4. CSS Styling (`render/node_red.css`)
- Clean, readable layout for JSON data
- Proper spacing and typography
- E-ink friendly (high contrast)

## Implementation Steps

### Step 1: Update `settings.html`
- Add form inputs for Node-RED URL and endpoint path
- Add timeout setting
- Add prepopulation logic for edit mode

### Step 2: Implement `node_red.py`
- Import required modules (requests, json, logging)
- Implement `generate_image` method:
  - Get settings (URL, path, timeout)
  - Construct full endpoint URL
  - Make HTTP GET request with timeout
  - Log request/response to console
  - Parse JSON response
  - Log parsed data to console
  - Render using HTML template
  - Handle all error cases

### Step 3: Create HTML Template
- Extend `plugin.html`
- Display JSON data in structured format
- Show error messages if needed
- Use Jinja2 templating for data display

### Step 4: Style with CSS
- Create readable layout
- Style JSON display (key-value pairs)
- Ensure good contrast for e-ink

## Error Handling
- Network errors (connection refused, timeout)
- HTTP errors (404, 500, etc.)
- Invalid JSON responses
- Missing settings
- Empty responses

All errors should:
- Log to console with details
- Display user-friendly message on screen
- Not crash the plugin

## Debugging
- Log full request URL
- Log HTTP status code
- Log response headers (if needed)
- Log parsed JSON data
- Log any errors with full traceback

## Testing Checklist
- [ ] Plugin loads without errors
- [ ] Settings form displays correctly
- [ ] Settings save and load correctly
- [ ] HTTP request works with valid endpoint
- [ ] JSON data displays correctly
- [ ] Console logging works
- [ ] Error handling works for various failure cases
- [ ] Works with different JSON structures
- [ ] Handles nested objects/arrays
- [ ] Timeout works correctly
