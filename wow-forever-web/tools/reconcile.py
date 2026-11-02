#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地 vs 线上对账（**只读**：不改数据、不构建、不上传，也不发布）。

站主要的那句话是："能不能一眼看出我们和线上的数据库版本需不需要更新。"
两条分发线分开答，因为它们的现成能力差很多：

网页（GitHub Pages）
    线上是逐字从 app/data 拷过去的（2026-11-02 实测：线上 data/meta.json 的 git blob 号
    等于提交 398805d 里那份），所以**不用改发布流程也能对账**：
      ① HEAD 拿 Content-Length —— 尺寸不同就直接判"不同"，不必下载；
      ② 尺寸相同才 GET 下来比 SHA-256（同尺寸不同内容是真出过的：线上/本地 meta.json 都是 5672 字节，
         差的只是里面那个日期字段）；
      ③ 线上那份 scale.json 很小、能稳定取到，里面就带着**线上那一版每个板块的核对日**，
         和本地 scale.json 对着一摆，就是"哪几块线上还停在旧日期"。
    为什么不全靠下载：这台机器到 Pages 的吞吐很差，5.3 MB 的 data/items.json 取 60 秒只回来 211 KB
    就被截断（curl 还报 200）。所以尺寸比对优先，取不到就照实写"读不到"，不许拿截断的字节算哈希。

小程序（阿里云 OSS 批次 + 指针）
    指针与 files.json 都是公共读，匿名 GET 即可（不碰密钥；bucket/region 从仓库根 .oss-env 现读，
    命名空间从 oss-release.js 现读，都不抄第二份）。比的是"本地最近构建的那一批"与"指针指的那一批"。

三种状态必须分清：**一致** / **不同** / **读不到**。读不到不等于一致，也不等于线上坏了。
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(WEB, "tools")
DATA = os.path.join(WEB, "app", "data")
REPO = os.path.dirname(WEB)
MINI_BUILD = os.path.join(REPO, "for-mini", "oss-build")

sys.path.insert(0, os.path.join(TOOLS, "admin"))      # catalog 那份板块表是唯一的，别在这儿重列一遍


def read(path):
    return io.open(path, encoding="utf-8").read() if os.path.isfile(path) else ""


def pages_base():
    """线上网页的地址从 publish.py 现读，不在这里抄第二份。"""
    m = re.search(r'^PAGES_URL\s*=\s*["\']([^"\']+)', read(os.path.join(TOOLS, "publish.py")), re.M)
    return (m.group(1).rstrip("/") if m else ""), ("publish.py" if m else "读不到 PAGES_URL")


def oss_config(env):
    """匿名读 OSS 只需要 bucket 与 region——密钥一概不读、不打印。"""
    kv = dict(re.findall(r"^(OSS_BUCKET|OSS_REGION)\s*=\s*(.+)$",
                         read(os.path.join(REPO, ".oss-env")), re.M))
    ns = re.search(r"const NAMESPACES\s*=\s*\{([^}]*)\}", read(os.path.join(TOOLS, "oss-release.js")))
    table = dict(re.findall(r"(\w+)\s*:\s*['\"]([^'\"]+)['\"]", ns.group(1))) if ns else {}
    bucket, region, prefix = (kv.get("OSS_BUCKET") or "").strip(), (kv.get("OSS_REGION") or "").strip(), table.get(env)
    if not (bucket and region and prefix):
        return None, "缺 bucket/region（仓库根 .oss-env）或 %s 的命名空间（oss-release.js）" % env
    return "https://%s.%s.aliyuncs.com/%s" % (bucket, region, prefix), "bucket %s · %s" % (bucket, region)


def fetch(url, timeout=25, method="GET", cap=None, tries=2):
    """返回 (状态, 头, 字节)。任何异常都归成 ('err', ...)，不假装读到了。
       默认试两次：这台机器到 Pages 一次连不上是常态（11-02 实测同一地址一会儿 200 一会儿 000），
       一次不通就判"读不到"会把"其实一致"的文件也算进读不到那一堆，等于把结论淹了。
       两次都不通才写"读不到"——注意仍然不把它当成"一致"，也不当成"线上坏了"。"""
    last = None
    for _ in range(max(1, tries)):
        try:
            req = urllib.request.Request(url, method=method, headers={"User-Agent": "wow-forever-reconcile/1"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read(cap) if (cap and method == "GET") else (r.read() if method == "GET" else b"")
                return r.status, dict((k.lower(), v) for k, v in r.getheaders()), body
        except urllib.error.HTTPError as e:
            return e.code, {}, b""
        except Exception as e:
            last = str(e)[:90]
    return "err", {}, last.encode("utf-8")


def sha(b):
    return hashlib.sha256(b).hexdigest() if b else ""


def local_stat(path):
    if not os.path.isfile(path):
        return None
    b = open(path, "rb").read()
    return {"bytes": len(b), "sha256": sha(b), "mtime": datetime.date.fromtimestamp(os.path.getmtime(path)).isoformat()}


# ─────────────────────────────── 网页线 ───────────────────────────────
def web_row(base, rel, loc):
    """一个文件：先 HEAD 比尺寸，同尺寸才下载比哈希。"""
    url = "%s/data/%s" % (base, rel)
    code, head, _ = fetch(url, timeout=12, method="HEAD")
    if code == 404:
        return {"state": "线上没有这个文件", "url": url}
    if code != 200:
        return {"state": "读不到（这台机到 Pages 常抖）", "url": url}
    live_bytes = int(head.get("content-length") or 0)
    out = {"state": None, "url": url, "liveBytes": live_bytes,
           "liveModified": head.get("last-modified"), "liveEtag": (head.get("etag") or "").strip('"')}
    if loc is None:
        out["state"] = "本地没有这个文件（线上有）"
        return out
    out["localBytes"] = loc["bytes"]
    if live_bytes != loc["bytes"]:
        out["state"] = "不同（尺寸就不一样）"
        return out
    code2, _, body = fetch(url, timeout=45)
    if code2 != 200 or len(body) != live_bytes:
        # 取不全就当读不到：拿截断字节算哈希会把"一致"判成"不同"
        out["state"] = "读不到（同尺寸但这一趟没取全）"
        return out
    out["state"] = "一致" if sha(body) == loc["sha256"] else "不同（同尺寸不同内容，多半是里面那个日期）"
    return out


def web_live_scale(base):
    """线上那版 scale.json：小、稳，里面就带逐板块核对日。"""
    code, _, body = fetch("%s/data/scale.json" % base, timeout=30)
    if code != 200:
        return None, "读不到（HTTP %s）" % code
    try:
        return json.loads(body.decode("utf-8")), "取到了"
    except Exception as e:
        return None, "解析失败 %s" % str(e)[:60]


def web_report(env_note=""):
    base, how = pages_base()
    out = {"base": base or None, "baseFrom": how, "rows": [], "note": env_note}
    if not base:
        out["error"] = "publish.py 里读不到 PAGES_URL"
        return out
    # 先问 version.json（以后的包里都有，一次请求就够）；还没有就退回读线上那份 scale.json。
    # 退路必须留着：线上是 10-28 那一批，version.json 是今天才加的，直接依赖它等于页面此刻是空的。
    live_sc, live_msg, via = None, "", ""
    code, _, body = fetch("%s/version.json" % base, timeout=20)
    if code == 200:
        try:
            ver = json.loads(body.decode("utf-8"))
            out["livePackage"] = {"package": ver.get("package"), "gitHead": ver.get("gitHead"),
                                  "builtAt": ver.get("builtAt"), "files": ver.get("files"),
                                  "fileManifestSha256": (ver.get("fileManifestSha256") or "")[:16]}
            live_sc = {"scale": {"dataVersions": ver.get("dataVersions") or []}}
            live_msg, via = "从 version.json 读到的", "version.json"
        except Exception as e:
            live_msg = "version.json 解析失败：%s" % str(e)[:60]
    else:
        via = "data/scale.json（线上还没有 version.json，退回逐文件比）"
    if live_sc is None:
        live_sc, live_msg = web_live_scale(base)
    out["via"] = via
    local_sc = {}
    try:
        local_sc = json.load(io.open(os.path.join(DATA, "scale.json"), encoding="utf-8")).get("scale") or {}
    except Exception:
        pass
    out["scaleLive"] = live_msg
    # 线上发布时间用 scale.json 的 Last-Modified 说话，比猜包号老实
    code, head, _ = fetch("%s/data/scale.json" % base, timeout=12, method="HEAD")
    out["liveModified"] = (head.get("last-modified") if code == 200 else None)
    # scale.json 的逐板块版本表在 "scale" 这一层里面，直接从文档根取会拿到空表
    # （第一版就是这么读的，结果线上核对日整列显示"—"，看着像"线上什么都没记"，其实是我读错了键）
    lv = {r.get("section"): r for r in (((live_sc or {}).get("scale") or {}).get("dataVersions") or [])}
    lcv = {r.get("section"): r for r in (local_sc.get("dataVersions") or [])}
    for section in sorted(set(lv) | set(lcv)):
        a, b = lv.get(section) or {}, lcv.get(section) or {}
        d1, d2 = a.get("checkedAt"), b.get("checkedAt")
        out["rows"].append({
            "section": section, "file": (b.get("file") if b else a.get("file")),
            "liveDate": d1, "localDate": d2,
            "liveDays": a.get("daysSince"), "localDays": b.get("daysSince"),
            "behind": (d1 != d2) if (d1 or d2) else None,
            "liveBuild": a.get("build"), "localBuild": b.get("build")})
    # 板块成品文件级的尺寸/哈希对账。
    # 并发跑：这台机器到 Pages 单请求常拖到超时，串行三十个文件要十来分钟（第一版就是这么死的）。
    # 线程只是把等待叠起来，判据一条没改：仍然先 HEAD 比尺寸、同尺寸才取全文比哈希。
    files = [f for f in sorted(os.listdir(DATA)) if f.endswith(".json")
             and f not in ("scale.json", "search.json")]      # 派生索引类，逐板块那层已经比过日期
    jobs = [(name, local_stat(os.path.join(DATA, name))) for name in files]
    with ThreadPoolExecutor(max_workers=8) as pool:
        got = list(pool.map(lambda nv: dict(web_row(base, nv[0], nv[1]), file=nv[0]), jobs))
    out.setdefault("files", []).extend(got)
    states = [r["state"] for r in out.get("files", [])]
    out["summary"] = {"一致": states.count("一致"),
                      "不同": sum(1 for s in states if s and s.startswith("不同")),
                      "线上没有": sum(1 for s in states if s == "线上没有这个文件"),
                      "读不到": sum(1 for s in states if s and s.startswith("读不到"))}
    return out


# ────────────────────────────── 小程序线 ──────────────────────────────
def mini_report(env):
    out = {"env": env, "rows": []}
    root = os.path.join(MINI_BUILD, env)
    local_p = os.path.join(root, "manifest.json")
    if not os.path.isfile(local_p):
        out["error"] = "本地没有 %s 批次（先跑 node tools/oss-release.js build --env %s）" % (env, env)
        return out
    local = json.load(io.open(local_p, encoding="utf-8"))
    out["local"] = {"buildId": local.get("buildId"), "files": (local.get("counts") or {}).get("files"),
                    # 批次是"哪一刻构建的"必须写出来：这一批不是 app/data 的实时投影，
                    # 别人（或上一次手工）跑过 build 之后它就变了。11-02 实测：同一个下午本地批次
                    # 从 0ab256f5cf02 换成了 d3e222b74dc1，对账数字跟着动，不说时间就像在骗人。
                    "builtAt": datetime.datetime.fromtimestamp(os.path.getmtime(local_p)).strftime("%Y-%m-%d %H:%M")}
    newest = max([(os.path.getmtime(os.path.join(DATA, f)), f) for f in os.listdir(DATA)
                  if f.endswith(".json")] or [(0, "")])
    out["dataNewerThanBatch"] = newest[0] > os.path.getmtime(local_p)
    out["newestDataFile"] = "%s（%s）" % (newest[1], datetime.datetime.fromtimestamp(newest[0]).strftime("%m-%d %H:%M"))
    origin, how = oss_config(env)
    out["oss"] = how
    if not origin:
        out["error"] = how
        return out
    code, _, body = fetch("%s/manifest.json" % origin, timeout=25)
    if code == 404:
        out["live"] = None
        out["error"] = "线上还没有指针（这一环境第一次发）"
        return out
    if code != 200:
        out["error"] = "线上指针读不到（HTTP %s）" % code
        return out
    live = json.loads(body.decode("utf-8"))
    out["live"] = {"buildId": live.get("buildId"), "files": (live.get("counts") or {}).get("files"),
                   "bundle": (live.get("bundle") or {}).get("path")}
    out["sameBatch"] = (out["live"]["buildId"] == out["local"]["buildId"])

    def bundle_of(doc):
        path = (doc.get("bundle") or {}).get("path")
        if not path:
            return None
        if os.path.isfile(os.path.join(MINI_BUILD, env, path)):          # 本地批次：直接读盘
            return json.load(io.open(os.path.join(MINI_BUILD, env, path), encoding="utf-8")).get("files") or {}
        code2, _, body2 = fetch("%s/%s" % (origin, path), timeout=40)    # 线上批次：匿名 GET
        return json.loads(body2.decode("utf-8")).get("files") or {} if code2 == 200 else None
    lf, rf = bundle_of(local), bundle_of(live)
    if rf is None:
        out["error"] = "线上那一批的 files.json 读不到，只能比到批次号这一层"
        return out
    for key in sorted(set(lf or {}) | set(rf)):
        a, b = (rf or {}).get(key), (lf or {}).get(key)
        # 这一层不比 SHA-256：每一批的产物里都嵌着自己那个 buildId（实测：线上/本地同一键
        # 唯一不同的就是 "buildId" 那一行，141 个键逐字节全不同），比哈希等于比"是不是同一批"，
        # 那是批次号那一层已经说过的事。这里只比**实质**：条数变了没、字节变了没——两份清单里都有，
        # 一个文件都不用下载。
        ra, rb = (a or {}).get("records"), (b or {}).get("records")
        ba, bb = (a or {}).get("bytes"), (b or {}).get("bytes")
        if a is None:
            state = "线上还没有这个键（本地新增）"
        elif b is None:
            state = "本地已撤（线上还留着）"
        elif ra is not None and rb is not None and ra != rb:
            state = "条数变了（线上 %s → 本地 %s）" % (ra, rb)
        elif ba != bb:
            # 状态词别和上面那条共用前缀：页面与汇总都按前缀筛"条数变了"，
            # 写成"条数没变、字节变了"会被一起捞进去（第一版就捞进 68 行，表头却写着"条数真的变了的键"）
            state = "字节变了、条数相同"
        else:
            state = "看着一样（只差批次号那一行）"
        out["rows"].append({"key": key, "path": (b or a or {}).get("path"), "state": state,
                            "liveBytes": ba, "localBytes": bb, "liveRecords": ra, "localRecords": rb})
    st = [r["state"] for r in out["rows"]]
    out["summary"] = {}
    for label in ("看着一样（只差批次号那一行）", "字节变了、条数相同",
                  "线上还没有这个键（本地新增）", "本地已撤（线上还留着）"):
        n = st.count(label)
        if n:
            out["summary"][label] = n
    out["summary"]["条数变了的键"] = sum(1 for s in st if s.startswith("条数变了"))
    return out


# ─────────────────────────────── 输出 ───────────────────────────────
def markdown(rep, day, heading=True):
    L = []
    if heading:                                 # 嵌进日报时别再带一个 H2，日报自己已经有节标题了
        L.append("## 本地 vs 线上对账（`tools/reconcile.py` 现读，只读不改任何东西）")
        L.append("")
    w = rep.get("web") or {}
    pkg = (w.get("livePackage") or {})
    L.append("- 网页线（%s）：%s" % (w.get("base") or "读不到地址",
               "线上包 **%s**（提交 %s · %s 打包）" % (pkg.get("package") or "—", pkg.get("gitHead") or "—",
                                            pkg.get("builtAt") or "—") if pkg else
               "线上还没有 %s，这一版是从数据文件本身读回来的（%s）" % ("version.json", w.get("scaleLive") or "—")))
    if pkg:
        L.append("  - 线上那份数据的文件时间：**%s**" % (w.get("liveModified") or "读不到"))
    else:
        L.append("  - 线上那份数据的文件时间：**%s**（下次打包起会带 `version.json`，那时一次请求就够）"
                 % (w.get("liveModified") or "读不到"))
    s = w.get("summary") or {}
    if s:
        L.append("  - 成品文件逐个数：一致 %s · 不同 %s · 线上还没有 %s · 读不到 %s（读不到≠一致，这台机到 Pages 常抖）"
                 % (s.get("一致"), s.get("不同"), s.get("线上没有"), s.get("读不到")))
    behind = [r for r in (w.get("rows") or []) if r.get("behind")]
    if behind:
        L.append("  - 核对日已经不一致的板块（线上还停在旧日期的就是这一批）：")
        L.append("")
        L.append("    | 板块 | 线上核对日 | 本地核对日 | 线上客户端 | 本地客户端 |")
        L.append("    | --- | --- | --- | --- | --- |")
        for r in behind:
            L.append("    | %s | %s | %s | %s | %s |" % (r["section"], r.get("liveDate") or "—",
                     r.get("localDate") or "—", r.get("liveBuild") or "—", r.get("localBuild") or "—"))
    else:
        L.append("  - 核对日逐板块都对得上（线上就是本地这一版）")
    m = rep.get("mini") or {}
    L.append("- 小程序线（%s 环境 · %s）：本地批次 `%s`（%s 个文件 · %s 构建） vs 线上指针 `%s`（%s 个文件）→ %s"
             % (m.get("env"), m.get("oss"), (m.get("local") or {}).get("buildId") or "—",
                (m.get("local") or {}).get("files") or "—", (m.get("local") or {}).get("builtAt") or "?",
                (m.get("live") or {}).get("buildId") or "—",
                (m.get("live") or {}).get("files") or "—",
                "同一批" if m.get("sameBatch") else "**不是同一批**"))
    if m.get("dataNewerThanBatch"):
        L.append("  - **注意**：`app/data` 比这一批本地构建更新（最新的是 %s）——这一批不是当前数据的快照，"
                 "要发得先重跑 `node tools/oss-release.js build --env %s` 再比一次。"
                 % (m.get("newestDataFile"), m.get("env") or "beta"))
    if m.get("summary"):
        ms = m["summary"]
        L.append("  - 逐键：%s" % " · ".join("%s %d" % (k, v) for k, v in ms.items() if v))
    if m.get("error"):
        L.append("  - 说明：%s" % m["error"])
    L.append("")
    L.append("> 这一节只回答\"差没差\"，不代站主决定发不发：发批次要显式点头，见 `docs/OPS-oss-分发层-poe方案落地-2026-10-21.md`。")
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="beta", help="小程序环境 beta|release")
    ap.add_argument("--json", help="把结果写成 JSON（给工作台的 /api/reconcile 与日报用）")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    day = datetime.date.today().isoformat()
    rep = {"generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
           "web": web_report(), "mini": mini_report(a.env)}
    if a.json:
        io.open(a.json, "w", encoding="utf-8").write(json.dumps(rep, ensure_ascii=False, indent=1) + "\n")
    if not a.quiet:
        print("\n".join(markdown(rep, day)))
    # 对账是报告不是门禁：取不到只写"读不到"，绝不因此把日更链拦红
    return 0


if __name__ == "__main__":
    sys.exit(main())
