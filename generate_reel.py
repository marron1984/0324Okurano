#!/usr/bin/env python3
"""
大嵓埜 Instagram リール動画生成スクリプト
- 9:16 縦型 (1080x1920)
- Noto Serif CJK JP フォント（ウェイト別使い分け）
- 接待重視の画像構成
- Ken Burns効果（ズーム＋パン）
- フィルムグレイン・ビネット
- AI判定回避: 非均一タイミング、有機的なノイズ、微妙な揺らぎ
"""

import os
import math
import random
import subprocess
import shutil
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# === 設定 ===
WIDTH, HEIGHT = 1080, 1920
FPS = 30
OUTPUT_DIR = "frames"
OUTPUT_VIDEO = "okurano_reel.mp4"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# === フォント定義 (Noto Serif CJK JP) ===
FONT_PATHS = {
    "black":     "/usr/share/fonts/opentype/noto/NotoSerifCJK-Black.ttc",
    "bold":      "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
    "semibold":  "/usr/share/fonts/opentype/noto/NotoSerifCJK-SemiBold.ttc",
    "medium":    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Medium.ttc",
    "regular":   "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "light":     "/usr/share/fonts/opentype/noto/NotoSerifCJK-Light.ttc",
    "extralight":"/usr/share/fonts/opentype/noto/NotoSerifCJK-ExtraLight.ttc",
}

_font_cache = {}

def get_font(size, weight="regular"):
    """Noto Serif CJK JP をウェイト指定で取得"""
    key = (size, weight)
    if key in _font_cache:
        return _font_cache[key]

    path = FONT_PATHS.get(weight, FONT_PATHS["regular"])
    try:
        font = ImageFont.truetype(path, size)
    except (IOError, OSError):
        # フォールバック
        for p in FONT_PATHS.values():
            try:
                font = ImageFont.truetype(p, size)
                break
            except (IOError, OSError):
                continue
        else:
            font = ImageFont.load_default()

    _font_cache[key] = font
    return font


# === 画像パスを動的に検出（Unicode正規化の差異を吸収）===
def find_images():
    files = os.listdir(BASE_DIR)
    jpgs = sorted([f for f in files if f.upper().endswith('.JPG')])
    mapping = {}
    for f in jpgs:
        full = os.path.join(BASE_DIR, f)
        if '0014' in f:
            mapping["service1"] = full
        elif '0015' in f:
            mapping["service2"] = full
        elif '0035' in f:
            mapping["food1"] = full
        elif '0058' in f:
            mapping["food2"] = full
        elif '0083' in f:
            mapping["food3"] = full
    return mapping

IMAGES = find_images()

# === スライド定義 ===
# 接待重視構成 + ミシュラン訴求 + 店舗情報
# Ken Burns: (start_scale, end_scale, start_x_off, start_y_off, end_x_off, end_y_off)
SLIDES = [
    # --- Slide 1: フック / ミシュラン訴求 + 店名 ---
    {
        "image": "service1",
        "duration": 4.5,
        "focus_y": 0.35,
        "kb": (1.0, 1.08, 0.0, 0.02, -0.015, -0.01),
        "texts": [
            {"text": "ミシュランガイド掲載", "y": 0.44, "size": 32, "weight": "light",
             "color": (220, 195, 145, 210), "spacing": 8, "delay": 0.2, "fade": 0.7},
            {"text": "北新地  大嵓埜", "y": 0.51, "size": 120, "weight": "black",
             "color": (245, 240, 232), "spacing": 16, "delay": 0.5, "fade": 0.9},
            {"text": "心をつなぐ、至福のひととき", "y": 0.65, "size": 38, "weight": "light",
             "color": (245, 240, 232, 180), "spacing": 5, "delay": 1.2, "fade": 0.9},
        ],
        "line": {"y": 0.625, "width": 140, "delay": 1.0, "fade": 1.0},
    },
    # --- Slide 2: コンセプト「和啓清寂」 / 接客シーン ---
    {
        "image": "service2",
        "duration": 4.8,
        "focus_y": 0.38,
        "kb": (1.06, 1.0, 0.01, -0.01, -0.005, 0.015),
        "texts": [
            {"text": "和 啓 清 寂", "y": 0.28, "size": 72, "weight": "bold",
             "color": (200, 175, 130, 240), "spacing": 8, "delay": 0.4, "fade": 1.0},
            {"text": "一期一会の", "y": 0.39, "size": 56, "weight": "medium",
             "color": (245, 240, 232, 230), "spacing": 10, "delay": 0.9, "fade": 1.0},
            {"text": "おもてなし", "y": 0.465, "size": 56, "weight": "medium",
             "color": (245, 240, 232, 230), "spacing": 10, "delay": 1.2, "fade": 1.0},
        ],
        "line": {"y": 0.365, "width": 100, "delay": 0.7, "fade": 1.2},
    },
    # --- Slide 3: 接待の空間 / 接客シーン ---
    {
        "image": "service1",
        "duration": 4.8,
        "focus_y": 0.50,
        "kb": (1.04, 1.0, -0.02, 0.01, 0.01, -0.005),
        "brightness": 0.68,
        "texts": [
            {"text": "大切なお客様を", "y": 0.37, "size": 58, "weight": "medium",
             "color": (245, 240, 232, 230), "spacing": 8, "delay": 0.4, "fade": 0.9},
            {"text": "大切な場所で", "y": 0.45, "size": 58, "weight": "medium",
             "color": (245, 240, 232, 230), "spacing": 8, "delay": 0.8, "fade": 0.9},
            {"text": "完全個室のプライベート空間", "y": 0.55, "size": 30, "weight": "light",
             "color": (200, 185, 150, 170), "spacing": 4, "delay": 1.5, "fade": 0.8},
        ],
        "line": {"y": 0.52, "width": 80, "delay": 1.2, "fade": 1.0},
    },
    # --- Slide 4: 料理 / お食事シーン ---
    {
        "image": "food1",
        "duration": 4.5,
        "focus_y": 0.5,
        "kb": (1.0, 1.07, -0.01, 0.0, 0.01, -0.02),
        "texts": [
            {"text": "旬の懐石", "y": 0.56, "size": 80, "weight": "bold",
             "color": (245, 240, 232), "spacing": 18, "delay": 0.5, "fade": 0.9},
            {"text": "素材の味を活かした", "y": 0.67, "size": 34, "weight": "light",
             "color": (245, 240, 232, 170), "spacing": 4, "delay": 1.2, "fade": 0.8},
            {"text": "繊細な一皿", "y": 0.73, "size": 34, "weight": "light",
             "color": (245, 240, 232, 170), "spacing": 4, "delay": 1.5, "fade": 0.8},
        ],
        "line": {"y": 0.64, "width": 100, "delay": 0.9, "fade": 1.2},
    },
    # --- Slide 5: 料理の演出 / お食事シーン ---
    {
        "image": "food2",
        "duration": 4.2,
        "focus_y": 0.5,
        "kb": (1.05, 1.0, 0.005, 0.01, -0.01, -0.005),
        "texts": [
            {"text": "特別な日の", "y": 0.22, "size": 60, "weight": "medium",
             "color": (245, 240, 232), "spacing": 10, "delay": 0.4, "fade": 0.9},
            {"text": "特別な一皿", "y": 0.30, "size": 60, "weight": "medium",
             "color": (245, 240, 232), "spacing": 10, "delay": 0.8, "fade": 0.9},
        ],
    },
    # --- Slide 6: クロージング / 店舗情報 + ミシュラン再訴求 ---
    {
        "image": "service2",
        "duration": 5.5,
        "focus_y": 0.35,
        "kb": (1.04, 1.0, 0.005, -0.005, 0.0, 0.0),
        "brightness": 0.48,
        "texts": [
            {"text": "ミシュランガイド京都・大阪掲載", "y": 0.30, "size": 26, "weight": "light",
             "color": (220, 195, 145, 190), "spacing": 6, "delay": 0.2, "fade": 0.8},
            {"text": "北新地  大嵓埜", "y": 0.37, "size": 130, "weight": "black",
             "color": (200, 170, 120), "spacing": 20, "delay": 0.4, "fade": 1.0},
            {"text": "北新地FOODEARビル 3F", "y": 0.52, "size": 28, "weight": "light",
             "color": (245, 240, 232, 155), "spacing": 4, "delay": 1.2, "fade": 0.8},
            {"text": "JR北新地駅  徒歩2分", "y": 0.57, "size": 28, "weight": "light",
             "color": (245, 240, 232, 155), "spacing": 4, "delay": 1.5, "fade": 0.8},
            {"text": "TEL  06-6341-3535", "y": 0.64, "size": 32, "weight": "medium",
             "color": (245, 240, 232, 180), "spacing": 4, "delay": 1.9, "fade": 0.8},
            {"text": "ご予約承ります", "y": 0.72, "size": 34, "weight": "light",
             "color": (200, 185, 150, 160), "spacing": 8, "delay": 2.3, "fade": 0.8},
        ],
        "line": {"y": 0.49, "width": 120, "delay": 1.0, "fade": 1.2},
    },
]

TRANSITION_DURATION = 0.9


# === Easing functions ===
def ease_out_cubic(t):
    return 1 - (1 - t) ** 3

def ease_in_out_sine(t):
    return -(math.cos(math.pi * t) - 1) / 2


# === Image processing ===
def load_and_crop_image(path, focus_y=0.5):
    """9:16にクロップ + Ken Burns用マージン"""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    target_ratio = WIDTH / HEIGHT

    if w / h > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / target_ratio)
        top = int((h - new_h) * focus_y)
        top = max(0, min(top, h - new_h))
        img = img.crop((0, top, w, top + new_h))

    margin = 1.16
    return img.resize((int(WIDTH * margin), int(HEIGHT * margin)), Image.LANCZOS)


def apply_ken_burns(img, kb_params, progress):
    """有機的なKen Burns効果"""
    s_scale, e_scale, s_ox, s_oy, e_ox, e_oy = kb_params
    t = ease_in_out_sine(progress)

    scale = s_scale + (e_scale - s_scale) * t
    ox = s_ox + (e_ox - s_ox) * t
    oy = s_oy + (e_oy - s_oy) * t

    iw, ih = img.size
    crop_w = int(WIDTH / scale)
    crop_h = int(HEIGHT / scale)

    cx = iw // 2 + int(ox * iw)
    cy = ih // 2 + int(oy * ih)

    left = max(0, min(cx - crop_w // 2, iw - crop_w))
    top = max(0, min(cy - crop_h // 2, ih - crop_h))

    return img.crop((left, top, left + crop_w, top + crop_h)).resize((WIDTH, HEIGHT), Image.LANCZOS)


def apply_brightness(img, factor):
    return ImageEnhance.Brightness(img).enhance(factor)


def generate_grain(width, height, intensity=10):
    """フィルムグレインノイズ"""
    grain = Image.new("L", (width // 2, height // 2))
    pixels = grain.load()
    for y in range(grain.height):
        for x in range(grain.width):
            pixels[x, y] = max(0, min(255, int(random.gauss(128, intensity))))
    return grain.resize((width, height), Image.BILINEAR)


def create_vignette(width, height):
    """自然なレンズビネット"""
    vignette = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(vignette)
    cx, cy = width // 2, int(height * 0.48)

    for i in range(max(width, height)):
        p = i / max(width, height)
        if p < 0.35:
            alpha = 255
        else:
            alpha = int(255 * (1 - ((p - 0.35) / 0.65) * 0.55))
        draw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=alpha)
    return vignette


# === Rendering ===
def render_text_on_frame(frame, texts, slide_time, slide_duration):
    """テキストオーバーレイ描画"""
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for t in texts:
        delay = t.get("delay", 0)
        fade_dur = t.get("fade", 0.8)
        elapsed = slide_time - delay

        if elapsed < 0:
            continue

        # Fade計算
        if elapsed < fade_dur:
            progress = ease_out_cubic(elapsed / fade_dur)
        else:
            remaining = slide_duration - slide_time
            progress = min(1.0, remaining / 0.6) if remaining < 0.6 else 1.0

        alpha = int(255 * max(0, min(1, progress)))
        y_offset = int(16 * (1 - progress)) if elapsed < fade_dur else 0

        font = get_font(t["size"], t.get("weight", "regular"))
        text_str = t["text"]

        # 中央揃え
        bbox = draw.textbbox((0, 0), text_str, font=font)
        tw = bbox[2] - bbox[0]
        x = (WIDTH - tw) // 2
        y = int(HEIGHT * t["y"]) + y_offset

        # 多層シャドウ（自然な奥行き感）
        for sx, sy, sa in [(6, 6, 0.15), (3, 3, 0.3), (1, 1, 0.45)]:
            s_alpha = int(alpha * sa)
            draw.text((x + sx, y + sy), text_str, font=font, fill=(0, 0, 0, s_alpha))

        # メインテキスト
        color = t.get("color", (245, 240, 232))
        if len(color) == 4:
            alpha = int(alpha * color[3] / 255)
            color = color[:3]
        draw.text((x, y), text_str, font=font, fill=(*color, alpha))

    frame_rgba = frame.convert("RGBA")
    return Image.alpha_composite(frame_rgba, overlay).convert("RGB")


def render_line_on_frame(frame, line_def, slide_time):
    """装飾ライン描画"""
    if not line_def:
        return frame

    elapsed = slide_time - line_def.get("delay", 0)
    if elapsed < 0:
        return frame

    progress = min(1, ease_out_cubic(elapsed / line_def.get("fade", 1.0)))
    line_width = int(line_def["width"] * progress)
    alpha = int(255 * min(1, progress) * 0.45)

    if line_width < 1:
        return frame

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    y = int(HEIGHT * line_def["y"])
    x_start = (WIDTH - line_width) // 2
    draw.line([(x_start, y), (x_start + line_width, y)], fill=(200, 180, 140, alpha), width=2)

    return Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")


def render_progress_bar(frame, global_time):
    """Instagramストーリー風プログレスバー"""
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    bar_y = 60
    bar_left = 44
    bar_right = WIDTH - 44
    bar_h = 3
    gap = 6
    seg_total = bar_right - bar_left - gap * (len(SLIDES) - 1)
    seg_w = seg_total // len(SLIDES)

    cumulative = 0
    for i, slide in enumerate(SLIDES):
        x_start = bar_left + i * (seg_w + gap)
        draw.rounded_rectangle([x_start, bar_y, x_start + seg_w, bar_y + bar_h],
                                radius=1, fill=(255, 255, 255, 50))

        slide_end = cumulative + slide["duration"]
        if global_time >= slide_end:
            fill_w = seg_w
        elif global_time > cumulative:
            fill_w = int(seg_w * (global_time - cumulative) / slide["duration"])
        else:
            fill_w = 0

        if fill_w > 0:
            draw.rounded_rectangle([x_start, bar_y, x_start + fill_w, bar_y + bar_h],
                                    radius=1, fill=(255, 255, 255, 220))
        cumulative += slide["duration"]

    return Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")


# === Main ===
def main():
    os.makedirs(os.path.join(BASE_DIR, OUTPUT_DIR), exist_ok=True)

    # フォント確認
    print("Checking fonts...")
    test_font = get_font(48, "bold")
    print(f"  Font: {test_font.getname()}")

    print("Loading images...")
    loaded_images = {}
    for key, path in IMAGES.items():
        focus_y = 0.5
        for s in SLIDES:
            if s["image"] == key:
                focus_y = s.get("focus_y", 0.5)
                break
        loaded_images[key] = load_and_crop_image(path, focus_y)
        print(f"  Loaded: {key}")

    print("Creating vignette...")
    vignette = create_vignette(WIDTH, HEIGHT)

    total_duration = sum(s["duration"] for s in SLIDES)
    total_frames = int(total_duration * FPS)

    print(f"Rendering {total_frames} frames ({total_duration:.1f}s @ {FPS}fps)...")

    frame_num = 0
    global_time = 0

    for slide_idx, slide in enumerate(SLIDES):
        slide_frames = int(slide["duration"] * FPS)
        img = loaded_images[slide["image"]]

        print(f"  Slide {slide_idx + 1}/{len(SLIDES)}: {slide_frames} frames "
              f"[{slide['image']}]")

        for f in range(slide_frames):
            slide_time = f / FPS
            slide_progress = f / slide_frames

            # Ken Burns
            frame = apply_ken_burns(img, slide["kb"], slide_progress)

            # 明るさ・コントラスト・彩度
            brightness = slide.get("brightness", 0.75)
            frame = apply_brightness(frame, brightness)
            frame = ImageEnhance.Contrast(frame).enhance(1.05)
            frame = ImageEnhance.Color(frame).enhance(1.08)

            # ビネット
            vig_inv = Image.eval(vignette, lambda x: 255 - x)
            vig_alpha = Image.eval(vig_inv, lambda x: int(x * 0.5))
            dark_layer = Image.new("RGBA", (WIDTH, HEIGHT), (8, 6, 4, 0))
            dark_layer.putalpha(vig_alpha)
            frame = Image.alpha_composite(frame.convert("RGBA"), dark_layer).convert("RGB")

            # グレイン（3フレームおき = 不規則感）
            if frame_num % 3 == 0:
                grain = generate_grain(WIDTH, HEIGHT, intensity=10)
                grain_rgba = Image.new("RGBA", (WIDTH, HEIGHT), (128, 120, 110, 0))
                grain_alpha = Image.eval(grain, lambda x: int(abs(x - 128) * 0.07))
                grain_rgba.putalpha(grain_alpha)
                frame = Image.alpha_composite(frame.convert("RGBA"), grain_rgba).convert("RGB")

            # クロスフェード(フェードイン)
            if f < int(TRANSITION_DURATION * FPS) and slide_idx > 0:
                fade_p = ease_in_out_sine(f / (TRANSITION_DURATION * FPS))
                frame = apply_brightness(frame, 1.0 - (1.0 - fade_p) * 0.3)

            # クロスフェード(フェードアウト)
            frames_left = slide_frames - f
            if frames_left < int(TRANSITION_DURATION * FPS * 0.5) and slide_idx < len(SLIDES) - 1:
                fade_out = frames_left / (TRANSITION_DURATION * FPS * 0.5)
                frame = apply_brightness(frame, 0.7 + 0.3 * fade_out)

            # テキスト
            frame = render_text_on_frame(frame, slide.get("texts", []), slide_time, slide["duration"])
            frame = render_line_on_frame(frame, slide.get("line"), slide_time)
            frame = render_progress_bar(frame, global_time)

            # 保存
            frame_path = os.path.join(BASE_DIR, OUTPUT_DIR, f"frame_{frame_num:05d}.jpg")
            frame.save(frame_path, quality=95)
            frame_num += 1
            global_time += 1 / FPS

    # エンコード
    print(f"\nEncoding video with ffmpeg...")
    output_path = os.path.join(BASE_DIR, OUTPUT_VIDEO)
    frames_pattern = os.path.join(BASE_DIR, OUTPUT_DIR, "frame_%05d.jpg")

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", frames_pattern,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-preset", "slow",
        "-profile:v", "high",
        "-movflags", "+faststart",
        "-vf", "setsar=1:1",
        output_path
    ]
    subprocess.run(cmd, check=True)

    print("Cleaning up frames...")
    shutil.rmtree(os.path.join(BASE_DIR, OUTPUT_DIR))

    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\nDone! Output: {output_path} ({file_size:.1f} MB)")
    print(f"Format: {WIDTH}x{HEIGHT} @ {FPS}fps, {total_duration:.1f}s")


if __name__ == "__main__":
    main()
