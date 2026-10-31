"""Exercise real WebGL, input, modal layout and IndexedDB across browser restarts.

python tools/browser_smoke.py http://127.0.0.1:8060
Use CHROMIUM_PATH for a system browser, or install Playwright's Chromium.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.async_api import async_playwright


async def run(url, output=Path("build/verification")):
    output.mkdir(parents=True, exist_ok=True)
    for name in ("01-title.png", "02-prologue.png", "03-pause.png", "04-gameplay.png",
                 "05-continue.png", "failure.png", "failure-state.json", "browser-state.json",
                 "browser-errors.json", "browser-persistence.json", "browser-quality.json", "06-balanced-gameplay.png",
                 "07-performance-gameplay.png", "08-skeletal-attack.png", "browser-storage.json",
                 "browser-progress.json", "browser-art.json", "browser-storage-diagnostics.json"):
        (output / name).unlink(missing_ok=True)
    errors = []
    stage = "initial_load"
    started = time.monotonic()
    progress = []
    art_states = {}
    known_save_targets = []
    storage_diagnostics = []
    storage_read_serial = 0

    def mark_stage(name):
        nonlocal stage
        stage = name
        item = {"stage": name, "elapsed_seconds": round(time.monotonic() - started, 3),
                "utc": datetime.now(timezone.utc).isoformat()}
        progress.append(item)
        (output / "browser-progress.json").write_text(json.dumps(progress, indent=2))
        print(f"RUNEFALL_BROWSER_STAGE {name} {item['elapsed_seconds']:.3f}s", flush=True)

    mark_stage(stage)
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

    async def ready(page, label):
        known_save_targets.clear()
        attach_errors(page)
        await page.add_init_script("""(() => {
            const stats = {count:0, max_gap_ms:0, max_gap_at_ms:0, last_ms:null, long_frames:[]};
            window.__RUNEFALL_QA_FRAME_PROBE = stats;
            function frame(now) {
                if (stats.last_ms !== null) {
                    const gap = now - stats.last_ms;
                    if (gap > stats.max_gap_ms) { stats.max_gap_ms = gap; stats.max_gap_at_ms = now; }
                    if (gap > 1000) {
                        stats.long_frames.push({at_ms:now, gap_ms:gap});
                        if (stats.long_frames.length > 24) stats.long_frames.shift();
                    }
                }
                stats.last_ms = now; stats.count++;
                requestAnimationFrame(frame);
            }
            requestAnimationFrame(frame);
        })();""")
        await page.bring_to_front()
        await page.goto(test_url, wait_until="networkidle")
        await page.wait_for_function("!document.getElementById('loading')", timeout=120000)
        await page.wait_for_function("window.__RUNEFALL_STATE !== undefined", timeout=30000)
        expected_commit = os.environ.get("RUNEFALL_EXPECTED_COMMIT")
        if expected_commit:
            build_id = await page.evaluate("window.__RUNEFALL_STATE.build_id")
            assert isinstance(build_id, str) and build_id.rsplit(" · ", 1)[-1] == expected_commit[:8], ("Published build differs from expected commit", build_id, expected_commit[:8])
        await page.bring_to_front()
        assert_hero_art(await state(page), label)

    async def state(page):
        return await page.evaluate("(() => { const s = window.__RUNEFALL_STATE; return s && {...s, qa_frame_probe:window.__RUNEFALL_QA_FRAME_PROBE}; })()")

    def record_art(label, status):
        if not isinstance(status, dict):
            art_states[label] = {"state_unavailable": status}
            (output / "browser-art.json").write_text(json.dumps(art_states, indent=2))
            return
        art_states[label] = {key: status.get(key) for key in
                             ("build_id", "quality", "encounter", "health", "z", "input_ready", "hero_art", "enemy_art")}
        (output / "browser-art.json").write_text(json.dumps(art_states, indent=2))

    def assert_hero_art(status, label):
        record_art(label, status)
        art = status.get("hero_art") or {}
        assert art.get("mode") == "skeletal" and art.get("profile") == "hero", (label, art)
        assert art.get("weapon_attached") is True, (label, art)
        assert art.get("eyes_attached") is True, (label, art)
        distance = art.get("grip_to_tip_m")
        assert isinstance(distance, (int, float)) and abs(distance - 1.19) <= 0.003, (label, art)

    def assert_melee_art(status):
        normal = [item for item in status.get("enemy_art", [])
                  if item.get("kind") == "melee" and not item.get("elite")
                  and not item.get("boss") and not item.get("dead")]
        assert normal, ("Combat entry did not expose a live normal melee enemy", status.get("enemy_art"))
        for art in normal:
            assert art.get("mode") == "skeletal" and art.get("profile") == "sentinel_melee", art
            assert art.get("weapon_attached") is True, art
            distance = art.get("grip_to_tip_m")
            assert isinstance(distance, (int, float)) and abs(distance - 1.19) <= 0.003, art

    # Observe the browser's durable copy, without writing to IDBFS or invoking
    # the engine's sync functions. This profile belongs only to this test.
    read_persisted_saves = """async requestInfo => {
            const knownTargets = requestInfo.targets;
            const saves = [];
            const targets = [];
            const trace = {request_id:requestInfo.id, phase:'started', events:[], key_count:0, primary_reads:0,
                cached_targets: Array.isArray(knownTargets) && knownTargets.length > 0};
            window.__RUNEFALL_QA_IDB_READ = trace;
            const mark = phase => {
                trace.phase = phase;
                trace.events.push({phase, milliseconds: performance.now()});
            };
            const grouped = new Map();
            if (trace.cached_targets) {
                for (const item of knownTargets) {
                    if (!grouped.has(item.database)) grouped.set(item.database, []);
                    grouped.get(item.database).push(item.path);
                }
            } else {
                mark('databases_request');
                for (const info of await indexedDB.databases()) {
                    if (info.name && info.name.startsWith('/userfs')) grouped.set(info.name, null);
                }
                mark('databases_response');
            }
            for (const [name, knownKeys] of grouped) {
                mark('open_request');
                const db = await new Promise((resolve, reject) => {
                    const request = indexedDB.open(name);
                    request.onupgradeneeded = () => request.transaction.abort();
                    request.onerror = () => reject(request.error);
                    request.onsuccess = () => resolve(request.result);
                });
                mark('open_response');
                try {
                    if (!db.objectStoreNames.contains('FILE_DATA')) continue;
                    await new Promise((resolve, reject) => {
                        const transaction = db.transaction('FILE_DATA', 'readonly');
                        const store = transaction.objectStore('FILE_DATA');
                        let readError = null;
                        const fail = error => {
                            readError = error;
                            transaction.abort();
                        };
                        const readPrimary = keys => {
                            mark('primary_requests');
                            for (const key of keys) {
                                if (typeof key !== 'string' || !key.endsWith('/runefall_v1.json')) continue;
                                targets.push({database:name, path:key});
                                trace.primary_reads++;
                                const request = store.get(key);
                                request.onsuccess = () => {
                                    const entry = request.result;
                                    if (!entry) return;
                                    try {
                                        saves.push({database:name, path:key,
                                            timestamp:new Date(entry.timestamp).toISOString(),
                                            save:JSON.parse(new TextDecoder().decode(entry.contents))});
                                    } catch (error) { fail(error); }
                                };
                            }
                        };
                        mark('transaction_request');
                        if (knownKeys !== null) {
                            readPrimary(knownKeys);
                        } else {
                            // Discover names in one request without cloning the
                            // contents of unrelated userfs/cache files.
                            const request = store.getAllKeys();
                            request.onsuccess = () => {
                                trace.key_count += request.result.length;
                                mark('keys_response');
                                readPrimary(request.result);
                            };
                        }
                        transaction.oncomplete = () => { mark('transaction_complete'); resolve(); };
                        transaction.onerror = () => reject(readError || transaction.error);
                        transaction.onabort = () => reject(readError || transaction.error);
                    });
                } finally {
                    db.close();
                }
            }
            mark('completed');
            return {saves, targets, diagnostic:trace};
        }"""

    async def persisted_saves(page):
        nonlocal storage_read_serial
        storage_read_serial += 1
        request_id = storage_read_serial
        read_started = time.monotonic()
        try:
            async with asyncio.timeout(30):
                result = await page.evaluate(read_persisted_saves, {"id":request_id, "targets":known_save_targets})
        except TimeoutError:
            try:
                async with asyncio.timeout(10):
                    diagnostic = await page.evaluate("({read:window.__RUNEFALL_QA_IDB_READ, frames:window.__RUNEFALL_QA_FRAME_PROBE})")
            except Exception as error:
                diagnostic = {"observation_error": type(error).__name__}
            storage_diagnostics.append({"stage":stage, "request_id":request_id, "outcome":"timeout", "diagnostic":diagnostic,
                                        "seconds":round(time.monotonic()-read_started, 3)})
            (output / "browser-storage-diagnostics.json").write_text(json.dumps(storage_diagnostics, indent=2))
            raise
        known_save_targets[:] = result["targets"]
        storage_diagnostics.append({"stage":stage, "request_id":request_id, "outcome":"completed", "diagnostic":result["diagnostic"],
                                    "seconds":round(time.monotonic()-read_started, 3)})
        (output / "browser-storage-diagnostics.json").write_text(json.dumps(storage_diagnostics, indent=2))
        return result["saves"]

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
                await ready(page, "title")
                mark_stage("first_tour")
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
                mark_stage("safe_quality_approach")
                await page.keyboard.down("w")
                await page.wait_for_function("window.__RUNEFALL_STATE.z <= -10", timeout=90000)
                await page.keyboard.up("w")
                status = await state(page)
                # First combat starts below z=-19.5. Compare both rendered
                # quality modes and wait for storage while safely outside it.
                assert status["encounter"] == -1 and -16 < status["z"] <= -8, status
                assert status["quality"] == 1 and not status["dead"] and status["health"] > 0, status
                assert_hero_art(status, "performance")
                quality_states = {"performance": status}
                await page.screenshot(path=str(output / "07-performance-gameplay.png"))
                mark_stage("balanced_quality_tour")
                await release_input(page)
                await click_button(page, "환경 설정")
                await page.wait_for_function("window.__RUNEFALL_STATE.buttons.some(b => b.kind === 'OptionButton')", timeout=15000)
                await select_quality(page, 0)
                await click_button(page, "완료")
                await page.wait_for_function("!window.__RUNEFALL_STATE.paused", timeout=15000)
                storage_states["balanced_before_wait"] = await persisted_saves(page)
                (output / "browser-storage.json").write_text(json.dumps(storage_states, indent=2))
                status = await state(page)
                assert status["encounter"] == -1 and -16 < status["z"] <= -8, status
                assert status["quality"] == 0 and not status["dead"] and status["health"] > 0, status
                assert_hero_art(status, "balanced")
                quality_states["balanced"] = status
                await page.screenshot(path=str(output / "06-balanced-gameplay.png"))
                await release_input(page)
                await wait_persisted_quality(page, 0)
                storage_states["balanced_committed"] = await persisted_saves(page)
                (output / "browser-storage.json").write_text(json.dumps(storage_states, indent=2))
                mark_stage("restore_performance_quality")
                await click_button(page, "환경 설정")
                await page.wait_for_function("window.__RUNEFALL_STATE.buttons.some(b => b.kind === 'OptionButton')", timeout=15000)
                await select_quality(page, 1)
                await click_button(page, "완료")
                await page.wait_for_function("!window.__RUNEFALL_STATE.paused && window.__RUNEFALL_STATE.quality === 1", timeout=15000)
                status = await state(page)
                assert status["encounter"] == -1 and -16 < status["z"] <= -8, status
                assert not status["dead"] and status["health"] > 0, status
                assert_hero_art(status, "restored")
                quality_states["restored"] = status
                (output / "browser-quality.json").write_text(json.dumps(quality_states, indent=2))
                storage_states["after_settings_done"] = await persisted_saves(page)
                (output / "browser-storage.json").write_text(json.dumps(storage_states, indent=2))
                await release_input(page)
                mark_stage("settings_durable_commit")
                await wait_persisted_quality(page, 1)
                storage_states["restored_committed"] = await persisted_saves(page)
                (output / "browser-storage.json").write_text(json.dumps(storage_states, indent=2))
                mark_stage("safe_skeletal_attack")
                await click_button(page, "계속하기")
                await page.wait_for_function("!window.__RUNEFALL_STATE.paused && window.__RUNEFALL_STATE.input_ready && window.__RUNEFALL_STATE.hero_art.state === 'idle'", timeout=15000)
                status = await state(page)
                assert status["encounter"] == -1 and -16 < status["z"] <= -8 and not status["dead"], status
                assert_hero_art(status, "safe_idle")
                idle_hand = status["hero_art"].get("right_hand_pose", [])
                assert len(idle_hand) == 7, status["hero_art"]
                # A fresh mouse event follows the real resume guard. This swing
                # happens before enemies spawn, so rendering/storage wait time
                # cannot turn the action observation into a survival test.
                await page.mouse.down()
                await page.mouse.up()
                await page.wait_for_function("before => { const s = window.__RUNEFALL_STATE; const pose = s.hero_art.right_hand_pose; return s.hero_art.state === 'light_1' && s.hero_art.sampled_time >= 0.08 && !s.dead && pose?.length === before.length && pose.some((value, index) => Math.abs(value - before[index]) > 0.0001); }", arg=idle_hand, timeout=15000)
                status = await state(page)
                assert status["encounter"] == -1, status
                assert_hero_art(status, "safe_attack")
                await page.screenshot(path=str(output / "08-skeletal-attack.png"))
                await page.wait_for_function("window.__RUNEFALL_STATE.input_ready && window.__RUNEFALL_STATE.hero_art.state === 'idle'", timeout=15000)
                status = await state(page)
                assert status["encounter"] == -1 and not status["dead"], status
                assert_hero_art(status, "after_safe_attack")
                mark_stage("first_combat")
                await page.keyboard.down("w")
                await page.wait_for_function("window.__RUNEFALL_STATE.encounter === 0", timeout=90000)
                await page.keyboard.up("w")
                await page.wait_for_function("window.__RUNEFALL_STATE.enemy_art.some(e => e.kind === 'melee' && !e.elite && !e.boss && !e.dead)", timeout=30000)
                status = await state(page)
                assert_hero_art(status, "combat_entry")
                assert_melee_art(status)
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
                assert status["quality"] == 1, status
                assert_hero_art(status, "combat")
                assert_melee_art(status)
                (output / "browser-state.json").write_text(json.dumps(status, indent=2))
                tour_completed = True
            finally:
                if errors or not tour_completed:
                    try:
                        storage_states["failure_" + stage] = await persisted_saves(page)
                    except Exception as error:
                        storage_states["failure_" + stage] = {"read_error": str(error)}
                    (output / "browser-storage.json").write_text(json.dumps(storage_states, indent=2))
                    await page.screenshot(path=str(output / "failure.png"))
                    status = await state(page)
                    record_art("failure_" + stage, status)
                    (output / "failure-state.json").write_text(json.dumps(status, indent=2))
                (output / "browser-errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2))
                if tour_completed:
                    storage_states["before_browser_close"] = await persisted_saves(page)
                    (output / "browser-storage.json").write_text(json.dumps(storage_states, indent=2))
                mark_stage("first_browser_close")
                await context.close()

            mark_stage("restart_load")
            context = await playwright.chromium.launch_persistent_context(profile, **launch_options)
            page = context.pages[0]
            continue_completed = False
            try:
                await ready(page, "restart_title")
                mark_stage("continue_tour")
                storage_states["after_browser_restart"] = await persisted_saves(page)
                (output / "browser-storage.json").write_text(json.dumps(storage_states, indent=2))
                assert (await state(page))["has_save"], "IndexedDB save did not survive a browser restart"
                await click_button(page, "여정 이어가기")
                await page.wait_for_function("window.__RUNEFALL_STATE.started && !window.__RUNEFALL_STATE.modal", timeout=15000)
                status = await state(page)
                assert status["checkpoint"] == 0 and abs(status["z"] - 6.0) < 1.0, status
                assert status["quality"] == 1, "Saved graphics settings did not survive the restart"
                assert_hero_art(status, "restart")
                await page.screenshot(path=str(output / "05-continue.png"))
                (output / "browser-persistence.json").write_text(json.dumps(status, indent=2))
                continue_completed = True
            finally:
                if errors or not continue_completed:
                    await page.screenshot(path=str(output / "failure.png"))
                    status = await state(page)
                    record_art("failure_" + stage, status)
                    (output / "failure-state.json").write_text(json.dumps(status, indent=2))
                if continue_completed:
                    await release_input(page)
                mark_stage("second_browser_close")
                await context.close()
                (output / "browser-errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2))
    if errors:
        raise RuntimeError("Browser errors: " + json.dumps(errors, ensure_ascii=False))
    mark_stage("completed")
    print("RUNEFALL_BROWSER_OK · WebGL, skeletal hero/melee, hand weapon, quality 0/1, input, combat, browser restart persistence")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default="http://127.0.0.1:8060")
    args = parser.parse_args()
    asyncio.run(run(args.url))
