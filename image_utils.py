from __future__ import annotations

from io import BytesIO
from typing import Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


Color = Tuple[int, int, int]


def load_image(file_or_bytes) -> Image.Image:
    image = Image.open(file_or_bytes)
    image = ImageOps.exif_transpose(image)
    return image.convert("RGB")


def compress_image(image: Image.Image, max_side: int = 1400, quality: int = 86) -> bytes:
    image = image.copy().convert("RGB")
    image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
    return buffer.getvalue()


def bytes_to_image(data: bytes) -> Image.Image:
    return load_image(BytesIO(data))


def apply_adjustments(
    image: Image.Image,
    temperature: int = 0,
    saturation: int = 100,
    brightness: int = 100,
) -> Image.Image:
    img = image.copy().convert("RGB")
    arr = np.asarray(img).astype(np.float32)

    temp = float(np.clip(temperature, -100, 100)) / 100.0
    if temp >= 0:
        arr[:, :, 0] *= 1.0 + 0.18 * temp
        arr[:, :, 2] *= 1.0 - 0.14 * temp
    else:
        cool = abs(temp)
        arr[:, :, 0] *= 1.0 - 0.12 * cool
        arr[:, :, 2] *= 1.0 + 0.20 * cool

    arr = np.clip(arr, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, mode="RGB")
    img = ImageEnhance.Color(img).enhance(max(saturation, 0) / 100.0)
    img = ImageEnhance.Brightness(img).enhance(max(brightness, 0) / 100.0)
    return img


def representative_color(image: Image.Image) -> Color:
    sample = image.copy().convert("RGB")
    sample.thumbnail((180, 180), Image.Resampling.BILINEAR)
    arr = np.asarray(sample).reshape(-1, 3).astype(np.float32)

    # Ignore near-white glare and near-black shadows so the chosen color feels expressive.
    brightness = arr.mean(axis=1)
    mask = (brightness > 35) & (brightness < 235)
    if mask.any():
        arr = arr[mask]

    pixels = arr[np.random.default_rng(42).choice(len(arr), size=min(6000, len(arr)), replace=False)]
    centroids = _initial_centroids(pixels, 5)
    for _ in range(12):
        distances = ((pixels[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        labels = distances.argmin(axis=1)
        for idx in range(len(centroids)):
            group = pixels[labels == idx]
            if len(group):
                centroids[idx] = group.mean(axis=0)

    distances = ((pixels[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
    labels = distances.argmin(axis=1)
    counts = np.bincount(labels, minlength=len(centroids))
    saturation = centroids.max(axis=1) - centroids.min(axis=1)
    scores = counts * (1.0 + saturation / 255.0)
    color = centroids[int(scores.argmax())]
    return tuple(int(x) for x in np.clip(color, 0, 255))  # type: ignore[return-value]


def _initial_centroids(pixels: np.ndarray, count: int) -> np.ndarray:
    if len(pixels) <= count:
        return np.pad(pixels, ((0, count - len(pixels)), (0, 0)), mode="edge")
    brightness = pixels.mean(axis=1)
    order = np.argsort(brightness)
    picks = np.linspace(0, len(order) - 1, count).astype(int)
    return pixels[order[picks]].copy()


def blend_colors(a: Color, b: Color) -> Color:
    arr = (np.array(a, dtype=np.float32) * 0.5) + (np.array(b, dtype=np.float32) * 0.5)
    return tuple(int(x) for x in np.clip(arr, 0, 255))  # type: ignore[return-value]


def color_to_hex(color: Color) -> str:
    return "#{:02X}{:02X}{:02X}".format(*color)


def image_to_png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def create_result_card(
    original: Image.Image,
    a_params: dict,
    b_params: dict,
) -> tuple[Image.Image, Color, Color, Color, str]:
    a_image = apply_adjustments(original, **a_params)
    b_image = apply_adjustments(original, **b_params)
    a_color = representative_color(a_image)
    b_color = representative_color(b_image)
    blended = blend_colors(a_color, b_color)
    hex_color = color_to_hex(blended)

    card = Image.new("RGB", (1080, 1680), "#fff8ef")
    draw = ImageDraw.Draw(card)
    _draw_background(draw, card.size, blended)

    title_font = _font(76, bold=True)
    subtitle_font = _font(34)
    label_font = _font(30, bold=True)
    body_font = _font(28)
    hex_font = _font(58, bold=True)

    draw.text((80, 78), "Color Us", fill="#2f2723", font=title_font)
    draw.text((84, 168), "OUR COLOR", fill="#866b5c", font=subtitle_font)

    a_photo = _polaroid(a_image, "A saw you", label_font)
    b_photo = _polaroid(b_image, "B saw you", label_font)
    card.paste(a_photo, (70, 250), a_photo)
    card.paste(b_photo, (555, 250), b_photo)

    _draw_swatch(draw, (95, 1020), a_color, "A COLOR", label_font, body_font)
    _draw_swatch(draw, (390, 1020), b_color, "B COLOR", label_font, body_font)

    draw.rounded_rectangle((250, 1240, 830, 1515), radius=70, fill=blended, outline="#ffffff", width=8)
    text_fill = "#2f2723" if sum(blended) > 420 else "#fff8ef"
    draw.text((540, 1300), "OUR COLOR", anchor="mm", fill=text_fill, font=label_font)
    draw.text((540, 1395), hex_color, anchor="mm", fill=text_fill, font=hex_font)
    draw.text((540, 1588), "同一张风景，因为你，有了新的颜色。", anchor="mm", fill="#6d5b52", font=body_font)

    return card, a_color, b_color, blended, hex_color


def _draw_background(draw: ImageDraw.ImageDraw, size: tuple[int, int], color: Color) -> None:
    w, h = size
    base = np.array([255, 248, 239], dtype=np.float32)
    accent = np.array(color, dtype=np.float32)
    for y in range(h):
        ratio = y / h
        mixed = base * (1 - ratio * 0.22) + accent * (ratio * 0.22)
        draw.line((0, y, w, y), fill=tuple(int(x) for x in mixed))


def _polaroid(image: Image.Image, caption: str, font: ImageFont.ImageFont) -> Image.Image:
    frame = Image.new("RGBA", (455, 660), (255, 252, 247, 255))
    shadow = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((12, 18, 445, 650), radius=18, fill=(70, 45, 30, 38))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    composed = Image.alpha_composite(shadow, frame)

    photo = ImageOps.fit(image, (385, 455), method=Image.Resampling.LANCZOS)
    composed.paste(photo, (35, 35))
    draw = ImageDraw.Draw(composed)
    draw.text((228, 565), caption, anchor="mm", fill="#55453d", font=font)
    return composed


def _draw_swatch(draw: ImageDraw.ImageDraw, xy: tuple[int, int], color: Color, title: str, title_font, body_font) -> None:
    x, y = xy
    draw.rounded_rectangle((x, y, x + 220, y + 150), radius=36, fill=color)
    draw.text((x, y + 180), title, fill="#5b4a42", font=title_font)
    draw.text((x, y + 222), color_to_hex(color), fill="#8c7367", font=body_font)


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()
