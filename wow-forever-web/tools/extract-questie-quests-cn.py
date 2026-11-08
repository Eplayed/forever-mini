#!/usr/bin/env python3
# 从 QuestieDB_Forever.toc（baked TOC 元数据存储）抽 questID → 任务名，并抽白云飞漏译补丁。
#
# 为什么是 TOC（2026-11-08 开库实测）：QuestieDB 1.0.12 起主数据不是 lua 表而是
# 「baked 模式」——全部实体以 Base64+zlib+CBOR 存在 .toc 的 ## X-* 元数据行里
# （src/read/baked.lua 的 getStored 读 GetAddOnMetadata，就是读 TOC 注释行）。
#   X-Quest-IDS(-N)            任务 ID 总表（zlib CBOR int 数组，升序）
#   X-l10n-zhCN-Quest(-N)      zhCN 翻译列块（zlib CBOR，列主序：1=任务名，8=目标文本；
#                              列内元素与 IDS 按位对齐——src/l10n/overlay.lua 的 provider）
#   X-Quest-<id>-S             单条任务的 Scalar 行（Base64 CBOR map，key=字段号，
#                              1=英文名；主行全英文，中文只在 l10n 块）
#
# 边界（与历次插件源同款，2026-11-08 站主拍板“白云飞整合数据侧可用”）：
#   取的是 任务ID、任务英文名、任务zhCN名、白云飞补丁的同层条目、白云飞 NPC 名 24 条——全是名称层。
#   一律不取：QuestObjectives.lua 的 749 条目标正文（成段句子，贴“描述文案”红线，本轮范围没批）、
#             QuestXP 经验表（站主未选）、任何攻略正文、Object/Item 的无关字段。
#   白云飞补丁与主库列块对同一 ID 都有且串不同时：两个都留（分歧都留），生效值按运行时
#   overlay 的覆盖顺序记为补丁值（l10n.SetCorrection 盖过 baked 列块）。
#
# 用法：python3 tools/extract-questie-quests-cn.py [--src <AddOns 目录>] [--show]
#       --show 只打印结构与对拍，不落盘。
import base64
import datetime
import hashlib
import io
import json
import os
import re
import struct
import sys
import zlib

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(WEB, "app", "data", "upstream")
DB_ADDON = "QuestieDB"
CN_ADDON = "BaiYunFeiQuestieCN"

from addons_root import resolve, explain


# ---------- 精简 CBOR 解码（RFC 8949 子集：int/bytes/utf8/array/map/tag/simple/float） ----------
class CBOR:
    def __init__(self, b):
        self.b, self.i = b, 0

    def _u8(self):
        v = self.b[self.i]
        self.i += 1
        return v

    def _take(self, n):
        v = self.b[self.i:self.i + n]
        self.i += n
        return v

    def _arg(self, ai):
        if ai < 24:
            return ai
        if ai == 24:
            return self._u8()
        if ai == 25:
            return int.from_bytes(self._take(2), "big")
        if ai == 26:
            return int.from_bytes(self._take(4), "big")
        if ai == 27:
            return int.from_bytes(self._take(8), "big")
        raise ValueError("CBOR 长参数 %d 不在快照预期内" % ai)

    def _half(self, raw):
        sign = raw >> 15 & 1
        exp = raw >> 10 & 0x1F
        frac = raw & 0x3FF
        if exp == 0:
            v = frac * 2.0 ** -24
        elif exp == 31:
            v = float("inf") if frac == 0 else float("nan")
        else:
            v = (frac + 1024) * 2.0 ** (exp - 25)
        return -v if sign else v

    def item(self):
        ib = self._u8()
        mt, ai = ib >> 5, ib & 0x1F
        if mt == 0:
            return self._arg(ai)
        if mt == 1:
            return -1 - self._arg(ai)
        if mt in (2, 3):
            if ai == 31:
                out = b"" if mt == 2 else ""
                while True:
                    h = self._u8()
                    if h == 0xFF:
                        return out
                    part = self.item() if (h >> 5) == mt else None
                    out = (out + part) if mt == 2 else (out + part)
                return out
            n = self._arg(ai)
            raw = self._take(n)
            return raw if mt == 2 else raw.decode("utf-8")
        if mt == 4:
            if ai == 31:
                arr = []
                while self.b[self.i] != 0xFF:
                    arr.append(self.item())
                self.i += 1
                return arr
            return [self.item() for _ in range(self._arg(ai))]
        if mt == 5:
            m = {}
            if ai == 31:
                while self.b[self.i] != 0xFF:
                    k = self.item()
                    m[k] = self.item()
                self.i += 1
            else:
                for _ in range(self._arg(ai)):
                    k = self.item()
                    m[k] = self.item()
            return m
        if mt == 6:  # tag：快照里没预期到，跳过标签解原值
            self._arg(ai)
            return self.item()
        if ai == 20:
            return False
        if ai == 21:
            return True
        if ai in (22, 23):
            return None
        if ai == 25:
            return self._half(int.from_bytes(self._take(2), "big"))
        if ai == 26:
            return struct.unpack(">f", self._take(4))[0]
        if ai == 27:
            return struct.unpack(">d", self._take(8))[0]
        raise ValueError("CBOR simple %d 不在快照预期内" % ai)


def cbor(b):
    d = CBOR(b)
    v = d.item()
    if d.i != len(b):
        raise ValueError("CBOR 尾部多余 %d 字节" % (len(b) - d.i))
    return v


def zcbor(b64_text):
    """baked 列块与 IDS 的固定解码链：Base64 → zlib → CBOR。"""
    return cbor(zlib.decompress(base64.b64decode(b64_text)))


# ---------- 白云飞 Locale：ns.TBL[id] = "..."（\ddd 十进制转义为主，实测混有未转义字面字符） ----------
ROW_RE = re.compile(r'ns\.(\w+)\[(\d+)\]\s*=\s*"(.*)"\s*$')


def unescape_mixed(raw):
    r"""\ddd 十进制转义解一个字节；实测有 5 行混着字面 , / 74A / XL 这类没转义的 ASCII，按字面并入。"""
    out = bytearray()
    i = 0
    while i < len(raw):
        if raw[i] == "\\" and i + 1 < len(raw) and raw[i + 1].isdigit():
            j, num = i + 1, ""
            while j < len(raw) and raw[j].isdigit() and len(num) < 3:
                num += raw[j]
                j += 1
            out.append(int(num))
            i = j
        else:
            out.extend(raw[i].encode("utf-8"))
            i += 1
    return out.decode("utf-8")


def parse_locale(path, tables):
    """tables: {lua表名: 'scalar'} → {表名: {id: 值}}。"""
    out = {t: {} for t in tables}
    for line in io.open(path, encoding="utf-8", errors="strict"):
        m = ROW_RE.match(line.strip())
        if m and m.group(1) in tables:
            out[m.group(1)][int(m.group(2))] = unescape_mixed(m.group(3))
    return out, sum(len(v) for v in out.values())


def addon_version(addon_dir, addon):
    p = os.path.join(addon_dir, addon + ".toc")
    if not os.path.exists(p):
        return "版本未记"
    for line in io.open(p, encoding="utf-8", errors="ignore"):
        m = re.match(r"\s*##\s*Version:\s*(\S+)", line)
        if m:
            return m.group(1)
    return "版本未记"


def resolve_src():
    for i, a in enumerate(sys.argv):
        if a == "--src":
            return sys.argv[i + 1]
    root = resolve(DB_ADDON)
    if os.path.isdir(os.path.join(root, DB_ADDON)):
        return root
    sys.exit("找不到 %s。给 --src <AddOns 目录>，或设 WOW_ADDONS。\n%s" % (DB_ADDON, explain()))


def main():
    src = resolve_src()
    toc_path = os.path.join(src, DB_ADDON, "QuestieDB_Forever.toc")
    if not os.path.exists(toc_path):
        sys.exit("找不到 %s" % toc_path)
    qn_path = os.path.join(src, CN_ADDON, "Locale", "QuestNames.lua")
    npc_path = os.path.join(src, CN_ADDON, "Locale", "NpcNames.lua")

    # ---- 流式扫 TOC：15.5 MB 一次读完，只留需要的行 ----
    ids_parts, zh_parts = {}, {}
    scalar_en = {}
    toc_version = "版本未记"
    toc_bytes = 0
    with io.open(toc_path, "rb") as f:
        raw = f.read()
    toc_bytes = len(raw)
    for line in raw.split(b"\n"):
        if not line.startswith(b"## "):
            continue
        t = line[3:].decode("utf-8", errors="replace")
        if t.startswith("Version:"):
            toc_version = t.split(":", 1)[1].strip()
        elif t.startswith("X-Quest-IDS"):
            m = re.match(r"X-Quest-IDS(?:-(\d+))?: (.+)$", t)
            # 块头行的值是 "~16~" 这种分块计数，不是数据，跳过（'16' 是 base64 字母表字符，混进去毁对齐）
            if m and not m.group(2).startswith("~"):
                ids_parts[int(m.group(1) or 0)] = m.group(2)
        elif t.startswith("X-l10n-zhCN-Quest"):
            m = re.match(r"X-l10n-zhCN-Quest(?:-(\d+))?: (.+)$", t)
            if m and not m.group(2).startswith("~"):
                zh_parts[int(m.group(1) or 0)] = m.group(2)
        else:
            m = re.match(r"X-Quest-(\d+)-S: (.+)$", t)
            if m:
                row = cbor(base64.b64decode(m.group(2).strip()))
                # 两种行形态（实测）：dict{字段号:值} 或 list[b'REUSE ME' 标记, f1, f2, ...]
                if isinstance(row, dict):
                    name = row.get(1)
                elif isinstance(row, list) and len(row) > 1:
                    name = row[1]
                else:
                    name = None
                if isinstance(name, bytes):
                    name = name.decode("utf-8")
                if isinstance(name, str):
                    scalar_en[int(m.group(1))] = name

    ids = zcbor("".join(v for _, v in sorted(ids_parts.items())))
    if not isinstance(ids, list):
        sys.exit("X-Quest-IDS 解出来不是数组（拿到 %s）" % type(ids).__name__)

    zh_block = zcbor("".join(v for _, v in sorted(zh_parts.items())))
    # 实测是数组形态：[任务名列, objectivesText 列]（列内与 IDS 按位对齐）
    if not isinstance(zh_block, list) or not zh_block:
        sys.exit("zhCN 列块解出来不是数组（拿到 %s）" % type(zh_block).__name__)
    name_col = zh_block[0]
    if not isinstance(name_col, list):
        sys.exit("zhCN 列块第一列（任务名列）不是数组（拿到 %s）" % type(name_col).__name__)
    if len(name_col) != len(ids):
        sys.exit("zhCN 名字列长度 %d 与 ID 表长度 %d 不齐——对位关系破了，不许猜" % (len(name_col), len(ids)))

    def as_text(v):
        return v.decode("utf-8") if isinstance(v, bytes) else v

    cn_by_id = {qid: as_text(name_col[pos]) for pos, qid in enumerate(ids)
                if isinstance(name_col[pos], (str, bytes))}

    # ---- 白云飞补丁层 ----
    patches, npc_patch = {}, {}
    n_rows = 0
    if os.path.exists(qn_path):
        parsed, n_rows = parse_locale(qn_path, {"QUEST_NAMES": "scalar"})
        patches = parsed["QUEST_NAMES"]
    if os.path.exists(npc_path):
        parsed, n_npc = parse_locale(npc_path, {"NPC_NAMES": "scalar"})
        npc_patch = parsed["NPC_NAMES"]

    # ---- 组装：列块为底，补丁覆盖（分歧两个都留） ----
    agree = diff = patch_only = 0
    quests = []
    for qid in sorted(set(ids) | set(patches)):
        en = scalar_en.get(qid)
        cn_block = cn_by_id.get(qid)
        cn_patch = patches.get(qid)
        if cn_patch is not None and cn_block is not None and cn_patch != cn_block:
            diff += 1
            quests.append({"id": qid, "en": en, "cn": cn_patch, "cnVia": "baiyunfei-patch",
                           "cnBlock": cn_block})
        elif cn_patch is not None:
            agree += 1
            quests.append({"id": qid, "en": en, "cn": cn_patch, "cnVia": "baiyunfei-patch"})
        elif cn_block is not None:
            patch_only += 0  # 占位；真实计数在 else 分支外统一算
            quests.append({"id": qid, "en": en, "cn": cn_block, "cnVia": "questie-zhCN-column"})
        else:
            quests.append({"id": qid, "en": en, "cn": None, "cnVia": None})
    via_block = sum(1 for q in quests if q["cnVia"] == "questie-zhCN-column")
    unnamed = sum(1 for q in quests if q["cn"] is None)
    patch_total = sum(1 for q in quests if q["cnVia"] == "baiyunfei-patch")

    # ---- 与本站副本任务对拍（dungeon-quests.json 只有 nameEn/nameCn，按英文名桥） ----
    dq_path = os.path.join(WEB, "app", "data", "dungeon-quests.json")
    our_quests = []
    if os.path.exists(dq_path):
        dq = json.loads(io.open(dq_path, encoding="utf-8").read())
        for _d, body in sorted((dq.get("dungeons") or {}).items()):
            for q in body.get("quests") or []:
                our_quests.append(q)
    en_index = {}
    for q in quests:
        if q["en"] and q["cn"]:
            en_index.setdefault(q["en"].casefold(), q)
    same = differ = missing_en = 0
    diff_rows = []
    for q in our_quests:
        en = (q.get("nameEn") or "").strip()
        cn = (q.get("nameCn") or "").strip()
        hit = en_index.get(en.casefold())
        if not hit:
            missing_en += 1  # 英文名在快照里没有：只计数（两源英文名写法可能不同），不猜
            continue
        if not cn:
            continue
        if hit["cn"] == cn:
            same += 1
        else:
            differ += 1
            if len(diff_rows) < 25:
                diff_rows.append({"nameEn": en, "ourCn": cn, "questieCn": hit["cn"],
                                  "via": hit["cnVia"]})

    counts = {
        "questIds": len(ids),
        "rowsWithCn": len(quests) - unnamed,
        "rowsWithoutCn": unnamed,
        "cnFromZhCNColumn": via_block,
        "cnFromBaiyunfeiPatch": patch_total,
        "patchAgreesWithColumn": agree,
        "patchDiffersFromColumn": diff,
        "baiyunfeiPatchRows": len(patches),
        "baiyunfeiNpcPatchRows": len(npc_patch),
        "scalarEnglishNames": len(scalar_en),
        "ourDungeonQuests": len(our_quests),
        "ourEnNotInSnapshot": missing_en,
        "ourCnMatched": same,
        "ourCnDiffer": differ,
    }

    print("QuestieDB Forever TOC：%d 字节，Version %s" % (toc_bytes, toc_version))
    print("任务 ID %d 个；有中文名 %d（列块 %d + 补丁 %d，其中补丁与列块一致 %d、分歧 %d）；无中文名 %d"
          % (counts["questIds"], counts["rowsWithCn"], via_block, patch_total, agree, diff, unnamed))
    print("白云飞补丁原文件 %d 行（QuestNames）/ %d 行（NpcNames）" % (len(patches), len(npc_patch)))
    print("与本站副本任务对拍（按英文名桥）：本站 %d 条，英文名对上快照 %d（一致 %d、分歧 %d）、对不上 %d"
          % (counts["ourDungeonQuests"], same + differ, same, differ, missing_en))
    for r in diff_rows:
        print("  分歧 %-28s 本站「%s」/ 快照「%s」(%s)" % (r["nameEn"][:28], r["ourCn"], r["questieCn"], r["via"]))

    if "--show" in sys.argv:
        return

    b = raw
    snap = {
        "meta": {
            "source": "%s（QuestieDB %s，baked TOC metadata store）+ %s %s Locale/QuestNames.lua、NpcNames.lua"
                      % (DB_ADDON, toc_version, CN_ADDON, addon_version(src, CN_ADDON)),
            "addon": DB_ADDON,
            "addonVersion": toc_version,
            "sourceFile": "QuestieDB/QuestieDB_Forever.toc + BaiYunFeiQuestieCN/Locale/{QuestNames,NpcNames}.lua",
            "sourceStamp": {"bytes": toc_bytes, "sha256": hashlib.sha256(b).hexdigest(),
                            "fileDate": datetime.datetime.fromtimestamp(
                                os.path.getmtime(toc_path)).strftime("%Y-%m-%d")},
            "fetched": datetime.date.today().isoformat(),
            "took": "任务ID、任务英文名（Scalar 行字段1）、任务zhCN名（l10n 列块列1 + 白云飞757条补丁）、"
                    "白云飞 NPC 名 24 条（npcNames）。分歧时 cn=补丁值（运行时 overlay 生效序），cnBlock=列块原值",
            "droppedFields": ["l10n 列块列 8 objectivesText 与白云飞 QuestObjectives.lua 的 749 条目标正文"
                              "（成段句子，贴「描述文案」红线，2026-11-08 开采范围没批）",
                              "QuestXP 经验表（站主未选）",
                              "Scalar 行除字段 1 外的全部字段（等级/目标/奖励等，本轮只要名字层）"],
            "boundary": "主库 zhCN 列块是国服客户端串的插件转述（baked 进 TOC）；白云飞补丁自述只补列块漏译。"
                        "两者都按名称层事实标识符取；快照不进成品，要不要接进 dungeon-quests 由合并层决定。",
            "decode": "## X-* 行 → Base64 → zlib → CBOR（tools/extract-questie-quests-cn.py 内置解码器）",
            "aliasNote": "zhCN 列块与 IDS 按位对齐（overlay.lua 的 provider 二分），脚本已断言长度一致",
            "counts": counts,
            "reconOurCnDiff": diff_rows,
        },
        "npcNames": [{"npcId": k, "nameCn": v} for k, v in sorted(npc_patch.items())],
        "quests": quests,
    }
    if not os.path.isdir(UP):
        os.makedirs(UP)
    p = os.path.join(UP, "questie-quests-cn.json")
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("写 %s（%.1f KB）" % (os.path.relpath(p, WEB), os.path.getsize(p) / 1024.0))


if __name__ == "__main__":
    main()
