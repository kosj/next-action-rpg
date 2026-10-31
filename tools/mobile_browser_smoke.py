"""Exercise the real Web game with Chromium touch emulation, never mouse taps.

python tools/mobile_browser_smoke.py http://127.0.0.1:8060/web/ --output build/verification/mobile

This is not an Android/iOS device, Safari, or hardware-performance test. CDP
point-specific start/move/end follows the current official Puppeteer touch
implementation, pinned for review:
https://github.com/puppeteer/puppeteer/blob/72317747dbead16bcb53334cb8c356ccc9f01ce3/packages/puppeteer-core/src/cdp/Input.ts
The older dispatchTouchEvent PDL comment says touchEnd has no points; the
current implementation ends an individual handle with that point's ID. Actual
trusted DOM touches and Godot pointer ownership are observed to verify this.
"""
import argparse
import ast
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.async_api import async_playwright


UI_TIMEOUT = 15000
STORAGE_TIMEOUT = 30
PORTRAIT = {"width": 390, "height": 844}
LANDSCAPE = {"width": 844, "height": 390}
NARROW = {"width": 360, "height": 640}
ACTIONS = {"light", "heavy", "dodge", "parry", "heal", "skill_1", "skill_2", "skill_3",
           "interact", "lock_on", "target_next", "pause", "sprint"}


def readonly_storage_reader():
    """Reuse the actual desktop reader, including its key-only discovery/cache."""
    source = Path(__file__).with_name("browser_smoke.py")
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    values = [ast.literal_eval(node.value) for node in ast.walk(tree)
              if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == "read_persisted_saves"
                      for target in node.targets)]
    if len(values) != 1 or not isinstance(values[0], str):
        raise RuntimeError("Expected one literal desktop readonly persistence reader")
    return values[0]


def center(rect):
    return rect[0] + rect[2] / 2, rect[1] + rect[3] / 2


def contains(rect, point):
    return rect[0] <= point[0] <= rect[0] + rect[2] and rect[1] <= point[1] <= rect[1] + rect[3]


def distance(a, b):
    return math.hypot(a["x"] - b["x"], a["z"] - b["z"])


class Touches:
    """CDP emits real trusted touch events; IDs stay independent until release."""
    def __init__(self, client, page, log):
        self.client, self.page, self.log = client, page, log
        self.points = {}
        self.serial = 0

    async def send(self, kind, points):
        started = time.monotonic()
        async with asyncio.timeout(UI_TIMEOUT / 1000):
            await self.client.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": points})
        self.log.append({"type": kind, "points": [dict(point) for point in points],
                         "driver_ids_at_send": sorted(self.points),
                         "dispatch_seconds": round(time.monotonic()-started,3)})

    async def start(self, x, y):
        self.serial += 1
        point = {"id": self.serial, "x": x, "y": y, "radiusX": 1, "radiusY": 1, "force": .5}
        self.points[point["id"]] = point
        await self.send("touchStart", [point])
        return point["id"]

    async def move(self, pointer, x, y):
        point = self.points[pointer]
        point.update(x=x, y=y)
        await self.send("touchMove", [point])

    async def end(self, pointer):
        point = self.points[pointer]
        await self.send("touchEnd", [point])
        del self.points[pointer]

    async def release(self):
        for pointer in list(self.points):
            await self.end(pointer)

    async def cancel(self):
        await self.send("touchCancel", [])
        self.points.clear()

    async def tap(self, x, y):
        pointer = await self.start(x, y)
        # A real render boundary, not a fixed delay or game action injection.
        await self.page.evaluate("() => new Promise(resolve => requestAnimationFrame(resolve))")
        await self.end(pointer)


class MobileRun:
    def __init__(self, output):
        self.output = output
        self.started = time.monotonic()
        self.stage = "initial_load"
        self.progress, self.errors, self.states = [], [], {}
        self.events, self.layouts, self.storage = [], [], []
        self.storage_trace, self.save_targets = [], []
        self.navigation = []
        self.read_serial = 0
        self.reader = readonly_storage_reader()
        self.page = self.client = self.touch = None

    def write(self, name, value):
        (self.output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def mark(self, name):
        self.stage = name
        row = {"stage": name, "elapsed_seconds": round(time.monotonic() - self.started, 3),
               "utc": datetime.now(timezone.utc).isoformat()}
        self.progress.append(row)
        self.write("mobile-progress.json", self.progress)
        print(f"RUNEFALL_MOBILE_STAGE {name} {row['elapsed_seconds']:.3f}s", flush=True)

    async def state(self):
        return await self.page.evaluate("structuredClone(window.__RUNEFALL_STATE)")

    async def wait(self, expression, argument=None, timeout=UI_TIMEOUT):
        # page.evaluate awaits this Promise and serializes the satisfying
        # snapshot in the same round trip. wait_for_function + json_value adds
        # another renderer round trip while a real joystick is still held.
        # This is an awaited Promise, not a truthy async polling predicate.
        async with asyncio.timeout(timeout / 1000):
            return await self.page.evaluate(
                "a => new Promise(resolve => { function poll() { const s = window.__RUNEFALL_STATE; "
                "if (s && (" + expression + ")) resolve(structuredClone(s)); "
                "else requestAnimationFrame(poll); } poll(); })", argument)

    async def next_state(self, before):
        return await self.wait("s.physics_frame > a", before["physics_frame"])

    async def record(self, name, screenshot=False, status=None):
        status = status or await self.state()
        self.states[name] = status
        self.write("mobile-states.json", self.states)
        if screenshot:
            await self.page.screenshot(path=str(self.output / (name + ".png")))
        return status

    async def failure(self):
        if not self.page or self.page.is_closed():
            return
        try:
            async with asyncio.timeout(10):
                self.write("mobile-failure-state.json", await self.state())
                self.write("mobile-failure-touch-observation.json", await self.page.evaluate(
                    "({touches:window.__RUNEFALL_MOBILE_TOUCH_OBS,read:window.__RUNEFALL_QA_IDB_READ})"))
            await self.page.screenshot(path=str(self.output / "mobile-failure.png"), timeout=15000)
        except Exception as error:
            self.write("mobile-failure-diagnostic.json", {"error": str(error)})

    async def bind(self, context, page):
        self.page = page
        self.client = await context.new_cdp_session(page)
        await self.client.send("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 5})
        self.touch = Touches(self.client, page, self.events)
        self.save_targets.clear()
        page.on("pageerror", lambda error: self.errors.append(f"{self.stage}: {error}"))
        page.on("console", lambda message: self.errors.append(f"{self.stage}: {message.text}")
                if message.type == "error" else None)
        await page.add_init_script("""(() => {
          const report = {events:[], max_points:0, trusted:true, focus:[]};
          window.__RUNEFALL_MOBILE_TOUCH_OBS = report;
          for (const type of ['touchstart','touchmove','touchend','touchcancel']) {
            document.addEventListener(type, event => {
              report.max_points = Math.max(report.max_points, event.touches.length);
              report.trusted = report.trusted && event.isTrusted;
              report.events.push({type, touches:[...event.touches].map(t=>t.identifier),
                changed:[...event.changedTouches].map(t=>t.identifier), trusted:event.isTrusted});
              if (report.events.length > 200) report.events.shift();
            }, {capture:true,passive:true});
          }
          for (const type of ['blur','focus','visibilitychange']) {
            window.addEventListener(type, () => report.focus.push({type, focused:document.hasFocus(),
              visibility:document.visibilityState}), {capture:true});
          }
        })();""")

    async def ready(self, url):
        await self.page.goto(url, wait_until="networkidle")
        status = await self.wait("!document.getElementById('loading') && s.touch && s.touch.available", timeout=120000)
        required = {"physics_frame", "x", "z", "camera_yaw", "camera_pitch", "max_health", "rune", "potions",
                    "charge_elapsed", "dodge_cooldown", "parry_cooldown", "locked", "locked_target_id",
                    "interaction_kind", "interaction_index", "interaction_targets", "render_scale", "dpr", "ui", "touch"}
        assert required <= set(status), ("Missing readonly mobile QA fields", sorted(required-set(status)))
        expected = os.environ.get("RUNEFALL_EXPECTED_COMMIT")
        if expected:
            assert status["build_id"].rsplit(" · ", 1)[-1] == expected[:8], status
        art = status["hero_art"]
        assert art["mode"] == "skeletal" and art["eyes_attached"] and art["weapon_attached"], art
        assert abs(art["grip_to_tip_m"] - 1.19) <= .003, art
        self.write("mobile-browser.json", await self.client.send("Browser.getVersion"))
        self.write("mobile-environment.json", await self.page.evaluate("""({
          user_agent:navigator.userAgent, dpr:devicePixelRatio, max_touch_points:navigator.maxTouchPoints,
          coarse:matchMedia('(pointer:coarse)').matches, width:innerWidth,height:innerHeight,
          scope:'Chromium mobile/touch emulation, not Android/iOS/Safari or target hardware'
        })"""))
        assert await self.page.evaluate("devicePixelRatio === 2 && navigator.maxTouchPoints >= 3"), status
        return status

    async def canvas(self, status=None):
        status = status or await self.state()
        box = await self.page.locator("canvas").bounding_box()
        assert box and status["ui_width"] > 0 and status["ui_height"] > 0
        return box, box["width"] / status["ui_width"], box["height"] / status["ui_height"]

    async def css(self, point, status=None):
        box, sx, sy = await self.canvas(status)
        return box["x"] + point[0] * sx, box["y"] + point[1] * sy

    async def touch_action(self, action, hold=False):
        status = await self.state()
        assert status["touch"]["visible"] and not status["touch"]["waiting_release"], status["touch"]
        point = center(status["touch"]["action_rects"][action])
        x, y = await self.css(point, status)
        if hold:
            return await self.touch.start(x, y)
        await self.touch.tap(x, y)

    async def layout(self, label):
        status = await self.state()
        # Container sorting is deferred by Godot. Observe a fresh emitted
        # snapshot after the UI transition, rather than measuring birth sizes.
        status = await self.next_state(status)
        box, sx, sy = await self.canvas(status)
        assert box["width"] <= (await self.page.evaluate("innerWidth")) + 1
        assert abs(status["dpr"] - 2) < .01, status
        expected_scale = min(.8, 1/status["dpr"]) if status["quality"] == 0 else min(.65, .8/status["dpr"])
        assert abs(status["render_scale"] - expected_scale) < .001, (label, expected_scale, status["render_scale"])
        targets = []
        for button in status["buttons"]:
            if button.get("disabled") or not button.get("on_screen", True):
                continue
            target = {"text": button["text"], "width_css": button["w"] * sx,
                      "height_css": button["h"] * sy, "font_css": button.get("font_size", 0) * sy}
            assert target["width_css"] >= 44 - .01 and target["height_css"] >= 44 - .01, (label, target)
            targets.append(target)
        touch = status["touch"]
        if touch["visible"]:
            assert ACTIONS <= set(touch["action_rects"]), touch
            left, top, right, bottom = touch["safe_margins"]
            for action, rect in touch["action_rects"].items():
                assert rect[2] * sx >= 44 - .01 and rect[3] * sy >= 44 - .01, (label, action, rect, sx, sy)
                assert rect[0] >= left - .01 and rect[1] >= top - .01
                assert rect[0] + rect[2] <= status["ui_width"] - right + .01
                assert rect[1] + rect[3] <= status["ui_height"] - bottom + .01
        if status["modal"]:
            assert status["modal_x"] >= -1 and status["modal_y"] >= -1, status
            assert status["modal_x"] + status["modal_w"] <= status["ui_width"] + 1
            assert status["modal_y"] + status["modal_h"] <= status["ui_height"] + 1
        clipped = [text for text in status.get("ui", {}).get("texts", [])
                   if text.get("alpha", 1) > .1 and text.get("visible_w", 0) > 0 and text.get("visible_h", 0) > 0
                   and text.get("minimum_h", 0) > text["h"] + 1]
        assert not clipped, (label, clipped)
        self.layouts.append({"stage": label, "canvas": box, "logical_to_css": [sx, sy],
                             "ui": status.get("ui"), "touch": touch, "buttons_css": targets,
                             "render_scale": status.get("render_scale"), "dpr": status.get("dpr")})
        self.write("mobile-layout.json", self.layouts)
        return await self.record(label, screenshot=True, status=status)

    async def tap_button(self, prefix):
        # Move the real ScrollContainer with a finger if a target is clipped.
        for _ in range(10):
            status = await self.state()
            matches = [button for button in status["buttons"]
                       if button["text"].startswith(prefix) and not button.get("disabled", False)]
            assert matches, (prefix, status)
            button = matches[-1]  # modal controls follow background title controls
            if button.get("on_screen", True) and button.get("visible_h", button["h"]) >= min(44, button["h"]) - .01:
                rect = [button.get("visible_x", button["x"]), button.get("visible_y", button["y"]),
                        button.get("visible_w", button["w"]), button.get("visible_h", button["h"])]
                await self.touch.tap(*await self.css(center(rect), status))
                return
            scrolls = [item for item in status.get("ui", {}).get("scrolls", []) if item["max"] > item["page"]]
            assert scrolls, ("No scrollable route to button", prefix, status)
            scroll = scrolls[-1]
            downward = button["y"] + button["h"] / 2 > scroll["y"] + scroll["h"] / 2
            x = scroll["x"] + scroll["w"] / 2
            first, last = (.78, .25) if downward else (.25, .78)
            pointer = await self.touch.start(*await self.css((x, scroll["y"] + scroll["h"] * first), status))
            for fraction in [.25, .5, .75, 1]:
                y = scroll["y"] + scroll["h"] * (first + (last - first) * fraction)
                await self.touch.move(pointer, *await self.css((x, y), status))
                await self.page.evaluate("() => new Promise(resolve => requestAnimationFrame(resolve))")
            await self.touch.end(pointer)
            await self.next_state(status)
        raise AssertionError(("Button still clipped after bounded real scrolls", prefix))

    async def input_ready(self):
        state = await self.wait("s.input_ready && !s.paused && !s.modal && s.touch.visible && !s.touch.waiting_release")
        # Menus intentionally keep GUI mouse emulation until all GUI fingers
        # lift. Only the committed gameplay layer must disable that alias.
        assert state["touch"]["emulate_mouse_from_touch"] is False, state["touch"]
        return state

    async def idle(self):
        return await self.wait("s.input_ready && s.hero_art.state === 'idle' && s.touch.active_pointers.length === 0")

    async def stable(self, reference=None):
        state = await self.wait("s.input_ready && !s.paused && !s.modal && s.touch.visible && !s.touch.waiting_release && s.touch.active_pointers.length===0 && s.touch.pressed_actions.length===0")
        assert state["touch"]["emulate_mouse_from_touch"] is False, state
        assert state["hero_art"]["state"] == "idle", state
        if reference:
            assert distance(state, reference) < .2, ("Menu gesture moved/attacked", reference, state)
        first = state
        for _ in range(2):
            state = await self.next_state(state)
            assert state["hero_art"]["state"] == "idle", state
            assert distance(state, first) < .15, ("Input persisted after release", first, state)
        return state

    async def read_saves(self):
        self.read_serial += 1
        started = time.monotonic()
        try:
            async with asyncio.timeout(STORAGE_TIMEOUT):
                result = await self.page.evaluate(self.reader, {"id": self.read_serial, "targets": self.save_targets})
        except TimeoutError:
            self.storage_trace.append({"stage": self.stage, "outcome": "timeout",
                                       "seconds": round(time.monotonic() - started, 3)})
            self.write("mobile-storage-diagnostics.json", self.storage_trace)
            raise
        self.save_targets[:] = result["targets"]
        self.storage_trace.append({"stage": self.stage, "seconds": round(time.monotonic() - started, 3),
                                   "diagnostic": result["diagnostic"]})
        self.write("mobile-storage-diagnostics.json", self.storage_trace)
        return result["saves"]

    async def commit(self, quality):
        async with asyncio.timeout(STORAGE_TIMEOUT):
            while True:
                rows = await self.read_saves()
                self.storage.append({"stage": self.stage, "quality_expected": quality, "rows": rows})
                self.write("mobile-storage.json", self.storage)
                if len(rows) == 1:
                    save = rows[0]["save"]
                    if (save.get("version") == 1 and save.get("journey_started") is True
                            and save.get("checkpoint") == 0 and save.get("settings", {}).get("quality") == quality):
                        return
                await self.page.evaluate("() => new Promise(resolve => requestAnimationFrame(resolve))")

    async def set_quality(self, index, label):
        before = await self.idle()
        await self.touch_action("pause")
        await self.wait("s.paused && s.modal")
        await self.tap_button("환경 설정")
        await self.wait("s.buttons.some(b => b.text.startsWith('균형 · 기본'))")
        await self.layout(label + "-settings")
        await self.tap_button("균형 · 기본" if index == 0 else "성능 · 낮은")
        await self.wait("s.quality === a", index)
        await self.tap_button("완료")
        await self.stable(before)
        await self.commit(index)

    async def stick(self, vector=(0, 0)):
        status = await self.input_ready()
        origin = status["touch"]["joystick_center"]
        pointer = await self.touch.start(*await self.css(origin, status))
        if vector != (0, 0):
            radius = status["touch"]["joystick_radius"]
            await self.touch.move(pointer, *await self.css((origin[0] + vector[0] * radius,
                                                           origin[1] + vector[1] * radius), status))
        return pointer

    async def look(self):
        status = await self.input_ready()
        touch = status["touch"]
        rect = touch["look_rect"]
        blocked = [*touch["action_rects"].values(), touch["joystick_rect"]]
        candidates = [(rect[0] + rect[2] * x, rect[1] + rect[3] * y)
                      for y in [.25, .4, .55, .7] for x in [.35, .5, .7]]
        point = next((point for point in candidates if not any(contains(item, point) for item in blocked)), None)
        assert point, ("No free camera-drag region", touch)
        return await self.touch.start(*await self.css(point, status)), point

    async def navigate(self, x, z):
        state = await self.idle()
        pointer = None
        try:
            async with asyncio.timeout(60):
                while True:
                    dx, dz = x - state["x"], z - state["z"]
                    length = math.hypot(dx, dz)
                    if length < .8:
                        break
                    if pointer is None:
                        pointer = await self.stick()
                    yaw = state["camera_yaw"]
                    local = ((dx * math.cos(yaw) - dz * math.sin(yaw)) / length,
                             (dx * math.sin(yaw) + dz * math.cos(yaw)) / length)
                    origin, radius = state["touch"]["joystick_center"], state["touch"]["joystick_radius"]
                    desired_strength = min(.8, max(.1, (length - .45) / 8))
                    # The real stick maps (raw_radius-.14)/.86. Slow down near
                    # the target rather than relaxing distance/time criteria.
                    raw_radius = .14 + .86 * desired_strength
                    self.navigation.append({"target":[x,z], "physics_frame":state["physics_frame"],
                        "position":[state["x"],state["z"]], "distance":length,
                        "desired_strength":desired_strength, "raw_radius":raw_radius})
                    self.write("mobile-navigation.json", self.navigation)
                    await self.touch.move(pointer, *await self.css((origin[0] + local[0] * radius * raw_radius,
                                                                  origin[1] + local[1] * radius * raw_radius), state))
                    state = await self.wait("Math.hypot(s.x-a.x,s.z-a.z)>.35 || Math.hypot(s.x-a.tx,s.z-a.tz)<.8",
                                            {"x": state["x"], "z": state["z"], "tx": x, "tz": z})
        finally:
            if pointer is not None:
                await self.touch.end(pointer)
        stopped = await self.idle()
        self.navigation.append({"target":[x,z], "stopped_position":[stopped["x"],stopped["z"]],
                                "physics_frame":stopped["physics_frame"]})
        self.write("mobile-navigation.json", self.navigation)
        assert math.hypot(stopped["x"]-x, stopped["z"]-z) < 1.2, stopped

    async def resize(self, size, angle=0):
        await self.page.set_viewport_size(size)
        await self.client.send("Emulation.setDeviceMetricsOverride", {
            **size, "deviceScaleFactor": 2, "mobile": True,
            "screenWidth": size["width"], "screenHeight": size["height"],
            "screenOrientation": {"type": "landscapePrimary" if angle else "portraitPrimary", "angle": angle}})
        await self.wait("Math.abs(s.ui_width-a.width)<1 && Math.abs(s.ui_height-a.height)<1", size)

    async def cancelled(self, reason, change):
        await self.idle()
        await self.stick((0, -.6))
        await self.touch_action("heavy", hold=True)
        held = await self.wait("s.charge_elapsed>.1 && s.touch.active_pointers.length>=2")
        await change()
        cleared = await self.wait("s.touch.active_pointers.length===0 && s.touch.pressed_actions.length===0")
        assert cleared["touch"]["cancel_count"] > held["touch"]["cancel_count"], (reason, held, cleared)
        assert cleared["hero_art"]["state"] not in ["heavy", "light_1", "light_2", "light_3"], cleared
        if self.touch.points:
            await self.touch.cancel()
        if cleared["paused"] and cleared["modal"]:
            await self.tap_button("계속하기")
        await self.stable()
        await self.record(reason)

    async def multitouch_light(self):
        before = await self.idle()
        centered = await self.stick()
        await self.wait("s.touch.active_pointers.some(p => p.owner==='stick')")
        await self.touch.end(centered)
        await self.stable(before)
        blank_look, _ = await self.look()
        await self.touch.end(blank_look)
        after_blank = await self.stable(before)
        assert abs(after_blank["camera_yaw"]-before["camera_yaw"]) < .001
        # A deliberate quarter-strength movement gesture keeps the test in
        # the safe spawn room while pointer/camera/action ownership is read.
        stick = await self.stick((0, -(.14+.86*.25)))
        look, origin = await self.look()
        await self.touch.move(look, *await self.css((origin[0]+35,origin[1])))
        moving = await self.wait("Math.abs(s.camera_yaw-a.yaw)>.02 && Math.hypot(s.x-a.x,s.z-a.z)>.4",
                                 {"yaw":before["camera_yaw"],"x":before["x"],"z":before["z"]})
        assert moving["hero_art"]["state"] in ["idle","walk","run"] and not moving["touch"]["pressed_actions"], moving
        action = await self.touch_action("light",hold=True)
        simultaneous = await self.wait("s.touch.active_pointers.length>=3 && s.hero_art.state.startsWith('light_')")
        assert {p["owner"] for p in simultaneous["touch"]["active_pointers"]} >= {"stick","look","action"}
        await self.record("06-three-pointer-light",screenshot=True,status=simultaneous)
        await self.touch.move(action,*await self.css(origin,simultaneous))
        owned = await self.next_state(simultaneous)
        assert any(p["owner"]=="action" and p["action"]=="light" for p in owned["touch"]["active_pointers"]), owned
        assert abs(owned["camera_yaw"]-simultaneous["camera_yaw"]) < .001, owned
        await self.touch.end(action)
        await self.wait("s.touch.active_pointers.length===2 && !s.touch.pressed_actions.includes('light')")
        await self.touch.end(look)
        await self.touch.end(stick)
        await self.idle()


async def run(url, output=Path("build/verification/mobile"), phase="full"):
    assert phase in ["full","input-focus","multitouch-focus"], phase
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name in ["mobile-progress.json", "mobile-errors.json", "mobile-states.json", "mobile-layout.json",
                 "mobile-storage.json", "mobile-storage-diagnostics.json", "mobile-result.json",
                 "mobile-failure-state.json", "mobile-failure-diagnostic.json", "mobile-failure.png",
                 "mobile-failure-touch-observation.json", "mobile-touch-observation.json",
                 "mobile-dispatched-touch-events.json", "mobile-browser.json", "mobile-environment.json",
                 "mobile-navigation.json"]:
        (output/name).unlink(missing_ok=True)
    for name in ["01-portrait-title", "02-portrait-prologue", "03-portrait-gameplay", "04-rest-menu",
                 "05-shop-menu", "06-three-pointer-light", "07-heavy-held", "08-skill-one",
                 "09-portrait-settings", "10-landscape-gameplay", "11-landscape-settings",
                 "12-narrow-gameplay", "13-narrow-settings", "14-touch-combat-paused",
                 "15-restarted-touch-controls"]:
        (output/(name+".png")).unlink(missing_ok=True)
    qa = MobileRun(output)
    # A prior success must never survive a failed rerun in this output folder.
    qa.write("mobile-result.json", {"outcome": "running", "scope": "Unverified current run"})
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query)); query["qa"] = "1"
    test_url = urlunsplit(parts._replace(query=urlencode(query)))
    executable = os.environ.get("CHROMIUM_PATH") or shutil.which("chromium")
    options = {"headless": True, "viewport": PORTRAIT, "device_scale_factor": 2,
               "is_mobile": True, "has_touch": True,
               "args": ["--no-sandbox", "--disable-dev-shm-usage", "--use-angle=swiftshader",
                        "--enable-unsafe-swiftshader", "--autoplay-policy=no-user-gesture-required"]}
    if executable:
        options["executable_path"] = executable
    qa.write("mobile-scope.json", {"scope": "Actual emulated Chromium multitouch/UI/gameplay/persistence, not real Android/iOS/Safari or GPU performance",
                                   "phase": phase,
                                   "reader_sha256": hashlib.sha256(qa.reader.encode()).hexdigest(),
                                   "viewports": [PORTRAIT, LANDSCAPE, NARROW], "dpr": 2,
                                   "ui_timeout_ms": UI_TIMEOUT, "storage_timeout_seconds": STORAGE_TIMEOUT})
    context = None
    try:
        async with async_playwright() as playwright:
            with tempfile.TemporaryDirectory(prefix=".runefall-mobile-profile-", dir=output.resolve().parent) as profile:
                context = await playwright.chromium.launch_persistent_context(profile, **options)
                try:
                    page = context.pages[0]
                    await qa.bind(context, page)
                    qa.mark("portrait_title")
                    await qa.ready(test_url)
                    if phase == "full":
                        await qa.layout("01-portrait-title")
                    await qa.tap_button("새로운 서약")
                    await qa.wait("s.started && s.modal")
                    if phase == "full":
                        await qa.layout("02-portrait-prologue")
                    await qa.tap_button("성역으로 향한다")
                    await qa.stable()
                    if phase == "full":
                        await qa.layout("03-portrait-gameplay")
                    else:
                        if phase == "input-focus":
                            qa.mark("focused_navigation")
                            await qa.navigate(5,4)
                            await qa.navigate(0,6)
                        qa.mark("focused_three_pointer_input")
                        await qa.multitouch_light()
                        observation = await qa.page.evaluate("structuredClone(window.__RUNEFALL_MOBILE_TOUCH_OBS)")
                        assert observation["max_points"] >= 3 and observation["trusted"], observation
                        qa.write("mobile-touch-observation.json",observation)
                        assert not qa.errors,qa.errors
                        qa.mark("focused_completed")
                        qa.write("mobile-result.json",{"outcome":"focused_passed","phase":phase,
                            "seconds":round(time.monotonic()-qa.started,3),"errors":qa.errors,
                            "scope":"Fresh journey; trusted three-pointer movement/look/light only, plus navigation round trip for input-focus. Not full mobile QA."})
                        print("RUNEFALL_MOBILE_FOCUSED_OK · navigation/multitouch only; full workflow pending",flush=True)
                        return

                    qa.mark("rest_and_shop_taps")
                    await qa.touch_action("interact")
                    rest = await qa.wait("s.modal")
                    await qa.layout("04-rest-menu")
                    await qa.tap_button("여정을 계속한다")
                    await qa.stable(rest)
                    target = next(t for t in (await qa.state())["interaction_targets"] if t["kind"] == "npc" and t["index"] == 1)
                    await qa.navigate(target["x"], target["z"])
                    await qa.wait("s.interaction_kind==='npc' && s.interaction_index===1")
                    await qa.touch_action("interact")
                    shop = await qa.wait("s.modal")
                    assert any("대장장이" in text["text"] for text in shop["ui"]["texts"]), shop
                    await qa.layout("05-shop-menu")
                    await qa.tap_button("여정을 계속한다")
                    await qa.stable(shop)
                    await qa.navigate(0, 6)

                    qa.mark("three_pointer_movement_look_light")
                    await qa.multitouch_light()
                    await qa.navigate(0, 6)

                    sprint_stick = await qa.stick((.95, 0))
                    sprint = await qa.touch_action("sprint", hold=True)
                    await qa.record("sprint", status=await qa.wait("s.hero_art.state==='run'"))
                    await qa.touch.end(sprint); await qa.touch.end(sprint_stick)
                    await qa.idle()
                    await qa.navigate(0, 6)

                    qa.mark("hold_heavy_dodge_parry_heal_skill")
                    heavy = await qa.touch_action("heavy", hold=True)
                    charged = await qa.wait("s.charge_elapsed>=.65 && s.touch.pressed_actions.includes('heavy')")
                    await qa.record("07-heavy-held", screenshot=True, status=charged)
                    await qa.touch.end(heavy)
                    await qa.record("heavy-release", status=await qa.wait("s.hero_art.state==='heavy'"))
                    await qa.idle()
                    await qa.navigate(0, 6)
                    for action_name, cost in [("skill_2", 45), ("skill_3", 80)]:
                        gated = await qa.idle()
                        if gated["rune"] < cost:
                            await qa.touch_action(action_name)
                            after_gated = await qa.stable(gated)
                            assert abs(after_gated["rune"]-gated["rune"]) < .01
                            await qa.record(action_name + "-resource-gated", status=after_gated)
                    await qa.touch_action("dodge")
                    await qa.record("dodge", status=await qa.wait("s.dodge_cooldown>0"))
                    await qa.idle()
                    await qa.touch_action("parry")
                    await qa.record("parry", status=await qa.wait("s.parry_cooldown>0"))
                    await qa.idle()
                    heal = await qa.state()
                    await qa.touch_action("heal")
                    if heal["health"] < heal["max_health"] and heal["potions"] > 0:
                        await qa.wait("s.health>a.hp && s.potions===a.potions-1", {"hp": heal["health"], "potions": heal["potions"]})
                    else:
                        await qa.stable(heal)
                        after = await qa.state()
                        assert after["potions"] == heal["potions"], after
                    await qa.record("heal-legitimate-or-full-health-noop")
                    await qa.navigate(0, 6)
                    skill = await qa.idle()
                    assert skill["rune"] >= 25, skill
                    await qa.touch_action("skill_1")
                    await qa.record("08-skill-one", screenshot=True, status=await qa.wait("s.hero_art.state==='skill_1' && Math.abs(s.rune-(a-25))<.01", skill["rune"]))
                    await qa.idle()
                    await qa.navigate(0, 6)

                    qa.mark("pause_cancel_focus_and_quality")
                    await qa.stick((0, -.6)); await qa.touch_action("heavy", hold=True)
                    await qa.wait("s.charge_elapsed>.1")
                    await qa.touch_action("pause")
                    paused = await qa.wait("s.paused && s.modal && s.touch.active_pointers.length===0")
                    await qa.touch.release()
                    await qa.tap_button("계속하기")
                    await qa.stable(paused)
                    await qa.set_quality(1, "09-portrait")
                    await qa.cancelled("touchcancel", qa.touch.cancel)

                    async def focus_loss():
                        blank = await context.new_page()
                        try:
                            await blank.bring_to_front()
                            await qa.page.wait_for_function("!document.hasFocus() || document.visibilityState==='hidden'", timeout=UI_TIMEOUT)
                        finally:
                            await qa.page.bring_to_front()
                            await blank.close()
                    await qa.cancelled("focus-loss", focus_loss)

                    qa.mark("landscape_and_narrow_orientation")
                    await qa.cancelled("landscape-input-clear", lambda: qa.resize(LANDSCAPE, 90))
                    await qa.layout("10-landscape-gameplay")
                    await qa.set_quality(0, "11-landscape")
                    await qa.cancelled("narrow-input-clear", lambda: qa.resize(NARROW))
                    await qa.layout("12-narrow-gameplay")
                    await qa.set_quality(1, "13-narrow")
                    await qa.resize(PORTRAIT)
                    if (await qa.state())["paused"]:
                        await qa.tap_button("계속하기")
                    await qa.stable()

                    qa.mark("touch_combat_lock_and_alive")
                    await qa.navigate(0, -22)
                    await qa.wait("s.encounter>=0 && !s.dead")
                    await qa.touch_action("lock_on")
                    locked = await qa.wait("s.locked")
                    await qa.record("lock-on", status=locked)
                    await qa.touch_action("target_next")
                    await qa.record("target-next", status=await qa.wait("s.locked && s.locked_target_id!==a", locked["locked_target_id"]))
                    await qa.touch_action("light")
                    await qa.wait("s.hero_art.state.startsWith('light_')")
                    await qa.idle()
                    await qa.touch_action("pause")
                    combat = await qa.wait("s.paused && s.modal && s.health>0 && !s.dead")
                    await qa.record("14-touch-combat-paused", screenshot=True, status=combat)
                    await qa.commit(1)
                    observation = await qa.page.evaluate("structuredClone(window.__RUNEFALL_MOBILE_TOUCH_OBS)")
                    assert observation["max_points"] >= 3 and observation["trusted"], observation
                    qa.write("mobile-touch-observation.json", observation)
                except Exception:
                    await qa.failure()
                    raise
                finally:
                    await context.close()
                    context = None
                qa.mark("complete_browser_restart")
                context = await playwright.chromium.launch_persistent_context(profile, **options)
                try:
                    await qa.bind(context, context.pages[0])
                    await qa.ready(test_url)
                    await qa.wait("s.has_save && s.quality===1")
                    await qa.tap_button("여정 이어가기")
                    restored = await qa.stable()
                    assert restored["checkpoint"] == 0 and restored["health"] > 0 and abs(restored["z"] - 6) < 1.5, restored
                    await qa.layout("15-restarted-touch-controls")
                    await qa.commit(1)
                except Exception:
                    await qa.failure()
                    raise
                finally:
                    await context.close()
                    context = None
        assert not qa.errors, qa.errors
        qa.mark("completed")
        qa.write("mobile-result.json", {"outcome": "passed", "seconds": round(time.monotonic() - qa.started, 3),
                                       "scope": "Chromium touch emulation only; actual UI/input/gameplay/committed saves and full browser restart",
                                       "states": list(qa.states), "errors": qa.errors})
        print("RUNEFALL_MOBILE_OK · trusted multitouch, layouts, actions, input cancellation, quality, committed saves and full browser restart", flush=True)
    except Exception as error:
        await qa.failure()
        qa.write("mobile-result.json", {"outcome": "failed", "stage": qa.stage,
                                       "seconds": round(time.monotonic() - qa.started, 3), "errors": qa.errors,
                                       "exception_type": type(error).__name__, "exception": str(error)})
        raise
    finally:
        qa.write("mobile-errors.json", qa.errors)
        qa.write("mobile-dispatched-touch-events.json", qa.events)
        if context:
            await context.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--output", type=Path, default=Path("build/verification/mobile"))
    parser.add_argument("--phase",choices=["full","input-focus","multitouch-focus"],default="full")
    arguments = parser.parse_args()
    asyncio.run(run(arguments.url, arguments.output,arguments.phase))
