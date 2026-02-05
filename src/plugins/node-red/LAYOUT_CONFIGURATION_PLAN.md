# Layout Configuration Implementation Plan

## Data Structure

Settings will be stored as:
```json
{
  "pageTitle": "Optional title",
  "divisions": [
    {
      "outputLines": [
        {
          "type": "title|divider|dataoutput",
          "value": "Text for title/divider OR JSON key name for dataoutput",
          "format": "Format string with {value} placeholder (for dataoutput only)",
          "font": "Jost|DS-Digital|Napoli|Dogica",
          "size": "x-small|small|normal|large|x-large",
          "color": "#000000"
        }
      ]
    }
  ]
}
```

## Implementation Steps

### 1. Settings HTML (`settings.html`)
- Add page title input field
- Add divisions container with add/delete buttons
- For each division:
  - Add output lines container with add/delete buttons
  - For each output line:
    - Type selector (Title/Divider/Data Output)
    - Value input (text for title/divider, JSON key for dataoutput)
    - Format string input (only for dataoutput, with {value} placeholder)
    - Font selector
    - Size selector
    - Color picker
- JavaScript to handle add/delete and form state
- Prepopulation logic for edit mode

### 2. Python Backend (`node_red.py`)
- Parse settings structure
- Extract data from JSON response using key names
- Replace placeholders in format strings
- Handle missing data (show "??")
- Pass structured data to template

### 3. HTML Template (`render/node_red.html`)
- Display page title if provided (centered top)
- Render divisions container
- For each division, render output lines
- Apply font, size, color to each element

### 4. CSS (`render/node_red.css`)
- Layout: divisions side-by-side in landscape, stacked in portrait
- Responsive font sizing based on size selection
- Color application
- Proper spacing and alignment

## Key Features

- **Divisions Layout**: CSS media query or container query for landscape/portrait
- **Data Extraction**: Support nested JSON keys (e.g., "sensor.temperature")
- **Format Strings**: Replace {value} placeholder with actual data
- **Missing Data**: Show "??" when JSON key not found
- **Font Support**: Jost, DS-Digital, Napoli, Dogica
- **Size Options**: x-small, small, normal, large, x-large
- **Color Picker**: Standard HTML color input
