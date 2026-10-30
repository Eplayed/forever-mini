#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B1：把网页那 76 份已登记的真实整人 GLB 批量转成微信可用的 PNG 衍生件，并出一份独立索引。

只做本地：不碰 OSS、不改小程序页面、不动网页原件与别人的 art.json。
产物只落在 for-mini/oss-build/beta/ 下（这个目录已 gitignore，且线上到底有哪一批
由 bucket 上的清单说话，不把 90 MB 二进制抄进 git）。

三条硬规矩（2026-10-30 门槛文件 B1 写的）：
  1) 转换一律调现有的 derive-glb-textures.py，这里不再写第二份 GLB 解析器；
     回读也用同一个模块的 read_glb，避免"两份解析器各说一套"。
  2) 动手前先把 76 件做一次只读体检：setId+faction 唯一、placementVerdict=PASS、
     源文件 bytes/SHA 与登记同、dollSnapshot 与 bis.json 当前套装逐格同。
     任一不对就停并列清单——不许"能转几件算几件"。
  3) 每件转完立刻独立回读：引用与 BIN 边界合法、非图片字节与源相同、贴图解码后逐像素相同。
     失败即停，不把半成品当成功。
"""
import hashlib
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # wow-forever-web
REPO = os.path.dirname(ROOT)
WEB = os.path.join(ROOT, "app")
DERIVE = os.path.join(HERE, "derive-glb-textures.py")
BUILD = os.path.join(REPO, "for-mini", "oss-build", "beta")
MODELS_OUT = os.path.join(BUILD, "models")
INDEX_OUT = os.path.join(BUILD, "bis", "models", "index.json")
FORMAT_VERSION = "glb-png-v1"
PRODUCT = "wow-forever-mini-models"
SCHEMA_VERSION = 1
# 索引里给客户端拼 key 用的前缀：模型对象将来发在 wow/{env}/v1/assets/models/real/ 下
ASSET_DIR = "assets/models/real/"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def load_derive():
    import importlib.util
    spec = importlib.util.spec_from_file_location("derive_glb_textures", DERIVE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def doll_triples(rows):
    out = []
    for r in rows or []:
        out.append([str(r.get("slot")), int(r.get("cell") or 1), int(r.get("item"))])
    return sorted(out)


def doll_hash(rows):
    """稳定哈希：键序固定 + 紧凑分隔符，同一套装备在任何机器上算出来都是同一个串"""
    canon = json.dumps(doll_triples(rows), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def preflight(art, bis):
    errs = []
    items = (art.get("bisRealModels") or {}).get("items") or []
    if not items:
        return ["art.json.bisRealModels 是空的：没有可转的登记"], []
    seen = {}
    sets_by_id = {s.get("id"): s for s in bis.get("sets") or []}
    for it in items:
        sid = str(it.get("setId"))
        fac = str(it.get("faction"))
        key = sid + "|" + fac
        if key in seen:
            errs.append("登记里 setId+faction 重复：" + key)
            continue
        seen[key] = 1
        if it.get("placementVerdict") != "PASS":
            errs.append("%s/%s 的 placementVerdict 不是 PASS（%s）" % (sid, fac, it.get("placementVerdict")))
        rel = it.get("file") or ""
        abs_p = os.path.join(WEB, rel)
        if rel.startswith("/") or ".." in rel or not os.path.isfile(abs_p):
            errs.append("%s/%s 的源文件找不到：%s" % (sid, fac, rel))
            continue
        got = sha256_file(abs_p)
        if got != it.get("sha256"):
            errs.append("%s/%s 源 SHA 与登记不符（%s ≠ %s）" % (sid, fac, got[:12], str(it.get("sha256"))[:12]))
        if os.path.getsize(abs_p) != it.get("bytes"):
            errs.append("%s/%s 源字节与登记不符（%s ≠ %s）" % (sid, fac, os.path.getsize(abs_p), it.get("bytes")))
        st = sets_by_id.get(sid)
        if not st:
            errs.append("%s/%s 的 setId 在 bis.json 里找不到这套" % (sid, fac))
            continue
        cur = doll_triples(((st.get("doll") or {}).get(fac)) or [])
        snap = doll_triples(it.get("dollSnapshot") or [])
        if cur != snap:
            miss = [t for t in cur if t not in snap][:3]
            extra = [t for t in snap if t not in cur][:3]
            errs.append("%s/%s 的 dollSnapshot 与 bis.json 当前套装不一致（套装少了 %s / 登记多了 %s）"
                        % (sid, fac, miss, extra))
    return errs, items


def read_back(derive, src_path, out_path):
    """独立回读：不复用转换过程的中间结果，重新从磁盘读两份再比"""
    j0, b0 = derive.read_glb(src_path)
    j1, b1 = derive.read_glb(out_path)
    errs = []
    for key in ("meshes", "nodes", "materials", "accessors"):
        if len(j1.get(key) or []) != len(j0.get(key) or []):
            errs.append("%s 数量变了（%d ≠ %d）" % (key, len(j1.get(key) or []), len(j0.get(key) or [])))
    if json.dumps({k: j0.get(k) for k in ("meshes", "nodes", "materials", "accessors", "samplers")},
                  sort_keys=True) != json.dumps({k: j1.get(k) for k in ("meshes", "nodes", "materials", "accessors", "samplers")}, sort_keys=True):
        errs.append("几何/材质段与源不同（只许换贴图编码）")
    if j1.get("extensionsRequired"):
        errs.append("候选仍声明 required 扩展：%s" % j1["extensionsRequired"])
    for i, v in enumerate(j1.get("bufferViews") or []):
        if v.get("buffer") != 0:
            errs.append("bufferView %d 指向别的 buffer" % i)
        if v.get("byteOffset", 0) + v["byteLength"] > len(b1):
            errs.append("bufferView %d 越 BIN 边界" % i)
    nviews = len(j1.get("bufferViews") or [])
    for i, a in enumerate(j1.get("accessors") or []):
        bv = a.get("bufferView")
        if bv is not None and not (0 <= bv < nviews):
            errs.append("accessor %d 引用越界的 bufferView %s" % (i, bv))
    img0 = {j0["images"][i]["bufferView"] if j0["images"][i].get("bufferView") is not None
            else (j0["images"][i].get("extensions") or {}).get("EXT_texture_webp", {}).get("bufferView")
            for i in range(len(j0.get("images") or []))}

    def view(j, blob, i):
        v = j["bufferViews"][i]
        off = v.get("byteOffset", 0)
        return blob[off:off + v["byteLength"]]

    for i in range(min(len(j0.get("bufferViews") or []), nviews)):
        if i in img0:
            continue
        if view(j0, b0, i) != view(j1, b1, i):
            errs.append("非图片 bufferView %d 字节与源不同" % i)
    from PIL import Image
    for i in range(len(j0.get("images") or [])):
        def pix(j, blob, k):
            im = j["images"][k]
            s = im.get("bufferView")
            if s is None:
                s = (im.get("extensions") or {}).get("EXT_texture_webp", {}).get("bufferView")
            raw = view(j, blob, s)
            import io as _io
            return list(Image.open(_io.BytesIO(raw)).convert("RGBA").getdata())
        if pix(j0, b0, i) != pix(j1, b1, i):
            errs.append("贴图 %d 解码后像素与源不同" % i)
    return {"bufferViews": nviews, "accessors": len(j1.get("accessors") or []),
            "meshes": len(j1.get("meshes") or []), "images": len(j1.get("images") or []),
            "binBytes": len(b1)}, errs


def main():
    derive = load_derive()
    art = json.load(io.open(os.path.join(WEB, "data", "art.json"), encoding="utf-8"))
    bis = json.load(io.open(os.path.join(WEB, "data", "bis.json"), encoding="utf-8"))

    errs, items = preflight(art, bis)
    if errs:
        print("前置体检未过，%d 项：" % len(errs))
        for e in errs[:40]:
            print("  ✗ " + e)
        print("一件都不转（不留半成品当成功）。")
        return 1
    print("前置体检：%d 件全部 setId+faction 唯一、PASS、源 SHA/字节吻合、dollSnapshot 与 bis.json 逐格相同" % len(items))

    if os.path.isdir(MODELS_OUT):
        for f in os.listdir(MODELS_OUT):
            os.remove(os.path.join(MODELS_OUT, f))
    else:
        os.makedirs(MODELS_OUT)

    entries = []
    failed = []
    for n, it in enumerate(items, 1):
        sid, fac = it["setId"], it["faction"]
        src_abs = os.path.join(WEB, it["file"])
        tmp = os.path.join(MODELS_OUT, ".tmp-%s-%s.glb" % (sid, fac))
        r = subprocess.run([sys.executable, DERIVE, "--file", it["file"], "--out", tmp, "--format", "PNG"],
                           cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            failed.append("%s/%s 转换失败：%s" % (sid, fac, (r.stdout + r.stderr).strip().splitlines()[-1:]))
            if os.path.isfile(tmp):
                os.remove(tmp)
            continue
        sha = sha256_file(tmp)
        name = "%s-%s-%s.glb" % (sid, fac, sha[:12])
        final = os.path.join(MODELS_OUT, name)
        os.rename(tmp, final)
        stat, rb_errs = read_back(derive, src_abs, final)
        if rb_errs:
            failed.append("%s/%s 回读不合格：%s" % (sid, fac, "; ".join(rb_errs[:4])))
            os.remove(final)
            continue
        entries.append({
            "setId": sid, "faction": fac, "raceId": it.get("raceId"), "bodyType": it.get("bodyType"),
            "file": name, "assetDir": ASSET_DIR,
            "pngBytes": os.path.getsize(final), "pngSha256": sha,
            "sourceBytes": it["bytes"], "sourceSha256": it["sha256"],
            "e12SourceBytes": it.get("sourceBytes"), "e12SourceSha256": it.get("sourceSha256"),
            "placementVerdict": it["placementVerdict"],
            "dollSnapshot": it["dollSnapshot"], "dollSnapshotHash": doll_hash(it["dollSnapshot"]),
            "formatVersion": FORMAT_VERSION,
            "bufferViews": stat["bufferViews"], "accessors": stat["accessors"],
            "meshes": stat["meshes"], "images": stat["images"]
        })
        print("[%2d/%d] %s/%s → %s（%d B，回读 %d bufferView / %d accessor / %d 贴图 全合格）"
              % (n, len(items), sid, fac, name, os.path.getsize(final),
                 stat["bufferViews"], stat["accessors"], stat["images"]))

    if failed or len(entries) != len(items):
        print("\n✗ 有 %d 件没做成，索引不写：" % len(failed))
        for f in failed:
            print("  ✗ " + f)
        return 1

    keys = [e["setId"] + "|" + e["faction"] for e in entries]
    files = [e["file"] for e in entries]
    assert len(set(keys)) == len(keys) and len(set(files)) == len(files), "索引键或路径不唯一"
    total = sum(e["pngBytes"] for e in entries)
    big = max(entries, key=lambda e: e["pngBytes"])
    small = min(entries, key=lambda e: e["pngBytes"])
    index = {
        "schemaVersion": SCHEMA_VERSION,
        "product": PRODUCT,
        "kind": "bis-models-index",
        "formatVersion": FORMAT_VERSION,
        "assetDir": ASSET_DIR,
        "source": {
            "registry": "wow-forever-web/app/data/art.json.bisRealModels",
            "sets": "wow-forever-web/app/data/bis.json",
            "converter": "wow-forever-web/tools/derive-glb-textures.py --format PNG",
            "builder": "wow-forever-web/tools/build-mini-bis-models.py",
            "note": "每条同时记网页源与 PNG 成品的 bytes/sha256，还有最初 E12 导出包的 sourceSha256："
                    "网页那一份没动过，这里只是派生；换源就会换成品哈希。"
        },
        "timeNote": "本索引不含生成时间字段：同一批登记重跑得到同一份字节。什么时候建的看对象的服务端"
                    " Last-Modified 与构建端日志，模型何时核对看登记里的 sourceZip 与 bis.json 的 fetched。",
        "checks": [
            "转换前逐件核：setId+faction 唯一、placementVerdict=PASS、源 bytes/SHA 与登记同、dollSnapshot 与 bis.json 当前套装逐格同",
            "转换后逐件独立回读 GLB：bufferView/accessor 引用有效且不越 BIN、非图片 bufferView 逐字节与源同、"
            "meshes/nodes/materials/accessors/samplers 段与源同、贴图解码后逐像素同、不再声明 required 扩展",
            "文件名带成品 SHA 前 12 位；索引里不写本机绝对路径，客户端拼出来的 key 必须落在 assets/models/real/ 下"
        ],
        "counts": {
            "models": len(entries), "sets": len({e["setId"] for e in entries}),
            "bytes": total, "sourceBytes": sum(e["sourceBytes"] for e in entries),
            "max": {"setId": big["setId"], "faction": big["faction"], "bytes": big["pngBytes"]},
            "min": {"setId": small["setId"], "faction": small["faction"], "bytes": small["pngBytes"]}
        },
        "models": sorted(entries, key=lambda e: (e["setId"], e["faction"]))
    }
    body = json.dumps(index, ensure_ascii=False, indent=1) + "\n"
    if not os.path.isdir(os.path.dirname(INDEX_OUT)):
        os.makedirs(os.path.dirname(INDEX_OUT))
    with io.open(INDEX_OUT, "w", encoding="utf-8") as f:
        f.write(body)
    ib = body.encode("utf-8")
    print("\n索引 %s · %d B · sha256 %s" % (os.path.relpath(INDEX_OUT, REPO), len(ib),
                                          hashlib.sha256(ib).hexdigest()[:16] + "…"))
    print("76 件成品合计 %d B（%.2f MB）· 最大 %s/%s %d B · 最小 %s/%s %d B · 源合计 %d B"
          % (total, total / 1048576.0, big["setId"], big["faction"], big["pngBytes"],
             small["setId"], small["faction"], small["pngBytes"], index["counts"]["sourceBytes"]))
    print("状态：LOCAL_READY（未上传 OSS、未改页面）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
