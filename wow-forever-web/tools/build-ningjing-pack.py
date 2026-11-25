#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build-ningjing-pack.py — 「宁静之光」对标双皮肤图文包与公众号内联 HTML 渲染引擎

支持两套核心视觉皮肤 + 同源双壳输出（一次渲染，同时产出「小绿书/头条 3:4 翻页图包」+「公众号内联 HTML 长图文」）：
1. theme="grimoire"（无限冒险笔记 · 复古皮质古书封面 + 做旧羊皮纸手账风）：
   - 直接从 wow-forever 真源数据（dungeons.json / dungeon-quests.json / dungeon-geo.json /
     items.json / items-detail.json / bis.json）自动组装任意副本的任务路线、前置火漆印章、
     中文区域入口坐标图 + 副本内部首领点位图、无限服新增套装与特殊掉落属性胶囊卡、常见问答 FAQ。
2. theme="frosted-daily"（无限服日报 · 暗调毛玻璃信息卡 + 双色语义高亮公众号长文）：
   - 1 张主题原画高斯模糊压暗作为全局统一毛玻璃底板；
   - 支持 5 类模块化组件：kpi（三列数字看板）、stat_change（属性/机制改动箭头盒+高清图标列表）、
     pill_table（区域/分类胶囊标签表）、timeline（纵向彩色节点时间线+核心大数字）、
     compare / faq（双栏对比暗盒 / 悬念清单）；
   - 同源双壳：
     * carousel 模式（1080x1440 3:4）：带顶栏（栏目名+日期）、双行海报大标题、底栏（页码+来源）；
     * wechat 内嵌模式（1080x自适应高）：自动剥离顶栏、重复大标题与底栏页码，只渲染核心毛玻璃盒，
       并生成零 SVG/Table 冗余的微信 ProseMirror 兼容内联 HTML（定性暗金 #A7803A / 定量橙红 #C0612B
       双色语义高亮 + 44x3px 短横线小标题 + 金线四行总结 + 资料来源 + 跑本无限助手引导尾卡 + 一键复制工具栏）。

用法：
  python wow-forever-web/tools/build-ningjing-pack.py --mode all
  python wow-forever-web/tools/build-ningjing-pack.py --mode dungeon --dungeon deathmine
  python wow-forever-web/tools/build-ningjing-pack.py --mode dungeon --dungeon hall-of-thanes
  python wow-forever-web/tools/build-ningjing-pack.py --mode daily --preset hotfix-1117
"""
from __future__ import annotations

import argparse
import base64
import html as html_lib
import json
import os
import pathlib
import re
import shutil
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def _find_app_root() -> pathlib.Path:
    """自动定位 wow-forever-web/app 目录（兼容 Windows 仓库与 MacBook 仓库布局）。"""
    here = pathlib.Path(__file__).resolve()
    candidates = [
        here.parents[1] / "app",
        here.parents[2] / "wow-forever-web" / "app",
        pathlib.Path.home() / "Documents/project/wow-forever/wow-forever-web/app",
        pathlib.Path(r"D:/project/forever/wow-forever-web/app"),
    ]
    for c in candidates:
        if (c / "data" / "dungeons.json").is_file():
            return c
    raise FileNotFoundError("未找到 wow-forever-web/app/data/dungeons.json")


def _esc(text: Any) -> str:
    return html_lib.escape(str(text or ""))


def _file_uri(path: Optional[pathlib.Path]) -> str:
    if not path or not path.is_file():
        return ""
    return path.resolve().as_uri()


def _format_semantic_prose(text: str, accent_qual: str = "#A7803A",
                           accent_num: str = "#C0612B",
                           accent_blue: str = "#1D7FB8") -> str:
    """将正文中的语义标记转换为公众号内联样式的 <strong>：
    - **定性重点** -> 暗金色 (#A7803A)
    - !!定量数字!! -> 赤陶橙红 (#C0612B)
    - @@等级/蓝色节点@@ -> 湛蓝色 (#1D7FB8)
    若 **...** 内本身以数字/百分比/金币开头，也自动归入定量橙红。
    """
    escaped = _esc(text)

    def _repl_bold(m: re.Match) -> str:
        inner = m.group(1)
        if re.search(r"^[\d约第]+|[0-9]+\s*(?:金|银|铜|级|%|人|名|个|只|件|天|小时|秒|点)", inner):
            color = accent_num
        else:
            color = accent_qual
        return (f'<strong style="color: {color}; font-weight: 700;">'
                f'{inner}</strong>')

    escaped = re.sub(
        r"!!(.+?)!!",
        lambda m: f'<strong style="color: {accent_num}; font-weight: 700;">{m.group(1)}</strong>',
        escaped,
    )
    escaped = re.sub(
        r"@@(.+?)@@",
        lambda m: f'<strong style="color: {accent_blue}; font-weight: 700;">{m.group(1)}</strong>',
        escaped,
    )
    escaped = re.sub(r"\*\*(.+?)\*\*", _repl_bold, escaped)
    return escaped


def _wow_quality_color(quality: Any) -> str:
    q = str(quality or "").strip()
    if q in ("精良", "蓝", "rare", "3", "3.0"):
        return "#4DA6FF"
    if q in ("优秀", "绿", "uncommon", "2", "2.0"):
        return "#2CE862"
    if q in ("史诗", "紫", "epic", "4", "4.0"):
        return "#C678FF"
    if q in ("传说", "橙", "legendary", "5", "5.0"):
        return "#FF8C1A"
    if q in ("粗糙", "灰", "poor", "0", "0.0"):
        return "#9D9D9D"
    return "#FFFFFF"


def _render_wechat_inline_tooltip(it: Dict[str, Any]) -> str:
    """渲染 100% 兼容微信公众号富文本编辑器的游戏内物品属性框（无 flex/grid）。"""
    qc = _esc(it.get("quality_color") or _wow_quality_color(it.get("quality")))
    name = _esc(it.get("name") or "未知物品")
    q_txt = _esc(it.get("quality") or "")
    ilvl = _esc(it.get("ilvl") or "")
    iid = _esc(it.get("id") or "")
    head_meta = " · ".join(x for x in (
        f"{q_txt}" if q_txt else "",
        f"物品等级 {ilvl}" if ilvl else "",
        f"ID {iid}" if iid else "",
    ) if x)
    tags = [x for x in (
        it.get("bind"),
        it.get("unique"),
        it.get("slot_type"),
        it.get("req_level"),
    ) if x]
    lines: List[str] = [
        f'<section style="margin: 12px 0; padding: 14px 16px; '
        f'background-color: rgb(22, 26, 35); border-radius: 8px; '
        f'border: 1px solid rgba(255, 255, 255, 0.14); border-left: 4px solid {qc};">',
        f'<p style="font-family: \'PingFang SC\', \'Microsoft YaHei\', sans-serif; '
        f'font-size: 16px; font-weight: 700; color: {qc}; margin: 0 0 4px; line-height: 1.4;">'
        f'{name}'
        + (f' <span style="font-size: 12px; font-weight: 500; color: rgb(168, 162, 152);">（{head_meta}）</span>' if head_meta else '')
        + '</p>',
    ]
    if tags:
        lines.append(
            f'<p style="font-family: \'PingFang SC\', \'Microsoft YaHei\', sans-serif; '
            f'font-size: 13px; color: rgb(226, 222, 214); margin: 0 0 6px; line-height: 1.5;">'
            f'{_esc(" · ".join(str(t) for t in tags))}</p>'
        )
    for st in it.get("stats") or []:
        if str(st).strip():
            lines.append(
                f'<p style="font-family: \'PingFang SC\', \'Microsoft YaHei\', sans-serif; '
                f'font-size: 14px; color: rgb(245, 245, 245); margin: 0 0 4px; line-height: 1.5;">'
                f'{_esc(st)}</p>'
            )
    for ul in it.get("use_lines") or []:
        if str(ul).strip():
            lines.append(
                f'<p style="font-family: \'PingFang SC\', \'Microsoft YaHei\', sans-serif; '
                f'font-size: 14px; font-weight: 600; color: rgb(62, 232, 108); margin: 0 0 5px; line-height: 1.55;">'
                f'{_esc(ul)}</p>'
            )
    if it.get("flavor"):
        lines.append(
            f'<p style="font-family: \'PingFang SC\', \'Microsoft YaHei\', sans-serif; '
            f'font-size: 13px; color: rgb(242, 201, 100); margin: 2px 0 4px; line-height: 1.5;">'
            f'{_esc(it["flavor"])}</p>'
        )
    foot_parts = [str(x) for x in (it.get("source"), it.get("meta_right")) if x]
    if foot_parts:
        lines.append(
            f'<p style="font-family: \'PingFang SC\', \'Microsoft YaHei\', sans-serif; '
            f'font-size: 12px; color: rgb(156, 150, 140); margin: 4px 0 0; line-height: 1.45;">'
            f'{_esc(" ｜ ".join(foot_parts))}</p>'
        )
    lines.append("</section>")
    return "".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# 一、WeChat 公众号内联 HTML 编译器（100% 复刻「宁静之光」DOM 规范 + 一键复制工具栏）
# ═══════════════════════════════════════════════════════════════════════════

def render_talent_panels_section_html(
    talent_builds: List[Dict[str, Any]],
    *,
    h_color: str = "rgb(46, 31, 61)",
    qual_color: str = "rgb(167, 128, 58)",
) -> str:
    """渲染已校验通过的天赋模拟器 .tpanel 实图板块（兼容公众号与动态替换）。"""
    verified = [b for b in (talent_builds or []) if b.get("status") == "verified" and b.get("panel_img_rel")]
    if not verified:
        return ""
    blocks: List[str] = [
        '<!-- TALENT_PANELS_START -->',
        f'<section style="margin: 36px 0 16px;">'
        f'<p style="font-family: \'PingFang SC\', \'Microsoft YaHei\', sans-serif; '
        f'font-size: 21px; line-height: 1.45; letter-spacing: 0.5px; '
        f'color: {h_color}; font-weight: 700; margin: 0;">推荐天赋加点（模拟器实图）</p>'
        f'<section style="width: 44px; height: 3px; background-color: {h_color}; margin-top: 10px;"></section>'
        f'</section>',
    ]
    for b in verified:
        cls_cn = _esc(b.get("class_cn") or b.get("class_id") or "")
        sum_txt = _esc(b.get("summary_text") or "")
        p_code = _esc(b.get("p_code") or "")
        img_rel = _esc(b.get("panel_img_rel") or "")
        kt = "、".join(_esc(x) for x in (b.get("key_talents") or [])[:5])
        blocks.append(
            f'<p style="font-family: \'PingFang SC\', \'Microsoft YaHei\', sans-serif; '
            f'font-size: 16px; line-height: 1.8; color: rgb(43, 43, 43); margin: 0 0 10px;">'
            f'<strong style="color: {qual_color}; font-weight: 700;">{cls_cn}</strong>：'
            f'{sum_txt}'
            + (f'；关键深层天赋：{kt}' if kt else '')
            + '。</p>'
        )
        blocks.append(
            f'<section style="margin: 12px 0 14px; text-align: center;">'
            f'<img src="{img_rel}" style="width: 100%; max-width: 1080px; '
            f'border-radius: 8px; display: block; margin: 0 auto;" '
            f'alt="{cls_cn}天赋加点示意图" />'
            f'</section>'
        )
        if p_code:
            blocks.append(
                f'<p style="font-family: \'PingFang SC\', \'Microsoft YaHei\', sans-serif; '
                f'font-size: 12.5px; line-height: 1.65; color: rgb(122, 116, 102); '
                f'margin: 0 0 22px; text-align: center;">模拟器加点代码：<code>?c={_esc(b.get("class_id"))}&amp;p={p_code}</code></p>'
            )
    blocks.append(
        '<p style="font-family: \'PingFang SC\', \'Microsoft YaHei\', sans-serif; '
        'font-size: 13.5px; line-height: 1.75; color: rgb(122, 116, 102); margin: 0 0 18px;">'
        '注：以上天赋图基于视频实机画面于「跑本无限助手」天赋模拟器校验还原并截取加点面板，过路点可根据自身装备与升级习惯微调。</p>'
    )
    blocks.append('<!-- TALENT_PANELS_END -->')
    return "".join(blocks)


def compile_wechat_article_html(
    *,
    title: str,
    column_name: str,
    date_str: str,
    lead_text: str,
    hero_img_rel: str,
    header_banner_rel: str,
    footer_banner_rel: str,
    sections: List[Dict[str, Any]],
    closing_lines: List[str],
    footnote: str,
    sources: List[str],
    theme_palette: Optional[Dict[str, str]] = None,
    talent_builds: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """生成可直接粘贴进微信公众号后台的内联 HTML（带本地浏览器一键复制悬浮栏）。"""
    pal = theme_palette or {}
    h_color = pal.get("heading", "rgb(46, 31, 61)")       # #2E1F3D 深紫炭色
    qual_color = pal.get("qual", "rgb(167, 128, 58)")     # #A7803A 暗金（定性）
    num_color = pal.get("num", "rgb(192, 97, 43)")        # #C0612B 赤陶红（定量）
    blue_color = pal.get("blue", "rgb(29, 127, 184)")     # #1D7FB8 湛蓝
    rule_color = pal.get("rule", "rgb(201, 164, 92)")     # #C9A45C 金线

    body_p_style = (
        "font-family: 'PingFang SC', 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif; "
        "font-size: 16px; line-height: 1.85; letter-spacing: 0.5px; "
        "color: rgb(43, 43, 43); margin: 0 0 18px; text-align: justify;"
    )

    nodes: List[str] = []

    # 1. 顶部栏目横幅
    if header_banner_rel:
        nodes.append(
            f'<section style="margin: 0 0 18px; text-align: center;">'
            f'<img src="{_esc(header_banner_rel)}" style="width: 100%; max-width: 1080px; '
            f'display: block; margin: 0 auto;" alt="栏目横幅" />'
            f'</section>'
        )

    # 2. 主封面插画
    if hero_img_rel:
        nodes.append(
            f'<section style="margin: 0 0 24px; text-align: center;">'
            f'<img src="{_esc(hero_img_rel)}" style="width: 100%; max-width: 1080px; '
            f'border-radius: 8px; display: block; margin: 0 auto; '
            f'box-shadow: 0 6px 20px rgba(0,0,0,0.08);" alt="封面主图" />'
            f'</section>'
        )

    # 3. 顶部金线导语块
    if lead_text:
        formatted_lead = _format_semantic_prose(lead_text, qual_color, num_color, blue_color)
        nodes.append(
            f'<section style="margin: 22px 0 28px; padding: 3px 0 3px 14px; '
            f'border-left: 3px solid {qual_color};">'
            f'<p style="font-family: \'PingFang SC\', \'Microsoft YaHei\', sans-serif; '
            f'font-size: 16px; line-height: 1.8; letter-spacing: 0.5px; '
            f'color: {h_color}; font-weight: 700; margin: 0;">{formatted_lead}</p>'
            f'</section>'
        )

    # 4. 各分节（小标题 + 44x3px 短横线 + 2~3 段短正文 + 1080px 去头尾内嵌图卡）
    for sec in sections:
        sec_title = sec.get("title") or ""
        if sec_title:
            title_html = "<br/>".join(_esc(line) for line in sec_title.split("\n") if line.strip())
            nodes.append(
                f'<section style="margin: 36px 0 16px;">'
                f'<p style="font-family: \'PingFang SC\', \'Microsoft YaHei\', sans-serif; '
                f'font-size: 21px; line-height: 1.45; letter-spacing: 0.5px; '
                f'color: {h_color}; font-weight: 700; margin: 0;">{title_html}</p>'
                f'<section style="width: 44px; height: 3px; background-color: {h_color}; '
                f'margin-top: 10px;"></section>'
                f'</section>'
            )
        for para in sec.get("paragraphs") or []:
            if not str(para).strip():
                continue
            p_html = _format_semantic_prose(str(para), qual_color, num_color, blue_color)
            nodes.append(f'<p style="{body_p_style}">{p_html}</p>')

        card_rel = sec.get("card_img_rel") or ""
        if not card_rel:
            for it in sec.get("item_tooltips") or []:
                nodes.append(_render_wechat_inline_tooltip(it))
        else:
            nodes.append(
                f'<section style="margin: 20px 0 30px; text-align: center;">'
                f'<img src="{_esc(card_rel)}" style="width: 100%; max-width: 1080px; '
                f'border-radius: 8px; display: block; margin: 0 auto;" '
                f'alt="{_esc(sec_title)}" />'
                f'</section>'
            )

    # 4b. 已校验通过的天赋模拟器 .tpanel 容器实图板块（仅当视频/工坊传入 verified build 时出现）
    tp_html = render_talent_panels_section_html(talent_builds or [], h_color=h_color, qual_color=qual_color)
    if tp_html:
        nodes.append(tp_html)
    else:
        nodes.append('<!-- TALENT_PANELS_START --><!-- TALENT_PANELS_END -->')

    # 5. 结尾居中金线四行总结
    if closing_lines:
        c_html = "<br/>".join(_esc(line) for line in closing_lines)
        nodes.append(
            f'<section style="margin: 40px 0 32px; text-align: center;">'
            f'<section style="width: 36px; height: 2px; background-color: {rule_color}; '
            f'margin: 0 auto 18px;"></section>'
            f'<p style="font-family: \'PingFang SC\', \'Microsoft YaHei\', sans-serif; '
            f'font-size: 16px; line-height: 2.0; letter-spacing: 0.8px; '
            f'color: {h_color}; font-weight: 700; margin: 0;">{c_html}</p>'
            f'<section style="width: 36px; height: 2px; background-color: {rule_color}; '
            f'margin: 18px auto 0;"></section>'
            f'</section>'
        )

    # 6. 附注与资料来源
    if footnote:
        nodes.append(
            f'<p style="font-family: \'PingFang SC\', \'Microsoft YaHei\', sans-serif; '
            f'font-size: 14px; line-height: 1.75; color: rgb(122, 116, 102); '
            f'margin: 24px 0 18px;">{_esc(footnote)}</p>'
        )

    if sources:
        src_items = "".join(
            f'<p style="font-family: \'PingFang SC\', \'Microsoft YaHei\', sans-serif; '
            f'font-size: 12.5px; line-height: 1.75; color: rgb(138, 132, 120); '
            f'margin: 0 0 4px;">{_esc(s)}</p>'
            for s in sources
        )
        nodes.append(
            f'<section style="margin: 22px 0 28px; padding-top: 18px; '
            f'border-top: 1px solid rgb(227, 221, 208);">'
            f'<p style="font-family: \'PingFang SC\', \'Microsoft YaHei\', sans-serif; '
            f'font-size: 13px; line-height: 1.6; color: rgb(90, 84, 72); '
            f'font-weight: 700; margin: 0 0 8px;">资料与数据核对来源</p>'
            f'{src_items}'
            f'</section>'
        )

    # 7. 栏目签名 + 引导尾卡
    nodes.append(
        f'<p style="font-family: \'PingFang SC\', \'Microsoft YaHei\', sans-serif; '
        f'font-size: 13px; line-height: 1.6; color: {qual_color}; font-weight: 700; '
        f'text-align: center; letter-spacing: 1px; margin: 28px 0 16px;">'
        f'跑本无限助手 · paoben.top ｜ {_esc(column_name)}</p>'
    )
    if footer_banner_rel:
        nodes.append(
            f'<section style="margin: 0 0 12px; text-align: center;">'
            f'<img src="{_esc(footer_banner_rel)}" style="width: 100%; max-width: 1080px; '
            f'display: block; margin: 0 auto; border-radius: 6px;" alt="尾卡" />'
            f'</section>'
        )

    js_content_inner = "\n".join(nodes)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{_esc(title)}</title>
<style>
  body {{
    margin: 0;
    padding: 72px 16px 60px;
    background: #F4F1EA;
    font-family: "PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
    color: #2B2B2B;
  }}
  .toolbar {{
    position: fixed;
    top: 0; left: 0; right: 0;
    height: 56px;
    background: #1F1924;
    color: #F5EBD6;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.25);
    z-index: 9999;
  }}
  .toolbar .meta {{
    font-size: 14px;
    color: #D4C5A8;
  }}
  .toolbar .meta strong {{
    color: #F3C969;
  }}
  .toolbar .btns {{
    display: flex;
    gap: 12px;
  }}
  .toolbar button {{
    background: linear-gradient(180deg, #E2B857, #B88A28);
    color: #1A120B;
    border: none;
    padding: 8px 18px;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
  }}
  .toolbar button:hover {{
    filter: brightness(1.08);
  }}
  .page-shell {{
    max-width: 677px;
    margin: 0 auto;
    background: #FFFFFF;
    padding: 36px 28px 48px;
    border-radius: 10px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.06);
  }}
  .wx-title {{
    font-size: 22px;
    line-height: 1.4;
    font-weight: 700;
    color: #191919;
    margin: 0 0 10px;
  }}
  .wx-byline {{
    font-size: 13px;
    color: #888888;
    margin: 0 0 24px;
    display: flex;
    gap: 10px;
    align-items: center;
  }}
  .wx-tag {{
    background: #F2F2F2;
    color: #666666;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 12px;
  }}
</style>
</head>
<body>
  <div class="toolbar">
    <div class="meta">
      <strong>跑本无限助手 · 公众号内联排版预览</strong> ｜ 栏目：{_esc(column_name)}（{_esc(date_str)}）
    </div>
    <div class="btns">
      <button onclick="pushWechatDraft()" id="pushDraftBtn" style="background:linear-gradient(180deg,#2EA043,#1E7E34);color:#FFFFFF;">🚀 推送到公众号草稿箱</button>
      <button onclick="copyWechatRichText()" id="copyBtn">📋 复制正文排版</button>
    </div>
  </div>
  <div class="page-shell">
    <h1 class="wx-title">{_esc(title)}</h1>
    <div class="wx-byline">
      <span class="wx-tag">原创</span>
      <span>跑本无限助手</span>
      <span style="color:#576B95;">{_esc(column_name)}</span>
      <span>{_esc(date_str)}</span>
    </div>
    <div id="js_content" class="rich_media_content autoTypeSetting24psection">
<!-- WECHAT_BODY_START -->
{js_content_inner}
<!-- WECHAT_BODY_END -->
    </div>
  </div>
<script>
async function pushWechatDraft() {{
  const btn = document.getElementById('pushDraftBtn');
  if (location.protocol === 'file:') {{
    alert('请通过 MacBook 工作台 http://127.0.0.1:15801/ningjing 打开本页后再点推送，本地 file:// 无法访问后台接口。');
    return;
  }}
  btn.disabled = true;
  btn.textContent = '⏳ 正在上传8张图片并推送草稿箱...';
  try {{
    const mNing = location.pathname.match(/\\/media\\/ningjing\\/([^/]+)\\//);
    const mPost = location.pathname.match(/\\/media\\/poster\\/([^/]+)\\//);
    const body = mNing ? {{pack_id: mNing[1]}} : mPost ? {{poster_id: mPost[1]}} : {{}};
    const res = await fetch('/api/ningjing/push_wechat_draft', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(body)
    }});
    const data = await res.json();
    if (!data.ok) {{
      alert('推送失败：' + (data.error || '未知错误'));
      btn.textContent = '❌ 推送失败（点击重试）';
    }} else {{
      btn.textContent = '✅ 已推送公众号草稿箱！';
      alert('推送成功！请登录微信公众平台（mp.weixin.qq.com）->「草稿箱」查看并发布。\\nmedia_id: ' + (data.media_id || ''));
    }}
  }} catch (e) {{
    alert('请求异常：' + e.message);
    btn.textContent = '❌ 推送失败（点击重试）';
  }} finally {{
    btn.disabled = false;
  }}
}}
function copyWechatRichText() {{
  const el = document.getElementById('js_content');
  const range = document.createRange();
  range.selectNodeContents(el);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);
  try {{
    document.execCommand('copy');
    const btn = document.getElementById('copyBtn');
    btn.textContent = '✅ 已复制内联排版！请前往公众号后台 Ctrl+V';
    setTimeout(() => {{
      btn.textContent = '📋 一键复制公众号正文（直接粘贴微信后台）';
    }}, 3500);
  }} catch (e) {{
    alert('复制失败，请手动选中正文复制: ' + e);
  }}
  sel.removeAllRanges();
}}
</script>
</body>
</html>
"""


def compile_carousel_preview_html(
    *,
    pack_id: str,
    title: str,
    column_name: str,
    date_str: str,
    caption_text: str,
    slides: List[str],
    media_prefix: str = "",
    zip_url: str = "",
    article_url: str = "../wechat/article.html",
    back_url: str = "",
) -> str:
    """生成小绿书 / 头条号 / 小红书 图文配文与 3:4 轮播图全览页（带一键复制与打包下载）。"""
    clean_cap = (caption_text or "").strip()
    tags = re.findall(r"#[^\s#]+", clean_cap)
    tags_html = "".join(
        f'<span class="tag-chip">{_esc(t)}</span>' for t in tags
    ) or '<span style="color:#8F877A;font-size:13px;">（暂无话题标签）</span>'

    slide_cards = []
    for idx, s in enumerate(slides, 1):
        # s 可能是 "carousel/slide_01.png" 或 "slide_01.png"
        fname = pathlib.Path(s).name
        img_src = f"{media_prefix}{fname}" if media_prefix else fname
        slide_cards.append(
            f'<div class="slide-card">'
            f'<a href="{_esc(img_src)}" target="_blank" rel="noopener">'
            f'<img src="{_esc(img_src)}" alt="P{idx}" loading="lazy" />'
            f'</a>'
            f'<div class="slide-foot">'
            f'<span>P{idx} · 1080×1440 (3:4)</span>'
            f'<a class="dl-one" href="{_esc(img_src)}" download="{_esc(pack_id)}_P{idx:02d}.png">⬇ 保存原图</a>'
            f'</div>'
            f'</div>'
        )

    zip_btn = (
        f'<a class="btn btn-green" href="{_esc(zip_url)}">📦 打包下载全套配图 (ZIP)</a>'
        if zip_url else ""
    )
    back_btn = (
        f'<a class="btn btn-dark" href="{_esc(back_url)}">← 返回工坊</a>'
        if back_url else ""
    )
    art_btn = (
        f'<a class="btn btn-dark" href="{_esc(article_url)}" target="_blank">👁 切换公众号长文</a>'
        if article_url else ""
    )
    raw_txt_url = f"{media_prefix}caption.txt" if media_prefix else "caption.txt"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{_esc(title)} · 小绿书/头条图文配文</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #141118;
    color: #EFE9DC;
    font-family: "PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
    padding: 0 0 64px;
  }}
  .toolbar {{
    position: sticky; top: 0; z-index: 99;
    background: #1C1722;
    border-bottom: 1px solid rgba(229,184,105,0.28);
    padding: 12px 24px;
    display: flex; align-items: center; justify-content: space-between;
    gap: 12px; flex-wrap: wrap;
    box-shadow: 0 6px 20px rgba(0,0,0,0.35);
  }}
  .tb-meta {{ font-size: 13.5px; color: #CBBF9F; }}
  .tb-meta strong {{ color: #F3C969; }}
  .tb-btns {{ display: flex; gap: 10px; flex-wrap: wrap; }}
  .btn {{
    display: inline-flex; align-items: center; gap: 6px;
    padding: 8px 15px; border-radius: 6px; border: none;
    font-size: 13.5px; font-weight: 700; cursor: pointer;
    text-decoration: none;
  }}
  .btn-gold {{ background: linear-gradient(180deg, #E5B85B, #B58728); color: #19120A; }}
  .btn-green {{ background: linear-gradient(180deg, #2EA043, #1E7E34); color: #FFFFFF; }}
  .btn-dark {{ background: #2A2333; color: #E5B869; border: 1px solid rgba(229,184,105,0.38); }}
  .wrap {{ max-width: 1120px; margin: 26px auto 0; padding: 0 24px; }}
  .panel {{
    background: #1D1824;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 22px;
  }}
  .panel-hdr {{
    display: flex; align-items: center; justify-content: space-between;
    gap: 12px; flex-wrap: wrap; margin-bottom: 12px;
  }}
  .panel-title {{ font-size: 15.5px; font-weight: 800; color: #F3C969; }}
  .title-box {{
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
    background: #120F16; border: 1px solid rgba(229,184,105,0.28);
    border-radius: 8px; padding: 12px 16px; flex-wrap: wrap;
  }}
  .title-text {{ font-size: 18px; font-weight: 800; color: #FFFFFF; }}
  .count-badge {{
    font-size: 12px; color: #A8A093;
    background: rgba(255,255,255,0.06); padding: 2px 10px; border-radius: 999px;
  }}
  textarea.cap-editor {{
    width: 100%; min-height: 140px; resize: vertical;
    background: #120F16; color: #EFE9DC;
    border: 1px solid rgba(255,255,255,0.14); border-radius: 8px;
    padding: 14px 16px; font-size: 15px; line-height: 1.7;
    font-family: inherit;
  }}
  .tags-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; align-items: center; }}
  .tag-chip {{
    font-size: 12.5px; font-weight: 700; color: #F3C969;
    background: rgba(229,184,105,0.14); border: 1px solid rgba(229,184,105,0.34);
    padding: 3px 10px; border-radius: 999px;
  }}
  .slides-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
    gap: 18px;
  }}
  .slide-card {{
    background: #120F16; border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px; padding: 10px; overflow: hidden;
  }}
  .slide-card img {{ width: 100%; display: block; border-radius: 6px; }}
  .slide-foot {{
    display: flex; align-items: center; justify-content: space-between;
    margin-top: 10px; font-size: 12.5px; color: #A8A093;
  }}
  .dl-one {{ color: #E5B869; text-decoration: none; font-weight: 700; }}
  .dl-one:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
  <div class="toolbar">
    <div class="tb-meta">
      <strong>跑本无限助手 · 小绿书 / 头条号图文配文</strong> ｜ 栏目：{_esc(column_name)}（{_esc(date_str)}） ｜ 共 {len(slides)} 张 3:4 配图
    </div>
    <div class="tb-btns">
      {back_btn}
      {art_btn}
      {zip_btn}
      <button class="btn btn-gold" id="copyCapBtn" onclick="copyText('capBox', this, '📋 一键复制完整配文')">📋 一键复制完整配文</button>
    </div>
  </div>
  <div class="wrap">
    <div class="panel">
      <div class="panel-hdr">
        <span class="panel-title">📌 推荐标题（小绿书 / 头条号 / 小红书）</span>
        <span class="count-badge">{len(title)} 字</span>
      </div>
      <div class="title-box">
        <span class="title-text" id="titleTxt">{_esc(title)}</span>
        <button class="btn btn-dark" onclick="copyPlain(document.getElementById('titleTxt').textContent, this, '📋 复制标题')">📋 复制标题</button>
      </div>
    </div>

    <div class="panel">
      <div class="panel-hdr">
        <span class="panel-title">📝 配文正文与话题标签（可直接微调后复制发布）</span>
        <div style="display:flex;gap:10px;align-items:center;">
          <span class="count-badge" id="capLen">{len(clean_cap)} 字</span>
          <a class="dl-one" href="{_esc(raw_txt_url)}" target="_blank">查看纯文本 caption.txt</a>
        </div>
      </div>
      <textarea class="cap-editor" id="capBox" oninput="document.getElementById('capLen').textContent=this.value.length+' 字'">{_esc(clean_cap)}</textarea>
      <div class="tags-row">
        <span style="font-size:12.5px;color:#A8A093;">话题标签：</span>
        {tags_html}
      </div>
    </div>

    <div class="panel">
      <div class="panel-hdr">
        <span class="panel-title">🖼️ 全套 3:4 轮播配图（点击放大，按 P1→P{len(slides)} 顺序上传）</span>
        {zip_btn}
      </div>
      <div class="slides-grid">{"".join(slide_cards)}</div>
    </div>
  </div>
<script>
async function copyPlain(txt, btn, resetLabel) {{
  try {{
    await navigator.clipboard.writeText(txt);
    btn.textContent = '✅ 已复制';
    setTimeout(() => {{ btn.textContent = resetLabel; }}, 2200);
  }} catch (_e) {{
    const ta = document.createElement('textarea');
    ta.value = txt;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    ta.remove();
    btn.textContent = '✅ 已复制';
    setTimeout(() => {{ btn.textContent = resetLabel; }}, 2200);
  }}
}}
function copyText(elId, btn, resetLabel) {{
  const el = document.getElementById(elId);
  copyPlain(el ? el.value : '', btn, resetLabel);
}}
</script>
</body>
</html>
"""


# ═══════════════════════════════════════════════════════════════════════════
# 二、首尾栏目横幅与尾卡 HTML 渲染（1080×120 栏目条 & 1080×392 暖米色尾卡）
# ═══════════════════════════════════════════════════════════════════════════

def build_header_banner_html(brand_name: str, column_name: str, emblem_uri: str) -> str:
    emblem_img = (
        f'<img src="{emblem_uri}" style="width:52px;height:52px;border-radius:12px;'
        f'object-fit:cover;border:1.5px solid #D5C4A1;box-shadow:0 2px 6px rgba(0,0,0,0.12);" />'
        if emblem_uri else
        '<div style="width:52px;height:52px;border-radius:12px;background:#2E1F3D;color:#F3C969;'
        'display:flex;align-items:center;justify-content:center;font-weight:900;font-size:24px;">✦</div>'
    )
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:1080px; height:120px; background:#FFFFFF;
       font-family:"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif; }}
.banner {{
  width:1080px; height:120px;
  border-top:1.5px solid #EAE4D7;
  border-bottom:1.5px solid #EAE4D7;
  display:flex; align-items:center; justify-content:center; gap:18px;
  background:#FFFFFF;
}}
.brand {{ font-size:32px; font-weight:800; color:#231F20; letter-spacing:1.5px; }}
.star {{ font-size:24px; color:#C5A059; }}
.col {{ font-size:32px; font-weight:700; color:#8C8275; letter-spacing:2px; }}
</style></head><body>
<div class="banner">
  {emblem_img}
  <span class="brand">{_esc(brand_name)}</span>
  <span class="star">✦</span>
  <span class="col">{_esc(column_name)}</span>
</div>
</body></html>"""


def _find_mini_qrcode_uri(app_root: Optional[pathlib.Path] = None) -> str:
    """定位本地留存的小程序太阳码（禁止外链），内联为 data URI 确保任意渲染模式可见。"""
    roots: List[pathlib.Path] = []
    if app_root:
        roots.append(app_root)
    try:
        roots.append(_find_app_root())
    except Exception:
        pass
    for r in roots:
        for rel, mime in (
            ("img/art/brand/mini-qrcode.jpg", "image/jpeg"),
            ("img/art/brand/mini-qrcode.png", "image/png"),
        ):
            p = r / rel
            if p.is_file():
                try:
                    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
                    return f"data:{mime};base64,{b64}"
                except Exception:
                    return _file_uri(p)
    return ""


def _resolve_web_domain() -> str:
    """读取营销配置里的网页端域名（默认 paoben.top）。"""
    for cfg in (
        pathlib.Path.home() / "Documents/project/video2text/config/marketing_hooks.json",
        pathlib.Path(__file__).resolve().parents[1] / "config/marketing_hooks.json",
    ):
        if cfg.is_file():
            try:
                doc = json.loads(cfg.read_text(encoding="utf-8"))
                dom = str(doc.get("brand_web") or "").strip()
                if dom:
                    return dom
            except Exception:
                pass
    return "paoben.top"


def build_footer_cta_html(
    brand_name: str,
    column_name: str,
    emblem_uri: str,
    qrcode_uri: str = "",
    web_domain: str = "",
) -> str:
    web_dom = (web_domain or _resolve_web_domain()).strip()
    if qrcode_uri:
        left_block = (
            '<div class="qr-card">'
            f'<img src="{qrcode_uri}" class="qr-img" alt="小程序码" />'
            '<div class="qr-cap">长按识别小程序码</div>'
            '</div>'
        )
        body_html = f"""
    <div class="eyebrow">手机小程序 · 电脑网页端 双端免费</div>
    <h2>谢谢你读到这里</h2>
    <p><span class="dark">手机端</span>：长按左侧码打开小程序 <strong>{_esc(brand_name)}</strong></p>
    <p><span class="dark">电脑端</span>：访问 <strong>{_esc(web_dom)}</strong>（查表 / 3D配装 / 团本）</p>
    <p>觉得有用点个<strong>赞与在看</strong>，设<strong>星标 ★</strong>不错过攻略</p>
    <div class="hint">微信搜「{_esc(brand_name)}」· 电脑开 {_esc(web_dom)}（同源校对）</div>"""
    else:
        left_block = (
            f'<img src="{emblem_uri}" style="width:168px;height:168px;border-radius:28px;'
            f'object-fit:cover;border:2px solid #D5C4A1;box-shadow:0 6px 18px rgba(0,0,0,0.12);" />'
            if emblem_uri else
            '<div style="width:168px;height:168px;border-radius:28px;background:#2E1F3D;color:#F3C969;'
            'display:flex;align-items:center;justify-content:center;font-weight:900;font-size:64px;">✦</div>'
        )
        body_html = f"""
    <div class="eyebrow">手机小程序 · 电脑网页端 双端免费</div>
    <h2>谢谢你读到这里</h2>
    <p><span class="dark">手机端</span>：微信搜小程序 <strong>{_esc(brand_name)}</strong></p>
    <p><span class="dark">电脑端</span>：访问 <strong>{_esc(web_dom)}</strong>（查表 / 3D配装 / 团本）</p>
    <p>觉得有用点个<strong>赞与在看</strong>，设<strong>星标 ★</strong>不错过攻略</p>
    <div class="hint">微信搜「{_esc(brand_name)}」· 电脑开 {_esc(web_dom)}（同源校对）</div>"""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:1080px; height:440px; background:#F3F1EC;
       font-family:"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif; }}
.cta {{
  width:1080px; height:440px; background:#F3F1EC;
  border:2px solid #E5D9C0; border-radius:16px;
  display:flex; align-items:center; justify-content:center; gap:44px;
  padding:32px 52px; position:relative;
}}
.qr-card {{
  flex:0 0 auto;
  background:#FFFFFF;
  padding:16px 16px 12px;
  border-radius:22px;
  border:1.5px solid #E2D5BA;
  box-shadow:0 8px 24px rgba(31,29,26,0.08);
  text-align:center;
}}
.qr-img {{
  width:244px; height:244px; display:block; object-fit:contain;
}}
.qr-cap {{
  margin-top:10px; font-size:19px; font-weight:700;
  color:#8C6B2A; letter-spacing:1.2px;
}}
.txt {{ flex:1; min-width:0; }}
.eyebrow {{
  display:inline-block;
  padding:5px 15px; border-radius:999px;
  background:#EAE2D0; color:#8C6B2A;
  font-size:19px; font-weight:700; letter-spacing:1px;
  margin-bottom:14px;
}}
.txt h2 {{
  font-family:"Songti SC","Noto Serif CJK SC","SimSun",serif;
  font-size:44px; font-weight:900; color:#1F1D1A; margin-bottom:16px; letter-spacing:2px;
}}
.txt p {{
  font-size:24px; line-height:1.78; color:#7A746B; font-weight:500; white-space:nowrap;
}}
.txt p strong {{ color:#A7803A; font-weight:700; }}
.txt p .dark {{ color:#2B2926; font-weight:600; }}
.txt .hint {{
  margin-top:16px; font-size:19px; color:#9A9285; letter-spacing:0.4px; white-space:nowrap;
}}
</style></head><body>
<div class="cta">
  {left_block}
  <div class="txt">{body_html}
  </div>
</div>
</body></html>"""


def _render_cover_icons_strip(cover_icons: List[Dict[str, Any]], *, size: int = 64) -> str:
    """将本篇真实装备/职业/技能图标渲染成精致的主题图标陈列条（供公众号封面与 3:4 首图共用）。"""
    items = [x for x in (cover_icons or []) if isinstance(x, dict) and x.get("icon_uri")][:6]
    if not items:
        return ""
    q_border = {
        "传说": "#FF8000", "史诗": "#B96CFF", "精良": "#4EA1E8",
        "优秀": "#4ADE80", "普通": "#C9BFA8",
    }
    chips: List[str] = []
    for it in items:
        bd = q_border.get(str(it.get("quality") or ""), "#D8B467")
        lbl = str(it.get("label") or "").strip()[:6]
        chips.append(
            f'<div class="cov-ic-item">'
            f'<div class="cov-ic-box" style="width:{size}px;height:{size}px;border-color:{bd};">'
            f'<img src="{it["icon_uri"]}" style="width:100%;height:100%;object-fit:cover;display:block;" />'
            f'</div>'
            + (f'<div class="cov-ic-lbl">{_esc(lbl)}</div>' if lbl else "")
            + f'</div>'
        )
    return f'<div class="cov-ic-strip">{"".join(chips)}</div>'


def build_wechat_hero_cover_html(
    *,
    bg_uri: str,
    column_name: str,
    date_str: str,
    kicker: str,
    title_line1: str,
    title_line2: str,
    subtitle: str,
    cover_icons: Optional[List[Dict[str, Any]]] = None,
    stat_badge: str = "",
    brand_name: str = "跑本无限助手",
) -> str:
    """渲染 1080×720 公众号主题封面图（视觉核心落在居中 2.35:1 安全带内，公众号信息流与文首双适配）。"""
    icons_html = _render_cover_icons_strip(cover_icons or [], size=64)
    badge_html = f'<span class="stat-pill">{_esc(stat_badge)}</span>' if stat_badge else ""
    h2_html = f'<div class="hero-h2">{_esc(title_line2)}</div>' if title_line2 else ""
    sub_html = f'<div class="hero-sub">{_esc(subtitle)}</div>' if subtitle else ""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  width:1080px; height:720px; overflow:hidden; background:#100D15;
  font-family:"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif; color:#FFFFFF;
}}
.wrap {{
  width:1080px; height:720px; position:relative; overflow:hidden;
  display:flex; align-items:center; padding:88px 68px;
}}
.bg {{
  position:absolute; inset:0;
  background-image:url("{bg_uri}");
  background-size:cover; background-position:center;
  transform:scale(1.03);
  z-index:0;
}}
.veil {{
  position:absolute; inset:0; z-index:1;
  background:
    linear-gradient(90deg, rgba(12,9,17,0.92) 0%, rgba(12,9,17,0.78) 54%, rgba(12,9,17,0.34) 100%),
    linear-gradient(180deg, rgba(12,9,17,0.52) 0%, rgba(12,9,17,0.10) 45%, rgba(12,9,17,0.76) 100%);
}}
.content {{
  position:relative; z-index:2; width:100%;
  display:flex; flex-direction:column; gap:18px;
}}
.pills {{ display:flex; align-items:center; gap:12px; flex-wrap:wrap; }}
.kicker {{
  display:inline-block; padding:7px 18px; border-radius:8px;
  background:linear-gradient(180deg,#EED089,#C99A3B); color:#1A1308;
  font-size:23px; font-weight:800; letter-spacing:1px;
  box-shadow:0 4px 14px rgba(0,0,0,0.45);
}}
.stat-pill {{
  display:inline-block; padding:6px 16px; border-radius:8px;
  background:rgba(28,22,38,0.82); color:#EED089;
  border:1.5px solid rgba(229,184,105,0.55);
  font-size:21px; font-weight:700;
}}
.title-box {{ margin-top:2px; }}
.hero-h1 {{
  font-size:66px; line-height:1.18; font-weight:900; color:#FFFFFF;
  letter-spacing:1.5px; text-shadow:0 4px 20px rgba(0,0,0,0.88);
}}
.hero-h2 {{
  font-size:66px; line-height:1.18; font-weight:900; color:#F2C86B;
  letter-spacing:1.5px; margin-top:4px;
  text-shadow:0 4px 20px rgba(0,0,0,0.88);
}}
.hero-sub {{
  font-size:27px; color:#DED7C9; font-weight:600; letter-spacing:0.6px;
  text-shadow:0 2px 10px rgba(0,0,0,0.85);
}}
.cov-ic-strip {{
  display:flex; align-items:flex-start; gap:16px; margin-top:8px;
}}
.cov-ic-item {{
  display:flex; flex-direction:column; align-items:center; gap:6px; width:82px;
}}
.cov-ic-box {{
  border-radius:12px; overflow:hidden; border:2.5px solid #D8B467;
  background:#15121A; box-shadow:0 6px 16px rgba(0,0,0,0.65);
}}
.cov-ic-lbl {{
  font-size:15px; font-weight:700; color:#EFE7D6; text-align:center;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:82px;
  text-shadow:0 2px 6px rgba(0,0,0,0.9);
}}
.top-brand {{
  position:absolute; top:28px; right:36px; z-index:3;
  padding:6px 16px; border-radius:999px;
  background:rgba(16,13,22,0.66); border:1px solid rgba(238,208,137,0.4);
  font-size:20px; font-weight:700; color:#F3D285; letter-spacing:1px;
}}
.wm {{
  position:absolute; right:34px; bottom:24px; z-index:3;
  font-size:20px; color:rgba(255,255,255,0.66);
  text-shadow:0 2px 8px rgba(0,0,0,0.85);
}}
</style></head><body>
<div class="wrap">
  <div class="bg"></div>
  <div class="veil"></div>
  <div class="top-brand">{_esc(column_name)} · {_esc(date_str)}</div>
  <div class="content">
    <div class="pills"><span class="kicker">{_esc(kicker)}</span>{badge_html}</div>
    <div class="title-box">
      <div class="hero-h1">{_esc(title_line1)}</div>
      {h2_html}
    </div>
    {sub_html}
    {icons_html}
  </div>
  <div class="wm">小程序：{_esc(brand_name)} · 网页：paoben.top</div>
</div>
</body></html>"""


# ═══════════════════════════════════════════════════════════════════════════
# 三、皮肤 A：theme="frosted-daily"（暗调毛玻璃日报 · 支持 3:4 轮播卡 & 1080px 去头尾内嵌卡）
# ═══════════════════════════════════════════════════════════════════════════

def build_frosted_card_html(
    card: Dict[str, Any],
    *,
    bg_uri: str,
    mode: str = "carousel",  # "carousel" (1080x1440 3:4) | "inline" (1080xauto)
    idx: int = 1,
    total: int = 1,
    column_name: str = "无限服日报",
    date_str: str = "11.19",
    source_label: str = "官方蓝帖与已核实测库",
    brand_name: str = "跑本无限助手",
) -> str:
    """渲染一张「宁静之光 · 魔兽无限日报」同款暗调毛玻璃信息卡。
    - mode="carousel"：1080x1440，含顶部栏目条、双行大标题、毛玻璃信息盒、底部页码与来源；
    - mode="inline"：1080x自适应高度，自动剥离顶栏、海报大标题与底栏页码，只渲染核心毛玻璃卡片，
      供公众号长文直接内嵌，与 HTML 小标题及正文零重复。
    """
    is_cover = card.get("kind") == "cover"
    accent = card.get("accent") or "#E5B869"

    # 构造卡片内部组件 HTML
    body_blocks: List[str] = []

    # 组件 1：顶部胶囊标签组 (pills)
    pills = card.get("pills") or []
    if pills:
        pills_html = "".join(f'<span class="pill">{_esc(p)}</span>' for p in pills)
        body_blocks.append(f'<div class="pill-row">{pills_html}</div>')

    # 组件 2：导语/顶部说明 (intro)
    if card.get("intro"):
        body_blocks.append(f'<p class="card-intro">{_esc(card["intro"])}</p>')

    # 组件 3：三列 KPI 数字看板 (kpis)
    kpis = card.get("kpis") or []
    if kpis:
        cols_html = "".join(
            f'<div class="kpi-col">'
            f'<div class="kpi-val" style="color:{_esc(k.get("color") or accent)}">{_esc(k.get("val"))}</div>'
            f'<div class="kpi-lbl">{_esc(k.get("label"))}</div>'
            f'</div>'
            for k in kpis
        )
        body_blocks.append(f'<div class="kpi-bar">{cols_html}</div>')

    # 组件 4：属性/机制改动箭头对比盒 (stat_change)
    sc = card.get("stat_change")
    if isinstance(sc, dict):
        body_blocks.append(
            f'<div class="stat-change-box">'
            f'<div class="sc-left">'
            f'<div class="sc-name">{_esc(sc.get("name"))}</div>'
            f'<div class="sc-sub">{_esc(sc.get("sub"))}</div>'
            f'</div>'
            f'<div class="sc-right">'
            f'<span class="sc-old">{_esc(sc.get("before"))}</span>'
            f'<span class="sc-arrow">→</span>'
            f'<span class="sc-new" style="color:{_esc(sc.get("after_color") or "#58A6FF")}">'
            f'{_esc(sc.get("after"))}</span>'
            f'</div>'
            f'</div>'
        )

    # 组件 5：超大号焦点数字 (hero_stat)
    hs = card.get("hero_stat")
    if isinstance(hs, dict):
        align_cls = "center" if hs.get("align") == "center" else "left"
        body_blocks.append(
            f'<div class="hero-stat {align_cls}">'
            f'<span class="hs-num" style="color:{_esc(hs.get("color") or "#4EA1E8")}">'
            f'{_esc(hs.get("num"))}</span>'
            f'<span class="hs-unit">{_esc(hs.get("unit"))}</span>'
            f'<div class="hs-desc">{_esc(hs.get("desc") or "")}</div>'
            f'</div>'
        )

    # 组件 6：横幅插画/截图条 (banner_uri)
    if card.get("banner_uri"):
        cap = f'<div class="shot-cap">{_esc(card["banner_caption"])}</div>' if card.get("banner_caption") else ""
        body_blocks.append(
            f'<div class="banner-box">'
            f'<img src="{card["banner_uri"]}" />'
            f'{cap}'
            f'</div>'
        )

    # 组件 7：纵向彩色圆环时间线 (timeline)
    tl = card.get("timeline") or []
    if tl:
        tl_rows = []
        for idx_t, node in enumerate(tl):
            c = node.get("color") or ("#E5B869" if idx_t == 0 else "#E05A47" if idx_t == 1 else "#4EA1E8")
            sub_html = f'<div class="tl-sub">{_esc(node.get("desc"))}</div>' if node.get("desc") else ""
            tl_rows.append(
                f'<div class="tl-item">'
                f'<div class="tl-dot" style="border-color:{_esc(c)};"></div>'
                f'<div class="tl-content">'
                f'<div class="tl-time" style="color:{_esc(c)};">{_esc(node.get("time"))}</div>'
                f'<div class="tl-title">{_esc(node.get("title"))}</div>'
                f'{sub_html}'
                f'</div>'
                f'</div>'
            )
        body_blocks.append(f'<div class="timeline-box">{"".join(tl_rows)}</div>')

    # 组件 8：带高清图标的技能/装备条目列表 (icon_rows)
    icon_rows = card.get("icon_rows") or []
    if icon_rows:
        sec_hdr = (
            f'<div class="sub-sec-title">{_esc(card["icon_section_title"])}</div>'
            if card.get("icon_section_title") else ""
        )
        ir_html = []
        for r in icon_rows:
            ic_uri = r.get("icon_uri") or ""
            ic_tag = (
                f'<img class="ir-icon" src="{ic_uri}" />'
                if ic_uri else
                f'<div class="ir-icon-fallback">{_esc((r.get("title") or "✦")[:1])}</div>'
            )
            badge_html = f'<span class="ir-badge">{_esc(r["badge"])}</span>' if r.get("badge") else ""
            ir_html.append(
                f'<div class="ir-row">'
                f'{ic_tag}'
                f'<div class="ir-txt">'
                f'<div class="ir-head">{_esc(r.get("title"))}{badge_html}</div>'
                f'<div class="ir-desc">{_esc(r.get("desc"))}</div>'
                f'</div>'
                f'</div>'
            )
        body_blocks.append(f'{sec_hdr}<div class="ir-list">{"".join(ir_html)}</div>')

    # 组件 9：区域/分类胶囊标签表 (pill_rows，对标 11.17 热修任务与世界表)
    pill_rows = card.get("pill_rows") or []
    if pill_rows:
        pr_html = []
        for r in pill_rows:
            tone = r.get("tone") or "brown"
            sub_html = f'<div class="pr-sub">{_esc(r.get("sub"))}</div>' if r.get("sub") else ""
            pr_html.append(
                f'<div class="pr-row">'
                f'<div class="pr-tag tone-{_esc(tone)}">{_esc(r.get("tag"))}</div>'
                f'<div class="pr-main">'
                f'<div class="pr-title">{_esc(r.get("title"))}</div>'
                f'{sub_html}'
                f'</div>'
                f'</div>'
            )
        body_blocks.append(f'<div class="pr-table">{"".join(pr_html)}</div>')

    # 组件 10：双栏对比暗盒 (compare_boxes，对标「他的说法 vs 被翻出的旧话」「联盟 vs 部落」)
    cmp_boxes = card.get("compare_boxes") or []
    if cmp_boxes:
        cb_html = "".join(
            f'<div class="cmp-col">'
            f'<div class="cmp-head" style="color:{_esc(b.get("color") or accent)}">{_esc(b.get("label"))}</div>'
            f'<div class="cmp-body">{_esc(b.get("text"))}</div>'
            f'</div>'
            for b in cmp_boxes
        )
        body_blocks.append(f'<div class="cmp-grid">{cb_html}</div>')

    # 组件 11：问号/要点行 (q_rows，对标「这笔账还剩几行没算」)
    q_rows = card.get("q_rows") or []
    if q_rows:
        qr_html = "".join(
            f'<div class="qr-row">'
            f'<div class="qr-sym">{_esc(q.get("symbol") or "?")}</div>'
            f'<div class="qr-txt">'
            f'<div class="qr-title">{_esc(q.get("title"))}</div>'
            f'<div class="qr-desc">{_esc(q.get("desc"))}</div>'
            f'</div>'
            f'</div>'
            for q in q_rows
        )
        body_blocks.append(f'<div class="qr-list">{"".join(qr_html)}</div>')

    # 组件 11b：游戏内物品属性 Tooltip 卡组 (item_tooltips)
    item_tooltips = card.get("item_tooltips") or []
    if item_tooltips:
        tt_html = []
        for it in item_tooltips:
            qc = _esc(it.get("quality_color") or _wow_quality_color(it.get("quality")))
            ic_uri = it.get("icon_uri") or ""
            ic_box = (
                f'<img class="tt-icon" style="border-color:{qc};" src="{ic_uri}" />'
                if ic_uri else
                f'<div class="tt-icon-fb" style="border-color:{qc};color:{qc};">{_esc((it.get("name") or "✦")[:1])}</div>'
            )
            ilvl_tag = f'装等 {it["ilvl"]}' if it.get("ilvl") else ""
            q_label = it.get("quality") or ""
            right_bits = " · ".join(x for x in (q_label, ilvl_tag, f'ID {it["id"]}' if it.get("id") else "") if x)
            tags = [x for x in (it.get("bind"), it.get("unique"), it.get("slot_type"), it.get("req_level")) if x]
            meta_line = f'<div class="tt-meta">{_esc(" · ".join(str(t) for t in tags))}</div>' if tags else ""
            stats_html = "".join(
                f'<div class="tt-stat">{_esc(s)}</div>' for s in (it.get("stats") or []) if str(s).strip()
            )
            uses_html = "".join(
                f'<div class="tt-use">{_esc(u)}</div>' for u in (it.get("use_lines") or []) if str(u).strip()
            )
            flavor_html = f'<div class="tt-flavor">{_esc(it["flavor"])}</div>' if it.get("flavor") else ""
            foot_l = f'<span>{_esc(it.get("source") or "")}</span>'
            foot_r = f'<span>{_esc(it.get("meta_right") or "")}</span>'
            foot_html = (
                f'<div class="tt-foot">{foot_l}{foot_r}</div>'
                if (it.get("source") or it.get("meta_right")) else ""
            )
            tt_html.append(
                f'<div class="tt-card" style="border-left-color:{qc};">'
                f'<div class="tt-head">'
                f'{ic_box}'
                f'<div class="tt-head-txt">'
                f'<div class="tt-title-row">'
                f'<span class="tt-title" style="color:{qc};">{_esc(it.get("name"))}</span>'
                + (f'<span class="tt-right">{_esc(right_bits)}</span>' if right_bits else "")
                + f'</div>'
                f'{meta_line}'
                f'</div>'
                f'</div>'
                f'{stats_html}{uses_html}{flavor_html}{foot_html}'
                f'</div>'
            )
        body_blocks.append(f'<div class="tt-list">{"".join(tt_html)}</div>')

    # 组件 12：中段说明正文 (summary)
    if card.get("summary"):
        body_blocks.append(f'<p class="card-summary">{_esc(card["summary"])}</p>')

    # 组件 13：底部金线引用块 (quote)
    q_block = card.get("quote")
    if isinstance(q_block, dict):
        q_note = f'<div class="qb-note">{_esc(q_block.get("note"))}</div>' if q_block.get("note") else ""
        body_blocks.append(
            f'<div class="quote-box">'
            f'<div class="qb-title">{_esc(q_block.get("text"))}</div>'
            f'{q_note}'
            f'</div>'
        )

    inner_payload = "\n".join(body_blocks)

    # 如果是 3:4 封面卡 (kind == "cover" and mode == "carousel")
    if is_cover and mode == "carousel":
        kicker_tag = card.get("kicker") or f"热修与动态 · {date_str}"
        h1_line1 = card.get("title_line1") or card.get("title") or ""
        h1_line2 = card.get("title_line2") or ""
        sub_line = card.get("subtitle") or ""
        cov_icons_html = _render_cover_icons_strip(card.get("cover_icons") or [], size=72)
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:1080px; height:1440px; background:#0F0C14;
       font-family:"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif; color:#FFFFFF; }}
.cover-wrap {{
  width:1080px; height:1440px; position:relative; overflow:hidden;
  display:flex; flex-direction:column; justify-content:space-between;
  padding:52px 60px 56px;
}}
.cover-bg {{
  position:absolute; inset:0;
  background-image:url("{bg_uri}");
  background-size:cover; background-position:center;
  z-index:0;
}}
.cover-grad {{
  position:absolute; inset:0;
  background:linear-gradient(180deg,
    rgba(10,8,14,0.68) 0%,
    rgba(10,8,14,0.12) 28%,
    rgba(10,8,14,0.22) 55%,
    rgba(10,8,14,0.92) 80%,
    rgba(8,6,12,0.98) 100%);
  z-index:1;
}}
.top-header {{
  position:relative; z-index:2;
  display:flex; align-items:center; justify-content:space-between;
}}
.emblem-badge {{
  display:flex; align-items:center; gap:18px;
}}
.emblem-circle {{
  width:88px; height:88px; border-radius:50%;
  background:radial-gradient(circle, #2A4B7C 0%, #132440 75%);
  border:3px solid #D8B467;
  box-shadow:0 4px 16px rgba(0,0,0,0.65), inset 0 0 12px rgba(243,201,105,0.4);
  display:flex; align-items:center; justify-content:center;
  font-family:"Times New Roman",serif; font-size:38px; font-weight:900; color:#F5D98E;
}}
.top-right {{
  text-align:right;
}}
.col-title {{
  font-size:60px; font-weight:900; color:#F3D285; letter-spacing:4px;
  text-shadow:0 4px 16px rgba(0,0,0,0.85);
}}
.col-rule {{
  height:2px; background:linear-gradient(90deg, transparent, rgba(243,210,133,0.75));
  margin:10px 0 8px;
}}
.col-date {{
  font-size:44px; font-weight:800; color:#FFFFFF; letter-spacing:2px;
  text-shadow:0 3px 10px rgba(0,0,0,0.85);
}}
.bottom-hero {{
  position:relative; z-index:2;
}}
.kicker-pill {{
  display:inline-block;
  background:#E5C278; color:#1D150B;
  font-size:28px; font-weight:800;
  padding:10px 24px; border-radius:8px;
  margin-bottom:26px;
  box-shadow:0 4px 14px rgba(0,0,0,0.45);
}}
.hero-h1 {{
  font-size:74px; line-height:1.24; font-weight:900; color:#FFFFFF;
  letter-spacing:1.5px; text-shadow:0 4px 18px rgba(0,0,0,0.9);
}}
.hero-h2 {{
  font-size:74px; line-height:1.24; font-weight:900; color:#E8B85D;
  letter-spacing:1.5px; margin-top:6px;
  text-shadow:0 4px 18px rgba(0,0,0,0.9);
}}
.hero-sub {{
  margin-top:24px; font-size:30px; color:#C8C2B8; font-weight:600;
  letter-spacing:1px;
}}
.cov-ic-strip {{
  display:flex; align-items:flex-start; gap:18px; margin-top:28px;
}}
.cov-ic-item {{
  display:flex; flex-direction:column; align-items:center; gap:8px; width:96px;
}}
.cov-ic-box {{
  border-radius:14px; overflow:hidden; border:2.5px solid #D8B467;
  background:#15121A; box-shadow:0 6px 16px rgba(0,0,0,0.65);
}}
.cov-ic-lbl {{
  font-size:17px; font-weight:700; color:#EFE7D6; text-align:center;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:96px;
  text-shadow:0 2px 6px rgba(0,0,0,0.9);
}}
.wm {{
  position:absolute; right:56px; bottom:52px; z-index:3;
  text-align:right; font-size:22px; color:rgba(255,255,255,0.68);
}}
</style></head><body>
<div class="cover-wrap">
  <div class="cover-bg"></div>
  <div class="cover-grad"></div>
  <div class="top-header">
    <div class="emblem-badge">
      <div class="emblem-circle">FOR</div>
    </div>
    <div class="top-right">
      <div class="col-title">{_esc(column_name)}</div>
      <div class="col-rule"></div>
      <div class="col-date">{_esc(date_str)}</div>
    </div>
  </div>
  <div class="bottom-hero">
    <div class="kicker-pill">{_esc(kicker_tag)}</div>
    <div class="hero-h1">{_esc(h1_line1)}</div>
    {f'<div class="hero-h2">{_esc(h1_line2)}</div>' if h1_line2 else ''}
    <div class="hero-sub">{_esc(sub_line)}</div>
    {cov_icons_html}
  </div>
  <div class="wm">小程序：{_esc(brand_name)} · 网页：paoben.top</div>
</div>
</body></html>"""

    # 内页卡片：mode="carousel" (1080x1440) vs mode="inline" (1080xauto)
    h_line1 = card.get("title_line1") or card.get("title") or ""
    h_line2 = card.get("title_line2") or ""
    h2_color = card.get("title_line2_color") or accent

    chrome_top = ""
    chrome_bottom = ""
    if mode == "carousel":
        chrome_top = f"""
        <div class="c-topbar">
          <div class="c-brand">
            <span class="c-logo">FOR</span>
            <span class="c-col">{_esc(column_name)}</span>
          </div>
          <div class="c-line"></div>
          <div class="c-date">{_esc(date_str)}</div>
        </div>
        <div class="c-headline">
          <div class="c-h1">{_esc(h_line1)}</div>
          {f'<div class="c-h2" style="color:{_esc(h2_color)}">{_esc(h_line2)}</div>' if h_line2 else ''}
        </div>
        """
        chrome_bottom = f"""
        <div class="c-footbar">
          <div class="c-pg"><strong>{idx:02d} / {total:02d}</strong>　来源：{_esc(source_label)}</div>
          <div class="c-wm">小程序：{_esc(brand_name)} · 网页：paoben.top</div>
        </div>
        """
    else:
        chrome_bottom = f"""
        <div class="inline-wm">小程序：{_esc(brand_name)} · 网页：paoben.top</div>
        """

    wrap_cls = "card-shell carousel-mode" if mode == "carousel" else "card-shell inline-mode"

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  width:1080px;
  background:#16121A;
  font-family:"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif;
  color:#F2EFE9;
}}
.card-shell {{
  width:1080px;
  position:relative;
  overflow:hidden;
  display:flex;
  flex-direction:column;
  background:#16121A;
}}
.card-shell.carousel-mode {{
  height:1440px;
  padding:52px 64px 48px;
  justify-content:space-between;
}}
.card-shell.inline-mode {{
  height:auto;
  min-height:460px;
  padding:48px 56px 52px;
  border-radius:14px;
}}
.blur-bg {{
  position:absolute; inset:-40px;
  background-image:url("{bg_uri}");
  background-size:cover; background-position:center;
  filter:blur(32px) brightness(0.34) saturate(1.15);
  transform:scale(1.08);
  z-index:0;
}}
.blur-overlay {{
  position:absolute; inset:0;
  background:
    radial-gradient(ellipse at 50% 0%, rgba(212,168,87,0.16), transparent 60%),
    linear-gradient(180deg, rgba(20,15,24,0.55) 0%, rgba(14,11,18,0.82) 100%);
  z-index:1;
}}
.content-layer {{
  position:relative; z-index:2;
  display:flex; flex-direction:column;
  flex:1;
}}
.carousel-mode .content-layer {{
  justify-content:flex-start;
  gap:8px;
}}
.carousel-mode .card-summary {{
  font-size:32px;
  line-height:1.72;
  margin:18px 0 28px;
}}
/* Top bar & Headline for 3:4 Carousel */
.c-topbar {{
  display:flex; align-items:center; gap:20px; margin-bottom:44px;
}}
.c-brand {{ display:flex; align-items:center; gap:12px; }}
.c-logo {{
  width:42px; height:42px; border-radius:50%;
  background:#1F3A60; border:2px solid #D8B467;
  display:inline-flex; align-items:center; justify-content:center;
  font-size:16px; font-weight:900; color:#F5D98E;
}}
.c-col {{ font-size:28px; font-weight:800; color:#E8C97A; letter-spacing:1.5px; }}
.c-line {{ flex:1; height:1px; background:rgba(255,255,255,0.16); }}
.c-date {{ font-size:28px; font-weight:700; color:#EAE6DF; }}
.c-headline {{ margin-bottom:38px; }}
.c-h1 {{ font-size:62px; line-height:1.25; font-weight:900; color:#FFFFFF; letter-spacing:1px; }}
.c-h2 {{ font-size:62px; line-height:1.25; font-weight:900; margin-top:6px; letter-spacing:1px; }}

/* Modular Components */
.pill-row {{ display:flex; flex-wrap:wrap; gap:16px; margin-bottom:26px; }}
.pill {{
  padding:10px 28px; border-radius:999px;
  background:rgba(192,97,43,0.22);
  border:1.5px solid rgba(218,134,78,0.55);
  color:#F7EFE6; font-size:26px; font-weight:700; letter-spacing:0.5px;
}}
.card-intro {{
  font-size:30px; line-height:1.65; color:#E2DDD5; margin-bottom:28px;
}}
.kpi-bar {{
  display:grid; grid-template-columns:repeat(3, 1fr);
  border-top:1px solid rgba(255,255,255,0.14);
  border-bottom:1px solid rgba(255,255,255,0.14);
  padding:30px 0; margin-bottom:30px;
}}
.kpi-col {{
  text-align:center; padding:0 12px;
  border-right:1px solid rgba(255,255,255,0.12);
}}
.kpi-col:last-child {{ border-right:none; }}
.kpi-val {{ font-size:56px; font-weight:900; line-height:1.15; letter-spacing:1px; white-space:nowrap; }}
.kpi-lbl {{ font-size:25px; color:#C8C2B8; margin-top:10px; font-weight:500; }}

.stat-change-box {{
  background:rgba(12,14,22,0.72);
  border:1.5px solid rgba(255,255,255,0.12);
  border-radius:16px;
  padding:32px 38px;
  display:flex; align-items:center; justify-content:space-between;
  margin-bottom:26px;
}}
.sc-name {{ font-size:32px; font-weight:800; color:#FFFFFF; }}
.sc-sub {{ font-size:24px; color:#9E988E; margin-top:6px; }}
.sc-right {{ display:flex; align-items:center; gap:24px; }}
.sc-old {{ font-size:46px; font-weight:800; color:#B8B2A6; }}
.sc-arrow {{ font-size:38px; color:#8C867B; }}
.sc-new {{ font-size:48px; font-weight:900; }}

.hero-stat {{ margin:14px 0 32px; }}
.hero-stat.center {{
  text-align:center; padding:26px 0;
  border-top:1px solid rgba(255,255,255,0.13);
  border-bottom:1px solid rgba(255,255,255,0.13);
}}
.hs-num {{ font-size:112px; font-weight:900; line-height:1.05; }}
.hero-stat.center .hs-num {{ font-size:68px; }}
.hs-unit {{ font-size:36px; font-weight:800; color:#FFFFFF; margin-left:14px; }}
.hs-desc {{ font-size:26px; color:#C8C2B8; margin-top:10px; }}

.banner-box {{
  border-radius:14px; overflow:hidden;
  border:1.5px solid rgba(212,168,87,0.38);
  margin:12px 0 28px;
  background:rgba(0,0,0,0.4);
}}
.banner-box img {{ width:100%; max-height:300px; object-fit:cover; display:block; }}
.shot-cap {{
  padding:16px 22px; font-size:25px; line-height:1.55; color:#D5CFC4;
  background:rgba(15,12,18,0.85);
}}

.sub-sec-title {{
  font-size:28px; font-weight:800; color:#E5B869; margin:12px 0 18px;
}}
.ir-list {{ display:flex; flex-direction:column; gap:18px; margin-bottom:24px; }}
.ir-row {{
  display:flex; align-items:flex-start; gap:22px;
  padding:20px 24px;
  background:rgba(0,0,0,0.34);
  border:1px solid rgba(255,255,255,0.09);
  border-radius:14px;
}}
.ir-icon {{
  width:72px; height:72px; border-radius:12px;
  border:2px solid #C8A458; flex-shrink:0; object-fit:cover;
}}
.ir-icon-fallback {{
  width:72px; height:72px; border-radius:12px;
  background:#2A2232; border:2px solid #C8A458;
  display:flex; align-items:center; justify-content:center;
  font-size:32px; font-weight:900; color:#E5B869; flex-shrink:0;
}}
.ir-head {{ font-size:31px; font-weight:800; color:#FFFFFF; display:flex; align-items:center; gap:14px; }}
.ir-badge {{
  font-size:21px; padding:3px 12px; border-radius:6px;
  background:rgba(229,184,105,0.2); color:#F3C969; border:1px solid rgba(229,184,105,0.45);
}}
.ir-desc {{ font-size:26px; line-height:1.55; color:#C4BEB4; margin-top:8px; }}

.pr-table {{
  background:rgba(0,0,0,0.28);
  border:1px solid rgba(255,255,255,0.1);
  border-radius:16px;
  padding:10px 28px;
  margin-bottom:24px;
}}
.pr-row {{
  display:flex; align-items:flex-start; gap:24px;
  padding:20px 0;
  border-bottom:1px dashed rgba(255,255,255,0.13);
}}
.pr-row:last-child {{ border-bottom:none; }}
.pr-tag {{
  min-width:136px; text-align:center;
  padding:8px 18px; border-radius:8px;
  font-size:24px; font-weight:800; flex-shrink:0;
  background:rgba(167,128,58,0.22);
  border:1.5px solid rgba(201,164,92,0.5);
  color:#EED294;
}}
.pr-tag.tone-green {{
  background:rgba(46,139,87,0.24); border-color:rgba(82,183,136,0.55); color:#95E1B8;
}}
.pr-tag.tone-blue {{
  background:rgba(37,99,235,0.24); border-color:rgba(96,165,250,0.55); color:#93C5FD;
}}
.pr-title {{ font-size:29px; font-weight:800; color:#FFFFFF; line-height:1.4; }}
.pr-sub {{ font-size:24px; color:#A8A298; margin-top:6px; line-height:1.45; }}

.timeline-box {{
  position:relative; padding-left:44px; margin:10px 0 28px;
  display:flex; flex-direction:column; gap:28px;
}}
.timeline-box::before {{
  content:""; position:absolute; left:13px; top:18px; bottom:18px;
  width:2px; background:rgba(255,255,255,0.18);
}}
.tl-item {{ position:relative; }}
.tl-dot {{
  position:absolute; left:-44px; top:6px;
  width:28px; height:28px; border-radius:50%;
  background:#18131D; border:3.5px solid #E5B869;
}}
.tl-time {{ font-size:26px; font-weight:800; margin-bottom:4px; }}
.tl-title {{ font-size:33px; font-weight:800; color:#FFFFFF; line-height:1.35; }}
.tl-sub {{ font-size:26px; color:#B8B2A8; margin-top:6px; line-height:1.45; }}

.cmp-grid {{
  display:grid; grid-template-columns:1fr 1fr; gap:22px; margin-top:16px; margin-bottom:20px;
}}
.cmp-col {{
  background:rgba(0,0,0,0.38);
  border:1px solid rgba(255,255,255,0.11);
  border-radius:14px; padding:26px 28px;
}}
.cmp-head {{ font-size:25px; font-weight:800; margin-bottom:12px; }}
.cmp-body {{ font-size:28px; font-weight:700; color:#FFFFFF; line-height:1.55; }}

.qr-list {{ display:flex; flex-direction:column; }}
.qr-row {{
  display:flex; align-items:flex-start; gap:30px;
  padding:26px 0;
  border-bottom:1px solid rgba(255,255,255,0.12);
}}
.qr-row:last-child {{ border-bottom:none; }}
.qr-sym {{
  font-size:74px; font-weight:900; color:#D8A84E; line-height:1;
  width:56px; text-align:center; flex-shrink:0;
}}
.qr-title {{ font-size:34px; font-weight:800; color:#FFFFFF; margin-bottom:8px; }}
.qr-desc {{ font-size:27px; color:#C4BEB4; line-height:1.5; }}

.tt-list {{ display:flex; flex-direction:column; gap:16px; margin-bottom:16px; }}
.tt-card {{
  background:rgba(8,11,16,0.86);
  border:1px solid rgba(255,255,255,0.14);
  border-left:5px solid #3897FF;
  border-radius:14px;
  padding:18px 22px;
  box-shadow:0 8px 24px rgba(0,0,0,0.34);
}}
.tt-head {{ display:flex; align-items:flex-start; gap:18px; margin-bottom:10px; }}
.tt-icon {{
  width:62px; height:62px; border-radius:10px; flex-shrink:0;
  border:2px solid #D8A84E; object-fit:cover; background:#111;
}}
.tt-icon-fb {{
  width:62px; height:62px; border-radius:10px; flex-shrink:0;
  border:2px solid #D8A84E; background:#141822;
  display:flex; align-items:center; justify-content:center;
  font-size:26px; font-weight:900;
}}
.tt-head-txt {{ flex:1; min-width:0; }}
.tt-title-row {{
  display:flex; align-items:baseline; justify-content:space-between; gap:14px;
  flex-wrap:wrap;
}}
.tt-title {{ font-size:30px; font-weight:900; line-height:1.25; }}
.tt-right {{
  font-size:21px; color:#A8A298; font-weight:700;
  background:rgba(255,255,255,0.06); padding:4px 12px; border-radius:999px;
  white-space:nowrap;
}}
.tt-meta {{ font-size:22px; color:#E4DFD6; margin-top:6px; line-height:1.35; }}
.tt-stat {{ font-size:23px; color:#FFFFFF; font-weight:600; line-height:1.45; margin-top:4px; }}
.tt-use {{ font-size:24px; color:#2EE866; font-weight:700; line-height:1.46; margin-top:6px; }}
.tt-flavor {{ font-size:21px; color:#F2C964; line-height:1.42; margin-top:6px; }}
.tt-foot {{
  display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap;
  margin-top:10px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.09);
  font-size:20px; color:#9E988E;
}}

.card-summary {{
  font-size:30px; line-height:1.68; color:#E8E3DC; margin:12px 0 26px;
}}
.quote-box {{
  margin-top:auto;
  border-left:4px solid #D8A84E;
  padding:6px 0 6px 24px;
}}
.qb-title {{ font-size:31px; font-weight:800; color:#FFFFFF; line-height:1.55; }}
.qb-note {{ font-size:25px; color:#B5AFA6; margin-top:10px; }}

.c-footbar {{
  position:relative; z-index:2;
  display:flex; align-items:center; justify-content:space-between;
  padding-top:24px; margin-top:24px;
  border-top:1px solid rgba(255,255,255,0.1);
  font-size:23px; color:#9E988E;
}}
.c-footbar strong {{ color:#E8E3DC; }}
.inline-wm {{
  position:relative; z-index:2;
  text-align:right; font-size:21px; color:rgba(255,255,255,0.52);
  margin-top:14px;
}}
</style></head><body>
<div class="{wrap_cls}" id="cardRoot">
  <div class="blur-bg"></div>
  <div class="blur-overlay"></div>
  <div class="content-layer">
    {chrome_top}
    {inner_payload}
  </div>
  {chrome_bottom}
</div>
</body></html>"""


# ═══════════════════════════════════════════════════════════════════════════
# 四、皮肤 B：theme="grimoire"（无限冒险笔记 · 复古皮质封面 + 做旧羊皮纸手账风）
# ═══════════════════════════════════════════════════════════════════════════

_WAX_SEAL_SVG = """<svg viewBox="0 0 48 48" width="42" height="42" style="flex-shrink:0;">
  <circle cx="24" cy="24" r="21" fill="#8F1D1D" stroke="#5A0F0F" stroke-width="2"/>
  <circle cx="24" cy="24" r="16" fill="#A82424" stroke="#D47A6A" stroke-width="1" stroke-dasharray="3,2"/>
  <path d="M24 14 L26.8 20.5 L33.8 21.2 L28.5 25.8 L30.1 32.6 L24 29 L17.9 32.6 L19.5 25.8 L14.2 21.2 L21.2 20.5 Z" fill="#F2C97D"/>
</svg>"""


def build_grimoire_cover_html(
    *,
    dungeon_name: str,
    subtitle: str,
    level_str: str,
    faction: str,
    art_uri: str,
    faction_icon_uri: str,
    brand_name: str = "跑本无限助手",
) -> str:
    """渲染 P1 拟物皮质古书封面（1080x1440）。"""
    is_horde = "部落" in (faction or "")
    fac_label = "部落" if is_horde else "联盟" if "联盟" in (faction or "") else "双阵营"
    fac_color = "#E04F3E" if is_horde else "#639BFF" if fac_label == "联盟" else "#E5C172"
    table_bg = (
        "radial-gradient(circle at 50% 42%, #2B424C 0%, #16242B 68%, #0C1418 100%)"
        if not is_horde else
        "radial-gradient(circle at 50% 42%, #3E2A27 0%, #211513 68%, #120B0A 100%)"
    )
    fac_img = (
        f'<img src="{faction_icon_uri}" style="width:42px;height:42px;object-fit:contain;" />'
        if faction_icon_uri else ""
    )

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  width:1080px; height:1440px;
  background:{table_bg};
  font-family:"Songti SC","Noto Serif CJK SC","STSong","SimSun",serif;
  display:flex; align-items:center; justify-content:center;
  position:relative; overflow:hidden;
}}
/* Wood/Stone grain lines */
body::before {{
  content:""; position:absolute; inset:0;
  background:repeating-linear-gradient(
    0deg,
    rgba(255,255,255,0.015) 0px,
    rgba(255,255,255,0.015) 2px,
    transparent 2px,
    transparent 9px
  );
  pointer-events:none;
}}
.book-wrap {{
  width:850px; height:1180px;
  position:relative;
  border-radius:14px 22px 22px 14px;
  background:
    radial-gradient(circle at 50% 48%, rgba(92,64,38,0.32) 0%, rgba(24,16,11,0.96) 78%),
    linear-gradient(135deg, #2E2118 0%, #1B130D 52%, #120C08 100%);
  box-shadow:
    -18px 24px 48px rgba(0,0,0,0.85),
    0 32px 68px rgba(0,0,0,0.75),
    inset 18px 0 28px rgba(0,0,0,0.65),
    inset 0 0 0 3px #4E3B26;
  padding:46px 52px;
  display:flex; flex-direction:column; align-items:center; justify-content:space-between;
}}
/* Book page edge on right & bottom */
.book-wrap::after {{
  content:""; position:absolute; top:14px; right:-12px; bottom:10px; width:12px;
  background:linear-gradient(90deg, #D8C39E, #A8916C 60%, #735F3E);
  border-radius:0 6px 6px 0;
  box-shadow:4px 6px 14px rgba(0,0,0,0.6);
}}
/* Spine groove */
.spine-groove {{
  position:absolute; top:0; bottom:0; left:34px; width:4px;
  background:linear-gradient(90deg, rgba(0,0,0,0.75), rgba(255,215,140,0.12));
}}
.inner-border {{
  width:100%; height:100%;
  border:2px solid rgba(196,158,92,0.55);
  border-radius:10px;
  padding:44px 40px 38px;
  display:flex; flex-direction:column; align-items:center; justify-content:space-between;
  position:relative;
  box-shadow:inset 0 0 0 6px rgba(24,16,11,0.9), inset 0 0 0 7px rgba(196,158,92,0.28);
}}
/* Faint magic circle engraving */
.magic-ring {{
  position:absolute; top:50%; left:50%;
  width:620px; height:620px;
  transform:translate(-50%, -50%);
  border-radius:50%;
  border:1.5px dashed rgba(212,175,106,0.14);
  pointer-events:none;
}}
.magic-ring::before {{
  content:""; position:absolute; inset:34px;
  border-radius:50%;
  border:1px solid rgba(212,175,106,0.10);
}}
.crest {{
  width:92px; height:92px; border-radius:50%;
  background:radial-gradient(circle, #2A4B7C 0%, #122138 75%);
  border:3px solid #D8B467;
  box-shadow:0 6px 18px rgba(0,0,0,0.7);
  display:flex; align-items:center; justify-content:center;
  font-family:"Times New Roman",serif; font-size:34px; font-weight:900; color:#F7DF9C;
  letter-spacing:1px;
}}
.title-group {{ text-align:center; position:relative; z-index:2; }}
.book-title {{
  font-size:86px; font-weight:900; letter-spacing:10px;
  background:linear-gradient(180deg, #FFF3C4 0%, #E0B96B 55%, #9B7331 100%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  filter:drop-shadow(0 4px 10px rgba(0,0,0,0.85));
}}
.book-sub {{
  margin-top:14px;
  font-family:"PingFang SC","Microsoft YaHei",sans-serif;
  font-size:26px; font-weight:600; color:#C8B696; letter-spacing:6px;
}}
.art-frame {{
  width:360px; height:470px;
  padding:10px;
  background:linear-gradient(180deg, #7B6037, #43321B);
  border-radius:6px;
  box-shadow:0 12px 32px rgba(0,0,0,0.8), inset 0 0 0 1px #B89658;
  position:relative; z-index:2;
}}
.art-inner {{
  width:100%; height:100%; overflow:hidden; position:relative;
  border:1px solid #2A1E11;
}}
.art-inner img {{
  width:100%; height:100%; object-fit:cover;
  filter:sepia(0.18) contrast(1.08) brightness(0.95);
}}
.art-inner::after {{
  content:""; position:absolute; inset:0;
  box-shadow:inset 0 0 36px rgba(15,10,5,0.75);
}}
.book-foot {{
  display:flex; align-items:center; gap:16px;
  font-family:"PingFang SC","Microsoft YaHei",sans-serif;
  font-size:32px; font-weight:800; color:#D8C8AE;
  letter-spacing:2px; position:relative; z-index:2;
}}
.fac-text {{ color:{fac_color}; }}
.table-wm {{
  position:absolute; right:56px; bottom:38px;
  font-family:"PingFang SC","Microsoft YaHei",sans-serif;
  font-size:23px; color:rgba(235,225,205,0.72);
}}
</style></head><body>
  <div class="book-wrap">
    <div class="spine-groove"></div>
    <div class="inner-border">
      <div class="magic-ring"></div>
      <div class="crest">FOR</div>
      <div class="title-group">
        <div class="book-title">{_esc(dungeon_name)}</div>
        <div class="book-sub">{_esc(subtitle)}</div>
      </div>
      <div class="art-frame">
        <div class="art-inner">
          <img src="{art_uri}" />
        </div>
      </div>
      <div class="book-foot">
        <span>{_esc(level_str)}</span>
        <span>·</span>
        <span class="fac-text">{_esc(fac_label)}</span>
        {fac_img}
      </div>
    </div>
  </div>
  <div class="table-wm">小程序：{_esc(brand_name)} · 网页：paoben.top</div>
</body></html>"""


def wrap_grimoire_page_html(
    inner_html: str,
    *,
    dungeon_name: str,
    faction: str,
    phase_active: str,  # "总览" | "出发前" | "必刷掉落" | "常见问题"
    page_num: int,
    faction_icon_uri: str = "",
    mode: str = "carousel",  # "carousel" (1080x1440) | "inline" (1080xauto)
    brand_name: str = "跑本无限助手",
) -> str:
    """将羊皮纸手账内页包装为 3:4 完整手账页（carousel）或 1080x自适应内嵌卡（inline）。"""
    phases = ["总览", "出发前", "必刷掉落", "常见问题"]
    bc_parts = []
    for p in phases:
        cls = "bc-item active" if p == phase_active else "bc-item"
        bc_parts.append(f'<span class="{cls}">{_esc(p)}</span>')
    breadcrumb_html = '<span class="bc-sep">&gt;</span>'.join(bc_parts)

    fac_label = "部落" if "部落" in (faction or "") else "联盟" if "联盟" in (faction or "") else "双阵营"
    fac_img = (
        f'<img src="{faction_icon_uri}" style="width:28px;height:28px;object-fit:contain;" />'
        if faction_icon_uri else ""
    )

    header_html = ""
    footer_html = ""
    if mode == "carousel":
        header_html = f"""
        <div class="p-topbar">
          <div class="p-run-title">冒险笔记 · {_esc(dungeon_name)}</div>
          <div class="p-run-right">
            <div class="p-bc">{breadcrumb_html}</div>
            <div class="p-fac">{_esc(fac_label)} {fac_img}</div>
          </div>
        </div>
        """
        footer_html = f"""
        <div class="p-footbar">
          <div class="p-brand">✦ {_esc(brand_name)}</div>
          <div class="p-pg">◆ {page_num:02d} ◆</div>
          <div class="p-wm">小程序：{_esc(brand_name)} · 网页：paoben.top</div>
        </div>
        """
    else:
        footer_html = f"""
        <div class="p-inline-foot">
          <span>冒险笔记 · {_esc(dungeon_name)}</span>
          <span>小程序：{_esc(brand_name)} · 网页：paoben.top</span>
        </div>
        """

    shell_cls = "parchment-shell carousel-mode" if mode == "carousel" else "parchment-shell inline-mode"

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  width:1080px;
  background:#2B1D12;
  font-family:"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif;
  color:#2B1D12;
}}
.parchment-shell {{
  width:1080px;
  position:relative;
  overflow:hidden;
  display:flex;
  flex-direction:column;
  background:
    radial-gradient(circle at 22% 18%, rgba(255,248,231,0.55) 0%, transparent 52%),
    radial-gradient(circle at 80% 78%, rgba(168,128,76,0.28) 0%, transparent 48%),
    linear-gradient(168deg, #EFE0C4 0%, #E5CFA8 48%, #D8BC8E 100%);
  box-shadow:
    inset 0 0 75px rgba(78,46,16,0.48),
    inset 0 0 0 14px #2B1D12,
    inset 0 0 0 17px #8C6D3F;
}}
.parchment-shell.carousel-mode {{
  height:1440px;
  padding:46px 62px 42px;
  justify-content:space-between;
}}
.parchment-shell.inline-mode {{
  height:auto;
  padding:40px 52px 36px;
  border-radius:14px;
}}
.watermark-crest {{
  position:absolute; right:40px; bottom:60px;
  width:420px; height:420px;
  opacity:0.06; pointer-events:none;
  background-image:url("{faction_icon_uri}");
  background-size:contain; background-repeat:no-repeat; background-position:center;
}}
.p-topbar {{
  display:flex; align-items:center; justify-content:space-between;
  padding-bottom:14px; margin-bottom:18px;
  border-bottom:1.5px solid rgba(112,82,46,0.32);
  font-size:22px; color:#6E5233; font-weight:700;
}}
.p-run-right {{ display:flex; align-items:center; gap:22px; }}
.p-bc {{ display:flex; align-items:center; gap:8px; font-size:20px; color:#8A6E4B; }}
.bc-item.active {{
  color:#9E2A2B; font-weight:800;
  background:rgba(158,42,43,0.12); padding:2px 10px; border-radius:4px;
}}
.p-fac {{ display:flex; align-items:center; gap:6px; font-weight:800; color:#4A3520; }}

.p-main {{ position:relative; z-index:2; flex:1; display:flex; flex-direction:column; }}

/* Shared Grimoire Typography & Components */
.g-header-row {{
  display:flex; align-items:flex-end; justify-content:space-between;
  margin-bottom:18px;
}}
.g-eyebrow {{ font-size:23px; font-weight:800; color:#9E2A2B; margin-bottom:4px; letter-spacing:1px; }}
.g-title {{
  font-family:"Songti SC","Noto Serif CJK SC","STSong",serif;
  font-size:58px; font-weight:900; color:#23160C; line-height:1.15; letter-spacing:2px;
}}
.g-kpi-right {{ text-align:right; }}
.g-kpi-big {{
  font-family:"Georgia","Songti SC",serif;
  font-size:44px; font-weight:900; color:#8C2318; line-height:1.15;
}}
.g-kpi-sub {{ font-size:22px; color:#6A5035; font-weight:700; margin-top:4px; }}

.g-callout {{
  border-left:4px solid #9E2A2B;
  padding:6px 0 6px 16px;
  margin-bottom:20px;
  font-size:24px; line-height:1.5; color:#3D2918; font-weight:700;
  background:rgba(158,42,43,0.06);
  border-radius:0 6px 6px 0;
}}
.g-callout .red {{ color:#9E2A2B; }}

/* Side-by-side Annotated Maps */
.g-map-grid {{
  display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-bottom:22px;
}}
.g-map-box {{
  height:256px; position:relative; overflow:hidden;
  border:2.5px solid #6E5233; border-radius:8px;
  box-shadow:0 4px 12px rgba(0,0,0,0.18);
  background:#2A2118;
}}
.g-map-box img {{
  width:100%; height:100%; object-fit:cover;
  filter:sepia(0.15) contrast(1.06);
}}
.g-map-tag {{
  position:absolute; top:10px; left:10px;
  background:rgba(28,20,12,0.86); color:#F3E5AB;
  padding:4px 12px; border-radius:4px;
  font-size:20px; font-weight:800;
  border:1px solid rgba(212,175,106,0.5);
}}
.g-pin {{
  position:absolute; transform:translate(-50%, -50%);
  display:flex; align-items:center; gap:4px;
  background:rgba(24,16,10,0.88); color:#FFF5D6;
  padding:3px 9px; border-radius:999px;
  font-size:17px; font-weight:800; white-space:nowrap;
  border:1.5px solid #E5B869;
  box-shadow:0 2px 6px rgba(0,0,0,0.6);
}}
.g-pin .dot {{
  width:11px; height:11px; border-radius:50%;
  background:#E03E2D; border:1.5px solid #FFFFFF;
}}
.g-pin.entry .dot {{ background:#3B82F6; }}
.g-boss-num-pin {{
  position:absolute; transform:translate(-50%, -50%);
  width:28px; height:28px; border-radius:50%;
  background:#A82020; color:#FFF7E0;
  border:2px solid #F3D285;
  font-size:16px; font-weight:900;
  display:flex; align-items:center; justify-content:center;
  box-shadow:0 2px 6px rgba(0,0,0,0.75);
}}
.g-map-legend {{
  position:absolute; left:0; right:0; bottom:0;
  background:rgba(20,14,8,0.88);
  color:#EFE2C6; font-size:15.5px; font-weight:700;
  padding:5px 10px;
  display:flex; flex-wrap:wrap; gap:8px;
  border-top:1px solid rgba(212,175,106,0.4);
}}

/* Quest Overview Table */
.g-quest-table {{
  display:flex; flex-direction:column;
  border-top:2px solid rgba(110,82,51,0.45);
}}
.g-q-row {{
  display:flex; align-items:center; justify-content:space-between; gap:14px;
  padding:13px 6px;
  border-bottom:1px dashed rgba(110,82,51,0.35);
}}
.g-q-left {{ display:flex; align-items:center; gap:10px; flex-shrink:0; white-space:nowrap; }}
.g-q-name {{
  font-family:"Songti SC","Noto Serif CJK SC",serif;
  font-size:26px; font-weight:900; color:#23160C; white-space:nowrap;
}}
.g-badge {{
  font-size:18px; font-weight:800; padding:3px 10px; border-radius:4px;
  background:#9E2A2B; color:#FFF8EC; white-space:nowrap; flex-shrink:0;
}}
.g-badge.olive {{ background:#526A32; }}
.g-badge.blue {{ background:#2B5B84; }}
.g-q-mid {{ flex:1; font-size:21px; line-height:1.4; color:#5A432C; font-weight:600; text-align:left; }}
.g-q-right {{
  font-family:"Georgia",serif; font-size:24px; font-weight:800; color:#3D2918;
  flex-shrink:0; white-space:nowrap; text-align:right;
}}

/* Step Chain with Wax Seal */
.g-step-list {{ display:flex; flex-direction:column; gap:14px; margin-bottom:20px; }}
.g-step-row {{
  display:flex; align-items:center; gap:16px;
  padding:12px 16px;
  background:rgba(255,250,240,0.52);
  border:1px solid rgba(128,96,58,0.28);
  border-radius:10px;
}}
.g-step-row.highlight {{
  background:rgba(158,42,43,0.11);
  border:1.5px solid rgba(158,42,43,0.52);
}}
.g-step-num {{
  width:38px; height:38px; border-radius:50%;
  background:#D6C098; border:2px solid #8A6A3E;
  color:#3D2918; font-weight:900; font-size:21px;
  display:flex; align-items:center; justify-content:center; flex-shrink:0;
}}
.g-step-row.highlight .g-step-num {{
  background:#9E2A2B; border-color:#6B1515; color:#FFFFFF;
}}
.g-step-zone {{
  min-width:210px; font-size:22px; font-weight:800; color:#5C4328; flex-shrink:0;
}}
.g-step-row.highlight .g-step-zone {{ color:#8C1D1D; }}
.g-step-desc {{
  flex:1; font-size:24px; font-weight:700; color:#23160C;
}}
.g-step-row.highlight .g-step-desc {{ color:#8C1D1D; font-weight:800; }}

/* Equipment & Item Set Cards on Parchment */
.g-item-list {{ display:flex; flex-direction:column; gap:16px; }}
.g-item-grid-2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
.g-item-card {{
  background:rgba(252,247,237,0.88);
  border:1.5px solid rgba(128,96,58,0.36);
  border-left:6px solid #2D8B4E;
  border-radius:10px;
  padding:16px 20px;
  display:flex; align-items:flex-start; gap:18px;
  box-shadow:0 3px 10px rgba(60,38,14,0.08);
}}
.g-item-card.q-3 {{ border-left-color:#1D6FA5; }}
.g-item-card.q-4 {{ border-left-color:#7E3AF2; }}
.g-item-icon {{
  width:68px; height:68px; border-radius:8px;
  border:2px solid #7A5C38; flex-shrink:0; object-fit:cover;
}}
.g-item-main {{ flex:1; min-width:0; }}
.g-item-head {{
  display:flex; align-items:baseline; justify-content:space-between; gap:10px;
  flex-wrap:wrap;
}}
.g-item-name {{ font-size:27px; font-weight:900; color:#1E703B; }}
.g-item-card.q-3 .g-item-name {{ color:#155A8A; }}
.g-item-card.q-4 .g-item-name {{ color:#6425C9; }}
.g-item-slot {{ font-size:20px; color:#735B40; font-weight:600; }}
.g-pills {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }}
.g-stat-pill {{
  background:rgba(110,85,54,0.12);
  border:1px solid rgba(110,85,54,0.24);
  color:#2B1D12; font-size:20px; font-weight:700;
  padding:3px 11px; border-radius:6px;
}}
.g-stat-pill.effect {{
  background:rgba(45,139,78,0.13);
  border-color:rgba(45,139,78,0.35);
  color:#195E32;
}}
.g-item-foot {{
  margin-top:10px; display:flex; align-items:center; gap:10px; flex-wrap:wrap;
  font-size:20px; color:#5A432C; font-weight:700;
}}
.g-fit-tag {{
  background:#9E2A2B; color:#FFFFFF;
  font-size:18px; font-weight:800; padding:2px 9px; border-radius:4px;
}}

/* FAQ & Back-Cover Pillar Box */
.g-faq-list {{ display:flex; flex-direction:column; gap:16px; margin-bottom:22px; }}
.g-faq-q {{ font-size:25px; font-weight:900; color:#9E2A2B; margin-bottom:4px; }}
.g-faq-a {{ font-size:22px; line-height:1.55; color:#2B1D12; font-weight:600; }}

.g-back-box {{
  margin-top:auto;
  background:rgba(252,246,234,0.78);
  border:2px solid rgba(128,96,58,0.45);
  border-radius:12px;
  padding:22px 26px;
}}
.g-back-head {{
  text-align:center; margin-bottom:16px;
}}
.g-back-title {{
  font-family:"Songti SC",serif;
  font-size:34px; font-weight:900; color:#23160C;
}}
.g-back-sub {{ font-size:21px; color:#6A5035; margin-top:4px; font-weight:600; }}
.g-pillar-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
.g-pillar {{
  background:rgba(235,220,192,0.75);
  border:1px solid rgba(128,96,58,0.35);
  border-radius:8px; padding:12px 16px;
}}
.g-pillar-t {{ font-size:23px; font-weight:900; color:#8C2318; }}
.g-pillar-d {{ font-size:19px; color:#4A3520; margin-top:3px; font-weight:600; }}

.p-footbar {{
  display:flex; align-items:center; justify-content:space-between;
  padding-top:14px; margin-top:16px;
  border-top:1.5px solid rgba(112,82,46,0.32);
  font-size:21px; color:#6E5233; font-weight:700;
}}
.p-inline-foot {{
  display:flex; align-items:center; justify-content:space-between;
  padding-top:12px; margin-top:16px;
  border-top:1px solid rgba(112,82,46,0.25);
  font-size:19px; color:#7A5E3D; font-weight:700;
}}
</style></head><body>
<div class="{shell_cls}" id="cardRoot">
  <div class="watermark-crest"></div>
  {header_html}
  <div class="p-main">
    {inner_html}
  </div>
  {footer_html}
</div>
</body></html>"""


# ═══════════════════════════════════════════════════════════════════════════
# 五、从 wow-forever 真源数据自动构建「无限冒险笔记（副本全指南）」
# ═══════════════════════════════════════════════════════════════════════════

def build_dungeon_notebook_spec(app_root: pathlib.Path, dungeon_id: str) -> Dict[str, Any]:
    """读取 wow-forever-web/app/data/ 下的已核真源数据，生成指定副本的手账+公众号双模态数据包。"""
    data_dir = app_root / "data"
    dungeons_doc = json.loads((data_dir / "dungeons.json").read_text(encoding="utf-8"))
    quests_doc = json.loads((data_dir / "dungeon-quests.json").read_text(encoding="utf-8"))["dungeons"]
    geo_doc = json.loads((data_dir / "dungeon-geo.json").read_text(encoding="utf-8"))["dungeons"]
    items_list = json.loads((data_dir / "items.json").read_text(encoding="utf-8"))["items"]
    items_detail = json.loads((data_dir / "items-detail.json").read_text(encoding="utf-8"))["items"]
    bis_doc = json.loads((data_dir / "bis.json").read_text(encoding="utf-8"))

    items_by_id = {str(it["id"]): it for it in items_list}
    all_dungeons = {
        d["id"]: d
        for d in (dungeons_doc.get("newDungeons") or []) + (dungeons_doc.get("classicDungeons") or [])
    }
    if dungeon_id not in all_dungeons:
        raise KeyError(f"未知副本 ID: {dungeon_id}（可选：{list(all_dungeons.keys())[:10]}...）")

    d = all_dungeons[dungeon_id]
    d_name = d["nameCn"]
    is_new_dungeon = d.get("kind") == "new" or d in (dungeons_doc.get("newDungeons") or [])
    lvl_range = d.get("levelRange") or "15-25"
    zone_cn = (d.get("zoneCn") or "").split("·")[0].strip()
    faction = d.get("faction") or ("联盟" if dungeon_id in ("deathmine", "the-stocks", "hall-of-thanes") else
                                   "部落" if dungeon_id in ("ragefire-chasm", "ruins-of-lordaeron") else "双阵营")

    quests = (quests_doc.get(dungeon_id) or {}).get("quests") or []
    geo = geo_doc.get(dungeon_id) or {}
    entry = geo.get("entry") or {}
    boss_pos = geo.get("bossPos") or {}
    bosses = d.get("bosses") or []
    drops = d.get("drops") or []

    # 图标与原画路径
    art_path = app_root / (d.get("art") or f"img/art/dungeons/{dungeon_id}.webp")
    entry_map_path = app_root / (entry.get("mapFile") or "img/art/maps/1436.webp")
    boss_map_path = app_root / (geo.get("bossMap") or "img/art/dungeonmaps/dmap_deadmines.webp")
    fac_icon_path = app_root / (
        "img/art/factions/horde.png" if "部落" in faction else "img/art/factions/alliance.png"
    )
    emblem_path = app_root / "img/art/panels/library.webp"

    total_xp = sum(int(q.get("xp") or 0) for q in quests)

    # 1. 组装地图坐标大头针（带防重叠偏移）
    entry_pins_html = []
    entry_placed: List[Tuple[float, float]] = []
    if entry.get("x") and entry.get("y"):
        ex, ey = float(entry["x"]), float(entry["y"])
        entry_placed.append((ex, ey))
        entry_pins_html.append(
            f'<div class="g-pin entry" style="left:{ex:.1f}%;top:{ey:.1f}%;">'
            f'<span class="dot"></span><span>副本入口 ({entry["x"]}, {entry["y"]})</span></div>'
        )
    seen_hubs = set()
    for q in quests:
        px, py = q.get("pickupX"), q.get("pickupY")
        p_map = q.get("pickupMap") or q.get("pickupZone") or ""
        if px and py and (entry.get("zone") or "")[:2] in p_map:
            hub_key = (round(px), round(py))
            if hub_key not in seen_hubs:
                seen_hubs.add(hub_key)
                dx, dy = float(px), float(py)
                for ex0, ey0 in entry_placed:
                    if abs(dx - ex0) < 22.0 and abs(dy - ey0) < 13.0:
                        dy = min(84.0, ey0 + 14.5) if ey0 < 65.0 else max(18.0, ey0 - 14.5)
                entry_placed.append((dx, dy))
                npc_short = (q.get("pickupNpc") or "接取点").split("·")[0][:6]
                entry_pins_html.append(
                    f'<div class="g-pin" style="left:{dx:.1f}%;top:{dy:.1f}%;">'
                    f'<span class="dot"></span><span>{_esc(npc_short)} ({px},{py})</span></div>'
                )

    boss_pins_html = []
    boss_legend_items = []
    placed_coords: List[Tuple[float, float]] = []
    for idx_b, (b_name, pos_list) in enumerate(list(boss_pos.items())[:8], 1):
        if not pos_list:
            continue
        bx = float(pos_list[0].get("x") or 50.0)
        by = float(pos_list[0].get("y") or 50.0)
        # 防重叠微调：若与已放置点过近，做螺旋偏移
        for px0, py0 in placed_coords:
            if abs(bx - px0) < 7.5 and abs(by - py0) < 9.5:
                bx = min(90.0, max(10.0, bx + (7.5 if idx_b % 2 == 0 else -7.5)))
                by = min(76.0, max(16.0, by + (8.0 if idx_b % 3 == 0 else -7.0)))
        placed_coords.append((bx, by))
        boss_pins_html.append(
            f'<div class="g-boss-num-pin" style="left:{bx:.1f}%;top:{by:.1f}%;">{idx_b}</div>'
        )
        boss_legend_items.append(f'<span>{idx_b}.{_esc(b_name[:5])}</span>')
    if boss_legend_items:
        boss_pins_html.append(f'<div class="g-map-legend">{"".join(boss_legend_items)}</div>')

    # 2. 组装 P2（副本总览与全任务速查表）
    q_rows_html = []
    for q in quests:
        q_name = q.get("nameCn") or "未知任务"
        pre = q.get("preQuest")
        p_zone = q.get("pickupZone") or "副本内"
        p_npc = q.get("pickupNpc") or ""
        px, py = q.get("pickupX"), q.get("pickupY")
        coord_txt = f" ({px}, {py})" if (px and py) else ""
        badge = (
            f'<span class="g-badge">需前置</span>' if pre else
            f'<span class="g-badge blue">本内接取</span>' if "副本" in p_zone or d_name in p_zone else
            f'<span class="g-badge olive">直接接取</span>'
        )
        xp_val = f'{int(q["xp"]):,} 经验' if q.get("xp") else f'Lv.{q.get("questLevel") or "--"}'
        req_txt = f'（{q["reqLevel"]}级可接）' if q.get("reqLevel") else ""
        q_rows_html.append(
            f'<div class="g-q-row">'
            f'<div class="g-q-left"><span class="g-q-name">{_esc(q_name)}</span>{badge}</div>'
            f'<div class="g-q-mid">{_esc(p_zone)} · {_esc(p_npc)}{_esc(coord_txt)} {_esc(req_txt)}</div>'
            f'<div class="g-q-right">{_esc(xp_val)}</div>'
            f'</div>'
        )

    boss_names_str = "、".join(b.get("nameCn") for b in bosses[:4] if b.get("nameCn"))
    if len(bosses) > 4:
        boss_names_str += f" 等 {len(bosses)} 位首领"

    entry_coord_str = (
        f'{entry.get("zone") or zone_cn} ({entry["x"]}, {entry["y"]})'
        if entry.get("x") else zone_cn
    )
    kpi_top = f"{total_xp:,} 经验" if total_xp else f"{len(quests)} 个副本任务"

    page2_inner = f"""
    <div class="g-header-row">
      <div>
        <div class="g-eyebrow">{'无限服新增五人副本' if is_new_dungeon else '经典五人副本'} · 冒险总览</div>
        <div class="g-title">{_esc(d_name)}</div>
      </div>
      <div class="g-kpi-right">
        <div class="g-kpi-big">{_esc(kpi_top)}</div>
        <div class="g-kpi-sub">{_esc(lvl_range)} 级 · {len(quests)} 个任务 · {len(bosses)} 位首领</div>
      </div>
    </div>
    <div class="g-callout">
      <span class="red">入口</span>　{_esc(entry_coord_str)}　｜　<span class="red">首领</span>　{_esc(boss_names_str)}
    </div>
    <div class="g-map-grid">
      <div class="g-map-box">
        <img src="{_file_uri(entry_map_path)}" />
        <div class="g-map-tag">区域入口与接取点 · {_esc(entry.get("zone") or zone_cn)}</div>
        {"".join(entry_pins_html)}
      </div>
      <div class="g-map-box">
        <img src="{_file_uri(boss_map_path)}" />
        <div class="g-map-tag">副本内部首领点位图（共 {len(bosses)} 首领）</div>
        {"".join(boss_pins_html)}
      </div>
    </div>
    <div class="g-quest-table">
      {"".join(q_rows_html)}
    </div>
    """

    # 3. 组装 P3（进本前准备与任务接取路线 · 火漆印章页）
    step_rows_html = []
    step_idx = 1
    for q in quests:
        q_name = q.get("nameCn") or ""
        p_zone = q.get("pickupZone") or zone_cn
        p_npc = q.get("pickupNpc") or "任务官"
        px, py = q.get("pickupX"), q.get("pickupY")
        coord_str = f" ({px}, {py})" if (px and py) else ""
        pre = q.get("preQuest")
        req_lv = q.get("reqLevel") or q.get("questLevel") or ""
        if pre:
            step_rows_html.append(
                f'<div class="g-step-row">'
                f'<div class="g-step-num">{step_idx}</div>'
                f'<div class="g-step-zone">{_esc(p_zone)}{_esc(coord_str)}</div>'
                f'<div class="g-step-desc">先找 <strong>{_esc(p_npc)}</strong> 完成前置链《{_esc(pre)}》（{req_lv}级可接）</div>'
                f'</div>'
            )
            step_idx += 1
            step_rows_html.append(
                f'<div class="g-step-row highlight">'
                f'<div class="g-step-num">{step_idx}</div>'
                f'<div class="g-step-zone">进本目标 · {_esc(q_name)}</div>'
                f'<div class="g-step-desc">接取《{_esc(q_name)}》（{q.get("xp") or "--"} 经验），进本击败对应首领或收集信物</div>'
                f'{_WAX_SEAL_SVG}'
                f'</div>'
            )
            step_idx += 1
        else:
            is_inside = ("副本" in p_zone) or (d_name in p_zone)
            hl_cls = "g-step-row highlight" if is_inside else "g-step-row"
            seal = _WAX_SEAL_SVG if is_inside else ""
            step_rows_html.append(
                f'<div class="{hl_cls}">'
                f'<div class="g-step-num">{step_idx}</div>'
                f'<div class="g-step-zone">{_esc(p_zone)}{_esc(coord_str)}</div>'
                f'<div class="g-step-desc">找 <strong>{_esc(p_npc)}</strong> 接取《{_esc(q_name)}》（{req_lv}级可接 · {q.get("xp") or "--"} 经验）</div>'
                f'{seal}'
                f'</div>'
            )
            step_idx += 1

    # 补充最终进本清剿汇总步
    step_rows_html.append(
        f'<div class="g-step-row highlight">'
        f'<div class="g-step-num">{step_idx}</div>'
        f'<div class="g-step-zone">副本内清剿 · {_esc(d_name)}</div>'
        f'<div class="g-step-desc">按点位图推进击败 {_esc(boss_names_str)}，一次交齐全部任务</div>'
        f'{_WAX_SEAL_SVG}'
        f'</div>'
    )

    min_req = min([int(q["reqLevel"]) for q in quests if q.get("reqLevel")] or [14])
    page3_inner = f"""
    <div class="g-header-row">
      <div>
        <div class="g-eyebrow">任务接取路线 · 前置与坐标核对</div>
        <div class="g-title">出发前任务路线</div>
      </div>
      <div class="g-kpi-right">
        <div class="g-kpi-big">最低 {min_req} 级可接</div>
        <div class="g-kpi-sub">盖有火漆印章为副本内核心节点</div>
      </div>
    </div>
    <div class="g-callout">
      <span class="red">跑本提醒</span>　进本前建议先核对任务日志；无前置任务可由已接队友在副本门口直接共享。
    </div>
    <div class="g-step-list">
      {"".join(step_rows_html[:7])}
    </div>
    """

    # 4. 组装 P4 & P5（【无限服独家】本副本新增/魔改特殊装备、套装与首领精良掉落）
    # 4.1 查该副本关联的套装（bis.json -> itemSets）
    dungeon_sets = []
    for iset in bis_doc.get("itemSets") or []:
        pieces = iset.get("pieces") or []
        if any(p.get("dungeonId") == dungeon_id for p in pieces):
            dungeon_sets.append(iset)

    # 4.2 查该副本的特殊掉落与精良掉落（优先无限新增/魔改 + 首领有名掉落）
    rich_drops = []
    seen_item_ids = set()
    # 每套装备优先收录首领掉落的核心部件（2件套全收，5件套优先收首领掉的那1-2件，留版面给副本特色武器与特效装）
    for iset in dungeon_sets:
        pieces = iset.get("pieces") or []
        limit_per_set = 2 if len(pieces) <= 3 else 1
        added_in_set = 0
        # 优先选非小怪掉的部件
        sorted_pieces = sorted(pieces, key=lambda p: ("小怪" not in str(p.get("src") or ""), p.get("dungeonId") == dungeon_id), reverse=True)
        for p in sorted_pieces:
            if added_in_set >= limit_per_set:
                break
            iid = str(p.get("item"))
            if iid not in seen_item_ids and iid in items_by_id:
                seen_item_ids.add(iid)
                rich_drops.append((iid, p.get("src") or d_name, iset.get("name")))
                added_in_set += 1

    for dr in drops:
        iid = str(dr.get("itemId"))
        if iid in seen_item_ids or iid not in items_by_id:
            continue
        it = items_by_id[iid]
        if "图样：" in (it.get("name") or "") or "结构图：" in (it.get("name") or "") or "配方：" in (it.get("name") or ""):
            continue
        det = items_detail.get(iid) or {}
        if not det.get("st") and it.get("quality", 1) < 3:
            continue
        seen_item_ids.add(iid)
        boss_cn = dr.get("bossCn") or "首领掉落"
        rich_drops.append((iid, f"{d_name} · {boss_cn}", None))

    # 排序：优先 有绿字特效/无限魔改 + 首领非小怪 + 套装代表件 + 高品质
    def _drop_sort_key(entry_tuple):
        iid, src_label, set_name = entry_tuple
        it = items_by_id.get(iid) or {}
        det = items_detail.get(iid) or {}
        st_lines = det.get("st") or []
        has_green = any("装备：" in s or "使用：" in s or "击中时" in s for s in st_lines)
        is_special = it.get("status") in ("new", "changed") or has_green
        not_trash = "小怪" not in src_label and "待实测" not in src_label
        return (int(not_trash and (is_special or bool(set_name))), int(bool(set_name)), int(has_green), int(not_trash), int(it.get("quality") or 1), int(it.get("ilvl") or 0))

    rich_drops.sort(key=_drop_sort_key, reverse=True)

    def _render_item_card_html(iid: str, src_label: str, set_name: Optional[str]) -> str:
        it = items_by_id.get(iid) or {}
        det = items_detail.get(iid) or {}
        q = int(it.get("quality") or 2)
        icon_file = app_root / "img/icons" / (it.get("icon") or "inv_misc_questionmark.jpg")
        st_raw = det.get("st") or []
        stat_pills = []
        effect_pills = []
        for s in st_raw:
            s_clean = s.strip()
            if not s_clean or s_clean in ("装备唯一", "唯一", "手指", "颈部", "背部"):
                continue
            if "（0/" in s_clean or "(0/" in s_clean:
                continue
            if any(k in s_clean for k in ("装备：", "使用：", "套装：", "击中时")):
                effect_pills.append(f'<span class="g-stat-pill effect">{_esc(s_clean)}</span>')
            elif len(stat_pills) < 4:
                stat_pills.append(f'<span class="g-stat-pill">{_esc(s_clean)}</span>')

        status_badge = ""
        if set_name:
            status_badge = f'<span class="g-fit-tag">套装 · {_esc(set_name)}</span>'
        elif it.get("status") == "new":
            status_badge = '<span class="g-fit-tag">无限新增</span>'
        elif it.get("status") == "changed":
            status_badge = '<span class="g-fit-tag">无限魔改</span>'

        slot_txt = f'{it.get("type") or ""} · 装等 {it.get("ilvl") or "--"} · 需 {it.get("rlvl") or "--"} 级'
        pills_all = "".join(stat_pills + effect_pills[:2])
        return (
            f'<div class="g-item-card q-{q}">'
            f'<img class="g-item-icon" src="{_file_uri(icon_file)}" />'
            f'<div class="g-item-main">'
            f'<div class="g-item-head">'
            f'<span class="g-item-name">{_esc(it.get("name"))}</span>'
            f'<span class="g-item-slot">{_esc(slot_txt)}</span>'
            f'</div>'
            f'<div class="g-pills">{pills_all}</div>'
            f'<div class="g-item-foot">'
            f'{status_badge}'
            f'<span>出处：{_esc(src_label.replace("副本：", ""))}</span>'
            f'</div>'
            f'</div>'
            f'</div>'
        )

    top_items_p4 = [_render_item_card_html(*x) for x in rich_drops[:4]]
    top_items_p5 = [_render_item_card_html(*x) for x in rich_drops[4:8]]

    set_summary_txt = (
        "、".join(f"《{s['name']}》（{len(s.get('pieces', []))}件套）" for s in dungeon_sets)
        if dungeon_sets else "无限服专属属性与精良掉落"
    )

    page4_inner = f"""
    <div class="g-header-row">
      <div>
        <div class="g-eyebrow">无限服专属装备库 · 核心必刷（一）</div>
        <div class="g-title">专属套装与特殊掉落</div>
      </div>
      <div class="g-kpi-right">
        <div class="g-kpi-big">{len(drops)} 件已核掉落</div>
        <div class="g-kpi-sub">图标与属性取自无限服客户端实测库</div>
      </div>
    </div>
    <div class="g-callout">
      <span class="red">重点关注</span>　本副本关联：{_esc(set_summary_txt)}。打到以下特殊词缀装备切勿直接卖店。
    </div>
    <div class="g-item-list">
      {"".join(top_items_p4)}
    </div>
    """

    page5_inner = f"""
    <div class="g-header-row">
      <div>
        <div class="g-eyebrow">首领精良战利品 · 核心必刷（二）</div>
        <div class="g-title">首领代表性掉落</div>
      </div>
      <div class="g-kpi-right">
        <div class="g-kpi-big">Lv.{_esc(lvl_range)} 毕业</div>
        <div class="g-kpi-sub">可在「跑本无限助手」小程序一键加入冒险清单</div>
      </div>
    </div>
    <div class="g-callout">
      <span class="red">数据说明</span>　以下为各首领代表性精良/优秀掉落（按本站纪律只列事实属性与归属，不标掉率百分比）。
    </div>
    <div class="g-item-list">
      {"".join(top_items_p5 if top_items_p5 else top_items_p4)}
    </div>
    """

    # 5. 组装 P6（常见问题避坑 FAQ & 封底「跑本无限助手」尾页）
    pre_quests = [q for q in quests if q.get("preQuest")]
    pre_faq_a = (
        "、".join(f"《{q['nameCn']}》（需先做《{q['preQuest']}》）" for q in pre_quests)
        + " 必须本人做完前置才能接，队友无法直接共享；其余无前置任务可在进本后由队友共享。"
        if pre_quests else
        f"本副本的 {len(quests)} 个任务均无冗长跨图前置，达到最低接取等级（{min_req} 级）即可找对应 NPC 接取，或由队友在副本内直接共享。"
    )

    page6_inner = f"""
    <div class="g-header-row">
      <div>
        <div class="g-eyebrow">跑本避坑指南 · 常见问题</div>
        <div class="g-title">常见问题与工具速查</div>
      </div>
      <div class="g-kpi-right">
        <div class="g-kpi-big">跑本无限助手</div>
        <div class="g-kpi-sub">小程序 · 网页 paoben.top</div>
      </div>
    </div>
    <div class="g-faq-list">
      <div>
        <div class="g-faq-q">Q1：队友在副本门口共享任务，为什么我接不到？</div>
        <div class="g-faq-a">{_esc(pre_faq_a)}</div>
      </div>
      <div>
        <div class="g-faq-q">Q2：{_esc(d_name)}的入口在哪？跑尸体容易迷路怎么办？</div>
        <div class="g-faq-a">副本入口位于 <strong>{_esc(entry_coord_str)}</strong>。进矿洞/大门后沿主路推进即可；建议对照第 02 页的「区域入口图」与「内部首领点位图」标记路线。</div>
      </div>
      <div>
        <div class="g-faq-q">Q3：无限服在这个副本里新增或改动了哪些值得留的装备？</div>
        <div class="g-faq-a">除常规首领蓝装外，重点留意第 04–05 页列出的 <strong>{_esc(set_summary_txt)}</strong>。手机微信小程序搜「跑本无限助手」可一键加入【冒险清单】，电脑双屏直接开 <strong>paoben.top</strong> 查大屏地图与 3D 配装。</div>
      </div>
    </div>
    <div class="g-back-box">
      <div class="g-back-head">
        <div class="g-back-title">跑本无限助手 · 电脑端 paoben.top</div>
        <div class="g-back-sub">手机小程序 + 电脑网页双端同源免费查，做你手边的跑本工具</div>
      </div>
      <div class="g-pillar-grid">
        <div class="g-pillar">
          <div class="g-pillar-t">📘 冒险笔记 · 38本全指南</div>
          <div class="g-pillar-d">38座副本入口坐标、内部首领点位与任务链</div>
        </div>
        <div class="g-pillar">
          <div class="g-pillar-t">⚔️ BIS配装 · 14-60级套装</div>
          <div class="g-pillar-d">练级过渡套、36套新增套装与60级团前BiS</div>
        </div>
        <div class="g-pillar">
          <div class="g-pillar-t">📜 练级天赋 · 245条实测宏</div>
          <div class="g-pillar-d">九职业练级推荐天赋模拟器与一键复制宏</div>
        </div>
        <div class="g-pillar">
          <div class="g-pillar-t">📰 无限服日报 · 蓝帖热修</div>
          <div class="g-pillar-d">每日官方在线修正、职业改动与版本动态</div>
        </div>
      </div>
    </div>
    """

    # 6. 同时组装公众号长文 sections 与小绿书配文
    prose_sections = [
        {
            "title": f"进本之前，先看清这 {len(quests)} 个任务的来处",
            "paragraphs": [
                f"**{d_name}**位于{zone_cn}（入口坐标 !!{entry_coord_str}!!），推荐等级 !!{lvl_range}级!!，副本内共有 !!{len(bosses)}位首领!!与 !!{len(quests)}个关联任务!!。",
                f"如果把这 !!{len(quests)}个任务!!在进本前全部接齐，一趟下来仅任务结算就能拿到约 !!{total_xp:,}点经验!!，还不含沿途精英怪与首领的额外产出。",
            ],
            "card_index": 1,
        },
        {
            "title": "接取路线与前置要求：哪些必须提前做？",
            "paragraphs": [
                f"很多队伍进本后才发现有人接不到共享任务——原因通常是卡在了**前置任务链**或**最低接取等级（{min_req}级）**。",
                f"出发前请对照下方路线图与坐标逐一检查任务日志；盖有**红色火漆印章**的步骤为进入**{d_name}**后的核心交付节点。",
            ],
            "card_index": 2,
        },
        {
            "title": "无限服专属新增套装与特殊掉落",
            "paragraphs": [
                f"与传统旧世不同，无限服在**{d_name}**里塞进了多件极具实用价值的**专属套装与特殊词缀装备**（含 {_esc(set_summary_txt)}）。",
                "下面这些装备的图标、护甲与绿字特效均已由本站从无限服客户端与实测库逐条核对，刷到后千万别顺手卖了商店。",
            ],
            "card_index": 3,
        },
        {
            "title": "首领核心战利品与跑本常见问题",
            "paragraphs": [
                f"除了特殊功能装，**{d_name}**各首领还出产多件 !!{lvl_range}级!! 阶段极其扎实的过渡蓝绿装。你可以打开「跑本无限助手」小程序，把目标装备一键加进自己的**冒险清单**。",
            ],
            "card_index": 4,
        },
    ]

    caption_text = (
        f"无限冒险笔记｜{d_name}副本任务与专属掉落全指南\n\n"
        f"去{d_name}之前，最怕两件事：一是到了副本门口才发现缺了前置任务，队友共享都接不到；"
        f"二是出了无限服新增的特殊词缀装备或新套装部件，不认识直接卖了商店。\n\n"
        f"这期《无限冒险笔记》把{d_name}（{lvl_range}级 · {faction}）的 {len(quests)} 个副本任务接取坐标、"
        f"区域入口与内部 {len(bosses)} 位首领点位图，以及无限服专属套装和代表性掉落全部整理在了一本手账里。\n\n"
        f"手机端微信搜「跑本无限助手」小程序随时勾选冒险清单，电脑双屏打开 paoben.top 查大屏地图、3D配装与 12.10 团本筹备。\n\n"
        f"#无限服 #副本攻略 #{d_name} #无限冒险笔记 #跑本无限助手"
    )

    return {
        "pack_id": f"grimoire-{dungeon_id}",
        "theme": "grimoire",
        "title": f"无限冒险笔记｜{d_name}副本任务与专属掉落全指南",
        "column_name": "无限冒险笔记",
        "date_str": datetime.now().strftime("%Y-%m-%d"),
        "dungeon_name": d_name,
        "subtitle": "无限冒险笔记 · 副本任务与专属掉落",
        "level_str": f"{lvl_range} 级",
        "faction": faction,
        "art_uri": _file_uri(art_path),
        "faction_icon_uri": _file_uri(fac_icon_path),
        "emblem_uri": _file_uri(emblem_path),
        "lead_text": f"一趟拿满 {total_xp:,} 任务经验，顺手刷齐无限服新增套装与特殊掉落——出发前先把这份手账翻一遍。",
        "pages": [
            {"phase": "总览", "inner_html": page2_inner},
            {"phase": "出发前", "inner_html": page3_inner},
            {"phase": "必刷掉落", "inner_html": page4_inner},
            {"phase": "必刷掉落", "inner_html": page5_inner},
            {"phase": "常见问题", "inner_html": page6_inner},
        ],
        "prose_sections": prose_sections,
        "closing_lines": [
            "接齐任务再进门，",
            "认准坐标不迷路，",
            "特殊掉落留好包，",
            "下一座副本我们接着记。",
        ],
        "footnote": f"注：本指南任务坐标、首领点位及物品属性均核自本站无限服数据库，按本站规则不标注掉率百分比。",
        "sources": [
            "电脑端资料站：paoben.top（38座副本点位、3D配装预览、12.10团本筹备）",
            "微信小程序：跑本无限助手（手机随身副本手册与冒险清单）",
            "DungeonsForever / QuestieDB / ForeverLevelingBiS 套装表",
        ],
        "caption_text": caption_text,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 六、从 wow-forever 热修与动态真源构建「无限服日报（暗调毛玻璃风）」
# ═══════════════════════════════════════════════════════════════════════════

def build_daily_hotfix_spec(app_root: pathlib.Path) -> Dict[str, Any]:
    """基于本站已核热修与副本/套装数据，构建「无限服日报」双模态（小绿书 3:4 + 公众号长文）数据包。"""
    emblem_path = app_root / "img/art/panels/spellbook.webp"
    hero_art_path = app_root / "img/art/dungeons/upper-blackrock-spire.webp"
    paladin_banner = app_root / "img/art/classbanners/paladin.webp"
    blackmaw_art = app_root / "img/art/dungeons/blackmaw-hold.webp"

    icon_flurry = app_root / "img/icons/ability_ghoulfrenzy.jpg"
    icon_seal = app_root / "img/icons/spell_holy_righteousnessaura.jpg"
    icon_shield = app_root / "img/icons/inv_shield_05.jpg"
    icon_bag = app_root / "img/icons/inv_misc_bag_10_blue.jpg"

    cards = [
        # Slide 1: 3:4 封面卡
        {
            "kind": "cover",
            "kicker": "热修与数据盘点 · 11.19",
            "title_line1": "黑上恢复预定难度",
            "title_line2": "防骑魂铸套改加法强",
            "subtitle": "奥山58级接取 · 阿迦玛甘之血本外可做 · 睡袋选点摆放",
        },
        # Slide 2 / Inline Card 1: 黑石塔上层 KPI 卡
        {
            "kind": "info",
            "accent": "#E5B869",
            "title_line1": "黑石塔上层",
            "title_line2": "又要认真打了",
            "title_line2_color": "#E06D3B",
            "kpis": [
                {"val": "10人", "label": "满编配置要求"},
                {"val": "生命+伤害", "label": "敌方数值同步回调"},
                {"val": "上层专属", "label": "黑下本次未提及"},
            ],
            "summary": "此前黑石塔上层（UBRS）敌人的生命值与伤害明显低于预定水平，热修后已恢复至设计难度，需要一支认真配合的10人满编队伍才能顺利通关。",
            "quote": {
                "text": "「前些天打得轻松，是数值偏低，不是副本本来就这样。」",
                "note": "官方热修说明 · 备战团本前先在跑本无限助手核对 60 级 Pre-Raid 配装",
            },
        },
        # Slide 3 / Inline Card 2: 防骑魂铸套 & 萨满乱舞 (stat_change + icon_rows)
        {
            "kind": "info",
            "accent": "#E5B869",
            "title_line1": "防骑的魂铸套",
            "title_line2": "力量换成了法术强度",
            "title_line2_color": "#E5B869",
            "stat_change": {
                "name": "魂铸（坦克版 T0.5）",
                "sub": "圣骑士防护向套装属性调整",
                "before": "力量",
                "after": "法术强度",
                "after_color": "#58A6FF",
            },
            "summary": "开发团队明确希望法术强度成为防护圣骑士建立仇恨与打出伤害的主属性。",
            "banner_uri": _file_uri(paladin_banner),
            "icon_section_title": "同批职业与增益修复",
            "icon_rows": [
                {
                    "icon_uri": _file_uri(icon_flurry),
                    "title": "萨满祭司 · 乱舞",
                    "badge": "机制修复",
                    "desc": "风怒图腾的攻击命中时，乱舞不会再被错误消耗层数。",
                },
                {
                    "icon_uri": _file_uri(icon_seal),
                    "title": "暴风城的力量 / 酋长的祝福",
                    "badge": "世界增益",
                    "desc": "角色死亡时会正确消失，且只会施加给玩家角色。",
                },
            ],
        },
        # Slide 4 / Inline Card 3: 战场与 58 级门槛 (hero_stat + compare_boxes)
        {
            "kind": "info",
            "accent": "#4EA1E8",
            "title_line1": "奥特兰克山谷",
            "title_line2": "阵营任务要58级才能接",
            "title_line2_color": "#4EA1E8",
            "hero_stat": {
                "num": "58",
                "unit": "级起才能接取",
                "desc": "双阵营奥山入场任务统一上调接取门槛",
                "color": "#4EA1E8",
                "align": "left",
            },
            "compare_boxes": [
                {"label": "联盟阵营任务", "text": "《奥特兰克的战斗》\n需角色达到 58 级", "color": "#639BFF"},
                {"label": "部落阵营任务", "text": "《为奥特兰克而战》\n需角色达到 58 级", "color": "#E05A47"},
            ],
            "icon_rows": [
                {
                    "icon_uri": _file_uri(icon_shield),
                    "title": "战歌峡谷 · 出发房间禁骑乘",
                    "badge": "战场修复",
                    "desc": "开场前在战歌峡谷出发房间内提前上马的问题已修复。",
                }
            ],
        },
        # Slide 5 / Inline Card 4: 辛德拉与世界任务胶囊表 (pill_rows)
        {
            "kind": "info",
            "accent": "#52B788",
            "title_line1": "辛德拉与世界任务",
            "title_line2": "附近队友一起算进度",
            "title_line2_color": "#52B788",
            "pill_rows": [
                {
                    "tag": "辛德拉",
                    "tone": "green",
                    "title": "修复水晶塔进度共享给附近队友，水晶之心全队可拾取",
                    "sub": "《回家之路》护送 NPC 洛克伦移动速度放缓，刺背碎颅者施法频率降低",
                },
                {
                    "tag": "剃刀高地",
                    "tone": "green",
                    "title": "《阿迦玛甘之血》不再是副本任务，门外精英区即可完成",
                    "sub": "剃刀高地位于贫瘠之地最南端，毗邻千针石林",
                },
                {
                    "tag": "舒适的睡袋",
                    "tone": "brown",
                    "title": "睡袋改为像猎人陷阱一样选点摆放，走入范围即显休息光环",
                    "sub": "配合《旅途小憩》插件可直观监控休息层数与队友同框倒计时",
                },
                {
                    "tag": "暴风城/湿地",
                    "tone": "brown",
                    "title": "军情七处马迪亚斯·肖可正常向潜行者交付《拉文霍德庄园》信件",
                    "sub": "湿地《大地上的脓疱》与千针石林《新的矿石样本》任务怪刷新数量上调",
                },
            ],
        },
        # Slide 6 / Inline Card 5: 团本前夕跑本准备时间线 (timeline)
        {
            "kind": "info",
            "accent": "#E5B869",
            "title_line1": "备战 60 级满级与团本",
            "title_line2": "这三件事现在就能查",
            "title_line2_color": "#E5B869",
            "timeline": [
                {
                    "time": "14–58 级练级期",
                    "title": "36 套五人本与无限服新增套装收集",
                    "desc": "死矿同谋佳偶对戒、洛丹伦腐疗者套、达拉然紫罗兰巫师套等均已入库",
                    "color": "#52B788",
                },
                {
                    "time": "58–60 级满级冲刺",
                    "title": "九职业 27 套团本前（Pre-Raid）BiS 配装核对",
                    "desc": "黑上恢复预定难度后，进本前先在跑本无限助手锁定本专精必刷部位与出处",
                    "color": "#E5B869",
                },
                {
                    "time": "60 级第一阶段团本",
                    "title": "18 套海加尔峰 T1 职业套装名录",
                    "desc": "多专精 T1 部件编号与护甲定位已在网页端与小程序同步上线",
                    "color": "#4EA1E8",
                },
            ],
            "quote": {
                "text": "打开微信小程序「跑本无限助手」，把要刷的副本任务和团前 BiS 一键加入冒险清单。",
                "note": "数据与本站网页资料库同源同步",
            },
        },
    ]

    sections = [
        {
            "title": "黑石塔上层，恢复预定难度",
            "paragraphs": [
                "此前**黑石塔上层**敌人的生命值和伤害都明显低于预定水平，这次热修一并回调。蓝帖明确提到，现在又需要一支认真配合的 !!10人满编队伍!! 才能顺利通关，具体上调幅度未公布，黑石塔下层本次没有提及。",
                "对于刚满 !!60级!! 准备刷雷德双刀、石楠之环或各职业 **团本前（Pre-Raid）BiS** 的玩家来说，进本前建议先组齐标准配置。",
            ],
            "card_index": 1,
        },
        {
            "title": "防骑的魂铸套，力量换成了法术强度",
            "paragraphs": [
                "坦克版 T0.5 **「魂铸」**套装原来提供的力量属性，在本次热修中正式改为了**法术强度**。开发团队解释，希望让法术强度成为防护圣骑士制造伤害与仇恨的主要属性。",
                "另外还有两条职业与增益修复：风怒图腾命中时，萨满祭司的**乱舞**不会再误掉层数；**暴风城的力量**与**酋长的祝福**在角色死亡时会正确消失，且只会施加给玩家角色。",
            ],
            "card_index": 2,
        },
        {
            "title": "奥特兰克山谷，阵营任务要 58 级才能接",
            "paragraphs": [
                "奥山两边的阵营入场任务——联盟《奥特兰克的战斗》与部落《为奥特兰克而战》，现在统一调整为 @@58级@@ 才能接取。同时，战歌峡谷开场前在出发房间里提前骑上坐骑的问题也已修复。",
            ],
            "card_index": 3,
        },
        {
            "title": "辛德拉的水晶塔、睡袋摆放与世界任务优化",
            "paragraphs": [
                "辛德拉声望与任务体验轻松了不少：**修复水晶塔**的进度现在会共享给附近队友，**水晶之心**任务掉落全队每个人都能拾取；剃刀高地的《阿迦玛甘之血》也不再要求进副本，门外精英区就能做完。",
                "备受练级玩家好评的**舒适的睡袋**，现在改成了像猎人陷阱一样**选点摆放**，走进范围就会出现休息光环。",
            ],
            "card_index": 4,
        },
        {
            "title": "备战满级与团本：跑本无限助手已同步 27 套团前 BiS",
            "paragraphs": [
                "随着黑上难度回归与满级玩家增多，本站与「跑本无限助手」小程序已同步更新 !!36套!! 14–58 级练级套装、九职业 !!27套!! 60 级团前 Pre-Raid BiS（共 !!422件!! 装备中文出处）以及 !!18套!! 海加尔峰 T1 名录，方便进本前随手核对。",
            ],
            "card_index": 5,
        },
    ]

    caption_text = (
        "无限服日报｜黑上难度回归，防骑魂铸套改法强\n\n"
        "暴雪 11 月 17 日热修，最大的一条落在黑石塔上层：此前黑上的敌人血量和伤害都低于预定，"
        "这次一起回调了，现在又要一支认真打的 10 人满编队伍才过得去。\n\n"
        "防骑的坦克版 T0.5「魂铸」，原来给的力量换成了法术强度；萨满风怒图腾打中时，乱舞不会再误掉层数。\n\n"
        "奥山两边的阵营任务现在都要 58 级才能接；《阿迦玛甘之血》改在剃刀高地门外精英区就能做完；"
        "舒适的睡袋现在能像猎人陷阱一样选点摆放。\n\n"
        "想查 38 座副本掉落、14–60 级套装与九职业团前 BiS 配装：手机微信搜「跑本无限助手」小程序，电脑双屏直接开 paoben.top 查看。\n\n"
        "#无限服日报 #魔兽世界无限 #黑石塔上层 #跑本无限助手 #热修速递"
    )

    return {
        "pack_id": "daily-hotfix-1117",
        "theme": "frosted-daily",
        "title": "11.17热修：黑上恢复预定难度，防骑魂铸套改加法强",
        "column_name": "无限服日报",
        "date_str": "11.19",
        "source_label": "暴雪官方蓝帖（11月17日热修）与本站数据库",
        "hero_art_uri": _file_uri(hero_art_path),
        "emblem_uri": _file_uri(emblem_path),
        "lead_text": "黑石塔上层恢复了原本的 10 人满编难度，防骑 T0.5 魂铸套由力量改为法术强度；辛德拉任务共享进度，睡袋也改成了选点摆放。",
        "cards": cards,
        "prose_sections": sections,
        "closing_lines": [
            "黑上恢复满编难度，",
            "防骑魂铸改走法强，",
            "野外任务减负提速，",
            "进本前先核好你的配装。",
        ],
        "footnote": "注：热修条目按美服蓝帖发布时间整理，国服具体生效时间以官方公告与游戏内实装为准。",
        "sources": [
            "电脑端资料站：paoben.top（大屏查表、3D配装预览、12.10团本筹备）",
            "微信小程序：跑本无限助手（60级团前BiS、副本手册与宏命令）",
            "暴雪官方论坛蓝帖（11月17日在线修正说明）",
        ],
        "caption_text": caption_text,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 七、Playwright 渲染流水线（同时输出 carousel 3:4 图包 + wechat 内嵌卡与 article.html）
# ═══════════════════════════════════════════════════════════════════════════

def _render_fixed_page(page, html_str: str, out_png: pathlib.Path, width: int, height: int) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tf:
        tf.write(html_str)
        tmp_path = pathlib.Path(tf.name)
    try:
        page.set_viewport_size({"width": width, "height": height})
        page.goto(tmp_path.resolve().as_uri())
        page.wait_for_timeout(180)
        el = page.query_selector("#cardRoot")
        if el:
            natural_h = page.evaluate("document.querySelector('#cardRoot').scrollHeight")
            if natural_h > height:
                scale = height / float(natural_h)
                scaled_w = width / scale
                scaled_h = height / scale
                page.add_style_tag(
                    content=(
                        f"#cardRoot{{transform:scale({scale:.4f});transform-origin:top left;"
                        f"width:{scaled_w:.2f}px !important;height:{scaled_h:.2f}px !important;}}"
                    )
                )
                page.wait_for_timeout(60)
        page.screenshot(path=str(out_png), clip={"x": 0, "y": 0, "width": width, "height": height})
    finally:
        tmp_path.unlink(missing_ok=True)


def _render_auto_height_card(page, html_str: str, out_png: pathlib.Path, width: int = 1080) -> Tuple[int, int]:
    """渲染公众号内嵌卡片（宽度固定 1080px，高度按内容实际高度自适应裁切，不留大块空白）。"""
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tf:
        tf.write(html_str)
        tmp_path = pathlib.Path(tf.name)
    try:
        page.set_viewport_size({"width": width, "height": 1800})
        page.goto(tmp_path.resolve().as_uri())
        page.wait_for_timeout(180)
        box = page.evaluate("""() => {
            const el = document.querySelector('#cardRoot') || document.body;
            const rect = el.getBoundingClientRect();
            return { width: Math.ceil(rect.width), height: Math.ceil(rect.height) };
        }""")
        h = max(320, min(1600, int(box.get("height") or 760)))
        page.screenshot(path=str(out_png), clip={"x": 0, "y": 0, "width": width, "height": h})
        return width, h
    finally:
        tmp_path.unlink(missing_ok=True)


def _launch_browser(p):
    """优先走 Playwright 默认 Chromium；若本机未下载 ms-playwright 壳，则回退系统 Chrome / Edge。"""
    try:
        return p.chromium.launch(headless=True)
    except Exception:
        pass
    for ch in ("chrome", "msedge"):
        try:
            return p.chromium.launch(headless=True, channel=ch)
        except Exception:
            pass
    for exe in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ):
        if os.path.isfile(exe):
            return p.chromium.launch(headless=True, executable_path=exe)
    raise RuntimeError("未找到可用的 Chromium / Chrome / Edge 浏览器可执行文件")


def render_pack(spec: Dict[str, Any], out_root: pathlib.Path, brand_name: str = "跑本无限助手") -> Dict[str, Any]:
    """使用 Playwright 渲染一套完整双模态包（carousel/ + wechat/）。"""
    from playwright.sync_api import sync_playwright

    pack_dir = out_root / spec["pack_id"]
    carousel_dir = pack_dir / "carousel"
    wechat_dir = pack_dir / "wechat"
    carousel_dir.mkdir(parents=True, exist_ok=True)
    wechat_dir.mkdir(parents=True, exist_ok=True)

    theme = spec["theme"]
    column_name = spec["column_name"]
    date_str = spec["date_str"]
    emblem_uri = spec.get("emblem_uri") or ""

    carousel_files: List[str] = []
    inline_files: List[str] = []

    with sync_playwright() as p:
        browser = _launch_browser(p)
        page = browser.new_page(viewport={"width": 1080, "height": 1440}, device_scale_factor=1)

        # 1. 渲染公众号首尾栏目横幅
        header_png = wechat_dir / "header_banner.png"
        footer_png = wechat_dir / "footer_cta.png"
        _render_fixed_page(
            page,
            build_header_banner_html(brand_name, column_name, emblem_uri),
            header_png,
            1080,
            120,
        )
        _render_fixed_page(
            page,
            build_footer_cta_html(
                brand_name,
                column_name,
                emblem_uri,
                qrcode_uri=spec.get("qrcode_uri") or _find_mini_qrcode_uri(),
            ),
            footer_png,
            1080,
            440,
        )

        if theme == "grimoire":
            pages_spec = spec["pages"]
            total_slides = 1 + len(pages_spec)

            # P1 皮质封面 (3:4)
            cover_png = carousel_dir / "slide_01.png"
            cover_html = build_grimoire_cover_html(
                dungeon_name=spec["dungeon_name"],
                subtitle=spec["subtitle"],
                level_str=spec["level_str"],
                faction=spec["faction"],
                art_uri=spec["art_uri"],
                faction_icon_uri=spec["faction_icon_uri"],
                brand_name=brand_name,
            )
            _render_fixed_page(page, cover_html, cover_png, 1080, 1440)
            shutil.copyfile(cover_png, wechat_dir / "hero_cover.png")
            carousel_files.append("carousel/slide_01.png")

            # P2..Pn 羊皮纸内页（同时渲 3:4 carousel 版 + 1080xauto 公众号内嵌版）
            for idx_p, pg in enumerate(pages_spec, 2):
                s_png = carousel_dir / f"slide_{idx_p:02d}.png"
                s_html = wrap_grimoire_page_html(
                    pg["inner_html"],
                    dungeon_name=spec["dungeon_name"],
                    faction=spec["faction"],
                    phase_active=pg["phase"],
                    page_num=idx_p,
                    faction_icon_uri=spec["faction_icon_uri"],
                    mode="carousel",
                    brand_name=brand_name,
                )
                _render_fixed_page(page, s_html, s_png, 1080, 1440)
                carousel_files.append(f"carousel/slide_{idx_p:02d}.png")

                c_idx = idx_p - 1
                c_png = wechat_dir / f"card_{c_idx:02d}.png"
                c_html = wrap_grimoire_page_html(
                    pg["inner_html"],
                    dungeon_name=spec["dungeon_name"],
                    faction=spec["faction"],
                    phase_active=pg["phase"],
                    page_num=idx_p,
                    faction_icon_uri=spec["faction_icon_uri"],
                    mode="inline",
                    brand_name=brand_name,
                )
                _render_auto_height_card(page, c_html, c_png, 1080)
                inline_files.append(f"card_{c_idx:02d}.png")

        else:
            # theme == "frosted-daily"
            cards = spec["cards"]
            total_slides = len(cards)
            bg_uri = spec["hero_art_uri"]

            # 自动从本篇信息卡提取最多 6 个真实装备/职业/技能图标用于封面陈列（确保封面强贴题）
            auto_cover_icons: List[Dict[str, Any]] = []
            seen_ic = set()
            tt_total = 0
            for c_item in cards:
                if c_item.get("kind") == "cover":
                    continue
                for tt in (c_item.get("item_tooltips") or []):
                    if isinstance(tt, dict):
                        tt_total += 1
                        uri = tt.get("icon_uri") or ""
                        if uri and uri not in seen_ic and len(auto_cover_icons) < 6:
                            seen_ic.add(uri)
                            auto_cover_icons.append({
                                "icon_uri": uri,
                                "label": tt.get("name") or "",
                                "quality": tt.get("quality") or "史诗",
                            })
                for ir in (c_item.get("icon_rows") or []):
                    if isinstance(ir, dict):
                        uri = ir.get("icon_uri") or ""
                        if uri and uri not in seen_ic and len(auto_cover_icons) < 6:
                            seen_ic.add(uri)
                            auto_cover_icons.append({
                                "icon_uri": uri,
                                "label": ir.get("title") or "",
                                "quality": "",
                            })

            cov_card = cards[0] if (cards and cards[0].get("kind") == "cover") else {}
            if cov_card and not cov_card.get("cover_icons") and auto_cover_icons:
                cov_card["cover_icons"] = auto_cover_icons
            cover_icons = cov_card.get("cover_icons") or auto_cover_icons
            stat_badge = f"含 {tt_total} 件实装装备属性" if tt_total >= 2 else ""

            # 保存公众号主封面图（1080x720 主题海报封面，核心信息居于 2.35:1 安全带内）
            hero_html = build_wechat_hero_cover_html(
                bg_uri=bg_uri,
                column_name=column_name,
                date_str=date_str,
                kicker=cov_card.get("kicker") or f"{column_name} · 今日速览",
                title_line1=cov_card.get("title_line1") or spec["title"][:10],
                title_line2=cov_card.get("title_line2") or "",
                subtitle=cov_card.get("subtitle") or (spec.get("lead_text") or "")[:28],
                cover_icons=cover_icons,
                stat_badge=stat_badge,
                brand_name=brand_name,
            )
            _render_fixed_page(page, hero_html, wechat_dir / "hero_cover.png", 1080, 720)

            info_idx = 0
            for idx_c, card in enumerate(cards, 1):
                s_png = carousel_dir / f"slide_{idx_c:02d}.png"
                s_html = build_frosted_card_html(
                    card,
                    bg_uri=bg_uri,
                    mode="carousel",
                    idx=idx_c,
                    total=total_slides,
                    column_name=column_name,
                    date_str=date_str,
                    source_label=spec.get("source_label") or "官方蓝帖与本站实测库",
                    brand_name=brand_name,
                )
                _render_fixed_page(page, s_html, s_png, 1080, 1440)
                carousel_files.append(f"carousel/slide_{idx_c:02d}.png")

                if card.get("kind") != "cover":
                    info_idx += 1
                    c_png = wechat_dir / f"card_{info_idx:02d}.png"
                    c_html = build_frosted_card_html(
                        card,
                        bg_uri=bg_uri,
                        mode="inline",
                        idx=idx_c,
                        total=total_slides,
                        column_name=column_name,
                        date_str=date_str,
                        source_label=spec.get("source_label") or "官方蓝帖与本站实测库",
                        brand_name=brand_name,
                    )
                    _render_auto_height_card(page, c_html, c_png, 1080)
                    inline_files.append(f"card_{info_idx:02d}.png")

        browser.close()

    # 2. 保存小绿书 / 头条图文配文及全览预览页
    caption_txt = spec.get("caption_text") or ""
    (carousel_dir / "caption.txt").write_text(caption_txt, encoding="utf-8")
    (carousel_dir / "preview.html").write_text(
        compile_carousel_preview_html(
            pack_id=spec["pack_id"],
            title=spec["title"],
            column_name=column_name,
            date_str=date_str,
            caption_text=caption_txt,
            slides=carousel_files,
            article_url="../wechat/article.html",
        ),
        encoding="utf-8",
    )

    # 3. 编译公众号内联 HTML (article.html) 与 Markdown (article.md)
    info_cards_only = [c for c in (spec.get("cards") or []) if c.get("kind") != "cover"]
    wx_sections = []
    md_lines = [f"# {spec['title']}", "", f"> {spec.get('lead_text') or ''}", ""]
    for sec in spec.get("prose_sections") or []:
        c_idx = int(sec.get("card_index") or 1)
        card_rel = f"card_{c_idx:02d}.png" if c_idx <= len(inline_files) else ""
        sec_tooltips = sec.get("item_tooltips")
        if not sec_tooltips and 1 <= c_idx <= len(info_cards_only):
            sec_tooltips = info_cards_only[c_idx - 1].get("item_tooltips")
        wx_sections.append({
            "title": sec.get("title") or "",
            "paragraphs": sec.get("paragraphs") or [],
            "item_tooltips": sec_tooltips or [],
            "card_img_rel": card_rel,
        })
        if sec.get("title"):
            md_lines.extend([f"## {sec['title']}", ""])
        for para in sec.get("paragraphs") or []:
            md_lines.extend([para, ""])
        for it in sec_tooltips or []:
            meta_txt = " · ".join(str(x) for x in (
                it.get("quality"),
                f"装等 {it['ilvl']}" if it.get("ilvl") else "",
                it.get("bind"),
                it.get("unique"),
                it.get("slot_type"),
                it.get("source"),
                it.get("meta_right"),
            ) if x)
            md_lines.append(f"- **{it.get('name')}**（{meta_txt}）")
            for u in it.get("use_lines") or []:
                md_lines.append(f"  - `{u}`")
            if it.get("flavor"):
                md_lines.append(f"  - *{it['flavor']}*")
            md_lines.append("")
        if card_rel:
            md_lines.extend([f"![{_esc(sec.get('title') or '信息图卡')}]({card_rel})", ""])

    talent_builds = list(spec.get("talent_builds") or [])
    verified_talents = [b for b in talent_builds if b.get("status") == "verified" and b.get("panel_img_rel")]

    if verified_talents:
        md_lines.extend(["## 推荐天赋加点（模拟器实图）", ""])
        for b in verified_talents:
            cls_cn = b.get("class_cn") or b.get("class_id") or ""
            md_lines.extend([
                f"- **{cls_cn}**：{b.get('summary_text') or ''}（`?c={b.get('class_id')}&p={b.get('p_code')}`）",
                "",
                f"![{cls_cn}天赋加点示意图]({b['panel_img_rel']})",
                "",
            ])

    article_html = compile_wechat_article_html(
        title=spec["title"],
        column_name=column_name,
        date_str=date_str,
        lead_text=spec.get("lead_text") or "",
        hero_img_rel="hero_cover.png",
        header_banner_rel="header_banner.png",
        footer_banner_rel="footer_cta.png",
        sections=wx_sections,
        closing_lines=spec.get("closing_lines") or [],
        footnote=spec.get("footnote") or "",
        sources=spec.get("sources") or [],
        talent_builds=talent_builds,
    )
    (wechat_dir / "article.html").write_text(article_html, encoding="utf-8")
    (wechat_dir / "article.md").write_text("\n".join(md_lines), encoding="utf-8")

    # 4. 拍一张公众号文章长图预览（供审稿与验证）
    with sync_playwright() as p:
        browser = _launch_browser(p)
        pg = browser.new_page(viewport={"width": 760, "height": 1200}, device_scale_factor=1)
        pg.goto((wechat_dir / "article.html").resolve().as_uri())
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(wechat_dir / "article_preview.png"), full_page=True)
        browser.close()

    manifest = {
        "pack_id": spec["pack_id"],
        "theme": theme,
        "title": spec["title"],
        "column_name": column_name,
        "date_str": date_str,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "carousel_slides": carousel_files,
        "carousel_caption": "carousel/caption.txt",
        "carousel_preview_html": "carousel/preview.html",
        "wechat_article_html": "wechat/article.html",
        "wechat_article_md": "wechat/article.md",
        "wechat_inline_cards": [f"wechat/{f}" for f in inline_files],
    }
    if talent_builds:
        manifest["talent_builds"] = [
            {
                "status": b.get("status"),
                "class_id": b.get("class_id"),
                "class_cn": b.get("class_cn"),
                "summary_text": b.get("summary_text"),
                "p_code": b.get("p_code"),
                "simulator_url": b.get("simulator_url"),
                "panel_img_rel": b.get("panel_img_rel"),
                "ref_frame_rel": b.get("ref_frame_rel"),
                "tree_names": b.get("tree_names"),
                "tree_sums": b.get("tree_sums"),
                "total_points": b.get("total_points"),
                "key_talents": b.get("key_talents"),
                "issues": b.get("issues"),
            }
            for b in talent_builds
        ]
    (pack_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def render_poster_companion_html(
    folder: pathlib.Path,
    manifest: Dict[str, Any],
    plan: Dict[str, Any],
    promo: Optional[Dict[str, Any]] = None,
    brand_name: str = "跑本无限助手",
) -> str:
    """将 video2text 现有的攻略清单/海报 plan 同步渲染为「宁静之光风格」的公众号内联 HTML (article.html)
    及去顶底栏的 1080px 毛玻璃内嵌信息卡 (inline_card_01.png...)，彻底消除图文重复与素文简陋问题。
    """
    from playwright.sync_api import sync_playwright

    folder = pathlib.Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    try:
        app_root = _find_app_root()
    except FileNotFoundError:
        app_root = None

    # 尝试加载同音字归一化与 wow_cards 图标映射
    try:
        from . import term_glossary
        norm_fn = lambda s: term_glossary.normalize_wow(str(s or ""), manifest.get("title") or "魔兽无限")
    except Exception:
        norm_fn = lambda s: str(s or "")

    try:
        from .graphics import icons as v2t_icons
    except Exception:
        v2t_icons = None

    title = norm_fn(manifest.get("title") or plan.get("title") or "无限服攻略指南")
    column_name = "无限服攻略"
    date_str = datetime.now().strftime("%m.%d")

    emblem_uri = _file_uri(app_root / "img/art/panels/library.webp") if app_root else ""
    default_bg_uri = _file_uri(app_root / "img/art/scenes/guangshu.webp") if app_root else ""

    pages = plan.get("pages") or [plan]
    has_cover = bool(pages and pages[0].get("checklist_cover"))
    content_pages = pages[1:] if has_cover and len(pages) > 1 else pages

    # 挑选一张最贴切的主题原画作为整篇毛玻璃卡片的统一底板
    bg_uri = default_bg_uri
    if v2t_icons and app_root:
        for pg in pages:
            for nm in [pg.get("title") or ""] + [c.get("t") or "" for c in (pg.get("cards") or [])]:
                cmeta = v2t_icons.card_visual(norm_fn(nm))
                art_rel = cmeta.get("banner") or cmeta.get("map_img")
                if art_rel:
                    p_art = v2t_icons.visual_path("art", art_rel)
                    if p_art:
                        bg_uri = p_art.as_uri()
                        break
            if bg_uri != default_bg_uri:
                break

    wx_sections: List[Dict[str, Any]] = []
    lead_points = [norm_fn(pg.get("title") or "") for pg in content_pages if pg.get("title")]
    lead_text = (
        f"本文共整理 {len(content_pages)} 个核心部分（{' / '.join(lead_points[:4])}），"
        f"关键图标、数值与出处已对照无限服数据库核实。"
        if lead_points else
        "核心要点与属性出处已对照无限服数据库核实。"
    )

    with sync_playwright() as p:
        browser = _launch_browser(p)
        page = browser.new_page(viewport={"width": 1080, "height": 1440}, device_scale_factor=1)

        _render_fixed_page(
            page,
            build_header_banner_html(brand_name, column_name, emblem_uri),
            folder / "header_banner.png",
            1080,
            120,
        )
        _render_fixed_page(
            page,
            build_footer_cta_html(
                brand_name,
                column_name,
                emblem_uri,
                qrcode_uri=_find_mini_qrcode_uri(app_root),
            ),
            folder / "footer_cta.png",
            1080,
            440,
        )

        for idx_s, pg in enumerate(content_pages, 1):
            sec_title = norm_fn(pg.get("title") or f"要点 {idx_s}")
            sec_sub = norm_fn(pg.get("subtitle") or "")
            raw_cards = list(pg.get("cards") or []) + list(pg.get("contrast") or [])
            if pg.get("warn"):
                raw_cards.append(pg["warn"])

            icon_rows = []
            paragraphs = []
            if sec_sub:
                paragraphs.append(f"**{sec_sub}**。")

            prose_bits = []
            for c in raw_cards:
                ct = norm_fn(c.get("t") or "").strip()
                cd = norm_fn(c.get("d") or "").strip()
                if not ct and not cd:
                    continue
                ic_uri = ""
                badge_txt = ""
                if v2t_icons:
                    cmeta = v2t_icons.card_visual(ct)
                    ic_path = v2t_icons.visual_path("icons", cmeta.get("icon"))
                    if ic_path:
                        ic_uri = ic_path.as_uri()
                    badge_txt = cmeta.get("meta") or ""
                    st_line = cmeta.get("stats") or ""
                    if st_line and st_line not in cd:
                        cd = f"{cd}（数据库核对属性：{st_line}）" if cd else st_line
                icon_rows.append({
                    "icon_uri": ic_uri,
                    "title": ct,
                    "badge": badge_txt,
                    "desc": cd,
                })
                prose_bits.append(f"**{ct}**：{cd}")

            # 组装克制的 1~2 段短叙事正文（突出重点，具体细项交由下方毛玻璃信息卡展示）
            if len(prose_bits) <= 2:
                paragraphs.extend(prose_bits)
            else:
                paragraphs.append("；".join(prose_bits[:2]) + "。")
                paragraphs.append("；".join(prose_bits[2:4]) + "。具体属性与要点对照见下方图卡：")

            card_spec = {
                "kind": "info",
                "accent": "#E5B869",
                "icon_section_title": f"{sec_title} · 核心要点速查",
                "icon_rows": icon_rows,
            }
            bignum = pg.get("bignum") or {}
            if bignum.get("v"):
                card_spec["hero_stat"] = {
                    "num": norm_fn(bignum.get("v")),
                    "unit": norm_fn(bignum.get("label") or ""),
                    "desc": norm_fn(bignum.get("note") or ""),
                    "color": "#E5B869",
                    "align": "center",
                }

            card_filename = f"inline_card_{idx_s:02d}.png"
            c_html = build_frosted_card_html(
                card_spec,
                bg_uri=bg_uri,
                mode="inline",
                idx=idx_s,
                total=len(content_pages),
                column_name=column_name,
                date_str=date_str,
                brand_name=brand_name,
            )
            _render_auto_height_card(page, c_html, folder / card_filename, 1080)
            wx_sections.append({
                "title": sec_title,
                "paragraphs": paragraphs,
                "card_img_rel": card_filename,
            })

        browser.close()

    hero_rel = manifest.get("pages", [{}])[0].get("file") or "poster_p1.png"
    src_note = norm_fn(manifest.get("public_source_note") or "本站无限服数据库与公开攻略核对整理")
    promo_copy = (promo or {}).get("copy") or "想查 38 座副本入口、任务坐标与 14–60 级配装：手机微信搜「跑本无限助手」小程序，电脑直接打开 paoben.top。"

    article_html = compile_wechat_article_html(
        title=title,
        column_name=column_name,
        date_str=datetime.now().strftime("%Y-%m-%d"),
        lead_text=lead_text,
        hero_img_rel=hero_rel,
        header_banner_rel="header_banner.png",
        footer_banner_rel="footer_cta.png",
        sections=wx_sections,
        closing_lines=[
            "核心机制先核清，",
            "关键属性记心里，",
            "少走弯路多出货，",
            "下期攻略我们接着聊。",
        ],
        footnote=promo_copy,
        sources=[
            src_note,
            "电脑端资料站：paoben.top（大屏查表、3D配装预览、12.10团本筹备）",
            "微信小程序：跑本无限助手（副本手册、练级天赋与宏命令）",
        ],
    )
    out_html_path = folder / "article.html"
    out_html_path.write_text(article_html, encoding="utf-8")
    return str(out_html_path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=["all", "dungeon", "daily"], default="all")
    ap.add_argument("--dungeon", default="deathmine", help="副本 ID（如 deathmine / hall-of-thanes / ruins-of-lordaeron / ragefire-chasm）")
    ap.add_argument("--out", default="", help="输出根目录（默认 wow-forever-web/docs/screenshots/ningjing-packs）")
    args = ap.parse_args()

    app_root = _find_app_root()
    out_root = (
        pathlib.Path(args.out)
        if args.out else
        app_root.parent / "docs" / "screenshots" / "ningjing-packs"
    )
    out_root.mkdir(parents=True, exist_ok=True)

    results = []
    if args.mode in ("all", "dungeon"):
        d_spec = build_dungeon_notebook_spec(app_root, args.dungeon)
        print(f"[ningjing] 正在渲染羊皮纸手账包：{d_spec['title']} ...")
        m1 = render_pack(d_spec, out_root)
        results.append(m1)
        print(f"  -> 完成：{len(m1['carousel_slides'])} 张 3:4 轮播图 + {len(m1['wechat_inline_cards'])} 张公众号内嵌卡 + {m1['wechat_article_html']}")

    if args.mode in ("all", "daily"):
        h_spec = build_daily_hotfix_spec(app_root)
        print(f"[ningjing] 正在渲染暗调毛玻璃日报包：{h_spec['title']} ...")
        m2 = render_pack(h_spec, out_root)
        results.append(m2)
        print(f"  -> 完成：{len(m2['carousel_slides'])} 张 3:4 轮播图 + {len(m2['wechat_inline_cards'])} 张公众号内嵌卡 + {m2['wechat_article_html']}")

    print(json.dumps({"ok": True, "out_root": str(out_root), "packs": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
