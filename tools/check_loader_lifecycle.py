import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import re
import shutil

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description='Verify actual shell progress callbacks after loading DOM removal, with a stub Engine and real Chromium.')
parser.add_argument('--before', type=Path, default=ROOT/'docs/validation/v0.1.6/loader/before.html')
parser.add_argument('--after', type=Path, default=ROOT/'game/web/shell.html')
parser.add_argument('--output', type=Path, default=ROOT/'build/verification/loader')
args = parser.parse_args()
OUT = args.output
STUB = '''<script>
window.__loaderProbe={events:[],completed:false};
class Engine {
 static getMissingFeatures(){return [];}
 startGame(config){
  config.onProgress(1,2);
  window.__loaderProbe.early_value=document.getElementById('progress').value;
  return Promise.resolve().then(()=>{
   setTimeout(()=>{
    window.__loaderProbe.removed=!document.getElementById('loading');
    try {config.onProgress(2,2);config.onProgress(0,0);}
    finally {window.__loaderProbe.completed=true;}
   },0);
  });
 }
}
</script>'''

def fixture(text):
    text = text.replace('$GODOT_HEAD_INCLUDE', '')
    text = re.sub(r'<script src="[^"]+"></script>', '', text)
    text = re.sub(r'const engine = new Engine\(.*?\);', 'const engine = new Engine({});', text)
    return text.replace('<script>', STUB + '<script>', 1)

async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sources = {
        'before': args.before,
        'after': args.after,
    }
    results = {}
    async with async_playwright() as playwright:
        options = {'headless':True,'args':['--no-sandbox','--disable-dev-shm-usage']}
        executable = shutil.which('chromium')
        if executable:
            options['executable_path'] = executable
        browser = await playwright.chromium.launch(**options)
        try:
            for name,path in sources.items():
                page = await browser.new_page()
                errors = []
                page.on('pageerror',lambda error:errors.append(str(error)))
                source = path.read_text()
                await page.set_content(fixture(source))
                await page.wait_for_function('window.__loaderProbe.completed',timeout=5000)
                state = await page.evaluate('structuredClone(window.__loaderProbe)')
                results[name] = {'source':str(path),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                                 'state':state,'page_errors':errors}
                assert state['early_value'] == .5 and state['removed'] and state['completed'], results[name]
                if name == 'before':
                    assert len(errors)==1 and "Cannot set properties of null" in errors[0], results[name]
                else:
                    assert errors == [], results[name]
                await page.close()
        finally:
            await browser.close()
    report={'status':'passed','scope':'Actual source shell callback with stub Engine Promise; early progress plus late callback after real loading DOM removal. No WASM/gameplay/save/restart approval.',
            'browser_closed':True,'cases':results}
    (OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'before_errors':len(results['before']['page_errors']),
                      'after_errors':len(results['after']['page_errors']),'browser_closed':True}))

asyncio.run(main())
