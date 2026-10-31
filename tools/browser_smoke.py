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
                 "browser-errors.json", "browser-persistence.json", "browser-quality.json", "06-balanced-gameplay.png",
                 "browser-storage.json"):
        (output / name).unlink(missing_ok=True)
    errors = []
    stage = "initial_load"
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
        page.on("pageerror", lambda error: errors.append(f"{stage}: {error}"))
        page.on("console", lambda message: errors.append(f"{stage}: {message.text}") if message.type == "error" else None)

    async def ready(page):
        attach_errors(page)
        await page.bring_to_front()
        await page.goto(test_url, wait_until="networkidle")
        await page.wait_for_function("!document.getElementById('loading')", timeout=120000)
        await page.wait_for_function("window.__RUNEFALL_STATE !== undefined", timeout=30000)
        expected_commit = os.environ.get("RUNEFALL_EXPECTED_COMMIT")
        if expected_commit:
            build_id = await page.evaluate("window.__RUNEFALL_STATE.build_id")
            assert isinstance(build_id, str) and build_id.rsplit(" · ", 1)[-1] == expected_commit[:8], ("Published build differs from expected commit", build_id, expected_commit[:8])
        await page.bring_to_front()

    async def state(page):
        return await page.evaluate("window.__RUNEFALL_STATE")

    # Observe the browser's durable copy, without writing to IDBFS or invoking
    # the engine's sync functions. This profile belongs only to this test.
    read_persisted_saves = """async () => {
            const saves = [];
            for (const info of await indexedDB.databases()) {
                if (!info.name || !info.name.startsWith('/userfs')) continue;
                const db = await new Promise((resolve, reject) => {
                    const request = indexedDB.open(info.name);
                    request.onupgradeneeded = () => request.transaction.abort();
                    request.onerror = () => reject(request.error);
                    request.onsuccess = () => resolve(request.result);
                });
                try {
                    if (!db.objectStoreNames.contains('FILE_DATA')) continue;
                    await new Promise((resolve, reject) => {
                        const transaction = db.transaction('FILE_DATA', 'readonly');
                        const request = transaction.objectStore('FILE_DATA').openCursor();
                        request.onsuccess = () => {
                            const cursor = request.result;
                            if (!cursor) return;
                            if (String(cursor.key).endsWith('/runefall_v1.json')) {
                                const entry = cursor.value;
                                saves.push({database: info.name, path: cursor.key,
                                    timestamp: entry.timestamp.toISOString(),
                                    save: JSON.parse(new TextDecoder().decode(entry.contents))});
                            }
                            cursor.continue();
                        };
                        transaction.oncomplete = resolve;
                        transaction.onerror = () => reject(transaction.error);
                        transaction.onabort = () => reject(transaction.error);
                    });
                } finally {
                    db.close();
                }
            }
            return saves;
        }"""

    async def persisted_saves(page):
        async with asyncio.timeout(30):
            return await page.evaluate(read_persisted_saves)

    async def wait_persisted_quality(page, index):
        # Godot flushes its in-memory userfs to IndexedDB asynchronously on a
        # following frame. Check the committed primary before closing Chromium;
        # a memory-only QA state cannot establish browser-restart persistence.
        # wait_for_function does not poll asynchronous predicates: a Promise is
        # already truthy before its result is known. Await each readonly IDB
        # transaction in Python and only retry after an actual animation frame.
        async with asyncio.timeout(30):
            while True:
                rows = await persisted_saves(page)
                storage_states["waiting_quality_" + str(index)] = rows
                (output / "browser-storage.json").write_text(json.dumps(storage_states, indent=2))
                if len(rows) == 1:
                    saved = rows[0]["save"]
                    if (saved.get("version") == 1 and saved.get("journey_started") is True
                            and saved.get("checkpoint") == 0
                            and saved.get("settings", {}).get("quality") == index):
                        return
                await page.evaluate("() => new Promise(resolve => requestAnimationFrame(resolve))")

    async def click_button(page, prefix):
        status = await state(page)
        button = next((item for item in status["buttons"] if item["text"].startswith(prefix)), None)
        assert button is not None, (prefix, status)
        canvas = await page.locator("canvas").bounding_box()
        assert canvas is not None
        x = canvas["x"] + (button["x"] + button["w"] / 2) / status["ui_width"] * canvas["width"]
        y = canvas["y"] + (button["y"] + button["h"] / 2) / status["ui_height"] * canvas["height"]
        await page.mouse.click(x, y)

    async def select_quality(page, index):
        current = (await state(page))["quality"]
        await click_button(page, "균형" if current == 0 else "성능")
        await page.wait_for_function("window.__RUNEFALL_STATE.buttons.some(b => b.popup_visible)", timeout=30000)
        popup = next(item for item in (await state(page))["buttons"] if item.get("popup_visible"))
        focus = popup["popup_focus"]
        if focus < 0:
            await page.keyboard.press("ArrowDown")
            await page.wait_for_function("window.__RUNEFALL_STATE.buttons.some(b => b.popup_visible && b.popup_focus === 0)", timeout=30000)
            focus = 0
        if focus != index:
            await page.keyboard.press("ArrowDown" if index > focus else "ArrowUp")
            await page.wait_for_function("target => window.__RUNEFALL_STATE.buttons.some(b => b.popup_visible && b.popup_focus === target)", arg=index, timeout=30000)
        await page.keyboard.press("Enter")
        await page.wait_for_function("target => window.__RUNEFALL_STATE.quality === target", arg=index, timeout=15000)

    async def release_input(page):
        await page.keyboard.press("Escape")
        await page.wait_for_function("window.__RUNEFALL_STATE.paused", timeout=30000)
        await page.wait_for_function("!document.pointerLockElement", timeout=15000)

    async with async_playwright() as playwright:
        # A persistent profile is required to test IndexedDB after the browser closes.
        # Its temporary directory isolates this run from the developer's saves.
        with tempfile.TemporaryDirectory(prefix="runefall-browser-") as profile:
            context = await playwright.chromium.launch_persistent_context(profile, **launch_options)
            page = context.pages[0]
            tour_completed = False
            storage_states = {}
            try:
                await ready(page)
                stage = "first_tour"
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
                await select_quality(page, 1)
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
                quality_states = {"performance": status}
                stage = "balanced_quality_tour"
                await release_input(page)
                await click_button(page, "환경 설정")
                await page.wait_for_function("window.__RUNEFALL_STATE.buttons.some(b => b.kind === 'OptionButton')", timeout=15000)
                await select_quality(page, 0)
                await click_button(page, "완료")
                await page.wait_for_function("!window.__RUNEFALL_STATE.paused", timeout=15000)
                storage_states["balanced_before_wait"] = await persisted_saves(page)
                (output / "browser-storage.json").write_text(json.dumps(storage_states, indent=2))
                status = await state(page)
                assert status["quality"] == 0 and not status["dead"], status
                quality_states["balanced"] = status
                await page.screenshot(path=str(output / "06-balanced-gameplay.png"))
                await release_input(page)
                await wait_persisted_quality(page, 0)
                storage_states["balanced_committed"] = await persisted_saves(page)
                (output / "browser-storage.json").write_text(json.dumps(storage_states, indent=2))
                stage = "restore_performance_quality"
                await click_button(page, "환경 설정")
                await page.wait_for_function("window.__RUNEFALL_STATE.buttons.some(b => b.kind === 'OptionButton')", timeout=15000)
                await select_quality(page, 1)
                await click_button(page, "완료")
                await page.wait_for_function("!window.__RUNEFALL_STATE.paused && window.__RUNEFALL_STATE.quality === 1", timeout=15000)
                quality_states["restored"] = await state(page)
                (output / "browser-quality.json").write_text(json.dumps(quality_states, indent=2))
                storage_states["after_settings_done"] = await persisted_saves(page)
                (output / "browser-storage.json").write_text(json.dumps(storage_states, indent=2))
                await release_input(page)
                stage = "settings_durable_commit"
                await wait_persisted_quality(page, 1)
                storage_states["restored_committed"] = await persisted_saves(page)
                (output / "browser-storage.json").write_text(json.dumps(storage_states, indent=2))
                tour_completed = True
            finally:
                if errors or not tour_completed:
                    try:
                        storage_states["failure_" + stage] = await persisted_saves(page)
                    except Exception as error:
                        storage_states["failure_" + stage] = {"read_error": str(error)}
                    (output / "browser-storage.json").write_text(json.dumps(storage_states, indent=2))
                    await page.screenshot(path=str(output / "failure.png"))
                    (output / "failure-state.json").write_text(json.dumps(await state(page), indent=2))
                (output / "browser-errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2))
                if tour_completed:
                    storage_states["before_browser_close"] = await persisted_saves(page)
                    (output / "browser-storage.json").write_text(json.dumps(storage_states, indent=2))
                stage = "first_browser_close"
                await context.close()

            stage = "restart_load"
            context = await playwright.chromium.launch_persistent_context(profile, **launch_options)
            page = context.pages[0]
            continue_completed = False
            try:
                await ready(page)
                stage = "continue_tour"
                storage_states["after_browser_restart"] = await persisted_saves(page)
                (output / "browser-storage.json").write_text(json.dumps(storage_states, indent=2))
                assert (await state(page))["has_save"], "IndexedDB save did not survive a browser restart"
                await click_button(page, "여정 이어가기")
                await page.wait_for_function("window.__RUNEFALL_STATE.started && !window.__RUNEFALL_STATE.modal", timeout=15000)
                status = await state(page)
                assert status["checkpoint"] == 0 and abs(status["z"] - 6.0) < 1.0, status
                assert status["quality"] == 1, "Saved graphics settings did not survive the restart"
                await page.screenshot(path=str(output / "05-continue.png"))
                (output / "browser-persistence.json").write_text(json.dumps(status, indent=2))
                continue_completed = True
            finally:
                if errors or not continue_completed:
                    await page.screenshot(path=str(output / "failure.png"))
                    (output / "failure-state.json").write_text(json.dumps(await state(page), indent=2))
                if continue_completed:
                    await release_input(page)
                stage = "second_browser_close"
                await context.close()
                (output / "browser-errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2))
    if errors:
        raise RuntimeError("Browser errors: " + json.dumps(errors, ensure_ascii=False))
    print("RUNEFALL_BROWSER_OK · WebGL, quality 0/1, modal, input, combat entry, browser restart persistence")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default="http://127.0.0.1:8060")
    args = parser.parse_args()
    asyncio.run(run(args.url))
