"""Convert registered boss portraits for the mini program's PNG decoder."""
import hashlib
import io
import json
from pathlib import Path

from PIL import Image

APP = Path(__file__).resolve().parents[1] / "app"
OUT = APP / "img/art/bosses-mini-png"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    data = json.loads((APP / "data/dungeons.json").read_text(encoding="utf-8"))
    paths = {
        boss["portrait"]
        for key in ("newDungeons", "classicDungeons", "raids")
        for dungeon in data[key]
        for boss in dungeon["bosses"]
        if str(boss.get("portrait")).endswith(".webp")
    }
    OUT.mkdir(parents=True, exist_ok=True)
    files = {}
    for source in sorted(paths):
        original = (APP / source).read_bytes()
        image = Image.open(io.BytesIO(original)).convert("RGBA")
        output = io.BytesIO()
        image.save(output, format="PNG", optimize=True)
        png = output.getvalue()
        sha = digest(png)
        target = OUT / f"{Path(source).stem}-{sha[:12]}.png"
        target.write_bytes(png)
        files[source] = {
            "file": target.relative_to(APP).as_posix(),
            "sourceSha256": digest(original),
            "sha256": sha,
            "bytes": len(png),
        }
    manifest = {
        "kind": "boss-portrait-format-derivatives",
        "note": "Registered local portrait images decoded to RGBA and saved losslessly as PNG. Original art manifests retain source attribution.",
        "files": files,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"{len(files)} PNGs, {sum(x['bytes'] for x in files.values())} bytes")


if __name__ == "__main__":
    main()
