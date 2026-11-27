#!/usr/bin/env python3
"""
build-world-tiles.py — 12K 原生高清无缝游戏大地图瓦片金字塔生成器：
  1. 解决经典大陆底图裁切无限新域问题：河林（药引港半岛）/ 海加尔山 / 辛德拉 / 泽风岛
     的真实陆地轮廓自动并入海岸线遮罩，零缺块；
  2. 消除 1414/1415 低分海洋放大后的粗条纹与未绘山地矩形直边：海面做低频去条纹+高分羊皮纸
     颗粒重构，未拼接外缘采用平滑缓动羽化；
  3. 最高层级升级至 z4 = 12288×8192（12K，逐区保留 1002×668 完整原生像素清晰度 + 轻锐化），
     按东西两半（6144×8192）低内存无损切分 512×512 WebP 瓦片金字塔：
       - z1: 2048×1366 (12 瓦片)
       - z2: 4096×2730 (陆地稀疏瓦片)
       - z3: 6144×4096 (陆地稀疏瓦片)
       - z4: 12288×8192 (12K 原生超清陆地稀疏瓦片)
"""
import hashlib
import json
import math
import os
from datetime import date
import numpy as np
from PIL import Image, ImageFilter

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.dirname(TOOLS_DIR)
APP_DIR = os.path.join(WEB_DIR, 'app')
MAPS_DIR = os.path.join(APP_DIR, 'img', 'art', 'maps')
TILES_DIR = os.path.join(APP_DIR, 'img', 'art', 'world-tiles')
ATLAS_PATH = os.path.join(APP_DIR, 'data', 'world-atlas.json')
MANIFEST_PATH = os.path.join(APP_DIR, 'img', 'art', 'manifest.json')
UPSTREAM_META = os.path.join(APP_DIR, 'data', 'upstream', 'world-tiles-meta.json')

TILE_SIZE = 512
Z4_W, Z4_H = 12288, 8192
Z3_W, Z3_H = 6144, 4096


def rgb_to_hsv_np(rgb: np.ndarray):
    r, g, b = rgb[:, :, 0] / 255.0, rgb[:, :, 1] / 255.0, rgb[:, :, 2] / 255.0
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    df = mx - mn
    s = np.where(mx > 1e-6, df / (mx + 1e-6), 0.0)
    v = mx
    h = np.zeros_like(mx)
    m = df > 1e-6
    rm = m & (mx == r)
    gm = m & (mx == g)
    bm = m & (mx == b)
    h[rm] = (60.0 * ((g[rm] - b[rm]) / df[rm]) + 360.0) % 360.0
    h[gm] = 60.0 * ((b[gm] - r[gm]) / df[gm]) + 120.0
    h[bm] = 60.0 * ((r[bm] - g[bm]) / df[bm]) + 240.0
    return h, s, v


def smoothstep(x: np.ndarray) -> np.ndarray:
    t = np.clip(x, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def build_classic_land_mask(base_6k: np.ndarray) -> np.ndarray:
    """从 947+1414+1415 基底提取经典两大陆的有机海岸线遮罩（形状 H×W, float32 [0,1]）。"""
    ch, cw, _ = base_6k.shape
    sw, sh = cw // 4, ch // 4
    sm = np.asarray(
        Image.fromarray(base_6k.astype(np.uint8)).resize((sw, sh), Image.BILINEAR),
        dtype=np.float32,
    )
    r, b = sm[:, :, 0], sm[:, :, 2]
    _, s, _ = rgb_to_hsv_np(sm)
    warmth = r - b
    is_land = ((warmth > 43.0) & (s > 0.30)) | ((warmth > 56.0) & (s > 0.22))

    lm = Image.fromarray((is_land.astype(np.uint8) * 255))
    lm = lm.filter(ImageFilter.MinFilter(5))
    lm = lm.filter(ImageFilter.MaxFilter(9))
    lm = lm.filter(ImageFilter.GaussianBlur(radius=6))
    land_full = np.asarray(lm.resize((cw, ch), Image.BILINEAR), dtype=np.float32) / 255.0
    return np.clip(land_full * 1.18, 0.0, 1.0)


def compute_zone_mask(img_rgb: np.ndarray, is_new: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """
    基于局部墨线对比度 + 色彩屏障 + 连通域过滤，精准剥离外围空白羊皮纸、邻居地名字样与外海横纹，
    仅保留区域真实的有机山脉轮廓与海岸线（零矩形硬切边、零邻居叠字、新域零缺块）。
    """
    H, W, _ = img_rgb.shape
    sh, sw = H // 2, W // 2
    small = np.asarray(Image.fromarray(img_rgb).resize((sw, sh), Image.BILINEAR), dtype=np.float32)
    h, s, v = rgb_to_hsv_np(small)
    gray = small[:, :, 0] * 0.299 + small[:, :, 1] * 0.587 + small[:, :, 2] * 0.114

    # 局部墨线对比度（9×9 标准差）：空白羊皮纸与外海均 < 11，画出的山脉/海岸线/建筑/道路均 > 13
    m1 = np.asarray(Image.fromarray(np.clip(gray, 0, 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(4)), dtype=np.float32)
    sq = np.clip((gray - m1) ** 2, 0.0, 255.0 * 16.0)
    m2 = np.asarray(Image.fromarray(np.clip(sq / 16.0, 0, 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(4)), dtype=np.float32) * 16.0
    lstd = np.sqrt(np.maximum(0.0, m2))

    # 方向梯度比：识别海面强水平横条纹（|dy| 显著大于 |dx| 且低对比度/灰褐色）
    gx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    gy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    gx_s = np.asarray(Image.fromarray(np.clip(gx * 4, 0, 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(4)), dtype=np.float32) / 4.0
    gy_s = np.asarray(Image.fromarray(np.clip(gy * 4, 0, 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(4)), dtype=np.float32) / 4.0
    is_hwave_sea = (gy_s > gx_s * 1.45 + 0.8) & (s < 0.48) & (h < 54) & (lstd < 20.0)

    bx, by = int(sw * 0.044), int(sh * 0.048)
    frame_ok = np.ones((sh, sw), dtype=bool)
    frame_ok[:by, :] = False
    frame_ok[-by:, :] = False
    frame_ok[:, :bx] = False
    frame_ok[:, -bx:] = False

    # 明确属于「手绘区域内容」的屏障像素：
    # 1) 强墨线山脉/海岸/道路/地形纹理 (lstd >= 11.2 且非纯水平海浪)
    # 2) 深色墨线轮廓与暗色林地（含费伍德森林等暗绿/暗紫地貌）(v < 0.34)
    # 3) 非羊皮纸地貌色彩（绿林/浅海青蓝湾/雪原/赤红与橙红峡谷地貌如荒芜之地/杜隆塔尔）
    is_ink_art = ((lstd >= 11.2) & (~is_hwave_sea)) | (v < 0.34)
    is_green_or_cyan = (h >= 49) & (h <= 220) & (s >= 0.15) & (v >= 0.20)
    is_red_or_orange = ((h <= 28) | (h >= 338)) & (s >= 0.44) & (v >= 0.20)
    is_snow = (v >= 0.78) & (s <= 0.34)
    barrier = frame_ok & (is_ink_art | is_green_or_cyan | is_red_or_orange | is_snow)

    # 闭运算封住外圈山脉上的小路与山口缺口（防泛洪漏进荒芜之地/贫瘠之地/赤脊山内陆平原）
    b_img = Image.fromarray((barrier.astype(np.uint8) * 255))
    b_closed = np.asarray(b_img.filter(ImageFilter.MaxFilter(7)), dtype=np.uint8) > 127

    # 从 4% 卷边外框泛洪识别所有真实外部空白羊皮纸与外海
    visited = ~frame_ok
    stack = []
    for x in range(bx, sw - bx):
        for y in (by, sh - by - 1):
            if not b_closed[y, x] and not visited[y, x]:
                visited[y, x] = True
                stack.append((y, x))
    for y in range(by, sh - by):
        for x in (bx, sw - bx - 1):
            if not b_closed[y, x] and not visited[y, x]:
                visited[y, x] = True
                stack.append((y, x))
    while stack:
        cy, cx = stack.pop()
        for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
            if 0 <= ny < sh and 0 <= nx < sw and not visited[ny, nx] and not b_closed[ny, nx]:
                visited[ny, nx] = True
                stack.append((ny, nx))

    painted = ~visited

    # 连通域清理：自动剔除漂浮在空白羊皮纸上的邻居地名（BADLANDS / 灼热峡谷 / DESOLACE）与角落装饰云塔
    labels = np.zeros((sh, sw), dtype=np.int32)
    comp_sizes = []
    comp_bboxes = []
    cid = 0
    for y in range(sh):
        for x in range(sw):
            if painted[y, x] and labels[y, x] == 0:
                cid += 1
                q = [(y, x)]
                labels[y, x] = cid
                cnt = 0
                minx = maxx = x
                miny = maxy = y
                while q:
                    cy, cx = q.pop()
                    cnt += 1
                    if cx < minx: minx = cx
                    if cx > maxx: maxx = cx
                    if cy < miny: miny = cy
                    if cy > maxy: maxy = cy
                    for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                        if 0 <= ny < sh and 0 <= nx < sw and painted[ny, nx] and labels[ny, nx] == 0:
                            labels[ny, nx] = cid
                            q.append((ny, nx))
                comp_sizes.append((cnt, cid))
                comp_bboxes.append((minx, miny, maxx, maxy))

    if comp_sizes:
        comp_sizes.sort(reverse=True)
        main_cnt, main_id = comp_sizes[0]
        keep_ids = {main_id}
        # 保留与主体面积可观或紧邻主体的近海小岛（如河林药引港离岛、热砂港、棘齿城外岛）
        mb = comp_bboxes[main_id - 1]
        for cnt, c_id in comp_sizes[1:]:
            if cnt >= max(380, int(main_cnt * 0.045)):
                # 排除紧贴最外角装饰物（如泽风岛四角塔楼云朵）
                x0, y0, x1, y1 = comp_bboxes[c_id - 1]
                cx_n = (x0 + x1) * 0.5 / sw
                cy_n = (y0 + y1) * 0.5 / sh
                in_corner = (cx_n < 0.18 or cx_n > 0.82) and (cy_n < 0.25 or cy_n > 0.75)
                if not in_corner:
                    keep_ids.add(c_id)
            elif is_new and cnt >= 90:
                x0, y0, x1, y1 = comp_bboxes[c_id - 1]
                # 新域近岸离岛（靠近主陆地包围盒）
                near_main = (x1 >= mb[0] - 28 and x0 <= mb[2] + 28 and y1 >= mb[1] - 28 and y0 <= mb[3] + 28)
                cx_n = (x0 + x1) * 0.5 / sw
                cy_n = (y0 + y1) * 0.5 / sh
                in_corner = (cx_n < 0.18 or cx_n > 0.82) and (cy_n < 0.25 or cy_n > 0.75)
                if near_main and not in_corner:
                    keep_ids.add(c_id)
        painted = np.isin(labels, list(keep_ids))

    if float(np.mean(painted)) < 0.14:
        yy, xx = np.mgrid[0:sh, 0:sw]
        d = np.sqrt(((xx - sw * 0.5) / (sw * 0.43)) ** 2 + ((yy - sh * 0.5) / (sh * 0.43)) ** 2)
        a_sm = smoothstep((1.0 - d) / 0.30).astype(np.float32)
        alpha = np.asarray(Image.fromarray((a_sm * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), dtype=np.float32) / 255.0
        return alpha, alpha * alpha

    # 回缩抵消 MaxFilter(7) 膨胀，再平滑有机羽化
    p_img = Image.fromarray((painted.astype(np.uint8) * 255))
    p_img = p_img.filter(ImageFilter.MinFilter(5 if is_new else 7))
    p_img = p_img.filter(ImageFilter.MaxFilter(5 if is_new else 3))
    a_full = np.asarray(p_img.filter(ImageFilter.GaussianBlur(radius=9)).resize((W, H), Image.BILINEAR), dtype=np.float32) / 255.0
    alpha = smoothstep((a_full - 0.10) / 0.80)

    # 外框极边缘平滑保护（防止碰边处出现生硬截断）
    fx = smoothstep((np.minimum(np.arange(W), W - 1 - np.arange(W)) - W * 0.036) / (W * 0.085))
    fy = smoothstep((np.minimum(np.arange(H), H - 1 - np.arange(H)) - H * 0.040) / (H * 0.090))
    alpha *= np.minimum(fy[:, None], fx[None, :])

    # 柔和的内部核心距离权重（相邻区域自然水彩过渡，杜绝硬拼接线）
    core = np.asarray(p_img.filter(ImageFilter.GaussianBlur(radius=28)).resize((W, H), Image.BILINEAR), dtype=np.float32) / 255.0
    yy, xx = np.mgrid[0:H, 0:W]
    rad = np.sqrt(((xx - W * 0.5) / (W * 0.54)) ** 2 + ((yy - H * 0.5) / (H * 0.54)) ** 2)
    center_pref = np.clip(1.20 - rad * 0.45, 0.25, 1.20)
    weight = (alpha ** 1.45) * (core ** 0.95) * center_pref
    return alpha.astype(np.float32), weight.astype(np.float32)


def build_base_canvas(atlas, w: int, h: int, x_off: int = 0, full_w: int = None) -> tuple[np.ndarray, np.ndarray]:
    """
    构建区域基底（947 + 1414 + 1415），并对海面做低频去粗条纹 + 细腻双频羊皮纸颗粒，
    消除低分大陆底图放大后的巨大横条纹。返回 (canvas_rgb_f32, classic_land_mask_f32)。
    """
    fw = full_w or w
    cw = atlas['meta']['canvas']['w']
    ch = atlas['meta']['canvas']['h']
    sx = fw / cw
    sy = h / ch

    # 先在 3072×2048 合成干净基底与经典海岸线遮罩，再裁剪放大到目标块
    bw, bh = 3072, 2048
    bsx, bsy = bw / cw, bh / ch
    base = Image.open(os.path.join(MAPS_DIR, '947.webp')).convert('RGB').resize((bw, bh), Image.LANCZOS)
    c_arr = np.asarray(base, dtype=np.float32)

    for c in atlas['continents']:
        cimg = Image.open(os.path.join(APP_DIR, c['mapFile'])).convert('RGB')
        rx, ry, rw, rh = c['rect']
        tx, ty, tw, th = int(round(rx * bsx)), int(round(ry * bsy)), int(round(rw * bsx)), int(round(rh * bsy))
        cimg_r = np.asarray(cimg.resize((tw, th), Image.LANCZOS), dtype=np.float32)
        yy, xx = np.mgrid[0:th, 0:tw]
        dx = (xx - tw * 0.5) / (tw * 0.48)
        dy = (yy - th * 0.5) / (th * 0.48)
        ca = smoothstep((1.0 - np.sqrt(dx * dx + dy * dy)) / 0.26)[:, :, None]
        x0, y0 = max(0, tx), max(0, ty)
        x1, y1 = min(bw, tx + tw), min(bh, ty + th)
        sx0, sy0 = x0 - tx, y0 - ty
        sx1, sy1 = sx0 + (x1 - x0), sy0 + (y1 - y0)
        a_s = ca[sy0:sy1, sx0:sx1]
        c_arr[y0:y1, x0:x1] = c_arr[y0:y1, x0:x1] * (1.0 - a_s) + cimg_r[sy0:sy1, sx0:sx1] * a_s

    classic_lm_small = build_classic_land_mask(c_arr)

    # 关键：在全部海面（包括紧贴海岸线的近海）强力垂直去条纹，彻底消除 1414/1415 放大后的巨大横条纹，
    # 仅保护大漩涡与陆地本身，随后在目标分辨率叠加高分细腻古卷纸纹！
    c_img_u8 = Image.fromarray(np.clip(c_arr, 0, 255).astype(np.uint8))
    # 垂直强平滑（压缩高度 14× 再平滑还原）专杀水平粗波浪条纹，同时保留海洋色带与海怪轮廓的色调层次
    sea_v = c_img_u8.resize((bw // 4, bh // 16), Image.BILINEAR).resize((bw, bh), Image.BICUBIC)
    sea_soft = np.asarray(sea_v.filter(ImageFilter.GaussianBlur(radius=4)), dtype=np.float32)
    # 内缩陆地遮罩让近岸海水也彻底平滑
    lm_tight = np.asarray(
        Image.fromarray((classic_lm_small * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(13)).filter(ImageFilter.GaussianBlur(radius=6)),
        dtype=np.float32,
    ) / 255.0
    # 保护中央无尽之海大漩涡细节
    yy_b, xx_b = np.mgrid[0:bh, 0:bw]
    mael_d = np.sqrt(((xx_b - bw * 0.485) / (bw * 0.085)) ** 2 + ((yy_b - bh * 0.51) / (bh * 0.13)) ** 2)
    mael_protect = smoothstep((1.0 - mael_d) / 0.35)
    sea_w = (1.0 - np.clip(lm_tight * 1.1, 0.0, 1.0)) * (1.0 - mael_protect * 0.72) * 0.94
    c_clean = c_arr * (1.0 - sea_w[:, :, None]) + sea_soft * sea_w[:, :, None]

    # 柔化 1414/1415 基底上未绘山区（海加尔山南侧、灼热峡谷西侧、洛克莫丹东侧）的刺眼亮黄/亮绿低分色块，
    # 调和为古卷暖褐山脊底色，避免区域空隙透出突兀的荧光黄糊块
    ch_h, ch_s, ch_v = rgb_to_hsv_np(c_clean)
    is_garish_gap = (classic_lm_small > 0.25) & (ch_h >= 40.0) & (ch_h <= 85.0) & (ch_s >= 0.36) & (ch_v >= 0.42)
    gap_mask = np.asarray(
        Image.fromarray((is_garish_gap.astype(np.uint8) * 255)).filter(ImageFilter.GaussianBlur(radius=12)),
        dtype=np.float32,
    ) / 255.0
    # 降饱和并压暖为古地图深羊皮纸棕褐色（与周围山脉轮廓自然融合）
    lum = c_clean[:, :, 0] * 0.299 + c_clean[:, :, 1] * 0.587 + c_clean[:, :, 2] * 0.114
    warm_tone = np.stack([
        np.clip(lum * 0.86 + 10.0, 0, 255),
        np.clip(lum * 0.68 + 4.0, 0, 255),
        np.clip(lum * 0.39, 0, 255),
    ], axis=-1)
    gap_w = (gap_mask * 0.78)[:, :, None]
    c_clean = c_clean * (1.0 - gap_w) + warm_tone * gap_w

    # 裁切出目标条带 [x_off .. x_off + w] 并高质量缩放到目标分辨率
    bx0 = int(round(x_off * (bw / fw)))
    bx1 = int(round((x_off + w) * (bw / fw)))
    strip_img = Image.fromarray(np.clip(c_clean, 0, 255).astype(np.uint8)).crop((bx0, 0, bx1, bh)).resize((w, h), Image.LANCZOS)
    lm_strip = Image.fromarray((classic_lm_small * 255).astype(np.uint8)).crop((bx0, 0, bx1, bh)).resize((w, h), Image.BILINEAR)

    canvas = np.asarray(strip_img, dtype=np.float32)
    classic_lm = np.asarray(lm_strip, dtype=np.float32) / 255.0

    # 双频细腻羊皮纸肌理（让 12K 放大时的海洋与未绘山岭都具有细腻古卷纸纹，不发糊）
    rng = np.random.default_rng(42 + x_off)
    g1 = rng.normal(0.0, 2.4, size=(h, w, 1)).astype(np.float32)
    g2_sm = rng.normal(0.0, 3.6, size=(max(1, h // 4), max(1, w // 4))).astype(np.float32)
    g2 = np.asarray(
        Image.fromarray(np.clip(g2_sm * 8 + 128, 0, 255).astype(np.uint8)).resize((w, h), Image.BILINEAR),
        dtype=np.float32,
    )[:, :, None]
    g2 = (g2 - 128.0) / 8.0
    canvas = np.clip(canvas + g1 + g2, 0, 255)
    return canvas, classic_lm


def render_stitched_strip(atlas, zone_cache: dict, fw: int, fh: int, x_off: int, sw: int) -> tuple[Image.Image, np.ndarray]:
    """
    渲染目标分辨率 fw×fh 中 [x_off .. x_off + sw] 的无缝拼接条带。
    返回 (PIL.Image RGB, land_presence_u8[fh, sw])。
    """
    cw = atlas['meta']['canvas']['w']
    ch = atlas['meta']['canvas']['h']
    sx = fw / cw
    sy = fh / ch

    canvas, classic_lm = build_base_canvas(atlas, sw, fh, x_off=x_off, full_w=fw)
    acc_rgb = np.zeros((fh, sw, 3), dtype=np.float32)
    acc_w = np.zeros((fh, sw), dtype=np.float32)
    acc_max_a = np.zeros((fh, sw), dtype=np.float32)
    new_zone_a = np.zeros((fh, sw), dtype=np.float32)

    # 无限新增且嵌套在旧经典占位山脉内部的新域（海加尔山 2482 / 辛德拉 2652 / 泽风岛 2521）
    # 在二阶段独立前景叠加，防止冬泉谷(1452)/费伍德(1448)/凄凉之地(1443)/菲拉斯(1444)旧占位山脉重影覆盖！
    # 河林(2548)继续走一阶段无缝过渡，避免西缘邻居字样覆盖荒芜之地与赤脊山。
    FOREGROUND_NEW_IDS = {'2482', '2652', '2521'}

    outdoor_zones = [z for z in atlas['zones'] if not z.get('isCity')]
    pass1_zones = [z for z in outdoor_zones if str(z['mapId']) not in FOREGROUND_NEW_IDS]
    pass2_zones = [z for z in outdoor_zones if str(z['mapId']) in FOREGROUND_NEW_IDS]

    for z in pass1_zones:
        mid = str(z['mapId'])
        cached = zone_cache.get(mid)
        if not cached:
            continue
        rx, ry, rw, rh = z['rect']
        tx = int(round(rx * sx)) - x_off
        ty = int(round(ry * sy))
        tw = max(1, int(round(rw * sx)))
        th = max(1, int(round(rh * sy)))
        if tx + tw <= 0 or tx >= sw or ty + th <= 0 or ty >= fh:
            continue

        zimg, za_u8, zw_u8 = cached
        rgb_r = np.asarray(zimg.resize((tw, th), Image.LANCZOS), dtype=np.float32)
        a_r = np.asarray(za_u8.resize((tw, th), Image.BILINEAR), dtype=np.float32) / 255.0
        w_r = np.asarray(zw_u8.resize((tw, th), Image.BILINEAR), dtype=np.float32) / 255.0

        x0, y0 = max(0, tx), max(0, ty)
        x1, y1 = min(sw, tx + tw), min(fh, ty + th)
        if x1 <= x0 or y1 <= y0:
            continue
        sx0, sy0 = x0 - tx, y0 - ty
        sx1, sy1 = sx0 + (x1 - x0), sy0 + (y1 - y0)

        a_s = a_r[sy0:sy1, sx0:sx1]
        is_new = bool(z.get('isNew'))
        w_s = (w_r[sy0:sy1, sx0:sx1] ** 1.35)
        acc_rgb[y0:y1, x0:x1] += rgb_r[sy0:sy1, sx0:sx1] * w_s[:, :, None]
        acc_w[y0:y1, x0:x1] += w_s
        acc_max_a[y0:y1, x0:x1] = np.maximum(acc_max_a[y0:y1, x0:x1], a_s)
        if is_new:
            new_zone_a[y0:y1, x0:x1] = np.maximum(new_zone_a[y0:y1, x0:x1], a_s)

    valid = acc_w > 1e-5
    stitched = np.zeros_like(canvas)
    stitched[valid] = acc_rgb[valid] / acc_w[valid, None]

    effective_lm = np.maximum(classic_lm, new_zone_a)
    blend_a = np.clip(acc_max_a * effective_lm, 0.0, 1.0)
    comp = canvas * (1.0 - blend_a[:, :, None]) + stitched * blend_a[:, :, None]

    # 二阶段：海加尔山(2482) / 辛德拉(2652) / 泽风岛(2521) 完整前景叠加，零旧山脉重影、边缘柔和有机羽化
    for z in pass2_zones:
        mid = str(z['mapId'])
        cached = zone_cache.get(mid)
        if not cached:
            continue
        rx, ry, rw, rh = z['rect']
        tx = int(round(rx * sx)) - x_off
        ty = int(round(ry * sy))
        tw = max(1, int(round(rw * sx)))
        th = max(1, int(round(rh * sy)))
        if tx + tw <= 0 or tx >= sw or ty + th <= 0 or ty >= fh:
            continue

        zimg, za_u8, _ = cached
        # 560×373 新域（如海加尔山/泽风岛）在放大到 12K 时轻度预锐化，保证地标道路清晰可读
        z_rs = zimg.resize((tw, th), Image.LANCZOS)
        if zimg.size[0] < 700 and tw >= 600:
            z_rs = z_rs.filter(ImageFilter.UnsharpMask(radius=1.1, percent=65, threshold=2))
        rgb_r = np.asarray(z_rs, dtype=np.float32)
        a_r = np.asarray(za_u8.resize((tw, th), Image.BILINEAR), dtype=np.float32) / 255.0

        x0, y0 = max(0, tx), max(0, ty)
        x1, y1 = min(sw, tx + tw), min(fh, ty + th)
        if x1 <= x0 or y1 <= y0:
            continue
        sx0, sy0 = x0 - tx, y0 - ty
        sx1, sy1 = sx0 + (x1 - x0), sy0 + (y1 - y0)

        # 内核 100% 实心前景覆盖，外缘 18% 平滑融入相邻大陆山脉
        ov_a = smoothstep((a_r[sy0:sy1, sx0:sx1] - 0.08) / 0.58)
        comp[y0:y1, x0:x1] = comp[y0:y1, x0:x1] * (1.0 - ov_a[:, :, None]) + rgb_r[sy0:sy1, sx0:sx1] * ov_a[:, :, None]
        blend_a[y0:y1, x0:x1] = np.maximum(blend_a[y0:y1, x0:x1], ov_a)

    final_u8 = np.clip(comp, 0, 255).astype(np.uint8)
    out_img = Image.fromarray(final_u8)
    # 轻微锐化（提升道路、山脉与地标文字在 12K 放大时的边缘 crisp 度）
    out_img = out_img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=55, threshold=3))
    return out_img, (blend_a * 255).astype(np.uint8)


def main():
    atlas = json.load(open(ATLAS_PATH, encoding='utf-8'))
    outdoor_zones = [z for z in atlas['zones'] if not z.get('isCity')]

    print(f'[1/5] 预计算 {len(outdoor_zones)} 张区域地图真实轮廓与羽化遮罩...')
    zone_cache = {}
    for z in outdoor_zones:
        zp = os.path.join(APP_DIR, z['mapFile'])
        if not os.path.exists(zp):
            continue
        zimg = Image.open(zp).convert('RGB')
        za, zw = compute_zone_mask(np.asarray(zimg), is_new=bool(z.get('isNew')))
        za_u8 = Image.fromarray(np.clip(za * 255, 0, 255).astype(np.uint8))
        zw_u8 = Image.fromarray(np.clip(zw / (zw.max() + 1e-6) * 255, 0, 255).astype(np.uint8))
        zone_cache[str(z['mapId'])] = (zimg, za_u8, zw_u8)

    # 清理旧瓦片目录
    os.makedirs(TILES_DIR, exist_ok=True)
    for sub in ('z1', 'z2', 'z3', 'z4'):
        sd = os.path.join(TILES_DIR, sub)
        if os.path.isdir(sd):
            for fn in os.listdir(sd):
                if fn.endswith('.webp'):
                    os.remove(os.path.join(sd, fn))
        os.makedirs(sd, exist_ok=True)

    meta_levels = []
    total_files = 0
    total_bytes = 0

    # 先合成 6K 整图，切出 z1 (2K) / z2 (4K) / z3 (6K)
    print(f'[2/5] 渲染 6K ({Z3_W}×{Z3_H}) 无缝连续大图并切分 z1/z2/z3...')
    img_6k, mask_6k = render_stitched_strip(atlas, zone_cache, Z3_W, Z3_H, 0, Z3_W)
    mask_6k_img = Image.fromarray(mask_6k)

    for sp in (
        {'z': 1, 'w': 2048, 'h': 1366, 'q': 84, 'sparse': False},
        {'z': 2, 'w': 4096, 'h': 2730, 'q': 82, 'sparse': True},
        {'z': 3, 'w': Z3_W, 'h': Z3_H, 'q': 80, 'sparse': True},
    ):
        z, lw, lh = sp['z'], sp['w'], sp['h']
        cols = math.ceil(lw / TILE_SIZE)
        rows = math.ceil(lh / TILE_SIZE)
        z_dir = os.path.join(TILES_DIR, f'z{z}')
        img_lv = img_6k if (lw == Z3_W and lh == Z3_H) else img_6k.resize((lw, lh), Image.LANCZOS)
        mask_lv = mask_6k if (lw == Z3_W and lh == Z3_H) else np.asarray(mask_6k_img.resize((lw, lh), Image.BILINEAR))
        present = []
        for r in range(rows):
            for c in range(cols):
                x0, y0 = c * TILE_SIZE, r * TILE_SIZE
                x1, y1 = min(lw, x0 + TILE_SIZE), min(lh, y0 + TILE_SIZE)
                if sp['sparse'] and int(mask_lv[y0:y1, x0:x1].max()) < 8:
                    continue
                out_p = os.path.join(z_dir, f'{c}_{r}.webp')
                img_lv.crop((x0, y0, x1, y1)).save(out_p, 'WEBP', quality=sp['q'], method=4)
                total_files += 1
                total_bytes += os.path.getsize(out_p)
                present.append(f'{c}_{r}')
        meta_levels.append({
            'z': z, 'w': lw, 'h': lh, 'tileSize': TILE_SIZE, 'cols': cols, 'rows': rows,
            'dir': f'img/art/world-tiles/z{z}', 'tiles': present,
        })
        print(f'  z{z} ({lw}×{lh}): {len(present)}/{cols*rows} 瓦片')

    # 释放 6K 大图内存，再分东西两半渲染 12K (12288×8192) 原生超清层 z4！
    del img_6k, mask_6k, mask_6k_img
    print(f'[3/5] 分两半渲染 12K ({Z4_W}×{Z4_H}) 原生超清层 z4（保留每区 1002×668 完整像素）...')
    z4_dir = os.path.join(TILES_DIR, 'z4')
    z4_cols = math.ceil(Z4_W / TILE_SIZE)  # 24
    z4_rows = math.ceil(Z4_H / TILE_SIZE)  # 16
    half_w = Z4_W // 2  # 6144 = 12 * 512 精确对齐瓦片列边界！
    z4_present = []
    for half_idx, x_off in enumerate((0, half_w)):
        col_off = x_off // TILE_SIZE
        strip_img, strip_mask = render_stitched_strip(atlas, zone_cache, Z4_W, Z4_H, x_off, half_w)
        # 顺手存一份检验截图到 scratch 供人工复核（不进仓库）
        scr = r'C:\Users\Administrator\.gemini\antigravity\brain\05fd54f3-d54e-4fb4-9154-e15406073c42\scratch\seamless-test'
        if os.path.isdir(scr):
            if half_idx == 1:
                # 河林 + 东大陆中部 12K 实景裁切
                strip_img.crop((1600, 3200, 4900, 6200)).resize((1400, 1272), Image.LANCZOS).save(os.path.join(scr, 'verify_12k_ek_river.png'))
            else:
                # 卡利姆多中部 + 海加尔山 + 辛德拉 + 泽风岛 12K 实景裁切
                strip_img.crop((1400, 1400, 5600, 6000)).resize((1400, 1533), Image.LANCZOS).save(os.path.join(scr, 'verify_12k_kal_new.png'))
                # 海加尔山 (2482) 1:1 12K 近景实拍
                strip_img.crop((2250, 1950, 3900, 3250)).save(os.path.join(scr, 'verify_12k_hyjal_closeup.png'))
                # 泽风岛 (2521) 1:1 12K 近景实拍（在东半西缘 x≈6044，由半幅拼接完后单独检）
        for r in range(z4_rows):
            for lc in range(half_w // TILE_SIZE):
                x0, y0 = lc * TILE_SIZE, r * TILE_SIZE
                x1, y1 = min(half_w, x0 + TILE_SIZE), min(Z4_H, y0 + TILE_SIZE)
                if int(strip_mask[y0:y1, x0:x1].max()) < 8:
                    continue
                gc = col_off + lc
                out_p = os.path.join(z4_dir, f'{gc}_{r}.webp')
                strip_img.crop((x0, y0, x1, y1)).save(out_p, 'WEBP', quality=78, method=4)
                total_files += 1
                total_bytes += os.path.getsize(out_p)
                z4_present.append(f'{gc}_{r}')
        del strip_img, strip_mask
    z4_present.sort(key=lambda s: (int(s.split('_')[1]), int(s.split('_')[0])))
    meta_levels.append({
        'z': 4, 'w': Z4_W, 'h': Z4_H, 'tileSize': TILE_SIZE, 'cols': z4_cols, 'rows': z4_rows,
        'dir': 'img/art/world-tiles/z4', 'tiles': z4_present,
    })
    print(f'  z4 ({Z4_W}×{Z4_H}): {len(z4_present)}/{z4_cols*z4_rows} 瓦片')

    print('[4/5] 写入瓦片金字塔元数据至 upstream/world-tiles-meta.json、world-atlas.json 与 manifest.json...')
    pyramid = {
        'generatedAt': date.today().isoformat(),
        'master': {'w': Z4_W, 'h': Z4_H},
        'stitchedZones': len(zone_cache),
        'levels': meta_levels,
    }
    os.makedirs(os.path.dirname(UPSTREAM_META), exist_ok=True)
    with open(UPSTREAM_META, 'w', encoding='utf-8') as f:
        json.dump(pyramid, f, ensure_ascii=False, indent=2)

    atlas['tilePyramid'] = pyramid
    with open(ATLAS_PATH, 'w', encoding='utf-8') as f:
        json.dump(atlas, f, ensure_ascii=False, separators=(',', ':'))

    manifest = json.load(open(MANIFEST_PATH, encoding='utf-8'))
    if isinstance(manifest, dict) and 'items' in manifest:
        items = [it for it in manifest['items'] if not str(it.get('file', '')).startswith('world-tiles/')]
        meta_bytes = open(UPSTREAM_META, 'rb').read()
        items.append({
            'file': 'world-tiles/z4',
            'kind': 'world-tile-pyramid',
            'source': 'derived-local: client 947/1414/1415 + 43 local zone maps (12K native stitched)',
            'fetchedAt': date.today().isoformat(),
            'tiles': total_files,
            'bytes': total_bytes,
            'sha1': hashlib.sha1(meta_bytes).hexdigest(),
        })
        manifest['items'] = items
        with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f'[5/5] 全部完成！共生成 {total_files} 张 WebP 瓦片，总计 {total_bytes / 1024 / 1024:.2f} MB。')


if __name__ == '__main__':
    main()
