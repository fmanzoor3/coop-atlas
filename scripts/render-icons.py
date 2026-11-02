"""Render the checked-in SVG to opaque PNGs. Requires Playwright and Chromium."""
from pathlib import Path
import io
from PIL import Image
from playwright.sync_api import sync_playwright
root = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    page = browser.new_page(device_scale_factor=1)
    svg = (root / 'icon.svg').read_text()
    for size, filename in [(180, 'apple-touch-icon.png'), (180, 'apple-touch-icon-v4.png'), (192, 'icon-192.png'), (512, 'icon-512.png')]:
        page.set_viewport_size({'width': size, 'height': size})
        page.set_content('<style>html,body{margin:0;background:#201044}svg{display:block;width:100vw;height:100vh}</style>' + svg)
        Image.open(io.BytesIO(page.screenshot())).convert('RGB').save(root / filename, optimize=True)
    browser.close()
