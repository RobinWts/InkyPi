import requests
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
from io import BytesIO
import os
import logging
import hashlib
import tempfile
import subprocess
import shutil

logger = logging.getLogger(__name__)

# Check if Playwright is available
_playwright_available = None
_playwright_browser = None

def _check_playwright_available():
    """Check if Playwright is installed and available."""
    global _playwright_available
    if _playwright_available is None:
        try:
            from playwright.sync_api import sync_playwright
            _playwright_available = True
            logger.info("Playwright is available and will be used for rendering")
        except ImportError:
            _playwright_available = False
            logger.info("Playwright not available, falling back to Chromium subprocess")
    return _playwright_available

def _get_playwright_browser():
    """Get or create a Playwright browser instance (singleton pattern)."""
    global _playwright_browser
    if _playwright_browser is None:
        try:
            from playwright.sync_api import sync_playwright
            playwright = sync_playwright().start()
            # Use chromium for consistency with existing behavior
            _playwright_browser = {
                'playwright': playwright,
                'browser': playwright.chromium.launch(headless=True)
            }
            logger.debug("Playwright browser instance created")
        except Exception as e:
            logger.error(f"Failed to create Playwright browser: {str(e)}")
            return None
    return _playwright_browser

def _cleanup_playwright():
    """Cleanup Playwright resources."""
    global _playwright_browser
    if _playwright_browser:
        try:
            _playwright_browser['browser'].close()
            _playwright_browser['playwright'].stop()
            _playwright_browser = None
            logger.debug("Playwright browser cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up Playwright: {str(e)}")

def get_image(image_url):
    response = requests.get(image_url, timeout=30)
    img = None
    if 200 <= response.status_code < 300 or response.status_code == 304:
        img = Image.open(BytesIO(response.content))
    else:
        logger.error(f"Received non-200 response from {image_url}: status_code: {response.status_code}")
    return img

def change_orientation(image, orientation, inverted=False):
    if orientation == 'horizontal':
        angle = 0
    elif orientation == 'vertical':
        angle = 90

    if inverted:
        angle = (angle + 180) % 360

    return image.rotate(angle, expand=1)

def resize_image(image, desired_size, image_settings=[]):
    img_width, img_height = image.size
    desired_width, desired_height = desired_size
    desired_width, desired_height = int(desired_width), int(desired_height)

    img_ratio = img_width / img_height
    desired_ratio = desired_width / desired_height

    keep_width = "keep-width" in image_settings

    x_offset, y_offset = 0,0
    new_width, new_height = img_width,img_height
    # Step 1: Determine crop dimensions
    desired_ratio = desired_width / desired_height
    if img_ratio > desired_ratio:
        # Image is wider than desired aspect ratio
        new_width = int(img_height * desired_ratio)
        if not keep_width:
            x_offset = (img_width - new_width) // 2
    else:
        # Image is taller than desired aspect ratio
        new_height = int(img_width / desired_ratio)
        if not keep_width:
            y_offset = (img_height - new_height) // 2

    # Step 2: Crop the image
    image = image.crop((x_offset, y_offset, x_offset + new_width, y_offset + new_height))

    # Step 3: Resize to the exact desired dimensions (if necessary)
    return image.resize((desired_width, desired_height), Image.LANCZOS)

def apply_image_enhancement(img, image_settings={}):
    # Convert image to RGB mode if necessary for enhancement operations
    # ImageEnhance requires RGB mode for operations like blend
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
        

    # Apply Brightness
    img = ImageEnhance.Brightness(img).enhance(image_settings.get("brightness", 1.0))

    # Apply Contrast
    img = ImageEnhance.Contrast(img).enhance(image_settings.get("contrast", 1.0))

    # Apply Saturation (Color)
    img = ImageEnhance.Color(img).enhance(image_settings.get("saturation", 1.0))

    # Apply Sharpness
    img = ImageEnhance.Sharpness(img).enhance(image_settings.get("sharpness", 1.0))

    return img

def compute_image_hash(image):
    """Compute SHA-256 hash of an image."""
    image = image.convert("RGB")
    img_bytes = image.tobytes()
    return hashlib.sha256(img_bytes).hexdigest()

def _take_screenshot_html_playwright(html_str, dimensions, timeout_ms=None):
    """Take screenshot using Playwright.
    Writes HTML to a temp file and loads it via file:// so that linked CSS and
    font URLs (absolute file paths) resolve correctly; set_content(html) would
    use about:blank and break resource loading.
    """
    image = None
    html_file_path = None
    try:
        browser_instance = _get_playwright_browser()
        if not browser_instance:
            return None

        # Write HTML to temp file so we can load it via file:// and allow
        # stylesheets/fonts (absolute file paths) to load
        with tempfile.NamedTemporaryFile(
            suffix=".html", delete=False, mode="w", encoding="utf-8"
        ) as html_file:
            html_file.write(html_str)
            html_file_path = html_file.name

        file_url = f"file://{os.path.abspath(html_file_path)}"

        browser = browser_instance["browser"]
        context = browser.new_context(
            viewport={"width": dimensions[0], "height": dimensions[1]},
            device_scale_factor=1,
        )
        page = context.new_page()

        if timeout_ms:
            page.set_default_timeout(timeout_ms)

        page.goto(file_url, wait_until="networkidle")

        screenshot_bytes = page.screenshot(type="png")
        image = Image.open(BytesIO(screenshot_bytes))

        context.close()

    except Exception as e:
        logger.error(f"Failed to take screenshot with Playwright: {str(e)}")
    finally:
        if html_file_path and os.path.exists(html_file_path):
            try:
                os.remove(html_file_path)
            except OSError as e:
                logger.debug(f"Could not remove temp HTML file: {e}")

    return image

def _take_screenshot_playwright(target, dimensions, timeout_ms=None):
    """Take screenshot of a file or URL using Playwright."""
    image = None
    try:
        browser_instance = _get_playwright_browser()
        if not browser_instance:
            return None
        
        browser = browser_instance['browser']
        context = browser.new_context(
            viewport={'width': dimensions[0], 'height': dimensions[1]},
            device_scale_factor=1
        )
        page = context.new_page()
        
        # Set timeout if provided
        if timeout_ms:
            page.set_default_timeout(timeout_ms)
        
        # Navigate to file:// URL or regular URL
        if os.path.isfile(target):
            target = f"file://{os.path.abspath(target)}"
        
        page.goto(target, wait_until='networkidle')
        
        # Take screenshot
        screenshot_bytes = page.screenshot(type='png')
        image = Image.open(BytesIO(screenshot_bytes))
        
        # Cleanup
        context.close()
        
    except Exception as e:
        logger.error(f"Failed to take screenshot with Playwright: {str(e)}")
    
    return image

def take_screenshot_html(html_str, dimensions, timeout_ms=None):
    image = None
    try:
        # Try Playwright first if available
        if _check_playwright_available():
            image = _take_screenshot_html_playwright(html_str, dimensions, timeout_ms)
            if image:
                return image
            logger.warning("Playwright screenshot failed, falling back to Chromium subprocess")
        
        # Fallback to Chromium subprocess method
        # Create a temporary HTML file
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as html_file:
            html_file.write(html_str.encode("utf-8"))
            html_file_path = html_file.name

        image = take_screenshot(html_file_path, dimensions, timeout_ms)

        # Remove html file
        os.remove(html_file_path)

    except Exception as e:
        logger.error(f"Failed to take screenshot: {str(e)}")

    return image

def _find_chromium_binary():
    """Find the first available Chromium-based binary in PATH or common install locations."""
    # 1. Check PATH (works when binary name is on PATH)
    path_candidates = ["chromium-headless-shell", "chromium", "chrome", "google-chrome"]
    for candidate in path_candidates:
        path = shutil.which(candidate)
        if path:
            logger.debug(f"Found browser binary: {candidate} at {path}")
            return path

    # 2. On macOS, check .app bundles (Chrome is not typically on PATH)
    if os.name == "posix" and os.uname().sysname == "Darwin":
        app_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
        for app_path in app_paths:
            if os.path.isfile(app_path) and os.access(app_path, os.X_OK):
                logger.debug(f"Found browser at {app_path}")
                return app_path

    return None


def take_screenshot(target, dimensions, timeout_ms=None):
    image = None
    try:
        # Try Playwright first if available
        if _check_playwright_available():
            image = _take_screenshot_playwright(target, dimensions, timeout_ms)
            if image:
                return image
            logger.warning("Playwright screenshot failed, falling back to Chromium subprocess")
        
        # Fallback to Chromium subprocess method
        # Find available browser binary
        browser = _find_chromium_binary()
        if not browser:
            logger.error("No Chromium-based browser found. Install chromium, chromium-headless-shell, or chrome.")
            return None

        # Create a temporary output file for the screenshot
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as img_file:
            img_file_path = img_file.name

        command = [
            browser,
            target,
            "--headless",
            f"--screenshot={img_file_path}",
            f"--window-size={dimensions[0]},{dimensions[1]}",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--use-gl=swiftshader",
            "--hide-scrollbars",
            "--in-process-gpu",
            "--js-flags=--jitless",
            "--disable-zero-copy",
            "--disable-gpu-memory-buffer-compositor-resources",
            "--disable-extensions",
            "--disable-plugins",
            "--mute-audio",
            "--renderer-process-limit=1",
            "--no-zygote",
            "--no-sandbox",
            # Crisp text for e-ink: disable LCD/subpixel and subpixel positioning so
            # B&W palette conversion stays sharp (Chromium content + gfx switches).
            "--disable-lcd-text",
            "--disable-font-subpixel-positioning",
        ]
        if timeout_ms:
            command.append(f"--timeout={timeout_ms}")
        result = subprocess.run(command, capture_output=True, check=False)

        # Check if the process failed or the output file is missing
        if result.returncode != 0 or not os.path.exists(img_file_path):
            logger.error(f"Failed to take screenshot (return code: {result.returncode})")
            return None

        # Load the image using PIL
        with Image.open(img_file_path) as img:
            image = img.copy()

        # Remove image files
        os.remove(img_file_path)

    except Exception as e:
        logger.error(f"Failed to take screenshot: {str(e)}")

    return image

def pad_image_blur(img: Image, dimensions: tuple[int, int]) -> Image:
    bkg = ImageOps.fit(img, dimensions)
    bkg = bkg.filter(ImageFilter.BoxBlur(8))
    img = ImageOps.contain(img, dimensions)

    img_size = img.size
    bkg.paste(img, ((dimensions[0] - img_size[0]) // 2, (dimensions[1] - img_size[1]) // 2))
    return bkg
