#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""界面回归与抓取用的浏览器：默认 Chrome，可用环境变量 `WOW_BROWSER_CHANNEL` 临时换（如 msedge）。

为什么要有这个开关（2026-11-02）：这台机器的 Chrome 被一次没跑完的自动更新弄坏了——
启动器的清单指向 156.0.8078.48，而那个目录只落了 7 个文件，于是新起的进程全被系统拒绝
（事件日志写的是 SideBySide「找不到程序集」，playwright 那边转述成 `spawn UNKNOWN`）。
`site-check` 是本站**唯一**的界面闸，不能因为浏览器坏了就让整条日更链停摆。

换浏览器**不等于没有代价**，所以这里把代价写死在话里：
  · Edge 与 Chrome 是不同的 Chromium 版本（本机 Edge 142 vs Chrome 156），
    渲染与部分 API 行为可能有差别，这一轮的"通过"只代表那个浏览器；
  · 所以每个用到浏览器的脚本都要把 `banner()` 打出来，日报也要照抄一行，
    别让"701/701"这种数字脱离它是在哪跑出来的。
默认值没变：不设这个环境变量，一切照旧走 Chrome。
"""
import os

DEFAULT = "chrome"
ENV = "WOW_BROWSER_CHANNEL"


def channel():
    return (os.environ.get(ENV) or "").strip() or DEFAULT


def is_default():
    return channel() == DEFAULT


def _system_chrome_missing():
    """系统 Chrome 找不找得到：只查 Linux 侧（WSL）。Windows 侧 channel=chrome 一直由
       playwright 自己找注册表/Program Files，别在这猜——猜错反而把好端端的 Windows 跑法改坏。"""
    import shutil
    return shutil.which("google-chrome") is None and shutil.which("google-chrome-stable") is None


def using_bundled():
    """真跑的时候用的是不是 playwright 自带 chromium（WSL 里没有系统 Chrome 时的回退）。"""
    import sys
    return sys.platform.startswith("linux") and channel() == DEFAULT and _system_chrome_missing()


def banner():
    """给人看的一行：谁在跑这一轮界面回归。换过浏览器时这句话必须显眼。"""
    c = channel()
    if using_bundled():
        return ("浏览器 playwright 自带 chromium（WSL 里没有系统 Chrome，%s 缺席的回退；"
                "渲染行为可能与 Windows 侧的 Chrome 有差别）" % DEFAULT)
    if is_default():
        return "浏览器 %s（默认）" % c
    return ("浏览器 %s（由 %s 指定，**不是 Chrome**：这一轮的界面结论只代表 %s，"
            "Chrome 修好后要再跑一次才算 Chrome 的数）" % (c, ENV, c))


def launch(pw, **kw):
    """统一入口：channel 与 headless 只在这一处定，别每个脚本各抄一份。"""
    kw.setdefault("headless", True)
    if using_bundled():
        return pw.chromium.launch(**kw)
    return pw.chromium.launch(channel=channel(), **kw)
