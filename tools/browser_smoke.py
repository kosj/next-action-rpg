"""Exercise real WebGL, input, modal layout and IndexedDB across browser restarts.

python tools/browser_smoke.py http://127.0.0.1:8060
Use CHROMIUM_PATH for a system browser, or install Playwright's Chromium.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import tempfile
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.async_api import async_playwright


async def run(url, output=Path("build/verification")):
    output.mkdir(parents=True, exist_ok=True)
    for name in ("01-title.png", "02-prologue.png", "03-pause.png", "04-gameplay.png",
                 "05-continue.png", "failure.png", "failure-state.json", "browser-state.json",
                 "browser-errors.json", "browser-persistence.json"):
        (output / name).unlink(missing_ok=True)
    errors = []
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query["qa"] = "1"
    test_url = urlunsplit(parts._replace(query=urlencode(query)))
    executable = os.environ.get("CHROMIUM_PATH") or shutil.which("chromium")
    launch_options = dict(
        headless=True, viewport={"width": 960, "height": 600}, device_scale_factor=1,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--use-angle=swiftshader",
              "--enable-unsafe-swiftshader", "--autoplay-policy=no-user-gesture-required"],
    )
    if executable:
        launch_options["executable_path"] = executable

    def attach_errors(page):
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)

    async def ready(page):
        attach_errors(page)
        await page.goto(test_url, wait_until="networkidle")
        await page.wait_for_function("!document.getElementById('loading')", timeout=120000)
        await page.wait_for_function("window.__RUNEFALL_STATE !== undefined", timeout=30000)

    async def state(page):
        return await page.evaluate("window.__RUNEFALL_STATE")

    async def click_button(page, prefix):
        status = await state(page)
        button = next((item for item in status["buttons"] if item["text"].startswith(prefix)), None)
        assert button is not None, (prefix, status)
        canvas = await page.locator("canvas").bounding_box()
        assert canvas is not None
        x = canvas["x"] + (button["x"] + button["w"] / 2) / status["ui_width"] * canvas["width"]
        y = canvas["y"] + (button["y"] + button["h"] / 2) / status["ui_height"] * canvas["height"]
        await page.mouse.click(x, y)

    async with async_playwright() as playwright:
        # A persistent profile is required to test IndexedDB after the browser closes.
        # Its temporary directory isolates this run from the developer's saves.
        with tempfile.TemporaryDirectory(prefix="runefall-browser-") as profile:
            context = await playwright.chromium.launch_persistent_context(profile, **launch_options)
            page = context.pages[0]
            tour_completed = False
            try:
                await ready(page)
                assert not (await state(page))["has_save"], "Fresh profile unexpectedly contains a save"
                await page.screenshot(path=str(output / "01-title.png"))
                await click_button(page, "새로운 서약")
                await page.wait_for_function("window.__RUNEFALL_STATE.started && window.__RUNEFALL_STATE.modal", timeout=15000)
                status = await state(page)
                assert status["modal_x"] >= 0 and status["modal_y"] >= 0, status
                assert status["modal_x"] + status["modal_w"] <= status["ui_width"] and status["modal_y"] + status["modal_h"] <= status["ui_height"], status
                await page.screenshot(path=str(output / "02-prologue.png"))
                await page.keyboard.press("Enter")
                await page.wait_for_function("!window.__RUNEFALL_STATE.paused", timeout=15000)
                assert (await state(page))["hud_y"] > 0
                await page.keyboard.press("Escape")
                await page.wait_for_function("window.__RUNEFALL_STATE.paused", timeout=15000)
                await page.screenshot(path=str(output / "03-pause.png"))
                await click_button(page, "환경 설정")
                await page.wait_for_function("window.__RUNEFALL_STATE.buttons.some(b => b.kind === 'OptionButton')", timeout=15000)
                await click_button(page, "균형")
                await page.wait_for_function("window.__RUNEFALL_STATE.buttons.some(b => b.popup_visible)", timeout=30000)
                await page.keyboard.press("ArrowDown")
                await page.wait_for_function("window.__RUNEFALL_STATE.buttons.some(b => b.popup_visible && b.popup_focus === 1)", timeout=30000)
                await page.keyboard.press("Enter")
                await page.wait_for_function("window.__RUNEFALL_STATE.quality === 1", timeout=15000)
                await click_button(page, "완료")
                await page.wait_for_function("!window.__RUNEFALL_STATE.paused", timeout=15000)
                await page.keyboard.down("w")
                await page.wait_for_function("window.__RUNEFALL_STATE.encounter === 0", timeout=90000)
                await page.keyboard.up("w")
                await page.keyboard.press("Tab")
                for _ in range(10):
                    # Moving to an absolute coordinate under pointer lock rotates the
                    # camera. Click in place so the tour keeps its initial direction.
                    await page.mouse.down()
                    await page.mouse.up()
                    await page.wait_for_timeout(200)
                await page.keyboard.press("Space")
                await page.wait_for_timeout(1500)
                await page.screenshot(path=str(output / "04-gameplay.png"))
                status = await state(page)
                assert not status["dead"] and status["health"] > 0, status
                (output / "browser-state.json").write_text(json.dumps(status, indent=2))
                tour_completed = True
            finally:
                if errors or not tour_completed:
                    await page.screenshot(path=str(output / "failure.png"))
                    (output / "failure-state.json").write_text(json.dumps(await state(page), indent=2))
                (output / "browser-errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2))
                await context.close()

            context = await playwright.chromium.launch_persistent_context(profile, **launch_options)
            page = context.pages[0]
            try:
                await ready(page)
                assert (await state(page))["has_save"], "IndexedDB save did not survive a browser restart"
                await click_button(page, "여정 이어가기")
                await page.wait_for_function("window.__RUNEFALL_STATE.started && !window.__RUNEFALL_STATE.modal", timeout=15000)
                status = await state(page)
                assert status["checkpoint"] == 0 and abs(status["z"] - 6.0) < 1.0, status
                assert status["quality"] == 1, "Saved graphics settings did not survive the restart"
                await page.screenshot(path=str(output / "05-continue.png"))
                (output / "browser-persistence.json").write_text(json.dumps(status, indent=2))
            finally:
                (output / "browser-errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2))
                await context.close()
    if errors:
        raise RuntimeError("Browser errors: " + json.dumps(errors, ensure_ascii=False))
    print("RUNEFALL_BROWSER_OK · WebGL, modal, input, combat entry, browser restart persistence")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default="http://127.0.0.1:8060")
    args = parser.parse_args()
    asyncio.run(run(args.url))
