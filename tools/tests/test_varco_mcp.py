"""Exercise real subprocess JSON-RPC pipes using a synthetic Codex child only."""
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import varco_mcp


FAKE_CHILD = r'''
import json, os, sys, time
mode, trace = sys.argv[1:]
def record(value):
    with open(trace, 'a', encoding='utf-8') as stream:
        stream.write(json.dumps(value)+'\n')
record({'pid': os.getpid()})
for line in sys.stdin:
    message = json.loads(line)
    record(message)
    method = message.get('method')
    if method == 'initialized':
        continue
    if method == 'initialize':
        result = {'capabilities': {}}
    elif method == 'mcpServerStatus/list':
        if mode == 'hang':
            time.sleep(60)
        if mode == 'close':
            sys.exit(7)
        if mode == 'malformed':
            print('NOT JSON WITH SYNTHETIC SECRET', flush=True)
            continue
        if mode == 'rpc_error':
            print(json.dumps({'id': message['id'], 'error': {'code': -32000, 'message': 'SYNTHETIC SECRET', 'data': {'authorizationUrl': 'https://example.invalid/oauth/authorize?code=SYNTHETIC'}}}), flush=True)
            continue
        if mode == 'interactive':
            print(json.dumps({'id': 'approval-1', 'method': 'unexpected/requestApproval', 'params': {'authorizationUrl': 'https://example.invalid/oauth/authorize?code=SYNTHETIC'}}), flush=True)
            continue
        print(json.dumps({'method': 'synthetic/notification', 'params': {'authorizationUrl': 'https://example.invalid/oauth/authorize?code=SYNTHETIC'}}), flush=True)
        result = {'data': [{'name': 'varco-3d', 'authStatus': 'oAuth', 'runtimeStatus': None, 'toolsError': None,
                           'tools': {'synthetic_tool': {'name': 'synthetic_tool', 'inputSchema': {'type': 'object', 'required': ['prompt'], 'properties': {'prompt': {'type': 'string'}}}}}}], 'nextCursor': None}
    elif method == 'thread/start':
        result = {'thread': {'id': 'synthetic-ephemeral-thread'}}
    elif method == 'mcpServer/tool/call':
        result = {'content': [{'type': 'text', 'text': 'synthetic success'}]}
        if mode == 'tool_error':
            result = {'isError': True, 'content': [{'type': 'text', 'text': 'SYNTHETIC SECRET https://example.invalid/oauth/authorize?code=SYNTHETIC'}]}
        if mode == 'tool_malformed':
            result = {'unexpected': 'synthetic'}
    elif 'error' in message:
        break
    else:
        sys.exit(8)
    print(json.dumps({'id': message['id'], 'result': result}), flush=True)
'''


class VarcoMCPTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.child = self.root / "fake_codex.py"
        self.child.write_text(FAKE_CHILD, encoding="utf-8")
        self.arguments = self.root / "arguments.json"
        self.arguments.write_text(json.dumps({"prompt": "synthetic prompt"}), encoding="utf-8")
        self.counter = 0

    def invoke(self, argv, mode="success"):
        self.counter += 1
        self.trace = self.root / f"trace-{self.counter}.jsonl"
        output = StringIO()
        with redirect_stdout(output):
            status = varco_mcp.main(argv, app_server_command=(sys.executable, str(self.child), mode, str(self.trace)))
        result = json.loads(output.getvalue())
        self.assertNotIn("SYNTHETIC SECRET", output.getvalue())
        self.assertNotIn("oauth/authorize", output.getvalue())
        self.messages = [json.loads(line) for line in self.trace.read_text().splitlines()] if self.trace.exists() else []
        return status, result

    def call(self, *, mode="success", tool="synthetic_tool", prefix=()):
        return self.invoke([*prefix, "call", tool, "--arguments", str(self.arguments)], mode)

    def test_catalog_and_call_complete_real_stdio_round_trips(self):
        status, result = self.invoke(["catalog"])
        self.assertEqual(status, 0)
        self.assertEqual(result["authStatus"], "oAuth")
        self.assertIn("synthetic_tool", result["tools"])
        self.assertNotIn("thread/start", [item.get("method") for item in self.messages])
        status, result = self.call()
        self.assertEqual(status, 0)
        self.assertEqual(result["result"]["content"][0]["text"], "synthetic success")
        thread = next(item for item in self.messages if item.get("method") == "thread/start")
        self.assertEqual(thread["params"], {"cwd": str(varco_mcp.ROOT), "ephemeral": True})
        tool = next(item for item in self.messages if item.get("method") == "mcpServer/tool/call")
        self.assertEqual(tool["params"], {"threadId": "synthetic-ephemeral-thread", "server": "varco-3d",
                                          "tool": "synthetic_tool", "arguments": {"prompt": "synthetic prompt"}})

    def test_unknown_tool_and_missing_arguments_stop_before_thread_or_call(self):
        status, result = self.call(tool="not_discovered")
        self.assertEqual(status, 1)
        self.assertFalse(result["ok"])
        self.assertNotIn("thread/start", [item.get("method") for item in self.messages])
        self.arguments.write_text("{}", encoding="utf-8")
        status, result = self.call()
        self.assertEqual(status, 1)
        self.assertIn("required field", result["error"])
        self.assertNotIn("mcpServer/tool/call", [item.get("method") for item in self.messages])
        self.arguments.write_text("[]", encoding="utf-8")
        status, result = self.call()
        self.assertEqual(status, 1)
        self.assertEqual(self.messages, [], "Non-object arguments should fail before child startup")
        for text in ('{"prompt": NaN}', '{"prompt": 1e999}'):
            self.arguments.write_text(text, encoding="utf-8")
            status, result = self.call()
            self.assertEqual(status, 1)
            self.assertEqual(self.messages, [])

    def test_rpc_error_bad_json_and_child_eof_fail_without_backend_data(self):
        for mode in ("rpc_error", "malformed", "close"):
            with self.subTest(mode=mode):
                status, result = self.invoke(["catalog"], mode)
                self.assertEqual(status, 1)
                self.assertFalse(result["ok"])
                self.assertIn("error", result)

    def test_mcp_tool_error_is_nonzero_and_omits_sensitive_error_body(self):
        status, result = self.call(mode="tool_error")
        self.assertEqual(status, 1)
        self.assertIn("isError", result["error"])
        self.assertNotIn("result", result)
        status, result = self.call(mode="tool_malformed")
        self.assertEqual(status, 1)
        self.assertIn("invalid MCP tool result", result["error"])

    def test_unexpected_interactive_request_is_explicitly_rejected(self):
        status, result = self.invoke(["catalog"], "interactive")
        self.assertEqual(status, 1)
        self.assertIn("interactive participation", result["error"])
        rejection = next(item for item in self.messages if item.get("id") == "approval-1")
        self.assertEqual(rejection["error"]["code"], -32601)

    def test_request_timeout_reaps_the_hanging_child(self):
        started = time.monotonic()
        status, result = self.invoke(["--timeout", "0.15", "catalog"], "hang")
        self.assertEqual(status, 1)
        self.assertIn("Timed out", result["error"])
        self.assertLess(time.monotonic() - started, 5)
        pid = self.messages[0]["pid"]
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)


if __name__ == "__main__":
    unittest.main()
