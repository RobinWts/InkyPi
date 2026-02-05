#!/usr/bin/env python3
"""
Simple script to create a placeholder icon for the Node-RED plugin.
Run this script to generate icon.png (requires Pillow).
"""

from PIL import Image, ImageDraw, ImageFont

# Create a simple placeholder icon (64x64 pixels, matching typical plugin icon size)
size = (64, 64)
img = Image.new('RGB', size, color='#8E0000')  # Node-RED red color
draw = ImageDraw.Draw(img)

# Draw a simple "NR" text or Node-RED logo placeholder
# For now, just draw a simple rectangle border
border_width = 4
draw.rectangle(
    [border_width, border_width, size[0] - border_width, size[1] - border_width],
    outline='white',
    width=border_width
)

# Try to add text if font is available
try:
    # Try to use a default font
    font = ImageFont.load_default()
    text = "NR"
    # Calculate text position (centered)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)
    draw.text(position, text, fill='white', font=font)
except Exception:
    # If font fails, just draw a circle
    center = (size[0] // 2, size[1] // 2)
    radius = size[0] // 4
    draw.ellipse(
        [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius],
        outline='white',
        width=2
    )

img.save('icon.png')
print("Created icon.png")
