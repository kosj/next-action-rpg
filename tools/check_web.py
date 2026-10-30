"""Serve the exported game below /web/ and run browser checks, including on CI."""
import asyncio
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

from browser_smoke import run


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


def main():
    root = Path(__file__).resolve().parents[1]
    if not (root / "build/web/index.html").is_file():
        raise SystemExit("Build the Web preset before running browser validation")
    handler = partial(QuietHandler, directory=str(root / "build"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        # A subdirectory catches absolute-URL mistakes that break project Pages URLs.
        asyncio.run(run(f"http://127.0.0.1:{server.server_port}/web/", root / "build/verification"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
