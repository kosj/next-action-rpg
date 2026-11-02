"""Exercise the real browser observer helper against an isolated test double.

This opens no game and proves no gameplay, rendering, phone performance or AAA
quality. In particular the expected deadline failure must retain its evidence.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil

from playwright.async_api import async_playwright
from mobile_browser_smoke import MobileRun, UI_TIMEOUT


async def run(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    qa = MobileRun(output)
    qa.stage = "isolated_observer_test_double"
    result = {"passed":False,"scope":__doc__,"ui_timeout_ms":UI_TIMEOUT,
              "browser_started":False,"browser_closed":False,
              "helper_sha256":hashlib.sha256(Path(__file__).with_name("mobile_browser_smoke.py").read_bytes()).hexdigest()}
    try:
        async with async_playwright() as playwright:
            options = {"headless":True,"args":["--no-sandbox"]}
            executable = os.environ.get("CHROMIUM_PATH") or shutil.which("chromium") or shutil.which("chromium-browser")
            if executable:
                options["executable_path"] = executable
            browser = await playwright.chromium.launch(**options)
            result["browser_started"] = True
            try:
                page = await browser.new_page()
                qa.page = page
                await page.goto("about:blank")
                await page.evaluate("""() => {
                    window.__RUNEFALL_STATE={physics_frame:1,ready:false,health:120,
                      hero_art:{state:'idle'},attack:{attack_id:'',attack_instance_id:0,stagger:0}};
                }""")

                async def test_double_change():
                    await page.evaluate("""() => new Promise(resolve => requestAnimationFrame(() => {
                      window.__RUNEFALL_STATE.physics_frame++;
                      window.__RUNEFALL_STATE.ready=true;resolve();
                    }))""")

                first = await qa.observe_action("s.ready",None,test_double_change)
                retained = await page.evaluate("structuredClone(window.__RUNEFALL_MOBILE_ACTION_OBS[1])")
                assert first["physics_frame"] == 2 and retained["terminal"] == "matched",retained
                assert retained["snapshot"] == first and retained["timeline"],retained
                result["matched_terminal_retained_until_host_ack"] = True

                async def no_gesture():
                    # Negative helper test only: never send a real game action.
                    return None

                failed = None
                try:
                    await qa.observe_action("false",None,no_gesture)
                except (TimeoutError,AssertionError) as error:
                    failed = type(error).__name__
                assert failed is not None,"An unsatisfied predicate silently passed"
                # This is forensic evidence AFTER the failed gate, not a late pass.
                await page.wait_for_function(
                    "window.__RUNEFALL_MOBILE_ACTION_OBS[2]?.terminal==='expired'",timeout=2000)
                rows = await page.evaluate("structuredClone(window.__RUNEFALL_MOBILE_ACTION_OBS)")
                assert "1" not in rows,"Previously received match was not acknowledged on next arm"
                assert rows["2"]["expired"] and "snapshot" not in rows["2"],rows
                assert rows["2"]["poll_count"] > 0 and len(rows["2"]["timeline"]) <= 64,rows
                assert qa.action_attempts[-1]["outcome"] == "failed",qa.action_attempts
                result.update({"passed":True,"negative_gate_exception":failed,
                    "expired_evidence_retained":True,"received_previous_result_acknowledged":True,
                    "negative_terminal":rows["2"],"host_attempts":qa.action_attempts})

                class WithheldTerminalReply:
                    """Test-only IPC double: browser matches, host receives no reply."""
                    async def evaluate(self, *args):
                        value = await page.evaluate(*args)
                        if isinstance(value,dict) and value.get("terminal") == "matched":
                            result["withheld_reply_reached_terminal"] = True
                            # Deliberate unresolved test double, not a game delay.
                            await asyncio.Future()
                        return value

                result["passed"] = False
                qa.page = WithheldTerminalReply()
                withheld_failed = False
                try:
                    await qa.observe_action("s.ready",None,test_double_change)
                except TimeoutError:
                    withheld_failed = True
                finally:
                    qa.page = page
                late = await page.evaluate("structuredClone(window.__RUNEFALL_MOBILE_ACTION_OBS[3])")
                assert withheld_failed and result.get("withheld_reply_reached_terminal"),late
                assert late["terminal"] == "matched" and late["snapshot"]["physics_frame"] == 3,late
                assert qa.action_attempts[-1]["outcome"] == "failed" and len(qa.action_observations) == 1
                result.update({"passed":True,"matched_but_withheld_reply_still_fails_deadline":True,
                               "matched_evidence_retained_after_host_timeout":late})
            finally:
                await browser.close()
                result["browser_closed"] = True
    finally:
        (output/"observer-proof.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("MOBILE_OBSERVER_HELPER_OK match/expiry/withheld-reply evidence retained; unchanged15s gate")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=Path("build/verification/mobile/observer-helper"))
    args = parser.parse_args()
    asyncio.run(run(args.output))


if __name__ == "__main__":
    main()
