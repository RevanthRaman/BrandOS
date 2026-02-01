import asyncio
import nest_asyncio
from playwright.async_api import async_playwright

# Patch asyncio to allow nested event loops (critical for Streamlit)
nest_asyncio.apply()

async def _capture_screenshot_async(url):
    """
    Async implementation of screenshot capture using Playwright.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            # Create a context with viewport suitable for desktop
            context = await browser.new_context(viewport={'width': 1280, 'height': 800})
            page = await context.new_page()
            
            # Navigate with a timeout
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            
            # Wait a bit for animations/lazy load
            await page.wait_for_timeout(2000)
            
            # Capture screenshot
            screenshot_bytes = await page.screenshot(type='jpeg', quality=80)
            
            return screenshot_bytes
            
        except Exception as e:
            print(f"Playwright Error: {e}")
            return None
        finally:
            await browser.close()

def capture_website_screenshot(url):
    """
    Synchronous wrapper for the async screenshot function.
    Returns bytes or None.
    """
    try:
        # Run the async function in the existing loop if compatible, or new loop
        return asyncio.run(_capture_screenshot_async(url))
    except Exception as e:
        print(f"Screenshot Engine Error: {e}")
        return None
