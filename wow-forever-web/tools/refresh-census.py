"""Refresh the licensed Everloot aggregate without replacing the last good sample on failure."""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile


ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "app/data/population-census.json"
VALIDATE = r"""
const { readFileSync } = require('node:fs');
const { validateCensus } = require('./tools/oss-release.js');
const current = JSON.parse(readFileSync(process.argv[1], 'utf8'));
const sample = JSON.parse(readFileSync(0, 'utf8'));
const errors = validateCensus(sample, current.classes.map(row => row.id));
if (errors.length) {
  console.error(errors.join('\n'));
  process.exitCode = 1;
}
"""


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def project_sample(payload, current, now):
    answer = payload["answer"]
    page = answer["page"]
    window = page["window"]
    source = current["provenance"]
    if (payload["arguments"].get("window") != "week" or answer["connected"] is not True
            or page["collecting"] is not False or page["scope"]["id"] != current["scope"]["id"]
            or window["id"] != "week" or answer["url"] != source["url"]
            or page["source"]["url"] != source["url"] or page["licence"] != source["license"]):
        raise ValueError("Everloot 未返回已登记口径、来源和许可的可用样本")

    data_as_of = answer["dataAsOf"]
    observed_at = timestamp(data_as_of)
    if (data_as_of != window["to"] or observed_at < timestamp(current["dataAsOf"])
            or not now - timedelta(days=7) <= observed_at <= now + timedelta(minutes=5)):
        raise ValueError("Everloot 样本时间已过期、倒退或与统计区间不符")

    sample = dict(current, dataAsOf=data_as_of, characters=page["characters"], installs=page["installs"])
    sample["window"] = dict(current["window"], **{key: window[key] for key in ("from", "to")})
    sample["provenance"] = dict(source, checkedAt=now.astimezone(timezone(timedelta(hours=8))).date().isoformat())
    for field, dimension in (("factions", "faction"), ("classes", "class")):
        rows = [
            {"id": cell[dimension].lower(), "count": cell["count"], "share": cell["share"]}
            for cell in page["cells"] if cell["slice"] == dimension
        ]
        rank = {row["id"]: index for index, row in enumerate(current[field])}
        sample[field] = sorted(rows, key=lambda row: rank.get(row["id"], len(rank)))
    return sample


def main():
    current = json.loads(TARGET.read_text(encoding="utf-8"))
    curl = "curl.exe" if os.name == "nt" else "curl"
    response = subprocess.check_output([
        curl, "--fail", "--silent", "--show-error", "--max-time", "25",
        current["provenance"]["apiUrl"],
    ])
    sample = project_sample(json.loads(response), current, datetime.now(timezone.utc))
    content = json.dumps(sample, ensure_ascii=False, indent=2) + "\n"
    subprocess.run(["node", "-e", VALIDATE, str(TARGET)], input=content.encode("utf-8"), cwd=ROOT, check=True)
    if sample != current:
        staging = None
        try:
            with NamedTemporaryFile(dir=TARGET.parent, delete=False) as handle:
                staging = Path(handle.name)
                handle.write(content.encode("utf-8"))
            staging.replace(TARGET)
        finally:
            if staging is not None:
                staging.unlink(missing_ok=True)
    print(f"Everloot {sample['dataAsOf']} · {sample['characters']} 角色 · {sample['installs']} 上报安装")


if __name__ == "__main__":
    try:
        main()
    except (subprocess.CalledProcessError, OSError, KeyError, ValueError, TypeError, AttributeError) as exc:
        sys.exit(f"人口普查刷新失败，保留原样本。{exc}")
