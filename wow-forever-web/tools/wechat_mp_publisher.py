#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wechat_mp_publisher.py — 微信公众号官方接口直推草稿箱

流程：
1. 读取 WECHAT_MP_APPID / WECHAT_MP_APPSECRET（环境变量优先，其次 config/config.env.local）；
2. 获取并缓存 access_token（若命中 errcode=40164 IP 白名单拦截，明确提取出出口 IP 提示配置）；
3. 扫描 wechat/article.html 中 #js_content 的全部本地图片，超 900KB 或非 JPG/PNG 自动转压缩 JPG，
   调用 cgi-bin/media/uploadimg 上传至微信图床（mmbiz.qpic.cn，不占永久素材额度，按 SHA-1 缓存去重）；
4. 上传封面图（hero_cover.png / poster_p1.png）至 cgi-bin/material/add_material?type=image 获取 thumb_media_id；
5. 替换正文中全部 <img> 为 mmbiz.qpic.cn URL，调用 cgi-bin/draft/add 新增图文草稿，落盘 draft_receipt.json。

Python 3.9+ 兼容。严禁在代码或日志中打印 AppSecret 或 access_token。
"""
from __future__ import annotations

import hashlib
import html as html_lib
import io
import json
import os
import pathlib
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

try:
    from PIL import Image
except ImportError:
    Image = None


TOKEN_TTL_SAFE = 6800
UPLOAD_MAX_BYTES = 900 * 1024  # 微信 uploadimg 限制 1MB，留安全余量


class WechatMPError(RuntimeError):
    """微信公众平台接口错误（携带可操作提示）。"""


def _repo_root() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve()
    if here.parent.name == "src":
        return here.parents[1]
    return pathlib.Path.home() / "Documents/project/video2text"


def _load_env_file(path: pathlib.Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def load_credentials(root: Optional[pathlib.Path] = None) -> Tuple[str, str]:
    root = root or _repo_root()
    env_cfg = _load_env_file(root / "config" / "config.env.local")
    appid = (os.environ.get("WECHAT_MP_APPID") or env_cfg.get("WECHAT_MP_APPID") or "").strip()
    secret = (os.environ.get("WECHAT_MP_APPSECRET") or env_cfg.get("WECHAT_MP_APPSECRET") or "").strip()
    if not appid or not secret:
        raise WechatMPError(
            "未配置 WECHAT_MP_APPID 或 WECHAT_MP_APPSECRET，请先写入 video2text/config/config.env.local。"
        )
    return appid, secret


def _format_wx_err(data: Dict[str, Any]) -> str:
    code = data.get("errcode")
    msg = str(data.get("errmsg") or "")
    if code == 40164:
        m = re.search(r"invalid ip\s+([0-9a-fA-F:.]+)", msg)
        ip_str = m.group(1) if m else "当前出口IP"
        return (
            f"公众号 IP 白名单未放行（errcode 40164）：请登录微信公众平台（mp.weixin.qq.com）"
            f"→「设置与开发」→「基本配置」→「IP白名单」，将本机出口 IP「{ip_str}」加入白名单后再点推送。"
        )
    if code == 40001 or code == 42001:
        return f"access_token 失效或已过期（errcode {code}）：{msg}"
    if code == 45009:
        return f"当日接口调用达到上限（errcode 45009）：{msg}"
    if code == 40007:
        return f"无效的封面素材 media_id（errcode 40007）：{msg}"
    return f"微信接口返回错误（errcode {code}）：{msg}"


def get_access_token(root: Optional[pathlib.Path] = None, force_refresh: bool = False) -> str:
    root = root or _repo_root()
    appid, secret = load_credentials(root)
    cache_path = root / "output" / ".wechat_token_cache.json"
    app_hash = hashlib.sha1(appid.encode("utf-8")).hexdigest()[:12]
    now = time.time()

    if not force_refresh and cache_path.is_file():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
            if cache.get("app_hash") == app_hash and float(cache.get("expires_at") or 0) > now:
                tok = str(cache.get("access_token") or "")
                if tok:
                    return tok
        except Exception:
            pass

    resp = requests.get(
        "https://api.weixin.qq.com/cgi-bin/token",
        params={"grant_type": "client_credential", "appid": appid, "secret": secret},
        timeout=20,
    )
    data = resp.json()
    if "access_token" not in data:
        raise WechatMPError(_format_wx_err(data))

    tok = data["access_token"]
    expires_in = int(data.get("expires_in") or 7200)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {"app_hash": app_hash, "access_token": tok, "expires_at": now + min(TOKEN_TTL_SAFE, expires_in - 200)},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return tok


def _prepare_image_bytes(img_path: pathlib.Path, max_bytes: int = UPLOAD_MAX_BYTES) -> Tuple[str, bytes, str]:
    """确保上传图片为 JPG/PNG 且不超过微信大小限制。返回 (filename, bytes, mime)。"""
    raw = img_path.read_bytes()
    ext = img_path.suffix.lower()
    if ext in (".jpg", ".jpeg") and len(raw) <= max_bytes:
        return img_path.name, raw, "image/jpeg"
    if ext == ".png" and len(raw) <= max_bytes:
        return img_path.name, raw, "image/png"

    if Image is None:
        if ext in (".jpg", ".jpeg", ".png"):
            return img_path.name, raw, "image/png" if ext == ".png" else "image/jpeg"
        raise WechatMPError(f"图片 {img_path.name} 需要转换格式/压缩，但当前环境缺少 Pillow")

    with Image.open(io.BytesIO(raw)) as im:
        if im.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", im.size, (20, 16, 24))
            if im.mode == "P":
                im = im.convert("RGBA")
            bg.paste(im, mask=im.split()[-1] if "A" in im.mode else None)
            rgb = bg
        else:
            rgb = im.convert("RGB")

        for quality in (90, 82, 74, 65):
            buf = io.BytesIO()
            rgb.save(buf, format="JPEG", quality=quality, optimize=True)
            data = buf.getvalue()
            if len(data) <= max_bytes:
                return img_path.stem + ".jpg", data, "image/jpeg"

        # 仍超限则等比缩放宽度
        w, h = rgb.size
        if w > 900:
            rgb = rgb.resize((900, int(h * 900 / w)), Image.LANCZOS)
        buf = io.BytesIO()
        rgb.save(buf, format="JPEG", quality=72, optimize=True)
        return img_path.stem + ".jpg", buf.getvalue(), "image/jpeg"


def _load_img_cache(root: pathlib.Path) -> Dict[str, Any]:
    p = root / "output" / ".wechat_img_cache.json"
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"uploadimg": {}, "thumb": {}}


def _save_img_cache(root: pathlib.Path, cache: Dict[str, Any]) -> None:
    p = root / "output" / ".wechat_img_cache.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def upload_body_image(img_path: pathlib.Path, root: Optional[pathlib.Path] = None) -> str:
    """上传正文插图到 cgi-bin/media/uploadimg，返回 mmbiz.qpic.cn URL。"""
    root = root or _repo_root()
    appid, _ = load_credentials(root)
    raw = img_path.read_bytes()
    key = f"{appid}:{hashlib.sha1(raw).hexdigest()}"
    cache = _load_img_cache(root)
    if key in cache.get("uploadimg", {}):
        return cache["uploadimg"][key]

    fname, payload, mime = _prepare_image_bytes(img_path, max_bytes=UPLOAD_MAX_BYTES)
    for attempt in range(2):
        tok = get_access_token(root, force_refresh=(attempt == 1))
        resp = requests.post(
            "https://api.weixin.qq.com/cgi-bin/media/uploadimg",
            params={"access_token": tok},
            files={"media": (fname, payload, mime)},
            timeout=30,
        )
        data = resp.json()
        if data.get("errcode") in (40001, 42001) and attempt == 0:
            continue
        if "url" not in data:
            raise WechatMPError(f"上传正文图片 {img_path.name} 失败 — {_format_wx_err(data)}")
        url = str(data["url"])
        cache.setdefault("uploadimg", {})[key] = url
        _save_img_cache(root, cache)
        return url
    raise WechatMPError(f"上传正文图片 {img_path.name} 重试后仍失败")


def upload_cover_thumb(img_path: pathlib.Path, root: Optional[pathlib.Path] = None) -> str:
    """上传永久图片素材作为图文封面，返回 thumb_media_id。"""
    root = root or _repo_root()
    appid, _ = load_credentials(root)
    raw = img_path.read_bytes()
    key = f"{appid}:{hashlib.sha1(raw).hexdigest()}"
    cache = _load_img_cache(root)
    if key in cache.get("thumb", {}):
        return cache["thumb"][key]

    fname, payload, mime = _prepare_image_bytes(img_path, max_bytes=1800 * 1024)
    for attempt in range(2):
        tok = get_access_token(root, force_refresh=(attempt == 1))
        resp = requests.post(
            "https://api.weixin.qq.com/cgi-bin/material/add_material",
            params={"access_token": tok, "type": "image"},
            files={"media": (fname, payload, mime)},
            timeout=30,
        )
        data = resp.json()
        if data.get("errcode") in (40001, 42001) and attempt == 0:
            continue
        if "media_id" not in data:
            raise WechatMPError(f"上传封面图 {img_path.name} 失败 — {_format_wx_err(data)}")
        mid = str(data["media_id"])
        cache.setdefault("thumb", {})[key] = mid
        _save_img_cache(root, cache)
        return mid
    raise WechatMPError(f"上传封面图 {img_path.name} 重试后仍失败")


def _extract_article_parts(article_html: pathlib.Path) -> Tuple[str, str, str]:
    """从 article.html 提取 (title, digest, js_content_inner_html)。"""
    raw = article_html.read_text(encoding="utf-8")

    # Title
    m_title = re.search(r'<h1 class="wx-title">(.*?)</h1>', raw, re.S)
    if not m_title:
        m_title = re.search(r"<title>(.*?)</title>", raw, re.S)
    title = html_lib.unescape(re.sub(r"<[^>]+>", "", m_title.group(1))).strip() if m_title else "无限服攻略"

    # Body
    m_mark = re.search(r"<!-- WECHAT_BODY_START -->\s*(.*?)\s*<!-- WECHAT_BODY_END -->", raw, re.S)
    if m_mark:
        body_html = m_mark.group(1).strip()
    else:
        m_div = re.search(r'<div id="js_content"[^>]*>(.*?)</div>\s*</div>\s*<script>', raw, re.S)
        if not m_div:
            raise WechatMPError(f"无法从 {article_html.name} 解析正文区域 #js_content")
        body_html = m_div.group(1).strip()

    # Digest (first paragraph text)
    plain = html_lib.unescape(re.sub(r"<[^>]+>", " ", body_html))
    plain = re.sub(r"\s+", " ", plain).strip()
    digest = plain[:115]

    return title, digest, body_html


def _resolve_local_image(wechat_dir: pathlib.Path, src: str) -> Optional[pathlib.Path]:
    src = src.strip()
    if not src or src.startswith(("http://", "https://", "data:")):
        return None
    clean = src.split("?", 1)[0].split("#", 1)[0]
    for base in (wechat_dir, wechat_dir.parent):
        cand = (base / clean).resolve()
        if cand.is_file() and (cand.is_relative_to(wechat_dir.resolve()) or cand.is_relative_to(wechat_dir.parent.resolve())):
            return cand
    return None


def push_article_dir_to_draft(
    wechat_dir: pathlib.Path,
    *,
    title: Optional[str] = None,
    author: str = "跑本无限助手",
    digest: Optional[str] = None,
    root: Optional[pathlib.Path] = None,
) -> Dict[str, Any]:
    """将 wechat/article.html 及其配图完整上传并推送至微信公众号草稿箱。"""
    root = root or _repo_root()
    wechat_dir = pathlib.Path(wechat_dir)
    article_html = wechat_dir / "article.html"
    if not article_html.is_file():
        raise WechatMPError(f"未找到公众号排版文件：{article_html}")

    parsed_title, parsed_digest, body_html = _extract_article_parts(article_html)
    final_title = (title or parsed_title).strip()[:32]
    final_author = author.strip()[:8]
    final_digest = (digest or parsed_digest).strip()[:120]

    # 1. 查找并上传全部正文本地图片
    img_url_map: Dict[str, str] = {}
    cover_candidate: Optional[pathlib.Path] = None

    def _replace_img(m: re.Match) -> str:
        nonlocal cover_candidate
        prefix_attr, quote, src_val = m.group(1), m.group(2), m.group(3)
        local_path = _resolve_local_image(wechat_dir, src_val)
        if local_path is None:
            return m.group(0)
        if cover_candidate is None and "header_banner" not in local_path.name:
            cover_candidate = local_path
        if src_val not in img_url_map:
            img_url_map[src_val] = upload_body_image(local_path, root=root)
        mmbiz_url = img_url_map[src_val]
        return f"{prefix_attr}{quote}{mmbiz_url}{quote}"

    uploaded_body = re.sub(
        r'(<img\b[^>]*\bsrc=)(["\'])([^"\']+)\2',
        _replace_img,
        body_html,
        flags=re.I,
    )

    # 2. 确定封面图并上传永久素材获取 thumb_media_id
    for pref in ("hero_cover.png", "poster_p1.png", "poster.png"):
        for base in (wechat_dir, wechat_dir.parent):
            cand = base / pref
            if cand.is_file():
                cover_candidate = cand
                break
        if cover_candidate and cover_candidate.name == pref:
            break
    if cover_candidate is None:
        raise WechatMPError("未找到可用的文章封面图（hero_cover.png / poster_p1.png）")

    thumb_media_id = upload_cover_thumb(cover_candidate, root=root)

    # 3. 推送草稿箱 (cgi-bin/draft/add)
    payload = {
        "articles": [
            {
                "title": final_title,
                "author": final_author,
                "digest": final_digest,
                "content": uploaded_body,
                "thumb_media_id": thumb_media_id,
                "need_open_comment": 1,
                "only_fans_can_comment": 0,
            }
        ]
    }
    body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    draft_media_id = ""
    for attempt in range(2):
        tok = get_access_token(root, force_refresh=(attempt == 1))
        resp = requests.post(
            "https://api.weixin.qq.com/cgi-bin/draft/add",
            params={"access_token": tok},
            data=body_bytes,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=30,
        )
        res = resp.json()
        if res.get("errcode") in (40001, 42001) and attempt == 0:
            continue
        if "media_id" not in res:
            raise WechatMPError(f"创建公众号草稿失败 — {_format_wx_err(res)}")
        draft_media_id = str(res["media_id"])
        break

    receipt = {
        "ok": True,
        "media_id": draft_media_id,
        "title": final_title,
        "author": final_author,
        "thumb_media_id": thumb_media_id,
        "uploaded_images": img_url_map,
        "pushed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (wechat_dir / "draft_receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return receipt
