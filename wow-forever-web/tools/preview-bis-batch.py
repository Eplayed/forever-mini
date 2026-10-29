#!/usr/bin/env python3
"""Read-only loopback preview of Windows batch GLBs outside the site assets."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


HERE = Path(__file__).resolve().parent
THREE = HERE.parent / "app/node_modules/three"
DEFAULT_SOURCE = Path("/private/tmp/wow-ro/ziliao-export/round9-all-bis-3d/packages")


def handler_for(source):
    files = {
        "/": (HERE / "bis-batch-preview.html", "text/html; charset=utf-8"),
        "/vendor/three.module.js": (THREE / "build/three.module.js", "text/javascript; charset=utf-8"),
        "/vendor/three.core.js": (THREE / "build/three.core.js", "text/javascript; charset=utf-8"),
        "/vendor/GLTFLoader.js": (THREE / "examples/jsm/loaders/GLTFLoader.js", "text/javascript; charset=utf-8"),
        "/vendor/OrbitControls.js": (THREE / "examples/jsm/controls/OrbitControls.js", "text/javascript; charset=utf-8"),
        "/utils/BufferGeometryUtils.js": (THREE / "examples/jsm/utils/BufferGeometryUtils.js", "text/javascript; charset=utf-8"),
        "/utils/SkeletonUtils.js": (THREE / "examples/jsm/utils/SkeletonUtils.js", "text/javascript; charset=utf-8"),
    }
    if (source / "glb").is_dir():
        for path in (source / "glb").glob("*.glb"):
            files["/models/" + path.name] = (path.resolve(), "model/gltf-binary")
    for package in source.iterdir():
        result = package / "RESULT.json"
        if not result.is_file():
            continue
        for row in json.loads(result.read_text())["results"]:
            path = (package / row["glbFile"]).resolve()
            if path.is_relative_to(package.resolve()) and path.is_file():
                files["/models/" + path.name] = (path, "model/gltf-binary")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            entry = files.get(urlsplit(self.path).path)
            if not entry:
                self.send_error(404)
                return
            filename, mime = entry
            size = filename.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(size))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                with filename.open("rb") as src:
                    while part := src.read(1024 * 1024):
                        self.wfile.write(part)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *_args):
            pass

    return Handler, sum(path.endswith(".glb") for path in files)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--port", type=int, default=8893)
    ap.add_argument("--expected", type=int, default=76)
    args = ap.parse_args()
    handler, count = handler_for(args.source)
    if count != args.expected:
        ap.error(f"expected {args.expected} GLB paths, found {count}")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Preview: http://127.0.0.1:{args.port}/?model=hunter-alliance", flush=True)
    print(f"Read-only source: {args.source} ({count} GLBs)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
