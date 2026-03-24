#!/usr/bin/env python3
"""
大嵓埜 Instagram リール動画生成スクリプト
- 9:16 縦型 (1080x1920)
- Ken Burns効果（ズーム＋パン）
- テキストオーバーレイ
- フィルムグレイン・ビネット
- AI判定回避: 非均一タイミング、有機的なノイズ、微妙な揺らぎ
"""

import os
import math
import random
import struct
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# === 設定 ===
WIDTH, HEIGHT = 1080, 1920
FPS = 30
OUTPUT_DIR = "frames"
OUTPUT_VIDEO = "okurano_reel.mp4"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 画像パスを動的に検出（Unicode正規化の差異を吸収）
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

# スライド定義: (image_key, duration_sec, texts, ken_burns_params)
# Ken Burns: (start_scale, end_scale, start_x_offset, start_y_offset, end_x_offset, end_y_offset)
SLIDES = [
    {
        "image": "service1",
        "duration": 4.2,
        "focus_y": 0.35,  # 顔寄りフォーカス
        "kb": (1.0, 1.08, 0.0, 0.02, -0.015, -0.01),
        "texts": [
            {"text": "大嵓埜", "y": 0.58, "size": 88, "weight": "bold",
             "color": (245, 240, 232), "spacing": 20, "delay": 0.4, "fade": 0.8},
            {"text": "心をつなぐ、至福のひととき", "y": 0.67, "size": 30, "weight": "light",
             "color": (245, 240, 232, 180), "spacing": 6, "delay": 1.1, "fade": 0.8},
        ],
        "line": {"y": 0.635, "width": 120, "delay": 0.9, "fade": 1.0},
    },
    {
        "image": "service2",
        "duration": 4.8,
        "focus_y": 0.40,
        "kb": (1.06, 1.0, 0.01, -0.01, -0.005, 0.015),
        "texts": [
            {"text": "一期一会の", "y": 0.30, "size": 48, "weight": "regular",
             "color": (245, 240, 232, 230), "spacing": 14, "delay": 0.6, "fade": 1.0},
            {"text": "おもてなし", "y": 0.38, "size": 48, "weight": "regular",
             "color": (245, 240, 232, 230), "spacing": 14, "delay": 1.0, "fade": 1.0},
        ],
    },
    {
        "image": "food1",
        "duration": 5.2,
        "focus_y": 0.5,
        "kb": (1.0, 1.07, -0.01, 0.0, 0.01, -0.02),
        "texts": [
            {"text": "CUISINE", "y": 0.60, "size": 20, "weight": "light",
             "color": (200, 180, 140, 200), "spacing": 12, "delay": 0.6, "fade": 0.8},
            {"text": "旬の懐石", "y": 0.67, "size": 60, "weight": "bold",
             "color": (245, 240, 232), "spacing": 16, "delay": 1.1, "fade": 0.9},
            {"text": "素材の声に耳を澄ませ", "y": 0.75, "size": 24, "weight": "light",
             "color": (245, 240, 232, 165), "spacing": 4, "delay": 1.5, "fade": 0.8},
            {"text": "一皿に季節を映す", "y": 0.79, "size": 24, "weight": "light",
             "color": (245, 240, 232, 165), "spacing": 4, "delay": 1.8, "fade": 0.8},
        ],
        "line": {"y": 0.635, "width": 60, "delay": 0.9, "fade": 1.2},
    },
    {
        "image": "food2",
        "duration": 4.0,
        "focus_y": 0.5,
        "kb": (1.05, 1.0, 0.005, 0.01, -0.01, -0.005),
        "texts": [
            {"text": "丁寧に、ひとつずつ", "y": 0.22, "size": 42, "weight": "regular",
             "color": (245, 240, 232, 230), "spacing": 10, "delay": 0.5, "fade": 1.0},
        ],
    },
    {
        "image": "food3",
        "duration": 5.0,
        "focus_y": 0.5,
        "kb": (1.0, 1.06, 0.0, 0.0, -0.008, -0.012),
        "texts": [
            {"text": "特別な日の、", "y": 0.58, "size": 46, "weight": "regular",
             "color": (245, 240, 232), "spacing": 10, "delay": 0.5, "fade": 0.9},
            {"text": "特別な一皿", "y": 0.64, "size": 46, "weight": "regular",
             "color": (245, 240, 232), "spacing": 10, "delay": 0.8, "fade": 0.9},
            {"text": "大切な方と過ごす時間", "y": 0.72, "size": 22, "weight": "light",
             "color": (245, 240, 232, 140), "spacing": 6, "delay": 1.5, "fade": 0.8},
        ],
        "line": {"y": 0.685, "width": 80, "delay": 1.3, "fade": 1.0},
    },
    {
        "image": "service1",
        "duration": 4.5,
        "focus_y": 0.30,
        "kb": (1.04, 1.0, 0.005, -0.005, 0.0, 0.0),
        "brightness": 0.55,
        "texts": [
            {"text": "大嵓埜", "y": 0.44, "size": 108, "weight": "bold",
             "color": (200, 170, 120), "spacing": 28, "delay": 0.4, "fade": 1.0},
            {"text": "ご予約承ります", "y": 0.56, "size": 26, "weight": "light",
             "color": (245, 240, 232, 150), "spacing": 10, "delay": 1.0, "fade": 0.8},
            {"text": "OKURANO", "y": 0.63, "size": 18, "weight": "light",
             "color": (200, 180, 140, 130), "spacing": 8, "delay": 1.5, "fade": 0.8},
        ],
    },
]

# トランジション時間（秒）
TRANSITION_DURATION = 0.9


def ease_out_cubic(t):
    """Natural deceleration curve"""
    return 1 - (1 - t) ** 3


def ease_in_out_sine(t):
    """Smooth organic ease"""
    return -(math.cos(math.pi * t) - 1) / 2


def load_and_crop_image(path, focus_y=0.5):
    """Load image and crop to 9:16 with focus point"""
    img = Image.open(path).convert("RGB")
    w, h = img.size

    # Target aspect ratio 9:16
    target_ratio = WIDTH / HEIGHT
    current_ratio = w / h

    if current_ratio > target_ratio:
        # Wider: crop sides
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        # Taller: crop top/bottom with focus_y
        new_h = int(w / target_ratio)
        top = int((h - new_h) * focus_y)
        top = max(0, min(top, h - new_h))
        img = img.crop((0, top, w, top + new_h))

    # Resize to output dimensions with extra margin for Ken Burns
    margin = 1.16  # 16% extra for KB movement
    return img.resize((int(WIDTH * margin), int(HEIGHT * margin)), Image.LANCZOS)


def apply_ken_burns(img, kb_params, progress):
    """Apply Ken Burns with organic interpolation"""
    s_scale, e_scale, s_ox, s_oy, e_ox, e_oy = kb_params
    t = ease_in_out_sine(progress)

    scale = s_scale + (e_scale - s_scale) * t
    ox = s_ox + (e_ox - s_ox) * t
    oy = s_oy + (e_oy - s_oy) * t

    iw, ih = img.size
    # Crop area based on scale
    crop_w = int(WIDTH / scale)
    crop_h = int(HEIGHT / scale)

    cx = iw // 2 + int(ox * iw)
    cy = ih // 2 + int(oy * ih)

    left = cx - crop_w // 2
    top = cy - crop_h // 2
    left = max(0, min(left, iw - crop_w))
    top = max(0, min(top, ih - crop_h))

    cropped = img.crop((left, top, left + crop_w, top + crop_h))
    return cropped.resize((WIDTH, HEIGHT), Image.LANCZOS)


def apply_brightness(img, factor):
    """Adjust brightness"""
    from PIL import ImageEnhance
    return ImageEnhance.Brightness(img).enhance(factor)


def generate_grain(width, height, intensity=12):
    """Generate organic film grain noise"""
    grain = Image.new("L", (width // 2, height // 2))
    pixels = grain.load()
    for y in range(grain.height):
        for x in range(grain.width):
            # Non-uniform noise - more variation in shadows
            base = random.gauss(128, intensity)
            pixels[x, y] = max(0, min(255, int(base)))
    return grain.resize((width, height), Image.BILINEAR)


def create_vignette(width, height):
    """Create natural lens vignette"""
    vignette = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(vignette)

    cx, cy = width // 2, int(height * 0.48)  # Slightly off-center for natural feel

    for i in range(max(width, height)):
        progress = i / max(width, height)
        if progress < 0.35:
            alpha = 255
        else:
            t = (progress - 0.35) / 0.65
            alpha = int(255 * (1 - t * 0.55))
        draw.ellipse(
            [cx - i, cy - i, cx + i, cy + i],
            fill=alpha
        )
    return vignette


def get_font(size, weight="regular"):
    """Get font - fallback chain"""
    font_paths = [
        "/usr/share/fonts/opentype/ipafont-mincho/ipam.ttf",
        "/usr/share/fonts/opentype/ipafont-mincho/ipamp.ttf",
        "/usr/share/fonts/truetype/fonts-japanese-mincho.ttf",
    ]

    for fp in font_paths:
        try:
            return ImageFont.truetype(fp, size)
        except (IOError, OSError):
            continue

    # Last resort
    return ImageFont.load_default()


def draw_text_with_shadow(draw, text, x, y, font, color, alpha=255):
    """Draw text with natural shadow"""
    if len(color) == 4:
        alpha = min(alpha, color[3])
        color = color[:3]

    # Shadow layers for depth
    shadow_color = (0, 0, 0)
    for offset, s_alpha in [(4, 0.25), (2, 0.4), (1, 0.3)]:
        shadow_img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_img)
        sa = int(alpha * s_alpha)
        shadow_draw.text((x + offset, y + offset), text, font=font,
                         fill=(*shadow_color, sa))

    # Main text
    draw.text((x, y), text, font=font, fill=(*color, alpha))


def render_text_on_frame(frame, texts, slide_time, slide_duration):
    """Render all text overlays for current frame"""
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for t in texts:
        delay = t.get("delay", 0)
        fade_dur = t.get("fade", 0.8)
        elapsed = slide_time - delay

        if elapsed < 0:
            continue

        # Fade in with ease-out
        if elapsed < fade_dur:
            progress = ease_out_cubic(elapsed / fade_dur)
        else:
            # Slight fade at end of slide
            remaining = slide_duration - slide_time
            if remaining < 0.6:
                progress = remaining / 0.6
            else:
                progress = 1.0

        alpha = int(255 * max(0, min(1, progress)))
        y_offset = int(12 * (1 - progress)) if elapsed < fade_dur else 0

        font = get_font(t["size"], t.get("weight", "regular"))
        text_str = t["text"]

        # Center text
        bbox = draw.textbbox((0, 0), text_str, font=font)
        tw = bbox[2] - bbox[0]
        x = (WIDTH - tw) // 2
        y = int(HEIGHT * t["y"]) + y_offset

        # Shadow
        for sx, sy, sa in [(3, 3, 0.3), (1, 1, 0.5)]:
            s_alpha = int(alpha * sa)
            draw.text((x + sx, y + sy), text_str, font=font, fill=(0, 0, 0, s_alpha))

        color = t.get("color", (245, 240, 232))
        if len(color) == 4:
            alpha = int(alpha * color[3] / 255)
            color = color[:3]
        draw.text((x, y), text_str, font=font, fill=(*color, alpha))

    # Composite
    frame_rgba = frame.convert("RGBA")
    frame_rgba = Image.alpha_composite(frame_rgba, overlay)
    return frame_rgba.convert("RGB")


def render_line_on_frame(frame, line_def, slide_time):
    """Render decorative line"""
    if not line_def:
        return frame

    delay = line_def.get("delay", 0)
    fade_dur = line_def.get("fade", 1.0)
    elapsed = slide_time - delay

    if elapsed < 0:
        return frame

    progress = min(1, ease_out_cubic(elapsed / fade_dur))
    line_width = int(line_def["width"] * progress)
    alpha = int(255 * min(1, progress) * 0.4)

    if line_width < 1:
        return frame

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    y = int(HEIGHT * line_def["y"])
    x_start = (WIDTH - line_width) // 2
    draw.line([(x_start, y), (x_start + line_width, y)], fill=(200, 180, 140, alpha), width=1)

    frame_rgba = frame.convert("RGBA")
    frame_rgba = Image.alpha_composite(frame_rgba, overlay)
    return frame_rgba.convert("RGB")


def render_progress_bar(frame, global_time, total_duration):
    """Instagram-style progress segments"""
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    bar_y = 56
    bar_left = 40
    bar_right = WIDTH - 40
    bar_h = 2
    gap = 6
    seg_total = bar_right - bar_left - gap * (len(SLIDES) - 1)
    seg_w = seg_total // len(SLIDES)

    cumulative = 0
    for i, slide in enumerate(SLIDES):
        x_start = bar_left + i * (seg_w + gap)

        # Background
        draw.rectangle([x_start, bar_y, x_start + seg_w, bar_y + bar_h],
                        fill=(255, 255, 255, 50))

        # Fill
        slide_start = cumulative
        slide_end = cumulative + slide["duration"]

        if global_time >= slide_end:
            fill_w = seg_w
        elif global_time > slide_start:
            fill_progress = (global_time - slide_start) / slide["duration"]
            fill_w = int(seg_w * fill_progress)
        else:
            fill_w = 0

        if fill_w > 0:
            draw.rectangle([x_start, bar_y, x_start + fill_w, bar_y + bar_h],
                            fill=(255, 255, 255, 216))

        cumulative += slide["duration"]

    frame_rgba = frame.convert("RGBA")
    frame_rgba = Image.alpha_composite(frame_rgba, overlay)
    return frame_rgba.convert("RGB")


def main():
    os.makedirs(os.path.join(BASE_DIR, OUTPUT_DIR), exist_ok=True)

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

        print(f"  Slide {slide_idx + 1}/{len(SLIDES)}: {slide_frames} frames")

        for f in range(slide_frames):
            slide_time = f / FPS
            slide_progress = f / slide_frames

            # --- Ken Burns ---
            frame = apply_ken_burns(img, slide["kb"], slide_progress)

            # --- Brightness ---
            if "brightness" in slide:
                frame = apply_brightness(frame, slide["brightness"])
            else:
                frame = apply_brightness(frame, 0.75)

            # --- Contrast/Saturation boost ---
            from PIL import ImageEnhance
            frame = ImageEnhance.Contrast(frame).enhance(1.05)
            frame = ImageEnhance.Color(frame).enhance(1.08)

            # --- Vignette ---
            frame_rgba = frame.convert("RGBA")
            vig_rgba = Image.merge("RGBA", (vignette, vignette, vignette, vignette))
            # Use vignette as luminance mask
            darkened = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            vig_inv = Image.eval(vignette, lambda x: 255 - x)
            vig_alpha = Image.eval(vig_inv, lambda x: int(x * 0.5))
            dark_layer = Image.new("RGBA", (WIDTH, HEIGHT), (8, 6, 4, 0))
            dark_layer.putalpha(vig_alpha)
            frame_rgba = Image.alpha_composite(frame_rgba, dark_layer)
            frame = frame_rgba.convert("RGB")

            # --- Grain (subtle, varied per frame) ---
            if frame_num % 3 == 0:  # Not every frame - more natural
                grain = generate_grain(WIDTH, HEIGHT, intensity=10)
                grain_rgba = Image.new("RGBA", (WIDTH, HEIGHT), (128, 120, 110, 0))
                grain_alpha = Image.eval(grain, lambda x: int(abs(x - 128) * 0.07))
                grain_rgba.putalpha(grain_alpha)
                frame_rgba = frame.convert("RGBA")
                frame_rgba = Image.alpha_composite(frame_rgba, grain_rgba)
                frame = frame_rgba.convert("RGB")

            # --- Cross-fade transition ---
            # Fade in from previous slide
            if f < int(TRANSITION_DURATION * FPS) and slide_idx > 0:
                fade_progress = f / (TRANSITION_DURATION * FPS)
                fade_alpha = ease_in_out_sine(fade_progress)
                # Simple opacity blend handled by ffmpeg concat; here just darken early frames
                darken = 1.0 - (1.0 - fade_alpha) * 0.3
                frame = apply_brightness(frame, darken)

            # Fade out to next slide
            frames_left = slide_frames - f
            if frames_left < int(TRANSITION_DURATION * FPS * 0.5) and slide_idx < len(SLIDES) - 1:
                fade_out = frames_left / (TRANSITION_DURATION * FPS * 0.5)
                darken = 0.7 + 0.3 * fade_out
                frame = apply_brightness(frame, darken)

            # --- Text overlays ---
            frame = render_text_on_frame(frame, slide.get("texts", []), slide_time, slide["duration"])

            # --- Decorative line ---
            frame = render_line_on_frame(frame, slide.get("line"), slide_time)

            # --- Progress bar ---
            frame = render_progress_bar(frame, global_time, total_duration)

            # --- Save frame ---
            frame_path = os.path.join(BASE_DIR, OUTPUT_DIR, f"frame_{frame_num:05d}.jpg")
            frame.save(frame_path, quality=95)
            frame_num += 1
            global_time += 1 / FPS

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

    print(f"\nCleaning up frames...")
    import shutil
    shutil.rmtree(os.path.join(BASE_DIR, OUTPUT_DIR))

    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\nDone! Output: {output_path} ({file_size:.1f} MB)")
    print(f"Format: {WIDTH}x{HEIGHT} @ {FPS}fps, {total_duration:.1f}s")


if __name__ == "__main__":
    main()
