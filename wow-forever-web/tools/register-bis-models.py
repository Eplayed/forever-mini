#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 app/img/models/ 里的模型登记进 app/data/art.json（键 `bisModels`）。

为什么要这一步：页面不许自己猜文件在不在（那样"模型没烘出来"和"路径写错了"
在界面上长得一模一样），也不许在组件里抄一份文件名。所以由这里扫目录生成台账，
页面读 `art.json.bisModels`：**目录空 → 那个按钮根本不出现**，有文件才给点。

来源边界（红线）：只登记本站自己生成的模型。`manifest.json` 里 `origin` 不是
`self-generated` 的一律拒绝入库——想放第三方站烘的 GLB 请先改根 AGENTS.md 那条素材红线。

用法：python3 tools/register-bis-models.py
"""
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(ROOT, "app", "img", "models")
ART = os.path.join(ROOT, "app", "data", "art.json")


def main():
    man_path = os.path.join(MD, "manifest.json")
    if not os.path.exists(man_path):
        sys.exit("缺 %s —— 先跑 tools/build-bis-placeholder-model.py" % os.path.relpath(man_path, ROOT))
    man = json.load(open(man_path, encoding="utf-8"))
    origin = man.get("origin")
    if origin != "self-generated":
        sys.exit("manifest.origin = %r，不是 self-generated：第三方或客户端来的模型要走红线改口径，"
                 "这个脚本只登记本站自产的模型" % origin)

    items = []
    for it in man.get("items") or []:
        f = it.get("file") or ""
        p = os.path.join(MD, f)
        if not os.path.exists(p):
            sys.exit("台账里登记了 %s，但文件不在 %s" % (f, os.path.relpath(MD, ROOT)))
        raw = open(p, "rb").read()
        real = hashlib.sha1(raw).hexdigest()
        if it.get("sha1") and it["sha1"] != real:
            sys.exit("%s 的 sha1 与台账不符（台账 %s ／ 实得 %s）——重跑生成脚本，别手改台账"
                     % (f, it["sha1"][:12], real[:12]))
        if len(raw) != it.get("bytes"):
            sys.exit("%s 字节数与台账不符（台账 %s ／ 实得 %d）" % (f, it.get("bytes"), len(raw)))
        items.append({
            "file": "img/models/" + f, "bytes": len(raw), "sha1": real,
            "kind": it.get("kind") or "placeholder",
            "generatedAt": man.get("generatedAt"),
            "gearNodes": it.get("gearNodes") or [],
        })

    art = json.load(open(ART, encoding="utf-8"))
    art["bisModels"] = {
        "items": items,
        "origin": origin,
        "note": man.get("note") or "",
        "generatedAt": man.get("generatedAt"),
        # 生成脚本的名字只留在 img/models/manifest.json（那份不进构建产物），
        # 抄进 art.json 就会被禁词闸拦下——那是给玩家看的数据文件，不该出现我们的脚本路径
    }
    with open(ART, "w", encoding="utf-8") as f:
        f.write(json.dumps(art, ensure_ascii=False, indent=1) + "\n")
    print("art.json.bisModels 登记 %d 个模型：%s"
          % (len(items), ", ".join(x["file"] for x in items) or "（空）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
