# -*- coding: utf-8 -*-
"""插件原件根目录（Interface/AddOns）在哪——所有 extract-* 抽取器共用这一份判断。

为什么要有这个文件：以前每个脚本各自写死 `~/Documents/project/.scratch/wow`，
那是 Mac 那台的工作副本。2026-11-01 站主定「Mac 不再做，全部在这台 Windows」，
插件实际装在 `C:\\GAME\\World of Warcraft\\_cn_beta_\\Interface\\AddOns`，
那些默认值一个个变成"找不到源"或者更糟——静默拿到旧副本。顺序写在这里，别再散着抄。

用法（在抽取器里）：
    from addons_root import resolve
    DEF_SRC = resolve('GearInsight_Forever')

resolve() 不会因为目录不存在就退出：命令行工具的 --help 不该被机器环境打断。
真要跑的时候各脚本自己那句"找不到源文件"会拦住，路径是看得懂的。
"""
import os

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # …/wow-forever-web
REPO_PARENT = os.path.dirname(os.path.dirname(WEB))                     # …/project 或 …
HOME = os.path.expanduser("~")

# 谁在这台机器上就先用谁：环境变量 → 本机两个安装位 → Mac 的两份工作副本
CANDIDATES = [
    os.environ.get("WOW_ADDONS") or "",
    "C:/GAME/World of Warcraft/_cn_beta_/Interface/AddOns",
    "C:/GAME/World of Warcraft/_forever_/Interface/AddOns",
    os.path.join(HOME, "Documents", "project", ".scratch", "wow"),
    os.path.join(REPO_PARENT, ".scratch", "wow"),
    os.path.join(REPO_PARENT, ".scratch", "wow-client-2026-10-21"),
]


def candidates():
    seen, out = set(), []
    for c in CANDIDATES:
        if c and c not in seen and os.path.isdir(c):
            seen.add(c)
            out.append(c)
    return out


def resolve(addon=None):
    """返回第一个存在的插件根；给了 addon 就必须真装着那个插件才算命中。
       一个都没有时返回第一个候选（哪怕不存在），让调用方的报错里出现一个有意义的路径。"""
    for c in candidates():
        if addon is None or os.path.isdir(os.path.join(c, addon)):
            return c
    return next((c for c in CANDIDATES if c), "(没有可用的插件目录)")


def explain():
    """给 daily 用：把"找过哪些地方、哪些真存在"讲清楚，别让人猜为什么拿不到源。"""
    have = candidates()
    lines = ["插件根解析：命中 %s" % (have[0] if have else "无")]
    for c in CANDIDATES:
        if not c:
            continue
        lines.append("  %s  %s" % ("存在" if os.path.isdir(c) else "不存在", c))
    return "\n".join(lines)


# ---- 客户端导出（listfile / db2）：跟插件不在同一层，也不该写死某台机器的挂载位 ----
EXPORT_CANDIDATES = [
    os.environ.get("WOW_EXPORT") or "",
    "C:/GAME/World of Warcraft/ziliao-export",     # 这台 Windows 的现役导出
    "/tmp/wow-ro/ziliao-export",                   # Mac 那台曾经的只读挂载位
]


def export_root():
    for c in EXPORT_CANDIDATES:
        if c and os.path.isdir(c):
            return c
    return EXPORT_CANDIDATES[1]


def listfile_csv():
    return os.path.join(export_root(), "listfile", "client-fdid-name.csv")


def source_ref(p, base=None):
    """快照里记的源文件路径。跨盘时 os.path.relpath 会抛 ValueError
       （2026-11-02 实测：gi-item-existence / xr-boss-model / addon-bis 三个抽取器崩在这行），
       这里退回「插件名/文件名」——既不把某台机器的绝对路径写进全线共用的数据，也不炸。"""
    try:
        return os.path.relpath(p, base) if base else os.path.relpath(p)
    except ValueError:
        parts = [x for x in os.path.abspath(p).replace("\\", "/").split("/") if x and ":" not in x]
        if "AddOns" in parts:
            return "/".join(parts[parts.index("AddOns") + 1:])
        return os.path.basename(p)



if __name__ == "__main__":
    print(explain())
