"""Use VARCO through the official Codex app-server client, never direct HTTP.

python tools/varco_mcp.py catalog > build/varco-catalog.json
python tools/varco_mcp.py call get_node_catalog --arguments build/varco-arguments.json \
    > build/varco-result.json

The configured Codex client owns MCP discovery, OAuth and credential storage.
This utility does not inspect authentication files or perform OAuth/login.
Authenticate separately with the official MCP client if user participation is
required. Interactive requests fail closed; they are never approved here.

Output is JSON. Full successful tool results can contain account/Flow information
and temporary asset URLs: save them only in gitignored build/ or a temporary
directory, never in knowledge records or source control. Notifications and backend
error bodies are not logged, so their credentials/OAuth URLs are not printed.
Argument validation checks only the discovered tool name, object shape and root
required fields. The official server validates the remaining JSON Schema rules.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SERVER = "varco-3d"
ARGUMENT_SCOPE = "Discovered tool name, root object and required fields only; full schema validation belongs to the server."


class ClientError(RuntimeError):
    """An error whose controlled message is safe to report without backend data."""


class CodexAppServer:
    def __init__(self, *, timeout=120.0, command=None):
        self.timeout = timeout
        # command injection is an in-process test seam; the CLI always uses Codex.
        self.command = tuple(command) if command is not None else ("codex", "app-server", "--stdio")
        self.process = None
        self.serial = 0

    async def __aenter__(self):
        try:
            self.process = await asyncio.create_subprocess_exec(
                *self.command, cwd=ROOT, stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
                limit=16_000_000,
            )
            await self.request("initialize", {
                "clientInfo": {"name": "runefall_varco_client", "version": "0.1.0"},
                "capabilities": {"experimentalApi": True},
            })
            await self.send({"method": "initialized", "params": {}})
            return self
        except BaseException:
            await self.close()
            raise

    async def __aexit__(self, *_):
        await self.close()

    async def send(self, value):
        try:
            self.process.stdin.write((json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))
            await self.process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            raise ClientError("The official Codex client closed its input stream") from None

    async def request(self, method, params):
        self.serial += 1
        identifier = self.serial

        async def exchange():
            await self.send({"id": identifier, "method": method, "params": params})
            while True:
                try:
                    line = await self.process.stdout.readline()
                except (ValueError, asyncio.LimitOverrunError):
                    raise ClientError("Codex response exceeded the supported frame size") from None
                if not line:
                    raise ClientError(f"The official Codex client closed before responding to {method}")
                try:
                    message = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    raise ClientError("The official Codex client returned malformed JSON") from None
                if not isinstance(message, dict):
                    raise ClientError("The official Codex client returned a non-object message")
                if "method" in message:
                    if not isinstance(message["method"], str):
                        raise ClientError("The official Codex client returned an invalid notification/request method")
                    if "id" in message:
                        await self.send({"id": message["id"], "error": {
                            "code": -32601, "message": "Interactive requests require user participation outside this utility",
                        }})
                        raise ClientError("Codex requested interactive participation; complete it in the official client")
                    # Notifications may contain OAuth or account data; do not log them.
                    continue
                if type(message.get("id")) is not int or message["id"] != identifier:
                    raise ClientError("The official Codex client returned an unexpected response ID")
                if ("result" in message) == ("error" in message):
                    raise ClientError("Codex response must contain exactly one result or error")
                if "error" in message:
                    error = message["error"]
                    code = error.get("code") if isinstance(error, dict) else None
                    code = code if type(code) is int else "unknown"
                    # Raw error text/data may contain credentials or authorization links.
                    raise ClientError(f"Codex JSON-RPC error {code} while handling {method}")
                return message["result"]

        try:
            return await asyncio.wait_for(exchange(), timeout=self.timeout)
        except asyncio.TimeoutError:
            raise ClientError(f"Timed out waiting for the official Codex client: {method}") from None

    async def close(self):
        process = self.process
        if process is None:
            return
        if process.stdin is not None:
            process.stdin.close()
        if process.returncode is None:
            try:
                await asyncio.wait_for(process.wait(), timeout=0.5)
            except asyncio.TimeoutError:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
                try:
                    await asyncio.wait_for(process.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                    await process.wait()
        else:
            await process.wait()


async def discover(client):
    result = await client.request("mcpServerStatus/list", {
        "serverName": SERVER, "detail": "toolsAndAuthOnly", "limit": 100,
    })
    if not isinstance(result, dict) or not isinstance(result.get("data"), list):
        raise ClientError("Codex returned an invalid MCP server catalog")
    servers = [server for server in result["data"] if isinstance(server, dict) and server.get("name") == SERVER]
    if len(servers) != 1:
        raise ClientError("VARCO MCP is not uniquely registered in the official Codex client")
    server = servers[0]
    tools = server.get("tools")
    if not isinstance(tools, dict) or server.get("toolsError"):
        raise ClientError("VARCO MCP tool discovery failed; check the official client's connection/authentication")
    for name, tool in tools.items():
        if not isinstance(name, str) or not name or not isinstance(tool, dict) or tool.get("name") != name or not isinstance(tool.get("inputSchema"), dict):
            raise ClientError("Codex returned an invalid discovered VARCO tool schema")
    auth = server.get("authStatus")
    runtime = server.get("runtimeStatus")
    return {
        "server": SERVER,
        "authStatus": auth if isinstance(auth, str) else None,
        "runtimeStatus": runtime if isinstance(runtime, str) else None,
        "tools": tools,
    }


def validate_arguments(tool, arguments):
    if not isinstance(arguments, dict):
        raise ClientError("Tool arguments must be a JSON object")
    schema = tool["inputSchema"]
    if schema.get("type", "object") != "object":
        raise ClientError("Discovered tool inputSchema does not declare a supported root object")
    required = schema.get("required", [])
    if not isinstance(required, list) or any(not isinstance(field, str) for field in required):
        raise ClientError("Discovered tool inputSchema has invalid required fields")
    if any(field not in arguments for field in required):
        raise ClientError("Tool arguments omit a required field from the discovered inputSchema")


async def execute(command, *, tool_name=None, arguments=None, timeout=120.0, app_server_command=None):
    async with CodexAppServer(timeout=timeout, command=app_server_command) as client:
        catalog = await discover(client)
        if command == "catalog":
            return {"ok": bool(catalog["tools"]), **catalog}
        if tool_name not in catalog["tools"]:
            raise ClientError("Requested tool was not found in the discovered VARCO catalog")
        if catalog["authStatus"] == "notLoggedIn":
            raise ClientError("VARCO MCP requires authentication in the official Codex client")
        validate_arguments(catalog["tools"][tool_name], arguments)
        thread = await client.request("thread/start", {"cwd": str(ROOT), "ephemeral": True})
        if not isinstance(thread, dict) or not isinstance(thread.get("thread"), dict) or not isinstance(thread["thread"].get("id"), str) or not thread["thread"]["id"]:
            raise ClientError("Codex returned an invalid ephemeral thread")
        result = await client.request("mcpServer/tool/call", {
            "threadId": thread["thread"]["id"], "server": SERVER,
            "tool": tool_name, "arguments": arguments,
        })
        if not isinstance(result, dict) or not isinstance(result.get("content"), list) or ("isError" in result and type(result["isError"]) is not bool):
            raise ClientError("Codex returned an invalid MCP tool result")
        if result.get("isError", False):
            raise ClientError("VARCO tool returned isError; its potentially sensitive error body was not logged")
        return {"ok": True, "server": SERVER, "tool": tool_name,
                "argument_validation_scope": ARGUMENT_SCOPE, "result": result}


def positive_timeout(value):
    try:
        timeout = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("timeout must be a positive finite number") from None
    if not 0 < timeout < float("inf"):
        raise argparse.ArgumentTypeError("timeout must be a positive finite number")
    return timeout


def reject_json_constant(_):
    raise ValueError("Nonfinite JSON constant")


def main(argv=None, *, app_server_command=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--timeout", type=positive_timeout, default=120.0, help="Seconds per official client request (default: 120)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("catalog", help="Show discovered VARCO tool schemas and authentication status")
    call = commands.add_parser("call", help="Call an explicitly named discovered tool in an ephemeral thread")
    call.add_argument("tool")
    call.add_argument("--arguments", required=True, type=Path, help="JSON object file; keep private arguments/results in gitignored storage")
    args = parser.parse_args(argv)
    try:
        arguments = None
        if args.command == "call":
            try:
                arguments = json.loads(args.arguments.read_text(encoding="utf-8"),
                                       parse_constant=reject_json_constant)
                # Also rejects overflowed JSON numbers such as 1e999.
                json.dumps(arguments, allow_nan=False)
            except (OSError, ValueError, RecursionError):
                raise ClientError("Could not read arguments as valid finite JSON; file contents were not logged") from None
            if not isinstance(arguments, dict):
                raise ClientError("Tool arguments must be a JSON object")
        result = asyncio.run(execute(args.command, tool_name=getattr(args, "tool", None), arguments=arguments,
                                     timeout=args.timeout, app_server_command=app_server_command))
    except (ClientError, OSError):
        # OSError details can include OS/environment paths; keep those out of logs too.
        error = sys.exc_info()[1]
        message = str(error) if isinstance(error, ClientError) else "Could not start or communicate with the official Codex client"
        result = {"ok": False, "error": message}
    except KeyboardInterrupt:
        result = {"ok": False, "error": "Cancelled; the official Codex child was cleaned up"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
