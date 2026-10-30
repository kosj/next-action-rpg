"""Canvas/browser smoke and visual capture. pip install playwright; use system chromium.

Run after serving build/web: python tools/browser_smoke.py http://127.0.0.1:8060
Screenshots are verification artifacts, not golden-file comparisons.
"""
import asyncio
import json
import os
from pathlib import Path
import sys
from playwright.async_api import async_playwright


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8060"
    output = Path("build/verification")
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH", "/usr/bin/chromium"), headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--autoplay-policy=no-user-gesture-required"])
        page = await browser.new_page(viewport={"width":1440,"height":900}, device_scale_factor=1)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        await page.goto(url + ('&' if '?' in url else '?') + 'qa=1', wait_until="networkidle")
        await page.wait_for_function("!document.getElementById('loading')", timeout=120000)
        await page.wait_for_function("window.__RUNEFALL_STATE !== undefined", timeout=30000)
        await page.wait_for_timeout(2500)
        await page.screenshot(path=str(output / "01-title.png"))
        await page.mouse.click(320, 445)
        await page.wait_for_function("window.__RUNEFALL_STATE.started && window.__RUNEFALL_STATE.modal", timeout=15000)
        status = await page.evaluate('window.__RUNEFALL_STATE')
        assert status['modal_x'] >= 0 and status['modal_y'] >= 0, status
        assert status['modal_x'] + status['modal_w'] <= 1440 and status['modal_y'] + status['modal_h'] <= 900, status
        await page.screenshot(path=str(output / "02-prologue.png"))
        await page.keyboard.press('Enter')
        await page.wait_for_function('!window.__RUNEFALL_STATE.paused', timeout=15000)
        assert (await page.evaluate('window.__RUNEFALL_STATE.hud_y')) > 0
        await page.keyboard.press("Escape")
        await page.wait_for_function('window.__RUNEFALL_STATE.paused', timeout=15000)
        await page.screenshot(path=str(output / "03-pause.png"))
        await page.keyboard.press("Enter")
        await page.wait_for_function('!window.__RUNEFALL_STATE.paused', timeout=15000)
        await page.mouse.click(800, 450)
        await page.keyboard.down("w")
        await page.wait_for_function('window.__RUNEFALL_STATE.encounter === 0', timeout=45000)
        await page.keyboard.up("w")
        await page.keyboard.press('Tab')
        for _ in range(10):
            await page.mouse.click(800, 450)
            await page.wait_for_timeout(200)
        await page.keyboard.press('Space')
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(output / "04-gameplay.png"))
        (output / "browser-errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2))
        (output / "browser-state.json").write_text(json.dumps(await page.evaluate('window.__RUNEFALL_STATE'), indent=2))
        await browser.close()
    if errors:
        raise SystemExit("Browser errors: " + json.dumps(errors, ensure_ascii=False))
    print("RUNEFALL_BROWSER_OK · title, input, pause, gameplay captured")


asyncio.run(main())
