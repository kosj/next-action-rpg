import asyncio
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from playwright.async_api import async_playwright

ROOT = Path('/workspace/.runefall-task/character-polish/eyes-web/palette')
OUT = Path('/workspace/next-action-rpg/build/art-review/character-polish/eyes-web/palette')

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

async def capture(port):
    messages, states = [], {}
    started = time.monotonic()
    def console(message):
        messages.append({'type':message.type, 'text':message.text})
        if message.type == 'error':
            print('EYE_ART_BROWSER_ERROR', message.text, flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path='/usr/bin/chromium', headless=True,
            args=['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader',
                  '--enable-unsafe-swiftshader','--autoplay-policy=no-user-gesture-required'])
        try:
            page = await browser.new_page(viewport={'width':1440,'height':900}, device_scale_factor=1)
            page.on('console', console)
            page.on('pageerror', lambda e:messages.append({'type':'pageerror','text':str(e)}))
            print('EYE_ART_STAGE load', flush=True)
            await page.goto(f'http://127.0.0.1:{port}/web/?qa=1', wait_until='networkidle', timeout=180000)
            await page.wait_for_function("!document.getElementById('loading') && window.__RUNEFALL_EYE_ART?.stage==='ready'", timeout=180000)

            async def shot(index, quality):
                await page.wait_for_function("e => { const s=window.__RUNEFALL_EYE_ART; return s && s.case_index===e.index && s.quality===e.quality; }", arg={'index':index,'quality':quality}, timeout=15000)
                await page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                state=await page.evaluate('structuredClone(window.__RUNEFALL_EYE_ART)')
                art=state['hero_art']
                assert art['mode']=='skeletal' and art['profile']=='hero' and art['eyes_attached'], state
                assert state['head_socket_max_component_error'] < .0001, state
                name=f"{index+1:02d}-{state['case']['name']}-q{quality}.png"
                await page.screenshot(path=str(OUT/name), timeout=90000)
                states[name]=state
                (OUT/'capture-states.json').write_text(json.dumps(states,indent=2,ensure_ascii=False)+'\n')
                print('EYE_ART_STAGE saved',name,round(time.monotonic()-started,3),flush=True)

            await page.keyboard.press('n')
            for index in [1,2]:
                await shot(index,0)
                await page.keyboard.press('q')
                await shot(index,1)
                await page.keyboard.press('q')
                if index < 2:
                    await page.keyboard.press('n')
            for index in [1,2]:
                pair=[s for s in states.values() if s['case_index']==index]
                assert len(pair)==2, pair
                for field in ['camera_transform','hero_transform','case','head_world_transform','eye_model_world_transform']:
                    assert pair[0][field]==pair[1][field], (field,pair)
            errors=[m for m in messages if m['type'] in ['error','pageerror']]
            assert not errors, errors
            print('EYE_ART_FIXED_CAPTURE_COMPLETE_VISUAL_REVIEW_PENDING',flush=True)
        finally:
            (OUT/'capture-console.json').write_text(json.dumps(messages,indent=2,ensure_ascii=False)+'\n')
            (OUT/'capture-timing.json').write_text(json.dumps({'seconds':round(time.monotonic()-started,3),'scope':'Four COLOR_0-only fixed-art eye comparisons; visual review separate from successful capture'},indent=2)+'\n')
            await browser.close()

if __name__=='__main__':
    # Deliberately unavailable until root confirms final geometry/native result.
    manifest=json.loads((ROOT/'source-manifest.json').read_text())
    assert manifest['root_final_hash_and_native_pass_received'] is True
    OUT.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)))
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        asyncio.run(capture(server.server_port))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
