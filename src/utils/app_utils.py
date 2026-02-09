import logging
import os
import socket
import subprocess
import json

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

logger = logging.getLogger(__name__)

# Hardcoded font families (base fonts, can be overridden by discovered fonts)
FONT_FAMILIES = {
    "Dogica": [{
        "font-weight": "normal",
        "file": "dogicapixel.ttf"
    },{
        "font-weight": "bold",
        "file": "dogicapixelbold.ttf"
    }],
    "Jost": [{
        "font-weight": "normal",
        "file": "Jost.ttf"
    },{
        "font-weight": "bold",
        "file": "Jost-SemiBold.ttf"
    }],
    "Napoli": [{
        "font-weight": "normal",
        "file": "Napoli.ttf"
    }],
    "DS-Digital": [{
        "font-weight": "normal",
        "file": os.path.join("DS-DIGI", "DS-DIGI.TTF")
    }]
}

# Cache for discovered fonts (lazy-loaded)
_DISCOVERED_FONTS = None
_FONTS_DIR = None

FONTS = {
    "ds-gigi": "DS-DIGI.TTF",
    "napoli": "Napoli.ttf",
    "jost": "Jost.ttf",
    "jost-semibold": "Jost-SemiBold.ttf"
}

def resolve_path(file_path):
    src_dir = os.getenv("SRC_DIR")
    if src_dir is None:
        # Default to the src directory
        src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    src_path = Path(src_dir)
    return str(src_path / file_path)

def _get_fonts_directory():
    """Get the fonts directory path."""
    global _FONTS_DIR
    if _FONTS_DIR is None:
        _FONTS_DIR = resolve_path(os.path.join("static", "fonts"))
    return _FONTS_DIR

def _extract_font_metadata(font_path):
    """
    Extract font metadata (family name, weight, style) from a font file.
    
    Uses fonttools if available (best practice), falls back to naming conventions.
    
    Args:
        font_path: Path to the font file (.ttf or .otf)
        
    Returns:
        dict with keys: 'family', 'weight', 'style', or None if extraction fails
    """
    # Try using fonttools (best practice for font metadata extraction)
    try:
        from fontTools.ttLib import TTFont
        
        font = TTFont(font_path)
        name_table = font.get('name')
        
        # Get font family name (nameID 1 = Font Family, nameID 16 = Typographic Family)
        family_name = name_table.getBestFamilyName() or name_table.getBestSubFamilyName()
        
        # Get subfamily/weight info (nameID 2 = Font Subfamily, nameID 17 = Typographic Subfamily)
        subfamily = name_table.getBestSubFamilyName() or ""
        subfamily_lower = subfamily.lower()
        
        # Determine weight from subfamily name (common patterns)
        weight = "normal"
        if any(term in subfamily_lower for term in ["bold", "black", "heavy", "700", "800", "900"]):
            weight = "bold"
        elif any(term in subfamily_lower for term in ["light", "thin", "100", "200", "300"]):
            weight = "normal"  # Keep as normal for CSS compatibility
        
        # Determine style
        style = "normal"
        if "italic" in subfamily_lower or "oblique" in subfamily_lower:
            style = "italic"
        
        # Also check OS/2 table for weight value if available
        if 'OS/2' in font:
            os2 = font['OS/2']
            us_weight = os2.usWeightClass
            if us_weight >= 700:
                weight = "bold"
            elif us_weight <= 300:
                weight = "normal"
        
        font.close()
        
        return {
            "family": family_name,
            "weight": weight,
            "style": style
        }
    except ImportError:
        # fonttools not available, use naming convention fallback
        logger.debug("fonttools not available, using naming convention fallback")
        return _extract_font_metadata_from_filename(font_path)
    except Exception as e:
        logger.warning(f"Failed to extract metadata from {font_path} using fonttools: {e}")
        return _extract_font_metadata_from_filename(font_path)

def _extract_font_metadata_from_filename(font_path):
    """
    Fallback: Extract font metadata from filename using naming conventions.
    
    Common patterns:
    - FontName-Regular.ttf -> family="FontName", weight="normal"
    - FontName-Bold.ttf -> family="FontName", weight="bold"
    - FontName-Italic.ttf -> family="FontName", style="italic"
    - FontName-BoldItalic.ttf -> family="FontName", weight="bold", style="italic"
    
    Args:
        font_path: Path to the font file
        
    Returns:
        dict with keys: 'family', 'weight', 'style', or None if extraction fails
    """
    filename = os.path.basename(font_path)
    name_without_ext = os.path.splitext(filename)[0]
    
    # Common weight/style suffixes
    weight = "normal"
    style = "normal"
    
    name_lower = name_without_ext.lower()
    
    # Check for weight indicators
    if any(term in name_lower for term in ["bold", "black", "heavy", "semibold", "semi-bold"]):
        weight = "bold"
    elif any(term in name_lower for term in ["light", "thin", "extralight"]):
        weight = "normal"  # Keep as normal for CSS compatibility
    
    # Check for style indicators
    if "italic" in name_lower or "oblique" in name_lower:
        style = "italic"
    
    # Extract family name by removing common suffixes
    family = name_without_ext
    for suffix in ["-Bold", "-Regular", "-Italic", "-Light", "-Black", "-Heavy", 
                   "-SemiBold", "-Semi-Bold", "-BoldItalic", "-Bold-Italic"]:
        if family.endswith(suffix):
            family = family[:-len(suffix)]
            break
    
    return {
        "family": family,
        "weight": weight,
        "style": style
    }

def _load_metadata_override(font_path):
    """
    Load metadata override from a JSON file if it exists.
    
    For a font file like "MyFont-Bold.ttf", checks for "MyFont-Bold.json"
    in the same directory. This allows manual overrides for edge cases.
    
    Args:
        font_path: Path to the font file
        
    Returns:
        dict with override metadata, or None if no override file exists
    """
    metadata_path = os.path.splitext(font_path)[0] + ".json"
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                # Validate required fields
                if "family" in metadata:
                    return metadata
        except Exception as e:
            logger.warning(f"Failed to load metadata override from {metadata_path}: {e}")
    return None

def _discover_fonts():
    """
    Discover fonts dynamically from the fonts directory.
    
    Scans the fonts directory recursively for .ttf and .otf files,
    extracts metadata from each font file, and merges with hardcoded
    FONT_FAMILIES (hardcoded takes precedence for overrides).
    
    Returns:
        dict: Font families dictionary in the same format as FONT_FAMILIES
    """
    global _DISCOVERED_FONTS
    
    if _DISCOVERED_FONTS is not None:
        logger.debug(f"Using cached font discovery results ({len(_DISCOVERED_FONTS)} families)")
        return _DISCOVERED_FONTS
    
    fonts_dir = _get_fonts_directory()
    logger.debug(f"Scanning fonts directory: {fonts_dir}")
    discovered = {}
    
    if not os.path.exists(fonts_dir):
        logger.warning(f"Fonts directory not found: {fonts_dir}")
        _DISCOVERED_FONTS = {}
        return {}
    
    # Scan for font files recursively
    font_extensions = {'.ttf', '.otf', '.TTF', '.OTF'}
    fonts_base_path = Path(fonts_dir)
    
    font_files_found = 0
    for font_file in fonts_base_path.rglob('*'):
        if font_file.suffix in font_extensions:
            font_files_found += 1
            try:
                font_path = str(font_file)
                relative_path = os.path.relpath(font_path, fonts_dir)
                
                # Check for metadata override first
                metadata_override = _load_metadata_override(font_path)
                
                if metadata_override:
                    metadata = metadata_override
                    # Ensure file path is set correctly
                    metadata['file'] = relative_path.replace('\\', '/')  # Normalize path separators
                else:
                    # Extract metadata from font file
                    metadata = _extract_font_metadata(font_path)
                    if not metadata:
                        logger.warning(f"Could not extract metadata from {font_path}, skipping")
                        continue
                    metadata['file'] = relative_path.replace('\\', '/')
                
                family = metadata['family']
                weight = metadata.get('weight', 'normal')
                style = metadata.get('style', 'normal')
                
                # Initialize family if not exists
                if family not in discovered:
                    discovered[family] = []
                
                # Add variant
                variant = {
                    "font-weight": weight,
                    "font-style": style,
                    "file": metadata['file']
                }
                
                # Avoid duplicates (same weight/style combination)
                if not any(v.get("font-weight") == weight and v.get("font-style") == style 
                          for v in discovered[family]):
                    discovered[family].append(variant)
                    
            except Exception as e:
                logger.warning(f"Error processing font file {font_file}: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                continue
    
    logger.debug(f"Found {font_files_found} font file(s) in {fonts_dir}")
    
    # Sort variants within each family for consistency
    for family in discovered:
        discovered[family].sort(key=lambda v: (v.get("font-weight", "normal"), v.get("font-style", "normal")))
    
    _DISCOVERED_FONTS = discovered
    logger.info(f"Font discovery complete: {len(discovered)} font families discovered from {font_files_found} font file(s)")
    
    return discovered

def _get_all_font_families():
    """
    Get merged font families (hardcoded + discovered).
    
    Hardcoded FONT_FAMILIES take precedence for overrides.
    Discovered fonts are merged in, adding new families or variants.
    
    Returns:
        dict: Merged font families dictionary
    """
    discovered = _discover_fonts()
    
    # Start with hardcoded fonts (base/overrides)
    merged = FONT_FAMILIES.copy()
    
    # Merge discovered fonts (discovered takes precedence for new families,
    # but hardcoded takes precedence for existing families)
    new_families = 0
    new_variants = 0
    for family, variants in discovered.items():
        if family not in merged:
            # New family, add all variants
            merged[family] = variants.copy()
            new_families += 1
            logger.debug(f"Added new font family: {family} with {len(variants)} variant(s)")
        else:
            # Existing family: merge variants, avoiding duplicates
            existing_weights_styles = {
                (v.get("font-weight", "normal"), v.get("font-style", "normal"))
                for v in merged[family]
            }
            for variant in variants:
                key = (variant.get("font-weight", "normal"), variant.get("font-style", "normal"))
                if key not in existing_weights_styles:
                    merged[family].append(variant)
                    new_variants += 1
                    logger.debug(f"Added new variant to {family}: weight={variant.get('font-weight')}, style={variant.get('font-style')}")
    
    if new_families > 0 or new_variants > 0:
        logger.debug(f"Merged fonts: {new_families} new families, {new_variants} new variants added")
    
    return merged

def get_ip_address():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
    return ip_address

def get_wifi_name():
    try:
        output = subprocess.check_output(['iwgetid', '-r']).decode('utf-8').strip()
        return output
    except subprocess.CalledProcessError:
        return None

def is_connected():
    """Check if the Raspberry Pi has an internet connection."""
    try:
        # Try to connect to Google's public DNS server
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except OSError:
        return False

def get_font(font_name, font_size=50, font_weight="normal"):
    """
    Get a PIL ImageFont object for the specified font.
    
    Uses merged font families (hardcoded + discovered) to find the font.
    Maintains backward compatibility with existing plugin code.
    
    Args:
        font_name: Name of the font family
        font_size: Size of the font in points
        font_weight: Weight of the font ("normal" or "bold")
        
    Returns:
        ImageFont object or None if font not found
    """
    font_families = _get_all_font_families()
    
    if font_name in font_families:
        font_variants = font_families[font_name]

        font_entry = next((entry for entry in font_variants if entry["font-weight"] == font_weight), None)
        if font_entry is None:
            font_entry = font_variants[0]  # Default to first available variant

        if font_entry:
            font_path = resolve_path(os.path.join("static", "fonts", font_entry["file"]))
            try:
                return ImageFont.truetype(font_path, font_size)
            except Exception as e:
                logger.error(f"Failed to load font file {font_path}: {e}")
                return None
        else:
            logger.warning(f"Requested font weight not found: font_name={font_name}, font_weight={font_weight}")
    else:
        logger.warning(f"Requested font not found: font_name={font_name}")

    return None

def get_fonts():
    """
    Get list of all available fonts for HTML/CSS rendering.
    
    Returns merged font families (hardcoded + discovered) in the format
    expected by the HTML template system. Maintains backward compatibility.
    
    Returns:
        list: List of font dictionaries with font_family, url, font_weight, font_style
    """
    try:
        font_families = _get_all_font_families()
        fonts_list = []
        
        for font_family, variants in font_families.items():
            for variant in variants:
                fonts_list.append({
                    "font_family": font_family,
                    "url": resolve_path(os.path.join("static", "fonts", variant["file"])),
                    "font_weight": variant.get("font-weight", "normal"),
                    "font_style": variant.get("font-style", "normal"),
                })
        
        logger.debug(f"get_fonts() returning {len(fonts_list)} font entries from {len(font_families)} families")
        return fonts_list
    except Exception as e:
        logger.error(f"Error in get_fonts(): {e}", exc_info=True)
        raise

def get_font_path(font_name):
    """
    Get the file path for a font by its legacy name.
    
    Note: This function uses the legacy FONTS dict. For new code,
    prefer using get_font() which supports dynamic font discovery.
    
    Args:
        font_name: Legacy font identifier from FONTS dict
        
    Returns:
        str: Absolute path to the font file
    """
    if font_name in FONTS:
        return resolve_path(os.path.join("static", "fonts", FONTS[font_name]))
    else:
        logger.warning(f"Legacy font name not found: {font_name}")
        return None

def reload_fonts():
    """
    Reload discovered fonts from the filesystem.
    
    Clears the font cache and forces a fresh discovery scan.
    Useful when fonts are added/removed at runtime.
    """
    global _DISCOVERED_FONTS
    _DISCOVERED_FONTS = None
    _discover_fonts()

def generate_startup_image(dimensions=(800,480)):
    bg_color = (255,255,255)
    text_color = (0,0,0)
    width, height = dimensions

    hostname = socket.gethostname()
    ip = get_ip_address()

    image = Image.new("RGBA", dimensions, bg_color)
    image_draw = ImageDraw.Draw(image)

    title_font_size = width * 0.145
    image_draw.text((width/2, height/2), "inkypi", anchor="mm", fill=text_color, font=get_font("Jost", title_font_size))

    text = f"To get started, visit http://{hostname}.local"
    text_font_size = width * 0.032

    # Draw the instructions
    y_text = height * 3 / 4
    image_draw.text((width/2, y_text), text, anchor="mm", fill=text_color, font=get_font("Jost", text_font_size))

    # Draw the IP on a line below
    ip_text = f"or http://{ip}"
    ip_text_font_size = width * 0.032
    bbox = image_draw.textbbox((0, 0), text, font=get_font("Jost", text_font_size))
    text_height = bbox[3] - bbox[1]
    ip_y = y_text + text_height * 1.35
    image_draw.text((width/2, ip_y), ip_text, anchor="mm", fill=text_color, font=get_font("Jost", ip_text_font_size))

    return image

def parse_form(request_form):
    request_dict = request_form.to_dict()
    for key in request_form.keys():
        if key.endswith('[]'):
            request_dict[key] = request_form.getlist(key)
    return request_dict

def handle_request_files(request_files, form_data={}):
    allowed_file_extensions = {'pdf', 'png', 'avif', 'jpg', 'jpeg', 'gif', 'webp', 'heif', 'heic'}
    file_location_map = {}
    # handle existing file locations being provided as part of the form data
    for key in set(request_files.keys()):
        is_list = key.endswith('[]')
        if key in form_data:
            file_location_map[key] = form_data.getlist(key) if is_list else form_data.get(key)
    # add new files in the request
    for key, file in request_files.items(multi=True):
        is_list = key.endswith('[]')
        file_name = file.filename
        if not file_name:
            continue

        extension = os.path.splitext(file_name)[1].replace('.', '')
        if not extension or extension.lower() not in allowed_file_extensions:
            continue

        file_name = os.path.basename(file_name)

        file_save_dir = resolve_path(os.path.join("static", "images", "saved"))
        file_path = os.path.join(file_save_dir, file_name)

        # Open the image and apply EXIF transformation before saving
        if extension in {'jpg', 'jpeg'}:
            try:
                with Image.open(file) as img:
                    img = ImageOps.exif_transpose(img)
                    img.save(file_path)
            except Exception as e:
                logger.warning(f"EXIF processing error for {file_name}: {e}")
                file.save(file_path)
        else:
            # Directly save non-JPEG files
            file.save(file_path)

        if is_list:
            file_location_map.setdefault(key, [])
            file_location_map[key].append(file_path)
        else:
            file_location_map[key] = file_path
    return file_location_map
