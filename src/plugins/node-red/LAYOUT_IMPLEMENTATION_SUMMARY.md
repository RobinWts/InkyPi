# Layout Configuration Implementation Summary

## ✅ Implementation Complete

All features have been implemented according to the requirements.

## Features Implemented

### 1. Page Title ✅
- Optional title field in settings
- Displayed centered at the top when provided
- Styled with border-bottom separator

### 2. Divisions Management ✅
- Add/Delete divisions functionality
- Each division contains multiple output lines
- Responsive layout:
  - **Landscape**: Divisions displayed side-by-side
  - **Portrait**: Divisions stacked vertically
- CSS media queries handle orientation automatically

### 3. Output Lines ✅
Each output line supports three types:

#### Title
- Static text display
- Configurable font, size, color
- Centered, bold styling

#### Divider
- Visual separator line
- Configurable text (default: "---")
- Configurable font, size, color

#### Data Output
- Extracts data from JSON response using key names
- Supports nested keys (dot notation, e.g., `sensor.temperature`)
- Format string with `{value}` placeholder
- Shows "??" when data not found
- Configurable font, size, color

### 4. Formatting Options ✅
- **Font**: Jost, DS-Digital, Napoli, Dogica
- **Size**: x-small, small, normal, large, x-large
- **Color**: HTML color picker
- Responsive font sizing using CSS container queries

## Settings Structure

The settings form stores data as:
```json
{
  "pageTitle": "Optional title",
  "division_0_type[]": ["dataoutput", "title"],
  "division_0_value[]": ["temperature", "Status"],
  "division_0_format[]": ["{value}°C", ""],
  "division_0_font[]": ["Jost", "Jost"],
  "division_0_size[]": ["normal", "large"],
  "division_0_color[]": ["#000000", "#333333"]
}
```

## Data Processing

1. **JSON Key Extraction**: Supports nested keys using dot notation
   - `temperature` → `data["temperature"]`
   - `sensor.temp` → `data["sensor"]["temp"]`
   - `items[0].name` → `data["items"][0]["name"]`

2. **Format String Replacement**: 
   - Format: `"{value}°C"`
   - Data: `25`
   - Result: `"25°C"`

3. **Missing Data Handling**:
   - If JSON key not found → displays "??"
   - Logs warning for debugging

## Responsive Design

- **Font Sizing**: Uses CSS container queries (`cqh`, `cqi`) with `clamp()` for bounds
- **Layout**: CSS media queries for orientation-based layout
- **Flexible**: Divisions adapt to available space

## Fallback Behavior

- If no divisions configured → displays raw JSON (backward compatible)
- If division has no output lines → division is skipped
- If output line has no data → shows "??"

## Usage Example

### Node-RED Flow
```json
{
  "temperature": 25,
  "humidity": 60,
  "status": "active"
}
```

### Settings Configuration
- **Division 1**:
  - Title: "Sensor Data" (Jost, large, #000000)
  - Data: `temperature` → Format: `"{value}°C"` (Jost, normal, #000000)
  - Data: `humidity` → Format: `"{value}%"` (Jost, normal, #000000)
  - Divider: "---"
  - Data: `status` → Format: `"Status: {value}"` (Jost, small, #666666)

### Output Display
```
Sensor Data
25°C
60%
---
Status: active
```

## Files Modified

1. **`settings.html`**: Complex form with add/delete functionality
2. **`node-red.py`**: Settings parsing, JSON extraction, format string processing
3. **`render/node_red.html`**: Template rendering with conditional logic
4. **`render/node_red.css`**: Responsive layout and styling

## Testing Checklist

- [ ] Add/delete divisions works
- [ ] Add/delete output lines works
- [ ] Type selector updates form correctly
- [ ] Format string replacement works
- [ ] Nested JSON keys work
- [ ] Missing data shows "??"
- [ ] Font/size/color apply correctly
- [ ] Landscape layout (side-by-side)
- [ ] Portrait layout (stacked)
- [ ] Page title displays when set
- [ ] Fallback to JSON when no divisions
