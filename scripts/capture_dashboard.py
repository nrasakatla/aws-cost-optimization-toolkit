"""Capture dashboard screenshots using Playwright + system Chrome.

Waits for Streamlit WebSocket to render, then captures full-page + viewport shots.
"""
from playwright.sync_api import sync_playwright

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
URL = "http://127.0.0.1:8599"
OUT_DIR = "reports"
INIT_WAIT_MS = 9000  # Streamlit needs time for the WS round-trip


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 2200})
        page.goto(URL, wait_until="networkidle", timeout=60000)
        # Wait for a real metric to appear (not the skeleton).
        page.wait_for_selector("text=Cost Optimization Toolkit", timeout=30000)
        page.wait_for_timeout(INIT_WAIT_MS)
        page.screenshot(path=f"{OUT_DIR}/dashboard-full.png", full_page=True)
        page.screenshot(path=f"{OUT_DIR}/dashboard-viewport.png")
        browser.close()
        print("screenshots saved")


if __name__ == "__main__":
    main()
