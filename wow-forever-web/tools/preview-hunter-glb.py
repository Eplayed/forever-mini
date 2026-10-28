#!/usr/bin/env python3
"""Loopback-only viewer for the four round-7 hunter GLBs.

Reads model bytes from the mounted Windows share. Nothing is copied into app/img,
app/public, or a release bundle.
"""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


HERE = Path(__file__).resolve().parent
THREE = HERE.parent / "app" / "node_modules" / "three"
NAMES = {"alliance-ranged", "alliance-melee", "horde-ranged", "horde-melee"}
DEFAULT_SOURCE = Path(
    "/private/tmp/wow-ro/ziliao-export/round7-2026-10-28/"
    "run-20261028-125743/glb"
)


def handler_for(source):
    files = {
        "/": (HERE / "hunter-glb-preview.html", "text/html; charset=utf-8"),
        "/vendor/three.module.js": (THREE / "build" / "three.module.js", "text/javascript; charset=utf-8"),
        "/vendor/three.core.js": (THREE / "build" / "three.core.js", "text/javascript; charset=utf-8"),
        "/vendor/GLTFLoader.js": (THREE / "examples" / "jsm" / "loaders" / "GLTFLoader.js", "text/javascript; charset=utf-8"),
        "/vendor/OrbitControls.js": (THREE / "examples" / "jsm" / "controls" / "OrbitControls.js", "text/javascript; charset=utf-8"),
        "/utils/BufferGeometryUtils.js": (THREE / "examples" / "jsm" / "utils" / "BufferGeometryUtils.js", "text/javascript; charset=utf-8"),
        "/utils/SkeletonUtils.js": (THREE / "examples" / "jsm" / "utils" / "SkeletonUtils.js", "text/javascript; charset=utf-8"),
    }
    files.update({f"/models/{name}.glb": (source / f"{name}.glb", "model/gltf-binary") for name in NAMES})

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path
            entry = files.get(path)
            if not entry or not entry[0].is_file():
                self.send_error(404)
                return
            filename, mime = entry
            size = filename.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(size))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                with filename.open("rb") as src:
                    while chunk := src.read(1024 * 1024):
                        self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--port", type=int, default=8892)
    args = parser.parse_args()
    source = args.source.resolve()
    missing = [name for name in sorted(NAMES) if not (source / f"{name}.glb").is_file()]
    if missing:
        parser.error(f"missing GLB in {source}: {', '.join(missing)}")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(source))
    print(f"Preview: http://127.0.0.1:{args.port}/", flush=True)
    print(f"Read-only source: {source}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
