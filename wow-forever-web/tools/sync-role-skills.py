#!/usr/bin/env python3
"""把仓库内六个角色 skill 从唯一真源同步到 Trae/Qoder 的发现目录。"""

import argparse
import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / ".agents" / "skills"
MIRRORS = (ROOT / ".trae" / "skills", ROOT / ".qoder" / "skills")
ROLES = ("wow-pm", "wow-planner", "wow-ui", "wow-dev", "wow-data", "wow-ops")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="校验两处镜像与真源逐字节相同")
    mode.add_argument("--write", action="store_true", help="从真源重生成两处镜像")
    args = parser.parse_args()

    problems = []
    for role in ROLES:
        source = SOURCE / role / "SKILL.md"
        if not source.is_file():
            problems.append("缺真源：%s" % source.relative_to(ROOT))
            continue
        content = source.read_bytes()
        if not content.startswith(("---\nname: %s\n" % role).encode("utf-8")):
            problems.append("真源 name 与目录不符：%s" % source.relative_to(ROOT))
            continue
        digest = hashlib.sha256(content).hexdigest()[:12]
        for mirror_dir in MIRRORS:
            target = mirror_dir / role / "SKILL.md"
            if args.write:
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists() or target.read_bytes() != content:
                    target.write_bytes(content)
                    print("已同步 %s → %s" % (role, target.relative_to(ROOT)))
            elif not target.is_file() or target.read_bytes() != content:
                problems.append("镜像缺失或不同：%s" % target.relative_to(ROOT))
        print("%s %s" % (role, digest))

    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    print("六个角色 skill：唯一真源与 Trae/Qoder 镜像一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
