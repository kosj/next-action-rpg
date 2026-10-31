import asyncio
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from playwright.async_api import async_playwright

ROOT = Path('/workspace/.runefall-task/character-polish/trail-lookdev/mix')
OUT = Path('/workspace/next-action-rpg/build/art-review/character-polish/trail/mix')
OUT.mkdir(parents=True, exist_ok=True)

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

async def capture(port):
    messages, states = [], {}
    started = time.monotonic()
    def console(message):
        messages.append({'type': message.type, 'text': message.text})
        if message.type == 'error':
            print('BROWSER_ERROR', message.text, flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path='/usr/bin/chromium', headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--use-angle=swiftshader',
                  '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'])
        try:
            page = await browser.new_page(viewport={'width': 1440, 'height': 900}, device_scale_factor=1)
            page.on('console', console)
            page.on('pageerror', lambda e: messages.append({'type':'pageerror', 'text':str(e)}))
            print('TRAIL_ART_STAGE load', flush=True)
            await page.goto(f'http://127.0.0.1:{port}/web/?qa=1', wait_until='networkidle', timeout=180000)
            await page.wait_for_function("!document.getElementById('loading') && window.__RUNEFALL_TRAIL_ART?.stage === 'ready'", timeout=180000)

            async def shot(name, key=None, hidden=False, detail=False, elapsed=.24):
                if key:
                    await page.keyboard.press(key)
                await page.wait_for_function("x => { const s=window.__RUNEFALL_TRAIL_ART; return s && s.hidden_ribbon_only===x.hidden && s.detail_reframe===x.detail && Math.abs(s.elapsed-x.elapsed)<.00001; }", arg={'hidden':hidden,'detail':detail,'elapsed':elapsed}, timeout=15000)
                await page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                state = await page.evaluate('structuredClone(window.__RUNEFALL_TRAIL_ART)')
                art = state['hero_art']
                assert art['mode'] == 'skeletal' and art['profile'] == 'hero' and art['weapon_attached'], state
                assert abs(art['grip_to_tip_m'] - 1.19) < .003, state
                assert art['blade_trail']['samples'] >= 2 and art['blade_trail']['triangles'] > 0, state
                assert art['blade_trail']['visible'] == (not hidden), state
                await page.screenshot(path=str(OUT/name), timeout=90000)
                states[name] = state
                (OUT/'capture-states.json').write_text(json.dumps(states, indent=2, ensure_ascii=False)+'\n')
                print('TRAIL_ART_STAGE saved', name, round(time.monotonic()-started, 3), flush=True)

            await shot('01-game-mix-024.png')
            await shot('02-detail-mix-024.png', 'v', detail=True)
            errors=[m for m in messages if m['type'] in ['error','pageerror']]
            assert not errors, errors
            print('TRAIL_ART_FIXED_CAPTURE_OK', flush=True)
        finally:
            (OUT/'capture-console.json').write_text(json.dumps(messages, indent=2, ensure_ascii=False)+'\n')
            (OUT/'capture-timing.json').write_text(json.dumps({'seconds':round(time.monotonic()-started,3),'scope':'Two MIX fixed-art fixture comparisons; not gameplay/timing QA'},indent=2)+'\n')
            await browser.close()

server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(ROOT)))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    asyncio.run(asyncio.wait_for(capture(server.server_port), timeout=145))
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
